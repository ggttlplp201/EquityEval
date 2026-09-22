"""Governed S6a storage. Owner reviews; fenced workers publish; readers never compute."""

from __future__ import annotations

import hashlib
from datetime import UTC
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from equity_ingest.financial_types import PeriodSpec, ScopeSpec, UnitSpec
from equity_ingest.financial_types import canonical_json as descriptor_json
from equity_schema.fundamentals import (
    FundamentalsPayload,
    InputManifest,
    SnapshotResponse,
    read_manifest,
)
from equity_schema.fundamentals_canonical import canonical_json, content_hash, parse_canonical
from equity_schema.pit import read_statements
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
    return "s6a-sha256:" + digest.hexdigest()


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


def _verify_sources(db: Database, manifest: InputManifest) -> None:
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
        for capture_id in source.selection.query.capture_ids:
            row = db.execute(
                "SELECT c.request_url,s.content_scope FROM source_captures c "
                "JOIN sources s ON s.id=c.source_id WHERE c.id=%s",
                (capture_id,),
            ).fetchone()
            if (
                not row
                or row["content_scope"] != "test fixture"
                or not row["request_url"].startswith("https://example.invalid/")
            ):
                raise ValueError("S6a accepts governed fictional evidence only")


def approve_fixture_manifest(
    db: Database, *, workspace_id: UUID, manifest: InputManifest, reviewed_by: str, reason: str
) -> UUID:
    """Owner-only synthetic review, including a reproducible expected output digest.

    This review calculation is not a published result. Workers still freeze the
    request-owned manifest before calculating. The digest prevents a compromised
    worker from substituting another result through the SQL writer.
    """
    from equity_core.fundamentals import calculate_payload

    _require_idle_autocommit(db)
    manifest = read_manifest(canonical_json(manifest))
    if not reviewed_by.strip() or not reason.strip():
        raise ValueError("Explicit review identity and rationale required")
    if manifest.selector.engine_revision != engine_revision():
        raise ValueError("Engine artifact differs from the pinned build")
    _verify_sources(db, manifest)
    expected = calculate_payload(manifest, history_payloads=_history(db, workspace_id, manifest))
    review_id = uuid4()
    with db.transaction():
        prior = db.execute(
            "SELECT id FROM fundamentals_input_reviews WHERE workspace_id=%s AND manifest_hash=%s",
            (workspace_id, content_hash(manifest)),
        ).fetchone()
        if prior:
            return UUID(str(prior["id"]))
        db.execute(
            """INSERT INTO fundamentals_input_reviews
          (id,workspace_id,issuer_id,security_id,quote_identifier_id,manifest_text,manifest_hash,
           compatibility_text,compatibility_hash,expected_payload_hash,reviewed_by,reason)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                review_id,
                workspace_id,
                manifest.selector.issuer_id,
                manifest.selector.security_id,
                manifest.selector.quote_identifier_id,
                canonical_json(manifest),
                content_hash(manifest),
                canonical_json(manifest.selector),
                content_hash(manifest.selector),
                content_hash(expected),
                reviewed_by,
                reason,
            ),
        )
        for index, source in enumerate(manifest.sources):
            selection, query = source.selection, source.selection.query
            db.execute(
                "INSERT INTO fundamentals_review_inputs VALUES(%s,%s,%s,%s,%s,%s,%s)",
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
                            sql.Identifier("fundamentals_review_" + name)
                        ),
                        (review_id, index, value),
                    )
        for index, ref in enumerate(manifest.history_samples):
            db.execute(
                "INSERT INTO fundamentals_review_history VALUES(%s,%s,%s,%s,%s)",
                (review_id, index, ref.snapshot_id, ref.payload_hash, ref.quarter_end),
            )
    return review_id


def enqueue_fundamentals(
    db: Database,
    *,
    workspace_id: UUID,
    watchlist_id: UUID | None,
    review_id: UUID,
    idempotency_key: str,
    parent_request_id: UUID | None,
    max_attempts: int,
) -> RequestHandle:
    """Narrow W1 wrapper binds complete S6 intent before the job can be claimed."""
    _require_idle_autocommit(db)
    return _request(
        _invoke(
            db,
            "SELECT fundamentals_enqueue(%s,%s,%s,%s,%s,%s) AS result",
            (
                workspace_id,
                watchlist_id,
                review_id,
                idempotency_key,
                parent_request_id,
                max_attempts,
            ),
        )
    )


def freeze_inputs(db: Database, lease: Lease, *, stage_id: UUID, review_id: UUID) -> UUID:
    _require_idle_autocommit(db)
    return UUID(
        str(
            _invoke(
                db,
                "SELECT fundamentals_freeze(%s,%s,%s) AS result",
                (Jsonb(lease.as_json()), stage_id, review_id),
            )
        )
    )


def frozen_manifest(db: Database, input_snapshot_id: UUID) -> tuple[UUID, InputManifest]:
    row = db.execute(
        """SELECT v.workspace_id,v.manifest_text,v.manifest_hash FROM analysis_input_snapshots i
      JOIN fundamentals_input_reviews v ON v.id=i.review_id WHERE i.id=%s""",
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
    from equity_core.fundamentals import calculate_payload

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
                "SELECT fundamentals_publish(%s,%s,%s,%s) AS result",
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


SNAPSHOT_SQL = """SELECT s.*,p.payload_text,v.compatibility_hash FROM analysis_snapshots s
 JOIN analysis_requests r ON r.id=s.request_id
 JOIN analysis_input_snapshots i ON i.id=s.input_snapshot_id
 JOIN fundamentals_input_reviews v ON v.id=i.review_id
 JOIN fundamentals_calculation_payloads p ON p.payload_hash=s.payload_hash"""


def get_snapshot(db: Database, *, workspace_id: UUID, snapshot_id: UUID) -> SnapshotResponse | None:
    row = db.execute(
        SNAPSHOT_SQL + " WHERE r.workspace_id=%s AND s.id=%s", (workspace_id, snapshot_id)
    ).fetchone()
    return _snapshot(row) if row else None


def get_latest(
    db: Database,
    *,
    workspace_id: UUID,
    issuer_id: UUID,
    security_id: UUID,
    compatibility_key: str,
    scope_id: UUID,
) -> tuple[SnapshotResponse | None, UUID, str] | None:
    row = db.execute(
        """SELECT l.snapshot_id,l.latest_request_id,e.state FROM latest_fundamentals l
      JOIN securities sec ON sec.id=l.security_id
      JOIN analysis_request_state c ON c.request_id=l.latest_request_id
      JOIN analysis_executions e ON e.id=c.current_execution_id
      WHERE l.workspace_id=%s AND sec.issuer_id=%s AND l.security_id=%s
      AND l.compatibility_hash=%s AND l.scope_id=%s
      AND (l.scope_id='00000000-0000-0000-0000-000000000000'::UUID OR EXISTS(
        SELECT 1 FROM watchlist_memberships m WHERE m.id=l.scope_id AND m.removed_at IS NULL))""",
        (workspace_id, issuer_id, security_id, compatibility_key, scope_id),
    ).fetchone()
    if not row:
        return None
    snapshot = (
        get_snapshot(db, workspace_id=workspace_id, snapshot_id=row["snapshot_id"])
        if row["snapshot_id"]
        else None
    )
    return snapshot, row["latest_request_id"], row["state"]
