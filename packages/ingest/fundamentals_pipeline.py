"""S6a worker stage for already approved synthetic inputs; no provider acquisition."""

from uuid import UUID

from equity_schema.fundamentals_store import (
    _require_idle_autocommit,
    calculate_and_publish,
    freeze_inputs,
)
from equity_schema.workflow import Database, Lease, start_stage


def run_fundamentals_stage(db: Database, lease: Lease) -> UUID:
    """Resume freeze/calculate/publish using the existing request and stage identity.

    The caller obtains a W1 lease after enqueue_fundamentals. A failed attempt is
    retried through W1; no scheduler or independent queue is created here.
    """
    _require_idle_autocommit(db)
    saved = db.execute(
        "SELECT stage_id,input_snapshot_id FROM analysis_snapshots WHERE request_id=%s",
        (lease.request_id,),
    ).fetchone()
    if saved:
        return calculate_and_publish(
            db, lease, stage_id=saved["stage_id"], input_snapshot_id=saved["input_snapshot_id"]
        )
    intent = db.execute(
        "SELECT review_id FROM fundamentals_request_intents WHERE request_id=%s",
        (lease.request_id,),
    ).fetchone()
    if not intent:
        raise ValueError("Request has no reviewed S6 intent")
    active = db.execute(
        "SELECT id FROM analysis_stage_attempts WHERE execution_id=%s "
        "AND stage_key='fundamentals' AND state='running'",
        (lease.execution_id,),
    ).fetchone()
    stage = active["id"] if active else start_stage(db, lease, stage_key="fundamentals")
    frozen = freeze_inputs(db, lease, stage_id=stage, review_id=intent["review_id"])
    return calculate_and_publish(db, lease, stage_id=stage, input_snapshot_id=frozen)
