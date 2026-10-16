"""Checked UI projection of the two immutable D049 results, with operand provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from typing import Any

from equity_schema.fundamentals_canonical import canonical_json, content_hash
from equity_schema.real_fundamentals import RealInputManifest, RealSnapshotResponse

from scripts.export_crcl_fundamentals import LABELS
from scripts.normalize_crcl import ROOT
from scripts.publish_crcl_broader import PUBLICATION as SOURCE_PUBLICATION
from scripts.publish_crcl_broader_fundamentals import PINS, PublicationPin
from scripts.review_crcl_broader import REPORT
from scripts.review_crcl_safety import source_detail

OUTPUT = "apps/web/src/features/analysis-readiness/broader.json"
MANIFEST = "apps/web/src/features/analysis-readiness/broader-manifest.ts"
PUBLICATION_HASHES: dict[str, str] = {
    "annual": "2f3180a7610bc1f08ff58fc8fdbf59712b7f6d6fbb84503aab08d05e27ae32d5",
    "instant": "996a7940a2127615c9137512d00af2232c4e0f57e84199277f1fcd3a17bc6acb",
}
SOURCE_PUBLICATION_SHA = "b8cb803d17e9f2d3f3a5d03bddcfa6cf917e11ae54e5123b9c106e9c65a8ba35"
REVIEW_SHA = "24841257b65e92f1ee2131e641cbeb411765598c96c455bdb10b459135ccb116"
CONCEPT_LABELS = {
    "revenue": "Revenue and reserve income",
    "operating_income": "Operating income (loss)",
    "net_income_consolidated": "Consolidated net income (loss), including NCI",
    "cash_from_operating_activities": "Cash from operating activities",
    "capital_expenditures_ppe": "Cash PPE purchases",
    "current_assets": "Reported current assets",
    "current_liabilities": "Reported current liabilities",
    "total_assets": "Total assets",
    "total_liabilities": "Total liabilities",
    "equity_including_noncontrolling_interests": "Permanent equity including NCI",
}
METRIC_LABELS = {**LABELS, "operating_margin": "Reported operating margin"}


def display(value: str, unit: str) -> str:
    number = Decimal(value)
    if unit == "fraction":
        return format(number, ".2%")
    if unit == "multiple":
        return format(number, ".4f") + "×"
    if unit != "USD":
        raise ValueError("Unreviewed display unit")
    return f"{number:,.0f} USD"


def project_result(
    preparation: dict[str, Any],
    publication: dict[str, Any],
    captures: dict[str, Any],
    pin: PublicationPin,
    basis: str,
) -> dict[str, Any]:
    saved = RealSnapshotResponse.model_validate(publication["snapshot"])
    payload = saved.result
    if (
        publication["manifestHash"] != pin.manifest_hash
        or saved.payload_hash != pin.payload_hash
        or content_hash(payload) != pin.payload_hash
        or content_hash(RealInputManifest.model_validate(preparation["manifest"]))
        != pin.manifest_hash
        or not publication["priorRowsPreserved"]
        or not publication["exactReplay"]
        or payload.selector.period_basis != basis
        or payload.evidence_mode != "real"
        or payload.accounting is None
        or payload.accounting.matches is not True
    ):
        raise ValueError("Broader publication or period/accounting proof differs")
    details = {}
    source_by_index = {}
    operands = []
    for evidence in payload.evidence:
        proof = next(p for p in payload.precision_evidence if p.input_index == evidence.input_index)
        sources = [source_detail(captures[str(proof.capture_id)], proof.accession)]
        sources += [
            {**source_detail(captures[str(c)], evidence.accession), "label": "SEC Company Facts"}
            for c in evidence.capture_ids
        ]
        source_by_index[evidence.input_index] = sources
        key = f"{basis}:operand:{evidence.input_index}"
        if evidence.value is None:
            raise ValueError("Reviewed operand unavailable")
        label = CONCEPT_LABELS[evidence.concept]
        operands.append({"id": key, "label": label, "display": display(evidence.value, "USD")})
        details[key] = {
            "title": label,
            "subtitle": "Exact immutable normalized operand and retained source",
            "sections": [
                {
                    "heading": "Operand provenance",
                    "rows": [
                        {"label": "Public evidence", "value": canonical_json(evidence)},
                        {
                            "label": "Original filing context, precision, scale and sign",
                            "value": canonical_json(proof),
                        },
                        {
                            "label": "Selection and normalization lineage",
                            "value": canonical_json(
                                preparation["manifest"]["sources"][evidence.input_index]
                            ),
                        },
                    ],
                }
            ],
            "sources": sources,
        }
    metrics, gaps = [], []
    rules = {r["metric_id"]: r for r in preparation["manifest"]["context"]["profile"]["rules"]}
    for metric in payload.metrics:
        key = f"{basis}:metric:{metric.metric_id}"
        rationale = rules[metric.metric_id]["rationale"]
        if metric.value is None:
            if metric.status != "unsupported" or not metric.reasons:
                raise ValueError("Unreviewed metric gap status")
            gaps.append(
                {
                    "id": metric.metric_id,
                    "label": METRIC_LABELS[metric.metric_id],
                    "requirement": rationale,
                    "reasons": list(metric.reasons),
                }
            )
            continue
        if metric.status != "valid" or not metric.input_indices:
            raise ValueError("Numeric metric lacks valid provenance")
        metrics.append(
            {
                "id": key,
                "metricId": metric.metric_id,
                "label": METRIC_LABELS[metric.metric_id],
                "display": display(metric.value, metric.unit),
                "scope": rationale,
            }
        )
        details[key] = {
            "title": METRIC_LABELS[metric.metric_id],
            "subtitle": rationale,
            "sections": [
                {
                    "heading": "Published calculation and source window",
                    "rows": [
                        {
                            "label": "Exact formula, result and operand references",
                            "value": canonical_json(metric),
                        },
                        {
                            "label": "Immutable snapshot",
                            "value": canonical_json(
                                {
                                    "snapshotId": saved.snapshot_id,
                                    "requestId": saved.request_id,
                                    "payloadHash": saved.payload_hash,
                                    "selector": payload.selector,
                                }
                            ),
                        },
                        {
                            "label": "Full operand evidence",
                            "value": canonical_json(
                                [
                                    e
                                    for e in payload.evidence
                                    if e.input_index in metric.input_indices
                                ]
                            ),
                        },
                    ],
                }
            ],
            "sources": [s for i in metric.input_indices for s in source_by_index[i]],
        }
    if len(metrics) != (4 if basis == "annual" else 2):
        raise ValueError("Reviewed selector metric roster changed")
    accounting_key = f"{basis}:accounting"
    details[accounting_key] = {
        "title": "Closing consolidated balance-sheet identity",
        "subtitle": "Assets = liabilities + permanent consolidated equity including NCI",
        "sections": [
            {
                "heading": "Published identity check",
                "rows": [
                    {
                        "label": "Exact accounting result",
                        "value": canonical_json(payload.accounting),
                    },
                    {
                        "label": "Source indices",
                        "value": canonical_json(
                            preparation["manifest"]["accounting_source_indices"]
                        ),
                    },
                ],
            }
        ],
        "sources": [
            s
            for i in preparation["manifest"]["accounting_source_indices"]
            for s in source_by_index[i]
        ],
    }
    return {
        "basis": basis,
        "snapshot": saved,
        "metrics": metrics,
        "gaps": gaps,
        "operands": operands,
        "accountingDetail": accounting_key,
        "details": details,
    }


def generated() -> dict[str, Any]:
    if set(PINS) != {"annual", "instant"} or set(PUBLICATION_HASHES) != set(PINS):
        raise ValueError("Both independently reviewed publications must be pinned")
    source_raw = (ROOT / SOURCE_PUBLICATION).read_bytes()
    if (
        SOURCE_PUBLICATION_SHA is None
        or hashlib.sha256(source_raw).hexdigest() != SOURCE_PUBLICATION_SHA
    ):
        raise ValueError("Broader source publication changed")
    source = json.loads(source_raw)
    captures = {c["id"]: c for c in source["inputs"]["captures"]}
    results, details = [], {}
    for basis, pin in PINS.items():
        values = []
        for path, digest in (
            (pin.preparation, pin.preparation_sha),
            (pin.publication, PUBLICATION_HASHES[basis]),
        ):
            raw = (ROOT / path).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("Broader publication artifact changed")
            values.append(json.loads(raw))
        result = project_result(values[0], values[1], captures, pin, basis)
        details.update(result.pop("details"))
        results.append(result)
    review_raw = (ROOT / REPORT).read_bytes()
    if hashlib.sha256(review_raw).hexdigest() != REVIEW_SHA:
        raise ValueError("Expanded accounting review changed")
    review = json.loads(review_raw)
    details["review"] = {
        "title": "Expanded accounting and source-history review",
        "subtitle": "Bounded retrospective observation; earlier history remains unproved",
        "sections": [
            {
                "heading": "Safety evidence",
                "rows": [
                    {"label": "Accounting scope", "value": canonical_json(review["findings"])},
                    {
                        "label": "Expanded body dispositions and matching-period comparisons",
                        "value": canonical_json(review["expandedLineReview"]),
                    },
                    {
                        "label": "Exact earlier-history missing resources",
                        "value": canonical_json(review["missingHistoryBodies"]),
                    },
                    {
                        "label": "Immutable source batch and replay",
                        "value": canonical_json(source["batch"]),
                    },
                ],
            }
        ],
        "sources": [
            {
                "label": "SEC retained source",
                "url": r["url"],
                "capturedAt": r["retrievedAt"],
                "transform": "Verified retained bytes SHA256 " + r["bodySha256"],
                "licence": "SEC public filings and government-created data reuse",
            }
            for r in review["lineage"]
        ],
    }
    comparative_rows: list[dict[str, Any]] = []
    seen = set()
    for row in review["comparativeSourceRows"]:
        fact, context = row["fact"], row["context"]
        identity = (fact["qualified_tag"], context["start_date"], context["end_date"])
        if identity in seen:
            continue
        seen.add(identity)
        key = "comparative:" + str(len(comparative_rows))
        label = fact["qualified_tag"].split("}")[-1]
        comparative_rows.append(
            {
                "id": key,
                "label": label,
                "period": context["start_date"] + " to " + context["end_date"],
                "display": display(fact["value"], "USD"),
            }
        )
        capture = captures[row["captureId"]]
        details[key] = {
            "title": label + " · comparative source row",
            "subtitle": (
                "Audited FY2025 filing comparative; not an eligible historical analysis operand"
            ),
            "sections": [
                {
                    "heading": "Exact comparative evidence and limitation",
                    "rows": [
                        {"label": "Inline fact and context", "value": canonical_json(row)},
                        {"label": "Eligibility", "value": review["findings"]["history"]},
                    ],
                }
            ],
            "sources": [source_detail(capture, "0001876042-26-000062")],
        }
    return {
        "kind": "published-real-crcl-broader",
        "results": results,
        "details": details,
        "sourceObservation": review["sourceObservation"],
        "findings": review["findings"],
        "missingHistory": review["missingHistoryBodies"],
        "comparativeRows": comparative_rows,
        "bodyCount": 41,
        "comparisonCount": len(review["expandedLineReview"]["editionComparisons"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    value = canonical_json(generated()) + "\n"
    manifest = (
        "// Generated from verified D5k publications.\nexport const broaderSha256 = "
        + json.dumps(hashlib.sha256(value.encode()).hexdigest())
        + ";\n"
    )
    for path, text in ((OUTPUT, value), (MANIFEST, manifest)):
        target = ROOT / path
        if args.check:
            if not target.exists() or target.read_text() != text:
                raise ValueError("Broader UI projection differs")
        else:
            target.write_text(text)


if __name__ == "__main__":
    main()
