"""Owned-application D5a preflight/publication and immutable read-back audit."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import date
from typing import Any
from uuid import UUID

import psycopg
from equity_ingest.archive import LocalArchive
from equity_ingest.financial_types import NormalizationBundle, canonical_json, content_hash
from equity_ingest.publisher import publish_bundle
from equity_schema.pit import HistoryMode, PitQuery, read_statement
from equity_schema.workflow import Database
from psycopg import sql
from psycopg.rows import dict_row

from scripts import app_postgres
from scripts.normalize_crcl import CUTOFF, REVIEW, ROOT, load_preparation
from scripts.review_crcl_identity import read_audit, verify_database_evidence

INPUT_HASH = "7970f9dc775f50f0c136ce66234e1a5478cd682fce75517ae24f222458caff47"
OUTPUT_HASH = "1971a99bc729858fc3d60c703834d7d3444b8c0a2ad38f6f2f902730c2e445f5"
REVISION = "d5a-crcl-fy2025-two-concepts-v1"
APPROVED_BY = "D039 / reviewed D5a proposal"
REVIEWED_SCOPE = REVIEW + " — two CRCL FY2025 consolidated income concepts only"
ALLOWED_ADDITIONS = frozenset(
    {
        "mapping_revisions",
        "filings",
        "filing_versions",
        "periods",
        "units",
        "semantic_scopes",
        "normalization_batches",
        "normalization_inputs",
        "statement_coverage",
        "source_observations",
        "fact_resolutions",
        "resolution_candidates",
        "data_quality_flags",
    }
)


def rows_snapshot(db: Database) -> dict[str, list[str]]:
    tables = db.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    ).fetchall()
    return {
        row["tablename"]: sorted(
            content_hash(item["row"])
            for item in db.execute(
                sql.SQL("SELECT to_jsonb(t) AS row FROM {} t").format(
                    sql.Identifier(row["tablename"])
                )
            ).fetchall()
        )
        for row in tables
    }


def verify_preserved(before: dict[str, list[str]], after: dict[str, list[str]]) -> None:
    if before.keys() != after.keys():
        raise ValueError("D5a must not change database schema")
    for table, hashes in before.items():
        if not set(hashes).issubset(after[table]) or (
            table not in ALLOWED_ADDITIONS and hashes != after[table]
        ):
            raise ValueError(f"D5a changed prior rows or unrelated state: {table}")


def register_mapping(db: Database, bundle: NormalizationBundle) -> dict[str, Any]:
    """Explicit owner approval is separate from the runtime publisher transaction."""
    with db.transaction():
        db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (REVISION,))
        row = db.execute(
            "SELECT * FROM mapping_revisions WHERE id=%s OR revision_key=%s",
            (bundle.inputs.mapping_revision_id, REVISION),
        ).fetchall()
        if not row:
            db.execute(
                """INSERT INTO mapping_revisions
                (id,revision_key,content_sha256,code_revision,approved_at,approved_by,reviewed_scope)
                VALUES (%s,%s,%s,%s,clock_timestamp(),%s,%s)""",
                (
                    bundle.inputs.mapping_revision_id,
                    REVISION,
                    content_hash(bundle.inputs.rules),
                    bundle.inputs.normalizer_revision,
                    APPROVED_BY,
                    REVIEWED_SCOPE,
                ),
            )
            row = db.execute(
                "SELECT * FROM mapping_revisions WHERE id=%s", (bundle.inputs.mapping_revision_id,)
            ).fetchall()
        if len(row) != 1:
            raise ValueError("Expected one owner-reviewed D5a mapping")
        validate_mapping(row[0], bundle)
        return dict(row[0])


def validate_mapping(row: dict[str, Any], bundle: NormalizationBundle) -> None:
    expected = {
        "id": bundle.inputs.mapping_revision_id,
        "revision_key": REVISION,
        "content_sha256": content_hash(bundle.inputs.rules),
        "code_revision": bundle.inputs.normalizer_revision,
        "approved_by": APPROVED_BY,
        "reviewed_scope": REVIEWED_SCOPE,
    }
    if any(row.get(key) != value for key, value in expected.items()):
        raise ValueError("Existing owner mapping differs from the reviewed D5a mapping")


def readback(db: Database, bundle: NormalizationBundle, batch_id: UUID) -> dict[str, Any]:
    records = db.execute(
        """SELECT DISTINCT c.period_id,c.scope_id,c.currency_unit_id,r.unit_id
        FROM statement_coverage c JOIN fact_resolutions r ON r.coverage_id=c.id
        WHERE c.batch_id=%s""",
        (batch_id,),
    ).fetchall()
    if len(records) != 1:
        raise ValueError("D5a expects one annual consolidated USD statement")
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
        captured_before=CUTOFF,
        mode=HistoryMode.AS_FILED_BY_DATE,
        filed_cutoff=date(2026, 3, 9),
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
    quality = db.execute(
        "SELECT * FROM data_quality_flags WHERE id=ANY(%s) ORDER BY id",
        (list(selected.quality_flag_ids),),
    ).fetchall()
    required = {"inventory_history_incomplete", "event_history_incomplete"}
    if not required.issubset({row["rule_key"] for row in quality}) or any(
        row["batch_id"] != batch_id
        or row["issuer_id"] != inputs.issuer_id
        or row["severity"] not in {"error", "blocking"}
        for row in quality
    ):
        raise ValueError("Published source-history quality evidence differs")
    expected_observations = {
        item.concept_std: item.selected_observation_id for item in bundle.resolutions
    }
    for result in (selected, original):
        if (
            {fact.concept: fact.value for fact in result.facts} != expected
            or result.usable_for_valuation
            or "blocking_quality_flag" not in result.flags
            or result.quality_flag_ids != selected.quality_flag_ids
            or any(
                fact.status != "observed"
                or fact.accession != "0001876042-26-000062"
                or fact.observation_ids != (expected_observations[fact.concept],)
                for fact in result.facts
            )
        ):
            raise ValueError("Published PIT result does not satisfy the reviewed D5a invariants")
    if (
        "earliest_available" not in original.flags
        or "coverage_unavailable" not in earlier.flags
        or any(fact.value is not None for fact in earlier.facts)
    ):
        raise ValueError("Original/earlier cutoff semantics differ from reviewed D5a history")
    return {
        "as_filed": asdict(selected),
        "before_filing": asdict(earlier),
        "original": asdict(original),
        "quality_evidence": quality,
    }


def application(action: str) -> dict[str, Any]:
    bundle, proof = load_preparation()
    if bundle.input_manifest_hash != INPUT_HASH or bundle.output_manifest_hash != OUTPUT_HASH:
        raise ValueError("Preparation changed; new review required before publication")
    audit = read_audit(ROOT)
    archive = LocalArchive(ROOT / "var/raw")
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as owner:
        # A session lock spans separate approval/publication transactions and serializes this CLI.
        owner.execute(
            "SELECT pg_advisory_lock(hashtextextended(%s,0))", (REVISION + "-application",)
        )
        with owner.transaction():
            owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            verify_database_evidence(owner, audit, archive)
            before = rows_snapshot(owner)
        report = {
            "kind": "governed-crcl-normalization",
            "input_hash": INPUT_HASH,
            "output_hash": OUTPUT_HASH,
            "preflight_ready": True,
            "source_precision": proof,
            "inputs": asdict(bundle.inputs),
            "before": {
                key: {"count": len(value), "sha256": content_hash(value)}
                for key, value in before.items()
            },
        }
        if action == "preflight":
            return report
        if action == "publish":
            mapping = register_mapping(owner, bundle)
            with psycopg.connect(
                url.set(drivername="postgresql").render_as_string(hide_password=False),
                autocommit=True,
                row_factory=dict_row,
            ) as db:
                first = publish_bundle(db, bundle)
                second = publish_bundle(db, bundle)
                if first.batch_id != second.batch_id or not second.reused:
                    raise RuntimeError("Exact publication replay must reuse its batch")
        with owner.transaction():
            owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            verify_database_evidence(owner, audit, archive)
            rows = owner.execute(
                "SELECT * FROM normalization_batches WHERE issuer_id=%s", (bundle.inputs.issuer_id,)
            ).fetchall()
            if (
                len(rows) != 1
                or rows[0]["input_manifest_hash"] != INPUT_HASH
                or rows[0]["output_manifest_hash"] != OUTPUT_HASH
            ):
                raise ValueError("Expected exactly the reviewed CRCL batch")
            mapping_row = owner.execute(
                "SELECT * FROM mapping_revisions WHERE id=%s", (bundle.inputs.mapping_revision_id,)
            ).fetchone()
            mapping = dict(mapping_row) if mapping_row else {}
            validate_mapping(mapping, bundle)
            report.update(
                batch=dict(rows[0]),
                mapping=mapping,
            )
            after = rows_snapshot(owner)
        report["selections"] = readback(owner, bundle, rows[0]["id"])
        verify_preserved(before, after)
        if action == "verify" and before != after:
            raise RuntimeError("Read-only verification changed state")
        report.update(
            after={
                key: {"count": len(value), "sha256": content_hash(value)}
                for key, value in after.items()
            },
            prior_rows_preserved=True,
            exact_replay_verified=action == "publish",
            financial_result=False,
        )
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "publish", "verify"))
    args = parser.parse_args()
    try:
        report = application(args.action)
    except (OSError, ValueError, RuntimeError, psycopg.Error):
        print(
            json.dumps(
                {
                    "status": "failed",
                    "action": args.action,
                    "reason": (
                        "Evidence or runtime check failed; no success claimed. "
                        "Mapping approval or publication may already have committed; run verify."
                    ),
                }
            )
        )
        return 1
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
