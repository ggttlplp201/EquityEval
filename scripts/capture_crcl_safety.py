"""Explicit D041 capture-only expansion; bounded pinned groups, no normalization."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import timedelta
from typing import Any
from uuid import UUID

import httpx
import psycopg
from dotenv import dotenv_values
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import ResourceKind, SourceDescriptor
from equity_ingest.financial_types import canonical_json
from equity_ingest.limiter import RedisRateLimiter
from equity_ingest.pipeline import run_source_bootstrap
from equity_ingest.sec import SecSource
from equity_ingest.transport import DatabaseAttemptStore, SecTransport
from equity_schema.bootstrap import BootstrapPlan
from equity_schema.workflow import Database, claim_source_bootstrap, enqueue_source_bootstrap
from psycopg.rows import dict_row
from redis.exceptions import RedisError

from scripts import app_postgres, app_redis
from scripts import bootstrap_crcl as bootstrap
from scripts.normalize_crcl import CUTOFF, RESOURCES, ROOT, prepare
from scripts.publish_crcl_normalization import rows_snapshot
from scripts.review_crcl_identity import read_audit, verify_database_evidence
from scripts.review_crcl_safety import ACQUISITION, START, capture_groups, scope_inventory


def capture_group(
    db: Database,
    identities: dict[str, UUID],
    resources: tuple[str, ...],
    group_number: int,
    contact: str,
    redis_url: str,
    *,
    request_prefix: str = "d5c-safety-2026-10-12-group",
    worker_id: str = "d5c-safety-capture",
) -> dict[str, Any]:
    plan = BootstrapPlan(
        identities["issuer"],
        "0001876042",
        identities["source"],
        identities["policy"],
        START,
        CUTOFF.date(),
        (RESOURCES[0], RESOURCES[1], *resources),
    )
    request = enqueue_source_bootstrap(
        db,
        workspace_id=identities["workspace"],
        security_id=identities["security"],
        idempotency_key=f"{request_prefix}-{group_number}",
        plan=plan,
    )
    lease = claim_source_bootstrap(
        db,
        worker_id=worker_id,
        lease_seconds=360,
        request_id=request.request_id,
    )
    if lease is None:
        raise ValueError("Pinned D5c group already exists; inspect saved state before retry")
    descriptor = SourceDescriptor(
        identities["source"],
        bootstrap.SOURCE_KEY,
        "SEC EDGAR public filings",
        identities["policy"],
        bootstrap.POLICY_KEY,
        bootstrap.LICENCE,
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
            result = run_source_bootstrap(db, lease, source, archive, plan)
            return {
                "request_id": str(request.request_id),
                "execution_id": str(lease.execution_id),
                "bootstrap_plan": plan.as_json(),
                "result": asdict(result),
                "acquisition_result": bootstrap.acquisition_result(db, lease.execution_id),
                "captures": [asdict(record) for record in source.records],
            }
    finally:
        limiter.client.close()


def capture() -> None:
    target = ROOT / ACQUISITION
    if target.exists():
        raise ValueError("D5c acquisition audit already exists; never overwrite a saved attempt")
    try:
        _capture()
    except (OSError, ValueError, RuntimeError, psycopg.Error, RedisError, httpx.HTTPError) as error:
        if target.exists():
            raise
        report: dict[str, Any] = {
            "kind": "d5c-governed-source-acquisition",
            "proposal": "eb42a9e",
            "status": "blocked",
            "errorType": type(error).__name__,
            "groups": [],
            "attempts": [],
            "originalRowsPreserved": None,
            "before": None,
            "after": None,
            "note": (
                "Acquisition prerequisite or reporting failed. Application preservation "
                "and any partial durable captures are unverified. Inspect durable state "
                "before any retry; no completeness or no-write claim is made."
            ),
        }
        target.write_text(canonical_json(report) + "\n")


def _capture() -> None:
    target = ROOT / ACQUISITION
    if target.exists():
        raise ValueError("D5c acquisition audit already exists; never overwrite a saved attempt")
    audit = read_audit(ROOT)
    archive = LocalArchive(ROOT / "var/raw")
    prepare(audit, archive)
    row = next(item for item in audit["captures"] if item["source_object_key"] == RESOURCES[1])
    from equity_ingest.sec_inventory import parse_submissions

    inventory = parse_submissions(
        archive.read_blob(row["blob_key"], row["body_sha256"], row["byte_count"]),
        expected_cik="0001876042",
        capture_id=UUID(row["capture_id"]),
    )
    captured = {
        item["source_object_key"].split("/")[2]: item
        for item in audit["captures"]
        if item["source_object_key"].startswith("filing_document/")
    }
    rows = scope_inventory(inventory, captured)
    groups = capture_groups(rows)
    if len(rows) != 19 or tuple(map(len, groups)) != (5, 5, 5, 1):
        raise ValueError("Pinned D5c roster changed")
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    cache = app_redis.configuration()
    with cache.client() as client:
        app_redis.verify(cache, client)
    contact = bootstrap.contact_from_settings(dotenv_values(ROOT / ".env"))
    with app_postgres.owner_connection(runtime, runtime.database) as owner:
        with owner.transaction():
            owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            verify_database_evidence(owner, audit, archive)
            before = rows_snapshot(owner)
        result_groups = []
        error_type = None
        try:
            with psycopg.connect(
                url.set(drivername="postgresql").render_as_string(hide_password=False),
                autocommit=True,
                row_factory=dict_row,
            ) as db:
                identities = bootstrap.registered(db)
                for number, resources in enumerate(groups, 1):
                    result = capture_group(
                        db,
                        identities,
                        resources,
                        number,
                        contact,
                        f"redis://127.0.0.1:{cache.port}/0",
                    )
                    result_groups.append(result)
                    if result["result"]["state"] != "completed" or result["result"]["gaps"]:
                        break
        except (OSError, ValueError, RuntimeError, psycopg.Error) as error:
            error_type = type(error).__name__
        with owner.transaction():
            owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            after = rows_snapshot(owner)
            attempts = owner.execute(
                "SELECT a.id,a.state,a.http_status,a.failure_code,a.completed_capture_id,"
                "a.requested_at,a.finished_at FROM source_fetch_attempts a "
                "JOIN analysis_stage_attempts s ON s.id=a.stage_attempt_id "
                "JOIN analysis_executions e ON e.id=s.execution_id "
                "JOIN analysis_requests r ON r.id=e.request_id "
                "WHERE r.idempotency_key LIKE 'd5c-safety-2026-10-12-group-%' ORDER BY "
                "a.requested_at"
            ).fetchall()
        preserved = before.keys() == after.keys() and all(
            set(values).issubset(after[key]) for key, values in before.items()
        )
        complete = len(result_groups) == len(groups) and all(
            group["result"]["state"] == "completed" and not group["result"]["gaps"]
            for group in result_groups
        )
        report: dict[str, Any] = {
            "kind": "d5c-governed-source-acquisition",
            "proposal": "eb42a9e",
            "status": "captured_pending_review" if complete else "incomplete",
            "errorType": error_type,
            "groups": result_groups,
            "attempts": attempts,
            "originalRowsPreserved": preserved,
            "before": {key: len(values) for key, values in before.items()},
            "after": {key: len(values) for key, values in after.items()},
            "note": (
                "Actual retrieval timestamps remain separate from the September cutoff. "
                "Stop after the first incomplete group; no automatic retry or scope "
                "expansion. Captures do not constitute financial/event review or analysis "
                "publication."
            ),
        }
        target.write_text(canonical_json(report) + "\n")
        if not preserved:
            raise ValueError("Prior application rows changed; inspect saved audit")
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "groups": len(result_groups),
                    "attempts": len(attempts),
                    "prior_rows_preserved": preserved,
                    "error_type": error_type,
                }
            )
        )


def recover(*, check: bool = False) -> None:
    """Read-only recovery from durable manifests after local report interruption."""
    from equity_ingest.financial_types import content_hash
    from psycopg import sql

    target = ROOT / ACQUISITION
    if target.exists() and not check:
        raise ValueError("Saved acquisition audit is immutable")
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    archive = LocalArchive(ROOT / "var/raw")
    baseline = json.loads((ROOT / "docs/research/crcl-normalization-2026-09-30.json").read_text())[
        "after"
    ]
    with app_postgres.owner_connection(runtime, runtime.database) as owner, owner.transaction():
        owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        requests = owner.execute(
            "SELECT r.*,e.id AS execution_id,e.state AS execution_state "
            "FROM analysis_requests r JOIN analysis_executions e ON e.request_id=r.id "
            "WHERE r.idempotency_key LIKE 'd5c-safety-2026-10-12-group-%' "
            "ORDER BY r.idempotency_key"
        ).fetchall()
        groups = []
        new_ids: set[str] = set()
        for request in requests:
            result = bootstrap.acquisition_result(owner, request["execution_id"])
            if request["execution_state"] != "completed" or result is None:
                raise ValueError("Recovery requires completed retained source results")
            ref = result["manifest"]
            manifest = json.loads(
                archive.read_blob(ref["blob_key"], ref["body_sha256"], ref["byte_count"])
            )
            captures = [
                record for fetch in manifest["fetch_results"] for record in fetch["records"]
            ]
            group = {
                "request_id": str(request["id"]),
                "execution_id": str(request["execution_id"]),
                "request_parameters_hash": request["request_parameters_hash"],
                "bootstrap_plan": request["bootstrap_plan"],
                "acquisition_result": result,
                "captures": captures,
                "result": {
                    "state": request["execution_state"],
                    "gaps": result["readiness"]["blocking_reasons"],
                },
            }
            verify_database_evidence(owner, group, archive)
            groups.append(group)
            new_ids.update((str(request["id"]), str(request["execution_id"])))
            new_ids.update(record["capture_id"] for record in captures)
            stages = owner.execute(
                "SELECT id FROM analysis_stage_attempts WHERE execution_id=%s",
                (request["execution_id"],),
            ).fetchall()
            new_ids.update(str(stage["id"]) for stage in stages)
        attempts = owner.execute(
            "SELECT a.id,a.state,a.http_status,a.failure_code,a.completed_capture_id,"
            "a.requested_at,a.finished_at FROM source_fetch_attempts a "
            "JOIN analysis_stage_attempts s ON s.id=a.stage_attempt_id "
            "JOIN analysis_executions e ON e.id=s.execution_id "
            "JOIN analysis_requests r ON r.id=e.request_id "
            "WHERE r.idempotency_key LIKE 'd5c-safety-2026-10-12-group-%' ORDER BY a.requested_at"
        ).fetchall()
        new_ids.update(str(attempt["id"]) for attempt in attempts)
        current = rows_snapshot(owner)
        preserved = {}
        for table in baseline:
            rows = owner.execute(
                sql.SQL("SELECT to_jsonb(t) AS row FROM {} t").format(sql.Identifier(table))
            ).fetchall()
            prior = sorted(
                content_hash(row["row"])
                for row in rows
                if not any(
                    isinstance(value, str) and value in new_ids for value in row["row"].values()
                )
            )
            preserved[table] = (
                len(prior) == baseline[table]["count"]
                and content_hash(prior) == baseline[table]["sha256"]
            )
        if not all(preserved.values()):
            raise ValueError(
                "Prior baseline mismatch: "
                + ", ".join(key for key, value in preserved.items() if not value)
            )
        report: dict[str, Any] = {
            "kind": "d5c-governed-source-acquisition",
            "proposal": "eb42a9e",
            "status": "captured_pending_review",
            "groups": groups,
            "attempts": attempts,
            "originalRowsPreserved": True,
            "preservationProof": preserved,
            "before": {key: value["count"] for key, value in baseline.items()},
            "after": {key: len(value) for key, value in current.items()},
            "recovery": (
                "Read-only reconstruction from verified request/results/manifests after "
                "final report SQL column-name error; no source retry."
            ),
            "note": (
                "All sixteen missing primary bodies were retained in October. Historical "
                "September knowledge remains incomplete; event and exhibit content review "
                "is separate."
            ),
        }
    encoded = canonical_json(report) + "\n"
    if check:
        if target.read_text() != encoded:
            raise ValueError("Saved acquisition audit differs from application replay")
    else:
        target.write_text(encoded)
    print(
        json.dumps(
            {"groups": len(groups), "attempts": len(attempts), "original_rows_preserved": True}
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "recover", "verify"))
    args = parser.parse_args()
    if args.action in {"recover", "verify"}:
        recover(check=args.action == "verify")
    else:
        capture()


if __name__ == "__main__":
    main()
