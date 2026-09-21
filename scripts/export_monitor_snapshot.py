"""Project the pinned D4a real monitor audit into a sanitized saved UI snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from scripts.export_pipeline_snapshot import ROOT, source_url, utc_label

AUDIT = "docs/research/crcl-filing-monitor-2026-09-21.json"
AUDIT_SHA256 = "ee1074c19265159a08abe95bf8a6795b2c6090bacbccf8875e34b0a6ee577794"
OUTPUT = "apps/web/src/features/pipeline/monitorSnapshot.ts"


def project(audit: dict[str, Any]) -> dict[str, Any]:
    result = audit["result"]
    if (
        audit["version"] != "crcl-filing-monitor-audit-v1"
        or result["version"] != "sec-filing-monitor-result-v1"
        or audit["protected_history_verified"] is not True
        or result["downstream"]["dispatched"] is not False
        or audit["scheduler"] != "not_configured"
    ):
        raise ValueError("Monitor projection requires the reviewed no-dispatch audit")
    plan = result["plan"]
    comparison = result["comparison"]
    captures = {r["capture_id"]: r for r in audit["captures"]}
    labels = {
        "no_change": "No new scoped filings",
        "new_filing": "New filing detected",
        "amendment": "Amendment detected",
        "mixed_changes": "Filings and amendments detected",
        "incomplete": "Incomplete check",
        "error": "Check failed",
    }

    def observation(row: dict[str, Any]) -> dict[str, Any]:
        capture = captures[row["capture_id"]]
        return {
            "accession": row["accession"],
            "form": row["form"],
            "filedDate": row["filed_date"],
            "reportDate": row["report_date"],
            "acceptanceAt": utc_label(row["acceptance_at"]),
            "sourceLocator": row["source_locator"],
            "captureId": row["capture_id"],
            "capturedAt": utc_label(capture["completed_at"]),
            "url": source_url(capture["request_url"]),
            "sha256": capture["body_sha256"],
        }

    return {
        "kind": "real-filing-monitor-snapshot",
        "outcome": result["outcome"],
        "outcomeLabel": labels[result["outcome"]],
        "baselineEligible": result["baseline_eligible"],
        "checkedAt": utc_label(result["checked_at"]) if result["checked_at"] else None,
        "requestId": audit["request_id"],
        "executionId": audit["execution_id"],
        "requestSha256": audit["request_parameters_hash"],
        "auditSha256": AUDIT_SHA256,
        "manifestSha256": result["manifest"]["body_sha256"],
        "baseline": {
            "kind": plan["baseline"]["kind"],
            "requestId": plan["baseline"]["request_id"],
            "executionId": plan["baseline"]["execution_id"],
            "cutoff": utc_label(plan["baseline"]["cutoff"]),
            "manifestSha256": plan["baseline"]["manifest_sha256"],
            "captureIds": result["baseline_capture_ids"],
        },
        "cutoff": utc_label(plan["cutoff"]),
        "filedStart": plan["inventory_start"],
        "filedEnd": plan["inventory_end"],
        "forms": plan["forms"],
        "coverage": {key: result["coverage"][key] for key in ("baseline", "current")},
        "flags": comparison["flags"],
        "newFilings": [observation(r) for r in comparison["new_filings"]],
        "amendments": [observation(r) for r in comparison["amendments"]],
        "filings": [observation(r) for r in comparison["current_filings"]],
        "filingCount": len(comparison["current_filings"]),
        "newCount": len(comparison["new_filings"]),
        "amendmentCount": len(comparison["amendments"]),
        "blockers": result["downstream"]["blockers"],
        "knownLimits": result["known_limits"],
        "history": {
            side: {key: result["history"][side][key] for key in ("required", "excluded_nonoverlap")}
            if result["history"][side] is not None
            else None
            for side in ("baseline", "current")
        },
        "amendmentMeaning": comparison["amendment_meaning"],
        "attempts": [
            {
                "id": a["attempt_id"],
                "status": a["http_status"],
                "state": a["state"],
                "requestedAt": utc_label(a["requested_at"]) if a["requested_at"] else None,
                "finishedAt": utc_label(a["finished_at"]) if a["finished_at"] else None,
                "reusedCaptureId": a["reused_capture_id"],
                "payloadSha256": a["payload"]["sha256"] if a["payload"] else None,
                "payloadBytes": a["payload"]["bytes"] if a["payload"] else None,
            }
            for a in audit["attempts"]
        ],
        "counts": [
            {"id": key, "label": label, "value": audit["application_counts"].get(key, 0)}
            for key, label in (
                ("source_bootstrap", "Acquisition requests"),
                ("sec_filing_monitor", "Filing checks"),
                ("source_captures", "Logical captures"),
                ("source_fetch_attempts", "Fetch attempts"),
                ("source_attempt_payloads", "Retained monitor bodies"),
                ("normalization_batches", "Normalization batches"),
            )
        ],
    }


def read_audit(root: Path = ROOT) -> dict[str, Any]:
    body = (root / AUDIT).read_bytes()
    if hashlib.sha256(body).hexdigest() != AUDIT_SHA256:
        raise ValueError("D4a audit changed; review before exporting")
    result: dict[str, Any] = json.loads(body)
    return result


def verify_application() -> None:
    from scripts import app_postgres
    from scripts.monitor_crcl_filings import public_audit

    expected = read_audit()
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as db, db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        actual = public_audit(
            db, UUID(expected["request_id"]), expected["protected_history_sha256"]
        )
    if actual != expected:
        raise ValueError("Application monitor audit differs from pinned saved state")


def export(root: Path = ROOT) -> str:
    result = project(read_audit(root))
    return (
        "// Generated by scripts/export_monitor_snapshot.py; saved real check, no live polling.\n"
        'import type { MonitorSnapshot } from "./monitorTypes";\n\nconst snapshot = '
        + json.dumps(result, indent=2, ensure_ascii=False)
        + " satisfies MonitorSnapshot;\n\nexport default snapshot;\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-application", action="store_true")
    args = parser.parse_args()
    rendered = export()
    if args.verify_application:
        try:
            verify_application()
        except Exception as error:
            raise SystemExit(f"Monitor verification failed ({type(error).__name__}).") from None
    path = ROOT / OUTPUT
    if args.check:
        if path.read_text() != rendered:
            raise SystemExit("Monitor snapshot differs from reviewed audit")
    else:
        path.write_text(rendered)


if __name__ == "__main__":
    main()
