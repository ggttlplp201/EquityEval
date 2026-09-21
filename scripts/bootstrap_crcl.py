"""Explicit owner setup / bounded CRCL source bootstrap through existing S3 transport."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

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
from equity_schema.workflow import (
    Database,
    claim_source_bootstrap,
    create_workspace_watchlist,
    enqueue_source_bootstrap,
)
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from redis.exceptions import RedisError

from scripts import app_postgres, app_redis

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = "docs/research/sec-application-policy-2026-09-21.md"
POLICY_KEY = "sec-public-filings-2026-09-21"
SOURCE_KEY = "sec-edgar-public-filings"
LICENCE = "SEC public filings and government-created data reuse"
IDENTITY_PATH = "docs/research/seven-company-pilot-identities.json"
WORKSPACE = "CRCL source bootstrap"


def contact_from_settings(values: dict[str, str | None]) -> str:
    configured = os.environ.get("SEC_USER_AGENT") or values.get("SEC_USER_AGENT") or ""
    contacts: list[str] = re.findall(r"[^\s<>(),@]+@[^\s<>(),@]+\.[A-Za-z]{2,}", configured)
    if len(contacts) != 1 or contacts[0].endswith((".invalid", "@example.com")):
        raise ValueError("Configure one genuine SEC identifying contact in SEC_USER_AGENT")
    return contacts[0]


def _ensure(
    db: Database,
    table: str,
    natural: dict[str, Any],
    expected: dict[str, Any],
    created: dict[str, Any] | None = None,
) -> UUID:
    condition = sql.SQL(" AND ").join(
        sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(key)) for key in natural
    )
    rows = db.execute(
        sql.SQL("SELECT * FROM {} WHERE {}").format(sql.Identifier(table), condition),
        list(natural.values()),
    ).fetchall()
    if rows:
        if len(rows) != 1 or any(rows[0][key] != value for key, value in expected.items()):
            raise ValueError(f"Existing {table} differs from reviewed bootstrap configuration")
        return UUID(str(rows[0]["id"]))
    record_id = uuid4()
    values = {"id": record_id, **natural, **expected, **(created or {})}
    db.execute(
        sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table),
            sql.SQL(",").join(map(sql.Identifier, values)),
            sql.SQL(",").join(sql.Placeholder() for _ in values),
        ),
        [Jsonb(v) if isinstance(v, dict) else v for v in values.values()],
    )
    return record_id


def register(db: Database, root: Path = ROOT) -> dict[str, UUID]:
    """Owner-only, idempotent reviewed identities/policy; never captures or quote dates."""
    identity_bytes = (root / IDENTITY_PATH).read_bytes()
    company = next(c for c in json.loads(identity_bytes)["companies"] if c["ticker"] == "CRCL")
    if (company["cik"], company["name"], company["security"]) != (
        "0001876042",
        "Circle Internet Group, Inc.",
        "Class A common stock",
    ):
        raise ValueError("CRCL identity packet changed; review required")
    review_hash = hashlib.sha256((root / POLICY_PATH).read_bytes()).hexdigest()
    now = datetime.now(UTC)
    with db.transaction():
        db.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,931))", ("crcl-bootstrap-setup",)
        )
        source = _ensure(
            db,
            "sources",
            {"source_key": SOURCE_KEY},
            {
                "name": "SEC EDGAR public filings",
                "base_url": "https://data.sec.gov",
                "terms_review_reference": POLICY_KEY,
                "content_scope": "SEC government data and public EDGAR filings",
            },
        )
        policy = _ensure(
            db,
            "source_policy_revisions",
            {"source_id": source, "review_key": POLICY_KEY},
            {
                "licence_label": LICENCE,
                "content_scope": (
                    "Company Facts, submissions/history, public EDGAR filing documents"
                ),
                "redistribution_status": "allowed",
                "permitted_use": (
                    "Retain source bodies and observations for local analysis "
                    "and reuse within reviewed SEC scope"
                ),
                "attribution_requirements": (
                    "SEC and issuer; source URL, accession, capture "
                    "timestamps, hashes and transforms"
                ),
                "terms_urls": [
                    "https://www.sec.gov/about/webmaster-frequently-asked-questions",
                    "https://www.sec.gov/about/privacy-information",
                    "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
                ],
                "reviewed_by": "Codex source review under owner-authorized D031",
                "review_artifact_reference": POLICY_PATH,
                "review_artifact_sha256": review_hash,
            },
            {"reviewed_at": now},
        )
        issuer = _ensure(
            db,
            "issuers",
            {"cik": company["cik"]},
            {"legal_name": company["name"]},
            {"first_seen_at": now},
        )
        security = _ensure(
            db,
            "securities",
            {
                "issuer_id": issuer,
                "instrument_kind": "common_stock",
                "share_class_label": company["security"],
            },
            {"active": True, "underlying_security_id": None},
        )
        rows = db.execute("SELECT id FROM workspaces WHERE name=%s", (WORKSPACE,)).fetchall()
        if len(rows) > 1:
            raise ValueError("Ambiguous bootstrap workspace")
        workspace = (
            rows[0]["id"] if rows else create_workspace_watchlist(db, name=WORKSPACE).workspace_id
        )
    return {
        "source": source,
        "policy": policy,
        "issuer": issuer,
        "security": security,
        "workspace": workspace,
    }


def registered(db: Database) -> dict[str, UUID]:
    rows = db.execute(
        "SELECT src.id AS source,p.id AS policy,i.id AS issuer,s.id AS security,w.id AS workspace, "
        "p.review_artifact_sha256 FROM sources src "
        "JOIN source_policy_revisions p ON p.source_id=src.id "
        "CROSS JOIN issuers i JOIN securities s ON s.issuer_id=i.id CROSS JOIN workspaces w "
        "WHERE src.source_key=%s AND p.review_key=%s AND i.cik='0001876042' "
        "AND s.instrument_kind='common_stock' AND s.share_class_label='Class A common stock' "
        "AND w.name=%s",
        (SOURCE_KEY, POLICY_KEY, WORKSPACE),
    ).fetchall()
    if (
        len(rows) != 1
        or rows[0]["review_artifact_sha256"]
        != hashlib.sha256((ROOT / POLICY_PATH).read_bytes()).hexdigest()
    ):
        raise ValueError("Reviewed CRCL bootstrap registration is missing or ambiguous")
    return {key: rows[0][key] for key in ("source", "policy", "issuer", "security", "workspace")}


def capture(
    db: Database, identities: dict[str, UUID], contact: str, redis_url: str, key: str
) -> dict[str, Any]:
    plan = BootstrapPlan(
        identities["issuer"],
        "0001876042",
        identities["source"],
        identities["policy"],
        date(2025, 1, 1),
        date(2026, 9, 21),
        (
            "company_facts/0001876042",
            "submissions/0001876042",
            "filing_document/0001876042/0001876042-26-000062/crcl-20251231.htm",
            "filing_document/0001876042/0001876042-26-000228/crcl-20251231.htm",
            "filing_document/0001876042/0001876042-26-000248/crcl-20260630.htm",
        ),
    )
    request = enqueue_source_bootstrap(
        db,
        workspace_id=identities["workspace"],
        security_id=identities["security"],
        idempotency_key=key,
        plan=plan,
    )
    lease = claim_source_bootstrap(
        db, worker_id="crcl-bootstrap-cli", lease_seconds=360, request_id=request.request_id
    )
    if lease is None:
        row = db.execute(
            "SELECT terminal_outcome FROM analysis_request_state WHERE request_id=%s",
            (request.request_id,),
        ).fetchone()
        return {
            "request_id": str(request.request_id),
            "state": row["terminal_outcome"] if row else "unknown",
            "dispatched": False,
            "note": "Request is terminal, leased, or waiting for its retry time",
        }
    descriptor = SourceDescriptor(
        identities["source"],
        SOURCE_KEY,
        "SEC EDGAR public filings",
        identities["policy"],
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
            result = run_source_bootstrap(db, lease, source, archive, plan)
            return {
                "request_id": str(request.request_id),
                "execution_id": str(lease.execution_id),
                "result": asdict(result),
                "captures": [asdict(r) for r in source.records],
                "identity_review": IDENTITY_PATH,
                "identity_review_sha256": hashlib.sha256(
                    (ROOT / IDENTITY_PATH).read_bytes()
                ).hexdigest(),
            }
    finally:
        limiter.client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("register", "capture"))
    parser.add_argument("--key", help="Explicit stable logical request key; reuse it for retries")
    args = parser.parse_args()
    if args.action == "capture" and not args.key:
        parser.error("capture requires --key")
    values = dotenv_values(ROOT / ".env")
    contact = contact_from_settings(values)
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    cache = app_redis.configuration()
    with cache.client() as client:
        app_redis.verify(cache, client)
    if args.action == "register":
        with app_postgres.owner_connection(runtime, runtime.database) as db:
            report = {"registered": register(db), "financial_capture_created": False}
    else:
        redis_url = f"redis://127.0.0.1:{cache.port}/0"
        with psycopg.connect(
            url.set(drivername="postgresql").render_as_string(hide_password=False),
            autocommit=True,
            row_factory=dict_row,
        ) as db:
            report = capture(db, registered(db), contact, redis_url, args.key)
    print(canonical_json(report))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, psycopg.Error, RedisError, httpx.HTTPError) as error:
        # Keep credentials/contact out of exceptions. Durable attempts hold failure evidence.
        print(
            f"CRCL bootstrap stopped ({type(error).__name__}); "
            "inspect configuration and request audit.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
