"""D036 adversarial isolated scheduler, actual W1/SEC path with fictional HTTP."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import psycopg
import pytest
from alembic import command
from equity_ingest.monitor_pipeline import run_filing_monitor
from equity_schema.filing_scheduler import (
    ScheduleConfig,
    create_schedule,
    revise_schedule,
    slot_times,
    tick,
)
from equity_schema.workflow import cancel_request, claim_filing_monitor
from psycopg import sql
from psycopg.rows import dict_row

from tests.conftest import migration_config
from tests.integration import test_filing_monitor as fixtures
from tests.test_filing_monitor import filing, submissions

identity = fixtures.identity
transport = fixtures.transport
pytestmark = fixtures.pytestmark


@pytest.fixture
def seeded(db_admin, db, identity, transport, monkeypatch):
    # These tests isolate DB lifecycle interleavings; shared Redis timing is tested
    # independently in test_sec_limiter/transport. Never replace the live limiter.
    from equity_ingest.limiter import Permit

    class FixtureLimiter:
        def acquire(self, *, deadline):
            return Permit("isolated-scheduler-fixture")

        def confirm(self, permit):
            return datetime.now(UTC)

        def cooldown(self, seconds):
            return datetime.now(UTC) + timedelta(seconds=seconds)

    monkeypatch.setattr(transport[0].transport, "limiter", FixtureLimiter())
    result = fixtures.seeded.__wrapped__(db_admin, db, identity, transport)
    # Isolated scheduler clock is fixed; no real/backdated application request.
    # Source request/lease timestamps retain their actual test runtime clock.
    set_clock(db_admin, fixtures.MONITOR_CUTOFF)
    return (replace(result[0], cutoff=fixtures.MONITOR_CUTOFF - timedelta(hours=1)), *result[1:])


def create(db_admin, identity, seeded, **changes):
    plan = seeded[0]
    config = ScheduleConfig(plan, plan.cutoff, 300, 0, 99, 3, 300, active=True)
    config = replace(config, **changes)
    schedule = create_schedule(
        db_admin,
        workspace=identity[0].workspace_id,
        security=identity[2],
        key="schedule",
        config=config,
        review="D036 isolated fixture",
    )
    return schedule, config


def state(db, schedule):
    return db.execute(
        "SELECT * FROM filing_schedule_state WHERE schedule_id=%s", (schedule,)
    ).fetchone()


def run_slot(db, schedule, seeded, monkeypatch, body=None):
    item = tick(db, schedule)
    request = UUID(item["request_id"])
    lease = claim_filing_monitor(db, worker_id="scheduled", request_id=request)
    assert lease is not None
    from equity_schema.filing_monitor import FilingMonitorPlan

    plan = FilingMonitorPlan.from_json(
        db.execute(
            "SELECT filing_monitor_plan FROM analysis_requests WHERE id=%s", (request,)
        ).fetchone()["filing_monitor_plan"]
    )
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(
            200, stream=httpx.ByteStream(json.dumps(body or submissions()).encode())
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(seeded[1].transport, "client", client)
        result = run_filing_monitor(db, lease, seeded[1], seeded[2], plan)
    return item, result, calls


def test_atomic_concurrent_ticks_complete_repeat_and_lineage(
    db_admin, db, identity, seeded, monkeypatch
):
    schedule, config = create(db_admin, identity, seeded)

    def concurrent(_):
        with psycopg.connect(db_admin.info.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            return tick(conn, schedule)

    with ThreadPoolExecutor(max_workers=4) as pool:
        slots = list(pool.map(concurrent, range(4)))
    assert len({s["request_id"] for s in slots}) == 1
    assert db.execute("SELECT count(*) AS n FROM filing_schedule_slots").fetchone()["n"] == 1
    item, result, calls = run_slot(db, schedule, seeded, monkeypatch)
    assert result["baseline_eligible"] and len(calls) == 1
    assert tick(db, schedule)["state"] == "not_due"
    baseline = state(db, schedule)["baseline"]
    assert (
        baseline["kind"] == "prior_monitor_result" and baseline["request_id"] == item["request_id"]
    )
    before = db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(x["state"] == "not_due" for x in pool.map(concurrent, range(4)))
    assert claim_filing_monitor(db, worker_id="again", request_id=UUID(item["request_id"])) is None
    assert db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"] == before
    assert (
        db.execute(
            "SELECT count(*) AS n FROM filing_schedule_events WHERE kind='resolved'"
        ).fetchone()["n"]
        == 1
    )
    assert (
        db.execute(
            "SELECT count(*) AS n FROM filing_schedule_events WHERE kind='missed_range'"
        ).fetchone()["n"]
        == 1
    )
    for table in ("security_identifiers", "watchlist_memberships", "normalization_batches"):
        assert (
            db.execute(
                sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier(table))
            ).fetchone()["n"]
            == 0
        )
    assert state(db, schedule)["baseline"] == baseline


def test_pause_blocks_claim_and_resume_exact_pending_request(db_admin, db, identity, seeded):
    schedule, c = create(db_admin, identity, seeded)
    item = tick(db, schedule)
    paused = replace(c, active=False)
    revision = revise_schedule(
        db_admin, schedule, epoch=1, key="pause", config=paused, reason="test"
    )
    assert (
        revise_schedule(db_admin, schedule, epoch=1, key="pause", config=paused, reason="test")
        == revision
    )
    assert tick(db, schedule)["state"] == "paused"
    assert claim_filing_monitor(db, worker_id="bypass", request_id=UUID(item["request_id"])) is None
    with pytest.raises(psycopg.errors.SerializationFailure):
        revise_schedule(db_admin, schedule, epoch=1, key="stale", config=c, reason="test")
    revise_schedule(db_admin, schedule, epoch=2, key="resume", config=c, reason="test")
    assert tick(db, schedule)["request_id"] == item["request_id"]
    assert (
        claim_filing_monitor(db, worker_id="resume", request_id=UUID(item["request_id"]))
        is not None
    )


@pytest.mark.parametrize(
    "field", ["resources", "forms", "policy_revision_id", "inventory_end", "version", "baseline"]
)
def test_full_scope_revision_and_privilege_guards(db_admin, db, identity, seeded, field):
    schedule, c = create(db_admin, identity, seeded)
    value = c.as_json()
    value["plan"][field] = value["plan"][field] if field == "baseline" else "invalid"
    if field == "baseline":
        value["plan"]["baseline"]["manifest_sha256"] = "0" * 64
    from psycopg.types.json import Jsonb

    with pytest.raises(psycopg.Error):
        db_admin.execute(
            "SELECT scheduler_revise(%s,1,%s,%s,%s)", (schedule, field, Jsonb(value), "test")
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        create_schedule(
            db,
            workspace=identity[0].workspace_id,
            security=identity[2],
            key="bypass",
            config=c,
            review="test",
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute(
            "UPDATE filing_schedule_state SET baseline=%s WHERE schedule_id=%s",
            (Jsonb(value["plan"]["baseline"]), schedule),
        )


def test_expired_scope_semantic_dedup_and_no_dispatch(db_admin, db, identity, seeded):
    schedule, c = create(db_admin, identity, seeded)
    db_admin.execute(
        "CREATE OR REPLACE FUNCTION scheduler_now() RETURNS TIMESTAMPTZ "
        "LANGUAGE sql VOLATILE SET search_path=public,pg_temp AS $$ "
        "SELECT '2026-09-22T00:00:00Z'::TIMESTAMPTZ $$"
    )
    for _ in range(4):
        assert tick(db, schedule)["state"] == "rebase_required"
    assert db.execute("SELECT count(*) AS n FROM filing_schedule_slots").fetchone()["n"] == 0
    assert (
        db.execute(
            "SELECT count(*) AS n FROM filing_schedule_events WHERE kind='blocked'"
        ).fetchone()["n"]
        == 1
    )


def test_terminal_incomplete_resolves_without_baseline_advance(
    db_admin, db, identity, seeded, monkeypatch
):
    schedule, c = create(db_admin, identity, seeded)
    set_clock(db_admin, c.anchor)
    old = state(db, schedule)["baseline"]
    _, result, _ = run_slot(
        db, schedule, seeded, monkeypatch, submissions([filing(acceptanceDateTime="")])
    )
    assert result["outcome"] == "incomplete"
    for _ in range(3):
        assert tick(db, schedule)["reason"] == "backoff"
    assert state(db, schedule)["baseline"] == old and state(db, schedule)["unresolved_slot"] is None
    assert (
        db.execute(
            "SELECT count(*) AS n FROM filing_schedule_events WHERE kind='resolved'"
        ).fetchone()["n"]
        == 1
    )

    set_clock(db_admin, c.anchor + timedelta(seconds=300))
    next_slot, result, _ = run_slot(db, schedule, seeded, monkeypatch)
    next_plan = db.execute(
        "SELECT filing_monitor_plan AS p FROM analysis_requests WHERE id=%s",
        (UUID(next_slot["request_id"]),),
    ).fetchone()["p"]
    assert next_plan["baseline"] == old and result["baseline_eligible"]


def test_cancelled_slot_resolves_backoff_without_erasing_failure(db_admin, db, identity, seeded):
    schedule, c = create(db_admin, identity, seeded)
    item = tick(db, schedule)
    old = state(db, schedule)["baseline"]
    cancel_request(db, request_id=UUID(item["request_id"]))
    for _ in range(3):
        assert tick(db, schedule)["reason"] == "backoff"
    assert state(db, schedule)["baseline"] == old and state(db, schedule)["unresolved_slot"] is None
    assert (
        db.execute(
            "SELECT count(*) AS n FROM filing_schedule_events WHERE kind='deferred'"
        ).fetchone()["n"]
        == 1
    )


def test_sql_python_jitter_match_and_immutable_history(db_admin, db, identity, seeded):
    schedule, c = create(db_admin, identity, seeded, jitter_seconds=30)
    st = state(db, schedule)
    for index in (0, 1, 100, 1000):
        expected = slot_times(c, schedule, st["revision_id"], index)[1]
        assert (
            db.execute(
                "SELECT scheduler_due(%s,%s,%s) AS t", (schedule, st["revision_id"], index)
            ).fetchone()["t"]
            == expected
        )
    with pytest.raises(psycopg.Error):
        db_admin.execute("UPDATE filing_schedule_revisions SET reason='changed'")


def test_populated_downgrade_refused(db_admin, db, identity, seeded, test_database_dsn):
    create(db_admin, identity, seeded)
    with pytest.raises(Exception, match="refusing to discard schedule history"):
        command.downgrade(migration_config(test_database_dsn), "0009_monitor_result_identity")
    assert db.execute("SELECT count(*) AS n FROM filing_schedules").fetchone()["n"] == 1


def set_clock(db_admin, at):
    db_admin.execute(
        sql.SQL(
            "CREATE OR REPLACE FUNCTION scheduler_now() RETURNS TIMESTAMPTZ "
            "LANGUAGE sql VOLATILE SET search_path=public,pg_temp AS {}"
        ).format(sql.Literal("SELECT '" + at.isoformat() + "'::TIMESTAMPTZ"))
    )


def test_success_failure_success_retains_latest_baseline(
    db_admin, db, identity, seeded, monkeypatch
):
    schedule, config = create(db_admin, identity, seeded)
    set_clock(db_admin, config.anchor)
    first, _, _ = run_slot(db, schedule, seeded, monkeypatch)
    tick(db, schedule)
    baseline = state(db, schedule)["baseline"]
    set_clock(db_admin, config.anchor + timedelta(seconds=300))
    second = tick(db, schedule)
    cancel_request(db, request_id=UUID(second["request_id"]))
    tick(db, schedule)
    assert state(db, schedule)["baseline"] == baseline
    set_clock(db_admin, config.anchor + timedelta(seconds=600))
    third, _, calls = run_slot(db, schedule, seeded, monkeypatch)
    third_plan = db.execute(
        "SELECT filing_monitor_plan AS p FROM analysis_requests WHERE id=%s",
        (UUID(third["request_id"]),),
    ).fetchone()["p"]
    assert third_plan["baseline"]["request_id"] == first["request_id"]
    assert len(calls) == 1
    tick(db, schedule)
    assert state(db, schedule)["baseline"]["request_id"] == third["request_id"]
    from psycopg.types.json import Jsonb

    with pytest.raises(psycopg.errors.CheckViolation, match="baseline regression"):
        db_admin.execute(
            "UPDATE filing_schedule_state SET baseline=%s,baseline_slot=0 WHERE schedule_id=%s",
            (Jsonb(baseline), schedule),
        )
    # Delayed old-slot reconciliation cannot regress the latest eligible baseline.
    with db_admin.transaction():
        db_admin.execute(
            "UPDATE filing_schedule_state SET unresolved_slot=%s WHERE schedule_id=%s",
            (UUID(first["slot_id"]), schedule),
        )
        with pytest.raises(psycopg.errors.CheckViolation, match="baseline regression"):
            with db_admin.transaction():
                db_admin.execute("SELECT scheduler_reconcile(%s)", (schedule,))
        db_admin.execute(
            "UPDATE filing_schedule_state SET unresolved_slot=NULL WHERE schedule_id=%s",
            (schedule,),
        )
    # Repeated reconciliation cannot replace the new baseline with an older completed slot.
    for _ in range(3):
        tick(db, schedule)
    assert state(db, schedule)["baseline"]["request_id"] == third["request_id"]
    outcomes = db.execute(
        "SELECT details->>'outcome' AS v FROM filing_schedule_events WHERE kind='resolved' "
        "ORDER BY at"
    ).fetchall()
    assert [r["v"] for r in outcomes] == ["no_change", "error", "no_change"]


@pytest.mark.parametrize("when", ["before_dispatch", "after_dispatch"])
def test_pause_dispatch_interleaving(db_admin, db, identity, seeded, monkeypatch, when):
    schedule, config = create(db_admin, identity, seeded)
    original = seeded[1].transport.attempts.dispatched

    def pause(request, attempt, at):
        if when == "after_dispatch":
            original(request, attempt, at)
        revise_schedule(
            db_admin,
            schedule,
            epoch=1,
            key="pause-at-boundary",
            config=replace(config, active=False),
            reason="interleaving fixture",
        )
        if when == "before_dispatch":
            original(request, attempt, at)

    monkeypatch.setattr(seeded[1].transport.attempts, "dispatched", pause)
    if when == "before_dispatch":
        with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="dispatch blocked"):
            run_slot(db, schedule, seeded, monkeypatch)
        assert (
            db.execute(
                "SELECT count(*) AS n FROM source_fetch_attempts a "
                "JOIN analysis_stage_attempts st ON st.id=a.stage_attempt_id "
                "JOIN analysis_executions e ON e.id=st.execution_id "
                "JOIN filing_schedule_slots sl ON sl.request_id=e.request_id "
                "WHERE a.requested_at IS NOT NULL"
            ).fetchone()["n"]
            == 0
        )
    else:
        _, result, calls = run_slot(db, schedule, seeded, monkeypatch)
        assert result["baseline_eligible"] and len(calls) == 1
        assert tick(db, schedule)["state"] == "paused"


def test_budget_reservation_and_last_boundary_lowered_limit(
    db_admin, db, identity, seeded, monkeypatch
):
    schedule, config = create(db_admin, identity, seeded)
    set_clock(db_admin, config.anchor)
    run_slot(db, schedule, seeded, monkeypatch)
    tick(db, schedule)
    set_clock(db_admin, config.anchor + timedelta(seconds=300))
    tick(db, schedule)
    original = seeded[1].transport.attempts.dispatched

    def lower(request, attempt, at):
        revise_schedule(
            db_admin,
            schedule,
            epoch=1,
            key="lower-budget",
            config=replace(config, budget_units=9),
            reason="test",
        )
        original(request, attempt, at)

    monkeypatch.setattr(seeded[1].transport.attempts, "dispatched", lower)
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="dispatch blocked"):
        run_slot(db, schedule, seeded, monkeypatch)
    assert db.execute("SELECT scheduler_budget(%s) AS n", (schedule,)).fetchone()["n"] == 18


def test_concurrent_workers_have_one_lease_and_crash_retry_backoff(db_admin, db, identity, seeded):
    schedule, _ = create(db_admin, identity, seeded)
    request = UUID(tick(db, schedule)["request_id"])

    def claim(_):
        with psycopg.connect(db_admin.info.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            return claim_filing_monitor(conn, worker_id="concurrent", request_id=request)

    with ThreadPoolExecutor(max_workers=4) as pool:
        leases = [x for x in pool.map(claim, range(4)) if x is not None]
    assert len(leases) == 1
    db_admin.execute(
        "UPDATE analysis_executions SET lease_expires_at=clock_timestamp()-interval '1 second' "
        "WHERE id=%s",
        (leases[0].execution_id,),
    )
    assert claim_filing_monitor(db, worker_id="recover", request_id=request) is None
    row = db.execute(
        "SELECT e.available_at,e.attempt_no FROM analysis_executions e "
        "JOIN analysis_request_state s ON s.current_execution_id=e.id WHERE s.request_id=%s",
        (request,),
    ).fetchone()
    from equity_ingest.filing_scheduler import schedule_snapshot

    assert schedule_snapshot(db, schedule)["retry_at"] == row["available_at"]
    assert row["attempt_no"] == 2 and row["available_at"] > datetime.now(UTC) + timedelta(
        seconds=55
    )


def test_saved_health_is_literal_and_read_only(db_admin, db, identity, seeded):
    from equity_ingest.filing_scheduler import schedule_snapshot

    schedule, config = create(db_admin, identity, seeded)
    set_clock(db_admin, config.anchor - timedelta(seconds=1))
    with db.transaction():
        db.execute("SET TRANSACTION READ ONLY")
        snap = schedule_snapshot(db, schedule)
    assert snap["health"] == "ready" and snap["service"] == "not_configured"
    assert snap["last_success_at"] is None and snap["actual_attempts"] == 0
    assert snap["next_due_actionable"]


def test_new_history_resource_requires_review_without_implicit_fetch(
    db_admin, db, identity, seeded, monkeypatch
):
    schedule, c = create(db_admin, identity, seeded)
    _, result, calls = run_slot(
        db,
        schedule,
        seeded,
        monkeypatch,
        submissions(
            history=[
                {
                    "name": "CIK0001876042-submissions-001.json",
                    "filingCount": 1,
                    "filingFrom": "2025-01-01",
                    "filingTo": "2025-12-31",
                }
            ]
        ),
    )
    assert result["outcome"] == "incomplete" and len(calls) == 1
    for _ in range(3):
        assert tick(db, schedule)["state"] == "rebase_required"
    assert (
        db.execute(
            "SELECT count(*) AS n FROM filing_schedule_events WHERE kind='blocked'"
        ).fetchone()["n"]
        == 1
    )


def test_raw_sql_config_array_order_is_canonical_and_repeated_create_is_noop(
    db_admin, db, identity, seeded
):
    from psycopg.types.json import Jsonb

    schedule, config = create(db_admin, identity, seeded)
    raw = config.as_json()
    raw["plan"]["forms"].reverse()
    repeated = db_admin.execute(
        "SELECT scheduler_create(%s,%s,%s,%s,%s) AS id",
        (identity[0].workspace_id, identity[2], "schedule", Jsonb(raw), "D036 isolated fixture"),
    ).fetchone()["id"]
    assert repeated == schedule
    assert db.execute("SELECT count(*) AS n FROM filing_schedule_revisions").fetchone()["n"] == 1


@pytest.mark.parametrize("after_success", [False, True])
def test_predispatch_cancellation_does_not_advance_http_completion(
    db_admin, db, identity, seeded, monkeypatch, after_success
):
    from equity_ingest.filing_scheduler import schedule_snapshot
    from equity_ingest.limiter import CoordinationUnavailable

    schedule, config = create(db_admin, identity, seeded)
    set_clock(db_admin, config.anchor)
    previous = None
    if after_success:
        run_slot(db, schedule, seeded, monkeypatch)
        tick(db, schedule)
        previous = schedule_snapshot(db, schedule)["last_http_completed_at"]
        assert previous is not None
        set_clock(db_admin, config.anchor + timedelta(seconds=300))

    def unavailable(*, deadline):
        raise CoordinationUnavailable("isolated fixture")

    monkeypatch.setattr(seeded[1].transport.limiter, "acquire", unavailable)
    _, result, calls = run_slot(db, schedule, seeded, monkeypatch)
    assert not calls and not result["baseline_eligible"]
    snap = schedule_snapshot(db, schedule)
    cancelled = [a for a in snap["attempts"] if a["state"] == "cancelled"]
    assert len(cancelled) == 1
    assert cancelled[0]["requested_at"] is None and cancelled[0]["finished_at"] is not None
    assert snap["actual_attempts"] == int(after_success)
    assert snap["last_http_completed_at"] == previous
