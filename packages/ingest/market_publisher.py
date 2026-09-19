"""Verify archived market evidence, then atomically publish a leased source stage."""

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from equity_schema.market_data import publish
from equity_schema.workflow import Database, Lease
from psycopg.errors import CheckViolation
from psycopg.pq import TransactionStatus

from .archive import ArchivedBody, LocalArchive
from .financial_types import evidence_id
from .market_normalize import market_input_hash, market_output_hash
from .market_types import MarketNormalizationBundle, market_canonical_json
from .provider_contracts import FredResource, PriceResource, ProviderResource, TreasuryResource
from .publisher import PublicationConflict


@dataclass(frozen=True)
class PublishedMarketBatch:
    batch_id: UUID
    reused: bool
    manifest: ArchivedBody
    quality_flag_ids: tuple[UUID, ...]
    capture_ids: tuple[UUID, ...]


def _quote_snapshot(db: Database, bundle: MarketNormalizationBundle) -> dict[str, Any] | None:
    context = bundle.inputs.quote_context
    if context is None:
        return None
    quote = db.execute(
        "SELECT q.*,s.instrument_kind FROM security_identifiers q "
        "JOIN securities s ON s.id=q.security_id WHERE q.id=%s",
        (context.quote_identifier_id,),
    ).fetchone()
    if quote is None:
        raise PublicationConflict("Pinned quote is absent from the identity registry")
    cutoff = bundle.inputs.retrieval_cutoff
    original = db.execute(
        "SELECT completed_at FROM source_captures WHERE id=%s", (quote["source_capture_id"],)
    ).fetchone()
    if (
        original is None
        or original["completed_at"] is None
        or (cutoff is not None and original["completed_at"] > cutoff)
    ):
        raise PublicationConflict("Registered quote evidence exceeds retrieval cutoff")
    closures = db.execute(
        "SELECT cl.*,c.completed_at AS capture_completed_at "
        "FROM security_identifier_closures cl JOIN source_captures c ON c.id=cl.source_capture_id "
        "WHERE cl.quote_identifier_id=%s AND c.completed_at IS NOT NULL "
        "AND (%s::timestamptz IS NULL OR c.completed_at<=%s) ORDER BY cl.id",
        (context.quote_identifier_id, cutoff, cutoff),
    ).fetchall()
    ends = [v for v in (quote["valid_to"], *(c["valid_to"] for c in closures)) if v is not None]
    expected = {
        "security_id": quote["security_id"],
        "venue": quote["exchange_code"],
        "quote_currency": quote["quote_currency"],
        "instrument_kind": quote["instrument_kind"],
        "valid_from": quote["valid_from"],
        "valid_to": min(ends) if ends else None,
    }
    if any(getattr(context, key) != value for key, value in expected.items()):
        raise PublicationConflict(
            "Pinned quote interpretation differs from registered quote evidence"
        )
    return {"quote": quote, "closures": closures}


def _snapshot(db: Database, bundle: MarketNormalizationBundle) -> dict[str, Any]:
    inputs = bundle.inputs
    captures: list[dict[str, Any]] = []
    policies: dict[str, Any] = {}
    series = inputs.series_definition
    for capture in inputs.captures:
        row = db.execute("SELECT * FROM source_captures WHERE id=%s", (capture.id,)).fetchone()
        expected = asdict(capture)
        expected.pop("role")
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise PublicationConflict("Pinned capture differs from archived database evidence")
        if capture.source_id != inputs.source_id:
            raise PublicationConflict("Pinned capture belongs to another source")
        if (
            row["http_status"] is None
            or (capture.role != "fetch_outcome" and not 200 <= row["http_status"] < 300)
            or row["blob_key"] is None
            or row["completed_at"] is None
        ):
            raise PublicationConflict("Pinned capture is not complete successful evidence")
        if inputs.retrieval_cutoff is not None and row["completed_at"] > inputs.retrieval_cutoff:
            raise PublicationConflict("Pinned capture exceeds retrieval cutoff")
        link = db.execute(
            "SELECT * FROM capture_policy_links WHERE capture_id=%s", (capture.id,)
        ).fetchone()
        if link is None or (
            capture.role in {"observations", "fetch_outcome"}
            and link["policy_revision_id"] != inputs.policy_revision_id
        ):
            raise PublicationConflict("Pinned capture has a different source policy")
        policy = db.execute(
            "SELECT * FROM source_policy_revisions WHERE id=%s", (link["policy_revision_id"],)
        ).fetchone()
        capability = db.execute(
            "SELECT * FROM source_policy_capabilities WHERE policy_revision_id=%s",
            (link["policy_revision_id"],),
        ).fetchone()
        if policy is None or capability is None:
            raise PublicationConflict("Pinned capture lacks a retained-content policy")
        db.execute(
            "SELECT market_validate_policy(%s,%s,%s,%s,false,false)",
            (
                link["policy_revision_id"],
                capture.source_id,
                capture.source_object_key,
                series.source_series_key if series else None,
            ),
        )
        if capture.role in {"observations", "fetch_outcome"}:
            db.execute(
                "SELECT market_validate_policy(%s,%s,%s,%s,true,false)",
                (
                    link["policy_revision_id"],
                    capture.source_id,
                    capture.source_object_key,
                    series.source_series_key if series else None,
                ),
            )
        # Operational disable/activation never rewrites the grant for retained history.
        immutable_capability = {
            key: value
            for key, value in capability.items()
            if key
            not in {
                "activated_at",
                "activated_by",
                "activation_reason",
                "disabled_at",
                "disabled_by",
                "disable_reason",
            }
        }
        policies[str(link["policy_revision_id"])] = {
            "policy": policy,
            "capability": immutable_capability,
        }
        captures.append({"capture": row, "role": capture.role, "policy_link": link})
    attempts = []
    for identifier in inputs.attempt_ids:
        attempt = db.execute(
            "SELECT * FROM source_fetch_attempts WHERE id=%s", (identifier,)
        ).fetchone()
        if (
            attempt is None
            or attempt["source_id"] != inputs.source_id
            or attempt["policy_revision_id"] != inputs.policy_revision_id
            or attempt["finished_at"] is None
            or attempt["state"] in {"prepared", "in_progress"}
            or (
                inputs.retrieval_cutoff is not None
                and attempt["finished_at"] > inputs.retrieval_cutoff
            )
        ):
            raise PublicationConflict(
                "Pinned attempt is unresolved, wrong-source/policy or after cutoff"
            )
        original = db.execute(
            "SELECT r.* FROM analysis_requests r JOIN analysis_executions e ON e.request_id=r.id "
            "JOIN analysis_stage_attempts st ON st.execution_id=e.id WHERE st.id=%s",
            (attempt["stage_attempt_id"],),
        ).fetchone()
        if original is None:
            raise PublicationConflict("Pinned attempt lacks immutable W1 intent")
        binding = inputs.quote_binding
        resources: tuple[ProviderResource, ...]
        if binding is not None:
            resources = (
                PriceResource(
                    binding.quote_identifier_id,
                    binding.security_id,
                    binding.provider_symbol,
                    inputs.requested_start,
                    inputs.requested_end,
                ),
            )
        elif inputs.treasury_month is not None:
            resources = (TreasuryResource(inputs.treasury_month),)
        elif series is not None:
            wire_day = inputs.source_as_of_date or original["requested_at"].astimezone(UTC).date()
            resources = tuple(
                FredResource(
                    series.source_series_key,
                    inputs.requested_start,
                    inputs.requested_end,
                    wire_day,
                    offset=page * 100000,
                )
                for page in range(20)
            )
        else:
            raise PublicationConflict("Pinned attempt lacks reviewed market resource scope")
        if not any(
            attempt["source_object_key"] == resource.object_key
            and attempt["request_url"] == resource.url
            and attempt["request_params_hash"] == resource.params_hash
            for resource in resources
        ):
            raise PublicationConflict("Pinned attempt differs from the exact market request")
        capture_ids = {c.id for c in inputs.captures}
        if any(
            identifier is not None and identifier not in capture_ids
            for identifier in (attempt["completed_capture_id"], attempt["reused_capture_id"])
        ):
            raise PublicationConflict("Pinned attempt requires its complete capture evidence")
        db.execute(
            "SELECT market_validate_policy(%s,%s,%s,%s,true,false)",
            (
                inputs.policy_revision_id,
                inputs.source_id,
                attempt["source_object_key"],
                series.source_series_key if series else None,
            ),
        )
        attempts.append(attempt)
    if not captures and not attempts:
        raise PublicationConflict("Publication requires pinned capture or attempt evidence")
    if len(set(inputs.attempt_ids)) != len(inputs.attempt_ids):
        raise PublicationConflict("Repeated market attempt evidence")
    return {
        "captures": captures,
        "attempts": attempts,
        "policies": policies,
        "quote": _quote_snapshot(db, bundle),
    }


def _anchor(bundle: MarketNormalizationBundle, evidence: dict[str, Any]) -> datetime:
    times: list[datetime] = [c.completed_at for c in bundle.inputs.captures]
    times.extend(a["finished_at"] for a in evidence["attempts"])
    return max(times).astimezone(UTC)


def _archive_manifest(
    archive: LocalArchive, bundle: MarketNormalizationBundle, evidence: dict[str, Any]
) -> ArchivedBody:
    body = market_canonical_json(
        {
            "schema": "market-publication-v1",
            "normalization": bundle,
            "evidence": evidence,
        }
    ).encode()
    digest = hashlib.sha256(body).hexdigest()
    capture_id = evidence_id("market_manifest", digest)
    retrieved_at = _anchor(bundle, evidence)
    object_key = bundle.input_manifest_hash
    # The deterministic key also permits safe reuse of an orphan from a failed commit.
    stamp = retrieved_at.strftime("%Y%m%dT%H%M%S%f%z")
    object_hash = hashlib.sha256(object_key.encode()).hexdigest()
    expected = ArchivedBody(
        f"market-manifest/{object_hash}/{digest}/{stamp}-{capture_id}.gz", digest, len(body)
    )
    try:
        result = archive.write(
            [body],
            source_key="market-manifest",
            source_object_key=object_key,
            params_hash=digest,
            capture_id=capture_id,
            retrieved_at=retrieved_at,
            max_bytes=len(body),
        )
    except FileExistsError:
        archive.verify(expected)
        return expected
    if result != expected:
        raise PublicationConflict("Archive manifest identity differs from its deterministic key")
    return result


def _payload(
    bundle: MarketNormalizationBundle, manifest: ArchivedBody, raised_at: datetime
) -> dict[str, Any]:
    inputs = bundle.inputs
    definition, binding, context = (
        inputs.series_definition,
        inputs.quote_binding,
        inputs.quote_context,
    )
    if (definition is None) != (binding is not None and context is not None):
        raise PublicationConflict("Publication requires exactly one reviewed market identity")
    batch_id = evidence_id("market_batch", [inputs.source_id, bundle.input_manifest_hash])
    return {
        "batch": {
            "id": batch_id,
            "data_kind": "macro" if definition else "price",
            "source_id": inputs.source_id,
            "policy_revision_id": inputs.policy_revision_id,
            "quote_identifier_id": context.quote_identifier_id if context else None,
            "security_id": context.security_id if context else None,
            "quote_binding_id": binding.id if binding else None,
            "source_series_key": definition.source_series_key if definition else None,
            "series_definition_id": definition.id if definition else None,
            "requested_start": inputs.requested_start,
            "requested_end": inputs.requested_end,
            "source_vintage_mode": (
                "source_as_of_date" if inputs.source_as_of_date else "current_provider_history"
            ),
            "source_as_of_date": inputs.source_as_of_date,
            "retrieval_cutoff": inputs.retrieval_cutoff,
            "parser_revision": inputs.parser_revision,
            "normalizer_revision": inputs.normalizer_revision,
            "selection_policy_revision": inputs.selection_policy_revision,
            "input_manifest_hash": bundle.input_manifest_hash,
            "output_manifest_hash": bundle.output_manifest_hash,
            "manifest_blob_key": manifest.blob_key,
            "manifest_body_sha256": manifest.body_sha256,
            "manifest_byte_count": manifest.byte_count,
            "coverage_state": bundle.coverage_state,
        },
        "inputs": [
            {
                "id": evidence_id("market_input", [batch_id, capture.id, capture.role]),
                "capture_id": capture.id,
                "attempt_id": None,
                "role": capture.role,
            }
            for capture in inputs.captures
        ]
        + [
            {
                "id": evidence_id("market_attempt_input", [batch_id, identifier]),
                "capture_id": None,
                "attempt_id": identifier,
                "role": "fetch_outcome",
            }
            for identifier in inputs.attempt_ids
        ],
        "definitions": [asdict(definition)] if definition else [],
        "bindings": [asdict(binding)] if binding else [],
        "prices": [asdict(row) for row in bundle.prices],
        "macros": [asdict(row) for row in bundle.macros],
        "flags": [asdict(flag) | {"raised_at": raised_at} for flag in bundle.flags],
    }


def publish_market_bundle(
    db: Database,
    bundle: MarketNormalizationBundle,
    *,
    lease: Lease,
    stage_id: UUID,
    archive: LocalArchive,
) -> PublishedMarketBatch:
    """Verify evidence before the short SQL publication and stage-completion transaction.

    Attempt-bearing FRED publication uses the approved W1 page plan: 100,000
    rows per page, at most 20 pages. Arbitrary standalone normalization page
    layouts remain outside this worker publication entry point.
    """
    if db.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("Publication requires an idle connection")
    if (
        market_input_hash(bundle.inputs) != bundle.input_manifest_hash
        or market_output_hash(bundle) != bundle.output_manifest_hash
    ):
        raise PublicationConflict("Market normalization manifest hash mismatch")
    try:
        with db.transaction():
            db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            evidence = _snapshot(db, bundle)
    except CheckViolation as exc:
        raise PublicationConflict("Pinned capture policy does not permit publication") from exc
    for item in evidence["captures"]:
        capture = item["capture"]
        archive.read_blob(capture["blob_key"], capture["body_sha256"], capture["byte_count"])
    manifest = _archive_manifest(archive, bundle, evidence)
    batch_id, reused = publish(
        db, lease, stage_id, _payload(bundle, manifest, _anchor(bundle, evidence))
    )
    return PublishedMarketBatch(
        batch_id,
        reused,
        manifest,
        tuple(flag.id for flag in bundle.flags),
        tuple(c.id for c in bundle.inputs.captures),
    )
