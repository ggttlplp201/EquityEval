"""Allowlisted saved D4b status. No network/database access unless explicitly verified."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from scripts.review_crcl_identity import ROOT

AUDIT = "docs/research/crcl-filing-scheduler-2026-09-21.json"
AUDIT_SHA256 = "1b1ddb429521ab8c2593c69b0b6994c61b0c978aa5cfdb96f002bfd92a3859c2"
OUTPUT = "apps/web/src/features/pipeline/schedulerSnapshot.ts"


def read_audit(root: Path = ROOT) -> dict[str, Any]:
    body = (root / AUDIT).read_bytes()
    if hashlib.sha256(body).hexdigest() != AUDIT_SHA256:
        raise ValueError("Scheduler audit differs from reviewed evidence")
    result: dict[str, Any] = json.loads(body)
    return result


def project(audit: dict[str, Any]) -> dict[str, Any]:
    s = audit["snapshot"]
    c = s["config"]
    monitors = audit["monitor_audits"]
    if (
        audit["version"] != "crcl-filing-scheduler-audit-v1"
        or audit["protected_history_verified"] is not True
        or audit["d4a_evidence_verified"] is not True
        or s["version"] != "sec-filing-scheduler-snapshot-v1"
        or audit["background_service"] != "not_configured"
        or any(m["result"]["downstream"]["dispatched"] is not False for m in monitors)
        or s["service"] != "not_configured"
        or s["downstream_dispatched"] is not False
    ):
        raise ValueError("Scheduler UI requires verified saved manual evidence")
    outcomes = {m["request_id"]: m for m in monitors}
    labels = {
        "no_change": "No new scoped filings",
        "new_filing": "New filing detected",
        "amendment": "Amendment detected",
        "mixed_changes": "Filings and amendments detected",
        "incomplete": "Incomplete check",
        "error": "Check failed",
    }
    slots = []
    for sl in s["slots"]:
        evidence = outcomes.get(sl["request_id"])
        result = evidence["result"] if evidence else None
        slots.append(
            {
                "index": sl["slot_index"],
                "requestId": sl["request_id"],
                "executionId": sl["current_execution_id"],
                "nominalAt": sl["nominal_at"],
                "dueAt": sl["due_at"],
                "state": sl["state"],
                "availableAt": sl["available_at"],
                "attemptNumber": sl["attempt_no"],
                "outcome": result["outcome"] if result else None,
                "outcomeLabel": labels[result["outcome"]]
                if result
                else "No completed filing comparison",
                "checkedAt": result["checked_at"] if result else None,
                "eligible": result["baseline_eligible"] if result else False,
                "manifestSha256": result["manifest"]["body_sha256"] if result else None,
                "planSha256": sl["plan_hash"],
                "baselineRequestId": sl["plan"]["baseline"]["request_id"],
                "baselineManifestSha256": sl["plan"]["baseline"]["manifest_sha256"],
                "filings": len(result["comparison"]["current_filings"]) if result else None,
                "newFilings": len(result["comparison"]["new_filings"]) if result else None,
                "amendments": len(result["comparison"]["amendments"]) if result else None,
                "coverage": {k: result["coverage"][k] for k in ("baseline", "current")}
                if result
                else None,
            }
        )
    counts = monitors[-1]["application_counts"] if monitors else {}
    return {
        "kind": "real-filing-scheduler-snapshot",
        "asOf": s["as_of"],
        "auditSha256": AUDIT_SHA256,
        "scheduleId": s["schedule_id"],
        "revisionId": s["revision_id"],
        "epoch": s["epoch"],
        "configSha256": s["config_sha256"],
        "active": c["active"],
        "health": s["health"],
        "service": "not_configured",
        "healthMeaning": s["health_meaning"],
        "reasons": s["reasons"],
        "filedStart": c["plan"]["inventory_start"],
        "filedEnd": c["plan"]["inventory_end"],
        "cadenceSeconds": c["cadence_seconds"],
        "jitterSeconds": c["jitter_seconds"],
        "budgetUnits": c["budget_units"],
        "reservedUnits": s["reserved_units"],
        "actualAttempts": s["actual_attempts"],
        "lastTickAt": s["last_tick_at"],
        "lastHttpCompletedAt": s["last_http_completed_at"],
        "lastSuccessAt": s["last_success_at"],
        "lastSuccessCutoff": s["last_success_cutoff"],
        "nextDueAt": s["next_due_at"],
        "nextDueActionable": s["next_due_actionable"],
        "lagSeconds": s["lag_seconds"],
        "retryAt": s["retry_at"],
        "failures": s["consecutive_failures"],
        "missedIntervals": [
            {k: r[k] for k in ("first", "last", "count", "reason")} for r in s["missed_intervals"]
        ],
        "slots": slots,
        "attempts": [
            {
                "id": a["id"],
                "state": a["state"],
                "status": a["http_status"],
                "requestedAt": a["requested_at"],
                "finishedAt": a["finished_at"],
                "payloadSha256": a["body_sha256"],
                "payloadBytes": a["byte_count"],
                "reusedCaptureId": a["reused_capture_id"],
            }
            for a in s["attempts"]
        ],
        "revisions": [
            {
                "epoch": r["epoch"],
                "at": r["created_at"],
                "active": r["config"]["active"],
                "reason": r["reason"],
                "configSha256": r["config_hash"],
            }
            for r in s["revisions"]
        ],
        "events": [
            {"kind": e["kind"], "at": e["at"], "key": e["semantic_key"]} for e in s["events"]
        ],
        "counts": [
            {"id": k, "value": v}
            for k, v in sorted(counts.items())
            if k
            in {
                "source_captures",
                "source_fetch_attempts",
                "source_attempt_payloads",
                "source_bootstrap",
                "sec_filing_monitor",
                "security_identifiers",
                "watchlist_memberships",
                "normalization_batches",
                "watchlist_add",
                "manual_refresh",
            }
        ],
    }


def export(root: Path = ROOT) -> str:
    return (
        "// Generated by scripts/export_scheduler_snapshot.py; saved manual state.\n"
        'import type { SchedulerSnapshot } from "./schedulerTypes";\n\nconst snapshot = '
        + json.dumps(project(read_audit(root)), indent=2, ensure_ascii=False)
        + " satisfies SchedulerSnapshot;\n\nexport default snapshot;\n"
    )


def verify_application(expected: dict[str, Any]) -> None:
    from scripts import app_postgres
    from scripts.schedule_crcl_filings import audit, json_safe

    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as db, db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        actual = audit(
            db,
            UUID(expected["snapshot"]["schedule_id"]),
            expected["protected_history_sha256"],
            as_of=datetime.fromisoformat(expected["snapshot"]["as_of"]),
        )
    if json.loads(json.dumps(actual, default=json_safe)) != expected:
        raise ValueError("Application schedule/evidence differs from saved checkpoint")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-application", action="store_true")
    args = parser.parse_args()
    rendered = export()
    if args.verify_application:
        try:
            verify_application(read_audit())
        except Exception as error:
            raise SystemExit(f"Scheduler verification failed ({type(error).__name__}).") from None
    if args.check:
        if (ROOT / OUTPUT).read_text() != rendered:
            raise ValueError("Scheduler projection differs")
    else:
        (ROOT / OUTPUT).write_text(rendered)


if __name__ == "__main__":
    main()
