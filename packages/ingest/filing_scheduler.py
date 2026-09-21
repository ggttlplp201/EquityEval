"""Read-only scheduler health projection. Provider work stays in the D4a worker."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from equity_schema.filing_scheduler import ScheduleConfig, slot_times
from equity_schema.workflow import Database


def schedule_snapshot(
    db: Database, schedule: UUID, *, as_of: datetime | None = None
) -> dict[str, Any]:
    if as_of is None:
        clock = db.execute("SELECT scheduler_now() AS t").fetchone()
        assert clock is not None
        as_of = clock["t"]
    assert as_of is not None
    if as_of.utcoffset() is None:
        raise ValueError("Snapshot clock requires timezone")
    row = db.execute(
        "SELECT s.*,st.revision_id,st.epoch,st.last_slot,st.unresolved_slot,st.baseline,"
        "st.baseline_slot,st.failures,st.retry_at,st.rebase_reason,st.last_tick_at,"
        "r.config,r.config_hash AS revision_hash "
        "FROM filing_schedules s JOIN filing_schedule_state st ON st.schedule_id=s.id "
        "JOIN filing_schedule_revisions r ON r.id=st.revision_id WHERE s.id=%s",
        (schedule,),
    ).fetchone()
    if row is None:
        raise ValueError("Unknown schedule")
    config = ScheduleConfig.from_json(row["config"])
    slots = db.execute(
        "SELECT sl.id,sl.revision_id,sl.slot_index,sl.nominal_at,sl.due_at,sl.plan,sl.plan_hash,"
        "sl.request_id,sl.request_key,sl.reserved_units,e.state,e.available_at,e.attempt_no,st.terminal_outcome,"
        "st.current_execution_id FROM filing_schedule_slots sl "
        "JOIN analysis_request_state st ON st.request_id=sl.request_id "
        "JOIN analysis_executions e ON e.id=st.current_execution_id "
        "WHERE sl.schedule_id=%s ORDER BY sl.slot_index",
        (schedule,),
    ).fetchall()
    events = db.execute(
        "SELECT kind,semantic_key,details,at,slot_id FROM filing_schedule_events "
        "WHERE schedule_id=%s ORDER BY at,id",
        (schedule,),
    ).fetchall()
    revisions = db.execute(
        "SELECT id,epoch,predecessor,first_slot,config,config_hash,reason,created_at "
        "FROM filing_schedule_revisions WHERE schedule_id=%s ORDER BY epoch",
        (schedule,),
    ).fetchall()
    attempts = db.execute(
        "SELECT a.id,a.state,a.http_status,a.requested_at,a.finished_at,a.reused_capture_id,"
        "p.body_sha256,p.byte_count FROM source_fetch_attempts a "
        "JOIN analysis_stage_attempts st ON st.id=a.stage_attempt_id "
        "JOIN analysis_executions e ON e.id=st.execution_id "
        "JOIN filing_schedule_slots sl ON sl.request_id=e.request_id "
        "LEFT JOIN source_attempt_payloads p ON p.attempt_id=a.id "
        "WHERE sl.schedule_id=%s ORDER BY a.prepared_at,a.id",
        (schedule,),
    ).fetchall()
    resolved_at = {e["slot_id"]: e["at"] for e in events if e["kind"] == "resolved"}
    reserved = {
        "n": sum(
            sl["reserved_units"]
            for sl in slots
            if sl["id"] not in resolved_at or resolved_at[sl["id"]] > as_of - timedelta(hours=24)
        )
    }
    unresolved = next((sl for sl in slots if sl["id"] == row["unresolved_slot"]), None)
    retry_gates = [
        g
        for g in (row["retry_at"], unresolved["available_at"] if unresolved else None)
        if g is not None and g > as_of
    ]
    retry_at = max(retry_gates) if retry_gates else row["retry_at"]
    next_index = row["last_slot"] + 1
    nominal, due = slot_times(config, schedule, row["revision_id"], next_index)
    outstanding_due = unresolved["due_at"] if unresolved else due
    lag = max(0, int((as_of - outstanding_due).total_seconds()))
    expired = as_of.astimezone(UTC).date() > config.plan.inventory_end
    reasons = []
    if expired or row["rebase_reason"]:
        health = "rebase_required"
        reasons.append(row["rebase_reason"] or "filed_window_expired")
    elif not config.active:
        health = "paused"
    elif row["failures"]:
        health = "degraded"
        reasons.append("last_poll_not_eligible")
    elif lag > config.lag_seconds:
        health = "lagging"
    elif unresolved or (row["retry_at"] and row["retry_at"] > as_of):
        health = "waiting"
    else:
        health = "ready"
    if reserved["n"] + config.reserved_units > config.budget_units:
        reasons.append("budget_reservation_full")
        if health == "ready":
            health = "waiting"
    eligible = [e for e in events if e["kind"] == "resolved" and e["details"].get("eligible")]
    last = eligible[-1] if eligible else None
    # Finishing a prepared attempt or recovering an unknown interruption is not
    # evidence that an HTTP operation actually completed.
    completed = [
        a["finished_at"]
        for a in attempts
        if a["requested_at"] is not None
        and a["finished_at"] is not None
        and a["state"] != "interrupted_unknown"
    ]
    return {
        "version": "sec-filing-scheduler-snapshot-v1",
        "as_of": as_of,
        "schedule_id": schedule,
        "revision_id": row["revision_id"],
        "epoch": row["epoch"],
        "config": row["config"],
        "config_sha256": row["revision_hash"],
        "service": "not_configured",
        "mode": "saved_manual_check",
        "health": health,
        "health_meaning": "Configuration readiness only; no registered background worker.",
        "reasons": reasons,
        "baseline": row["baseline"],
        "baseline_slot": row["baseline_slot"],
        "last_tick_at": row["last_tick_at"],
        "last_http_completed_at": max(completed) if completed else None,
        "last_success_at": last["details"]["checked_at"] if last else None,
        "last_success_cutoff": row["baseline"]["cutoff"] if last else None,
        "next_nominal_at": nominal,
        "next_due_at": due,
        "lag_seconds": lag,
        "next_due_actionable": config.active and not expired and row["rebase_reason"] is None,
        "retry_at": retry_at,
        "consecutive_failures": row["failures"],
        "reserved_units": reserved["n"],
        "actual_attempts": sum(a["requested_at"] is not None for a in attempts),
        "missed_intervals": [e["details"] for e in events if e["kind"] == "missed_range"],
        "slots": slots,
        "events": events,
        "revisions": revisions,
        "attempts": attempts,
        "downstream_dispatched": False,
    }
