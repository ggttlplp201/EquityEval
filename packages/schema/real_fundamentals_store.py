"""D048 real source-only storage; owner proofs precede fenced W1 publication."""

from __future__ import annotations

import hashlib
from datetime import UTC
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from equity_ingest.archive import LocalArchive
from equity_ingest.financial_types import PeriodSpec, ScopeSpec, UnitSpec
from equity_ingest.financial_types import canonical_json as descriptor_json
from equity_schema.fundamentals_canonical import canonical_json, content_hash, parse_canonical
from equity_schema.pit import read_statements
from equity_schema.real_fundamentals import (
    RealFundamentalsPayload as FundamentalsPayload,
)
from equity_schema.real_fundamentals import (
    RealInputManifest as InputManifest,
)
from equity_schema.real_fundamentals import (
    RealSnapshotResponse as SnapshotResponse,
)
from equity_schema.real_fundamentals import (
    read_manifest,
)
from equity_schema.workflow import Database, Lease, RequestHandle, _invoke, _request
from psycopg import sql
from psycopg.types.json import Jsonb


def engine_revision() -> str:
    """Pin installed engine and transfer contracts; never infer a mutable git label."""
    import equity_core
    import equity_ingest
    import equity_schema

    digest = hashlib.sha256()
    for package in (equity_core, equity_ingest, equity_schema):
        assert package.__file__ is not None
        root = Path(package.__file__).parent
        for path in sorted(root.glob("*.py")):
            digest.update(f"{package.__name__}/{path.name}\0".encode())
            digest.update(path.read_bytes())
    return "s6-real-v2-sha256:" + digest.hexdigest()


def _history(
    db: Database, workspace_id: UUID, manifest: InputManifest
) -> dict[UUID, FundamentalsPayload]:
    results = {}
    for ref in manifest.history_samples:
        snapshot = get_snapshot(db, workspace_id=workspace_id, snapshot_id=ref.snapshot_id)
        if snapshot is None or snapshot.payload_hash != ref.payload_hash:
            raise ValueError(
                "Historical snapshot is missing, outside workspace, or has a different hash"
            )
        results[ref.snapshot_id] = snapshot.result
    return results


def _require_idle_autocommit(db: Database) -> None:
    from psycopg.pq import TransactionStatus

    if not db.autocommit or db.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("S6 writes require an idle autocommit connection")


def freeze_inputs(db: Database, lease: Lease, *, stage_id: UUID, review_id: UUID) -> UUID:
    _require_idle_autocommit(db)
    return UUID(
        str(
            _invoke(
                db,
                "SELECT real_fundamentals_freeze(%s,%s,%s) AS result",
                (Jsonb(lease.as_json()), stage_id, review_id),
            )
        )
    )


def frozen_manifest(db: Database, input_snapshot_id: UUID) -> tuple[UUID, InputManifest]:
    row = db.execute(
        """SELECT v.workspace_id,v.manifest_text,v.manifest_hash
      FROM real_fundamentals_input_snapshots i
      JOIN real_fundamentals_input_reviews v ON v.id=i.review_id WHERE i.id=%s""",
        (input_snapshot_id,),
    ).fetchone()
    if not row:
        raise ValueError("Unknown frozen input snapshot")
    manifest = read_manifest(row["manifest_text"])
    if content_hash(manifest) != row["manifest_hash"]:
        raise ValueError("Stored manifest digest mismatch")
    return row["workspace_id"], manifest


def calculate_and_publish(
    db: Database, lease: Lease, *, stage_id: UUID, input_snapshot_id: UUID
) -> UUID:
    """Compute only frozen inputs, outside the atomic publication transaction."""
    from equity_core.real_fundamentals import calculate_payload

    _require_idle_autocommit(db)
    saved = db.execute(SNAPSHOT_SQL + " WHERE r.id=%s", (lease.request_id,)).fetchone()
    if saved:
        # A committed result survives engine upgrades; replay original bytes only.
        _snapshot(saved)
        payload_text = saved["payload_text"]
    else:
        workspace, manifest = frozen_manifest(db, input_snapshot_id)
        if manifest.selector.engine_revision != engine_revision():
            raise ValueError("Engine artifact differs from the pinned build")
        payload = calculate_payload(manifest, history_payloads=_history(db, workspace, manifest))
        payload_text = canonical_json(payload)
    return UUID(
        str(
            _invoke(
                db,
                "SELECT real_fundamentals_publish(%s,%s,%s,%s) AS result",
                (Jsonb(lease.as_json()), stage_id, input_snapshot_id, payload_text),
            )
        )
    )


def _snapshot(row: dict[str, Any]) -> SnapshotResponse:
    parse_canonical(row["payload_text"])
    payload = FundamentalsPayload.model_validate_json(row["payload_text"])
    if (
        canonical_json(payload) != row["payload_text"]
        or content_hash(payload) != row["payload_hash"]
    ):
        raise ValueError("Stored payload digest or typed representation mismatch")
    return SnapshotResponse(
        snapshot_id=row["id"],
        request_id=row["request_id"],
        execution_id=row["execution_id"],
        input_snapshot_id=row["input_snapshot_id"],
        generated_at=row["generated_at"].astimezone(UTC),
        compatibility_key=row["compatibility_hash"],
        payload_hash=row["payload_hash"],
        outcome=row["outcome"],
        result=payload,
    )


SNAPSHOT_SQL = """SELECT s.*,p.payload_text,v.compatibility_hash FROM real_fundamentals_snapshots s
 JOIN analysis_requests r ON r.id=s.request_id
 JOIN real_fundamentals_input_snapshots i ON i.id=s.input_snapshot_id
 JOIN real_fundamentals_input_reviews v ON v.id=i.review_id
 JOIN real_fundamentals_calculation_payloads p ON p.payload_hash=s.payload_hash"""


def get_snapshot(db: Database, *, workspace_id: UUID, snapshot_id: UUID) -> SnapshotResponse | None:
    row = db.execute(
        SNAPSHOT_SQL + " WHERE r.workspace_id=%s AND s.id=%s", (workspace_id, snapshot_id)
    ).fetchone()
    return _snapshot(row) if row else None


def get_latest(
    db: Database, *, workspace_id: UUID, issuer_id: UUID, security_id: UUID, compatibility_key: str
) -> tuple[SnapshotResponse | None, UUID, str] | None:
    row = db.execute(
        """SELECT l.snapshot_id,l.latest_request_id,e.state FROM latest_real_fundamentals l
    JOIN analysis_request_state c ON c.request_id=l.latest_request_id
    JOIN analysis_executions e ON e.id=c.current_execution_id
    WHERE l.workspace_id=%s AND l.issuer_id=%s AND l.security_id=%s AND l.compatibility_hash=%s""",
        (workspace_id, issuer_id, security_id, compatibility_key),
    ).fetchone()
    if not row:
        return None
    saved = (
        get_snapshot(db, workspace_id=workspace_id, snapshot_id=row["snapshot_id"])
        if row["snapshot_id"]
        else None
    )
    return saved, row["latest_request_id"], row["state"]


def compatibility_key(manifest: InputManifest) -> str:
    return content_hash(
        {"version": "s6-fundamentals-v2", "evidence_mode": "real", "selector": manifest.selector}
    )


def policy_document(manifest: InputManifest) -> dict[str, Any]:
    return {
        "context": manifest.context,
        "history_policy": manifest.history_policy,
        "trend_policy": manifest.trend_policy,
        "evidence": manifest.policy_evidence,
    }


def enqueue_fundamentals(
    db: Database,
    *,
    workspace_id: UUID,
    review_id: UUID,
    idempotency_key: str,
    parent_request_id: UUID | None = None,
    max_attempts: int = 3,
) -> RequestHandle:
    _require_idle_autocommit(db)
    return _request(
        _invoke(
            db,
            "SELECT real_fundamentals_enqueue(%s,%s,%s,%s,%s) AS result",
            (workspace_id, review_id, idempotency_key, parent_request_id, max_attempts),
        )
    )


def claim_real_fundamentals(
    db: Database, *, worker_id: str, lease_seconds: int = 60, request_id: UUID | None = None
) -> Lease | None:
    from equity_schema.workflow import _lease

    result = _invoke(
        db,
        "SELECT workflow_claim_real_fundamentals(%s,%s,%s) AS result",
        (worker_id, lease_seconds, request_id),
    )
    return _lease(result) if result is not None else None


def _verify_sources(db: Database, manifest: InputManifest, archive: LocalArchive) -> None:
    for capture in manifest.captures:
        row = db.execute(
            "SELECT fetched_at,body_sha256 FROM source_captures WHERE id=%s", (capture.capture_id,)
        ).fetchone()
        if (
            row is None
            or row["fetched_at"] != capture.fetched_at
            or row["body_sha256"] != capture.body_sha256
        ):
            raise ValueError("Capture provenance differs from retained evidence")
    sources = manifest.sources
    if sources:
        actual = read_statements(db, tuple(source.selection.query for source in sources))
        if actual.statements != tuple(source.selection for source in sources):
            raise ValueError("Frozen selections differ from retained point-in-time evidence")
    for source in sources:
        period = db.execute("SELECT * FROM periods WHERE id=%s", (source.period.id,)).fetchone()
        unit = db.execute("SELECT * FROM units WHERE id=%s", (source.unit.id,)).fetchone()
        scope = db.execute(
            "SELECT * FROM semantic_scopes WHERE id=%s", (source.scope.id,)
        ).fetchone()
        if (
            not period
            or not unit
            or not scope
            or (
                PeriodSpec(
                    period["id"], period["period_kind"], period["start_date"], period["end_date"]
                )
                != source.period
                or UnitSpec(
                    unit["id"],
                    unit["unit_key"],
                    tuple(unit["numerator_measures"]),
                    tuple(unit["denominator_measures"]),
                )
                != source.unit
                or ScopeSpec(
                    scope["id"],
                    scope["issuer_id"],
                    scope["instrument_id"],
                    scope["scope_kind"],
                    scope["descriptor_schema_version"],
                    descriptor_json(scope["descriptor_json"]),
                    scope["content_sha256"],
                )
                != source.scope
            )
        ):
            raise ValueError("Source metadata differs from retained typed records")
    capture_rows = {}
    bodies = {}
    for capture in manifest.captures:
        row = db.execute(
            "SELECT c.*,s.cik FROM source_captures c JOIN issuers s ON s.id=%s WHERE c.id=%s",
            (manifest.selector.issuer_id, capture.capture_id),
        ).fetchone()
        if (
            row is None
            or row["http_status"] != 200
            or not row["request_url"].startswith(
                ("https://www.sec.gov/Archives/", "https://data.sec.gov/")
            )
        ):
            raise ValueError(
                "Real source evidence must be retained successful official SEC content"
            )
        capability = db.execute(
            """SELECT 1 FROM capture_policy_links l JOIN source_policy_capabilities c
             ON c.policy_revision_id=l.policy_revision_id WHERE l.capture_id=%s
             AND c.internal_analysis_allowed
             AND c.raw_retention='indefinite_without_required_deletion'
             AND c.normalized_retention='indefinite_without_required_deletion'""",
            (capture.capture_id,),
        ).fetchone()
        if not capability:
            # SEC S3 source reviews predate and are independent of S4 market capabilities.
            policy = db.execute(
                """SELECT p.* FROM capture_policy_links l JOIN source_policy_revisions p
                ON p.id=l.policy_revision_id WHERE l.capture_id=%s AND p.source_id=%s""",
                (capture.capture_id, row["source_id"]),
            ).fetchone()
            reference = "docs/research/sec-application-policy-2026-09-21.md"
            digest = "719f60fbe146bbcfaba8049b4f8b61d0785915cc910187ff2b48f0e9479d2c4f"
            artifact = Path(__file__).resolve().parents[2] / reference
            if (
                not policy
                or policy["review_key"] != "sec-public-filings-2026-09-21"
                or policy["review_artifact_reference"] != reference
                or policy["review_artifact_sha256"] != digest
                or policy["reviewed_at"] > capture.fetched_at
                or not artifact.is_file()
                or hashlib.sha256(artifact.read_bytes()).hexdigest() != digest
            ):
                raise ValueError(
                    "Retained source lacks reviewed internal-analysis retention rights"
                )
        capture_rows[capture.capture_id] = row
        bodies[capture.capture_id] = archive.read_blob(
            row["blob_key"], row["body_sha256"], row["byte_count"]
        )
    for policy_proof in manifest.policy_evidence:
        if policy_proof.locator != "document":
            raise ValueError("Real policy currently requires full retained-document review")
    proved = set()
    extractions = {}
    from equity_core.real_fundamentals import precision_error
    from equity_ingest.filing import extract_inline_filing, select_filing_fact

    for proof in manifest.precision_evidence:
        source = manifest.sources[proof.input_index]
        row = capture_rows[proof.capture_id]
        if (
            row["request_url"] != proof.source_url
            or row["fetched_at"] != proof.fetched_at
            or source.fact is None
            or source.fact.accession != proof.accession
            or proof.accession not in row["source_object_key"]
        ):
            raise ValueError("Precision filing lineage differs from selected source edition")
        if proof.capture_id not in extractions:
            extractions[proof.capture_id] = extract_inline_filing(
                bodies[proof.capture_id],
                expected_sha256=row["body_sha256"],
                expected_byte_count=row["byte_count"],
                expected_cik=row["cik"],
            )
        extraction = extractions[proof.capture_id]
        selected = select_filing_fact(
            extraction,
            qualified_tag=proof.qualified_tag,
            context_id=proof.context_id,
            unit_id=proof.unit_id,
            expected_dimensions=(),
        )
        contexts = [c for c in extraction.contexts if c.id == proof.context_id]
        units = [u for u in extraction.units if u.id == proof.unit_id]
        fact = selected.fact
        if (
            selected.status != "observed"
            or fact is None
            or selected.value != source.value
            or proof.locator not in selected.candidate_locators
            or fact.decimals != proof.decimals
            or fact.scale != proof.scale
            or fact.sign != proof.sign
            or fact.precision is not None
            or len(contexts) != 1
            or contexts[0].start_date != source.period.start_date
            or contexts[0].end_date != source.period.end_date
            or contexts[0].cik != row["cik"]
            or contexts[0].dimensions
            or len(units) != 1
            or units[0].denominator_measures
            or units[0].numerator_measures
            != ("{http://www.xbrl.org/2003/iso4217}" + source.unit.unit_key,)
            or proof.qualified_tag.rsplit("}", 1)[-1]
            != (source.fact.source_tag or "").split(":")[-1]
            or source.precision is None
            or source.precision.absolute_error != precision_error(proof.decimals)
            or source.precision.evidence_refs
            != (f"capture:{proof.capture_id}:{proof.body_sha256}:{proof.locator}",)
        ):
            raise ValueError(
                "Selected fact/context/unit/sign/scale/precision proof differs from retained filing"
            )
        proved.add(proof.input_index)
    if proved != {i for i, source in enumerate(manifest.sources) if source.precision is not None}:
        raise ValueError("Every asserted source precision needs an exact retained filing proof")


def approve_real_manifest(
    db: Database,
    *,
    workspace_id: UUID,
    manifest: InputManifest,
    archive: LocalArchive,
    reviewed_by: str,
    reason: str,
) -> UUID:
    """Owner-only review of replayed real sources and deterministic expected output."""
    from equity_core.real_fundamentals import calculate_payload

    _require_idle_autocommit(db)
    manifest = read_manifest(canonical_json(manifest))
    if not reviewed_by.strip() or not reason.strip():
        raise ValueError("Explicit real review identity and rationale required")
    if manifest.selector.engine_revision != engine_revision():
        raise ValueError("Engine artifact differs from reviewed build")
    _verify_sources(db, manifest, archive)
    expected = calculate_payload(manifest, history_payloads=_history(db, workspace_id, manifest))
    policy = policy_document(manifest)
    review_id = uuid4()
    with db.transaction():
        prior = db.execute(
            "SELECT id FROM real_fundamentals_input_reviews "
            "WHERE workspace_id=%s AND manifest_hash=%s",
            (workspace_id, content_hash(manifest)),
        ).fetchone()
        if prior:
            return UUID(str(prior["id"]))
        stored = db.execute(
            "SELECT id FROM real_fundamentals_policy_reviews WHERE policy_hash=%s",
            (content_hash(policy),),
        ).fetchone()
        policy_id = stored["id"] if stored else uuid4()
        if not stored:
            db.execute(
                """INSERT INTO real_fundamentals_policy_reviews
              (id,issuer_id,policy_text,policy_hash,effective_on,known_on,reviewed_by,reason)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    policy_id,
                    manifest.selector.issuer_id,
                    canonical_json(policy),
                    content_hash(policy),
                    manifest.context.profile.effective_on,
                    manifest.context.profile.known_on,
                    reviewed_by,
                    reason,
                ),
            )
            for index, proof in enumerate(manifest.policy_evidence):
                db.execute(
                    "INSERT INTO real_fundamentals_policy_evidence VALUES(%s,%s,%s,%s,%s,%s)",
                    (
                        policy_id,
                        index,
                        proof.capture_id,
                        proof.body_sha256,
                        proof.locator,
                        proof.purpose,
                    ),
                )
        db.execute(
            """INSERT INTO real_fundamentals_input_reviews
          (id,workspace_id,issuer_id,security_id,policy_review_id,manifest_text,manifest_hash,
          compatibility_text,compatibility_hash,expected_payload_hash,reviewed_by,reason)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                review_id,
                workspace_id,
                manifest.selector.issuer_id,
                manifest.selector.security_id,
                policy_id,
                canonical_json(manifest),
                content_hash(manifest),
                canonical_json(manifest.selector),
                compatibility_key(manifest),
                content_hash(expected),
                reviewed_by,
                reason,
            ),
        )
        for capture in manifest.captures:
            db.execute(
                "INSERT INTO real_fundamentals_review_captures VALUES(%s,%s,%s,%s)",
                (review_id, capture.capture_id, capture.body_sha256, capture.fetched_at),
            )
        for index, source in enumerate(manifest.sources):
            selection, query = source.selection, source.selection.query
            db.execute(
                "INSERT INTO real_fundamentals_review_inputs VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    review_id,
                    index,
                    source.period.id,
                    source.unit.id,
                    source.scope.id,
                    query.mapping_revision_id,
                    selection.input_hash,
                ),
            )
            refs = {
                "batches": query.batch_ids,
                "captures": query.capture_ids,
                "editions": selection.filing_version_ids,
                "coverage": selection.coverage_ids,
                "events": (*query.filing_event_ids, *selection.event_ids),
                "quality": (*query.additional_quality_flag_ids, *selection.quality_flag_ids),
                "resolutions": tuple(v for fact in selection.facts for v in fact.resolution_ids),
                "observations": tuple(v for fact in selection.facts for v in fact.observation_ids),
            }
            for name, values in refs.items():
                for value in sorted(set(values), key=str):
                    db.execute(
                        sql.SQL("INSERT INTO {} VALUES(%s,%s,%s)").format(
                            sql.Identifier("real_fundamentals_input_" + name)
                        ),
                        (review_id, index, value),
                    )
        for index, ref in enumerate(manifest.history_samples):
            db.execute(
                "INSERT INTO real_fundamentals_review_history VALUES(%s,%s,%s,%s,%s)",
                (review_id, index, ref.snapshot_id, ref.payload_hash, ref.quarter_end),
            )
    return review_id
