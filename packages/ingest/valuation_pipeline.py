"""Explicit synthetic S7 worker. Reuses W1; never activates a provider or listener."""

from uuid import UUID

from equity_core.valuation_payload import (
    assemble_payload,
    bridge,
    calculate_scenario,
    calculate_sensitivity_cell,
    summarize_sensitivity,
)
from equity_schema.fundamentals_canonical import canonical_json
from equity_schema.fundamentals_store import _require_idle_autocommit
from equity_schema.valuation_store import (
    engine_build,
    freeze_inputs,
    frozen_manifest,
    publish,
    saved_payload,
)
from equity_schema.workflow import Database, Lease, renew_lease, start_stage


def run_valuation_stage(db: Database, lease: Lease) -> UUID:
    _require_idle_autocommit(db)
    saved = db.execute(
        "SELECT stage_id,input_snapshot_id FROM valuation_model_runs WHERE request_id=%s",
        (lease.request_id,),
    ).fetchone()
    if saved:
        body = saved_payload(db, lease)
        assert body is not None
        return publish(
            db,
            lease,
            stage_id=saved["stage_id"],
            input_snapshot_id=saved["input_snapshot_id"],
            payload_text=body,
        )
    intent = db.execute(
        "SELECT review_id FROM valuation_request_intents WHERE request_id=%s", (lease.request_id,)
    ).fetchone()
    if not intent:
        raise ValueError("No immutable valuation intent")
    active = db.execute(
        "SELECT id FROM analysis_stage_attempts WHERE execution_id=%s "
        "AND stage_key='valuation' AND state='running'",
        (lease.execution_id,),
    ).fetchone()
    stage = active["id"] if active else start_stage(db, lease, stage_key="valuation")
    frozen = freeze_inputs(db, lease, stage_id=stage, review_id=intent["review_id"])
    inputs = frozen_manifest(db, frozen)
    if inputs.model.engine_build != engine_build():
        raise ValueError("Frozen engine build differs; explicit reviewed rerun required")
    linked = bridge(inputs)
    results = []
    for scenario in inputs.assumptions.scenarios:
        lease = renew_lease(db, lease, lease_seconds=3600)
        results.append(calculate_scenario(scenario, linked))
    # Each solver/cell is a bounded pure batch; cancellation/lease checks run
    # between cells, not just between potentially large grids.
    sensitivities = []
    for grid in inputs.assumptions.sensitivities:
        cells = []
        for x in grid.x_values:
            for y in grid.y_values:
                lease = renew_lease(db, lease, lease_seconds=3600)
                cells.append(calculate_sensitivity_cell(inputs, linked, grid, x, y))
        sensitivities.append(summarize_sensitivity(grid, tuple(cells)))
    lease = renew_lease(db, lease, lease_seconds=3600)
    payload = assemble_payload(inputs, linked, tuple(results), tuple(sensitivities))
    return publish(
        db, lease, stage_id=stage, input_snapshot_id=frozen, payload_text=canonical_json(payload)
    )
