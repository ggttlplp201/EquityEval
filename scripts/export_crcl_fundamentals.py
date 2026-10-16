"""Checked UI projection of the immutable real-v2 publication; no finance calculation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from decimal import Decimal
from typing import Any

from equity_schema.fundamentals_canonical import canonical_json, content_hash
from equity_schema.real_fundamentals import RealSnapshotResponse

from scripts.export_crcl_observation import PUBLICATION_SHA as OBSERVATION_SHA
from scripts.normalize_crcl import ROOT
from scripts.publish_crcl_fundamentals import (
    MANIFEST_HASH,
    PAYLOAD_HASH,
    PREPARATION,
    PREPARATION_SHA,
    PUBLICATION,
)
from scripts.publish_crcl_observation import PUBLICATION as OBSERVATION
from scripts.review_crcl_safety import source_detail

PUBLICATION_SHA: str | None = "de966d943d93467c068ee2e67346aad20db4ef6a90d900e06582cfe158878e27"
OUTPUT = "apps/web/src/features/analysis-readiness/real.json"
MANIFEST = "apps/web/src/features/analysis-readiness/real-manifest.ts"
LABELS = {
    "revenue_growth_yoy": "Revenue growth",
    "gross_margin": "Reported gross margin",
    "gross_margin_derived": "Derived gross margin",
    "net_margin_consolidated": "Consolidated net margin",
    "free_cash_flow_ppe": "Free cash flow after PPE purchases",
    "free_cash_flow_margin_ppe": "Free cash flow margin",
    "current_ratio": "Current ratio",
    "net_working_capital": "Net working capital",
    "return_on_assets": "Return on assets",
}


def filing_source(capture: dict[str, Any]) -> dict[str, Any]:
    match = re.search(r"/(\d{18})/", capture["request_url"])
    if not match:
        raise ValueError("Policy evidence requires a retained filing accession")
    number = match[1]
    return source_detail(capture, f"{number[:10]}-{number[10:12]}-{number[12:]}")


def project(
    preparation: dict[str, Any], publication: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    saved = RealSnapshotResponse.model_validate(publication["snapshot"])
    if (
        publication.get("manifestHash") != MANIFEST_HASH
        or saved.payload_hash != PAYLOAD_HASH
        or content_hash(saved.result) != PAYLOAD_HASH
        or not publication.get("exactReplay")
        or not publication.get("priorRowsPreserved")
        or saved.result.evidence_mode != "real"
        or saved.outcome != "completed_with_gaps"
    ):
        raise ValueError("Real publication proof differs from the independently reviewed result")
    margin = next(m for m in saved.result.metrics if m.metric_id == "operating_margin")
    if margin.status != "valid" or margin.value is None or margin.input_indices != (0, 1):
        raise ValueError("No reviewed operating-margin publication")
    profile = preparation["manifest"]["context"]["profile"]
    requirements = {
        r["metric_id"]: r["rationale"] for r in profile["rules"] if r["applicable"] is None
    }
    captures = {c["id"]: c for c in observation["inputs"]["captures"]}
    sources = []
    details = {}
    operands = []
    for evidence in saved.result.evidence:
        proof = next(
            p for p in saved.result.precision_evidence if p.input_index == evidence.input_index
        )
        original = source_detail(captures[str(proof.capture_id)], proof.accession)
        fact_sources = [
            {**source_detail(captures[str(c)], evidence.accession), "label": "SEC Company Facts"}
            for c in evidence.capture_ids
        ]
        exact = preparation["manifest"]["sources"][evidence.input_index]["selection"]["facts"][0]
        label = (
            "Operating income (loss)"
            if evidence.concept == "operating_income"
            else "Revenue and reserve income"
        )
        if evidence.value is None:
            raise ValueError("Published margin operand unavailable")
        operands.append(
            {
                "id": evidence.concept,
                "label": label,
                "display": f"{Decimal(evidence.value):,.0f} USD",
            }
        )
        details[evidence.concept] = {
            "title": label,
            "subtitle": "Published real FY2025 consolidated operand",
            "sections": [
                {
                    "heading": "Exact source and normalization",
                    "rows": [
                        {
                            "label": "Selected fact and exact locator",
                            "value": canonical_json(exact),
                        },
                        {"label": "Public provenance", "value": canonical_json(evidence)},
                        {
                            "label": "Original inline precision, scale and sign",
                            "value": canonical_json(proof),
                        },
                    ],
                }
            ],
            "sources": [*fact_sources, original],
        }
        sources.extend([*fact_sources, original])
    details["operating_margin"] = {
        "title": "Reported operating margin",
        "subtitle": "Signed operating income / total revenue including reserve income",
        "sections": [
            {
                "heading": "Published calculation",
                "rows": [
                    {"label": "Exact fractional result", "value": margin.value},
                    {
                        "label": "Formula, operands and calculation hash",
                        "value": canonical_json(margin),
                    },
                    {
                        "label": "Snapshot and payload identity",
                        "value": canonical_json(
                            {
                                "snapshot_id": saved.snapshot_id,
                                "request_id": saved.request_id,
                                "payload_hash": saved.payload_hash,
                                "dependency_hash": saved.result.dependency_hash,
                            }
                        ),
                    },
                    {
                        "label": "Exact source observation and evaluation",
                        "value": canonical_json(saved.result.selector),
                    },
                    {
                        "label": "Full operand source and precision chain",
                        "value": canonical_json(
                            {
                                "evidence": saved.result.evidence,
                                "precision": saved.result.precision_evidence,
                            }
                        ),
                    },
                ],
            }
        ],
        "sources": sources,
    }
    details["policy"] = {
        "title": "Real publication policy and safety",
        "subtitle": "Reviewed applicability, source-history reconciliation and explicit gaps",
        "sections": [
            {
                "heading": "Policy and retained evidence",
                "rows": [
                    {
                        "label": "Business profile and exact missing requirements",
                        "value": canonical_json(profile),
                    },
                    {
                        "label": "Freshness policy",
                        "value": canonical_json(preparation["manifest"]["context"]["freshness"]),
                    },
                    {
                        "label": "Publication and preservation",
                        "value": canonical_json(
                            {
                                "manifestHash": MANIFEST_HASH,
                                "payloadHash": PAYLOAD_HASH,
                                "priorRowsPreserved": True,
                                "exactReplay": True,
                            }
                        ),
                    },
                    {
                        "label": "Source chain",
                        "value": canonical_json(preparation["manifest"]["captures"]),
                    },
                ],
            }
        ],
        "sources": [
            filing_source(captures[str(p.capture_id)]) for p in saved.result.policy_evidence
        ],
    }
    gaps = []
    for metric in saved.result.metrics:
        if metric.metric_id == "operating_margin":
            continue
        requirement = requirements[metric.metric_id]
        if (
            metric.status != "unsupported"
            or metric.value is not None
            or f"applicability_requirement:{requirement}" not in metric.reasons
        ):
            raise ValueError("Unresolved metric has inconsistent public status or requirements")
        gaps.append(
            {"id": metric.metric_id, "label": LABELS[metric.metric_id], "requirement": requirement}
        )
    return {
        "kind": "published-real-crcl-fundamentals",
        "snapshot": saved,
        "marginDisplay": format(Decimal(margin.value), ".2%"),
        "sourceObservation": publication["sourceObservation"],
        "evaluatedAt": publication["evaluatedAt"],
        "operands": operands,
        "unresolved": gaps,
        "details": details,
    }


def generated() -> dict[str, Any]:
    values = []
    for path, digest in (
        (PREPARATION, PREPARATION_SHA),
        (PUBLICATION, PUBLICATION_SHA),
        (OBSERVATION, OBSERVATION_SHA),
    ):
        if digest is None:
            raise ValueError("Real publication not yet independently pinned")
        raw = (ROOT / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Real fundamentals artifact changed")
        values.append(json.loads(raw))
    return project(*values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = canonical_json(generated()) + "\n"
    manifest = (
        "// Generated from verified real publication. Do not edit.\nexport const realSha256 = "
        + json.dumps(hashlib.sha256(output.encode()).hexdigest())
        + ";\n"
    )
    for path, value in ((OUTPUT, output), (MANIFEST, manifest)):
        target = ROOT / path
        if args.check:
            if not target.exists() or target.read_text() != value:
                raise ValueError("Real UI projection differs")
        else:
            target.write_text(value)


if __name__ == "__main__":
    main()
