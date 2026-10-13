"""D046 two-concept current S3 preparation; no database or financial publication."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from equity_ingest.archive import LocalArchive
from equity_ingest.financial_types import (
    Completeness,
    EvidenceCapture,
    NormalizationBundle,
    canonical_json,
)
from equity_ingest.sec_normalize import normalize_verified_bytes

from scripts.normalize_crcl import RESOURCES, ROOT, crosscheck, load_preparation
from scripts.review_crcl_registration import REPORT, retained_captures, review

OUTPUT = "docs/research/crcl-current-preparation-2026-10-13.json"


def prepare(root: Path = ROOT) -> tuple[NormalizationBundle, dict[str, Any]]:
    assessed = review(root)
    if (
        assessed["candidateBatch"]["status"] != "ready_for_s3_preparation"
        or assessed.get("timeScope", {}).get("state") != "observation_covers_retained_evidence"
    ):
        raise ValueError("Current source/history/accounting review is not complete")
    raw = (root / REPORT).read_bytes()
    if raw != (json.dumps(assessed, indent=2, sort_keys=True) + "\n").encode():
        raise ValueError("Current review must be saved and match deterministic replay")
    old, _ = load_preparation(root)
    rows = retained_captures(root)
    cutoff = datetime.fromisoformat(assessed["inventoryObservedAt"])
    current_facts = max(
        (r for r in rows if r["source_object_key"] == RESOURCES[0]),
        key=lambda r: datetime.fromisoformat(r["completed_at"]),
    )
    archive = LocalArchive(root / "var/raw")
    captures = []
    bodies = {}
    for row in sorted(rows, key=lambda r: r["capture_id"]):
        body = archive.read_blob(row["blob_key"], row["body_sha256"], row["byte_count"])
        if row["http_status"] != 200:
            raise ValueError("Current preparation cannot include failed evidence")
        bodies[row["capture_id"]] = body
        captures.append(
            EvidenceCapture(
                UUID(row["capture_id"]),
                UUID(row["source_id"]),
                row["source_object_key"],
                row["request_url"],
                row["body_sha256"],
                row["byte_count"],
                datetime.fromisoformat(row["fetched_at"]),
                datetime.fromisoformat(row["completed_at"]),
                "financial_facts"
                if row["capture_id"] == current_facts["capture_id"]
                else "reviewed_history",
            )
        )
    references = (
        REPORT + "#selected-FY2025-income-history",
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        "inventory_observed_at:" + assessed["inventoryObservedAt"],
    )
    completeness = Completeness(
        "complete",
        date(2025, 12, 31),
        datetime.fromisoformat(assessed["inventoryObservedAt"]).date(),
        references,
    )
    inputs = replace(
        old.inputs,
        companyfacts_capture_id=UUID(current_facts["capture_id"]),
        captures=tuple(captures),
        captured_before=cutoff,
        requests=tuple(replace(r, evidence_locator=REPORT) for r in old.inputs.requests),
        inventory_completeness=completeness,
        event_completeness=completeness,
    )
    bundle = normalize_verified_bytes(bodies[current_facts["capture_id"]], inputs)
    original = next(c for c in captures if c.source_object_key == RESOURCES[2])
    proof = crosscheck(bundle, bodies[str(original.id)], original)
    if not bundle.original_history_complete or bundle.quality_flags:
        raise ValueError("Existing normalizer did not clear the reviewed current coverage")
    return bundle, proof


def generated(root: Path = ROOT) -> dict[str, Any]:
    assessed = review(root)
    if assessed["candidateBatch"]["status"] != "ready_for_s3_preparation":
        return {
            "kind": "blocked-current-crcl-s3-preparation",
            "proposalCommit": "01348a5",
            "reviewSha256": hashlib.sha256((root / REPORT).read_bytes()).hexdigest(),
            "status": "blocked",
            "inputHash": None,
            "outputHash": None,
            "reasonCodes": assessed["candidateBatch"]["reasonCodes"],
            "timeScope": assessed["timeScope"],
            "batchId": None,
            "operatingMargin": None,
            "publishedMetricCount": 0,
            "note": "No current eligible bundle is prepared. Historical flags stay unchanged; "
            "date-level completeness cannot stand in for an unproved observation bound.",
        }
    bundle, proof = prepare(root)
    return {
        "kind": "reviewed-current-crcl-s3-preparation",
        "proposalCommit": "01348a5",
        "reviewSha256": hashlib.sha256((root / REPORT).read_bytes()).hexdigest(),
        "inputHash": bundle.input_manifest_hash,
        "outputHash": bundle.output_manifest_hash,
        "inputs": asdict(bundle.inputs),
        "sourcePrecision": proof,
        "originalHistoryComplete": bundle.original_history_complete,
        "qualityFlags": [asdict(f) for f in bundle.quality_flags],
        "mapping": "Existing D5a two-concept mapping reused unchanged",
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "note": "Current retrospective preparation only; no database write. "
        "September batch and flags are preserved. Real S6 publication is separate.",
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = canonical_json(generated()) + "\n"
    target = ROOT / OUTPUT
    if args.check:
        if not target.exists() or target.read_text() != text:
            raise ValueError("Current preparation differs from pinned evidence")
    else:
        target.write_text(text)
    print(json.dumps({"preparation": OUTPUT, "verified": args.check}))


if __name__ == "__main__":
    main()
