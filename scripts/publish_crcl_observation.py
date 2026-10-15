"""D047 reviewed current S3 publication; no S6 or financial metric publication."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import date
from typing import Any
from uuid import UUID

import psycopg
from equity_ingest.archive import LocalArchive
from equity_ingest.financial_types import NormalizationBundle, canonical_json
from equity_ingest.publisher import publish_bundle
from equity_schema.pit import HistoryMode, PitQuery, read_statement
from equity_schema.workflow import Database
from psycopg.rows import dict_row

from scripts import app_postgres
from scripts.normalize_crcl import ROOT, load_preparation
from scripts.prepare_crcl_observation import OUTPUT, generated, prepare
from scripts.publish_crcl_normalization import readback as historical_readback
from scripts.publish_crcl_normalization import rows_snapshot, validate_mapping, verify_preserved
from scripts.review_crcl_identity import verify_database_evidence
from scripts.review_crcl_observation import ACQUISITION

INPUT_HASH = "a179286890c64c55a8f6afb855506bf4732324bc74d5ef944e037695d67b72a4"
OUTPUT_HASH = "5a0f7405d7d939a9fdae7732ab2bd1b2d368c0f277ba948f47f156a4a33c8240"
PUBLICATION = "docs/research/crcl-observation-publication-2026-10-15.json"


def checked_preparation() -> tuple[NormalizationBundle, dict[str, Any]]:
    bundle, proof = prepare()
    if bundle.input_manifest_hash != INPUT_HASH or bundle.output_manifest_hash != OUTPUT_HASH:
        raise ValueError("Current preparation changed; independent review required")
    if (ROOT / OUTPUT).read_text() != canonical_json(generated()) + "\n":
        raise ValueError("Pinned preparation artifact differs from replay")
    return bundle, proof


def readback(db: Database, bundle: NormalizationBundle, batch_id: UUID) -> dict[str, Any]:
    records = db.execute(
        """SELECT DISTINCT c.period_id,c.scope_id,c.currency_unit_id,r.unit_id
        FROM statement_coverage c JOIN fact_resolutions r ON r.coverage_id=c.id
        WHERE c.batch_id=%s""",
        (batch_id,),
    ).fetchall()
    if len(records) != 1:
        raise ValueError("D5i expects one annual consolidated USD statement")
    row = records[0]
    inputs = bundle.inputs
    query = PitQuery(
        issuer_id=inputs.issuer_id,
        period_id=row["period_id"],
        scope_id=row["scope_id"],
        unit_id=row["unit_id"],
        reporting_currency_unit_id=row["currency_unit_id"],
        statement_family="income",
        concepts=inputs.requests[0].concepts,
        batch_ids=(batch_id,),
        capture_ids=tuple(c.id for c in inputs.captures),
        filing_event_ids=(),
        mapping_revision_id=inputs.mapping_revision_id,
        normalizer_revision=inputs.normalizer_revision,
        authority_policy_revision=inputs.authority_policy_revision,
        captured_before=inputs.captured_before,
        mode=HistoryMode.AS_FILED_BY_DATE,
        filed_cutoff=date(2026, 10, 15),
        audited_required=True,
    )
    selected = read_statement(db, query)
    earlier = read_statement(db, replace(query, filed_cutoff=date(2026, 3, 8)))
    original = read_statement(
        db, replace(query, mode=HistoryMode.ORIGINAL_AS_FILED, filed_cutoff=None)
    )
    observations = {item.id: item for item in bundle.observations}
    expected = {
        item.concept_std: observations[item.selected_observation_id].numeric_value
        for item in bundle.resolutions
        if item.selected_observation_id is not None
    }
    if selected.quality_flag_ids:
        raise ValueError("Current selection unexpectedly has quality flags")
    expected_observations = {
        item.concept_std: item.selected_observation_id for item in bundle.resolutions
    }
    for result in (selected, original):
        if (
            {fact.concept: fact.value for fact in result.facts} != expected
            or not result.usable_for_valuation
            or "blocking_quality_flag" in result.flags
            or result.quality_flag_ids != selected.quality_flag_ids
            or any(
                fact.status != "observed"
                or fact.accession != "0001876042-26-000062"
                or fact.observation_ids != (expected_observations[fact.concept],)
                for fact in result.facts
            )
        ):
            raise ValueError(
                f"D5i PIT invariants differ: {result.flags}, usable={result.usable_for_valuation}"
            )
    if (
        "earliest_available" not in original.flags
        or "coverage_unavailable" not in earlier.flags
        or any(fact.value is not None for fact in earlier.facts)
    ):
        raise ValueError("Original/earlier cutoff semantics differ from reviewed D5i history")
    return {
        "as_filed": asdict(selected),
        "before_filing": asdict(earlier),
        "original": asdict(original),
        "quality_evidence": [],
    }


def application(action: str) -> dict[str, Any]:
    bundle, proof = checked_preparation()
    old, _ = load_preparation()
    audit = json.loads((ROOT / ACQUISITION).read_bytes())
    archive = LocalArchive(ROOT / "var/raw")
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as owner:
        owner.execute(
            "SELECT pg_advisory_lock(hashtextextended(%s,0))", ("d5i-current-publication",)
        )
        with owner.transaction():
            owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            verify_database_evidence(owner, audit["groups"][0], archive)
            mapping = owner.execute(
                "SELECT * FROM mapping_revisions WHERE id=%s", (bundle.inputs.mapping_revision_id,)
            ).fetchone()
            if mapping is None:
                raise ValueError("Reviewed mapping missing")
            validate_mapping(dict(mapping), bundle)
            batches = owner.execute(
                "SELECT * FROM normalization_batches WHERE issuer_id=%s", (bundle.inputs.issuer_id,)
            ).fetchall()
            if not 1 <= len(batches) <= 2 or {b["input_manifest_hash"] for b in batches} - {
                old.input_manifest_hash,
                INPUT_HASH,
            }:
                raise ValueError("Unexpected CRCL batch set")
            prior = next(b for b in batches if b["input_manifest_hash"] == old.input_manifest_hash)
            before = rows_snapshot(owner)
        historical = historical_readback(owner, old, prior["id"])
        report = {
            "kind": "governed-crcl-current-normalization",
            "proposalCommit": "c55c2cf",
            "inputHash": INPUT_HASH,
            "outputHash": OUTPUT_HASH,
            "preflightReady": True,
            "sourcePrecision": proof,
            "inputs": asdict(bundle.inputs),
            "beforeRows": before,
            "historicalBatchId": str(prior["id"]),
            "historicalSelection": historical,
            "operatingMargin": None,
            "publishedMetricCount": 0,
        }
        if action == "preflight":
            return report
        replay = None
        if action == "publish":
            with psycopg.connect(
                url.set(drivername="postgresql").render_as_string(hide_password=False),
                autocommit=True,
                row_factory=dict_row,
            ) as db:
                first = publish_bundle(db, bundle)
                second = publish_bundle(db, bundle)
                if first.batch_id != second.batch_id or not second.reused:
                    raise ValueError("Exact replay failed")
                replay = {"batchId": str(first.batch_id), "secondReused": second.reused}
        with owner.transaction():
            owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            batches = owner.execute(
                "SELECT * FROM normalization_batches WHERE issuer_id=%s", (bundle.inputs.issuer_id,)
            ).fetchall()
            if len(batches) != 2:
                raise ValueError("Expected immutable historical plus current batch")
            current = next(b for b in batches if b["input_manifest_hash"] == INPUT_HASH)
            if current["output_manifest_hash"] != OUTPUT_HASH or current["state"] != "published":
                raise ValueError("Published current batch differs")
            verify_database_evidence(owner, audit["groups"][0], archive)
            after = rows_snapshot(owner)
        selection = readback(owner, bundle, current["id"])
        if historical_readback(owner, old, prior["id"]) != historical:
            raise ValueError("Historical D5a selection changed")
        verify_preserved(before, after)
        if action == "verify" and before != after:
            raise ValueError("Read-only verification changed rows")
        report.update(
            batch=dict(current),
            selections=selection,
            afterRows=after,
            priorRowsPreserved=True,
            exactReplay=replay,
        )
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "publish", "verify"))
    args = parser.parse_args()
    target = ROOT / PUBLICATION
    if args.action == "publish" and target.exists():
        raise ValueError("Saved publication exists; use verify, never overwrite")
    report = application(args.action)
    if args.action == "publish":
        target.write_text(canonical_json(report) + "\n")
    print(
        json.dumps(
            {
                "action": args.action,
                "preflightReady": report["preflightReady"],
                "batchId": str(report["batch"]["id"]) if "batch" in report else None,
                "inputHash": INPUT_HASH,
                "outputHash": OUTPUT_HASH,
            }
        )
    )


if __name__ == "__main__":
    main()
