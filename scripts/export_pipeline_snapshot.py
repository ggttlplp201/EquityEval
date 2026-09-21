"""Export a sanitized development snapshot from D3c/D3d audits and D3f research.

Use python -m scripts.export_pipeline_snapshot for the optional application check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ACQUISITION = "docs/research/crcl-pinned-bootstrap-2026-09-21.json"
REVIEW = "docs/research/crcl-quote-identity-review-2026-09-21.json"
REVIEW_SHA = "4f6c25d275d87ecd41a6b40ade9eb2cb75179a9b385dc554cc24ea2ab4474c99"
SEARCH = "docs/research/crcl-quote-currency-search-2026-09-21.json"
SEARCH_SHA = "229c3ac229324e209bc72adddfbaf29d09928e3058174bb94f34bbb5bdb41b5a"
OUTPUT = "apps/web/src/features/pipeline/snapshot.ts"
CAPTURE_LABELS = (
    "Company Facts",
    "Issuer Submissions",
    "FY2025 annual report",
    "FY2025 annual amendment",
    "Q2 2026 quarterly report",
)
FIELD_LABELS = {
    "symbol": "Trading symbol",
    "exchange_code": "Exchange code",
    "share_class": "Share class",
    "valid_from": "Listing start",
    "quote_currency": "Quote currency",
}
COUNT_LABELS = {
    "source_captures": "Captures",
    "source_fetch_attempts": "Fetch attempts",
    "analysis_requests": "Bootstrap requests",
    "issuers": "Issuer records",
    "securities": "Security records",
    "security_identifiers": "Quote identifiers",
    "watchlist_memberships": "Watchlist memberships",
    "normalization_batches": "Normalization batches",
}


def utc_label(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError("The reviewed capture audit requires explicit UTC timestamps")
    return parsed.isoformat().replace("+00:00", "Z")


def source_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc not in {"www.sec.gov", "data.sec.gov"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only reviewed public SEC source URLs may reach the UI")
    return value


def project(acquisition: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """Explicit field projection; never serialize audit dictionaries wholesale."""
    if (
        review["request_id"] != acquisition["request_id"]
        or review["captures"] != acquisition["captures"]
        or review["identity_capture_id"]
        != acquisition["acquisition_result"]["readiness"]["identity_capture_id"]
        or review["registration_ready"] is not False
        or review["ordinary_request_eligible"] is not False
        or review["financial_result"] is not False
        or review["blocking_reasons"] != ["quote_currency_unsubstantiated"]
    ):
        raise ValueError("This UI projection requires the reviewed blocked D3c/D3d state")
    fields = review["fields"]
    if fields["quote_currency"]["value"] is not None or fields["quote_currency"]["evidence"]:
        raise ValueError("Quote currency must remain missing in this reviewed snapshot")
    captures = [
        {
            "id": item["capture_id"],
            "label": label,
            "url": source_url(item["request_url"]),
            "sha256": item["body_sha256"],
            "bytes": item["byte_count"],
            "httpStatus": item["http_status"],
            "requestedAt": utc_label(item["requested_at"]),
            "capturedAt": utc_label(item["completed_at"]),
        }
        for label, item in zip(CAPTURE_LABELS, review["captures"], strict=True)
    ]
    capture_ids = {item["id"] for item in captures}

    def evidence(items: list[dict[str, Any]]) -> list[dict[str, str]]:
        result = []
        for item in items:
            if item["capture_id"] not in capture_ids:
                raise ValueError("Identity evidence must refer to a displayed source capture")
            result.append(
                {
                    "captureId": item["capture_id"],
                    "locator": item["locator"],
                    "excerpt": item["value"],
                }
            )
        return result

    identity_id = review["identity_capture_id"]
    # D3d's pinned replay verifies these exact Submissions fields against the raw body.
    # The audit preserves CIK in the plan; its issuer-name check is in review_crcl_identity.py.
    identity_fields = [
        {
            "id": "cik",
            "label": "SEC issuer identifier (CIK)",
            "value": acquisition["bootstrap_plan"]["cik"],
            "status": "supported",
            "evidence": [{"captureId": identity_id, "locator": "/cik", "excerpt": "0001876042"}],
        },
        {
            "id": "name",
            "label": "Issuer name",
            "value": "Circle Internet Group, Inc.",
            "status": "supported",
            "evidence": [
                {
                    "captureId": identity_id,
                    "locator": "/name",
                    "excerpt": "Circle Internet Group, Inc.",
                }
            ],
        },
        *[
            {
                "id": key,
                "label": label,
                "value": fields[key]["value"],
                "status": "unsubstantiated" if fields[key]["value"] is None else "supported",
                "evidence": evidence(fields[key]["evidence"]),
            }
            for key, label in FIELD_LABELS.items()
        ],
    ]
    counts = [
        {"id": key, "label": label, "value": review["database_snapshot"][key]["count"]}
        for key, label in COUNT_LABELS.items()
    ]
    return {
        "kind": "real-application-pipeline-snapshot",
        "ticker": "CRCL",
        "reviewedOn": "2026-09-21",
        "acquisitionVerifiedAt": utc_label(acquisition["verified_at"]),
        "reviewCheckpoint": "61524a7 / milestone/d3d-identity-review",
        "requestId": review["request_id"],
        "executionId": review["execution_id"],
        "acquisitionAuditSha256": review["audit_sha256"],
        "identityAuditSha256": REVIEW_SHA,
        "counts": counts,
        "captures": captures,
        "identityFields": identity_fields,
        "reportingCurrencyEvidence": evidence(
            review["excluded_currency_evidence"]["reporting_currency"]
        ),
        "plan": {
            "inventoryStart": acquisition["bootstrap_plan"]["inventory_start"],
            "inventoryEnd": acquisition["bootstrap_plan"]["inventory_end"],
            "resources": list(CAPTURE_LABELS),
            "hash": acquisition["request_parameters_hash"],
            "policy": "SEC public filings · reviewed 2026-09-21",
        },
        "blocker": {
            "code": review["blocking_reasons"][0],
            "title": "Quote currency needs source evidence",
            "explanation": (
                "The reviewed captures do not explicitly establish the currency in "
                "which CRCL's NYSE Class A shares are quoted. Reporting currency "
                "and offering-price units cannot fill this gap."
            ),
            "nextAction": (
                "Obtain and archive authoritative evidence linking this listing to "
                "its quote currency and effective dates. Review that evidence "
                "before registering a quote identifier or starting ordinary "
                "analysis."
            ),
        },
        "stages": [
            {
                "id": "plan",
                "number": "01",
                "label": "Pinned acquisition plan",
                "status": "verified",
                "statusLabel": "Pinned",
                "summary": (
                    "The request fixes its issuer, reviewed source policy, "
                    "inventory window and five exact resources."
                ),
            },
            {
                "id": "captures",
                "number": "02",
                "label": "Source captures",
                "status": "verified",
                "statusLabel": "Captured",
                "summary": (
                    "Five successful captures belong to this pinned request. The "
                    "application totals below include earlier bootstrap requests."
                ),
            },
            {
                "id": "identity",
                "number": "03",
                "label": "Identity review",
                "status": "gap",
                "statusLabel": "Reviewed · one gap",
                "summary": (
                    "Issuer identity, share class and listing start are supported. "
                    "Quote currency remains unsubstantiated."
                ),
            },
            {
                "id": "registration",
                "number": "04",
                "label": "Quote registration",
                "status": "blocked",
                "statusLabel": "Blocked",
                "summary": (
                    "No quote identifier has been registered. Capture readiness "
                    "only enabled an identity review."
                ),
            },
            {
                "id": "normalization",
                "number": "05",
                "label": "Financial normalization",
                "status": "not-started",
                "statusLabel": "Not started",
                "summary": (
                    "No application normalization batch has been created. Stored "
                    "source bodies are not published financial facts."
                ),
            },
            {
                "id": "analysis",
                "number": "06",
                "label": "Analysis / publication",
                "status": "not-started",
                "statusLabel": "Not started",
                "summary": (
                    "Ordinary analysis is blocked. There is no completed financial "
                    "analysis or published result from these requests."
                ),
            },
        ],
    }


def research_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc
        not in {
            "www.sec.gov",
            "www.nyse.com",
            "ftp.nyse.com",
            "www.ice.com",
            "investor.circle.com",
            "www.circle.com",
        }
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only reviewed public research URLs may reach the UI")
    return value


def project_search(search: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """Project authored search notes; they can never authorize registration."""
    target = search["target"]
    expected = {
        "cik": "0001876042",
        "issuer": "Circle Internet Group, Inc.",
        **{
            key: review["fields"][key]["value"]
            for key in (
                "symbol",
                "exchange_code",
                "share_class",
            )
        },
        "listing_start": review["fields"]["valid_from"]["value"],
    }
    if target != expected or search["identity_audit_sha256"] != REVIEW_SHA:
        raise ValueError("Currency search must bind to the reviewed Circle Class A identity")
    if (
        search["version"] != "crcl-currency-search-v1"
        or search["outcome"] != "blocked"
        or search["blocking_reasons"] != review["blocking_reasons"]
        or search["registration_ready"] is not False
        or review["registration_ready"] is not False
        or search["quote_currency"] is not None
        or search["quote_currency_valid_from"] is not None
        or search["new_capture_ids"] != []
        or search["new_policy_revision_ids"] != []
    ):
        raise ValueError("Search notes are not new capture, currency or registration evidence")
    sources = []
    seen = set()
    for source in search["sources"]:
        if source["id"] in seen or source["application_evidence"] not in {
            "none",
            "existing-captures-only",
        }:
            raise ValueError("Search sources must be unique and cannot claim new captures")
        seen.add(source["id"])
        sources.append(
            {
                "id": source["id"],
                "label": source["label"],
                "url": research_url(source["url"]),
                "statusLabel": source["status_label"],
                "method": source["method"],
                "finding": source["finding"],
                "dateContext": source["date_context"],
                "policy": source["policy"],
                "links": [
                    {"label": link["label"], "url": research_url(link["url"])}
                    for link in source.get("related_urls", [])
                ],
            }
        )
    if not sources:
        raise ValueError("The bounded search requires its source review notes")
    return {
        "reviewedOn": search["reviewed_on"],
        "sha256": SEARCH_SHA,
        "basis": search["basis"],
        "summary": search["summary"],
        "effectiveDateRule": search["effective_date_rule"],
        "nextAction": search["next_action"],
        "sources": sources,
    }


def read_pinned_audits(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    acquisition_raw = (root / ACQUISITION).read_bytes()
    review_raw = (root / REVIEW).read_bytes()
    review = json.loads(review_raw)
    if (
        hashlib.sha256(review_raw).hexdigest() != REVIEW_SHA
        or hashlib.sha256(acquisition_raw).hexdigest() != review["audit_sha256"]
    ):
        raise ValueError("Pinned D3c/D3d audit changed; review the new state before exporting")
    search_raw = (root / SEARCH).read_bytes()
    if hashlib.sha256(search_raw).hexdigest() != SEARCH_SHA:
        raise ValueError("Pinned D3f search changed; review the new findings before exporting")
    return json.loads(acquisition_raw), review, json.loads(search_raw)


def verify_application(root: Path = ROOT) -> None:
    # Optional operator check only. Normal export/build/tests never open application storage.
    from scripts.review_crcl_identity import application_review

    _, expected, _ = read_pinned_audits(root)
    if application_review() != expected:
        raise ValueError("Application evidence or counts drifted from the reviewed snapshot")


def export(root: Path = ROOT) -> str:
    acquisition, review, search = read_pinned_audits(root)
    result = project(acquisition, review)
    result["currencySearch"] = project_search(search, review)
    result["blocker"]["nextAction"] = result["currencySearch"]["nextAction"]
    return (
        "// Generated by scripts/export_pipeline_snapshot.py; do not hand edit.\n"
        "// Sanitized development snapshot, not a live status service or S6 API.\n"
        'import type { PipelineSnapshot } from "./types";\n\n'
        "const snapshot = "
        + json.dumps(result, indent=2, ensure_ascii=False)
        + " satisfies PipelineSnapshot;\n\nexport default snapshot;\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--verify-application",
        action="store_true",
        help="Replay existing archived identity evidence in a read-only transaction",
    )
    args = parser.parse_args()
    rendered = export()
    if args.verify_application:
        try:
            verify_application()
        except Exception as error:
            # Database exceptions may include connection details; never print their message.
            print(
                f"Application snapshot verification failed ({type(error).__name__}).",
                file=sys.stderr,
            )
            raise SystemExit(1) from None
    destination = ROOT / OUTPUT
    if args.check:
        if destination.read_text() != rendered:
            raise SystemExit("Pipeline snapshot differs from its reviewed source audits")
    else:
        destination.write_text(rendered)
    if args.verify_application:
        print("Application evidence and counts match the pinned snapshot; registration blocked.")


if __name__ == "__main__":
    main()
