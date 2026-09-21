"""Bounded SEC filing discovery over reviewed immutable predecessors and W1 leases."""

import hashlib
import json
from dataclasses import asdict, fields
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from equity_ingest.archive import ArchiveError, LocalArchive
from equity_ingest.contracts import FetchRequest, RawRecord, ResourceKind, SecResource
from equity_ingest.filing_monitor import compare_inventories
from equity_ingest.sec import SecSource
from equity_ingest.sec_inventory import (
    FilingInventory,
    SubmissionDocument,
    assemble_inventory,
    parse_submissions,
)
from equity_schema.filing_monitor import MONITOR_RESULT_VERSION, FilingMonitorPlan, timestamp
from equity_schema.ingestion import recover_interrupted_attempt
from equity_schema.workflow import (
    Database,
    Lease,
    LeaseLost,
    complete_filing_monitor,
    finish_execution,
    finish_stage,
    renew_lease,
    start_stage,
)
from psycopg.types.json import Jsonb


def load_record(db: Database, capture_id: UUID) -> RawRecord:
    """Load original representation and its original HTTP validators, never new timestamps."""
    row = db.execute(
        "SELECT c.*,c.id AS capture_id,l.policy_revision_id,a.response_headers "
        "FROM source_captures c JOIN capture_policy_links l ON l.capture_id=c.id "
        "JOIN source_fetch_attempts a ON a.completed_capture_id=c.id AND a.state='complete' "
        "WHERE c.id=%s",
        (capture_id,),
    ).fetchone()
    if row is None:
        raise ArchiveError("Monitor representation lacks original successful attempt")
    headers = row["response_headers"] or {}
    row.update(etag=headers.get("etag"), last_modified=headers.get("last_modified"))
    record = RawRecord(**{f.name: row[f.name] for f in fields(RawRecord)})
    # Constructed from one immutable DB row; transport independently validates live reuse.
    return record


def saved_result(db: Database, execution_id: UUID) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT result_reference FROM analysis_stage_attempts WHERE execution_id=%s "
        "AND stage_key='sec_monitor_result' AND state='completed'",
        (execution_id,),
    ).fetchone()
    return json.loads(row["result_reference"]) if row else None


def _baseline(
    db: Database, archive: LocalArchive, plan: FilingMonitorPlan, security: UUID
) -> tuple[dict[str, Any], tuple[RawRecord, ...]]:
    baseline_row = db.execute(
        "SELECT workflow_monitor_baseline(%s,%s) AS value", (Jsonb(plan.as_json()), security)
    ).fetchone()
    assert baseline_row is not None
    lineage = baseline_row["value"]
    key = "sec_bootstrap_manifest" if plan.baseline.kind == "initial_seed" else "sec_monitor_result"
    row = db.execute(
        "SELECT result_reference FROM analysis_stage_attempts WHERE execution_id=%s "
        "AND stage_key=%s AND state='completed'",
        (plan.baseline.execution_id, key),
    ).fetchone()
    assert row is not None
    result = json.loads(row["result_reference"])
    manifest = result["manifest"]
    body = json.loads(
        archive.read_blob(
            manifest["blob_key"], plan.baseline.manifest_sha256, manifest["byte_count"]
        )
    )
    if plan.baseline.kind == "initial_seed":
        if (
            body.get("execution_id") != str(plan.baseline.execution_id)
            or body.get("request", {}).get("id") != str(plan.baseline.request_id)
            or body.get("readiness") != result["readiness"]
        ):
            raise ArchiveError("Seed archive differs from approved predecessor")
    elif body != {
        "request_id": str(plan.baseline.request_id),
        "execution_id": str(plan.baseline.execution_id),
        "result": {k: v for k, v in result.items() if k != "manifest"},
    }:
        raise ArchiveError("Prior monitor archive differs from pinned result")
    return lineage, tuple(load_record(db, UUID(c)) for c in lineage["capture_ids"])


def _parse(archive: LocalArchive, record: RawRecord, plan: FilingMonitorPlan) -> SubmissionDocument:
    key = record.source_object_key
    if record.source_id != plan.source_id or record.policy_revision_id != plan.policy_revision_id:
        raise ArchiveError("Monitor capture policy differs from pinned intent")
    return parse_submissions(
        archive.read_blob(record.blob_key, record.body_sha256, record.byte_count),
        expected_cik=plan.cik,
        capture_id=record.capture_id,
        document_name=key.rsplit("/", 1)[1] if key.startswith("submissions_history/") else None,
    )


def history_scope(root: SubmissionDocument, plan: FilingMonitorPlan) -> dict[str, list[str]]:
    required: list[str] = []
    excluded: list[str] = []
    for doc in root.older_documents:
        target = (
            required
            if doc.filing_from <= plan.inventory_end and doc.filing_to >= plan.inventory_start
            else excluded
        )
        target.append(f"submissions_history/{plan.cik}/{doc.name}")
    return {"required": sorted(required), "excluded_nonoverlap": sorted(excluded)}


def _inventory(
    archive: LocalArchive, records: tuple[RawRecord, ...], plan: FilingMonitorPlan
) -> tuple[FilingInventory, dict[str, list[str]]]:
    by_key = {r.source_object_key: r for r in records}
    if len(by_key) != len(records) or f"submissions/{plan.cik}" not in by_key:
        raise ValueError("Missing or ambiguous Submissions root")
    root = _parse(archive, by_key[f"submissions/{plan.cik}"], plan)
    history = history_scope(root, plan)
    older = tuple(
        _parse(archive, by_key[key], plan) for key in history["required"] if key in by_key
    )
    inventory = assemble_inventory(
        root, older, boundary_start=plan.inventory_start, boundary_end=plan.inventory_end
    )
    return inventory, history


def run_filing_monitor(
    db: Database, lease: Lease, source: SecSource, archive: LocalArchive, plan: FilingMonitorPlan
) -> dict[str, Any]:
    """One pinned logical poll. No scheduling, normalization, registration or dispatch."""
    if db.info.transaction_status.name != "IDLE":
        raise ValueError("Monitor requires an idle database connection")
    row = db.execute("SELECT * FROM analysis_requests WHERE id=%s", (lease.request_id,)).fetchone()
    if (
        row is None
        or row["trigger"] != "sec_filing_monitor"
        or row["filing_monitor_plan"] != plan.as_json()
        or source.descriptor.source_id != plan.source_id
        or source.descriptor.policy_revision_id != plan.policy_revision_id
    ):
        raise ValueError("Monitor runtime differs from pinned request")
    lease = renew_lease(db, lease, lease_seconds=360)
    abandoned = db.execute(
        "SELECT a.id FROM source_fetch_attempts a "
        "JOIN analysis_stage_attempts s ON s.id=a.stage_attempt_id "
        "JOIN analysis_executions e ON e.id=s.execution_id WHERE e.request_id=%s AND e.id<>%s "
        "AND a.state IN ('prepared','in_progress')",
        (lease.request_id, lease.execution_id),
    ).fetchall()
    for attempt in abandoned:
        recover_interrupted_attempt(db, attempt["id"])
    # Completion can be retried after a crash between typed result and execution finalization.
    existing = saved_result(db, lease.execution_id)
    if existing is not None:
        descriptor = existing["manifest"]
        archived = json.loads(
            archive.read_blob(
                descriptor["blob_key"], descriptor["body_sha256"], descriptor["byte_count"]
            )
        )
        if archived != {
            "request_id": str(lease.request_id),
            "execution_id": str(lease.execution_id),
            "result": {k: v for k, v in existing.items() if k != "manifest"},
        }:
            raise ArchiveError("Saved completion differs from immutable run manifest")
        _finish(db, lease, existing)
        return existing
    baseline_row = db.execute(
        "SELECT workflow_monitor_baseline(%s,%s) AS value",
        (Jsonb(plan.as_json()), row["security_id"]),
    ).fetchone()
    assert baseline_row is not None
    lineage = baseline_row["value"]
    baseline_records: tuple[RawRecord, ...] = ()
    current: dict[str, RawRecord] = {}
    flags: list[str] = []
    histories: dict[str, Any] = {"baseline": None, "current": None}
    coverage = {"baseline": "incomplete", "current": "incomplete"}
    comparison: dict[str, Any] = {
        "outcome": "incomplete",
        "baseline_eligible": False,
        "flags": [],
        "new_filings": [],
        "amendments": [],
        "metadata_changes": [],
        "missing_accessions": [],
        "baseline_filings": [],
        "current_filings": [],
        "excluded_after_cutoff": {"baseline": [], "current": []},
        "amendment_meaning": "Separate filing edition; no restatement or non-reliance inference",
    }
    failed = False

    def fetch(key: str) -> RawRecord | None:
        nonlocal lease, failed
        lease = renew_lease(db, lease, lease_seconds=360)
        parts = key.split("/")
        resource = SecResource(
            plan.issuer_id,
            plan.cik,
            ResourceKind(parts[0]),
            filename=parts[2] if len(parts) == 3 else None,
        )
        # A retry of this logical request keeps the first successful observation.
        prior = db.execute(
            "SELECT coalesce(a.completed_capture_id,a.reused_capture_id) AS id FROM "
            "source_fetch_attempts a "
            "JOIN analysis_stage_attempts s ON s.id=a.stage_attempt_id JOIN "
            "analysis_executions e ON e.id=s.execution_id "
            "WHERE e.request_id=%s AND a.source_object_key=%s AND a.state IN "
            "('complete','not_modified','content_unchanged') "
            "ORDER BY a.finished_at,a.id LIMIT 1",
            (lease.request_id, key),
        ).fetchone()
        pinned = load_record(db, prior["id"]) if prior else None
        cached = next((r for r in baseline_records if r.source_object_key == key), None)
        stage = start_stage(
            db, lease, stage_key="sec_fetch_" + hashlib.sha256(key.encode()).hexdigest()[:24]
        )
        result = source.fetch(
            FetchRequest(
                uuid4(),
                resource,
                lease,
                stage,
                cache_mode="replay" if pinned else "conditional",
                cached_record=None if pinned else cached,
                replay_records=(pinned,) if pinned else (),
                monitor_payload=pinned is None,
            )
        )
        if "lease_lost" in result.gaps:
            raise LeaseLost("Monitor lease lost during acquisition")
        usable = (
            result.usable
            and len(result.successful_records) == 1
            and result.successful_records[0].http_status == 200
        )
        finish_stage(
            db,
            lease,
            stage_id=stage,
            outcome="completed" if usable else "blocked",
            reason=None if usable else "monitor_source_unavailable",
            reused_capture_ids=result.reused_capture_ids if usable else (),
        )
        if not usable:
            flags.extend(result.gaps or ("source_unavailable",))
            failed = True
            return None
        record = result.successful_records[0]
        current[key] = record
        return record

    try:
        lineage, baseline_records = _baseline(db, archive, plan, row["security_id"])
        old, histories["baseline"] = _inventory(archive, baseline_records, plan)
        coverage["baseline"] = old.completeness
        if len(histories["baseline"]["required"]) > 10:
            flags.append("baseline_history_limit_exceeded")
        baseline_check = compare_inventories(old, old, plan)
        # Both selections here share the old payload. Only baseline-side flags apply.
        flags.extend(f for f in baseline_check["flags"] if f.startswith("baseline"))
        if not flags:
            root_record = fetch(f"submissions/{plan.cik}")
            if root_record:
                try:
                    root = _parse(archive, root_record, plan)
                except (ValueError, KeyError, TypeError):
                    flags.append("current_submissions_invalid")
                else:
                    histories["current"] = history_scope(root, plan)
                    required = histories["current"]["required"]
                    if len(required) > 10:
                        flags.append("history_limit_exceeded")
                    else:
                        for key in required:
                            if key not in plan.resources:
                                flags.append("unplanned_overlapping_history")
                            else:
                                fetch(key)
                    try:
                        new, _ = _inventory(archive, tuple(current.values()), plan)
                    except (ValueError, KeyError, TypeError):
                        flags.append("current_submissions_invalid")
                    else:
                        coverage["current"] = new.completeness
                        comparison = compare_inventories(old, new, plan)
        else:
            comparison["baseline_filings"] = baseline_check["baseline_filings"]
    except ArchiveError:
        flags.append("archive_verification_failed")
        failed = True
    except (ValueError, KeyError, TypeError):
        flags.append("baseline_submissions_invalid")
    if flags or failed:
        comparison.update(
            outcome="error" if failed else "incomplete",
            baseline_eligible=False,
            flags=sorted(set(comparison["flags"]) | set(flags)),
        )
    checked_row = db.execute(
        "SELECT max(a.finished_at) AS checked FROM source_fetch_attempts a JOIN "
        "analysis_stage_attempts s ON s.id=a.stage_attempt_id "
        "JOIN analysis_executions e ON e.id=s.execution_id WHERE e.request_id=%s",
        (lease.request_id,),
    ).fetchone()
    assert checked_row is not None
    checked = checked_row["checked"]
    blockers = ["handoff_not_implemented", "financial_coverage_not_reviewed"]
    if not db.execute(
        "SELECT 1 FROM security_identifiers WHERE security_id=%s LIMIT 1", (row["security_id"],)
    ).fetchone():
        blockers.append("quote_registration_missing")
    result = {
        "version": MONITOR_RESULT_VERSION,
        "manifest_id": str(uuid4()),
        "plan": plan.as_json(),
        "outcome": comparison["outcome"],
        "baseline_eligible": comparison["baseline_eligible"],
        "baseline_capture_ids": lineage["capture_ids"],
        "current_capture_ids": sorted(str(r.capture_id) for r in current.values()),
        "checked_at": timestamp(checked) if checked else None,
        "coverage": coverage,
        "history": histories,
        "comparison": comparison,
        "known_limits": (
            "Advertised Submissions documents within the pinned filed window; acceptance "
            "metadata is not proof of historical public availability. "
            "No event or accounting restatement review."
        ),
        "downstream": {"dispatched": False, "blockers": blockers},
    }
    payload = json.dumps(
        {
            "request_id": str(lease.request_id),
            "execution_id": str(lease.execution_id),
            "result": result,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    manifest = archive.write(
        (payload,),
        source_key="filing-monitor",
        source_object_key=str(lease.execution_id),
        params_hash=hashlib.sha256(payload).hexdigest(),
        capture_id=UUID(result["manifest_id"]),
        retrieved_at=datetime.now(UTC),
        max_bytes=64 * 1024 * 1024,
    )
    archive.read(manifest)
    result["manifest"] = asdict(manifest)
    lease = renew_lease(db, lease, lease_seconds=360)
    stage = start_stage(db, lease, stage_key="sec_monitor_result")
    complete_filing_monitor(db, lease, stage_id=stage, result=result)
    _finish(db, lease, result)
    return result


def _finish(db: Database, lease: Lease, result: dict[str, Any]) -> None:
    if result["outcome"] == "error":
        finish_execution(db, lease, outcome="failed", reason="monitor_source_error")
    else:
        finish_execution(
            db, lease, outcome="completed" if result["baseline_eligible"] else "completed_with_gaps"
        )
