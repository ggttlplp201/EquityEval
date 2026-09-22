"""D038 fictional S6 → S4 evidence → S7 W1 tracer; no live source contact."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest
from equity_ingest.valuation_pipeline import run_valuation_stage
from equity_schema.fundamentals_canonical import content_hash
from equity_schema.fundamentals_store import get_snapshot
from equity_schema.market_selection import select_price
from equity_schema.valuation import RequestCreate
from equity_schema.valuation_store import (
    approve_fixture_manifest,
    engine_build,
    enqueue_valuation,
    get_latest,
    get_run,
    price_evidence,
    save_fixture_assumptions,
)
from equity_schema.workflow import claim_next, finish_execution

from tests.conftest import test_database_profile
from tests.integration.test_fundamentals_publication import publish as source_publish
from tests.integration.test_fundamentals_publication import setup
from tests.market_selection_seed import prepare_market, publish_prepared
from tests.valuation_seed import manifest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(test_database_profile() != "timescale-pg16", reason="S7 requires 0012"),
]
assert setup


@pytest.fixture
def valuation_setup(db_admin, db, setup):
    source_id = source_publish(db, setup)
    source = get_snapshot(db, workspace_id=setup[0].workspace_id, snapshot_id=source_id)
    inputs = setup[1]
    source_key = db.execute(
        "SELECT source_id FROM source_captures WHERE id=%s", (inputs.captures[0].capture_id,)
    ).fetchone()["source_id"]
    ids = dict(
        source=source_key,
        security=inputs.selector.security_id,
        quote=inputs.selector.quote_identifier_id,
    )
    at = datetime(2026, 2, 28, tzinfo=UTC)
    market = prepare_market(
        db_admin,
        db,
        ids=ids,
        day=date(2026, 2, 27),
        value="17.34375",
        captured_at=at,
        observation_changes=dict(publication_precision="instant", source_published_at=at),
    )
    publish_prepared(db, market)
    finish_execution(db, market[1], outcome="completed")
    selected = select_price(
        db,
        source_key,
        ids["quote"],
        date(2026, 2, 27),
        retrieval_cutoff=at,
        source_known_at=at,
        batch_id=market[3]["batch"]["id"],
    )
    assert selected.usable, selected.flags
    draft = manifest()
    saved = save_fixture_assumptions(
        db_admin,
        workspace_id=setup[0].workspace_id,
        content=draft.assumptions,
        idempotency_key="fictional-owner-review",
    )
    draft = draft.model_copy(
        update=dict(
            selector=inputs.selector,
            source_snapshot_id=source_id,
            source_payload_hash=source.payload_hash,
            source_input_hash=content_hash(inputs),
            assumption_set_id=saved.id,
            model=draft.model.model_copy(update={"engine_build": engine_build()}),
            price=price_evidence(selected, action_basis=draft.shares.action_basis),
        )
    )
    review = approve_fixture_manifest(
        db_admin,
        workspace_id=setup[0].workspace_id,
        manifest=draft,
        reviewed_by="fictional owner",
        reason="H03/H04 hand-computed economic claims; no company valuation",
    )
    return setup, draft, review


def enqueue(db, prepared, key="valuation-first", parent=None):
    source, draft, review = prepared
    request = enqueue_valuation(
        db,
        workspace_id=source[0].workspace_id,
        request=RequestCreate(
            review_id=review,
            parent_request_id=parent or source[3].request_id,
            idempotency_key=key,
            max_attempts=3,
        ),
    )
    lease = claim_next(db, worker_id="synthetic-valuation", lease_seconds=3600)
    return request, lease


def test_fictional_reverse_run_exact_replay_and_rerun(db, valuation_setup):
    source, draft, review = valuation_setup
    request, lease = enqueue(db, valuation_setup)
    run_id = run_valuation_stage(db, lease)
    run = get_run(db, workspace_id=source[0].workspace_id, run_id=run_id)
    assert run.result.bridge.market_ev_target == Decimal("193.4375")
    assert run.result.scenario_dispersion is not None
    assert run.result.evidence_mode == "synthetic"
    assert run_valuation_stage(db, lease) == run_id
    new, second_lease = enqueue(db, valuation_setup, "again", request.request_id)
    second_id = run_valuation_stage(db, second_lease)
    other = get_run(db, workspace_id=source[0].workspace_id, run_id=second_id)
    assert other.parent_run_id == run_id
    assert other.payload_hash == run.payload_hash
    assert other.input_snapshot_id != run.input_snapshot_id
    assert second_id != run_id
    assert get_run(db, workspace_id=uuid4(), run_id=run_id) is None
    latest = get_latest(
        db,
        workspace_id=source[0].workspace_id,
        issuer_id=draft.selector.issuer_id,
        security_id=draft.selector.security_id,
        quote_identifier_id=draft.selector.quote_identifier_id,
        scope_id=source[3].membership_id,
        compatibility_key=content_hash(draft),
    )
    assert latest.run.run_id == second_id
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("UPDATE valuation_model_runs SET outcome=%s WHERE id=%s", ("completed", run_id))


@pytest.mark.parametrize("action", ["cancel", "remove", "expire"])
def test_cancelled_removed_or_expired_worker_cannot_publish(db_admin, db, valuation_setup, action):
    from equity_schema.workflow import LeaseLost, cancel_request, remove_watchlist_stock

    request, lease = enqueue(db, valuation_setup)
    if action == "cancel":
        cancel_request(db, request_id=request.request_id)
    elif action == "remove":
        remove_watchlist_stock(db, membership_id=valuation_setup[0][3].membership_id)
    else:
        db_admin.execute(
            "UPDATE analysis_executions SET lease_expires_at=clock_timestamp()-interval '1 second' "
            "WHERE id=%s",
            (lease.execution_id,),
        )
    with pytest.raises((LeaseLost, psycopg.errors.ObjectNotInPrerequisiteState)):
        run_valuation_stage(db, lease)
    assert db.execute("SELECT count(*) n FROM valuation_model_runs").fetchone()["n"] == 0


def test_retry_keeps_manifest_and_old_epoch_is_fenced(db, valuation_setup):
    from equity_schema.valuation_store import freeze_inputs
    from equity_schema.workflow import LeaseLost, retry_execution, start_stage

    request, lease = enqueue(db, valuation_setup)
    stage = start_stage(db, lease, stage_key="valuation")
    frozen = freeze_inputs(db, lease, stage_id=stage, review_id=valuation_setup[2])
    retry_execution(db, lease, error_code="fictional_crash", delay_seconds=0)
    new = claim_next(db, worker_id="recovery", lease_seconds=3600)
    with pytest.raises(LeaseLost):
        run_valuation_stage(db, lease)
    run_id = run_valuation_stage(db, new)
    saved = get_run(db, workspace_id=valuation_setup[0][0].workspace_id, run_id=run_id)
    assert saved.input_snapshot_id == frozen


def test_newer_failed_request_prevents_older_promotion(db, valuation_setup):
    from equity_schema.workflow import finish_execution

    first, lease = enqueue(db, valuation_setup)
    first_id = run_valuation_stage(db, lease)
    old, old_lease = enqueue(db, valuation_setup, "older", first.request_id)
    new, new_lease = enqueue(db, valuation_setup, "newer", first.request_id)
    finish_execution(db, new_lease, outcome="failed", reason="fictional_failure_before_freeze")
    old_id = run_valuation_stage(db, old_lease)
    assert old_id != first_id
    source, draft, _ = valuation_setup
    latest = get_latest(
        db,
        workspace_id=source[0].workspace_id,
        issuer_id=draft.selector.issuer_id,
        security_id=draft.selector.security_id,
        quote_identifier_id=draft.selector.quote_identifier_id,
        scope_id=source[3].membership_id,
        compatibility_key=content_hash(draft),
    )
    assert latest.run.run_id == first_id
    assert latest.latest_request_id == new.request_id
    assert latest.latest_request_state == "failed"


def test_saved_replay_does_not_use_current_engine(db, valuation_setup, monkeypatch):
    import equity_ingest.valuation_pipeline as worker

    request, lease = enqueue(db, valuation_setup)
    saved = run_valuation_stage(db, lease)

    def never(*args, **kwargs):
        raise AssertionError("Saved replay must not calculate")

    monkeypatch.setattr(worker, "engine_build", never)
    monkeypatch.setattr(worker, "calculate_scenario", never)
    assert run_valuation_stage(db, lease) == saved


def test_forged_payload_and_wrong_lease_leave_no_partial_run(db, valuation_setup):
    from dataclasses import replace

    from equity_core.valuation_payload import calculate_payload
    from equity_schema.fundamentals_canonical import canonical_json
    from equity_schema.valuation_store import freeze_inputs, publish
    from equity_schema.workflow import LeaseLost, start_stage

    request, lease = enqueue(db, valuation_setup)
    stage = start_stage(db, lease, stage_key="valuation")
    frozen = freeze_inputs(db, lease, stage_id=stage, review_id=valuation_setup[2])
    payload = calculate_payload(valuation_setup[1])
    changed = payload.model_copy(update={"conclusions": ("forged",)})
    with pytest.raises(psycopg.errors.CheckViolation):
        publish(
            db,
            lease,
            stage_id=stage,
            input_snapshot_id=frozen,
            payload_text=canonical_json(changed),
        )
    with pytest.raises(LeaseLost):
        publish(
            db,
            replace(lease, fencing_token=lease.fencing_token + 1),
            stage_id=stage,
            input_snapshot_id=frozen,
            payload_text=canonical_json(payload),
        )
    assert db.execute("SELECT count(*) n FROM valuation_model_runs").fetchone()["n"] == 0
    assert db.execute("SELECT count(*) n FROM valuation_scenario_results").fetchone()["n"] == 0
    assert run_valuation_stage(db, lease)


def test_missing_claim_publishes_auditable_gapped_run(db_admin, db, valuation_setup):
    source, draft, _ = valuation_setup
    missing = draft.claims[0].model_copy(
        update=dict(state="unavailable", amount=None, basis="unreviewed", reasons=("missing",))
    )
    draft = draft.model_copy(update={"claims": (missing, *draft.claims[1:])})
    review = approve_fixture_manifest(
        db_admin,
        workspace_id=source[0].workspace_id,
        manifest=draft,
        reviewed_by="owner",
        reason="Explicit missing cash fixture",
    )
    request, lease = enqueue(db, (source, draft, review))
    saved = get_run(db, workspace_id=source[0].workspace_id, run_id=run_valuation_stage(db, lease))
    assert saved.outcome == "completed_with_gaps"
    assert saved.result.bridge.market_ev_target is None
    assert all(s.solve.state == "unavailable" for s in saved.result.scenarios)


def test_owner_review_rejects_changed_source_quote_or_engine(db_admin, valuation_setup):
    source, draft, _ = valuation_setup
    for change in [
        dict(source_payload_hash="0" * 64),
        dict(model=draft.model.model_copy(update={"engine_build": "0" * 64})),
        dict(price=draft.price.model_copy(update={"value": Decimal("99")})),
    ]:
        with pytest.raises(ValueError):
            approve_fixture_manifest(
                db_admin,
                workspace_id=source[0].workspace_id,
                manifest=draft.model_copy(update=change),
                reviewed_by="owner",
                reason="Bad fixture",
            )


def test_immutable_records_and_children_cannot_be_modified_or_appended(
    db_admin, db, valuation_setup
):
    from psycopg import sql

    source, draft, review = valuation_setup
    _, lease = enqueue(db, valuation_setup)
    saved = run_valuation_stage(db, lease)
    for table in [
        "valuation_assumption_sets",
        "valuation_input_reviews",
        "valuation_model_runs",
        "valuation_scenario_results",
    ]:
        with pytest.raises(psycopg.errors.CheckViolation):
            db_admin.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
        db_admin.execute("INSERT INTO valuation_conclusions VALUES(%s,99,%s)", (saved, "late"))
    with pytest.raises(
        (psycopg.errors.ObjectNotInPrerequisiteState, psycopg.errors.CheckViolation)
    ):
        db_admin.execute(
            "INSERT INTO valuation_review_claim_ids VALUES(%s,%s,%s)", (review, "cash", "late")
        )


def test_runtime_sql_cannot_store_incomplete_assumptions(db, valuation_setup):
    from equity_schema.fundamentals_canonical import canonical_json

    text = canonical_json(
        dict(
            authored_at=datetime.now(UTC),
            valuation_at="2026-01-01T00:00:00.000000Z",
            retrospective=True,
            judgments=[],
        )
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "SELECT valuation_create_assumptions(%s,NULL,'malformed-runtime',%s)",
            (valuation_setup[0][0].workspace_id, text),
        )


def test_run_children_must_match_payload_even_inside_owner_creation_transaction(
    db_admin, db, valuation_setup
):
    from equity_core.valuation_payload import calculate_payload
    from equity_schema.fundamentals_canonical import canonical_json
    from equity_schema.valuation_store import freeze_inputs
    from equity_schema.workflow import start_stage
    from psycopg.types.json import Jsonb

    _, lease = enqueue(db, valuation_setup)
    stage = start_stage(db, lease, stage_key="valuation")
    frozen = freeze_inputs(db, lease, stage_id=stage, review_id=valuation_setup[2])
    payload = canonical_json(calculate_payload(valuation_setup[1]))
    with pytest.raises(psycopg.errors.CheckViolation):
        with db_admin.transaction():
            saved = db_admin.execute(
                "SELECT valuation_publish(%s,%s,%s,%s) result",
                (Jsonb(lease.as_json()), stage, frozen, payload),
            ).fetchone()["result"]
            db_admin.execute(
                "INSERT INTO valuation_conclusions VALUES(%s,99,%s)", (saved, "forged")
            )
    assert db.execute("SELECT count(*) n FROM valuation_model_runs").fetchone()["n"] == 0


@pytest.mark.parametrize("defect", ["extra", "unit", "slot"])
def test_runtime_sql_rejects_nested_assumption_contract_violations(db, valuation_setup, defect):
    import json

    from equity_schema.fundamentals_canonical import canonical_json

    body = json.loads(canonical_json(valuation_setup[1].assumptions))
    body["authored_at"] = (
        datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )
    body["retrospective"] = True
    if defect == "extra":
        body["scenarios"][0]["invented_parameter"] = "1"
    elif defect == "unit":
        body["judgments"][0]["unit"] = "fraction"
    else:
        body["scenarios"][0]["terminal_margin"] = "0.2"
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "SELECT valuation_create_assumptions(%s,NULL,%s,%s)",
            (valuation_setup[0][0].workspace_id, "bad-nested-" + defect, canonical_json(body)),
        )


def test_cancel_between_sensitivity_cells_prevents_publication(
    db_admin, db, valuation_setup, monkeypatch
):
    import equity_ingest.valuation_pipeline as worker
    from equity_schema.valuation import SensitivityGrid
    from equity_schema.workflow import LeaseLost, cancel_request

    source, draft, _ = valuation_setup
    grid = SensitivityGrid(
        name="cell cancellation",
        reference_scenario="reference",
        output="conditional_reprice",
        x_parameter="wacc",
        x_values=("0.09", "0.1", "0.11"),
        y_parameter="terminal_growth",
        y_values=("0.01", "0.02", "0.03"),
        conditional_parameter="0.2",
    )
    assumptions = draft.assumptions.model_copy(update={"sensitivities": (grid,)})
    saved = save_fixture_assumptions(
        db_admin,
        workspace_id=source[0].workspace_id,
        content=assumptions,
        idempotency_key="grid-cancellation",
    )
    draft = draft.model_copy(update={"assumptions": assumptions, "assumption_set_id": saved.id})
    review = approve_fixture_manifest(
        db_admin,
        workspace_id=source[0].workspace_id,
        manifest=draft,
        reviewed_by="owner",
        reason="Fictional cancellation case",
    )
    request, lease = enqueue(db, (source, draft, review))
    original = worker.calculate_sensitivity_cell
    count = 0

    def cancelled(*args):
        nonlocal count
        count += 1
        cell = original(*args)
        cancel_request(db, request_id=request.request_id)
        return cell

    monkeypatch.setattr(worker, "calculate_sensitivity_cell", cancelled)
    with pytest.raises(LeaseLost):
        run_valuation_stage(db, lease)
    assert count == 1
    assert db.execute("SELECT count(*) n FROM valuation_model_runs").fetchone()["n"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("valuation_at", "2026-02-27T24:00:00.000000Z"),
        ("valuation_at", "2026-02-28T00:00:00Z"),
        ("revenue_anchor", "1e2"),
    ],
)
def test_runtime_sql_rejects_noncanonical_typed_values(db, valuation_setup, field, value):
    import json

    from equity_schema.fundamentals_canonical import canonical_json

    body = json.loads(canonical_json(valuation_setup[1].assumptions))
    body["authored_at"] = (
        datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )
    body["retrospective"] = True
    if field == "valuation_at":
        body[field] = value
    else:
        body["scenarios"][0][field] = value
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "SELECT valuation_create_assumptions(%s,NULL,%s,%s)",
            (valuation_setup[0][0].workspace_id, "bad-canonical", canonical_json(body)),
        )


def test_concurrent_publication_and_rollback_are_atomic(test_database_dsn, db, valuation_setup):
    from concurrent.futures import ThreadPoolExecutor

    from equity_core.valuation_payload import calculate_payload
    from equity_schema.fundamentals_canonical import canonical_json
    from equity_schema.valuation_store import freeze_inputs, publish
    from equity_schema.workflow import start_stage
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb

    _, lease = enqueue(db, valuation_setup)
    stage = start_stage(db, lease, stage_key="valuation")
    frozen = freeze_inputs(db, lease, stage_id=stage, review_id=valuation_setup[2])
    payload = canonical_json(calculate_payload(valuation_setup[1]))
    with pytest.raises(RuntimeError, match="before commit"):
        with db.transaction():
            db.execute(
                "SELECT valuation_publish(%s,%s,%s,%s)",
                (Jsonb(lease.as_json()), stage, frozen, payload),
            )
            raise RuntimeError("before commit")
    assert db.execute("SELECT count(*) n FROM valuation_model_runs").fetchone()["n"] == 0
    assert db.execute("SELECT count(*) n FROM valuation_payloads").fetchone()["n"] == 0

    def run(_):
        with psycopg.connect(test_database_dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            return publish(
                conn, lease, stage_id=stage, input_snapshot_id=frozen, payload_text=payload
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(run, range(2)))
    assert ids[0] == ids[1]
    assert db.execute("SELECT count(*) n FROM valuation_model_runs").fetchone()["n"] == 1
    assert db.execute("SELECT count(*) n FROM valuation_scenario_results").fetchone()["n"] == 3


def test_migration_refuses_to_drop_valuation_history(test_database_dsn, valuation_setup):
    from alembic import command

    from tests.conftest import migration_config

    with pytest.raises(Exception, match="cannot downgrade retained valuation history"):
        command.downgrade(migration_config(test_database_dsn), "0011_fundamentals_publication")


def test_raw_close_selector_cannot_be_substituted_with_adjusted_close(db, valuation_setup):
    from dataclasses import replace

    draft = valuation_setup[1]
    p = draft.price
    selected = select_price(
        db,
        p.source_id,
        p.quote_identifier_id,
        p.reference_date,
        retrieval_cutoff=p.retrieval_cutoff,
        source_known_at=p.source_known_at,
        batch_id=p.batch_id,
    )
    assert selected.field == "close"
    assert selected.adjustment_basis == "split_and_dividend"
    assert price_evidence(selected, action_basis=p.action_basis).value == Decimal("17.34375")
    with pytest.raises(ValueError, match="raw close"):
        price_evidence(replace(selected, field="adj_close"), action_basis=p.action_basis)


@pytest.mark.parametrize(
    "text",
    ["0", "-0", "0.000000", "0E-7", "-0E+2", "1E+2", "1.00E+4", "1.2300", "0.000001", "1.00E-7"],
)
def test_sql_canonical_decimal_spelling_matches_python(db, valuation_setup, text):
    import json

    from equity_schema.fundamentals_canonical import canonical_json
    from equity_schema.valuation_store import get_assumptions

    body = json.loads(canonical_json(valuation_setup[1].assumptions))
    body["authored_at"] = (
        datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )
    body["retrospective"] = True
    body["scenarios"][0]["revenue_anchor"] = text
    workspace = valuation_setup[0][0].workspace_id
    saved = db.execute(
        "SELECT valuation_create_assumptions(%s,NULL,%s,%s) id",
        (workspace, "decimal-" + text, canonical_json(body)),
    ).fetchone()["id"]
    assert (
        str(
            get_assumptions(db, workspace_id=workspace, assumption_id=saved)
            .content.scenarios[0]
            .revenue_anchor
        )
        == text
    )
