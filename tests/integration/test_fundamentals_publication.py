"""Synthetic governed tracer and adversarial W1 publication boundaries."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest
from equity_core.fundamentals import calculate_payload
from equity_schema.fundamentals_canonical import canonical_json, content_hash
from equity_schema.fundamentals_store import (
    approve_fixture_manifest,
    calculate_and_publish,
    enqueue_fundamentals,
    freeze_inputs,
    get_latest,
    get_snapshot,
)
from equity_schema.workflow import (
    LeaseLost,
    add_watchlist_stock,
    cancel_request,
    claim_next,
    finish_execution,
    finish_stage,
    remove_watchlist_stock,
    rerun_analysis,
    retry_execution,
    start_stage,
)
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from tests.conftest import test_database_profile
from tests.fundamentals_seed import database_manifest, request_options

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        test_database_profile() != "timescale-pg16", reason="S6 requires migration 0011"
    ),
]


@pytest.fixture
def setup(db_admin, db):
    workspace, inputs = database_manifest(db_admin, db)
    review = approve_fixture_manifest(
        db_admin,
        workspace_id=workspace.workspace_id,
        manifest=inputs,
        reviewed_by="synthetic-owner",
        reason="Hand-checked 20/100 = 0.2",
    )
    request = enqueue_fundamentals(
        db,
        workspace_id=workspace.workspace_id,
        watchlist_id=workspace.watchlist_id,
        review_id=review,
        idempotency_key="first",
        parent_request_id=None,
        max_attempts=3,
    )
    lease = claim_next(db, worker_id="synthetic-worker", lease_seconds=3600)
    stage = start_stage(db, lease, stage_key="fundamentals")
    frozen = freeze_inputs(db, lease, stage_id=stage, review_id=review)
    return workspace, inputs, review, request, lease, stage, frozen


def publish(db, setup):
    return calculate_and_publish(db, setup[4], stage_id=setup[5], input_snapshot_id=setup[6])


def refresh(db, setup, key):
    workspace, inputs, review, request, *_ = setup
    new = enqueue_fundamentals(
        db,
        workspace_id=workspace.workspace_id,
        watchlist_id=None,
        review_id=review,
        idempotency_key=key,
        parent_request_id=request.request_id,
        max_attempts=3,
    )
    lease = claim_next(db, worker_id=key, lease_seconds=3600)
    stage = start_stage(db, lease, stage_key="fundamentals")
    frozen = freeze_inputs(db, lease, stage_id=stage, review_id=review)
    return workspace, inputs, review, new, lease, stage, frozen


def latest(db, setup):
    workspace, inputs, _, request, *_ = setup
    return get_latest(
        db,
        workspace_id=workspace.workspace_id,
        issuer_id=inputs.selector.issuer_id,
        security_id=inputs.selector.security_id,
        compatibility_key=content_hash(inputs.selector),
        scope_id=request.membership_id,
    )


def test_publish_retry_rerun_and_exact_retrieval(db, setup):
    first = publish(db, setup)
    saved = get_snapshot(db, workspace_id=setup[0].workspace_id, snapshot_id=first)
    assert saved.result.metrics[0].value == "0.2", saved.result.metrics[0].reasons
    assert saved.result.metrics[0].status == "valid"
    assert saved.outcome == "completed_with_gaps"  # Explicit history window has no samples.
    assert publish(db, setup) == first
    assert get_snapshot(db, workspace_id=uuid4(), snapshot_id=first) is None
    new = refresh(db, setup, "refresh")
    second = publish(db, new)
    assert second != first
    other = get_snapshot(db, workspace_id=setup[0].workspace_id, snapshot_id=second)
    assert other.payload_hash == saved.payload_hash
    assert other.input_snapshot_id != saved.input_snapshot_id
    assert latest(db, setup)[0].snapshot_id == second
    assert (
        db.execute("SELECT count(*) n FROM fundamentals_calculation_payloads").fetchone()["n"] == 1
    )
    assert get_snapshot(db, workspace_id=setup[0].workspace_id, snapshot_id=first) == saved


def test_altered_payload_and_fence_rejected_without_partial_results(db, setup):
    body = calculate_payload(setup[1], history_payloads={}).model_dump(mode="json")
    body["metrics"][0]["value"] = "0.9"
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "SELECT fundamentals_publish(%s,%s,%s,%s)",
            (Jsonb(setup[4].as_json()), setup[5], setup[6], canonical_json(body)),
        )
    assert db.execute("SELECT count(*) n FROM analysis_snapshots").fetchone()["n"] == 0
    with pytest.raises(LeaseLost):
        calculate_and_publish(
            db, replace(setup[4], fencing_token=999), stage_id=setup[5], input_snapshot_id=setup[6]
        )
    assert publish(db, setup)


def test_failed_newer_refresh_preserves_saved_result_and_blocks_older_promotion(db, setup):
    first = publish(db, setup)
    older = refresh(db, setup, "older")
    newer = refresh(db, setup, "newer")
    finish_stage(db, newer[4], stage_id=newer[5], outcome="failed", reason="synthetic_failure")
    finish_execution(db, newer[4], outcome="failed", reason="synthetic_failure")
    older_id = publish(db, older)
    assert older_id != first
    current = latest(db, setup)
    assert current[0].snapshot_id == first
    assert current[1] == newer[3].request_id
    assert current[2] == "failed"


def test_retry_reuses_frozen_inputs_but_rejects_old_epoch(db, setup):
    retry_execution(db, setup[4], error_code="synthetic_crash", delay_seconds=0)
    lease = claim_next(db, worker_id="retry", lease_seconds=3600)
    stage = start_stage(db, lease, stage_key="fundamentals")
    assert freeze_inputs(db, lease, stage_id=stage, review_id=setup[2]) == setup[6]
    with pytest.raises(LeaseLost):
        publish(db, setup)
    assert calculate_and_publish(db, lease, stage_id=stage, input_snapshot_id=setup[6])


@pytest.mark.parametrize("action", ["cancel", "remove", "expire"])
def test_ineligible_worker_cannot_publish(db_admin, db, setup, action):
    if action == "cancel":
        cancel_request(db, request_id=setup[3].request_id)
    elif action == "remove":
        remove_watchlist_stock(db, membership_id=setup[3].membership_id)
    else:
        db_admin.execute(
            "UPDATE analysis_executions SET lease_expires_at=clock_timestamp()-interval '1 second' "
            "WHERE id=%s",
            (setup[4].execution_id,),
        )
    with pytest.raises((LeaseLost, psycopg.errors.ObjectNotInPrerequisiteState)):
        publish(db, setup)
    assert db.execute("SELECT count(*) n FROM analysis_snapshots").fetchone()["n"] == 0


def test_concurrent_publish_is_one_atomic_snapshot(test_database_dsn, db, setup):
    def run(_):
        with psycopg.connect(test_database_dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            return publish(conn, setup)

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(run, range(2)))
    assert ids[0] == ids[1]
    assert db.execute("SELECT count(*) n FROM analysis_snapshots").fetchone()["n"] == 1


def test_owner_history_immutable_runtime_cannot_approve_and_children_sealed(db_admin, db, setup):
    publish(db, setup)
    for table in (
        "fundamentals_input_reviews",
        "fundamentals_review_inputs",
        "analysis_input_snapshots",
        "fundamentals_calculation_payloads",
        "analysis_snapshots",
        "latest_fundamentals",
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            db_admin.execute(f"TRUNCATE {table} CASCADE")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(f"DELETE FROM {table}")
    with pytest.raises(psycopg.errors.CheckViolation):
        db_admin.execute("UPDATE analysis_snapshots SET generated_at=clock_timestamp()")
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
        db_admin.execute(
            "INSERT INTO fundamentals_review_inputs "
            "SELECT review_id,99,period_id,unit_id,scope_id,mapping_id,selection_hash "
            "FROM fundamentals_review_inputs LIMIT 1"
        )


def test_sql_canonicalization_matches_python(db_admin):
    for body in (
        {"😀": "é", "x": ["0.100", None, True, 3]},
        {"line": 'a\n\t\\"', "z": {}, "a": []},
    ):
        text = canonical_json(body)
        row = db_admin.execute(
            "SELECT fundamentals_canonical(%s::jsonb) value,fundamentals_hash(%s) hash",
            (text, text),
        ).fetchone()
        assert row["value"] == text
        assert row["hash"] == content_hash(body)


def test_rejected_owner_input_edits_and_runtime_review(db_admin, db, setup):
    inputs = setup[1]
    fact = replace(inputs.sources[0].fact, value=Decimal("900"))
    source = replace(
        inputs.sources[0], selection=replace(inputs.sources[0].selection, facts=(fact,))
    )
    changed = inputs.model_copy(update={"sources": (source, inputs.sources[1])})
    with pytest.raises(ValueError, match="point-in-time"):
        approve_fixture_manifest(
            db_admin,
            workspace_id=setup[0].workspace_id,
            manifest=changed,
            reviewed_by="owner",
            reason="test",
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute(
            "INSERT INTO fundamentals_input_reviews SELECT * FROM fundamentals_input_reviews"
        )


def test_request_mismatch_and_changed_frozen_review_rejected(db_admin, db, setup):
    from equity_schema.fundamentals_store import engine_revision

    inputs = setup[1]
    changed = inputs.model_copy(
        update={
            "selector": inputs.selector.model_copy(
                update={
                    "evaluated_at": inputs.selector.evaluated_at.replace(hour=1),
                    "engine_revision": engine_revision(),
                }
            )
        }
    )
    review = approve_fixture_manifest(
        db_admin,
        workspace_id=setup[0].workspace_id,
        manifest=changed,
        reviewed_by="owner",
        reason="different frozen time",
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="review intent mismatch"):
        freeze_inputs(db, setup[4], stage_id=setup[5], review_id=review)
    assert publish(db, setup)
    request = rerun_analysis(
        db,
        workspace_id=setup[0].workspace_id,
        security_id=inputs.selector.security_id,
        quote_identifier_id=inputs.selector.quote_identifier_id,
        idempotency_key="wrong-default-options",
    )
    lease = claim_next(db, worker_id="mismatch")
    assert lease.request_id == request.request_id
    stage = start_stage(db, lease, stage_key="fundamentals")
    with pytest.raises(psycopg.errors.CheckViolation, match="review intent mismatch"):
        freeze_inputs(db, lease, stage_id=stage, review_id=setup[2])


def test_remove_readd_cannot_inherit_old_latest(db, setup):
    first = publish(db, setup)
    remove_watchlist_stock(db, membership_id=setup[3].membership_id)
    assert latest(db, setup) is None
    new = add_watchlist_stock(
        db,
        watchlist_id=setup[0].watchlist_id,
        security_id=setup[1].selector.security_id,
        quote_identifier_id=setup[1].selector.quote_identifier_id,
        idempotency_key="re-add",
        options=request_options(setup[1]),
    )
    assert new.generation == setup[3].generation + 1
    assert (
        get_latest(
            db,
            workspace_id=setup[0].workspace_id,
            issuer_id=setup[1].selector.issuer_id,
            security_id=setup[1].selector.security_id,
            compatibility_key=content_hash(setup[1].selector),
            scope_id=new.membership_id,
        )
        is None
    )
    assert get_snapshot(db, workspace_id=setup[0].workspace_id, snapshot_id=first)


def test_rollback_before_commit_and_exact_replay_after_commit(db, setup):
    payload = canonical_json(calculate_payload(setup[1], history_payloads={}))
    with pytest.raises(RuntimeError, match="crash"):
        with db.transaction():
            db.execute(
                "SELECT fundamentals_publish(%s,%s,%s,%s)",
                (Jsonb(setup[4].as_json()), setup[5], setup[6], payload),
            )
            raise RuntimeError("crash before commit")
    assert db.execute("SELECT count(*) n FROM analysis_snapshots").fetchone()["n"] == 0
    assert (
        db.execute("SELECT count(*) n FROM fundamentals_calculation_payloads").fetchone()["n"] == 0
    )
    assert publish(db, setup) == publish(db, setup)
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="conflicting"):
        calculate_and_publish(
            db,
            replace(setup[4], worker_id="different"),
            stage_id=setup[5],
            input_snapshot_id=setup[6],
        )


def test_migration_refuses_to_drop_retained_history(test_database_dsn, setup):
    from alembic import command

    from tests.conftest import migration_config

    with pytest.raises(Exception, match="cannot downgrade retained fundamentals history"):
        command.downgrade(migration_config(test_database_dsn), "0010_filing_scheduler")


def test_newer_queued_or_failed_before_freeze_blocks_older_promotion(db, setup):
    first = publish(db, setup)
    older = refresh(db, setup, "older")
    newer = enqueue_fundamentals(
        db,
        workspace_id=setup[0].workspace_id,
        watchlist_id=None,
        review_id=setup[2],
        idempotency_key="before-freeze",
        parent_request_id=setup[3].request_id,
        max_attempts=3,
    )
    assert latest(db, setup)[1:] == (newer.request_id, "queued")
    cancel_request(db, request_id=newer.request_id)
    publish(db, older)
    assert latest(db, setup)[0].snapshot_id == first
    assert latest(db, setup)[1:] == (newer.request_id, "cancelled")


def test_non_autocommit_connections_rejected_before_calculation(test_database_dsn, setup):
    with psycopg.connect(test_database_dsn, row_factory=dict_row) as connection:
        with pytest.raises(ValueError, match="autocommit"):
            publish(connection, setup)
        assert connection.info.transaction_status == psycopg.pq.TransactionStatus.IDLE


def test_null_arguments_cannot_replay_a_published_snapshot(db, setup):
    publish(db, setup)
    with pytest.raises(
        psycopg.errors.ObjectNotInPrerequisiteState, match="conflicting publication replay"
    ):
        db.execute("SELECT fundamentals_publish(%s,NULL,NULL,NULL)", (Jsonb(setup[4].as_json()),))


def test_idempotent_enqueue_cannot_change_review_or_adopt_running_request(db_admin, db, setup):
    same = enqueue_fundamentals(
        db,
        workspace_id=setup[0].workspace_id,
        watchlist_id=setup[0].watchlist_id,
        review_id=setup[2],
        idempotency_key="first",
        parent_request_id=None,
        max_attempts=3,
    )
    assert same == setup[3]
    publish(db, setup)
    ordinary = rerun_analysis(
        db,
        workspace_id=setup[0].workspace_id,
        security_id=setup[1].selector.security_id,
        quote_identifier_id=setup[1].selector.quote_identifier_id,
        idempotency_key="ordinary",
        options=request_options(setup[1]),
    )
    claimed = claim_next(db, worker_id="ordinary")
    assert claimed.request_id == ordinary.request_id
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="without S6 intent"):
        enqueue_fundamentals(
            db,
            workspace_id=setup[0].workspace_id,
            watchlist_id=None,
            review_id=setup[2],
            idempotency_key="ordinary",
            parent_request_id=None,
            max_attempts=3,
        )


def test_worker_stage_resumes_a_crash_after_freeze(db, setup):
    from equity_ingest.fundamentals_pipeline import run_fundamentals_stage

    snapshot = run_fundamentals_stage(db, setup[4])
    assert run_fundamentals_stage(db, setup[4]) == snapshot
    assert db.execute("SELECT count(*) n FROM analysis_stage_attempts").fetchone()["n"] == 1


def test_committed_retry_survives_engine_change_without_recalculation(db, setup, monkeypatch):
    import equity_core.fundamentals as core
    import equity_schema.fundamentals_store as store
    from equity_ingest.fundamentals_pipeline import run_fundamentals_stage

    saved = run_fundamentals_stage(db, setup[4])
    monkeypatch.setattr(store, "engine_revision", lambda: "changed-engine")

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved replay must not recompute")

    monkeypatch.setattr(core, "calculate_payload", forbidden)
    assert run_fundamentals_stage(db, setup[4]) == saved
    assert publish(db, setup) == saved


def test_saved_envelope_is_stable_across_reader_timezones(db, setup):
    saved = publish(db, setup)
    before = get_snapshot(
        db, workspace_id=setup[0].workspace_id, snapshot_id=saved
    ).model_dump_json()
    db.execute("SET TIME ZONE 'Asia/Tokyo'")
    after = get_snapshot(
        db, workspace_id=setup[0].workspace_id, snapshot_id=saved
    ).model_dump_json()
    assert before == after


def test_changed_policy_contents_miss_cache_without_mutating_old_snapshot(db_admin, db, setup):
    first = publish(db, setup)
    saved = get_snapshot(db, workspace_id=setup[0].workspace_id, snapshot_id=first)
    inputs = setup[1]
    ctx = replace(inputs.context, freshness=replace(inputs.context.freshness, max_age_days=100))
    changed = inputs.model_copy(
        update={
            "context": ctx,
            "selector": inputs.selector.model_copy(
                update={
                    "policy_content_hash": content_hash(
                        (ctx, inputs.history_policy, inputs.trend_policy)
                    )
                }
            ),
        }
    )
    review = approve_fixture_manifest(
        db_admin,
        workspace_id=setup[0].workspace_id,
        manifest=changed,
        reviewed_by="owner",
        reason="Different explicit freshness policy; same revision label",
    )
    enqueue_fundamentals(
        db,
        workspace_id=setup[0].workspace_id,
        watchlist_id=None,
        review_id=review,
        idempotency_key="policy-change",
        parent_request_id=setup[3].request_id,
        max_attempts=3,
    )
    lease = claim_next(db, worker_id="policy-change")
    from equity_ingest.fundamentals_pipeline import run_fundamentals_stage

    second = run_fundamentals_stage(db, lease)
    current = get_snapshot(db, workspace_id=setup[0].workspace_id, snapshot_id=second)
    assert current.result.metrics[0].value == saved.result.metrics[0].value
    assert current.payload_hash != saved.payload_hash
    assert current.compatibility_key != saved.compatibility_key
    assert get_snapshot(db, workspace_id=setup[0].workspace_id, snapshot_id=first) == saved
    assert (
        db.execute("SELECT count(*) n FROM fundamentals_calculation_payloads").fetchone()["n"] == 2
    )
