"""Checked, sanitized D5a presentation; offline by default, no browser DB access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from equity_ingest.financial_types import canonical_json

from scripts.normalize_crcl import ROOT
from scripts.publish_crcl_normalization import INPUT_HASH, OUTPUT_HASH, application

AUDIT = "docs/research/crcl-normalization-2026-09-30.json"
AUDIT_SHA = "db58bf64ca5a84501e02417af563e931074beaa6574fdef51a3a47c2fc4917db"
OUTPUT = "apps/web/src/features/normalization/snapshot.json"
MANIFEST = "apps/web/src/features/normalization/manifest.ts"
LABELS = {"revenue": "Revenue and reserve income", "operating_income": "Operating income (loss)"}


def section(title: str, rows: dict[str, Any]) -> dict[str, Any]:
    return {
        "heading": title,
        "rows": [
            {"label": key, "value": "N/A" if value is None else str(value)}
            for key, value in rows.items()
        ],
    }


def project(audit: dict[str, Any]) -> dict[str, Any]:
    batch = audit["batch"]
    if (
        audit["input_hash"] != INPUT_HASH
        or audit["output_hash"] != OUTPUT_HASH
        or batch["state"] != "published"
        or audit["financial_result"] is not False
        or not audit["prior_rows_preserved"]
        or not audit["exact_replay_verified"]
    ):
        raise ValueError("A verified D5a publication audit is required")
    inputs = audit["inputs"]
    sources = [
        {
            "label": capture["role"].replace("_", " "),
            "url": capture["request_url"],
            "capturedAt": capture["completed_at"],
            "transform": "Archived bytes → reviewed S3 mapping → PIT selection",
            "licence": "SEC public filings · local analysis under the retained source policy",
        }
        for capture in inputs["captures"]
    ]
    details = {}
    details["publication"] = {
        "title": "Publication and retained evidence",
        "subtitle": "Real application · D5a",
        "sections": [
            section(
                "Publication",
                {
                    "Batch ID": batch["id"],
                    "Published at": batch["published_at"],
                    "Input hash": INPUT_HASH,
                    "Output hash": OUTPUT_HASH,
                    "Mapping ID": audit["mapping"]["id"],
                    "Mapping approved at": audit["mapping"]["approved_at"],
                    "Mapping hash": audit["mapping"]["content_sha256"],
                    "Prior rows preserved": True,
                    "Exact replay reused batch": True,
                },
            ),
            section(
                "Application counts after publication",
                {key: value["count"] for key, value in audit["after"].items() if value["count"]},
            ),
            section(
                "Original filing context",
                {
                    "Coverage": "Two selected FY2025 consolidated income concepts only",
                    "Amendment": (
                        "10-K/A adds separate Circle Reserve Fund statements; "
                        "no restatement edge created"
                    ),
                    "Quarterly report": (
                        "Separate filing metadata; no quarterly concept coverage requested"
                    ),
                    "Observation count": (
                        "9 retained Company Facts candidates; 2 selected resolutions"
                    ),
                    "History": (
                        "Filed-date reconstruction using September captures; "
                        "not app knowledge in March"
                    ),
                },
            ),
        ],
        "sources": sources,
    }
    details["eligibility"] = {
        "title": "Calculation eligibility",
        "subtitle": "Source normalization completed",
        "sections": [
            section(
                "Retained source-history flags",
                {
                    row["rule_key"]: row["severity"] + " · " + row["message"]
                    for row in audit["selections"]["quality_evidence"]
                },
            ),
            section(
                "Next prerequisites",
                {
                    "Valuation eligibility": False,
                    "Financial analysis": "N/A",
                    "Pending": (
                        "Reviewed financial/event history, applicable source metrics "
                        "and S5/S6 publication"
                    ),
                    "Quote currency": "N/A",
                    "Fair value": "N/A",
                },
            ),
        ],
        "sources": sources,
    }
    views = {}
    for key, label in (
        ("as_filed", "Filed by Mar 9, 2026"),
        ("before_filing", "Filed by Mar 8, 2026"),
        ("original", "Earliest available"),
    ):
        selection = audit["selections"][key]
        facts = []
        for fact in selection["facts"]:
            concept = fact["concept"]
            proof = audit["source_precision"][concept]
            detail_id = key + ":" + concept
            facts.append(
                {
                    "id": concept,
                    "label": LABELS[concept],
                    "value": fact["value"],
                    "detailId": detail_id,
                }
            )
            details[detail_id] = {
                "title": LABELS[concept],
                "subtitle": "CRCL · FY2025 · " + label,
                "sections": [
                    section(
                        "Point-in-time selection",
                        {
                            "Exact value (USD)": fact["value"],
                            "Status": fact["status"],
                            "Accession": fact["accession"],
                            "Filed date": fact["filed_date"],
                            "Filed cutoff": selection["query"]["filed_cutoff"],
                            "Retrieval cutoff": selection["query"]["captured_before"],
                            "History mode": selection["query"]["mode"],
                            "Selection hash": selection["input_hash"],
                            "PIT flags": ", ".join(selection["flags"]),
                            "Eligible for valuation": selection["usable_for_valuation"],
                            "Observation IDs": ", ".join(fact["observation_ids"]),
                            "Source hashes": ", ".join(fact["source_hashes"]),
                            "Company Facts locator": fact["source_locator"],
                            "Company Facts source token": fact["original_numeric_text"],
                            "Transform": fact["transform_json"],
                        },
                    ),
                    section(
                        "Separate original-filing precision evidence",
                        {
                            "Original literal": proof["fact"]["lexical_text"],
                            "Scale": proof["fact"]["scale"],
                            "Decimals": proof["fact"]["decimals"],
                            "Sign": proof["fact"]["sign"] or "positive",
                            "Context": proof["fact"]["context_id"],
                            "Period start": proof["context"]["start_date"],
                            "Period end": proof["context"]["end_date"],
                            "Unit": "USD",
                            "Filing locators": "\n".join(proof["candidate_locators"]),
                            "Source capture ID": proof["capture_id"],
                            "Whole-document extraction issues": proof["extractor_issue_count"],
                            "Company Facts context/precision": (
                                "Unknown; filing evidence remains separate"
                            ),
                        },
                    ),
                ],
                "sources": sources,
            }
        views[key] = {"label": label, "facts": facts}
    return {
        "kind": "real-crcl-normalization",
        "batchId": batch["id"],
        "publishedAt": batch["published_at"],
        "periodLabel": "FY2025",
        "retrievalCutoff": inputs["captured_before"],
        "factCount": audit["after"]["fact_resolutions"]["count"],
        "captureCount": audit["after"]["normalization_inputs"]["count"],
        "flagCount": audit["after"]["data_quality_flags"]["count"],
        "views": views,
        "details": details,
    }


def generated(root: Path = ROOT) -> dict[str, str]:
    raw = (root / AUDIT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != AUDIT_SHA:
        raise ValueError("D5a audit changed; new review required")
    snapshot = json.dumps(project(json.loads(raw)), indent=2, sort_keys=True) + "\n"
    checksum = hashlib.sha256(snapshot.encode()).hexdigest()
    return {
        OUTPUT: snapshot,
        MANIFEST: (
            "// Generated by scripts.export_crcl_normalization.\n"
            f'export const snapshotSha256 = "{checksum}";\n'
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-application", action="store_true")
    args = parser.parse_args()
    for path, value in generated().items():
        target = ROOT / path
        if args.check:
            if not target.exists() or target.read_text() != value:
                raise ValueError("D5a export differs: " + path)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value)
    if args.verify_application:
        actual = application("verify")
        saved = json.loads((ROOT / AUDIT).read_text())
        for key in ("batch", "mapping", "inputs", "source_precision", "selections", "after"):
            if canonical_json(actual[key]) != canonical_json(saved[key]):
                raise ValueError("Current application differs from the saved D5a audit: " + key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
