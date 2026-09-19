"""Independent W1 market stages driven only by the immutable request plan."""

import calendar
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from math import ceil
from typing import Literal
from uuid import UUID, uuid4

from equity_schema.workflow import (
    Database,
    Lease,
    LeaseLost,
    finish_stage,
    renew_lease,
    retry_execution,
    start_stage,
)
from equity_schema.workflow import (
    finish_execution as complete_execution,
)
from psycopg.pq import TransactionStatus

from .archive import ArchiveError, LocalArchive
from .contracts import FetchResult, RawRecord
from .financial_types import EvidenceCapture
from .market_normalize import unavailable_market_bundle
from .market_publisher import PublishedMarketBatch, publish_market_bundle
from .market_sources import MarketSource
from .market_types import (
    MacroSeriesDefinition,
    MarketNormalizationInput,
    QuoteBinding,
    QuoteContext,
)
from .provider_contracts import (
    FredResource,
    PriceResource,
    ProviderFetchRequest,
    ProviderKind,
    ProviderResource,
    TreasuryResource,
)
from .publisher import PublicationConflict

MAX_MONTHS = 120
MAX_FRED_PAGES = 20


@dataclass(frozen=True)
class MarketReview:
    bindings: tuple[tuple[QuoteBinding, QuoteContext], ...] = ()
    definitions: tuple[MacroSeriesDefinition, ...] = ()
    evidence: tuple[RawRecord, ...] = ()


@dataclass(frozen=True)
class MarketPipelineResult:
    publications: tuple[PublishedMarketBatch, ...]
    gaps: tuple[str, ...]
    state: Literal["completed_with_gaps", "retry_scheduled", "deferred", "failed"]
    next_eligible_at: datetime | None = None


def _evidence(record: RawRecord, role: str) -> EvidenceCapture:
    return EvidenceCapture(
        record.capture_id,
        record.source_id,
        record.source_object_key,
        record.request_url,
        record.body_sha256,
        record.byte_count,
        record.fetched_at,
        record.completed_at,
        role,
    )


def _windows(start: date, end: date) -> tuple[tuple[str, date, date], ...]:
    count = (end.year - start.year) * 12 + end.month - start.month + 1
    if count > MAX_MONTHS:
        raise ValueError("Market monthly request exceeds execution budget")
    windows = []
    current = start.replace(day=1)
    for index in range(count):
        last = current.replace(day=calendar.monthrange(current.year, current.month)[1])
        windows.append(
            (f"{current.year:04d}{current.month:02d}", max(start, current), min(end, last))
        )
        if index + 1 < count:
            current = date(current.year + int(current.month == 12), current.month % 12 + 1, 1)
    return tuple(windows)


def _fetch_history(
    db: Database, results: tuple[FetchResult, ...]
) -> tuple[tuple[RawRecord, ...], tuple[UUID, ...]]:
    """Recover only original immutable fetch evidence, identically for live and replay.

    A capture pins its original logical fetch and sequence; later attempts cannot
    be pulled into an older run by replay. Complete unsuccessful bodies stay in
    the run manifest as fetch outcomes, never observation inputs.
    """
    captures = {r.capture_id: r for result in results for r in result.records}
    ids = tuple(a.attempt_id for result in results for a in result.attempts)
    attempts = db.execute(
        "WITH anchors AS (SELECT logical_fetch_id,max(sequence_no) AS last_sequence "
        "FROM source_fetch_attempts WHERE completed_capture_id=ANY(%s::uuid[]) "
        "GROUP BY logical_fetch_id) SELECT a.* FROM source_fetch_attempts a "
        "WHERE a.id=ANY(%s::uuid[]) OR EXISTS(SELECT FROM anchors x "
        "WHERE x.logical_fetch_id=a.logical_fetch_id AND a.sequence_no<=x.last_sequence) "
        "ORDER BY a.id",
        (list(captures), list(ids)),
    ).fetchall()
    for attempt in attempts:
        capture_id = attempt["completed_capture_id"]
        if capture_id is None or capture_id in captures:
            continue
        row = db.execute(
            "SELECT c.*,p.policy_revision_id FROM source_captures c "
            "JOIN capture_policy_links p ON p.capture_id=c.id WHERE c.id=%s",
            (capture_id,),
        ).fetchone()
        if row is None:
            raise ArchiveError("Pinned attempt capture is missing")
        headers = attempt["response_headers"] or {}
        captures[capture_id] = RawRecord(
            capture_id=capture_id,
            **{
                key: row[key]
                for key in RawRecord.__dataclass_fields__
                if key not in {"capture_id", "etag", "last_modified"}
            },
            etag=headers.get("etag"),
            last_modified=headers.get("last_modified"),
        )
    return tuple(captures[key] for key in sorted(captures)), tuple(a["id"] for a in attempts)


def run_market_stages(
    db: Database,
    lease: Lease,
    archive: LocalArchive,
    providers: Mapping[UUID, MarketSource],
    review: MarketReview,
    *,
    replay_records: tuple[RawRecord, ...] | None = None,
    finalize_execution: bool = True,
) -> MarketPipelineResult:
    if db.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("Market stages require an idle database connection")
    row = db.execute("SELECT * FROM analysis_requests WHERE id=%s", (lease.request_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown immutable request")
    cutoff = row["retrieval_vintage"]
    if cutoff is not None and replay_records is None:
        raise ValueError("Historical capture cutoff requires explicit replay")
    gaps: list[str] = []
    publications: list[PublishedMarketBatch] = []
    eligible: list[datetime] = []
    fetched: dict[tuple[UUID, str, str], FetchResult] = {}
    metadata = {r.capture_id: r for r in review.evidence}
    if len(metadata) != len(review.evidence):
        raise ValueError("Duplicate reviewed evidence")

    def blocked(stage_key: str, reason: str) -> None:
        nonlocal lease
        lease = renew_lease(db, lease, lease_seconds=360)
        stage = start_stage(db, lease, stage_key=stage_key)
        finish_stage(db, lease, stage_id=stage, outcome="blocked", reason=reason)
        gaps.append(reason)

    def fetch(source: MarketSource, resource: ProviderResource) -> RawRecord | None:
        nonlocal lease
        key = (source.descriptor.source_id, resource.object_key, resource.params_hash)
        if key in fetched:
            result = fetched[key]
        else:
            lease = renew_lease(db, lease, lease_seconds=360)
            stage = start_stage(
                db,
                lease,
                stage_key="market_fetch_" + hashlib.sha256(str(key).encode()).hexdigest()[:24],
            )
            pinned = tuple(
                r
                for r in (replay_records or ())
                if r.source_id == key[0]
                and r.source_object_key == key[1]
                and r.request_params_hash == key[2]
            )
            try:
                result = source.fetch(
                    ProviderFetchRequest(
                        uuid4(),
                        resource,
                        lease,
                        stage,
                        cache_mode="replay" if replay_records is not None else "refresh",
                        replay_records=pinned,
                        retrieval_cutoff=cutoff,
                    )
                )
            except ValueError:
                result = FetchResult(
                    gaps=("market_capture_request_mismatch",), completeness="incomplete"
                )
            fetched[key] = result
            if "lease_lost" in result.gaps:
                raise LeaseLost("lease lost during market retrieval")
            if result.next_eligible_at is not None:
                eligible.append(result.next_eligible_at)
            gaps.extend(result.gaps)
            usable = result.usable and len(result.successful_records) == 1
            reason = None if usable else "market_capture_unavailable_or_ambiguous"
            finish_stage(
                db,
                lease,
                stage_id=stage,
                outcome="completed" if usable else "blocked",
                reason=reason,
                reused_capture_ids=result.reused_capture_ids if usable else (),
            )
            if reason:
                gaps.append(reason)
        return (
            result.successful_records[0]
            if result.usable and len(result.successful_records) == 1
            else None
        )

    def normalize(
        source: MarketSource,
        stage_key: str,
        resources: tuple[ProviderResource, ...],
        start: date,
        end: date,
        *,
        definition: MacroSeriesDefinition | None = None,
        binding: QuoteBinding | None = None,
        context: QuoteContext | None = None,
    ) -> None:
        nonlocal lease
        evidence_id = (
            definition.metadata_capture_id
            if definition
            else binding.identity_capture_id
            if binding
            else None
        )
        reviewed = metadata.get(evidence_id) if evidence_id else None
        if reviewed is None:
            blocked(stage_key, "reviewed_market_evidence_required")
            return
        if reviewed.source_id != source.descriptor.source_id or (
            cutoff and reviewed.completed_at > cutoff
        ):
            blocked(stage_key, "market_metadata_outside_request_vintage")
            return
        records: list[RawRecord] = []
        selected = list(resources)
        failure: str | None = None
        for resource in resources:
            record = fetch(source, resource)
            if record is None:
                failure = "market_observations_unavailable"
                break
            records.append(record)
        if failure is None and isinstance(resources[0], FredResource):
            first = resources[0]
            for page_number in range(MAX_FRED_PAGES):
                try:
                    page = json.loads(source.read_verified(records[-1]))
                    count = page["count"]
                    if type(count) is not int or count < 0 or count > first.limit * MAX_FRED_PAGES:
                        raise ValueError("Invalid or excessive FRED count")
                except (ValueError, KeyError, TypeError, ArchiveError):
                    failure = "fred_pagination_unavailable"
                    break
                next_offset = (page_number + 1) * first.limit
                if next_offset >= count:
                    break
                next_resource = FredResource(
                    first.series_id,
                    first.start,
                    first.end,
                    first.source_as_of,
                    next_offset,
                    first.limit,
                )
                selected.append(next_resource)
                record = fetch(source, next_resource)
                if record is None:
                    failure = "fred_pagination_incomplete"
                    break
                records.append(record)
        results = tuple(
            fetched[(source.descriptor.source_id, r.object_key, r.params_hash)]
            for r in selected
            if (source.descriptor.source_id, r.object_key, r.params_hash) in fetched
        )
        captures, attempt_ids = _fetch_history(db, results)
        if not captures and not attempt_ids:
            blocked(stage_key, failure or "market_capture_unavailable")
            return
        observation_ids = {r.capture_id for r in records} if failure is None else set()
        inputs = MarketNormalizationInput(
            source.descriptor.source_id,
            source.descriptor.policy_revision_id,
            start,
            end,
            tuple(
                _evidence(r, "observations" if r.capture_id in observation_ids else "fetch_outcome")
                for r in captures
            )
            + (_evidence(reviewed, "series_definition" if definition else "quote_identity"),),
            "parser-v1",
            "normalizer-v1",
            "selection-v1",
            series_definition=definition,
            quote_binding=binding,
            quote_context=context,
            retrieval_cutoff=cutoff,
            source_as_of_date=row["macro_source_as_of_date"] if definition else None,
            treasury_month=resources[0].month
            if isinstance(resources[0], TreasuryResource)
            else None,
            attempt_ids=attempt_ids,
        )
        lease = renew_lease(db, lease, lease_seconds=360)
        stage = start_stage(db, lease, stage_key=stage_key)
        try:
            if failure:
                bundle = unavailable_market_bundle(inputs, failure)
            else:
                try:
                    bundle = source.normalize(
                        inputs, resources=tuple(selected), records=tuple(records)
                    )
                except (ValueError, ArchiveError) as exc:
                    failure = "market_normalization_" + type(exc).__name__.lower()
                    inputs = replace(
                        inputs,
                        captures=tuple(
                            replace(c, role="fetch_outcome") if c.role == "observations" else c
                            for c in inputs.captures
                        ),
                    )
                    bundle = unavailable_market_bundle(inputs, failure)
            publication = publish_market_bundle(
                db, bundle, lease=lease, stage_id=stage, archive=archive
            )
        except (ValueError, ArchiveError, PublicationConflict) as exc:
            reason = "market_publication_" + type(exc).__name__
            finish_stage(db, lease, stage_id=stage, outcome="blocked", reason=reason)
            gaps.append(reason)
            return
        publications.append(publication)
        if failure:
            gaps.append(failure)
        if bundle.coverage_state != "complete":
            gaps.append("market_coverage_" + bundle.coverage_state)
        gaps.extend(flag.rule_key for flag in bundle.flags)

    if row["market_plan_revision"] is None:
        lease = renew_lease(db, lease, lease_seconds=360)
        legacy_stage = start_stage(db, lease, stage_key="market_sources")
        finish_stage(
            db,
            lease,
            stage_id=legacy_stage,
            outcome="unsupported",
            reason="immutable_market_plan_missing",
        )
        gaps.append("immutable_market_plan_missing")
    if row["price_source_id"] is not None:
        source = providers.get(row["price_source_id"])
        matches = [
            (binding, context)
            for binding, context in review.bindings
            if binding.source_id == row["price_source_id"]
            and binding.quote_identifier_id == row["quote_identifier_id"]
            and binding.security_id == row["security_id"]
        ]
        if source is None or source.descriptor.provider != ProviderKind.TIINGO:
            blocked("price_normalization", "price_provider_unavailable")
        elif len(matches) != 1:
            blocked("price_normalization", "reviewed_price_binding_required")
        else:
            binding, context = matches[0]
            resource = PriceResource(
                binding.quote_identifier_id,
                binding.security_id,
                binding.provider_symbol,
                row["price_start"],
                row["price_end"],
            )
            normalize(
                source,
                "price_normalization",
                (resource,),
                resource.start,
                resource.end,
                binding=binding,
                context=context,
            )
    if row["macro_source_id"] is not None:
        source = providers.get(row["macro_source_id"])
        for series in row["macro_series_keys"]:
            key = "macro_normalization_" + hashlib.sha256(series.encode()).hexdigest()[:16]
            matches_def = [
                d
                for d in review.definitions
                if d.source_id == row["macro_source_id"] and d.source_series_key == series
            ]
            if source is None or source.descriptor.provider not in {
                ProviderKind.TREASURY,
                ProviderKind.FRED,
            }:
                blocked(key, "macro_provider_unavailable")
                continue
            if len(matches_def) != 1:
                blocked(key, "reviewed_macro_definition_required")
                continue
            definition = matches_def[0]
            if source.descriptor.provider == ProviderKind.TREASURY:
                if row["macro_source_as_of_date"] is not None:
                    blocked(key, "treasury_source_vintage_unsupported")
                    continue
                try:
                    windows = _windows(row["macro_start"], row["macro_end"])
                except ValueError:
                    blocked(key, "market_window_exceeds_budget")
                    continue
                for month, start, end in windows:
                    key = (
                        "macro_normalization_"
                        + hashlib.sha256(f"{series}:{start}:{end}".encode()).hexdigest()[:16]
                    )
                    normalize(
                        source, key, (TreasuryResource(month),), start, end, definition=definition
                    )
            else:
                as_of = row["macro_source_as_of_date"] or row["requested_at"].astimezone(UTC).date()
                resource_fred = FredResource(series, row["macro_start"], row["macro_end"], as_of)
                normalize(
                    source,
                    key,
                    (resource_fred,),
                    resource_fred.start,
                    resource_fred.end,
                    definition=definition,
                )
    state: Literal["completed_with_gaps", "retry_scheduled", "deferred", "failed"] = (
        "completed_with_gaps"
    )
    next_at = max(eligible) if eligible else None
    if eligible:
        state = "deferred"
        if finalize_execution:
            delay = min(86400, max(1, ceil((max(eligible) - datetime.now(UTC)).total_seconds())))
            retry_execution(db, lease, error_code="market_source_deferred", delay_seconds=delay)
            terminal = db.execute(
                "SELECT terminal_outcome FROM analysis_request_state WHERE request_id=%s",
                (lease.request_id,),
            ).fetchone()
            state = (
                "failed"
                if terminal and terminal["terminal_outcome"] == "failed"
                else "retry_scheduled"
            )
    elif finalize_execution:
        complete_execution(
            db, lease, outcome="completed_with_gaps", reason="valuation_milestones_pending"
        )
    return MarketPipelineResult(tuple(publications), tuple(dict.fromkeys(gaps)), state, next_at)
