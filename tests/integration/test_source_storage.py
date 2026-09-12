"""S3 policy and staged transport persistence against actual PostgreSQL."""

from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
from equity_schema.ingestion import (
    AttemptRequest,
    CaptureMetadata,
    ResponseHeaders,
    finalize_attempt,
    mark_dispatched,
    prepare_attempt,
    record_response_headers,
    recover_interrupted_attempt,
    validate_stage_lease,
)
from equity_schema.workflow import (
    LeaseLost,
    add_watchlist_stock,
    cancel_request,
    claim_next,
    create_workspace_watchlist,
    start_stage,
)

from tests.evidence_seed import seed_evidence

pytestmark = pytest.mark.integration


@pytest.fixture
def active_fetch(db_admin, db):
    ids = seed_evidence(db_admin)
    policy = db_admin.execute(
        "SELECT policy_revision_id FROM capture_policy_links WHERE capture_id=%s", (ids["capture"],)
    ).fetchone()["policy_revision_id"]
    workspace = create_workspace_watchlist(db, name="S3 source test")
    request = add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key="fetch",
    )
    lease = claim_next(db, worker_id="fetch-test")
    assert lease is not None
    stage = start_stage(db, lease, stage_key="source_fetch")
    resource = AttemptRequest(
        uuid4(),
        1,
        ids["source"],
        policy,
        "test/issuer",
        "https://example.invalid/issuer.json",
        "a" * 64,
    )
    return ids, request, lease, stage, resource


def start_response(db, active_fetch, *, status=200, headers=None):
    _, _, lease, stage, resource = active_fetch
    attempt = prepare_attempt(db, lease, stage, resource)
    mark_dispatched(db, lease, attempt, datetime.now(UTC))
    record_response_headers(
        db,
        lease,
        attempt,
        datetime.now(UTC),
        status,
        headers or ResponseHeaders(content_type="application/json"),
    )
    return attempt


def test_archive_capture_policy_and_attempt_finalize_atomically(db_admin, db, active_fetch):
    _, _, lease, _, resource = active_fetch
    attempt = start_response(db, active_fetch)
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "b" * 64, "test/verified.json.gz", 123)
    result = finalize_attempt(
        db, lease, attempt, "complete", datetime.now(UTC), completed_capture=capture
    )
    assert result == capture.capture_id
    row = db.execute(
        "SELECT a.state,a.completed_capture_id,p.policy_revision_id,c.http_status "
        "FROM source_fetch_attempts a JOIN source_captures c ON c.id=a.completed_capture_id "
        "JOIN capture_policy_links p ON p.capture_id=c.id WHERE a.id=%s",
        (attempt,),
    ).fetchone()
    assert row == {
        "state": "complete",
        "completed_capture_id": capture.capture_id,
        "policy_revision_id": resource.policy_revision_id,
        "http_status": 200,
    }
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
        finalize_attempt(
            db, lease, attempt, "complete", datetime.now(UTC), completed_capture=capture
        )


def test_prepare_must_commit_before_dispatch(db, active_fetch):
    _, _, lease, stage, resource = active_fetch
    with pytest.raises(RuntimeError, match="idle"):
        with db.transaction():
            prepare_attempt(db, lease, stage, resource)


def test_partial_200_keeps_status_but_cannot_publish_capture(db, active_fetch):
    _, _, lease, _, _ = active_fetch
    attempt = start_response(db, active_fetch)
    finalize_attempt(
        db,
        lease,
        attempt,
        "transport_error",
        datetime.now(UTC),
        failure_code="incomplete_body",
        failure_detail="Response ended early",
    )
    row = db.execute(
        "SELECT state,http_status,completed_capture_id FROM source_fetch_attempts WHERE id=%s",
        (attempt,),
    ).fetchone()
    assert row == {"state": "transport_error", "http_status": 200, "completed_capture_id": None}


def test_cancelled_worker_cannot_publish_late_blob(db, active_fetch):
    _, request, lease, _, _ = active_fetch
    attempt = start_response(db, active_fetch)
    cancel_request(db, request_id=request.request_id)
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "b" * 64, "test/late.json.gz", 123)
    with pytest.raises(LeaseLost):
        finalize_attempt(
            db, lease, attempt, "complete", datetime.now(UTC), completed_capture=capture
        )
    assert (
        db.execute("SELECT id FROM source_captures WHERE id=%s", (capture.capture_id,)).fetchone()
        is None
    )
    assert recover_interrupted_attempt(db, attempt)
    assert (
        db.execute("SELECT state FROM source_fetch_attempts WHERE id=%s", (attempt,)).fetchone()[
            "state"
        ]
        == "interrupted_unknown"
    )


def test_current_lease_cannot_be_recovered_as_interrupted(db, active_fetch):
    _, _, lease, stage, resource = active_fetch
    attempt = prepare_attempt(db, lease, stage, resource)
    validate_stage_lease(db, lease, stage)
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
        recover_interrupted_attempt(db, attempt)


def test_runtime_cannot_insert_capture_or_self_approve_policy(db):
    for table in (
        "source_policy_revisions",
        "source_fetch_attempts",
        "capture_policy_links",
        "source_captures",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(
                psycopg.sql.SQL("INSERT INTO {} DEFAULT VALUES").format(
                    psycopg.sql.Identifier(table)
                )
            )


def complete_representation(db, active_fetch):
    _, _, lease, _, _ = active_fetch
    attempt = start_response(
        db,
        active_fetch,
        headers=ResponseHeaders(etag='"v1"', last_modified="Fri, 11 Sep 2026 00:00:00 GMT"),
    )
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "c" * 64, "test/representation.gz", 100)
    finalize_attempt(db, lease, attempt, "complete", datetime.now(UTC), completed_capture=capture)
    return capture


def test_304_reuses_exact_validated_representation_without_new_capture(db, active_fetch):
    from dataclasses import replace

    _, _, lease, stage, resource = active_fetch
    capture = complete_representation(db, active_fetch)
    conditional = replace(
        resource,
        logical_fetch_id=uuid4(),
        validator_capture_id=capture.capture_id,
        if_none_match='"v1"',
    )
    attempt = prepare_attempt(db, lease, stage, conditional)
    mark_dispatched(db, lease, attempt, datetime.now(UTC))
    record_response_headers(
        db, lease, attempt, datetime.now(UTC), 304, ResponseHeaders(etag='"v1"')
    )
    before = db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"]
    finalize_attempt(
        db, lease, attempt, "not_modified", datetime.now(UTC), reused_capture_id=capture.capture_id
    )
    assert db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == before
    row = db.execute(
        "SELECT reused_capture_id,completed_capture_id,http_status "
        "FROM source_fetch_attempts WHERE id=%s",
        (attempt,),
    ).fetchone()
    assert row == {
        "reused_capture_id": capture.capture_id,
        "completed_capture_id": None,
        "http_status": 304,
    }


@pytest.mark.parametrize(
    "changed",
    [
        {"if_none_match": '"wrong"'},
        {"request_params_hash": "e" * 64},
        {"source_object_key": "different/resource"},
        {"request_url": "https://example.invalid/another.json"},
    ],
)
def test_conditional_request_cannot_borrow_another_representation(db, active_fetch, changed):
    from dataclasses import replace

    _, _, lease, stage, resource = active_fetch
    capture = complete_representation(db, active_fetch)
    conditional = replace(
        resource,
        logical_fetch_id=uuid4(),
        validator_capture_id=capture.capture_id,
        if_none_match='"v1"',
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="representation"):
        prepare_attempt(db, lease, stage, replace(conditional, **changed))


def test_policy_from_another_source_is_rejected(db_admin, db, active_fetch):
    from dataclasses import replace

    _, _, lease, stage, resource = active_fetch
    other = seed_evidence(db_admin)
    policy = db_admin.execute(
        "SELECT policy_revision_id FROM capture_policy_links WHERE capture_id=%s",
        (other["capture"],),
    ).fetchone()["policy_revision_id"]
    with pytest.raises(psycopg.errors.CheckViolation, match="policy source"):
        prepare_attempt(db, lease, stage, replace(resource, policy_revision_id=policy))


def test_lost_or_ended_stage_blocks_dispatch(db, active_fetch):
    from equity_schema.workflow import finish_stage

    _, _, lease, stage, resource = active_fetch
    attempt = prepare_attempt(db, lease, stage, resource)
    finish_stage(db, lease, stage_id=stage, outcome="failed", reason="abandoned")
    with pytest.raises(LeaseLost):
        mark_dispatched(db, lease, attempt, datetime.now(UTC))
    assert recover_interrupted_attempt(db, attempt)
    assert not recover_interrupted_attempt(db, attempt)


def test_raw_sql_cannot_dispatch_before_prepare_transaction_commits(db, active_fetch):
    from dataclasses import asdict

    from psycopg.types.json import Jsonb

    _, _, lease, stage, resource = active_fetch
    values = {
        key: str(value) if isinstance(value, type(uuid4())) else value
        for key, value in asdict(resource).items()
        if value is not None
    }
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="committed"):
        with db.transaction():
            attempt = db.execute(
                "SELECT ingestion_prepare(%s,%s,%s) AS id",
                (Jsonb(lease.as_json()), stage, Jsonb(values)),
            ).fetchone()["id"]
            db.execute(
                "SELECT ingestion_dispatch(%s,%s,%s)",
                (Jsonb(lease.as_json()), attempt, datetime.now(UTC)),
            )


def test_headers_are_allowlisted_and_not_overwritten(db, active_fetch):
    from psycopg.types.json import Jsonb

    _, _, lease, stage, resource = active_fetch
    attempt = prepare_attempt(db, lease, stage, resource)
    mark_dispatched(db, lease, attempt, datetime.now(UTC))
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "SELECT ingestion_headers(%s,%s,%s,%s,%s)",
            (
                Jsonb(lease.as_json()),
                attempt,
                datetime.now(UTC),
                200,
                Jsonb({"authorization": "must not be stored"}),
            ),
        )
    record_response_headers(
        db, lease, attempt, datetime.now(UTC), 200, ResponseHeaders(etag='"first"')
    )
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
        record_response_headers(db, lease, attempt, datetime.now(UTC), 503, ResponseHeaders())


def test_redirect_body_remains_nonfinancial_archived_evidence(db, active_fetch):
    _, _, lease, _, _ = active_fetch
    attempt = start_response(
        db,
        active_fetch,
        status=302,
        headers=ResponseHeaders(location="https://example.invalid/issuer.json"),
    )
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "c" * 64, "test/redirect.gz", 10)
    finalize_attempt(db, lease, attempt, "redirected", datetime.now(UTC), completed_capture=capture)
    assert (
        db.execute(
            "SELECT http_status FROM source_captures WHERE id=%s", (capture.capture_id,)
        ).fetchone()["http_status"]
        == 302
    )


def test_invalid_capture_metadata_rolls_back_entire_finalization(db, active_fetch):
    _, _, lease, _, _ = active_fetch
    attempt = start_response(db, active_fetch)
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "invalid", "test/bad.gz", 10)
    with pytest.raises(psycopg.errors.CheckViolation):
        finalize_attempt(
            db, lease, attempt, "complete", datetime.now(UTC), completed_capture=capture
        )
    assert (
        db.execute("SELECT id FROM source_captures WHERE id=%s", (capture.capture_id,)).fetchone()
        is None
    )
    assert (
        db.execute("SELECT state FROM source_fetch_attempts WHERE id=%s", (attempt,)).fetchone()[
            "state"
        ]
        == "in_progress"
    )


def test_new_owner_capture_cannot_commit_without_policy_link(db_admin, active_fetch):
    ids, _, _, _, _ = active_fetch
    with pytest.raises(psycopg.errors.CheckViolation, match="policy link"):
        db_admin.execute(
            "INSERT INTO source_captures SELECT %s,source_id,source_object_key,request_url,"
            "request_params_hash,requested_at,completed_at,fetched_at,http_status,body_sha256,"
            "blob_key,byte_count,content_type,terms_review_reference "
            "FROM source_captures WHERE id=%s",
            (uuid4(), ids["capture"]),
        )


def test_fetch_budget_and_identity_do_not_reset(db, active_fetch):
    from dataclasses import replace

    _, _, lease, stage, resource = active_fetch
    for sequence in range(1, 4):
        attempt = prepare_attempt(db, lease, stage, replace(resource, sequence=sequence))
        mark_dispatched(db, lease, attempt, datetime.now(UTC))
        finalize_attempt(
            db, lease, attempt, "transport_error", datetime.now(UTC), failure_code="timeout"
        )
    with pytest.raises(psycopg.errors.InvalidParameterValue, match="budget"):
        prepare_attempt(db, lease, stage, replace(resource, sequence=4))


@pytest.mark.parametrize("status", [300, 305, 306, 399])
def test_refused_redirect_retains_actual_status_and_complete_body(db, active_fetch, status):
    _, _, lease, _, _ = active_fetch
    attempt = start_response(db, active_fetch, status=status)
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "c" * 64, "test/refused.gz", 10)
    finalize_attempt(
        db,
        lease,
        attempt,
        "redirect_refused",
        datetime.now(UTC),
        completed_capture=capture,
        failure_code="unsupported_redirect",
    )
    row = db.execute(
        "SELECT a.state,a.http_status,c.http_status AS capture_status "
        "FROM source_fetch_attempts a JOIN source_captures c ON c.id=a.completed_capture_id "
        "WHERE a.id=%s",
        (attempt,),
    ).fetchone()
    assert row == {
        "state": "redirect_refused",
        "http_status": status,
        "capture_status": status,
    }


def test_concurrent_finalizations_publish_exactly_one_capture(db, active_fetch, test_database_dsn):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from psycopg.rows import dict_row

    _, _, lease, _, _ = active_fetch
    attempt = start_response(db, active_fetch)
    barrier = Barrier(2)
    captures = [
        CaptureMetadata(uuid4(), datetime.now(UTC), "d" * 64, "test/concurrent.gz", 10)
        for _ in range(2)
    ]

    def finish(capture):
        with psycopg.connect(test_database_dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            conn.execute("SET statement_timeout='5s'")
            barrier.wait(timeout=5)
            try:
                return finalize_attempt(
                    conn,
                    lease,
                    attempt,
                    "complete",
                    datetime.now(UTC),
                    completed_capture=capture,
                )
            except psycopg.errors.ObjectNotInPrerequisiteState:
                return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(finish, captures))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    stored = db.execute(
        "SELECT c.id FROM source_captures c JOIN capture_policy_links p ON p.capture_id=c.id "
        "WHERE c.id=ANY(%s)",
        ([capture.capture_id for capture in captures],),
    ).fetchall()
    assert stored == [{"id": winners[0]}]


def test_owner_cannot_rewrite_terminal_attempt_or_policy_history(db_admin, db, active_fetch):
    _, _, lease, _, resource = active_fetch
    attempt = start_response(db, active_fetch)
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "d" * 64, "test/immutable.gz", 10)
    finalize_attempt(db, lease, attempt, "complete", datetime.now(UTC), completed_capture=capture)
    statements = [
        ("UPDATE source_fetch_attempts SET failure_detail='rewritten' WHERE id=%s", attempt),
        ("DELETE FROM source_fetch_attempts WHERE id=%s", attempt),
        (
            "UPDATE source_policy_revisions SET permitted_use='rewritten' WHERE id=%s",
            resource.policy_revision_id,
        ),
        ("DELETE FROM capture_policy_links WHERE capture_id=%s", capture.capture_id),
    ]
    for statement, identifier in statements:
        with pytest.raises(
            (psycopg.errors.ObjectNotInPrerequisiteState, psycopg.errors.CheckViolation),
            match="immutable",
        ):
            db_admin.execute(statement, (identifier,))


def test_capture_cannot_contradict_recorded_content_type(db, active_fetch):
    _, _, lease, _, _ = active_fetch
    attempt = start_response(db, active_fetch)
    capture = CaptureMetadata(
        uuid4(), datetime.now(UTC), "d" * 64, "test/wrong-type.gz", 10, "application/xml"
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="content type"):
        finalize_attempt(
            db, lease, attempt, "complete", datetime.now(UTC), completed_capture=capture
        )
    assert (
        db.execute("SELECT id FROM source_captures WHERE id=%s", (capture.capture_id,)).fetchone()
        is None
    )
