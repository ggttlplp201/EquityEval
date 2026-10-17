"""D050 finite CRCL history acquisition; no normalization or metric publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import psycopg
from dotenv import dotenv_values
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import ResourceKind, SourceDescriptor
from equity_ingest.limiter import RedisRateLimiter
from equity_ingest.pipeline import acquisition_lease_seconds, run_source_bootstrap
from equity_ingest.sec import SecSource
from equity_ingest.transport import DatabaseAttemptStore, SecTransport
from equity_schema.bootstrap import BootstrapPlan
from equity_schema.crcl_history import CRCL_HISTORY_DOCUMENTS, CRCL_HISTORY_VERSION
from equity_schema.workflow import Database, claim_source_bootstrap, enqueue_source_bootstrap
from psycopg.rows import dict_row
from redis.exceptions import RedisError

from scripts import app_postgres, app_redis
from scripts import bootstrap_crcl as bootstrap
from scripts.normalize_crcl import ROOT
from scripts.publish_crcl_fundamentals import _write_exclusive
from scripts.publish_crcl_normalization import rows_snapshot

SCOPE = ROOT / "docs/design/d5l/inventory-scope.json"
SCOPE_SHA = "754f225b924f52ac9d0bce9761ff2808627bda465aaeb2e59372e9fa93700d22"
ACQUISITION = ROOT / "docs/research/crcl-history-acquisition-2026-10-16.json"
INTENT = ROOT / "docs/research/crcl-history-acquisition-intent-2026-10-16.json"
MIGRATION = ROOT / "docs/research/crcl-history-migration-2026-10-16.json"
PREFIX = "d5l-history-2026-10-16-group"


def checked_scope(path: Path = SCOPE) -> dict[str, Any]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SCOPE_SHA:
        raise ValueError("D5l scope hash differs from committed proposal")
    value: dict[str, Any] = json.loads(raw)
    documents = [
        key
        for group in value["groups"]
        for key in group["resources"]
        if key.startswith("filing_document/")
    ]
    if len(documents) != 47 or set(documents) != CRCL_HISTORY_DOCUMENTS:
        raise ValueError("D5l application roster differs from proposal")
    return value


def group_plan(identities: dict[str, UUID], group: dict[str, Any]) -> BootstrapPlan:
    return BootstrapPlan(
        identities["issuer"],
        "0001876042",
        identities["source"],
        identities["policy"],
        date.fromisoformat(group["inventoryStart"]),
        date.fromisoformat(group["inventoryEnd"]),
        tuple(group["resources"]),
        version=CRCL_HISTORY_VERSION,
    )


def capture_group(
    db: Database,
    identities: dict[str, UUID],
    group: dict[str, Any],
    contact: str,
    redis_url: str,
    deadline: float,
) -> dict[str, Any]:
    plan = group_plan(identities, group)

    def remaining() -> float:
        return deadline - time.monotonic()

    seconds = acquisition_lease_seconds(remaining)
    request = enqueue_source_bootstrap(
        db,
        workspace_id=identities["workspace"],
        security_id=identities["security"],
        idempotency_key=f"{PREFIX}-{group['number']}",
        plan=plan,
        max_attempts=1,
    )
    lease = claim_source_bootstrap(
        db, worker_id="d5l-history-capture", lease_seconds=seconds, request_id=request.request_id
    )
    if lease is None:
        raise ValueError("Existing D5l request is not implicitly retried")
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
            result = run_source_bootstrap(
                db, lease, source, archive, plan, acquisition_remaining=remaining
            )
            return {
                "number": group["number"],
                "request_id": str(request.request_id),
                "execution_id": str(lease.execution_id),
                "bootstrap_plan": plan.as_json(),
                "result": asdict(result),
                "acquisition_result": bootstrap.acquisition_result(db, lease.execution_id),
                "captures": [asdict(record) for record in source.records],
            }
    finally:
        limiter.client.close()


def capture() -> dict[str, Any]:
    if ACQUISITION.exists() or INTENT.exists():
        raise ValueError("D5l acquisition attempt already exists; no implicit retry or overwrite")
    report: dict[str, Any] = {
        "kind": "d5l-governed-history-acquisition",
        "proposal": "dd2d4a9",
        "scopeSha256": SCOPE_SHA,
        "status": "blocked",
        "errorType": None,
        "groups": [],
        "beforeRows": None,
        "afterRows": None,
        "originalRowsPreserved": None,
        "budget": {"logicalResources": 69, "maximumDispatches": 207, "wallSeconds": 2700},
        "startedAt": datetime.now(UTC).isoformat(),
        "completedAt": None,
        "missingResources": [],
        "missingResourceMeaning": (
            "No verified retained capture in this attempt audit; "
            "not proof of absence after interruption."
        ),
        "retainedAttemptEvidence": [],
        "financialPublication": False,
    }
    try:
        scope = checked_scope()
        report["missingResources"] = [
            {"group": g["number"], "resource": k} for g in scope["groups"] for k in g["resources"]
        ]
        migration = json.loads(MIGRATION.read_text())
        if migration.get("head") != "0014_crcl_history_documents" or not migration.get(
            "originalRowsPreserved"
        ):
            raise ValueError("Reviewed migration preservation audit is required before acquisition")
        report["migrationSha256"] = hashlib.sha256(MIGRATION.read_bytes()).hexdigest()
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
                report["beforeRows"] = rows_snapshot(owner)
                if report["beforeRows"] != migration["afterRows"]:
                    raise ValueError("Application differs from reviewed migration baseline")
                identities = bootstrap.registered(owner)
                report["identities"] = {key: str(value) for key, value in identities.items()}
                report["plans"] = [
                    group_plan(identities, group).as_json() for group in scope["groups"]
                ]
            _write_exclusive(INTENT, report)
            deadline = time.monotonic() + 2700
            try:
                with psycopg.connect(
                    url.set(drivername="postgresql").render_as_string(hide_password=False),
                    autocommit=True,
                    row_factory=dict_row,
                ) as db:
                    identities = bootstrap.registered(db)
                    for group in scope["groups"]:
                        acquisition_lease_seconds(lambda: deadline - time.monotonic())
                        result = capture_group(
                            db,
                            identities,
                            group,
                            contact,
                            f"redis://127.0.0.1:{cache.port}/0",
                            deadline,
                        )
                        report["groups"].append(result)
                        captured = {r["source_object_key"] for r in result["captures"]}
                        report["missingResources"] = [
                            item
                            for item in report["missingResources"]
                            if item["group"] != group["number"] or item["resource"] not in captured
                        ]
                        if result["result"]["state"] != "completed" or result["result"]["gaps"]:
                            break
            finally:
                with owner.transaction():
                    owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    from scripts.recover_crcl_history import reconstruct

                    report = reconstruct(
                        owner, json.loads(INTENT.read_text()), LocalArchive(ROOT / "var/raw")
                    )
                    report["recoveredReadOnly"] = False

    except (OSError, ValueError, RuntimeError, psycopg.Error, RedisError, httpx.HTTPError) as error:
        report["errorType"] = type(error).__name__
        report["status"] = "incomplete" if report["groups"] else "blocked"
    report["completedAt"] = datetime.now(UTC).isoformat()
    if INTENT.exists():
        report["intentSha256"] = hashlib.sha256(INTENT.read_bytes()).hexdigest()
    _write_exclusive(ACQUISITION, report)
    return report


def recover() -> dict[str, Any]:
    from scripts.recover_crcl_history import reconstruct

    if ACQUISITION.exists():
        saved: dict[str, Any] = json.loads(ACQUISITION.read_text())
        if saved.get("intentSha256") != hashlib.sha256(INTENT.read_bytes()).hexdigest():
            raise ValueError("Saved acquisition audit differs from original intent")
        return saved
    intent = json.loads(INTENT.read_text())
    migration_raw = MIGRATION.read_bytes()
    migration = json.loads(migration_raw)
    if (
        intent.get("migrationSha256") != hashlib.sha256(migration_raw).hexdigest()
        or intent.get("beforeRows") != migration["afterRows"]
    ):
        raise ValueError("Recovery baseline differs from immutable migration audit")
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as owner, owner.transaction():
        owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        report = reconstruct(owner, intent, LocalArchive(ROOT / "var/raw"))
    report["intentSha256"] = hashlib.sha256(INTENT.read_bytes()).hexdigest()
    report["completedAt"] = datetime.now(UTC).isoformat()
    _write_exclusive(ACQUISITION, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "recover"))
    args = parser.parse_args()
    report = capture() if args.action == "capture" else recover()
    print(
        json.dumps(
            {
                "status": report["status"],
                "groups": len(report["groups"]),
                "missingResources": len(report["missingResources"]),
                "originalRowsPreserved": report["originalRowsPreserved"],
            }
        )
    )


if __name__ == "__main__":
    main()
