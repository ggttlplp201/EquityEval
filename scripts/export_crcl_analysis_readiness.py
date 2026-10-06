"""Export a checked D5b readiness view from the immutable D5a projection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.normalize_crcl import ROOT

NORMALIZATION = "apps/web/src/features/normalization/snapshot.json"
NORMALIZATION_SHA = "75df95334e317ffabaede646309dff1bc5a53eb0b52eb650cb700e0436dada06"
PROVENANCE = "docs/research/crcl-normalization-provenance-2026-09-30.json"
PROVENANCE_SHA = "1a1c2f2193654888eabd761821040d1f62f677210b3c9a3f697b246e1d2904e3"
OUTPUT = "apps/web/src/features/analysis-readiness/snapshot.json"
MANIFEST = "apps/web/src/features/analysis-readiness/manifest.ts"
BATCH_ID = "923458e4-242d-4731-9f57-9fd6779d7e9a"
EXPECTED_FACTS = (
    ("revenue", "Revenue and reserve income", "2746642000", "$2.75B"),
    ("operating_income", "Operating income (loss)", "-96435000", "−$96.44M"),
)
REASON_CODES = ("inventory_history_incomplete", "event_history_incomplete")


def rows_by_label(detail: dict[str, Any], heading: str) -> dict[str, str]:
    sections = [section for section in detail["sections"] if section["heading"] == heading]
    if len(sections) != 1:
        raise ValueError(f"Expected one {heading!r} section")
    rows = sections[0]["rows"]
    labels = [row["label"] for row in rows]
    if len(labels) != len(set(labels)):
        raise ValueError(f"Duplicate row in {heading!r}")
    return {row["label"]: row["value"] for row in rows}


def project(normalization: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    if (
        normalization.get("kind") != "real-crcl-normalization"
        or normalization.get("batchId") != BATCH_ID
        or normalization.get("periodLabel") != "FY2025"
        or normalization.get("factCount") != 2
        or normalization.get("flagCount") != 2
        or provenance.get("batch_id") != BATCH_ID
        or provenance.get("snapshot_sha256") != NORMALIZATION_SHA
    ):
        raise ValueError("Reviewed D5a normalization identity changed")

    views = normalization.get("views", {})
    if set(views) != {"as_filed", "before_filing", "original"}:
        raise ValueError("Reviewed D5a view roster changed")
    facts = views["as_filed"].get("facts", [])
    actual_facts = [(row.get("id"), row.get("label"), row.get("value")) for row in facts]
    expected_facts = []
    for fact_id, label, exact_value, _ in EXPECTED_FACTS:
        expected_facts.append((fact_id, label, exact_value))
    if actual_facts != expected_facts:
        raise ValueError("Reviewed D5a fact roster or signed value changed")

    eligibility = normalization["details"]["eligibility"]
    flag_rows = rows_by_label(eligibility, "Retained source-history flags")
    if tuple(flag_rows) != REASON_CODES or not all(
        flag_rows[code].startswith("error · ") for code in REASON_CODES
    ):
        raise ValueError("Reviewed D5a blocking flags changed")
    prerequisites = rows_by_label(eligibility, "Next prerequisites")
    if (
        prerequisites.get("Valuation eligibility") != "False"
        or prerequisites.get("Financial analysis") != "N/A"
    ):
        raise ValueError("Reviewed D5a eligibility changed")

    inputs = []
    details = {}
    expected_chain: list[str] | None = None
    for fact_id, label, exact_value, display_value in EXPECTED_FACTS:
        detail_id = f"as_filed:{fact_id}"
        detail = normalization["details"][detail_id]
        selection = rows_by_label(detail, "Point-in-time selection")
        chain = provenance["details"][detail_id]["source_chain_capture_ids"]
        if (
            selection.get("Exact value (USD)") != exact_value
            or selection.get("Status") != "observed"
            or selection.get("PIT flags") != "blocking_quality_flag"
            or selection.get("Eligible for valuation") != "False"
            or len(chain) != 3
            or len(set(chain)) != 3
        ):
            raise ValueError(f"Reviewed D5a selection changed: {fact_id}")
        if expected_chain is None:
            expected_chain = chain
        elif chain != expected_chain:
            raise ValueError("Selected D5a facts no longer share the reviewed source chain")
        inputs.append(
            {
                "id": fact_id,
                "label": label,
                "exactValue": exact_value,
                "displayValue": display_value,
                "unit": "USD",
                "status": "normalized_unusable",
                "analysisValue": None,
                "detailId": detail_id,
                "reasonCodes": list(REASON_CODES),
                "sourceChainCaptureIds": chain,
            }
        )
        details[detail_id] = detail

    gates = [
        {
            "id": "financial_history",
            "label": "Financial and event history",
            "status": "blocked",
            "reason": "Inventory and event review do not yet cover the required period.",
        },
        {
            "id": "metric_profile",
            "label": "Business and metric applicability",
            "status": "not_reviewed",
            "reason": " ".join(
                (
                    "The applicable CRCL metric roster and interpretation profile",
                    "are not approved.",
                )
            ),
        },
        {
            "id": "accounting_coverage",
            "label": "Accounting coverage",
            "status": "not_reviewed",
            "reason": "Two income-statement facts do not establish a complete analysis input set.",
        },
        {
            "id": "quote_identity",
            "label": "Quote identity for price ratios",
            "status": "blocked",
            "reason": (
                "Quotation currency remains unsubstantiated, so price-dependent "
                "ratios stay unavailable."
            ),
        },
        {
            "id": "publication_contract",
            "label": "Real fundamentals publication",
            "status": "not_implemented",
            "reason": (
                "The existing S6 packet is synthetic-only; a reviewed real publication "
                "contract is still required."
            ),
        },
    ]
    return {
        "kind": "real-crcl-analysis-readiness",
        "company": {"ticker": "CRCL", "name": "Circle Internet Group, Inc."},
        "batchId": BATCH_ID,
        "periodLabel": "FY2025",
        "sourceInputCount": len(inputs),
        "publishedMetricCount": 0,
        "status": "blocked",
        "inputs": inputs,
        "details": details,
        "candidateMetric": {
            "id": "operating_margin",
            "label": "Operating margin",
            "formula": "Operating income ÷ revenue",
            "value": None,
            "displayValue": "N/A",
            "unit": "percent",
            "status": "blocked",
            "reasonCodes": list(REASON_CODES),
            "requiredInputIds": ["operating_income", "revenue"],
        },
        "gates": gates,
        "source": {
            "normalizationHref": "/development/pilot/normalization",
            "publishedAt": normalization["publishedAt"],
            "retrievalCutoff": normalization["retrievalCutoff"],
            "snapshotSha256": NORMALIZATION_SHA,
        },
    }


def generated(root: Path = ROOT) -> dict[str, str]:
    normalization_raw = (root / NORMALIZATION).read_bytes()
    provenance_raw = (root / PROVENANCE).read_bytes()
    if hashlib.sha256(normalization_raw).hexdigest() != NORMALIZATION_SHA:
        raise ValueError("D5a normalization snapshot changed; new review required")
    if hashlib.sha256(provenance_raw).hexdigest() != PROVENANCE_SHA:
        raise ValueError("D5a normalization provenance changed; new review required")
    projection = project(json.loads(normalization_raw), json.loads(provenance_raw))
    snapshot = json.dumps(projection, indent=2, sort_keys=True) + "\n"
    checksum = hashlib.sha256(snapshot.encode()).hexdigest()
    return {
        OUTPUT: snapshot,
        MANIFEST: (
            "// Generated by scripts.export_crcl_analysis_readiness.\n"
            f'export const snapshotSha256 = "{checksum}";\n'
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, value in generated().items():
        target = ROOT / path
        if args.check:
            if not target.exists() or target.read_text() != value:
                raise ValueError("D5b export differs: " + path)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
