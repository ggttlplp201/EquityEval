"""D035 governed monitor integration; fictional HTTP and isolated PG16/Redis only."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest
from equity_ingest.monitor_pipeline import load_record, run_filing_monitor
from equity_ingest.pipeline import run_source_bootstrap
from equity_schema.filing_monitor import FORMS, FilingMonitorPlan, MonitorBaseline
from equity_schema.workflow import (
    claim_filing_monitor,
    claim_next,
    claim_source_bootstrap,
    enqueue_filing_monitor,
    finish_execution,
    finish_stage,
    start_stage,
)
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from tests.conftest import test_database_profile
from tests.evidence_seed import insert
from tests.integration import test_source_bootstrap as bootstrap_fixtures
from tests.integration.test_source_bootstrap import (
    bootstrap_plan,
    enqueue,
)
from tests.test_filing_monitor import filing, submissions
from tests.test_ingest_transport import Clock, Limiter

# Pin fictional acceptance metadata independently of the host calendar.
MONITOR_CUTOFF = datetime(2026, 9, 21, 12, tzinfo=UTC)

identity = bootstrap_fixtures.identity
transport = bootstrap_fixtures.transport
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        test_database_profile() != "timescale-pg16",
        reason="D035 monitor requires migration 0008",
    ),
]


@pytest.fixture
def seeded(db_admin, db, identity, transport):
    source, archive, calls = transport
    request = enqueue(db, identity)
    lease = claim_source_bootstrap(db, worker_id="seed")
    bootstrap = bootstrap_plan(db, identity)
    # Seed setup is not a rate-limit test: a wall-clock permit expiring under
    # CI load must not silently construct an ineligible comparison baseline.
    # Restore the real shared limiter for every monitor operation below.
    with pytest.MonkeyPatch.context() as setup:
        setup.setattr(source.transport, "limiter", Limiter(Clock()))
        result = run_source_bootstrap(db, lease, source, archive, bootstrap)
    assert (
        db.execute(
            "SELECT terminal_outcome FROM analysis_request_state WHERE request_id=%s",
            (request.request_id,),
        ).fetchone()["terminal_outcome"]
        == "completed"
    )
    capture = next(r for r in source.records if r.source_object_key.startswith("submissions/"))
    seed_id = uuid4()
    request_hash = db.execute(
        "SELECT request_parameters_hash FROM analysis_requests WHERE id=%s", (request.request_id,)
    ).fetchone()["request_parameters_hash"]
    plan = FilingMonitorPlan(
        bootstrap.issuer_id,
        bootstrap.cik,
        bootstrap.source_id,
        bootstrap.policy_revision_id,
        bootstrap.inventory_start,
        bootstrap.inventory_end,
        MONITOR_CUTOFF,
        tuple(FORMS),
        (capture.source_object_key,),
        MonitorBaseline(
            "initial_seed",
            request.request_id,
            lease.execution_id,
            result.manifest.body_sha256,
            MONITOR_CUTOFF - timedelta(hours=12),
            seed_approval_id=seed_id,
            plan_sha256=request_hash,
            capture_id=capture.capture_id,
        ),
    )
    scope = {
        k: v for k, v in plan.as_json().items() if k not in ("baseline", "cutoff", "resources")
    }
    insert(
        db_admin,
        "filing_monitor_seed_approvals",
        id=seed_id,
        security_id=identity[2],
        request_id=request.request_id,
        execution_id=lease.execution_id,
        request_parameters_hash=request_hash,
        manifest_sha256=result.manifest.body_sha256,
        capture_id=capture.capture_id,
        cutoff=plan.baseline.cutoff,
        scope=Jsonb(scope),
        review_reference="D035 fictional test seed",
        review_sha256="a" * 64,
    )
    return plan, source, archive, calls


def monitor_request(db, identity, plan, key="poll"):
    return enqueue_filing_monitor(
        db,
        workspace_id=identity[0].workspace_id,
        security_id=identity[2],
        idempotency_key=key,
        plan=plan,
    )


def run(db, identity, seeded, monkeypatch, body=None, status=200, key="poll", headers=None):
    plan, source, archive, _ = seeded
    request = monitor_request(db, identity, plan, key)
    lease = claim_filing_monitor(db, worker_id="monitor", request_id=request.request_id)
    calls = []
    if body is None:
        record = load_record(db, plan.baseline.capture_id)
        body = archive.read_blob(record.blob_key, record.body_sha256, record.byte_count)
    if isinstance(body, dict):
        body = json.dumps(body).encode()

    def handler(req):
        calls.append(req)
        return httpx.Response(status, stream=httpx.ByteStream(body), headers=headers or {})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source.transport, "client", client)
        result = run_filing_monitor(db, lease, source, archive, plan)
    return request, lease, result, calls


def test_identical_200_archives_attempt_and_reuses_capture(db, identity, seeded, monkeypatch):
    request, lease, result, calls = run(db, identity, seeded, monkeypatch)
    assert result["outcome"] == "no_change" and result["baseline_eligible"]
    assert len(calls) == 1
    assert result["baseline_capture_ids"] == result["current_capture_ids"]
    row = db.execute(
        "SELECT a.*,p.blob_key AS new_blob,p.body_sha256,p.byte_count FROM "
        "source_fetch_attempts a JOIN source_attempt_payloads p ON p.attempt_id=a.id"
    ).fetchone()
    assert row["state"] == "content_unchanged" and row["http_status"] == 200
    old = load_record(db, row["reused_capture_id"])
    assert row["new_blob"] != old.blob_key
    assert seeded[2].read_blob(row["new_blob"], row["body_sha256"], row["byte_count"]) == seeded[
        2
    ].read_blob(old.blob_key, old.body_sha256, old.byte_count)
    assert datetime.fromisoformat(result["checked_at"]) == row["finished_at"] > old.completed_at
    assert monitor_request(db, identity, seeded[0]).request_id == request.request_id
    assert claim_filing_monitor(db, worker_id="again", request_id=request.request_id) is None
    assert result["downstream"]["dispatched"] is False
    for table in ("security_identifiers", "watchlist_memberships", "normalization_batches"):
        assert db.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] == 0
    assert db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == 2


@pytest.mark.parametrize(
    "rows,outcome",
    [
        ([filing()], "new_filing"),
        ([filing(form="10-Q/A")], "amendment"),
        ([filing(), filing(2, form="10-K/A")], "mixed_changes"),
        ([filing(form="8-K")], "no_change"),
        ([filing(acceptanceDateTime="")], "incomplete"),
    ],
)
def test_new_changed_and_out_of_scope_bodies(db, identity, seeded, monkeypatch, rows, outcome):
    _, _, result, calls = run(db, identity, seeded, monkeypatch, submissions(rows))
    assert result["outcome"] == outcome and len(calls) == 1
    assert result["current_capture_ids"] != result["baseline_capture_ids"]
    assert db.execute("SELECT count(*) AS n FROM source_attempt_payloads").fetchone()["n"] == 1


def test_prior_result_exact_lineage_and_capture_reuse(db, identity, seeded, monkeypatch):
    request, lease, result, _ = run(db, identity, seeded, monkeypatch, submissions([filing()]))
    plan = replace(
        seeded[0],
        cutoff=MONITOR_CUTOFF,
        baseline=MonitorBaseline(
            "prior_monitor_result",
            request.request_id,
            lease.execution_id,
            result["manifest"]["body_sha256"],
            seeded[0].cutoff,
            manifest_id=UUID(result["manifest_id"]),
        ),
    )
    _, _, second, _ = run(
        db, identity, (plan, *seeded[1:]), monkeypatch, submissions([filing()]), key="second"
    )
    assert second["outcome"] == "no_change"
    assert (
        second["baseline_capture_ids"]
        == result["current_capture_ids"]
        == second["current_capture_ids"]
    )
    for change in (
        {"forms": ("10-Q",)},
        {"inventory_start": plan.inventory_start + timedelta(days=1)},
    ):
        with pytest.raises(psycopg.errors.CheckViolation, match="rebase"):
            monitor_request(db, identity, replace(plan, **change), key="invalid")
    with pytest.raises(psycopg.errors.CheckViolation):
        monitor_request(
            db,
            identity,
            replace(plan, baseline=replace(plan.baseline, manifest_sha256="0" * 64)),
            key="invalid-hash",
        )


@pytest.mark.parametrize(
    "overlap,count,expected",
    [(False, 1, "no_change"), (True, 1, "incomplete"), (True, 11, "incomplete")],
)
def test_advertised_history_requires_only_overlap_and_never_truncates(
    db, identity, seeded, monkeypatch, overlap, count, expected
):
    history = [
        {
            "name": f"CIK0001876042-submissions-{i:03d}.json",
            "filingCount": 1,
            "filingFrom": "2025-01-01" if overlap else "2020-01-01",
            "filingTo": "2025-12-31" if overlap else "2020-12-31",
        }
        for i in range(1, count + 1)
    ]
    _, _, result, calls = run(db, identity, seeded, monkeypatch, submissions(history=history))
    assert result["outcome"] == expected and len(calls) == 1
    if count > 10:
        assert "history_limit_exceeded" in result["comparison"]["flags"]
    if not overlap:
        assert result["history"]["current"]["excluded_nonoverlap"]


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        json.dumps(submissions(history=[{"name": "CIK0001876042-submissions-001.json"}])).encode(),
    ],
)
def test_malformed_archive_remains_auditable_incomplete(db, identity, seeded, monkeypatch, body):
    _, _, result, _ = run(db, identity, seeded, monkeypatch, body)
    assert result["outcome"] == "incomplete" and not result["baseline_eligible"]
    assert db.execute("SELECT count(*) AS n FROM source_attempt_payloads").fetchone()["n"] == 1


def test_http_error_is_distinct_and_cannot_seed_next(db, identity, seeded, monkeypatch):
    request, lease, result, _ = run(db, identity, seeded, monkeypatch, b"not found", status=404)
    assert result["outcome"] == "error" and not result["baseline_eligible"]
    plan = replace(
        seeded[0],
        baseline=MonitorBaseline(
            "prior_monitor_result",
            request.request_id,
            lease.execution_id,
            result["manifest"]["body_sha256"],
            seeded[0].cutoff,
            manifest_id=UUID(result["manifest_id"]),
        ),
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="terminal complete"):
        monitor_request(db, identity, plan, key="invalid-error-baseline")


def test_separate_claims_and_concurrent_idempotency(db_admin, db, identity, seeded):
    def enqueue_one(_):
        with psycopg.connect(db_admin.info.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            return monitor_request(conn, identity, seeded[0])

    with ThreadPoolExecutor(max_workers=3) as pool:
        requests = list(pool.map(enqueue_one, range(3)))
    assert len({r.request_id for r in requests}) == 1
    assert claim_next(db, worker_id="wrong") is None
    assert claim_source_bootstrap(db, worker_id="wrong") is None
    assert claim_filing_monitor(db, worker_id="right") is not None
    assert claim_filing_monitor(db, worker_id="duplicate") is None
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        monitor_request(
            db, identity, replace(seeded[0], cutoff=seeded[0].cutoff + timedelta(microseconds=1))
        )


def test_generic_completion_and_financial_stage_are_fenced(db, identity, seeded):
    monitor_request(db, identity, seeded[0])
    lease = claim_filing_monitor(db, worker_id="monitor")
    with pytest.raises(psycopg.errors.CheckViolation):
        start_stage(db, lease, stage_key="sec_normalization")
    with pytest.raises(psycopg.errors.CheckViolation):
        finish_execution(db, lease, outcome="completed")
    stage = start_stage(db, lease, stage_key="sec_monitor_result")
    with pytest.raises(psycopg.errors.CheckViolation):
        finish_stage(db, lease, stage_id=stage, outcome="completed")


def test_conditional_304_retains_validator_without_inventing_body(
    db, identity, seeded, monkeypatch
):
    request, lease, result, _ = run(
        db, identity, seeded, monkeypatch, submissions([filing()]), headers={"etag": '"fixture-v1"'}
    )
    plan = replace(
        seeded[0],
        cutoff=MONITOR_CUTOFF,
        baseline=MonitorBaseline(
            "prior_monitor_result",
            request.request_id,
            lease.execution_id,
            result["manifest"]["body_sha256"],
            seeded[0].cutoff,
            manifest_id=UUID(result["manifest_id"]),
        ),
    )
    _, _, second, calls = run(
        db, identity, (plan, *seeded[1:]), monkeypatch, b"", status=304, key="conditional"
    )
    assert second["outcome"] == "no_change" and len(calls) == 1
    assert calls[0].headers["if-none-match"] == '"fixture-v1"'
    attempt = db.execute(
        "SELECT * FROM source_fetch_attempts WHERE state='not_modified'"
    ).fetchone()
    assert (
        attempt["http_status"] == 304
        and attempt["validator_capture_id"] == attempt["reused_capture_id"]
    )
    assert not db.execute(
        "SELECT 1 FROM source_attempt_payloads WHERE attempt_id=%s", (attempt["id"],)
    ).fetchone()


def test_required_advertised_history_is_fetched_and_compared(db, identity, seeded, monkeypatch):
    from equity_ingest.monitor_pipeline import run_filing_monitor

    history_key = "submissions_history/0001876042/CIK0001876042-submissions-001.json"
    plan = replace(seeded[0], resources=(*seeded[0].resources, history_key))
    history = [
        {
            "name": history_key.rsplit("/", 1)[1],
            "filingCount": 1,
            "filingFrom": "2026-08-05",
            "filingTo": "2026-08-05",
        }
    ]
    body = submissions(history=history)
    calls = []

    def handler(req):
        calls.append(req)
        payload = (
            submissions([filing()])["filings"]["recent"]
            if "-submissions-" in str(req.url)
            else body
        )
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(payload).encode()))

    source, archive = seeded[1:3]
    request = monitor_request(db, identity, plan)
    lease = claim_filing_monitor(db, worker_id="monitor", request_id=request.request_id)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(source.transport, "client", client)
        result = run_filing_monitor(db, lease, source, archive, plan)
    assert len(calls) == 2 and result["outcome"] == "new_filing"
    assert result["coverage"] == {"baseline": "complete", "current": "complete"}
    assert len(result["current_capture_ids"]) == 2


@pytest.mark.parametrize("crash_point", ["before_result", "after_result"])
def test_crash_recovery_reuses_pinned_evidence_and_fences_old_lease(
    db, identity, seeded, monkeypatch, crash_point
):
    import equity_ingest.monitor_pipeline as pipeline
    from equity_schema.workflow import LeaseLost, retry_execution

    original = (
        pipeline.complete_filing_monitor if crash_point == "before_result" else pipeline._finish
    )

    def crash(*args, **kwargs):
        raise RuntimeError("fixture crash")

    target = "complete_filing_monitor" if crash_point == "before_result" else "_finish"
    monkeypatch.setattr(pipeline, target, crash)
    with pytest.raises(RuntimeError, match="fixture crash"):
        run(db, identity, seeded, monkeypatch, submissions([filing()]))
    request = monitor_request(db, identity, seeded[0])
    control = db.execute(
        "SELECT * FROM analysis_request_state WHERE request_id=%s", (request.request_id,)
    ).fetchone()
    row = db.execute(
        "SELECT * FROM analysis_executions WHERE id=%s", (control["current_execution_id"],)
    ).fetchone()
    from equity_schema.workflow import Lease

    lease = Lease(
        request.request_id,
        row["id"],
        control["attempt_epoch"],
        row["fencing_token"],
        row["lease_owner"],
        row["lease_expires_at"],
    )
    monkeypatch.setattr(pipeline, target, original)
    if crash_point == "before_result":
        retry_execution(db, lease, error_code="fixture_crash", delay_seconds=0)
        with pytest.raises(LeaseLost):
            run_filing_monitor(db, lease, seeded[1], seeded[2], seeded[0])
        lease = claim_filing_monitor(db, worker_id="recovery", request_id=request.request_id)

    def forbidden(req):
        raise AssertionError("Recovery must replay successful observations")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        monkeypatch.setattr(seeded[1].transport, "client", client)
        result = run_filing_monitor(db, lease, seeded[1], seeded[2], seeded[0])
    assert result["outcome"] == "new_filing"
    assert db.execute("SELECT count(*) AS n FROM source_attempt_payloads").fetchone()["n"] == 1


def test_corrupted_baseline_archive_prevents_network_and_advancement(
    db, identity, seeded, monkeypatch
):
    record = load_record(db, seeded[0].baseline.capture_id)
    original = seeded[2].read_blob

    def corrupt(key, sha, length):
        from equity_ingest.archive import ArchiveError

        if key == record.blob_key:
            raise ArchiveError("fixture corruption")
        return original(key, sha, length)

    monkeypatch.setattr(seeded[2], "read_blob", corrupt)
    _, _, result, calls = run(db, identity, seeded, monkeypatch, b"never fetched")
    assert result["outcome"] == "error" and result["checked_at"] is None and not calls
    assert "archive_verification_failed" in result["comparison"]["flags"]


def test_empty_downgrade_and_populated_upgrade_preserve_history(
    db_admin, db, identity, test_database_dsn
):
    from alembic import command

    from tests.conftest import migration_config

    config = migration_config(test_database_dsn)
    command.downgrade(config, "0007_bootstrap_intent")
    request = enqueue(db, identity)
    before = db.execute(
        "SELECT to_jsonb(r) AS row FROM analysis_requests r WHERE id=%s", (request.request_id,)
    ).fetchone()["row"]
    command.upgrade(config, "head")
    after = db.execute(
        "SELECT to_jsonb(r)-'filing_monitor_plan' AS row FROM analysis_requests r WHERE id=%s",
        (request.request_id,),
    ).fetchone()["row"]
    assert before == after
    assert claim_next(db, worker_id="ordinary") is None
    assert claim_source_bootstrap(db, worker_id="bootstrap").request_id == request.request_id


def test_downgrade_refuses_reviewed_seed_history(seeded, test_database_dsn):
    from alembic import command
    from sqlalchemy.exc import DBAPIError

    from tests.conftest import migration_config

    with pytest.raises(DBAPIError, match="refusing to discard monitor"):
        command.downgrade(migration_config(test_database_dsn), "0007_bootstrap_intent")


@pytest.mark.parametrize(
    "field", ["missing_arrays", "checked_time", "duplicates", "baseline", "dispatch"]
)
def test_typed_result_rejects_invalid_provenance_and_shape(
    db, identity, seeded, monkeypatch, field
):
    import copy

    import equity_ingest.monitor_pipeline as pipeline

    original = pipeline.complete_filing_monitor

    def check(database, lease, *, stage_id, result):
        invalid = copy.deepcopy(result)
        if field == "missing_arrays":
            del invalid["comparison"]["metadata_changes"]
        elif field == "checked_time":
            invalid["checked_at"] = None
        elif field == "duplicates":
            invalid["current_capture_ids"] *= 2
        elif field == "baseline":
            invalid["baseline_capture_ids"] = []
        else:
            invalid["downstream"]["dispatched"] = True
        with pytest.raises(psycopg.errors.CheckViolation):
            original(database, lease, stage_id=stage_id, result=invalid)
        original(database, lease, stage_id=stage_id, result=result)

    monkeypatch.setattr(pipeline, "complete_filing_monitor", check)
    assert run(db, identity, seeded, monkeypatch)[2]["outcome"] == "no_change"


def test_interrupted_200_body_is_retained_and_retry_is_honest(db, identity, seeded, monkeypatch):
    from equity_schema.workflow import Lease, retry_execution

    store = seeded[1].transport.attempts
    original = store.payload

    def crash(request, attempt, payload):
        original(request, attempt, payload)
        raise RuntimeError("crash after archive before capture")

    monkeypatch.setattr(store, "payload", crash)
    with pytest.raises(RuntimeError, match="crash after archive"):
        run(db, identity, seeded, monkeypatch)
    request = monitor_request(db, identity, seeded[0])
    row = db.execute(
        "SELECT e.*,s.attempt_epoch FROM analysis_executions e JOIN analysis_request_state s "
        "ON s.current_execution_id=e.id WHERE e.request_id=%s",
        (request.request_id,),
    ).fetchone()
    lease = Lease(
        request.request_id,
        row["id"],
        row["attempt_epoch"],
        row["fencing_token"],
        row["lease_owner"],
        row["lease_expires_at"],
    )
    retry_execution(db, lease, error_code="fixture_crash", delay_seconds=0)
    monkeypatch.setattr(store, "payload", original)
    _, _, result, calls = run(db, identity, seeded, monkeypatch)
    assert result["outcome"] == "no_change" and len(calls) == 1
    assert (
        db.execute(
            "SELECT count(*) AS n FROM source_fetch_attempts WHERE state='interrupted_unknown'"
        ).fetchone()["n"]
        == 1
    )
    assert db.execute("SELECT count(*) AS n FROM source_attempt_payloads").fetchone()["n"] == 2
    assert db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == 2


def test_concurrent_claim_has_one_owner(db_admin, db, identity, seeded):
    request = monitor_request(db, identity, seeded[0])

    def claim(i):
        with psycopg.connect(db_admin.info.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            return claim_filing_monitor(
                conn, worker_id=f"worker-{i}", request_id=request.request_id
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(pool.map(claim, range(2)))
    assert sum(lease is not None for lease in leases) == 1


def test_seed_cutoff_and_identity_cannot_be_replaced(db, identity, seeded):
    plan = seeded[0]
    for baseline in (
        replace(plan.baseline, cutoff=plan.baseline.cutoff - timedelta(seconds=1)),
        replace(plan.baseline, capture_id=uuid4()),
        replace(plan.baseline, plan_sha256="0" * 64),
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            monitor_request(db, identity, replace(plan, baseline=baseline))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("UPDATE filing_monitor_seed_approvals SET review_reference='altered'")


def test_partial_http_success_cannot_claim_complete_inventory(db, identity, seeded, monkeypatch):
    _, _, result, _ = run(db, identity, seeded, monkeypatch, submissions(), status=206)
    assert result["outcome"] == "error" and not result["baseline_eligible"]


def test_operator_can_inspect_queued_and_running_requests_without_http(db, identity, seeded):
    from scripts.monitor_crcl_filings import request_status

    request = monitor_request(db, identity, seeded[0])
    before = len(seeded[3])
    assert request_status(db, request.request_id)["execution_state"] == "queued"
    claim_filing_monitor(db, worker_id="operator-status")
    status = request_status(db, request.request_id)
    assert status["execution_state"] == "running" and status["typed_result_available"] is False
    assert len(seeded[3]) == before


def test_capture_loader_supports_readonly_audit_transaction(db, seeded):
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        capture = load_record(db, seeded[0].baseline.capture_id)
        assert capture.capture_id == seeded[0].baseline.capture_id


def test_one_completed_result_per_execution_is_database_enforced(db, identity, seeded, monkeypatch):
    import equity_ingest.monitor_pipeline as pipeline

    original = pipeline._finish

    def attempt_duplicate(database, lease, result):
        with pytest.raises(psycopg.errors.UniqueViolation, match="workflow_one_monitor_result"):
            with database.transaction():
                stage = start_stage(database, lease, stage_key="sec_monitor_result")
                pipeline.complete_filing_monitor(database, lease, stage_id=stage, result=result)
        original(database, lease, result)

    monkeypatch.setattr(pipeline, "_finish", attempt_duplicate)
    assert run(db, identity, seeded, monkeypatch)[2]["outcome"] == "no_change"
