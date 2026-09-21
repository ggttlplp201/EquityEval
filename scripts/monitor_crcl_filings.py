"""D035 one-shot CRCL filing poll. Explicit pinned plan/key; no background scheduler.

Run as python -m scripts.monitor_crcl_filings. Public audit output excludes raw paths,
contact details and credentials. Seed registration is the approved D3c lineage only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
import psycopg
from dotenv import dotenv_values
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import ResourceKind, SourceDescriptor
from equity_ingest.limiter import RedisRateLimiter
from equity_ingest.monitor_pipeline import load_record, run_filing_monitor, saved_result
from equity_ingest.sec import SecSource
from equity_ingest.transport import DatabaseAttemptStore, SecTransport
from equity_schema.filing_monitor import FORMS, FilingMonitorPlan, MonitorBaseline, timestamp
from equity_schema.workflow import Database, claim_filing_monitor, enqueue_filing_monitor
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from redis.exceptions import RedisError

from scripts import app_postgres, app_redis
from scripts.bootstrap_crcl import (
    LICENCE,
    POLICY_KEY,
    SOURCE_KEY,
    contact_from_settings,
    registered,
)
from scripts.review_crcl_identity import (
    AUDIT_SHA256,
    ROOT,
    TABLES,
    read_audit,
    review_bodies,
    verify_database_evidence,
)


def protected_history(db: Database) -> dict[str, list[str]]:
    """Hash individual preexisting rows without exposing their source paths or contacts."""
    return {
        table: [
            r["sha"]
            for r in db.execute(
                sql.SQL(
                    "SELECT "
                    "encode(sha256(convert_to((to_jsonb(t)-'filing_monitor_plan')::text,"
                    "'UTF8')),'hex') AS sha "
                    "FROM {} t ORDER BY sha"
                ).format(sql.Identifier(table))
            )
        ]
        for table in TABLES
    }


def verify_history(db: Database, before: dict[str, list[str]]) -> None:
    if set(before) != set(TABLES):
        raise ValueError("Protected history must include all checkpoint tables")
    after = protected_history(db)
    for table in TABLES:
        if Counter(before[table]) - Counter(after[table]):
            raise ValueError("Previously saved application evidence changed: " + table)


def register_seed(db: Database, cutoff: datetime) -> FilingMonitorPlan:
    audit = read_audit(ROOT)
    ids = registered(db)
    identity_id = UUID(audit["acquisition_result"]["readiness"]["identity_capture_id"])
    capture = load_record(db, identity_id)
    archive = LocalArchive(ROOT / "var/raw")
    archive.read_blob(capture.blob_key, capture.body_sha256, capture.byte_count)
    result = audit["acquisition_result"]
    manifest = result["manifest"]
    archive.read_blob(manifest["blob_key"], manifest["body_sha256"], manifest["byte_count"])
    actual = db.execute(
        "SELECT result_reference FROM analysis_stage_attempts WHERE "
        "execution_id=%s AND stage_key='sec_bootstrap_manifest' AND state='completed'",
        (UUID(audit["execution_id"]),),
    ).fetchone()
    if actual is None or json.loads(actual["result_reference"]) != result:
        raise ValueError("Approved D3c result changed")
    # This deterministic approval names exactly one reviewed seed, independent of poll time.
    seed = uuid5(NAMESPACE_URL, "equityeval:D035:" + audit["request_id"])
    plan = FilingMonitorPlan(
        ids["issuer"],
        "0001876042",
        ids["source"],
        ids["policy"],
        date(2025, 1, 1),
        date(2026, 9, 21),
        cutoff,
        tuple(FORMS),
        ("submissions/0001876042",),
        MonitorBaseline(
            "initial_seed",
            UUID(audit["request_id"]),
            UUID(audit["execution_id"]),
            manifest["body_sha256"],
            capture.requested_at,
            seed_approval_id=seed,
            plan_sha256=audit["request_parameters_hash"],
            capture_id=identity_id,
        ),
    )
    scope = {
        k: v for k, v in plan.as_json().items() if k not in ("baseline", "cutoff", "resources")
    }
    with db.transaction():
        db.execute(
            "INSERT INTO filing_monitor_seed_approvals(id,security_id,request_id,"
            "execution_id,request_parameters_hash,manifest_sha256,capture_id,"
            "cutoff,scope,review_reference,review_sha256) VALUES(%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING",
            (
                seed,
                ids["security"],
                UUID(audit["request_id"]),
                UUID(audit["execution_id"]),
                audit["request_parameters_hash"],
                manifest["body_sha256"],
                identity_id,
                capture.requested_at,
                Jsonb(scope),
                "D035 delegated approval; exact pinned D3c audit",
                AUDIT_SHA256,
            ),
        )
        db.execute(
            "SELECT workflow_monitor_baseline(%s,%s)", (Jsonb(plan.as_json()), ids["security"])
        )
    return plan


def poll(
    db: Database,
    plan: FilingMonitorPlan,
    key: str,
    contact: str,
    redis_url: str,
    *,
    max_attempts: int = 3,
) -> tuple[UUID, UUID]:
    ids = registered(db)
    request = enqueue_filing_monitor(
        db,
        workspace_id=ids["workspace"],
        security_id=ids["security"],
        idempotency_key=key,
        plan=plan,
        max_attempts=max_attempts,
    )
    lease = claim_filing_monitor(
        db, worker_id="crcl-filing-monitor-cli", request_id=request.request_id
    )
    if lease is None:
        row = db.execute(
            "SELECT current_execution_id FROM analysis_request_state WHERE request_id=%s",
            (request.request_id,),
        ).fetchone()
        assert row is not None
        return request.request_id, row["current_execution_id"]
    descriptor = SourceDescriptor(
        ids["source"],
        SOURCE_KEY,
        "SEC EDGAR public filings",
        ids["policy"],
        POLICY_KEY,
        LICENCE,
        "allowed",
        tuple(ResourceKind),
        timedelta(minutes=15),
    )
    archive = LocalArchive(ROOT / "var/raw")
    limiter = RedisRateLimiter.from_url(redis_url)
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            source = SecSource(
                descriptor,
                SecTransport(
                    descriptor,
                    archive,
                    limiter,
                    DatabaseAttemptStore(db, descriptor),
                    client,
                    contact,
                ),
                archive,
            )
            run_filing_monitor(db, lease, source, archive, plan)
    finally:
        limiter.client.close()
    return request.request_id, lease.execution_id


def request_status(db: Database, request_id: UUID) -> dict[str, Any]:
    row = db.execute(
        "SELECT r.request_parameters_hash,s.current_execution_id,s.terminal_outcome,e.state "
        "FROM analysis_requests r JOIN analysis_request_state s ON s.request_id=r.id "
        "JOIN analysis_executions e ON e.id=s.current_execution_id "
        "WHERE r.id=%s AND r.trigger='sec_filing_monitor'",
        (request_id,),
    ).fetchone()
    if row is None:
        raise ValueError("Unknown monitor request")
    return {
        "version": "crcl-filing-monitor-status-v1",
        "request_id": str(request_id),
        "execution_id": str(row["current_execution_id"]),
        "execution_state": row["state"],
        "terminal_outcome": row["terminal_outcome"],
        "request_parameters_hash": row["request_parameters_hash"],
        "typed_result_available": saved_result(db, row["current_execution_id"]) is not None,
        "downstream_dispatched": False,
    }


def public_audit(db: Database, request_id: UUID, before: dict[str, list[str]]) -> dict[str, Any]:
    verify_history(db, before)
    original_audit = read_audit(ROOT)
    original_archive = LocalArchive(ROOT / "var/raw")
    verify_database_evidence(db, original_audit, original_archive)
    review_bodies(original_audit, original_archive)
    row = db.execute(
        "SELECT r.filing_monitor_plan,r.request_parameters_hash,"
        "s.current_execution_id,s.terminal_outcome "
        "FROM analysis_requests r JOIN analysis_request_state s ON s.request_id=r.id "
        "WHERE r.id=%s AND r.trigger='sec_filing_monitor'",
        (request_id,),
    ).fetchone()
    if row is None or row["terminal_outcome"] is None:
        raise ValueError("Monitor has not reached an auditable terminal result")
    result = saved_result(db, row["current_execution_id"])
    if result is None:
        raise ValueError("No typed monitor result is available")
    archive = LocalArchive(ROOT / "var/raw")
    manifest = result["manifest"]
    body = json.loads(
        archive.read_blob(manifest["blob_key"], manifest["body_sha256"], manifest["byte_count"])
    )
    if body != {
        "request_id": str(request_id),
        "execution_id": str(row["current_execution_id"]),
        "result": {k: v for k, v in result.items() if k != "manifest"},
    }:
        raise ValueError("Result differs from immutable run manifest")
    captures = []
    for key in sorted(set(result["baseline_capture_ids"] + result["current_capture_ids"])):
        record = load_record(db, UUID(key))
        archive.read_blob(record.blob_key, record.body_sha256, record.byte_count)
        captures.append(
            {
                k: str(v) if isinstance(v, UUID) else timestamp(v) if isinstance(v, datetime) else v
                for k, v in asdict(record).items()
                if k not in ("blob_key", "etag", "last_modified")
            }
        )
    attempts = []
    for item in db.execute(
        "SELECT a.*,p.fetched_at AS payload_at,p.body_sha256 AS payload_sha,"
        "p.byte_count AS payload_bytes,p.blob_key AS payload_blob "
        "FROM source_fetch_attempts a JOIN analysis_stage_attempts s ON s.id=a.stage_attempt_id "
        "JOIN analysis_executions e ON e.id=s.execution_id LEFT JOIN "
        "source_attempt_payloads p ON p.attempt_id=a.id "
        "WHERE e.request_id=%s ORDER BY a.requested_at,a.id",
        (request_id,),
    ):
        if item["payload_blob"]:
            archive.read_blob(item["payload_blob"], item["payload_sha"], item["payload_bytes"])
        attempts.append(
            {
                "attempt_id": str(item["id"]),
                "state": item["state"],
                "http_status": item["http_status"],
                "source_object_key": item["source_object_key"],
                "requested_at": timestamp(item["requested_at"]) if item["requested_at"] else None,
                "finished_at": timestamp(item["finished_at"]) if item["finished_at"] else None,
                "completed_capture_id": str(item["completed_capture_id"])
                if item["completed_capture_id"]
                else None,
                "reused_capture_id": str(item["reused_capture_id"])
                if item["reused_capture_id"]
                else None,
                "validator_capture_id": str(item["validator_capture_id"])
                if item["validator_capture_id"]
                else None,
                "payload": {
                    "sha256": item["payload_sha"],
                    "bytes": item["payload_bytes"],
                    "archived_at": timestamp(item["payload_at"]),
                }
                if item["payload_at"]
                else None,
            }
        )
    counts = {}
    for table in (
        "source_captures",
        "source_fetch_attempts",
        "source_attempt_payloads",
        "security_identifiers",
        "watchlist_memberships",
        "normalization_batches",
    ):
        count = db.execute(
            sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier(table))
        ).fetchone()
        assert count is not None
        counts[table] = count["n"]
    counts.update(
        {
            r["trigger"]: r["n"]
            for r in db.execute(
                "SELECT trigger,count(*) AS n FROM analysis_requests GROUP BY trigger"
            )
        }
    )
    for prohibited in (
        "security_identifiers",
        "watchlist_memberships",
        "normalization_batches",
        "watchlist_add",
        "manual_refresh",
    ):
        if counts.get(prohibited, 0):
            raise ValueError("D4a audit requires no ordinary or financial side effects")
    return {
        "version": "crcl-filing-monitor-audit-v1",
        "request_id": str(request_id),
        "execution_id": str(row["current_execution_id"]),
        "request_parameters_hash": row["request_parameters_hash"],
        "execution_state": row["terminal_outcome"],
        "result": {**result, "manifest": {k: v for k, v in manifest.items() if k != "blob_key"}},
        "captures": captures,
        "attempts": attempts,
        "application_counts": counts,
        "protected_history_sha256": before,
        "protected_history_verified": True,
        "scheduler": "not_configured",
        "source_policy": "Existing approved SEC policy; no new provider",
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("history", "seed-plan", "poll", "inspect"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--cutoff", type=datetime.fromisoformat)
    parser.add_argument("--key")
    parser.add_argument("--request", type=UUID)
    args = parser.parse_args()
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    if args.action in ("history", "seed-plan"):
        with app_postgres.owner_connection(runtime, runtime.database) as db:
            if args.action == "history":
                report = protected_history(db)
            else:
                if args.cutoff is None:
                    parser.error("seed-plan requires --cutoff with an explicit timezone")
                report = register_seed(db, args.cutoff).as_json()
    else:
        if args.before is None:
            parser.error("poll/inspect requires --before protected history")
        before = json.loads(args.before.read_text())
        with psycopg.connect(
            url.set(drivername="postgresql").render_as_string(hide_password=False),
            autocommit=True,
            row_factory=dict_row,
        ) as db:
            verify_history(db, before)
            request_id = args.request
            if args.action == "poll":
                if args.plan is None or not args.key:
                    parser.error("poll requires an explicit --plan file and stable --key")
                plan = FilingMonitorPlan.from_json(json.loads(args.plan.read_text()))
                contact = contact_from_settings(dotenv_values(ROOT / ".env"))
                cache = app_redis.configuration()
                with cache.client() as client:
                    app_redis.verify(cache, client)
                request_id, _ = poll(
                    db, plan, args.key, contact, f"redis://127.0.0.1:{cache.port}/0"
                )
            if request_id is None:
                parser.error("inspect requires --request")
            status = request_status(db, request_id)
            report = (
                public_audit(db, request_id, before)
                if status["terminal_outcome"] is not None and status["typed_result_available"]
                else status
            )
    write_json(args.output, report)
    print("Saved " + args.action + " output. No scheduler or downstream financial work dispatched.")


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
            f"Filing monitor stopped ({type(error).__name__}); "
            "inspect the durable request and local configuration.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
