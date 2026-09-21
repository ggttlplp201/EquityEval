"""Replay the bounded D3c CRCL identity review; never register or fetch anything.

This verifies reviewed assertions against one pinned evidence vintage, not a
currency-discovery algorithm. New evidence requires a new substantive review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from equity_ingest.archive import LocalArchive
from equity_schema.workflow import Database
from lxml import etree
from psycopg import sql

from scripts import app_postgres
from scripts.bootstrap_crcl import acquisition_result, registered

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = "docs/research/crcl-pinned-bootstrap-2026-09-21.json"
AUDIT_SHA256 = "4b1bff12335faf50b67192f92f0f04a5f7d8d1ff8738644f037acf8036836dac"
IX = "http://www.xbrl.org/2013/inlineXBRL"
DEI = {"http://xbrl.sec.gov/dei/2025", "http://xbrl.sec.gov/dei/2026"}
SUBMISSIONS = "submissions/0001876042"
ORIGINAL = "filing_document/0001876042/0001876042-26-000062/crcl-20251231.htm"
LISTING_STATEMENT = (
    "Since June 5, 2025, our Class A common stock has been listed on the "
    "New York Stock Exchange under the symbol CRCL."
)
REPORTING_STATEMENT = (
    "Our reporting currency is the U.S. dollar and the functional currency "
    "of our international operations is its local currency."
)
TABLES = (
    "sources",
    "source_policy_revisions",
    "issuers",
    "securities",
    "source_captures",
    "capture_policy_links",
    "source_fetch_attempts",
    "analysis_requests",
    "analysis_executions",
    "analysis_stage_attempts",
    "execution_events",
    "security_identifiers",
    "security_identifier_validity",
    "watchlist_memberships",
    "normalization_batches",
)


def read_audit(root: Path) -> dict[str, Any]:
    raw = (root / AUDIT_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != AUDIT_SHA256:
        raise ValueError("D3c audit changed; a new evidence review is required")
    result: dict[str, Any] = json.loads(raw)
    return result


def xml_root(body: bytes) -> etree._Element:
    root = etree.fromstring(
        body, etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    )
    if getattr(root.getroottree().docinfo, "doctype", ""):
        raise ValueError("DTD-bearing identity evidence is unsupported")
    return root


def normalized_text(node: etree._Element) -> str:
    return " ".join(
        "".join(
            part.decode() if isinstance(part, bytes) else part for part in node.itertext()
        ).split()
    )


def evidence(node: etree._Element, capture_id: str, value: str) -> dict[str, str]:
    return {
        "capture_id": capture_id,
        "locator": node.getroottree().getpath(node),
        "value": value,
    }


def cover_evidence(root: etree._Element, capture_id: str) -> dict[str, dict[str, str]]:
    expected = {
        "TradingSymbol": "CRCL",
        "SecurityExchangeName": "New York Stock Exchange",
        "Security12bTitle": "Class A common stock, par value $0.0001 per share",
    }
    found: dict[str, list[etree._Element]] = {key: [] for key in expected}
    for node in root.iter(f"{{{IX}}}nonNumeric"):
        prefix, separator, local = (node.get("name") or "").partition(":")
        if separator and local in found and node.nsmap.get(prefix) in DEI:
            found[local].append(node)
    result = {}
    for local, value in expected.items():
        nodes = found[local]
        if len(nodes) != 1 or normalized_text(nodes[0]) != value:
            raise ValueError(f"Missing, conflicting or ambiguous cover identity: {local}")
        result[local] = evidence(nodes[0], capture_id, value)
    return result


def statement_evidence(root: etree._Element, capture_id: str, statement: str) -> dict[str, str]:
    # Prefer the smallest containing element so the locator remains inspectable.
    candidates = [
        node
        for node in root.iter()
        if isinstance(node.tag, str)
        and statement in normalized_text(node)
        and not any(statement in normalized_text(child) for child in node)
    ]
    if len(candidates) != 1:
        raise ValueError("Reviewed statement is missing or ambiguous; no date fallback")
    return evidence(candidates[0], capture_id, statement)


def review_bodies(audit: dict[str, Any], archive: LocalArchive) -> dict[str, Any]:
    captures = {item["source_object_key"]: item for item in audit["captures"]}
    bodies = {
        key: archive.read_blob(item["blob_key"], item["body_sha256"], item["byte_count"])
        for key, item in captures.items()
    }
    submissions = json.loads(bodies[SUBMISSIONS])
    if (
        submissions.get("cik") != "0001876042"
        or submissions.get("name") != "Circle Internet Group, Inc."
        or submissions.get("tickers") != ["CRCL"]
        or submissions.get("exchanges") != ["NYSE"]
    ):
        raise ValueError("Submissions identity is missing, conflicting or ambiguous")
    covers = []
    reporting = []
    listing = None
    for key, body in bodies.items():
        if not key.startswith("filing_document/"):
            continue
        root = xml_root(body)
        capture_id = captures[key]["capture_id"]
        covers.append(cover_evidence(root, capture_id))
        if key == ORIGINAL:
            listing = statement_evidence(root, capture_id, LISTING_STATEMENT)
        if "0001876042-26-000228" not in key:
            reporting.append(statement_evidence(root, capture_id, REPORTING_STATEMENT))
    if len(covers) != 3 or listing is None:
        raise ValueError("The reviewed three filings and original listing statement are required")
    identity_id = captures[SUBMISSIONS]["capture_id"]
    return {
        "review_version": "crcl-d3c-identity-review-v1",
        "review_basis": "Manual review replay over pinned D3c bytes; no new source discovery",
        "audit_sha256": AUDIT_SHA256,
        "request_id": audit["request_id"],
        "execution_id": audit["execution_id"],
        "identity_capture_id": identity_id,
        "fields": {
            "symbol": {
                "value": "CRCL",
                "evidence": [
                    {"capture_id": identity_id, "locator": "/tickers/0", "value": "CRCL"},
                    *[cover["TradingSymbol"] for cover in covers],
                ],
            },
            "exchange_code": {
                "value": "NYSE",
                "evidence": [
                    {"capture_id": identity_id, "locator": "/exchanges/0", "value": "NYSE"},
                    *[cover["SecurityExchangeName"] for cover in covers],
                ],
                "method": "SEC exchange code; no inferred MIC conversion",
            },
            "share_class": {
                "value": "Class A common stock",
                "evidence": [cover["Security12bTitle"] for cover in covers],
            },
            "valid_from": {
                "value": "2025-06-05",
                "evidence": [listing],
                "method": "Explicit listing-start statement; not filing/capture date",
            },
            "quote_currency": {
                "value": None,
                "evidence": [],
                "status": "unsubstantiated_in_reviewed_captures",
            },
        },
        "excluded_currency_evidence": {
            "reporting_currency": reporting,
            "reason": "Reporting currency, USD/share offering prices, par value and public "
            "float amounts do not explicitly establish exchange quote currency.",
        },
        "blocking_reasons": ["quote_currency_unsubstantiated"],
        "registration_ready": False,
        "ordinary_request_eligible": False,
        "financial_result": False,
        "event_review": "not_performed",
        "captures": audit["captures"],
    }


def metadata_equal(actual: Any, expected: Any) -> bool:
    if isinstance(actual, datetime):
        return isinstance(expected, str) and actual == datetime.fromisoformat(expected)
    return str(actual) == str(expected)


def verify_database_evidence(db: Database, audit: dict[str, Any], archive: LocalArchive) -> None:
    identities = registered(db)
    request = db.execute(
        "SELECT * FROM analysis_requests WHERE id=%s", (audit["request_id"],)
    ).fetchone()
    if (
        request is None
        or request["bootstrap_plan"] != audit["bootstrap_plan"]
        or request["request_parameters_hash"] != audit["request_parameters_hash"]
        or request["trigger"] != "source_bootstrap"
        or request["quote_identifier_id"] is not None
        or request["security_id"] != identities["security"]
        or request["workspace_id"] != identities["workspace"]
        or str(identities["issuer"]) != audit["bootstrap_plan"]["issuer_id"]
        or str(identities["source"]) != audit["bootstrap_plan"]["source_id"]
        or str(identities["policy"]) != audit["bootstrap_plan"]["policy_revision_id"]
    ):
        raise ValueError("Stored request differs from the reviewed D3c request")
    execution = db.execute(
        "SELECT request_id,state,error_code,error_detail FROM analysis_executions WHERE id=%s",
        (audit["execution_id"],),
    ).fetchone()
    if execution is None or (
        str(execution["request_id"]),
        execution["state"],
        execution["error_code"],
        execution["error_detail"],
    ) != (audit["request_id"], "completed", None, None):
        raise ValueError("Stored execution differs from the reviewed completion")
    result = acquisition_result(db, UUID(audit["execution_id"]))
    if result is None or result != audit["acquisition_result"]:
        raise ValueError("Persisted readiness differs from D3c audit")
    manifest_ref = result["manifest"]
    manifest = json.loads(
        archive.read_blob(
            manifest_ref["blob_key"], manifest_ref["body_sha256"], manifest_ref["byte_count"]
        )
    )
    if (
        manifest["bootstrap_plan"] != audit["bootstrap_plan"]
        or manifest["readiness"] != result["readiness"]
        or [record for fetch in manifest["fetch_results"] for record in fetch["records"]]
        != audit["captures"]
    ):
        raise ValueError("Archived acquisition manifest differs from D3c audit")
    for capture in audit["captures"]:
        row = db.execute(
            "SELECT c.*,p.policy_revision_id FROM source_captures c "
            "JOIN capture_policy_links p ON p.capture_id=c.id WHERE c.id=%s",
            (capture["capture_id"],),
        ).fetchone()
        if row is None or any(
            not metadata_equal(value, capture["capture_id" if key == "id" else key])
            for key, value in row.items()
        ):
            raise ValueError("Capture metadata or policy differs from D3c audit")
        attempt = db.execute(
            "SELECT a.id FROM source_fetch_attempts a "
            "JOIN analysis_stage_attempts s ON s.id=a.stage_attempt_id "
            "WHERE a.completed_capture_id=%s AND a.state='complete' AND a.http_status=200 "
            "AND a.policy_revision_id=%s AND s.execution_id=%s AND s.state='completed' "
            "AND s.error_code IS NULL AND s.error_detail IS NULL",
            (capture["capture_id"], capture["policy_revision_id"], audit["execution_id"]),
        ).fetchall()
        expected_attempts = [
            item["attempt_id"]
            for fetch in manifest["fetch_results"]
            if any(r["capture_id"] == capture["capture_id"] for r in fetch["records"])
            for item in fetch["attempts"]
            if item["outcome"] == "complete"
        ]
        if [str(row["id"]) for row in attempt] != expected_attempts:
            raise ValueError("Capture lacks its reviewed successful execution attempt")


def database_snapshot(db: Database) -> dict[str, Any]:
    snapshot = {}
    for table in TABLES:
        rows = db.execute(
            sql.SQL("SELECT to_jsonb(t) AS row FROM {} t").format(sql.Identifier(table))
        ).fetchall()
        encoded = sorted(
            json.dumps(row["row"], sort_keys=True, separators=(",", ":")) for row in rows
        )
        snapshot[table] = {
            "count": len(rows),
            "sha256": hashlib.sha256("\n".join(encoded).encode()).hexdigest(),
        }
    return snapshot


def application_review() -> dict[str, Any]:
    audit = read_audit(ROOT)
    archive = LocalArchive(ROOT / "var/raw")
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as db, db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        db.execute("SET LOCAL TIME ZONE 'UTC'")
        before = database_snapshot(db)
        verify_database_evidence(db, audit, archive)
        result = review_bodies(audit, archive)
        after = database_snapshot(db)
        if before != after:
            raise RuntimeError("Identity review changed the database snapshot")
    result["database_snapshot"] = after
    result["database_transaction"] = "repeatable_read_read_only"
    result["same_snapshot_before_after"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("review", "check-registration"))
    args = parser.parse_args()
    result = application_review()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if args.action == "check-registration" and not result["registration_ready"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        etree.XMLSyntaxError,
        psycopg.Error,
    ) as error:
        # Driver exceptions can contain credentials; emit the class, never the message/DSN.
        print(
            f"CRCL identity review failed ({type(error).__name__}); inspect local evidence.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
