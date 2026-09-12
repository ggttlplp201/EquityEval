"""Current S3 attempts must survive in point-in-time capture freshness manifests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
)
from equity_schema.vintage import SourceObject, prepare_capture_manifest
from equity_schema.workflow import (
    add_watchlist_stock,
    cancel_request,
    claim_next,
    create_workspace_watchlist,
    start_stage,
)

from tests.evidence_seed import seed_evidence

pytestmark = pytest.mark.integration


@pytest.fixture
def attempt_vintage(db_admin, db):
    ids = seed_evidence(db_admin)
    capture = db_admin.execute(
        "SELECT c.*,p.policy_revision_id FROM source_captures c "
        "JOIN capture_policy_links p ON p.capture_id=c.id WHERE c.id=%s",
        (ids["capture"],),
    ).fetchone()
    workspace = create_workspace_watchlist(db, name="S3 attempt vintage")
    request = add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key="attempt-vintage",
    )
    lease = claim_next(db, worker_id="vintage-review")
    assert lease is not None
    stage = start_stage(db, lease, stage_key="source_fetch")
    resource = AttemptRequest(
        uuid4(),
        1,
        ids["source"],
        capture["policy_revision_id"],
        capture["source_object_key"],
        capture["request_url"],
        capture["request_params_hash"],
    )
    return ids, request, lease, stage, resource


def start(db, setup, *, status=503, conditional=None, object_key=None):
    _, _, lease, stage, resource = setup
    request = replace(
        resource,
        logical_fetch_id=uuid4(),
        source_object_key=object_key or resource.source_object_key,
        validator_capture_id=conditional,
        if_none_match='"v1"' if conditional else None,
    )
    attempt = prepare_attempt(db, lease, stage, request)
    mark_dispatched(db, lease, attempt, datetime.now(UTC))
    record_response_headers(
        db,
        lease,
        attempt,
        datetime.now(UTC),
        status,
        ResponseHeaders(etag='"v1"', content_type="application/json"),
    )
    return attempt


def finish(db, setup, attempt, outcome, *, capture=None, reused=None):
    finalize_attempt(
        db,
        setup[2],
        attempt,
        outcome,
        datetime.now(UTC),
        completed_capture=capture,
        reused_capture_id=reused,
    )
    return db.execute(
        "SELECT finished_at FROM source_fetch_attempts WHERE id=%s", (attempt,)
    ).fetchone()["finished_at"]


def complete(db, setup):
    attempt = start(db, setup, status=200)
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "b" * 64, "test/current-source.gz", 20)
    cutoff = finish(db, setup, attempt, "complete", capture=capture)
    return attempt, capture, cutoff


def manifest(db, setup, cutoff, *, object_key=None):
    resource = setup[4]
    return prepare_capture_manifest(
        db,
        requirements=(
            SourceObject(
                resource.source_id, object_key or resource.source_object_key, "financial_payload"
            ),
        ),
        captured_before=cutoff,
    )


def test_new_s3_failure_retains_old_capture_and_current_failure_id(db, attempt_vintage):
    attempt = start(db, attempt_vintage)
    cutoff = finish(db, attempt_vintage, attempt, "http_error")
    result = manifest(db, attempt_vintage, cutoff)
    assert result.capture_ids == (attempt_vintage[0]["capture"],)
    assert result.failed_capture_ids == ()
    assert result.attempt_ids == result.failed_attempt_ids == (attempt,)
    assert "newer_capture_failed" in result.flags
    assert result.usable


def test_failed_s3_object_without_old_body_remains_explicit_gap(db, attempt_vintage):
    attempt = start(db, attempt_vintage, object_key="unavailable/object")
    cutoff = finish(db, attempt_vintage, attempt, "http_error")
    result = manifest(db, attempt_vintage, cutoff, object_key="unavailable/object")
    assert result.capture_ids == () and not result.usable
    assert result.failed_attempt_ids == (attempt,)
    assert {"capture_unavailable", "capture_failed"} <= set(result.flags)


def test_prior_s3_failure_does_not_override_later_success(db, attempt_vintage):
    failure = start(db, attempt_vintage)
    finish(db, attempt_vintage, failure, "http_error")
    success, capture, cutoff = complete(db, attempt_vintage)
    result = manifest(db, attempt_vintage, cutoff)
    assert result.capture_ids == (capture.capture_id,)
    assert result.attempt_ids == tuple(sorted((failure, success), key=str))
    assert result.failed_attempt_ids == result.flags == ()


def test_304_attempt_preserves_capture_identity_and_retrieval_time(db, attempt_vintage):
    success, capture, _ = complete(db, attempt_vintage)
    before = db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"]
    attempt = start(db, attempt_vintage, status=304, conditional=capture.capture_id)
    cutoff = finish(db, attempt_vintage, attempt, "not_modified", reused=capture.capture_id)
    result = manifest(db, attempt_vintage, cutoff)
    assert result.capture_ids == (capture.capture_id,)
    assert result.attempt_ids == tuple(sorted((attempt, success), key=str))
    assert result.failed_attempt_ids == result.flags == ()
    assert db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == before
    assert (
        db.execute(
            "SELECT fetched_at FROM source_captures WHERE id=%s", (capture.capture_id,)
        ).fetchone()["fetched_at"]
        == capture.fetched_at
    )


def test_terminal_outcome_after_cutoff_is_still_unknown_at_that_cutoff(db, attempt_vintage):
    attempt = start(db, attempt_vintage)
    cutoff = db.execute(
        "SELECT headers_received_at FROM source_fetch_attempts WHERE id=%s", (attempt,)
    ).fetchone()["headers_received_at"]
    finish(db, attempt_vintage, attempt, "http_error")
    result = manifest(db, attempt_vintage, cutoff)
    assert result.attempt_ids == (attempt,)
    assert result.failed_attempt_ids == ()
    assert "source_attempt_outcome_unknown" in result.flags
    assert "newer_capture_failed" not in result.flags


def test_prepared_attempt_is_unknown_without_invented_completion(db, attempt_vintage):
    _, _, lease, stage, resource = attempt_vintage
    attempt = prepare_attempt(db, lease, stage, resource)
    before = db.execute(
        "SELECT prepared_at,finished_at FROM source_fetch_attempts WHERE id=%s", (attempt,)
    ).fetchone()
    result = manifest(db, attempt_vintage, datetime.now(UTC))
    assert result.attempt_ids == (attempt,)
    assert result.failed_attempt_ids == ()
    assert "source_attempt_outcome_unknown" in result.flags
    assert (
        db.execute(
            "SELECT prepared_at,finished_at FROM source_fetch_attempts WHERE id=%s", (attempt,)
        ).fetchone()
        == before
    )
    assert (
        manifest(db, attempt_vintage, before["prepared_at"] - timedelta(microseconds=1)).attempt_ids
        == ()
    )


def test_interrupted_unknown_is_not_mislabeled_as_http_failure(db, attempt_vintage):
    attempt = start(db, attempt_vintage, status=200)
    cancel_request(db, request_id=attempt_vintage[1].request_id)
    assert recover_interrupted_attempt(db, attempt)
    result = manifest(db, attempt_vintage, datetime.now(UTC))
    assert result.attempt_ids == (attempt,)
    assert result.failed_attempt_ids == ()
    assert "source_attempt_outcome_unknown" in result.flags
    assert "newer_capture_failed" not in result.flags


def test_attempt_and_capture_reads_share_one_snapshot(db_admin, db, attempt_vintage):
    cutoff = datetime.now(UTC) + timedelta(hours=1)
    injected = []

    class ConcurrentInsert:
        info = db.info

        def transaction(self):
            return db.transaction()

        def execute(self, query, params=None):
            cursor = db.execute(query, params)
            if "SELECT c.* FROM source_captures" in query and not injected:
                attempt = start(db_admin, attempt_vintage)
                finish(db_admin, attempt_vintage, attempt, "http_error")
                injected.append(attempt)
            return cursor

    result = manifest(ConcurrentInsert(), attempt_vintage, cutoff)
    assert injected
    assert result.attempt_ids == result.failed_attempt_ids == ()
    assert not result.flags
    later = manifest(db, attempt_vintage, cutoff)
    assert later.attempt_ids == later.failed_attempt_ids == tuple(injected)


def test_successful_304_clears_prior_failure_without_refreshing_body(db, attempt_vintage):
    _, capture, _ = complete(db, attempt_vintage)
    failure = start(db, attempt_vintage)
    finish(db, attempt_vintage, failure, "http_error")
    revalidation = start(db, attempt_vintage, status=304, conditional=capture.capture_id)
    cutoff = finish(db, attempt_vintage, revalidation, "not_modified", reused=capture.capture_id)
    result = manifest(db, attempt_vintage, cutoff)
    assert result.capture_ids == (capture.capture_id,)
    assert failure in result.attempt_ids
    assert result.failed_attempt_ids == result.flags == ()
    assert (
        db.execute(
            "SELECT fetched_at FROM source_captures WHERE id=%s", (capture.capture_id,)
        ).fetchone()["fetched_at"]
        == capture.fetched_at
    )
