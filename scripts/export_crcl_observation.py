"""Checked D5i source-only projection; real S6 metrics remain absent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from equity_ingest.financial_types import canonical_json

from scripts.normalize_crcl import ROOT
from scripts.prepare_crcl_observation import OUTPUT as PREPARATION
from scripts.publish_crcl_observation import INPUT_HASH, OUTPUT_HASH, PUBLICATION
from scripts.review_crcl_observation import ACQUISITION, REPORT
from scripts.review_crcl_safety import source_detail

REVIEW_SHA = "d4b9c4131ebb6a0f118b831ba296443e623af2c9b5dd51e6c1f40f56b3c39920"
PREPARATION_SHA = "b3b769301aa2a5cea1cce885bbb270c56c18864e666c7f95e0ca97f7eb8c7ef5"
PUBLICATION_SHA = "16480213347471fab0810369b9a46175f59b52164de5a42afa68f6dbee6ae552"
OUTPUT = "apps/web/src/features/analysis-readiness/observation.json"
MANIFEST = "apps/web/src/features/analysis-readiness/observation-manifest.ts"


def project(
    review: dict[str, Any], preparation: dict[str, Any], publication: dict[str, Any] | None
) -> dict[str, Any]:
    if (
        hashlib.sha256((json.dumps(review, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        != REVIEW_SHA
    ):
        raise ValueError("D5i review changed")
    if hashlib.sha256((canonical_json(preparation) + "\n").encode()).hexdigest() != PREPARATION_SHA:
        raise ValueError("Pinned preparation contents changed")
    if (
        preparation["inputHash"] != INPUT_HASH
        or preparation["outputHash"] != OUTPUT_HASH
        or preparation["qualityFlags"]
        or not preparation["originalHistoryComplete"]
    ):
        raise ValueError("D5i preparation is not the reviewed eligible input")
    if (
        publication is not None
        and hashlib.sha256((canonical_json(publication) + "\n").encode()).hexdigest()
        != PUBLICATION_SHA
    ):
        raise ValueError("D5i publication is not independently reviewed and pinned")
    facts = []
    details = dict(review["details"])
    if publication is not None:
        if (
            publication["inputHash"] != INPUT_HASH
            or publication["outputHash"] != OUTPUT_HASH
            or not publication["priorRowsPreserved"]
            or not publication["exactReplay"]["secondReused"]
        ):
            raise ValueError("D5i publication proof differs")
        selection = publication["selections"]["as_filed"]
        if (
            not selection["usable_for_valuation"]
            or selection["quality_flag_ids"]
            or selection["flags"]
        ):
            raise ValueError("Current selected source facts are not eligible")
        captures = {c["id"]: c for c in publication["inputs"]["captures"]}
        for fact in selection["facts"]:
            key = fact["concept"]
            if (
                key not in {"revenue", "operating_income"}
                or fact["status"] != "observed"
                or fact["value"] is None
            ):
                raise ValueError("Unexpected current source operand")
            proof = publication["sourcePrecision"][key]
            sources = [
                {**source_detail(captures[c], fact["accession"]), "label": "SEC Company Facts"}
                for c in fact["capture_ids"]
            ]
            sources.append(source_detail(captures[proof["capture_id"]], fact["accession"]))
            facts.append(
                {
                    "id": key,
                    "label": "Revenue and reserve income"
                    if key == "revenue"
                    else "Operating income (loss)",
                    "value": fact["value"],
                    "unit": "USD",
                }
            )
            details[key] = {
                "title": facts[-1]["label"],
                "subtitle": "Published normalization source operand; "
                "no ratio or investment conclusion",
                "sections": [
                    {
                        "heading": "Evidence and limits",
                        "rows": [
                            {
                                "label": "Exact selected source fact",
                                "value": json.dumps(fact, sort_keys=True),
                            },
                            {
                                "label": "Original filing precision and context",
                                "value": json.dumps(proof, sort_keys=True),
                            },
                            {
                                "label": "Exact batch and cutoff",
                                "value": publication["batch"]["id"]
                                + " / "
                                + publication["inputs"]["captured_before"],
                            },
                        ],
                    }
                ],
                "sources": sources,
            }
    return {
        "kind": "real-crcl-current-source-readiness",
        "reviewedOn": "2026-10-15",
        "normalizationStatus": "published" if publication else "prepared",
        "batchId": publication["batch"]["id"] if publication else None,
        "historicalBatchId": publication["historicalBatchId"] if publication else None,
        "capturedBefore": review["inventoryObservedAt"],
        "timeScope": review["timeScope"],
        "facts": facts,
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "publicationBlocker": "The existing S6 input and result contracts only permit "
        "synthetic evidence "
        "and require a quote identifier. Real source-only publication needs a separate "
        "reviewed contract; no synthetic label or quote is invented.",
        "metadataNote": "Three filing acceptance timestamps differ between the "
        "September and October "
        "inventories. New metadata uses the exact fresh source values; the cause is not "
        "inferred and old versions are preserved.",
        "details": details,
    }


def generated(root: Path = ROOT) -> dict[str, str]:
    review = json.loads((root / REPORT).read_bytes())
    if hashlib.sha256((root / ACQUISITION).read_bytes()).hexdigest() != review["acquisitionSha256"]:
        raise ValueError("D5i acquisition lineage changed")
    preparation = json.loads((root / PREPARATION).read_bytes())
    publication = (
        json.loads((root / PUBLICATION).read_bytes()) if (root / PUBLICATION).exists() else None
    )
    snapshot = (
        json.dumps(project(review, preparation, publication), indent=2, sort_keys=True) + "\n"
    )
    digest = hashlib.sha256(snapshot.encode()).hexdigest()
    return {
        OUTPUT: snapshot,
        MANIFEST: "// Generated by scripts.export_crcl_observation.\n"
        + f'export const observationSha256 = "{digest}";\n',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, text in generated().items():
        target = ROOT / path
        if args.check:
            if not target.exists() or target.read_text() != text:
                raise ValueError("D5i projection differs")
        else:
            target.write_text(text)


if __name__ == "__main__":
    main()
