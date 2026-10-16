"""D049 exact S3 preparation and immutable publication audit; no S6 side effect."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import date
from typing import Any
from uuid import UUID

import psycopg
from equity_ingest.financial_types import NormalizationBundle, canonical_json, content_hash
from equity_ingest.publisher import publish_bundle
from equity_schema.pit import HistoryMode, PitQuery, read_statement
from equity_schema.workflow import Database
from psycopg.rows import dict_row

from scripts import app_postgres
from scripts.normalize_crcl import ROOT, load_preparation
from scripts.prepare_crcl_broader import OUTPUT, generated, prepare
from scripts.publish_crcl_fundamentals import _write_exclusive
from scripts.publish_crcl_normalization import readback as historical_readback
from scripts.publish_crcl_normalization import rows_snapshot, verify_preserved
from scripts.publish_crcl_observation import checked_preparation as prior_preparation
from scripts.publish_crcl_observation import readback as prior_readback

INPUT_HASH = "601ad6d6a5bbc9ad8627b2361da58598f94a68b97441eebaed3602a117157b91"
OUTPUT_HASH = "82f41c3f37b0a556c9c126a4b13347aceea83ed949cc3fda95de82b5ca7f4875"
PUBLICATION = "docs/research/crcl-broader-publication-2026-10-15.json"
INTENT = "docs/research/crcl-broader-publication-intent-2026-10-15.json"
REVISION = "d5k-crcl-fy2025-ten-concepts-v1"


def checked_preparation() -> tuple[NormalizationBundle, dict[str, Any]]:
    bundle, proof = prepare()
    if (bundle.input_manifest_hash, bundle.output_manifest_hash) != (INPUT_HASH, OUTPUT_HASH):
        raise ValueError("D5k preparation changed; independent review required")
    if (ROOT / OUTPUT).read_text() != canonical_json(generated()) + "\n":
        raise ValueError("Saved D5k preparation differs")
    return bundle, proof


def register_mapping(db: Database, bundle: NormalizationBundle) -> None:
    expected = {
        "id": bundle.inputs.mapping_revision_id,
        "revision_key": REVISION,
        "content_sha256": content_hash(bundle.inputs.rules),
        "code_revision": bundle.inputs.normalizer_revision,
        "approved_by": "D049 independent source review",
        "reviewed_scope": (
            "docs/design/d5k/proposal.md — FY2025 ten directly reported "
            "consolidated concepts; no earlier-period history"
        ),
    }
    with db.transaction():
        db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (REVISION,))
        rows = db.execute(
            "SELECT * FROM mapping_revisions WHERE id=%s OR revision_key=%s",
            (expected["id"], REVISION),
        ).fetchall()
        if not rows:
            db.execute(
                """INSERT INTO mapping_revisions
                (id,revision_key,content_sha256,code_revision,approved_at,approved_by,reviewed_scope)
                VALUES(%s,%s,%s,%s,clock_timestamp(),%s,%s)""",
                tuple(
                    expected[k]
                    for k in (
                        "id",
                        "revision_key",
                        "content_sha256",
                        "code_revision",
                        "approved_by",
                        "reviewed_scope",
                    )
                ),
            )
            rows = db.execute(
                "SELECT * FROM mapping_revisions WHERE id=%s", (expected["id"],)
            ).fetchall()
        if len(rows) != 1 or any(rows[0][k] != v for k, v in expected.items()):
            raise ValueError("Existing mapping differs from reviewed D5k identity")


def source_queries(bundle: NormalizationBundle, batch_id: UUID) -> list[PitQuery]:
    inputs = bundle.inputs
    return [
        PitQuery(
            issuer_id=inputs.issuer_id,
            period_id=request.period.id,
            scope_id=request.scope.id,
            unit_id=request.currency.id,
            reporting_currency_unit_id=request.currency.id,
            statement_family=request.statement_family,
            concepts=(concept,),
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
        for request in inputs.requests
        for concept in request.concepts
    ]


def readback(db: Database, bundle: NormalizationBundle, batch_id: UUID) -> dict[str, Any]:
    observations = {o.id: o for o in bundle.observations}
    expected = {
        r.concept_std: observations[r.selected_observation_id].numeric_value
        for r in bundle.resolutions
        if r.selected_observation_id is not None
    }
    result = {}
    for query in source_queries(bundle, batch_id):
        selected = read_statement(db, query)
        original = read_statement(
            db, replace(query, mode=HistoryMode.ORIGINAL_AS_FILED, filed_cutoff=None)
        )
        earlier = read_statement(db, replace(query, filed_cutoff=date(2026, 3, 8)))
        concept = query.concepts[0]
        for value in (selected, original):
            if (
                not value.usable_for_valuation
                or value.quality_flag_ids
                or len(value.facts) != 1
                or value.facts[0].value != expected[concept]
                or value.facts[0].accession != "0001876042-26-000062"
            ):
                raise ValueError("Exact broader PIT selection differs")
        if "earliest_available" not in original.flags or any(
            f.value is not None for f in earlier.facts
        ):
            raise ValueError("Original/pre-filing semantics changed")
        result[concept.value] = {
            "current": asdict(selected),
            "original_earliest_available": asdict(original),
            "before_filing": asdict(earlier),
        }
    return result


def application(action: str) -> dict[str, Any]:
    bundle, proof = checked_preparation()
    old, _ = load_preparation()
    prior, _ = prior_preparation()
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as owner:
        owner.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", ("d5k-broader-source",))
        before = rows_snapshot(owner)
        captures = owner.execute(
            "SELECT id,body_sha256,request_url,fetched_at,completed_at "
            "FROM source_captures WHERE id=ANY(%s)",
            ([c.id for c in bundle.inputs.captures],),
        ).fetchall()
        indexed = {str(c["id"]): c for c in captures}
        if len(indexed) != len(bundle.inputs.captures) or any(
            indexed[str(c.id)]["body_sha256"] != c.body_sha256
            or indexed[str(c.id)]["request_url"] != c.request_url
            or indexed[str(c.id)]["fetched_at"] != c.fetched_at
            or indexed[str(c.id)]["completed_at"] != c.completed_at
            for c in bundle.inputs.captures
        ):
            raise ValueError("Application capture lineage differs")
        batches = owner.execute(
            "SELECT id,input_manifest_hash,output_manifest_hash,state "
            "FROM normalization_batches WHERE issuer_id=%s",
            (bundle.inputs.issuer_id,),
        ).fetchall()
        by_hash = {b["input_manifest_hash"]: b for b in batches}
        if set(by_hash) - {old.input_manifest_hash, prior.input_manifest_hash, INPUT_HASH} or not {
            old.input_manifest_hash,
            prior.input_manifest_hash,
        } <= set(by_hash):
            raise ValueError("Unexpected prior batch set")
        old_selection = historical_readback(owner, old, by_hash[old.input_manifest_hash]["id"])
        prior_selection = prior_readback(owner, prior, by_hash[prior.input_manifest_hash]["id"])
        report = {
            "kind": "d5k-broader-source-publication",
            "inputHash": INPUT_HASH,
            "outputHash": OUTPUT_HASH,
            "sourceObservation": bundle.inputs.captured_before.isoformat(),
            "preflightReady": True,
            "sourcePrecision": proof,
            "inputs": asdict(bundle.inputs),
            "historicalSelection": old_selection,
            "priorSelection": prior_selection,
        }
        if action == "preflight":
            return report
        intent_path = ROOT / INTENT
        if not intent_path.exists():
            if action != "publish":
                raise ValueError("Original intent baseline unavailable")
            _write_exclusive(
                intent_path,
                {"inputHash": INPUT_HASH, "outputHash": OUTPUT_HASH, "beforeRows": before},
            )
        intent = json.loads(intent_path.read_text())
        if intent["inputHash"] != INPUT_HASH or intent["outputHash"] != OUTPUT_HASH:
            raise ValueError("Intent differs")
        baseline = intent["beforeRows"]
        verify_preserved(baseline, before)
        reused = None
        if action == "publish":
            register_mapping(owner, bundle)
            with psycopg.connect(
                url.set(drivername="postgresql").render_as_string(hide_password=False),
                autocommit=True,
                row_factory=dict_row,
            ) as db:
                first = publish_bundle(db, bundle)
                second = publish_bundle(db, bundle)
                if first.batch_id != second.batch_id or not second.reused:
                    raise ValueError("Exact S3 replay failed")
                reused = second.reused
        row = owner.execute(
            "SELECT * FROM normalization_batches WHERE input_manifest_hash=%s", (INPUT_HASH,)
        ).fetchone()
        if not row or row["output_manifest_hash"] != OUTPUT_HASH or row["state"] != "published":
            raise ValueError("Broader batch not published")
        selections = readback(owner, bundle, row["id"])
        after = rows_snapshot(owner)
        verify_preserved(baseline, after)
        if (
            historical_readback(owner, old, by_hash[old.input_manifest_hash]["id"]) != old_selection
            or prior_readback(owner, prior, by_hash[prior.input_manifest_hash]["id"])
            != prior_selection
        ):
            raise ValueError("Prior selections changed")
        if action == "verify" and before != after:
            raise ValueError("Verification wrote rows")
        report.update(
            batch=dict(row),
            selections=selections,
            beforeRows=baseline,
            afterRows=after,
            priorRowsPreserved=True,
            exactReplay=reused,
        )
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "publish", "verify"))
    args = parser.parse_args()
    target = ROOT / PUBLICATION
    if args.action == "publish" and target.exists():
        raise ValueError("Audit exists; use verify")
    report = application(args.action)
    if args.action == "publish":
        _write_exclusive(target, report)
    print(
        canonical_json(
            {
                "action": args.action,
                "inputHash": report["inputHash"],
                "outputHash": report["outputHash"],
                "preflightReady": report["preflightReady"],
            }
        )
    )


if __name__ == "__main__":
    main()
