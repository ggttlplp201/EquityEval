"""D047 two-concept current S3 preparation; no database or financial publication."""

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
    content_hash,
    evidence_id,
)
from equity_ingest.sec_inventory import parse_submissions
from equity_ingest.sec_normalize import normalize_verified_bytes

from scripts.normalize_crcl import RESOURCES, ROOT, crosscheck, load_preparation
from scripts.review_crcl_observation import REPORT, retained_captures, review

OUTPUT = "docs/research/crcl-observation-preparation-2026-10-15.json"


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
    current_inventory = max(
        (r for r in rows if r["source_object_key"] == RESOURCES[1]),
        key=lambda r: datetime.fromisoformat(r["completed_at"]),
    )
    metadata = parse_submissions(
        bodies[current_inventory["capture_id"]],
        expected_cik=old.inputs.cik,
        capture_id=UUID(current_inventory["capture_id"]),
    )
    filings = []
    versions = {}
    for old_filing in old.inputs.filings:
        matches = [f for f in metadata.filings if f.accession == old_filing.accession]
        if len(matches) != 1:
            raise ValueError("Fresh inventory must identify every selected filing uniquely")
        metadata_row = matches[0]
        if (
            metadata_row.filed_date,
            metadata_row.form,
            metadata_row.report_period_end,
            metadata_row.acceptance_time_basis,
        ) != (
            old_filing.filed_date,
            old_filing.form,
            old_filing.report_period_end,
            old_filing.acceptance_time_basis,
        ):
            raise ValueError("Fresh filing identity differs from the reviewed edition")
        if assessed["metadataRebinding"]["status"] != "reviewed_source_vintage_difference":
            raise ValueError("Metadata vintage delta is not reviewed")
        version_id = evidence_id(
            "d5i-filing-version",
            [old_filing.id, current_inventory["capture_id"], metadata_row.raw_metadata],
        )
        versions[old_filing.id] = version_id
        filings.append(
            replace(
                old_filing,
                id=version_id,
                metadata_capture_id=UUID(current_inventory["capture_id"]),
                acceptance_at=metadata_row.acceptance_at,
                metadata_hash=content_hash(metadata_row.raw_metadata),
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
        filings=tuple(filings),
        requests=tuple(
            replace(
                r,
                id=evidence_id("d5i-coverage", [versions[r.filing_version_id], r.scope.id]),
                filing_version_id=versions[r.filing_version_id],
                evidence_locator=REPORT,
            )
            for r in old.inputs.requests
        ),
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
            "proposalCommit": "c55c2cf",
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
        "proposalCommit": "c55c2cf",
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
