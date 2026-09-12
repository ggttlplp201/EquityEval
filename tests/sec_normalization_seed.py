"""Reviewed archived cohort inputs, separate from expected financial outputs.

The narrow coverage declarations below reference S1 review evidence. They make no
claim that a selected single filing is a complete historical/event inventory.
"""

import gzip
import json
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from equity_ingest.financial_types import (
    Completeness,
    CoverageRequest,
    EvidenceCapture,
    FilingMetadata,
    NormalizationInput,
    ScopeSpec,
    canonical_json,
    content_hash,
    evidence_id,
)
from equity_ingest.sec_normalize import period_spec, reviewed_cohort_rules, unit_spec
from equity_schema.concepts import Concept

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/research/s1/evidence"
PACKET = json.loads((ROOT / "tests/golden/sec_normalized_cohort.json").read_text())


def cohort_input(ticker: str) -> tuple[bytes, NormalizationInput]:
    """The JSON fixture supplies only independent anchor identity/date metadata here."""
    anchor = next(item for item in PACKET["companies"] if item["ticker"] == ticker)
    source = next(
        item
        for item in json.loads((EVIDENCE / "manifest.json").read_text())["requests"]
        if item["ticker"] == ticker
    )
    issuer = evidence_id("test-issuer", anchor["cik"])
    source_id = evidence_id("test-source", "sec-companyfacts")
    fetched = datetime.fromisoformat(source["fetched_at"])
    capture = EvidenceCapture(
        evidence_id("test-capture", source["raw_file"]),
        source_id,
        f"companyfacts:{anchor['cik']}",
        source["url"],
        source["raw_sha256"],
        source["raw_bytes"],
        fetched,
        fetched,
        "financial_facts",
    )
    body = gzip.decompress((EVIDENCE / source["raw_file"]).read_bytes())
    original = next(
        item
        for item in json.loads((EVIDENCE / "filing-manifest.json").read_text())["requests"]
        if item["id"] == ("KHC-restatement-note" if ticker == "KHC" else f"{ticker}-filing")
        and item["status"] == "archived"
    )
    document_time = datetime.fromisoformat(original["fetched_at"])
    document = EvidenceCapture(
        evidence_id("test-capture", original["raw_file"]),
        evidence_id("test-source", "sec-filing"),
        f"filing:{anchor['accession']}",
        original["url"],
        original["raw_sha256"],
        original["raw_bytes"],
        document_time,
        document_time,
        "reviewed_coverage",
    )
    filing = FilingMetadata(
        evidence_id("test-filing-version", anchor["accession"]),
        evidence_id("test-filing", anchor["accession"]),
        issuer,
        anchor["accession"],
        capture.id,
        date.fromisoformat(anchor["filed"]),
        "20-F" if ticker == "TSM" else "10-K",
        original["url"],
        content_hash({key: anchor[key] for key in ("cik", "accession", "filed", "start", "end")}),
        date.fromisoformat(anchor["end"]),
    )
    currency = unit_spec("TWD" if ticker == "TSM" else "USD")
    requests = []
    for index, concept in enumerate(Concept, 1):
        start = date.fromisoformat(anchor["start"]) if index <= 16 or index >= 35 else None
        period = period_spec(start, date.fromisoformat(anchor["end"]))
        if concept in {Concept.NET_INCOME_PARENT, Concept.EQUITY_PARENT}:
            kind, instrument = "parent", None
        elif 13 <= index <= 17:
            kind = "ordinary_common_shares" if ticker == "TSM" else "all_reported_common_classes"
            instrument = evidence_id("test-instrument", [ticker, kind])
        else:
            kind, instrument = "consolidated", None
        descriptor = canonical_json(
            {
                "consolidation": kind,
                "instrument": str(instrument) if instrument else None,
                "context_knowledge": "unknown",
                "scope_evidence": "docs/research/s1/concept-map.md",
                "cash_scope": "corporate_cash_excluding_holder_reserves"
                if ticker == "CRCL" and concept == Concept.CASH_AND_CASH_EQUIVALENTS
                else "not_applicable",
                "payment_basis": "cash_flow_addback"
                if concept == Concept.SHARE_BASED_COMPENSATION
                else "actual_cash_payment"
                if concept
                in {
                    Concept.DIVIDENDS_PAID,
                    Concept.SHARE_REPURCHASES,
                    Concept.CAPITAL_EXPENDITURES_PPE,
                }
                else "as_reported",
                "revenue_basis": "net_of_operating_interest"
                if ticker == "JPM" and concept == Concept.REVENUE
                else "reported_complete_scope",
            }
        )
        scope = ScopeSpec(
            evidence_id("test-scope", [issuer, descriptor]),
            issuer,
            instrument,
            kind,
            1,
            descriptor,
            content_hash(json.loads(descriptor)),
        )
        family = "income" if index <= 16 else "balance_sheet" if index <= 34 else "cash_flow"
        if index == 17:
            family = "other"
        state = "source_missing" if ticker == "TSM" and index != 17 else "covered"
        requests.append(
            CoverageRequest(
                evidence_id(
                    "test-coverage-request", [filing.id, period.id, scope.id, family, concept.value]
                ),
                filing.id,
                period,
                scope,
                currency,
                family,
                "ifrs" if ticker == "TSM" else "us_gaap",
                "periodic_complete",
                "audited" if index != 17 else "unknown",
                state,
                f"docs/research/s1/concept-map.md#{ticker}:{anchor['accession']}",
                (concept,),
                "annual" if start else "instant",
            )
        )
    # Different concepts sharing one scope/period/family need one coverage row.
    grouped: dict[tuple[Any, ...], CoverageRequest] = {}
    for request in requests:
        key = (
            request.filing_version_id,
            request.period.id,
            request.scope.id,
            request.statement_family,
        )
        if key in grouped:
            previous = grouped[key]
            grouped[key] = replace(previous, concepts=previous.concepts + request.concepts)
        else:
            grouped[key] = replace(request, id=evidence_id("test-coverage-request", key))
    requested = tuple(grouped.values())
    unknown = Completeness(
        "unknown",
        date(1990, 1, 1),
        date(2026, 9, 12),
        ("S1 inspected anchors do not establish exhaustive filing/event history",),
    )
    return body, NormalizationInput(
        issuer,
        anchor["cik"],
        capture.id,
        (capture, document),
        (filing,),
        requested,
        reviewed_cohort_rules(anchor["cik"], (filing,), requested),
        evidence_id("test-mapping", ticker),
        "companyfacts-json-v1",
        "companyfacts-reviewed-v1",
        "sec-reviewed-s1-v1",
        datetime(2026, 9, 12, tzinfo=UTC),
        unknown,
        unknown,
    )
