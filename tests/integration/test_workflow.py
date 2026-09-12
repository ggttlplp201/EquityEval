"""Actual PostgreSQL checks for durable watchlist requests and fake workers."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from equity_schema.workflow import (
    LeaseLost,
    RequestedPeriod,
    RequestOptions,
    add_watchlist_stock,
    cancel_request,
    claim_next,
    create_workspace_watchlist,
    finish_execution,
    finish_stage,
    remove_watchlist_stock,
    renew_lease,
    rerun_analysis,
    retry_execution,
    start_stage,
)
from psycopg.rows import dict_row

from tests.evidence_seed import seed_evidence

pytestmark = pytest.mark.integration


@pytest.fixture
def setup_workflow(db_admin, db):
    evidence = seed_evidence(db_admin)
    workspace = create_workspace_watchlist(db, name="Local", timezone="Asia/Shanghai")
    return workspace, evidence


def add(db, setup, key="add-1"):
    workspace, evidence = setup
    return add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=evidence["security"],
        quote_identifier_id=evidence["quote"],
        idempotency_key=key,
    )


def test_duplicate_add_keys_and_readd_preserve_intent(db_admin, db, setup_workflow):
    first = add(db, setup_workflow)
    duplicate = add(db, setup_workflow, key="second-click")
    assert first == duplicate
    remove_watchlist_stock(db, membership_id=first.membership_id)
    assert add(db, setup_workflow, key="second-click") == first
    assert (
        db.execute(
            "SELECT count(*) AS n FROM watchlist_memberships WHERE removed_at IS NULL"
        ).fetchone()["n"]
        == 0
    )
    readded = add(db, setup_workflow, key="new-add")
    assert readded.membership_id != first.membership_id
    assert readded.request_id != first.request_id
    assert readded.generation == first.generation + 1
    assert db.execute("SELECT count(*) AS n FROM analysis_requests").fetchone()["n"] == 2


def test_same_key_changed_options_and_unknown_assumption_rejected(db, setup_workflow):
    first = add(db, setup_workflow)
    workspace, evidence = setup_workflow
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        add_watchlist_stock(
            db,
            watchlist_id=workspace.watchlist_id,
            security_id=evidence["security"],
            quote_identifier_id=evidence["quote"],
            idempotency_key="add-1",
            options=RequestOptions(history_mode="original_as_filed"),
        )
    with pytest.raises(TypeError):
        RequestOptions(assumption_set_id=uuid4())
    assert first.request_id is not None


def test_explicit_refresh_is_new_intent_and_transport_retry_is_same(db, setup_workflow):
    first = add(db, setup_workflow)
    workspace, evidence = setup_workflow
    kwargs = dict(
        workspace_id=workspace.workspace_id,
        security_id=evidence["security"],
        quote_identifier_id=evidence["quote"],
        parent_request_id=first.request_id,
    )
    refresh = rerun_analysis(db, idempotency_key="refresh-1", **kwargs)
    assert rerun_analysis(db, idempotency_key="refresh-1", **kwargs) == refresh
    other = rerun_analysis(db, idempotency_key="refresh-2", **kwargs)
    assert len({first.request_id, refresh.request_id, other.request_id}) == 3
    assert first.request_sequence < refresh.request_sequence < other.request_sequence


def test_add_and_events_roll_back_with_outer_transaction(db, setup_workflow):
    with pytest.raises(RuntimeError), db.transaction():
        add(db, setup_workflow)
        raise RuntimeError("simulate crash before commit")
    for table in (
        "watchlist_memberships",
        "analysis_requests",
        "analysis_executions",
        "analysis_request_state",
        "analysis_request_keys",
        "execution_events",
    ):
        assert db.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] == 0


def test_concurrent_add_creates_one_request(db_admin, db, setup_workflow):
    def perform(index):
        with psycopg.connect(db_admin.info.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            return add(conn, setup_workflow, key=f"parallel-{index}")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(perform, range(2)))
    assert results[0].request_id == results[1].request_id
    assert db.execute("SELECT count(*) AS n FROM analysis_request_keys").fetchone()["n"] == 2


def test_fake_worker_stage_and_completion_are_atomic_and_immutable(db, setup_workflow):
    request = add(db, setup_workflow)
    lease = claim_next(db, worker_id="fake-worker", lease_seconds=60)
    assert lease is not None and lease.request_id == request.request_id
    assert claim_next(db, worker_id="other") is None
    lease = renew_lease(db, lease, lease_seconds=120)
    stage = start_stage(db, lease, stage_key="source_check")
    finish_stage(db, lease, stage_id=stage, outcome="completed")
    blocked = start_stage(db, lease, stage_key="valuation")
    finish_stage(
        db, lease, stage_id=blocked, outcome="unsupported", reason="bank_model_unavailable"
    )
    finish_execution(db, lease, outcome="completed_with_gaps")
    assert (
        db.execute(
            "SELECT terminal_outcome FROM analysis_request_state WHERE request_id=%s",
            (request.request_id,),
        ).fetchone()["terminal_outcome"]
        == "completed_with_gaps"
    )
    with pytest.raises(LeaseLost):
        finish_execution(db, lease)
    for statement in (
        "UPDATE analysis_requests SET trigger='manual_refresh'",
        "DELETE FROM execution_events",
        "TRUNCATE analysis_executions",
        "UPDATE analysis_stage_attempts SET state='running'",
        "UPDATE analysis_request_state SET terminal_outcome=NULL",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(statement)


def test_retry_epoch_blocks_old_worker_and_cancel_blocks_new(db, setup_workflow):
    request = add(db, setup_workflow)
    old = claim_next(db, worker_id="first")
    assert old is not None
    retry_execution(db, old, error_code="source_unavailable", delay_seconds=0)
    new = claim_next(db, worker_id="second")
    assert new is not None and new.execution_id != old.execution_id
    assert new.request_id == old.request_id and new.epoch > old.epoch
    with pytest.raises(LeaseLost):
        finish_execution(db, old)
    cancel_request(db, request_id=request.request_id)
    with pytest.raises(LeaseLost):
        finish_execution(db, new)
    assert claim_next(db, worker_id="third") is None


def test_expired_lease_recovered_once(db_admin, db, setup_workflow):
    add(db, setup_workflow)
    old = claim_next(db, worker_id="dead")
    assert old is not None
    db_admin.execute(
        "UPDATE analysis_executions SET lease_expires_at=clock_timestamp()-interval '1 second' "
        "WHERE id=%s",
        (old.execution_id,),
    )
    with pytest.raises(LeaseLost):
        renew_lease(db, old)
    new = claim_next(db, worker_id="recovery")
    assert new is not None and new.execution_id != old.execution_id
    assert new.epoch > old.epoch
    assert claim_next(db, worker_id="extra") is None
    finish_execution(db, new)


def test_retry_and_completion_reject_live_stage(db, setup_workflow):
    add(db, setup_workflow)
    lease = claim_next(db, worker_id="worker")
    assert lease is not None
    start_stage(db, lease, stage_key="pending")
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
        finish_execution(db, lease)
    retry_execution(db, lease, error_code="timeout", delay_seconds=0)
    assert db.execute("SELECT state FROM analysis_stage_attempts").fetchone()["state"] == "failed"


def test_cross_owner_parent_and_quote_rejected(db_admin, db, setup_workflow):
    first = add(db, setup_workflow)
    workspace, evidence = setup_workflow
    other = create_workspace_watchlist(db, name="Other")
    with pytest.raises(psycopg.errors.CheckViolation):
        rerun_analysis(
            db,
            workspace_id=other.workspace_id,
            security_id=evidence["security"],
            quote_identifier_id=evidence["quote"],
            idempotency_key="cross-owner",
            parent_request_id=first.request_id,
        )
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        rerun_analysis(
            db,
            workspace_id=workspace.workspace_id,
            security_id=uuid4(),
            quote_identifier_id=evidence["quote"],
            idempotency_key="wrong-security",
        )


def test_request_options_validate_dates_before_queueing():
    with pytest.raises(ValueError):
        RequestOptions(history_mode="as_filed_by_date")
    with pytest.raises(ValueError):
        RequestedPeriod(kind="instant", end=date(2025, 1, 1), start=date(2024, 1, 1))
    with pytest.raises(ValueError):
        RequestedPeriod(kind="duration", end=date(2024, 1, 1), start=date(2025, 1, 1))
    with pytest.raises(ValueError):
        RequestOptions(retrieval_vintage=datetime.now())
    options = RequestOptions(
        history_mode="as_filed_by_date",
        filed_cutoff=date(2025, 1, 1),
        requested_periods=(RequestedPeriod(kind="instant", end=date(2024, 12, 31)),),
        retrieval_vintage=datetime.now(UTC) - timedelta(days=1),
    )
    assert options.filed_cutoff == date(2025, 1, 1)


def test_retry_transition_rolls_back_state_stage_and_audit(db, setup_workflow):
    request = add(db, setup_workflow)
    lease = claim_next(db, worker_id="worker")
    assert lease is not None
    start_stage(db, lease, stage_key="fetch")
    before = db.execute("SELECT count(*) AS n FROM execution_events").fetchone()["n"]
    with pytest.raises(RuntimeError), db.transaction():
        retry_execution(db, lease, error_code="timeout", delay_seconds=0)
        raise RuntimeError("crash inside atomic transition")
    control = db.execute(
        "SELECT * FROM analysis_request_state WHERE request_id=%s", (request.request_id,)
    ).fetchone()
    assert control["current_execution_id"] == lease.execution_id
    assert control["attempt_epoch"] == lease.epoch
    assert db.execute("SELECT state FROM analysis_stage_attempts").fetchone()["state"] == "running"
    assert db.execute("SELECT count(*) AS n FROM execution_events").fetchone()["n"] == before


def test_concurrent_retry_has_one_winner(db_admin, db, setup_workflow):
    add(db, setup_workflow)
    lease = claim_next(db, worker_id="original")
    assert lease is not None

    def retry(_):
        with psycopg.connect(db_admin.info.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            try:
                retry_execution(conn, lease, error_code="timeout", delay_seconds=0)
                return "retried"
            except LeaseLost:
                return "lost"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(retry, range(2)))
    assert sorted(results) == ["lost", "retried"]
    assert db.execute("SELECT count(*) AS n FROM analysis_executions").fetchone()["n"] == 2


def test_retry_budget_is_durable(db, setup_workflow):
    workspace, evidence = setup_workflow
    request = add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=evidence["security"],
        quote_identifier_id=evidence["quote"],
        idempotency_key="once",
        options=RequestOptions(max_attempts=1),
    )
    lease = claim_next(db, worker_id="worker")
    assert lease is not None
    retry_execution(db, lease, error_code="timeout", delay_seconds=0)
    assert claim_next(db, worker_id="retry") is None
    assert (
        db.execute(
            "SELECT terminal_outcome FROM analysis_request_state WHERE request_id=%s",
            (request.request_id,),
        ).fetchone()["terminal_outcome"]
        == "failed"
    )


def test_reused_capture_retains_original_retrieval(db, setup_workflow):
    _, evidence = setup_workflow
    add(db, setup_workflow)
    before = db.execute(
        "SELECT fetched_at FROM source_captures WHERE id=%s", (evidence["capture"],)
    ).fetchone()["fetched_at"]
    lease = claim_next(db, worker_id="worker")
    assert lease is not None
    stage = start_stage(db, lease, stage_key="archive_replay")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        finish_stage(db, lease, stage_id=stage, outcome="completed", reused_capture_ids=(uuid4(),))
    finish_stage(
        db, lease, stage_id=stage, outcome="completed", reused_capture_ids=(evidence["capture"],)
    )
    assert db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == 1
    assert (
        db.execute(
            "SELECT fetched_at FROM source_captures WHERE id=%s", (evidence["capture"],)
        ).fetchone()["fetched_at"]
        == before
    )


def test_idempotency_vintage_is_independent_of_session_timezone(db, setup_workflow):
    workspace, evidence = setup_workflow
    options = RequestOptions(retrieval_vintage=datetime(2026, 1, 1, tzinfo=UTC))
    kwargs = dict(
        watchlist_id=workspace.watchlist_id,
        security_id=evidence["security"],
        quote_identifier_id=evidence["quote"],
        idempotency_key="vintage",
        options=options,
    )
    first = add_watchlist_stock(db, **kwargs)
    db.execute("SET TIME ZONE 'Asia/Shanghai'")
    assert add_watchlist_stock(db, **kwargs) == first


def test_new_add_key_cannot_silently_change_existing_request_options(db, setup_workflow):
    add(db, setup_workflow)
    workspace, evidence = setup_workflow
    with pytest.raises(psycopg.errors.InvalidParameterValue, match="explicit refresh"):
        add_watchlist_stock(
            db,
            watchlist_id=workspace.watchlist_id,
            security_id=evidence["security"],
            quote_identifier_id=evidence["quote"],
            idempotency_key="different-options",
            options=RequestOptions(history_mode="original_as_filed"),
        )
    assert db.execute("SELECT count(*) AS n FROM analysis_request_keys").fetchone()["n"] == 1
    assert db.execute("SELECT count(*) AS n FROM analysis_requests").fetchone()["n"] == 1


def test_archived_error_response_is_not_a_reusable_success(db_admin, db, setup_workflow):
    from tests.evidence_seed import insert

    _, evidence = setup_workflow
    capture = dict(
        db_admin.execute(
            "SELECT * FROM source_captures WHERE id=%s", (evidence["capture"],)
        ).fetchone()
    )
    capture["id"] = uuid4()
    capture["http_status"] = 503
    insert(db_admin, "source_captures", **capture)
    add(db, setup_workflow)
    lease = claim_next(db, worker_id="worker")
    assert lease is not None
    stage = start_stage(db, lease, stage_key="archive_replay")
    with pytest.raises(psycopg.errors.ForeignKeyViolation, match="not successful"):
        finish_stage(
            db, lease, stage_id=stage, outcome="completed", reused_capture_ids=(capture["id"],)
        )
    assert (
        db.execute("SELECT state FROM analysis_stage_attempts WHERE id=%s", (stage,)).fetchone()[
            "state"
        ]
        == "running"
    )


def test_closed_quote_rejects_new_requests_but_preserves_old_replay(db_admin, db, setup_workflow):
    from tests.evidence_seed import insert

    workspace, evidence = setup_workflow
    first = add(db, setup_workflow)
    today = db.execute("SELECT (clock_timestamp() AT TIME ZONE 'UTC')::DATE AS day").fetchone()[
        "day"
    ]
    db.execute(
        "SELECT close_security_identifier(%s,%s,%s)",
        (evidence["quote"], today, evidence["capture"]),
    )
    assert add(db, setup_workflow) == first
    with pytest.raises(psycopg.errors.CheckViolation, match="not currently valid"):
        rerun_analysis(
            db,
            workspace_id=workspace.workspace_id,
            security_id=evidence["security"],
            quote_identifier_id=evidence["quote"],
            idempotency_key="closed-quote-refresh",
            parent_request_id=first.request_id,
        )
    quote = dict(
        db_admin.execute(
            "SELECT * FROM security_identifiers WHERE id=%s", (evidence["quote"],)
        ).fetchone()
    )
    assert quote["valid_to"] is None
    quote["id"] = uuid4()
    quote["valid_from"] = today
    insert(db_admin, "security_identifiers", **quote)
    refreshed = rerun_analysis(
        db,
        workspace_id=workspace.workspace_id,
        security_id=evidence["security"],
        quote_identifier_id=quote["id"],
        idempotency_key="new-quote-refresh",
        parent_request_id=first.request_id,
    )
    assert refreshed.request_id != first.request_id
    rows = db.execute(
        "SELECT id,quote_identifier_id FROM analysis_requests ORDER BY request_sequence"
    ).fetchall()
    assert rows == [
        {"id": first.request_id, "quote_identifier_id": evidence["quote"]},
        {"id": refreshed.request_id, "quote_identifier_id": quote["id"]},
    ]
