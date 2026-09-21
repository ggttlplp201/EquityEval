"""D036 explicit manual scheduler operator. Never installs or starts a background loop."""

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import psycopg
from dotenv import dotenv_values
from equity_ingest.filing_scheduler import schedule_snapshot
from equity_schema.filing_monitor import FilingMonitorPlan, MonitorBaseline, timestamp
from equity_schema.filing_scheduler import ScheduleConfig, create_schedule, revise_schedule, tick
from psycopg import sql
from psycopg.rows import dict_row
from redis.exceptions import RedisError

from scripts import app_postgres, app_redis
from scripts.bootstrap_crcl import contact_from_settings, registered
from scripts.export_monitor_snapshot import read_audit as read_d4a
from scripts.monitor_crcl_filings import poll, protected_history, public_audit, verify_history
from scripts.review_crcl_identity import ROOT, TABLES


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return timestamp(value)
    if isinstance(value, UUID):
        return str(value)
    raise TypeError("Unsupported scheduler audit value")


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, default=json_safe, indent=2, sort_keys=True) + "\n")


def reviewed_config(anchor: datetime) -> ScheduleConfig:
    old = read_d4a()
    result = old["result"]
    plan = FilingMonitorPlan.from_json(result["plan"])
    baseline = MonitorBaseline(
        "prior_monitor_result",
        UUID(old["request_id"]),
        UUID(old["execution_id"]),
        result["manifest"]["body_sha256"],
        plan.cutoff,
        manifest_id=UUID(result["manifest_id"]),
    )
    return ScheduleConfig(
        replace(plan, baseline=baseline), anchor, 3600, 0, 3, 1, 3600, active=True
    )


def protected_monitor_history(db: Any) -> dict[str, list[str]]:
    result = protected_history(db)
    for table in ("filing_monitor_seed_approvals", "source_attempt_payloads"):
        result[table] = [
            r["sha"]
            for r in db.execute(
                sql.SQL(
                    "SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') AS sha "
                    "FROM {} t ORDER BY sha"
                ).format(sql.Identifier(table))
            )
        ]
    return result


def audit(
    db: Any, schedule: UUID, before: dict[str, list[str]], *, as_of: datetime | None = None
) -> dict[str, Any]:
    if set(before) != set(TABLES) | {"filing_monitor_seed_approvals", "source_attempt_payloads"}:
        raise ValueError("Incomplete scheduler preservation inventory")
    after = protected_monitor_history(db)
    for table, hashes in before.items():
        if Counter(hashes) - Counter(after[table]):
            raise ValueError("Earlier application evidence changed")
    legacy = {k: before[k] for k in TABLES}
    verify_history(db, legacy)
    snapshot = schedule_snapshot(db, schedule, as_of=as_of)
    monitors = []
    for slot in snapshot["slots"]:
        typed = db.execute(
            "SELECT 1 FROM analysis_stage_attempts WHERE execution_id=%s "
            "AND stage_key='sec_monitor_result' AND state='completed'",
            (slot["current_execution_id"],),
        ).fetchone()
        if slot["terminal_outcome"] and typed:
            monitors.append(public_audit(db, slot["request_id"], legacy))
    # Compare historical D4a evidence independently of cumulative application counts.
    original = read_d4a()
    actual = public_audit(db, UUID(original["request_id"]), original["protected_history_sha256"])
    if {k: v for k, v in actual.items() if k != "application_counts"} != {
        k: v for k, v in original.items() if k != "application_counts"
    }:
        raise ValueError("D4a historical evidence changed")
    return {
        "version": "crcl-filing-scheduler-audit-v1",
        "snapshot": snapshot,
        "monitor_audits": monitors,
        "d4a_evidence_verified": True,
        "protected_history_sha256": before,
        "protected_history_verified": True,
        "background_service": "not_configured",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("history", "prepare", "create", "tick", "run-slot", "pause", "resume", "inspect"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--schedule", type=UUID)
    parser.add_argument("--request", type=UUID)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--key")
    parser.add_argument("--epoch", type=int)
    parser.add_argument("--anchor", type=datetime.fromisoformat)
    args = parser.parse_args()
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    if args.action == "prepare":
        if args.anchor is None:
            parser.error("prepare requires explicit aware --anchor")
        write(args.output, reviewed_config(args.anchor).as_json())
        return
    owner = args.action in ("history", "create", "pause", "resume")
    connection = (
        app_postgres.owner_connection(runtime, runtime.database)
        if owner
        else psycopg.connect(
            url.set(drivername="postgresql").render_as_string(hide_password=False),
            autocommit=True,
            row_factory=dict_row,
        )
    )
    with connection as db:
        if args.action == "history":
            report = protected_monitor_history(db)
        elif args.action == "create":
            if not args.config or not args.key:
                parser.error("create requires --config and --key")
            config = ScheduleConfig.from_json(json.loads(args.config.read_text()))
            # The real acceptance CLI is narrower than the generic reviewed internal contract.
            if config != reviewed_config(config.anchor):
                raise ValueError("CRCL tracer config differs from D036")
            ids = registered(db)
            schedule = create_schedule(
                db,
                workspace=ids["workspace"],
                security=ids["security"],
                key=args.key,
                config=config,
                review="D036 coordinator approval; one manual CRCL slot then pause",
            )
            report = schedule_snapshot(db, schedule)
        else:
            if args.schedule is None:
                parser.error("action requires --schedule")
            if args.action in ("pause", "resume"):
                if args.epoch is None or not args.key:
                    parser.error("revision requires --epoch and --key")
                snap = schedule_snapshot(db, args.schedule)
                config = replace(
                    ScheduleConfig.from_json(snap["config"]), active=args.action == "resume"
                )
                revise_schedule(
                    db,
                    args.schedule,
                    epoch=args.epoch,
                    key=args.key,
                    config=config,
                    reason="D036 explicit operator " + args.action,
                )
                report = schedule_snapshot(db, args.schedule)
            elif args.action == "tick":
                report = tick(db, args.schedule)
            elif args.action == "run-slot":
                if args.request is None:
                    parser.error("run-slot requires exact --request from tick")
                slot = db.execute(
                    "SELECT sl.*,r.config FROM filing_schedule_slots sl "
                    "JOIN filing_schedule_revisions r ON r.id=sl.revision_id "
                    "WHERE sl.schedule_id=%s AND sl.request_id=%s",
                    (args.schedule, args.request),
                ).fetchone()
                if slot is None:
                    raise ValueError("Request is not a slot in this schedule")
                contact = contact_from_settings(dotenv_values(ROOT / ".env"))
                cache = app_redis.configuration()
                with cache.client() as client:
                    app_redis.verify(cache, client)
                poll(
                    db,
                    FilingMonitorPlan.from_json(slot["plan"]),
                    slot["request_key"],
                    contact,
                    f"redis://127.0.0.1:{cache.port}/0",
                    max_attempts=slot["config"]["max_attempts"],
                )
                report = tick(db, args.schedule)
            else:
                if args.before is None:
                    parser.error("inspect requires --before protected history")
                with db.transaction():
                    db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    report = audit(db, args.schedule, json.loads(args.before.read_text()))
    write(args.output, report)
    print(
        "Saved scheduler "
        + args.action
        + ". Background service not configured; no financial dispatch."
    )


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        TypeError,
        psycopg.Error,
        RedisError,
        httpx.HTTPError,
    ) as error:
        print(
            f"Scheduler stopped ({type(error).__name__}); inspect saved state/configuration.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
