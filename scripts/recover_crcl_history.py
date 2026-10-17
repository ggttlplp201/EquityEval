"""Read-only recovery of the exact D050 acquisition intent; never dispatches."""

from __future__ import annotations

import copy
import json
from typing import Any
from uuid import UUID

from equity_ingest.archive import ArchiveError, LocalArchive
from equity_schema.workflow import Database

from scripts import bootstrap_crcl as bootstrap
from scripts.capture_crcl_registration import preserved
from scripts.publish_crcl_normalization import rows_snapshot


def reconstruct(db: Database, intent: dict[str, Any], archive: LocalArchive) -> dict[str, Any]:
    from scripts.capture_crcl_history import PREFIX, SCOPE_SHA, checked_scope, group_plan

    if (
        intent.get("scopeSha256") != SCOPE_SHA
        or intent.get("proposal") != "dd2d4a9"
        or intent.get("groups")
        or intent.get("financialPublication") is not False
    ):
        raise ValueError("Recovery intent differs from the original D5l boundary")
    scope = checked_scope()
    identities = {key: UUID(value) for key, value in intent["identities"].items()}
    expected = [group_plan(identities, group).as_json() for group in scope["groups"]]
    if intent.get("plans") != expected:
        raise ValueError("Recovery intent plans differ from the exact reviewed roster")
    report = copy.deepcopy(intent)
    report.update(recoveredReadOnly=True, groups=[], retainedAttemptEvidence=[], archiveFailures=[])
    missing: list[dict[str, Any]] = []
    for group, plan in zip(scope["groups"], expected, strict=True):
        rows = db.execute(
            "SELECT r.id AS request_id,r.request_parameters_hash,r.bootstrap_plan,r.security_id,"
            "r.trigger,r.max_attempts,r.quote_identifier_id,e.id AS execution_id,e.state "
            "FROM analysis_requests r JOIN analysis_executions e ON e.request_id=r.id "
            "WHERE r.workspace_id=%s AND r.idempotency_key=%s ORDER BY e.attempt_no",
            (identities["workspace"], f"{PREFIX}-{group['number']}"),
        ).fetchall()
        if len(rows) > 1:
            raise ValueError("Recovery found an unreviewed retry execution")
        captured = set()
        if rows:
            row = rows[0]
            if (
                row["bootstrap_plan"] != plan
                or row["trigger"] != "source_bootstrap"
                or row["max_attempts"] != 1
                or row["quote_identifier_id"] is not None
                or row["security_id"] != identities["security"]
            ):
                raise ValueError("Recovery request differs from immutable acquisition intent")
            attempts = db.execute(
                "SELECT a.id AS attempt_id,a.state,a.source_object_key,a.completed_capture_id,"
                "a.policy_revision_id,a.response_headers,to_jsonb(c) AS capture "
                "FROM analysis_stage_attempts st JOIN source_fetch_attempts a "
                "ON a.stage_attempt_id=st.id "
                "LEFT JOIN source_captures c ON c.id=a.completed_capture_id "
                "WHERE st.execution_id=%s ORDER BY a.prepared_at,a.id",
                (row["execution_id"],),
            ).fetchall()
            records = []
            for attempt in attempts:
                report["retainedAttemptEvidence"].append({"group": group["number"], **attempt})
                capture = attempt["capture"]
                if capture is None:
                    continue
                try:
                    archive.read_blob(
                        capture["blob_key"], capture["body_sha256"], capture["byte_count"]
                    )
                except (ArchiveError, OSError, TypeError):
                    report["archiveFailures"].append(capture["id"])
                    continue
                record = {
                    **capture,
                    "capture_id": capture["id"],
                    "policy_revision_id": str(attempt["policy_revision_id"]),
                    "etag": attempt["response_headers"].get("etag"),
                    "last_modified": attempt["response_headers"].get("last_modified"),
                }
                del record["id"]
                records.append(record)
                captured.add(capture["source_object_key"])
            result = bootstrap.acquisition_result(db, row["execution_id"])
            gaps = (
                ["acquisition_completion_unavailable"]
                if result is None
                else list(result["readiness"]["blocking_reasons"])
            )
            if result is not None:
                manifest = result["manifest"]
                try:
                    raw = archive.read_blob(
                        manifest["blob_key"], manifest["body_sha256"], manifest["byte_count"]
                    )
                    payload = json.loads(raw)
                    if (
                        payload.get("bootstrap_plan") != plan
                        or payload.get("execution_id") != str(row["execution_id"])
                        or payload.get("request", {}).get("id") != str(row["request_id"])
                    ):
                        gaps.append("acquisition_manifest_identity")
                except (ArchiveError, OSError, ValueError):
                    gaps.append("acquisition_manifest_integrity")
            report["groups"].append(
                {
                    "number": group["number"],
                    "request_id": str(row["request_id"]),
                    "execution_id": str(row["execution_id"]),
                    "request_parameters_hash": row["request_parameters_hash"],
                    "bootstrap_plan": plan,
                    "captures": records,
                    "acquisition_result": result,
                    "result": {"state": row["state"], "gaps": gaps},
                }
            )
        missing.extend(
            {"group": group["number"], "resource": key}
            for key in group["resources"]
            if key not in captured
        )
    report["missingResources"] = missing
    report["afterRows"] = rows_snapshot(db)
    report["originalRowsPreserved"] = preserved(intent["beforeRows"], report["afterRows"])
    complete = (
        len(report["groups"]) == 11
        and not missing
        and not report["archiveFailures"]
        and report["originalRowsPreserved"]
        and all(
            group["result"]["state"] == "completed" and not group["result"]["gaps"]
            for group in report["groups"]
        )
    )
    report["status"] = "captured_pending_review" if complete else "incomplete"
    return report
