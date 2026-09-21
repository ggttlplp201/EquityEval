"""Real empty/populated PostgreSQL bootstrap contracts; fictional HTTP only."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import httpx
import psycopg
import pytest
from alembic import command
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import FetchRequest, ResourceKind, SecResource, SourceDescriptor
from equity_ingest.limiter import RedisRateLimiter
from equity_ingest.pipeline import SourcePlan, run_source_bootstrap, run_source_stages
from equity_ingest.sec import SecSource
from equity_ingest.transport import DatabaseAttemptStore, SecTransport
from equity_schema.bootstrap import BootstrapPlan
from equity_schema.workflow import (
    LeaseLost,
    cancel_request,
    claim_next,
    claim_source_bootstrap,
    create_workspace_watchlist,
    enqueue_source_bootstrap,
    finish_execution,
    renew_lease,
    rerun_analysis,
    retry_execution,
    start_stage,
)
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from tests.conftest import migration_config, test_database_profile
from tests.evidence_seed import insert, seed_evidence

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        test_database_profile() != "timescale-pg16",
        reason="Bootstrap is migration 0006 after Timescale 0005",
    ),
]


@pytest.fixture
def identity(db_admin, db):
    issuer, security = uuid4(), uuid4()
    insert(
        db_admin,
        "issuers",
        id=issuer,
        cik="0001876042",
        legal_name="Fictional bootstrap issuer",
        first_seen_at=datetime.now(UTC),
    )
    insert(
        db_admin,
        "securities",
        id=security,
        issuer_id=issuer,
        instrument_kind="common_stock",
        share_class_label="Fictional class",
    )
    workspace = create_workspace_watchlist(db, name="Bootstrap fixture")
    source_id, policy_id = uuid4(), uuid4()
    insert(
        db_admin,
        "sources",
        id=source_id,
        source_key="bootstrap-test",
        name="Fictional SEC policy",
        base_url="https://data.sec.gov",
        terms_review_reference="bootstrap-test",
        content_scope="Fictional tests",
    )
    insert(
        db_admin,
        "source_policy_revisions",
        id=policy_id,
        source_id=source_id,
        review_key="bootstrap-test",
        licence_label="Fictional test policy",
        content_scope="Fictional tests",
        redistribution_status="unknown",
        permitted_use="Tests only",
        attribution_requirements="Fixture",
        terms_urls=["https://example.invalid"],
        reviewed_at=datetime.now(UTC),
        reviewed_by="fixture",
        review_artifact_reference="tests/integration/test_source_bootstrap.py",
        review_artifact_sha256="a" * 64,
    )
    return workspace, issuer, security


def bootstrap_plan(db, identity):
    row = db.execute(
        "SELECT source_id,id FROM source_policy_revisions WHERE review_key='bootstrap-test'"
    ).fetchone()
    return BootstrapPlan(
        identity[1],
        "0001876042",
        row["source_id"],
        row["id"],
        date(2025, 1, 1),
        date(2026, 9, 21),
        ("company_facts/0001876042", "submissions/0001876042"),
    )


def enqueue(db, identity, key="bootstrap", **kwargs):
    workspace, _, security = identity
    return enqueue_source_bootstrap(
        db,
        workspace_id=workspace.workspace_id,
        security_id=security,
        idempotency_key=key,
        plan=kwargs.pop("plan", bootstrap_plan(db, identity)),
        **kwargs,
    )


def test_empty_db_bootstrap_and_separate_claiming(db_admin, db, identity):
    assert db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == 0
    request = enqueue(db, identity)
    row = db.execute(
        "SELECT * FROM analysis_requests WHERE id=%s", (request.request_id,)
    ).fetchone()
    assert row["quote_identifier_id"] is None and row["trigger"] == "source_bootstrap"
    assert request.membership_id is None and request.generation is None
    assert claim_next(db, worker_id="ordinary") is None
    lease = claim_source_bootstrap(db, worker_id="bootstrap")
    assert lease.request_id == request.request_id
    evidence = seed_evidence(db_admin)
    ordinary = rerun_analysis(
        db,
        workspace_id=identity[0].workspace_id,
        security_id=evidence["security"],
        quote_identifier_id=evidence["quote"],
        idempotency_key="normal",
    )
    assert claim_source_bootstrap(db, worker_id="wrong") is None
    assert claim_next(db, worker_id="ordinary").request_id == ordinary.request_id
    assert db.execute("SELECT count(*) AS n FROM watchlist_memberships").fetchone()["n"] == 0


def test_concurrent_idempotency_and_changed_parameters(db_admin, db, identity):
    def perform(_):
        with psycopg.connect(db_admin.info.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            return enqueue(conn, identity)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(perform, range(4)))
    assert len({r.request_id for r in results}) == 1
    assert db.execute("SELECT count(*) AS n FROM analysis_executions").fetchone()["n"] == 1
    with pytest.raises(psycopg.errors.InvalidParameterValue, match="different parameters"):
        enqueue(
            db,
            identity,
            plan=replace(bootstrap_plan(db, identity), inventory_start=date(2025, 1, 2)),
        )
    assert enqueue(db, identity) == results[0]


@pytest.mark.parametrize(
    "field", ["quote_identifier_id", "membership_id", "parent_request_id", "market_plan", "unknown"]
)
def test_bootstrap_rejects_extra_fields_even_null(db, identity, field):
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        db.execute(
            "SELECT workflow_enqueue_bootstrap(%s,%s,%s,%s)",
            (identity[0].workspace_id, identity[2], field, Jsonb({field: None})),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("quote_identifier_id", "gen_random_uuid()"),
        ("membership_id", "gen_random_uuid()"),
        ("parent_request_id", "gen_random_uuid()"),
        ("macro_series_keys", "ARRAY[]::text[]"),
        ("market_plan_revision", "'s4-market-data-v1'"),
    ],
)
def test_owner_insert_cannot_bypass_bootstrap_shape(db_admin, db, identity, field, value):
    request = enqueue(db, identity)
    # Clone a valid row, changing only a prohibited identity/market field.
    columns = [
        r["column_name"]
        for r in db_admin.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='analysis_requests' ORDER BY ordinal_position"
        )
    ]
    expressions = [
        "gen_random_uuid()"
        if c == "id"
        else "'invalid'"
        if c == "idempotency_key"
        else "nextval('workflow_request_sequence')"
        if c == "request_sequence"
        else value
        if c == field
        else c
        for c in columns
    ]
    with pytest.raises((psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation)):
        db_admin.execute(
            f"INSERT INTO analysis_requests ({','.join(columns)}) "
            f"SELECT {','.join(expressions)} FROM analysis_requests WHERE id=%s",
            (request.request_id,),
        )


def test_ordinary_null_quote_and_bootstrap_trigger_are_rejected(db, identity):
    for trigger in ("manual_refresh", "watchlist_add", "source_bootstrap"):
        with pytest.raises(psycopg.Error):
            db.execute(
                "SELECT workflow_enqueue(%s,%s,%s,NULL,%s,'{}',%s,NULL)",
                (
                    None if trigger == "watchlist_add" else identity[0].workspace_id,
                    identity[0].watchlist_id if trigger == "watchlist_add" else None,
                    identity[2],
                    trigger,
                    trigger,
                ),
            )


def test_bootstrap_retry_expiry_cancel_and_stage_fences(db_admin, db, identity):
    request = enqueue(db, identity)
    first = claim_source_bootstrap(db, worker_id="first")
    renewed = renew_lease(db, first, lease_seconds=120)
    assert renewed.expires_at > first.expires_at
    for key in ("sec_normalization", "price_normalization", "valuation", "macro_normalization_a"):
        with pytest.raises(psycopg.errors.CheckViolation, match="SEC capture"):
            start_stage(db, renewed, stage_key=key)
    db_admin.execute(
        "UPDATE analysis_executions SET lease_expires_at=clock_timestamp()-interval '1 second' "
        "WHERE id=%s",
        (first.execution_id,),
    )
    assert claim_next(db, worker_id="ordinary") is None
    with pytest.raises(LeaseLost):
        start_stage(db, first, stage_key="sec_inventory")
    second = claim_source_bootstrap(db, worker_id="second")
    assert second.execution_id != first.execution_id and second.epoch > first.epoch
    retry_execution(db, second, error_code="retry_fixture", delay_seconds=0)
    third = claim_source_bootstrap(db, worker_id="third")
    assert third.request_id == request.request_id
    with pytest.raises(LeaseLost):
        finish_execution(db, second)
    assert cancel_request(db, request_id=request.request_id)
    with pytest.raises(LeaseLost):
        renew_lease(db, third)
    assert claim_source_bootstrap(db, worker_id="fourth") is None
    assert (
        db.execute(
            "SELECT count(*) AS n FROM execution_events WHERE event_kind='cancelled'"
        ).fetchone()["n"]
        == 1
    )


@pytest.fixture
def transport(db_admin, db, identity, redis_url, tmp_path):
    row = db.execute(
        "SELECT source_id,id FROM source_policy_revisions WHERE review_key='bootstrap-test'"
    ).fetchone()
    source_id, policy_id = row["source_id"], row["id"]
    descriptor = SourceDescriptor(
        source_id,
        "bootstrap-test",
        "Fictional test source",
        policy_id,
        "bootstrap-test",
        "Fictional test policy",
        "unknown",
        tuple(ResourceKind),
        timedelta(minutes=15),
        limiter_key="test:" + uuid4().hex,
    )
    archive = LocalArchive(tmp_path)
    calls = []

    def handler(request):
        calls.append(request)
        body = (
            {"cik": 1876042, "facts": {}}
            if "/companyfacts/" in str(request.url)
            else {
                "cik": 1876042,
                "filings": {
                    "recent": {"accessionNumber": [], "filingDate": [], "form": []},
                    "files": [],
                },
            }
        )
        return httpx.Response(
            200,
            stream=httpx.ByteStream(json.dumps(body).encode()),
            headers={"Content-Type": "application/json"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        limiter = RedisRateLimiter.from_url(redis_url, key=descriptor.limiter_key)
        source = SecSource(
            descriptor,
            SecTransport(
                descriptor,
                archive,
                limiter,
                DatabaseAttemptStore(db, descriptor),
                client,
                "test@example.invalid",
            ),
            archive,
        )
        yield source, archive, calls
        limiter.client.close()


def test_genuine_workflow_transport_captures_but_never_normalizes(
    db, identity, transport, monkeypatch
):
    source, archive, calls = transport
    request = enqueue(db, identity)
    lease = claim_source_bootstrap(db, worker_id="bootstrap")
    plan = bootstrap_plan(db, identity)

    def forbidden(*args):
        raise AssertionError("Bootstrap must never normalize or build financial inputs")

    monkeypatch.setattr(source, "normalize", forbidden)
    with pytest.raises(ValueError, match="trigger"):
        run_source_stages(
            db,
            lease,
            source,
            archive,
            SourcePlan(plan.issuer_id, plan.cik, plan.inventory_start, plan.inventory_end),
            forbidden,
        )
    assert not calls
    result = run_source_bootstrap(db, lease, source, archive, plan)
    assert result.publication is None and result.manifest is not None
    manifest = json.loads(archive.read(result.manifest))
    assert manifest["request"]["quote_identifier_id"] is None
    assert manifest["request"]["id"] == str(request.request_id)
    assert manifest["financial_result"] is False and manifest["event_review"] == "not_performed"
    assert len(calls) == 2
    for record in source.records:
        assert record.requested_at <= record.fetched_at <= record.completed_at
        source.read_verified(record.capture_id)
        row = db.execute(
            "SELECT a.*,l.policy_revision_id FROM source_fetch_attempts a "
            "JOIN capture_policy_links l ON l.capture_id=a.completed_capture_id "
            "WHERE a.completed_capture_id=%s",
            (record.capture_id,),
        ).fetchone()
        assert row["state"] == "complete" and row["requested_at"] == record.requested_at
        assert (
            row["finished_at"] == record.completed_at
            and row["policy_revision_id"] == source.descriptor.policy_revision_id
        )
    for table in ("normalization_batches", "watchlist_memberships", "security_identifiers"):
        assert db.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] == 0


def test_bootstrap_transport_rejects_other_issuer_and_stale_worker(
    db_admin, db, identity, transport
):
    source, _, calls = transport
    request = enqueue(db, identity)
    lease = claim_source_bootstrap(db, worker_id="bootstrap")
    stage = start_stage(db, lease, stage_key="sec_fetch_" + "a" * 24)
    with pytest.raises(psycopg.errors.CheckViolation, match="registered issuer"):
        source.fetch(
            FetchRequest(
                uuid4(),
                SecResource(identity[1], "320193", ResourceKind.COMPANY_FACTS),
                lease,
                stage,
            )
        )
    assert not calls
    cancel_request(db, request_id=request.request_id)
    result = source.fetch(
        FetchRequest(
            uuid4(), SecResource(identity[1], "1876042", ResourceKind.COMPANY_FACTS), lease, stage
        )
    )
    assert result.gaps == ("lease_lost",)
    assert not calls


def test_populated_upgrade_preserves_ordinary_requests(db_admin, db, test_database_dsn):
    config = migration_config(test_database_dsn)
    command.downgrade(config, "0005_market_data_hypertables")
    evidence = seed_evidence(db_admin)
    workspace = create_workspace_watchlist(db, name="Existing ordinary request")
    request = rerun_analysis(
        db,
        workspace_id=workspace.workspace_id,
        security_id=evidence["security"],
        quote_identifier_id=evidence["quote"],
        idempotency_key="existing",
    )
    before = db.execute(
        "SELECT * FROM analysis_requests WHERE id=%s", (request.request_id,)
    ).fetchone()
    command.upgrade(config, "head")
    assert db.execute(
        "SELECT * FROM analysis_requests WHERE id=%s", (request.request_id,)
    ).fetchone() == {**before, "bootstrap_plan": None}
    assert claim_next(db, worker_id="ordinary").request_id == request.request_id


def test_downgrade_refuses_to_erase_bootstrap_history(db, identity, test_database_dsn):
    enqueue(db, identity)
    with pytest.raises(Exception, match="refusing to discard pinned bootstrap"):
        command.downgrade(migration_config(test_database_dsn), "0005_market_data_hypertables")


def test_specific_claim_does_not_take_another_request(db, identity):
    first = enqueue(db, identity, key="first")
    second = enqueue(db, identity, key="second")
    lease = claim_source_bootstrap(db, worker_id="second", request_id=second.request_id)
    assert lease.request_id == second.request_id
    assert claim_source_bootstrap(db, worker_id="ordinary-bootstrap").request_id == first.request_id


def test_bootstrap_rejected_by_combined_and_market_workers(db, identity, transport):
    from equity_ingest.analysis_pipeline import run_analysis_stages
    from equity_ingest.market_pipeline import MarketReview, run_market_stages

    source, archive, calls = transport
    enqueue(db, identity)
    lease = claim_source_bootstrap(db, worker_id="bootstrap")
    plan = bootstrap_plan(db, identity)
    with pytest.raises(ValueError, match="ordinary"):
        run_analysis_stages(db, lease, source, archive, plan, lambda _: None, {}, MarketReview())
    with pytest.raises(ValueError, match="cannot enter market"):
        run_market_stages(db, lease, archive, {}, MarketReview())
    assert not calls
    assert db.execute("SELECT count(*) AS n FROM analysis_stage_attempts").fetchone()["n"] == 0


def test_http_failure_preserves_real_attempt_and_null_quote_manifest(db, identity, transport):
    source, archive, _ = transport
    source.transport.client.close()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(404, stream=httpx.ByteStream(b"fixture not found"))
        )
    ) as client:
        source.transport.client = client
        enqueue(db, identity)
        lease = claim_source_bootstrap(db, worker_id="bootstrap")
        result = run_source_bootstrap(
            db,
            lease,
            source,
            archive,
            bootstrap_plan(db, identity),
        )
    assert result.state == "completed_with_gaps" and result.publication is None
    assert (
        result.gaps
        and json.loads(archive.read(result.manifest))["request"]["quote_identifier_id"] is None
    )
    rows = db.execute(
        "SELECT state,http_status,completed_capture_id FROM source_fetch_attempts"
    ).fetchall()
    assert len(rows) == 2 and all(
        r["state"] == "http_error" and r["http_status"] == 404 for r in rows
    )
    assert all(r["completed_capture_id"] for r in rows)


def test_owner_registration_is_idempotent_without_synthetic_evidence(db_admin, db, tmp_path):
    from scripts.bootstrap_crcl import IDENTITY_PATH, POLICY_PATH, ROOT, register, registered

    ids = register(db_admin)
    assert register(db_admin) == ids and registered(db) == ids
    for table in (
        "security_identifiers",
        "source_captures",
        "normalization_batches",
        "analysis_requests",
    ):
        assert db.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] == 0
    for name in (IDENTITY_PATH, POLICY_PATH):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / name).read_bytes())
    (tmp_path / POLICY_PATH).write_text("changed review")
    with pytest.raises(ValueError, match="differs"):
        register(db_admin, tmp_path)
    assert registered(db) == ids


def test_cancelled_bootstrap_cannot_finalize_dispatched_attempt(db, identity, transport):
    from equity_schema.ingestion import recover_interrupted_attempt

    source, _, calls = transport
    request = enqueue(db, identity)
    lease = claim_source_bootstrap(db, worker_id="bootstrap")
    stage = start_stage(db, lease, stage_key="sec_fetch_" + "b" * 24)
    fetch = FetchRequest(
        uuid4(), SecResource(identity[1], "1876042", ResourceKind.COMPANY_FACTS), lease, stage
    )
    store = source.transport.attempts
    attempt = store.prepare(fetch, 1, fetch.resource.url, None)
    store.dispatched(fetch, attempt, datetime.now(UTC))
    cancel_request(db, request_id=request.request_id)
    with pytest.raises(LeaseLost):
        store.finish(fetch, attempt, "transport_error", datetime.now(UTC), failure="test_error")
    assert recover_interrupted_attempt(db, attempt)
    row = db.execute(
        "SELECT state,completed_capture_id FROM source_fetch_attempts WHERE id=%s", (attempt,)
    ).fetchone()
    assert row == {"state": "interrupted_unknown", "completed_capture_id": None}
    assert not calls


def test_retry_exhaustion_retains_bootstrap_manifest(db, identity, transport):
    source, archive, _ = transport

    def unavailable(request):
        raise httpx.ConnectError("fixture unavailable", request=request)

    source.transport.client.close()
    with httpx.Client(transport=httpx.MockTransport(unavailable)) as client:
        source.transport.client = client
        source.transport.sleep = lambda _: None
        enqueue(db, identity, max_attempts=1)
        lease = claim_source_bootstrap(db, worker_id="bootstrap")
        result = run_source_bootstrap(
            db,
            lease,
            source,
            archive,
            bootstrap_plan(db, identity),
        )
    assert result.state == "failed" and "retry_budget_exhausted" in result.gaps
    manifest = json.loads(archive.read(result.manifest))
    assert manifest["request"]["quote_identifier_id"] is None
    assert "companyfacts_unavailable" in manifest["source_gaps"]
    assert db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == 0


def test_plan_is_idempotent_immutable_and_runtime_mismatch_fails_before_dispatch(
    db_admin, db, identity, transport
):
    source, archive, calls = transport
    plan = bootstrap_plan(db, identity)
    request = enqueue(db, identity, plan=plan)
    assert (
        enqueue(db, identity, plan=replace(plan, resources=tuple(reversed(plan.resources))))
        == request
    )
    changed = replace(
        plan,
        resources=(
            *plan.resources,
            "filing_document/0001876042/0001876042-26-000062/crcl-20251231.htm",
        ),
    )
    with pytest.raises(psycopg.errors.InvalidParameterValue, match="different parameters"):
        enqueue(db, identity, plan=changed)
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="immutable"):
        db_admin.execute(
            "UPDATE analysis_requests SET bootstrap_plan=%s WHERE id=%s",
            (Jsonb(changed.as_json()), request.request_id),
        )
    lease = claim_source_bootstrap(db, worker_id="plan-check")
    with pytest.raises(ValueError, match="immutable request intent"):
        run_source_bootstrap(db, lease, source, archive, changed)
    assert not calls
    assert db.execute("SELECT count(*) AS n FROM analysis_stage_attempts").fetchone()["n"] == 0
    stage = start_stage(db, lease, stage_key="sec_fetch_" + "c" * 24)
    with pytest.raises(psycopg.errors.CheckViolation, match="outside pinned plan"):
        source.fetch(
            FetchRequest(
                uuid4(),
                SecResource(
                    identity[1],
                    "1876042",
                    ResourceKind.FILING_DOCUMENT,
                    accession="0001876042-26-000062",
                    filename="crcl-20251231.htm",
                ),
                lease,
                stage,
            )
        )
    assert not calls


def test_ready_result_is_persisted_and_completed_error_fields_are_null(db, identity, transport):
    source, archive, _ = transport
    enqueue(db, identity)
    lease = claim_source_bootstrap(db, worker_id="ready")
    result = run_source_bootstrap(db, lease, source, archive, bootstrap_plan(db, identity))
    assert result.state == "completed" and result.bootstrap_readiness.registration_review_ready
    readiness = result.bootstrap_readiness
    capture = next(c for c in source.records if c.source_object_key == "submissions/0001876042")
    assert (
        readiness.identity_capture_id == capture.capture_id
        and readiness.identity_status == "captured"
    )
    assert readiness.blocking_reasons == ()
    stages = db.execute(
        "SELECT * FROM analysis_stage_attempts WHERE execution_id=%s", (lease.execution_id,)
    ).fetchall()
    assert all(s["error_code"] is None and s["error_detail"] is None for s in stages)
    stage = next(s for s in stages if s["stage_key"] == "sec_bootstrap_manifest")
    stored = json.loads(stage["result_reference"])
    assert stored["version"] == "sec-bootstrap-result-v1"
    assert stored["readiness"]["identity_capture_id"] == str(capture.capture_id)
    assert stored["manifest"]["body_sha256"] == result.manifest.body_sha256
    assert stage["input_manifest"]["bootstrap_plan"] == bootstrap_plan(db, identity).as_json()
    execution = db.execute(
        "SELECT error_code,error_detail FROM analysis_executions WHERE id=%s", (lease.execution_id,)
    ).fetchone()
    assert execution == {"error_code": None, "error_detail": None}
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="lease lost"):
        db.execute(
            "SELECT workflow_finish_stage(%s,%s,'completed',NULL,'{}')",
            (Jsonb(lease.as_json()), stage["id"]),
        )


@pytest.mark.parametrize("submissions_status", [404, 200])
def test_absent_or_invalid_submissions_never_claims_registration_readiness(
    db, identity, transport, submissions_status
):
    source, archive, _ = transport

    def handler(request):
        if "/companyfacts/" in str(request.url):
            return httpx.Response(200, stream=httpx.ByteStream(b'{"cik":1876042,"facts":{}}'))
        return httpx.Response(submissions_status, stream=httpx.ByteStream(b"{}"))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source.transport.client = client
        enqueue(db, identity)
        lease = claim_source_bootstrap(db, worker_id="missing-identity")
        result = run_source_bootstrap(db, lease, source, archive, bootstrap_plan(db, identity))
    assert result.state == "completed_with_gaps"
    assert result.bootstrap_readiness.identity_capture_id is None
    assert result.bootstrap_readiness.identity_status == "unavailable"
    assert not result.bootstrap_readiness.registration_review_ready
    assert "identity_submissions_unavailable" in result.bootstrap_readiness.blocking_reasons
    stored = db.execute(
        "SELECT result_reference,error_code FROM analysis_stage_attempts "
        "WHERE execution_id=%s AND stage_key='sec_bootstrap_manifest'",
        (lease.execution_id,),
    ).fetchone()
    assert stored["error_code"] is None
    assert json.loads(stored["result_reference"])["readiness"]["registration_review_ready"] is False


def test_unplanned_advertised_history_is_a_gap_not_a_new_dispatch(db, identity, transport):
    source, archive, calls = transport

    def handler(request):
        calls.append(request)
        if "/companyfacts/" in str(request.url):
            body = {"cik": 1876042, "facts": {}}
        else:
            body = {
                "cik": 1876042,
                "filings": {
                    "recent": {"accessionNumber": [], "filingDate": [], "form": []},
                    "files": [
                        {
                            "name": "CIK0001876042-submissions-001.json",
                            "filingCount": 1,
                            "filingFrom": "2025-01-01",
                            "filingTo": "2025-02-01",
                        }
                    ],
                },
            }
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(body).encode()))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source.transport.client = client
        enqueue(db, identity)
        lease = claim_source_bootstrap(db, worker_id="bounded")
        result = run_source_bootstrap(db, lease, source, archive, bootstrap_plan(db, identity))
    assert len(calls) == 2
    assert "unplanned_advertised_history" in result.gaps
    assert not result.bootstrap_readiness.registration_review_ready


def test_typed_completion_rejects_missing_identity_and_stale_worker(db, identity):
    from equity_schema.workflow import complete_bootstrap_stage

    request = enqueue(db, identity)
    lease = claim_source_bootstrap(db, worker_id="fenced-result")
    stage = start_stage(db, lease, stage_key="sec_bootstrap_manifest")
    invalid = {
        "version": "sec-bootstrap-result-v1",
        "manifest": {"blob_key": "bootstrap/test.gz", "body_sha256": "a" * 64, "byte_count": 1},
        "readiness": {
            "identity_capture_id": None,
            "identity_status": "unavailable",
            "registration_review_ready": True,
            "blocking_reasons": [],
        },
    }
    with pytest.raises(
        psycopg.errors.InvalidParameterValue, match="inconsistent bootstrap readiness"
    ):
        complete_bootstrap_stage(db, lease, stage_id=stage, result=invalid)
    cancel_request(db, request_id=request.request_id)
    with pytest.raises(LeaseLost):
        complete_bootstrap_stage(db, lease, stage_id=stage, result=invalid)


def test_populated_0006_upgrade_keeps_legacy_request_without_invented_plan(
    db_admin, db, identity, test_database_dsn
):
    config = migration_config(test_database_dsn)
    command.downgrade(config, "0006_source_bootstrap")
    old = db.execute(
        "SELECT workflow_enqueue_bootstrap(%s,%s,%s,'{}') AS r",
        (identity[0].workspace_id, identity[2], "legacy"),
    ).fetchone()["r"]
    lease = claim_source_bootstrap(db, worker_id="old")
    finish_execution(db, lease, reason="source_bootstrap_capture_only")
    before = db.execute(
        "SELECT * FROM analysis_requests WHERE id=%s", (old["request_id"],)
    ).fetchone()
    command.upgrade(config, "head")
    after = db.execute(
        "SELECT * FROM analysis_requests WHERE id=%s", (old["request_id"],)
    ).fetchone()
    assert after == {**before, "bootstrap_plan": None}
    assert (
        db.execute(
            "SELECT error_code FROM analysis_executions WHERE id=%s", (lease.execution_id,)
        ).fetchone()["error_code"]
        == "source_bootstrap_capture_only"
    )
    assert enqueue(db, identity, key="new").request_id != lease.request_id


def test_new_bootstrap_success_cannot_bypass_typed_completion(db, identity):
    enqueue(db, identity)
    lease = claim_source_bootstrap(db, worker_id="guarded-success")
    with pytest.raises(psycopg.errors.CheckViolation, match="typed acquisition result"):
        finish_execution(db, lease)
    stage = start_stage(db, lease, stage_key="sec_bootstrap_manifest")
    from equity_schema.workflow import finish_stage

    with pytest.raises(psycopg.errors.CheckViolation, match="typed result reference"):
        finish_stage(db, lease, stage_id=stage, outcome="completed")
    with pytest.raises(psycopg.errors.CheckViolation, match="cannot carry error fields"):
        finish_stage(db, lease, stage_id=stage, outcome="completed", reason="success metadata")


@pytest.mark.parametrize(
    "changes",
    [
        {"inventory_end": "2030-01-01"},
        {"resources": ["company_facts/0001876042"]},
        {"version": "unknown"},
        {"financial_periods": []},
    ],
)
def test_database_rejects_unbounded_or_unreviewed_plan(db, identity, changes):
    options = {"plan": {**bootstrap_plan(db, identity).as_json(), **changes}, "max_attempts": 3}
    with pytest.raises(psycopg.errors.InvalidParameterValue, match="invalid acquisition plan"):
        db.execute(
            "SELECT workflow_enqueue_bootstrap(%s,%s,%s,%s)",
            (identity[0].workspace_id, identity[2], "invalid-plan", Jsonb(options)),
        )


def test_pinned_plan_checks_policy_before_runtime_fetch(db, identity, transport):
    source, archive, calls = transport
    plan = bootstrap_plan(db, identity)
    enqueue(db, identity, plan=plan)
    lease = claim_source_bootstrap(db, worker_id="wrong-policy")
    source.descriptor = replace(source.descriptor, policy_revision_id=uuid4())
    with pytest.raises(ValueError, match="immutable request intent"):
        run_source_bootstrap(db, lease, source, archive, plan)
    assert not calls
