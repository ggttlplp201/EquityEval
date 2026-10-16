"""D049 bounded FY2025 accounting review; earlier comparative history stays blocked."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any

from equity_ingest.archive import LocalArchive
from equity_ingest.filing import extract_inline_filing, select_filing_fact
from lxml import html

from scripts.normalize_crcl import ACCESSION, CIK, RESOURCES, ROOT
from scripts.review_crcl_exhibits import clean
from scripts.review_crcl_identity import normalized_text
from scripts.review_crcl_observation import retained_captures

REPORT = "docs/research/crcl-broader-review-2026-10-15.json"
ORIGINAL_SHA = "e535360770ac9230b871b4a4f9ab74336f790aa089f3dd0a078be83e517bbd4c"
# Exact directly reported values, not calculation results or arithmetic substitutes.
SPECS = {
    "operating_income": ("OperatingIncomeLoss", "-96435000", "income", "c-1"),
    "revenue": ("Revenues", "2746642000", "income", "c-1"),
    "net_income_consolidated": ("ProfitLoss", "-69518000", "income", "c-1"),
    "cash_from_operating_activities": (
        "NetCashProvidedByUsedInOperatingActivities",
        "542129000",
        "cash_flow",
        "c-1",
    ),
    "capital_expenditures_ppe": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "12432000",
        "cash_flow",
        "c-1",
    ),
    "current_assets": ("AssetsCurrent", "77801467000", "balance_sheet", "c-6"),
    "current_liabilities": ("LiabilitiesCurrent", "75328395000", "balance_sheet", "c-6"),
    "total_assets": ("Assets", "78713207000", "balance_sheet", "c-6"),
    "total_liabilities": ("Liabilities", "75382434000", "balance_sheet", "c-6"),
    "equity_including_noncontrolling_interests": (
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "3330773000",
        "balance_sheet",
        "c-6",
    ),
}
ELIGIBLE = (
    "operating_margin",
    "net_margin_consolidated",
    "free_cash_flow_ppe",
    "free_cash_flow_margin_ppe",
    "current_ratio",
    "net_working_capital",
)
BLOCKED = {
    "gross_margin": (
        "No directly reported consolidated gross-profit operand is mapped; "
        "distribution/transaction costs are not a reviewed gross-profit definition."
    ),
    "gross_margin_derived": (
        "No reviewed complete-scope cost-of-revenue operand; do not substitute "
        "distribution/transaction costs or invent a subtotal."
    ),
    "revenue_growth_yoy": (
        "FY2024 comparative amount exists, but earlier draft/correspondence history "
        "is unretained. Review exact missing bodies and original/comparative "
        "edition coverage before normalizing the earlier period."
    ),
    "return_on_assets": (
        "Opening 2024-12-31 assets exist as a later comparative, but earlier "
        "draft/correspondence history is unretained. Earlier-period eligibility is "
        "unproved; closing assets alone cannot supply ROA."
    ),
}
FINDINGS = {
    "attribution": (
        "Use consolidated ProfitLoss, including NCI, rather than parent "
        "NetIncomeLoss. Tax and non-operating effects remain in reported net loss; "
        "no adjusted or recurring-profit claim."
    ),
    "cash_flow": (
        "Stablecoin-holder deposit changes are financing flows. CFO includes "
        "reserve-income receipts and operating working-capital effects. CFO minus "
        "cash PPE purchases excludes capitalized software, acquisitions and other "
        "investing; it is not issuer-discretionary cash."
    ),
    "liquidity": (
        "Current assets include segregated holder reserves and corporate-held "
        "stablecoin reserves; current liabilities include holder deposits. Current "
        "ratio and working capital describe these reported gross consolidated "
        "totals, not freely available corporate liquidity. No reserve netting."
    ),
    "equity": (
        "Use permanent consolidated equity including NCI for the closing FY2025 "
        "identity. FY2024 redeemable preferred equity is separate; the existing "
        "three-term identity cannot represent that earlier presentation without "
        "further review."
    ),
    "history": (
        "Comparative source rows are inspectable, but no complete 3/5/10-year "
        "analysis history or original historical application knowledge is asserted."
    ),
}


def retained() -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    rows = retained_captures(ROOT)
    if len(rows) != 71:
        raise ValueError("D5i retained lineage changed")
    archive = LocalArchive(ROOT / "var/raw")
    bodies = {
        r["capture_id"]: archive.read_blob(r["blob_key"], r["body_sha256"], r["byte_count"])
        for r in rows
    }
    return rows, bodies


def selected_facts() -> tuple[dict[str, Any], dict[str, Any]]:
    rows, bodies = retained()
    row = max(
        (r for r in rows if r["source_object_key"] == RESOURCES[0]), key=lambda r: r["completed_at"]
    )
    return json.loads(bodies[row["capture_id"]]), row


def validate_selected_facts(document: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for concept, (tag, value, family, _) in SPECS.items():
        entries = (
            document.get("facts", {})
            .get("us-gaap", {})
            .get(tag, {})
            .get("units", {})
            .get("USD", [])
        )
        matches = [
            (i, r)
            for i, r in enumerate(entries)
            if r.get("accn") == ACCESSION
            and r.get("end") == "2025-12-31"
            and r.get("start") == (None if family == "balance_sheet" else "2025-01-01")
        ]
        if len(matches) != 1 or Decimal(str(matches[0][1]["val"])) != Decimal(value):
            raise ValueError(f"Exact consolidated FY2025 source differs: {concept}")
        i, row = matches[0]
        if row.get("form") != "10-K" or row.get("filed") != "2026-03-09":
            raise ValueError("Selected edition metadata changed")
        result[concept] = {
            "value": value,
            "row": row,
            "locator": f"$.facts.us-gaap.{tag}.units.USD[{i}]",
        }
    return result


def original_proof(body: bytes, capture: dict[str, Any]) -> dict[str, Any]:
    if capture["body_sha256"] != ORIGINAL_SHA or hashlib.sha256(body).hexdigest() != ORIGINAL_SHA:
        raise ValueError("Original audited body changed; substantive review required")
    extraction = extract_inline_filing(
        body,
        expected_sha256=ORIGINAL_SHA,
        expected_byte_count=capture["byte_count"],
        expected_cik=CIK,
    )
    contexts = {c.id: c for c in extraction.contexts}
    proof = {}
    for concept, (tag, value, family, context) in SPECS.items():
        c = contexts[context]
        if (
            not c.valid
            or c.dimensions
            or c.cik != CIK
            or c.end_date != date(2025, 12, 31)
            or c.start_date != (None if family == "balance_sheet" else date(2025, 1, 1))
        ):
            raise ValueError("Selected context/scope changed")
        selected = select_filing_fact(
            extraction,
            qualified_tag="{http://fasb.org/us-gaap/2025}" + tag,
            context_id=context,
            unit_id="usd",
            expected_dimensions=(),
        )
        f = selected.fact
        if (
            selected.status != "observed"
            or selected.value != Decimal(value)
            or f is None
            or f.scale != 3
            or f.decimals != "-3"
        ):
            raise ValueError("Selected inline sign/scale/precision changed")
        proof[concept] = {
            "capture_id": capture["capture_id"],
            "body_sha256": ORIGINAL_SHA,
            "url": capture["request_url"],
            "retrievedAt": capture["completed_at"],
            "accession": ACCESSION,
            "fact": asdict(f),
            "context": asdict(c),
        }
    return proof


def review() -> dict[str, Any]:
    from scripts.publish_crcl_observation import checked_preparation
    from scripts.review_crcl_broader_events import review_bodies

    old, _ = checked_preparation()
    rows, bodies = retained()
    expanded = review_bodies(rows, bodies)
    original = next(r for r in rows if r["source_object_key"] == RESOURCES[2])
    proof = original_proof(bodies[original["capture_id"]], original)
    latest = max(
        (r for r in rows if r["source_object_key"] == RESOURCES[0]), key=lambda r: r["completed_at"]
    )
    operands = validate_selected_facts(json.loads(bodies[latest["capture_id"]]))
    vintages = []
    for row in rows:
        if row["source_object_key"] == RESOURCES[0]:
            selected = validate_selected_facts(json.loads(bodies[row["capture_id"]]))
            vintages.append(
                {
                    "captureId": row["capture_id"],
                    "bodySha256": row["body_sha256"],
                    "retrievedAt": row["completed_at"],
                    "url": row["request_url"],
                    "selectedRows": selected,
                }
            )
    comparisons = []
    for row in rows:
        if row["source_object_key"].endswith(("/crcl-20260331.htm", "/crcl-20260630.htm")):
            extraction = extract_inline_filing(
                bodies[row["capture_id"]],
                expected_sha256=row["body_sha256"],
                expected_byte_count=row["byte_count"],
                expected_cik=CIK,
            )
            contexts = {c.id: c for c in extraction.contexts}
            for concept, (tag, value, family, _) in SPECS.items():
                if family != "balance_sheet":
                    continue
                found = [
                    f
                    for f in extraction.facts
                    if f.qualified_tag.endswith("}" + tag)
                    and f.context_id in contexts
                    and contexts[f.context_id].valid
                    and contexts[f.context_id].end_date == date(2025, 12, 31)
                    and contexts[f.context_id].start_date is None
                    and not contexts[f.context_id].dimensions
                    and f.unit_id == "usd"
                ]
                if not found or any(f.value != Decimal(value) for f in found):
                    raise ValueError("Later comparative balance differs or is missing")
                comparisons.append(
                    {
                        "captureId": row["capture_id"],
                        "bodySha256": row["body_sha256"],
                        "url": row["request_url"],
                        "retrievedAt": row["completed_at"],
                        "concept": concept,
                        "consistent": True,
                        "facts": [asdict(f) for f in found],
                    }
                )
    doc = html.fromstring(bodies[original["capture_id"]])
    text = clean(normalized_text(doc))
    quotes = [
        "Net changes in deposits held for stablecoin holders",
        "Capitalization of software development costs",
        "Cash and cash equivalents segregated for the benefit of stablecoin holders",
        "Deposits from stablecoin holders",
        "had no impact on previously reported total assets, total liabilities and net income",
        "not available for general use",
    ]
    if any(q not in text for q in quotes):
        raise ValueError("Reviewed accounting policy evidence missing")
    inventory = max(
        (r for r in rows if r["source_object_key"] == RESOURCES[1]), key=lambda r: r["completed_at"]
    )
    source = json.loads(bodies[inventory["capture_id"]])
    if source["filings"]["files"]:
        raise ValueError("Additional inventory archives need review")
    recent = source["filings"]["recent"]
    missing = []
    retained_keys = {r["source_object_key"] for r in rows}
    for i, form in enumerate(recent["form"]):
        if (
            form not in {"DRS", "DRS/A", "DRSLTR", "UPLOAD"}
            or recent["filingDate"][i] < "2024-12-31"
        ):
            continue
        key = f"filing_document/{CIK}/{recent['accessionNumber'][i]}/{recent['primaryDocument'][i]}"
        if key not in retained_keys:
            if recent["filingDate"][i] >= "2025-12-31":
                raise ValueError("Unreviewed later draft/correspondence blocks FY2025 too")
            missing.append(
                {
                    "resourceKey": key,
                    "form": form,
                    "filedDate": recent["filingDate"][i],
                    "reason": (
                        "Body unretained; relevance and publication-time history "
                        "not inferable from metadata"
                    ),
                    "acquisitionContract": "PDF extension unsupported by BootstrapPlan"
                    if key.endswith(".pdf")
                    else "Existing HTML resource shape",
                    "inventoryCaptureId": inventory["capture_id"],
                }
            )
    if len(missing) != 9:
        raise ValueError("Pinned earlier history roster changed")
    tables = list(doc.iter("table"))
    comparative = []
    extraction = extract_inline_filing(
        bodies[original["capture_id"]],
        expected_sha256=ORIGINAL_SHA,
        expected_byte_count=original["byte_count"],
        expected_cik=CIK,
    )
    contexts = {c.id: c for c in extraction.contexts}
    for fact in extraction.facts:
        c = contexts.get(fact.context_id or "")
        if (
            c
            and not c.dimensions
            and c.start_date in {date(2023, 1, 1), date(2024, 1, 1)}
            and fact.qualified_tag.split("}")[-1]
            in {
                "Revenues",
                "ProfitLoss",
                "NetCashProvidedByUsedInOperatingActivities",
                "PaymentsToAcquirePropertyPlantAndEquipment",
            }
        ):
            comparative.append(
                {
                    "fact": asdict(fact),
                    "context": asdict(c),
                    "captureId": original["capture_id"],
                    "analysisEligible": False,
                }
            )
    return {
        "kind": "d5k-broader-fundamentals-review",
        "status": "ready_for_fy2025_preparation",
        "sourceObservation": old.inputs.captured_before.isoformat(),
        "coverageStart": "2025-12-31",
        "eligibleMetrics": list(ELIGIBLE),
        "blockedMetrics": BLOCKED,
        "operands": operands,
        "precisionProof": proof,
        "parentNetIncome": "-69508000",
        "findings": FINDINGS,
        "accountingQuotes": quotes,
        "statementTables": [
            {
                "index": i,
                "text": clean(normalized_text(tables[i])),
                "captureId": original["capture_id"],
                "bodySha256": ORIGINAL_SHA,
            }
            for i in (25, 26, 27, 30, 31)
        ],
        "factsVintages": vintages,
        "balanceComparisons": comparisons,
        "missingHistoryBodies": missing,
        "historicalAnalysisEligible": False,
        "comparativeSourceRows": comparative,
        "lineage": [
            {
                "captureId": r["capture_id"],
                "resourceKey": r["source_object_key"],
                "bodySha256": r["body_sha256"],
                "url": r["request_url"],
                "retrievedAt": r["completed_at"],
            }
            for r in rows
        ],
        "expandedLineReview": expanded,
    }


def main() -> None:
    from equity_ingest.financial_types import canonical_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = canonical_json(review()) + "\n"
    path = ROOT / REPORT
    if args.check:
        if path.read_text() != text:
            raise ValueError("Broader review differs from deterministic replay")
    else:
        path.write_text(text)
    print(REPORT)


if __name__ == "__main__":
    main()
