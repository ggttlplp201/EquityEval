"""Publish pinned normalization evidence in one short local transaction."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from equity_schema.workflow import Database, Lease, LeaseLost, finish_stage, renew_lease
from psycopg import sql
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from .archive import ArchivedBody
from .financial_types import NormalizationBundle, canonical_json, content_hash, evidence_id
from .sec_normalize import bundle_output_hash, normalization_input_hash


class PublicationConflict(ValueError):
    """Evidence differs from its immutable approved identity."""


@dataclass(frozen=True)
class PublishedBatch:
    batch_id: UUID
    reused: bool
    quality_flag_ids: tuple[UUID, ...]
    original_history_complete: bool
    capture_ids: tuple[UUID, ...] = ()
    filing_event_ids: tuple[UUID, ...] = ()
    additional_quality_flag_ids: tuple[UUID, ...] = ()


_JSON = {
    "descriptor_json",
    "transform_metadata",
    "raw_metadata",
    "raw_dimensions",
    "evidence_references",
}


def _data(value: Any) -> dict[str, Any]:
    result = asdict(value)
    for key, item in result.items():
        if key in _JSON and item is not None:
            result[key] = json.loads(item)
        elif isinstance(item, Enum):
            result[key] = item.value
        elif isinstance(item, tuple):
            result[key] = list(item)
    return result


def _insert(db: Database, table: str, values: dict[str, Any], *, ignore: bool = False) -> None:
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}){}").format(
        sql.Identifier(table),
        sql.SQL(",").join(map(sql.Identifier, values)),
        sql.SQL(",").join(sql.Placeholder() for _ in values),
        sql.SQL(" ON CONFLICT DO NOTHING") if ignore else sql.SQL(""),
    )
    db.execute(
        statement, [Jsonb(v) if k in _JSON and v is not None else v for k, v in values.items()]
    )


def _identity(db: Database, table: str, values: dict[str, Any], natural: tuple[str, ...]) -> UUID:
    condition = sql.SQL(" AND ").join(
        sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(k)) for k in natural
    )
    statement = sql.SQL("SELECT * FROM {} WHERE {}").format(sql.Identifier(table), condition)
    params = [values[k] for k in natural]
    row = db.execute(statement, params).fetchone()
    if row is None:
        _insert(db, table, values, ignore=True)
        row = db.execute(statement, params).fetchone()
    if row is None or any(row[k] != v for k, v in values.items() if k != "id"):
        raise PublicationConflict(f"{table} immutable identity/evidence conflict")
    return UUID(str(row["id"]))


def _validate_inputs(db: Database, bundle: NormalizationBundle) -> None:
    inputs = bundle.inputs
    if (
        normalization_input_hash(inputs) != bundle.input_manifest_hash
        or bundle_output_hash(bundle) != bundle.output_manifest_hash
    ):
        raise PublicationConflict("Normalization manifest hash mismatch")
    issuer = db.execute("SELECT cik FROM issuers WHERE id=%s", (inputs.issuer_id,)).fetchone()
    if issuer is None or issuer["cik"] != inputs.cik:
        raise PublicationConflict("Registered issuer differs from pinned CIK")
    mapping = db.execute(
        "SELECT content_sha256 FROM mapping_revisions WHERE id=%s", (inputs.mapping_revision_id,)
    ).fetchone()
    if mapping is None or mapping["content_sha256"] != content_hash(inputs.rules):
        raise PublicationConflict("Rules differ from the approved mapping revision")
    for scope in bundle.scopes:
        if scope.instrument_id is not None:
            instrument = db.execute(
                "SELECT issuer_id,instrument_kind FROM securities WHERE id=%s",
                (scope.instrument_id,),
            ).fetchone()
            if (
                instrument is None
                or instrument["issuer_id"] != inputs.issuer_id
                or instrument["instrument_kind"] != scope.scope_kind
            ):
                raise PublicationConflict("Scope differs from the registered share instrument")
    for capture in inputs.captures:
        row = db.execute("SELECT * FROM source_captures WHERE id=%s", (capture.id,)).fetchone()
        wanted = asdict(capture)
        wanted.pop("role")
        if row is None or any(row[k] != v for k, v in wanted.items()):
            raise PublicationConflict("Pinned capture differs from archived database evidence")
        if (
            row["http_status"] is None
            or not 200 <= row["http_status"] < 300
            or row["blob_key"] is None
        ):
            raise PublicationConflict("Pinned capture is not complete successful evidence")
        if row["completed_at"] > inputs.captured_before:
            raise PublicationConflict("Pinned capture exceeds retrieval cutoff")
        policy = db.execute(
            "SELECT policy_revision_id FROM capture_policy_links WHERE capture_id=%s",
            (capture.id,),
        ).fetchone()
        if policy is None:
            raise PublicationConflict("Pinned capture requires an explicit source-policy review")
    capture_ids = {c.id for c in inputs.captures}
    source_ids = {c.source_id for c in inputs.captures}
    for event in inputs.filing_event_ids:
        row = db.execute(
            "SELECT e.issuer_id,f.metadata_capture_id FROM filing_events e "
            "JOIN filing_versions f ON f.id=e.source_filing_version_id WHERE e.id=%s",
            (event,),
        ).fetchone()
        if (
            row is None
            or row["issuer_id"] != inputs.issuer_id
            or row["metadata_capture_id"] not in capture_ids
        ):
            raise PublicationConflict("Pinned event lacks issuer/capture evidence")
    for flag in inputs.additional_quality_flag_ids:
        row = db.execute("SELECT issuer_id FROM data_quality_flags WHERE id=%s", (flag,)).fetchone()
        if row is None or row["issuer_id"] != inputs.issuer_id:
            raise PublicationConflict("Pinned quality flag is absent or belongs to another issuer")
    for attempt in inputs.attempt_ids:
        row = db.execute(
            "SELECT source_id,finished_at FROM source_fetch_attempts WHERE id=%s", (attempt,)
        ).fetchone()
        if (
            row is None
            or row["source_id"] not in source_ids
            or row["finished_at"] is None
            or row["finished_at"] > inputs.captured_before
        ):
            raise PublicationConflict("Pinned attempt is absent, unfinished or outside cutoff")


NORMALIZATION_STAGE = "sec_normalization"


def _check_stage(db: Database, lease: Lease, stage_id: UUID, issuer_id: UUID) -> None:
    renew_lease(db, lease, lease_seconds=60)
    row = db.execute(
        "SELECT st.execution_id,st.state,st.stage_key,s.issuer_id "
        "FROM analysis_stage_attempts st "
        "JOIN analysis_executions e ON e.id=st.execution_id "
        "JOIN analysis_requests r ON r.id=e.request_id "
        "JOIN securities s ON s.id=r.security_id WHERE st.id=%s",
        (stage_id,),
    ).fetchone()
    if row is None or row["execution_id"] != lease.execution_id or row["state"] != "running":
        raise LeaseLost("Normalization stage is no longer running on this execution")
    if row["issuer_id"] != issuer_id or row["stage_key"] != NORMALIZATION_STAGE:
        raise PublicationConflict("Normalization issuer or stage purpose differs from the request")


def publish_bundle(
    db: Database,
    bundle: NormalizationBundle,
    *,
    lease: Lease | None = None,
    stage_id: UUID | None = None,
    stage_manifest: ArchivedBody | None = None,
) -> PublishedBatch:
    """Publish once; archived replay may run without a live execution stage."""
    if db.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("Publication requires an idle connection")
    if (lease is None) != (stage_id is None):
        raise ValueError("Lease and stage must be supplied together")
    if stage_manifest is not None and lease is None:
        raise ValueError("A stage manifest needs a leased workflow stage")
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        if lease is not None and stage_id is not None:
            _check_stage(db, lease, stage_id, bundle.inputs.issuer_id)
        _validate_inputs(db, bundle)
        db.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
            ("normalization:" + str(bundle.inputs.issuer_id),),
        )
        existing = db.execute(
            """
            SELECT id,output_manifest_hash FROM normalization_batches
            WHERE issuer_id=%s AND mapping_revision_id=%s AND normalizer_revision=%s
              AND source_authority_policy_revision=%s AND input_manifest_hash=%s
              AND state='published'
        """,
            (
                bundle.inputs.issuer_id,
                bundle.inputs.mapping_revision_id,
                bundle.inputs.normalizer_revision,
                bundle.inputs.authority_policy_revision,
                bundle.input_manifest_hash,
            ),
        ).fetchall()
        if existing:
            if (
                len(existing) != 1
                or existing[0]["output_manifest_hash"] != bundle.output_manifest_hash
            ):
                raise PublicationConflict(
                    "Nondeterministic output for the same pinned inputs/revisions"
                )
            batch_id = existing[0]["id"]
            flags = db.execute(
                "SELECT id FROM data_quality_flags WHERE batch_id=%s ORDER BY id", (batch_id,)
            ).fetchall()
            if lease is not None and stage_id is not None:
                _check_stage(db, lease, stage_id, bundle.inputs.issuer_id)
            result = _result(bundle, batch_id, True, tuple(r["id"] for r in flags))
            _complete_stage(db, lease, stage_id, stage_manifest, result)
            return result
        periods = {
            r.id: _identity(db, "periods", _data(r), ("period_kind", "start_date", "end_date"))
            for r in bundle.periods
        }
        units = {r.id: _identity(db, "units", _data(r), ("unit_key",)) for r in bundle.units}
        scopes = {
            r.id: _identity(
                db,
                "semantic_scopes",
                _data(r),
                ("issuer_id", "descriptor_schema_version", "content_sha256"),
            )
            for r in bundle.scopes
        }
        filings: dict[UUID, UUID] = {}
        for filing in bundle.filings:
            filing_id = _identity(
                db,
                "filings",
                {
                    "id": filing.filing_id,
                    "issuer_id": filing.issuer_id,
                    "accession": filing.accession,
                },
                ("issuer_id", "accession"),
            )
            values = _data(filing)
            for key in ("issuer_id", "accession"):
                values.pop(key)
            values["filing_id"] = filing_id
            filings[filing.id] = _identity(
                db, "filing_versions", values, ("filing_id", "metadata_capture_id", "metadata_hash")
            )
        now, batch_id = datetime.now(UTC), uuid4()
        _insert(
            db,
            "normalization_batches",
            {
                "id": batch_id,
                "issuer_id": bundle.inputs.issuer_id,
                "mapping_revision_id": bundle.inputs.mapping_revision_id,
                "normalizer_revision": bundle.inputs.normalizer_revision,
                "source_authority_policy_revision": bundle.inputs.authority_policy_revision,
                "created_at": now,
                "state": "building",
            },
        )
        for capture in bundle.inputs.captures:
            _insert(
                db,
                "normalization_inputs",
                {"batch_id": batch_id, "source_capture_id": capture.id, "role": capture.role},
            )
        coverage: dict[UUID, UUID] = {}
        for coverage_row in bundle.coverage:
            values = _data(coverage_row)
            values.update(
                id=evidence_id("published-coverage", [batch_id, coverage_row.id]),
                batch_id=batch_id,
                filing_version_id=filings[coverage_row.filing_version_id],
                period_id=periods[coverage_row.period_id],
                scope_id=scopes[coverage_row.scope_id],
                currency_unit_id=units[coverage_row.currency_unit_id]
                if coverage_row.currency_unit_id
                else None,
            )
            _insert(db, "statement_coverage", values)
            coverage[coverage_row.id] = values["id"]
        observations: dict[UUID, UUID] = {}
        for observation in bundle.observations:
            values = _data(observation)
            values.update(
                filing_version_id=filings[observation.filing_version_id],
                period_id=periods[observation.period_id],
                unit_id=units[observation.unit_id],
                semantic_scope_id=scopes[observation.semantic_scope_id]
                if observation.semantic_scope_id
                else None,
            )
            observations[observation.id] = _identity(
                db, "source_observations", values, ("source_capture_id", "source_locator")
            )
        resolutions: dict[UUID, UUID] = {}
        for resolution in bundle.resolutions:
            values = _data(resolution)
            values.update(
                id=evidence_id("published-resolution", [batch_id, resolution.id]),
                coverage_id=coverage[resolution.coverage_id],
                semantic_scope_id=scopes[resolution.semantic_scope_id],
                unit_id=units[resolution.unit_id],
                selected_observation_id=observations[resolution.selected_observation_id]
                if resolution.selected_observation_id
                else None,
            )
            _insert(db, "fact_resolutions", values)
            resolutions[resolution.id] = values["id"]
        for candidate in bundle.candidates:
            values = _data(candidate)
            values.update(
                resolution_id=resolutions[candidate.resolution_id],
                observation_id=observations[candidate.observation_id],
            )
            _insert(db, "resolution_candidates", values)
        flag_ids = []
        for flag in bundle.quality_flags:
            values = _data(flag)
            values.update(
                id=evidence_id("published-flag", [batch_id, flag.id]),
                batch_id=batch_id,
                raised_at=now,
                resolution_id=resolutions[flag.resolution_id] if flag.resolution_id else None,
                period_id=periods[flag.period_id] if flag.period_id else None,
            )
            _insert(db, "data_quality_flags", values)
            flag_ids.append(values["id"])
        if lease is not None and stage_id is not None:
            _check_stage(db, lease, stage_id, bundle.inputs.issuer_id)
        db.execute(
            """
            UPDATE normalization_batches SET state='published',published_at=clock_timestamp(),
                input_manifest_hash=%s,output_manifest_hash=%s WHERE id=%s
        """,
            (bundle.input_manifest_hash, bundle.output_manifest_hash, batch_id),
        )
        result = _result(bundle, batch_id, False, tuple(flag_ids))
        _complete_stage(db, lease, stage_id, stage_manifest, result)
        return result


def _result(
    bundle: NormalizationBundle, batch_id: UUID, reused: bool, flags: tuple[UUID, ...]
) -> PublishedBatch:
    additional = bundle.inputs.additional_quality_flag_ids
    return PublishedBatch(
        batch_id,
        reused,
        tuple(dict.fromkeys((*flags, *additional))),
        bundle.original_history_complete,
        tuple(c.id for c in bundle.inputs.captures),
        bundle.inputs.filing_event_ids,
        additional,
    )


def _complete_stage(
    db: Database,
    lease: Lease | None,
    stage_id: UUID | None,
    manifest: ArchivedBody | None,
    result: PublishedBatch,
) -> None:
    if manifest is not None:
        assert lease is not None and stage_id is not None
        finish_stage(
            db,
            lease,
            stage_id=stage_id,
            outcome="completed",
            reason=canonical_json(
                {
                    "batch_id": result.batch_id,
                    "manifest": asdict(manifest),
                    "original_history_complete": result.original_history_complete,
                }
            ),
        )
