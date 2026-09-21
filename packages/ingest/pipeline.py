"""Run approved SEC source stages for one claimed, resolved watchlist request.

A reviewed plan supplies scope/mapping judgments. This worker never guesses them
from an issuer name and never reports the later valuation stages as complete.
"""

import hashlib
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from math import ceil
from typing import Literal, Protocol
from uuid import UUID, uuid4

from equity_schema.workflow import (
    Database,
    Lease,
    LeaseLost,
    RequestedPeriod,
    finish_execution,
    finish_stage,
    renew_lease,
    retry_execution,
    start_stage,
)
from psycopg.pq import TransactionStatus

from .archive import ArchivedBody, ArchiveError, LocalArchive
from .contracts import FetchRequest, FetchResult, RawRecord, ResourceKind, SecResource, Source
from .financial_types import Completeness, NormalizationInput, canonical_json
from .publisher import NORMALIZATION_STAGE, PublishedBatch, publish_bundle
from .sec_inventory import FilingInventory, assemble_inventory, parse_submissions


class ReadableSource(Source, Protocol):
    def read_verified(self, capture_id: UUID) -> bytes: ...


@dataclass(frozen=True)
class SourcePlan:
    issuer_id: UUID
    cik: str
    inventory_start: date
    inventory_end: date
    filing_documents: tuple[SecResource, ...] = ()
    max_history_documents: int = 20

    def __post_init__(self) -> None:
        root = SecResource(self.issuer_id, self.cik, ResourceKind.SUBMISSIONS)
        object.__setattr__(self, "cik", root.cik)
        if self.inventory_start > self.inventory_end or not 0 <= self.max_history_documents <= 100:
            raise ValueError("An ordered inventory window and bounded history budget are required")
        if len(self.filing_documents) > 100 or len(set(self.filing_documents)) != len(
            self.filing_documents
        ):
            raise ValueError("Filing document plan must be unique and bounded")
        if any(
            r.kind != ResourceKind.FILING_DOCUMENT
            or r.issuer_id != self.issuer_id
            or r.cik != self.cik
            for r in self.filing_documents
        ):
            raise ValueError("Filing document plan must belong to the resolved issuer")


@dataclass(frozen=True)
class SourceContext:
    companyfacts: RawRecord
    records: tuple[RawRecord, ...]
    results: tuple[FetchResult, ...]
    inventory: FilingInventory | None
    gaps: tuple[str, ...]
    requested_periods: tuple[RequestedPeriod, ...]
    retrieval_cutoff: datetime | None
    history_mode: str
    filed_cutoff: date | None


@dataclass(frozen=True)
class PipelineResult:
    state: Literal[
        "completed",
        "completed_with_gaps",
        "retry_scheduled",
        "waiting_for_input",
        "failed",
        "deferred",
    ]
    publication: PublishedBatch | None = None
    manifest: ArchivedBody | None = None
    inventory: FilingInventory | None = None
    gaps: tuple[str, ...] = ()
    next_eligible_at: datetime | None = None


InputBuilder = Callable[[SourceContext], NormalizationInput | None]


def run_source_stages(
    db: Database,
    lease: Lease,
    source: ReadableSource,
    archive: LocalArchive,
    plan: SourcePlan,
    build_inputs: InputBuilder,
    *,
    replay_records: tuple[RawRecord, ...] | None = None,
    finalize_execution: bool = True,
) -> PipelineResult:
    return _run_source_stages(
        db,
        lease,
        source,
        archive,
        plan,
        build_inputs,
        replay_records=replay_records,
        finalize_execution=finalize_execution,
        bootstrap=False,
    )


def run_source_bootstrap(
    db: Database,
    lease: Lease,
    source: ReadableSource,
    archive: LocalArchive,
    plan: SourcePlan,
    *,
    replay_records: tuple[RawRecord, ...] | None = None,
) -> PipelineResult:
    """Capture issuer evidence without normalization, quotes, membership or valuation."""
    return _run_source_stages(
        db,
        lease,
        source,
        archive,
        plan,
        None,
        replay_records=replay_records,
        finalize_execution=True,
        bootstrap=True,
    )


def _run_source_stages(
    db: Database,
    lease: Lease,
    source: ReadableSource,
    archive: LocalArchive,
    plan: SourcePlan,
    build_inputs: InputBuilder | None,
    *,
    replay_records: tuple[RawRecord, ...] | None = None,
    finalize_execution: bool = True,
    bootstrap: bool,
) -> PipelineResult:
    """Fetch -> inventory -> reviewed normalization -> immutable publication.

    ``None`` replay_records means fresh HTTP. A tuple means explicit archive-only
    replay (including an empty, therefore unavailable, archive). Every request's
    retrieval vintage is enforced; a historical request cannot silently go live.
    The supplied archive stores complete, hash-addressed run manifests as well as
    source bodies. Terminal stage audit records retain the manifest reference.
    """
    if db.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("Source stages require an idle database connection")
    row = db.execute(
        "SELECT r.*,s.issuer_id,i.cik FROM analysis_requests r "
        "JOIN securities s ON s.id=r.security_id JOIN issuers i ON i.id=s.issuer_id "
        "WHERE r.id=%s",
        (lease.request_id,),
    ).fetchone()
    if row is None or row["issuer_id"] != plan.issuer_id or row["cik"] != plan.cik:
        raise ValueError("Source plan does not match the claimed request's issuer")
    if (row["trigger"] == "source_bootstrap") != bootstrap:
        raise ValueError("Source worker does not match request trigger")
    lease = renew_lease(db, lease, lease_seconds=360)
    cutoff = row["retrieval_vintage"]
    if cutoff is not None and replay_records is None:
        raise ValueError("Historical retrieval vintage requires explicit archived replay")
    periods = tuple(
        RequestedPeriod(
            kind=p["kind"],
            end=date.fromisoformat(p["end"]),
            start=date.fromisoformat(p["start"]) if p["start"] else None,
        )
        for p in row["requested_periods"]
    )
    results: list[FetchResult] = []
    records: dict[UUID, RawRecord] = {}
    gaps: list[str] = []
    inventory: FilingInventory | None = None
    current_stage: UUID | None = None

    def fetch(resource: SecResource) -> RawRecord | None:
        nonlocal lease, current_stage
        lease = renew_lease(db, lease, lease_seconds=360)
        current_stage = start_stage(
            db,
            lease,
            stage_key="sec_fetch_" + hashlib.sha256(resource.object_key.encode()).hexdigest()[:24],
        )
        pinned = tuple(
            r for r in (replay_records or ()) if r.source_object_key == resource.object_key
        )
        result = source.fetch(
            FetchRequest(
                uuid4(),
                resource,
                lease,
                current_stage,
                cache_mode="replay" if replay_records is not None else "refresh",
                replay_records=pinned,
                requested_periods=periods,
                retrieval_cutoff=cutoff,
            )
        )
        results.append(result)
        records.update((r.capture_id, r) for r in result.records)
        gaps.extend(result.gaps)
        successes = result.successful_records
        usable = result.usable and len(successes) == 1
        if not usable and not result.gaps:
            gaps.append("capture_vintage_choice_required" if successes else "capture_unavailable")
        finish_stage(
            db,
            lease,
            stage_id=current_stage,
            outcome="completed" if usable else "blocked",
            reason=None if usable else canonical_json({"gaps": gaps}),
            reused_capture_ids=result.reused_capture_ids if usable else (),
        )
        current_stage = None
        return successes[0] if usable else None

    try:
        companyfacts = fetch(SecResource(plan.issuer_id, plan.cik, ResourceKind.COMPANY_FACTS))
        recent_record = fetch(SecResource(plan.issuer_id, plan.cik, ResourceKind.SUBMISSIONS))
        if recent_record is not None:
            current_stage = start_stage(db, lease, stage_key="sec_inventory_parse")
            recent = parse_submissions(
                source.read_verified(recent_record.capture_id),
                expected_cik=plan.cik,
                capture_id=recent_record.capture_id,
            )
            finish_stage(db, lease, stage_id=current_stage, outcome="completed")
            current_stage = None
            older = []
            needed = sorted(
                (
                    d
                    for d in recent.older_documents
                    if d.filing_from <= plan.inventory_end and d.filing_to >= plan.inventory_start
                ),
                key=lambda d: d.name,
            )
            for document in needed[: plan.max_history_documents]:
                record = fetch(
                    SecResource(
                        plan.issuer_id,
                        plan.cik,
                        ResourceKind.SUBMISSIONS_HISTORY,
                        filename=document.name,
                    )
                )
                if record is not None:
                    current_stage = start_stage(
                        db,
                        lease,
                        stage_key="sec_parse_"
                        + hashlib.sha256(document.name.encode()).hexdigest()[:24],
                    )
                    older.append(
                        parse_submissions(
                            source.read_verified(record.capture_id),
                            expected_cik=plan.cik,
                            capture_id=record.capture_id,
                            document_name=document.name,
                        )
                    )
                    finish_stage(db, lease, stage_id=current_stage, outcome="completed")
                    current_stage = None
            current_stage = start_stage(db, lease, stage_key="sec_inventory")
            inventory = assemble_inventory(
                recent,
                tuple(older),
                boundary_start=plan.inventory_start,
                boundary_end=plan.inventory_end,
            )
            gaps.extend(inventory.flags)
            finish_stage(
                db,
                lease,
                stage_id=current_stage,
                outcome="completed" if inventory.completeness == "complete" else "blocked",
                reason=canonical_json(
                    {"flags": inventory.flags, "missing": inventory.missing_documents}
                ),
            )
            current_stage = None
        else:
            gaps.append("filing_inventory_unavailable")
        for resource in plan.filing_documents:
            fetch(resource)
        if bootstrap and companyfacts is None:
            gaps.append("companyfacts_unavailable")
        bootstrap_manifest = None
        if bootstrap:
            lease = renew_lease(db, lease, lease_seconds=360)
            current_stage = start_stage(db, lease, stage_key="sec_bootstrap_manifest")
            payload = canonical_json(
                {
                    "format": "sec-bootstrap-run-v1",
                    "financial_result": False,
                    "request": {
                        k: row[k]
                        for k in (
                            "id",
                            "trigger",
                            "workspace_id",
                            "security_id",
                            "quote_identifier_id",
                            "history_mode",
                            "filed_cutoff",
                            "requested_periods",
                            "retrieval_vintage",
                        )
                    },
                    "execution_id": lease.execution_id,
                    "plan": asdict(plan),
                    "fetch_results": [asdict(r) for r in results],
                    "inventory": asdict(inventory) if inventory else None,
                    "source_gaps": gaps,
                    "event_review": "not_performed",
                }
            ).encode()
            bootstrap_manifest = archive.write(
                (payload,),
                source_key="bootstrap",
                source_object_key=str(lease.execution_id),
                params_hash=hashlib.sha256(payload).hexdigest(),
                capture_id=uuid4(),
                retrieved_at=datetime.now(UTC),
                max_bytes=64 * 1024 * 1024,
            )
            finish_stage(
                db,
                lease,
                stage_id=current_stage,
                outcome="completed",
                reason=canonical_json(
                    {"manifest": asdict(bootstrap_manifest), "financial_result": False}
                ),
            )
            current_stage = None
        deferred = [r.next_eligible_at for r in results if r.next_eligible_at is not None]
        retryable = {"coordination_unavailable", "dispatch_budget_exhausted", "transport_error"}
        if deferred or retryable.intersection(gaps):
            # W1 has a bounded 24h delay. A longer SEC cooldown is retained by Redis;
            # an earlier worker wakeup still cannot dispatch before that cooldown.
            delay = min(
                86400,
                max(
                    1, ceil((max(deferred) - datetime.now(UTC)).total_seconds()) if deferred else 30
                ),
            )
            if not finalize_execution:
                return PipelineResult(
                    "deferred",
                    inventory=inventory,
                    gaps=tuple(gaps),
                    next_eligible_at=max(deferred) if deferred else None,
                )
            retry_execution(db, lease, error_code="sec_source_deferred", delay_seconds=delay)
            state = db.execute(
                "SELECT terminal_outcome FROM analysis_request_state WHERE request_id=%s",
                (lease.request_id,),
            ).fetchone()
            if state is not None and state["terminal_outcome"] == "failed":
                return PipelineResult(
                    "failed",
                    manifest=bootstrap_manifest,
                    inventory=inventory,
                    gaps=(*gaps, "retry_budget_exhausted"),
                )
            return PipelineResult(
                "retry_scheduled",
                manifest=bootstrap_manifest,
                inventory=inventory,
                gaps=tuple(gaps),
            )
        if bootstrap:
            outcome: Literal["completed", "completed_with_gaps"] = (
                "completed_with_gaps" if gaps else "completed"
            )
            finish_execution(db, lease, outcome=outcome, reason="source_bootstrap_capture_only")
            return PipelineResult(
                outcome, manifest=bootstrap_manifest, inventory=inventory, gaps=tuple(gaps)
            )
        assert build_inputs is not None
        current_stage = start_stage(db, lease, stage_key=NORMALIZATION_STAGE)
        context = (
            None
            if companyfacts is None
            else SourceContext(
                companyfacts,
                tuple(records.values()),
                tuple(results),
                inventory,
                tuple(gaps),
                periods,
                cutoff,
                row["history_mode"],
                row["filed_cutoff"],
            )
        )
        inputs = None if context is None else build_inputs(context)
        if inputs is None:
            reason = "reviewed_mapping_required" if companyfacts else "companyfacts_unavailable"
            finish_stage(db, lease, stage_id=current_stage, outcome="blocked", reason=reason)
            current_stage = None
            if finalize_execution:
                finish_execution(db, lease, outcome="waiting_for_input", reason=reason)
            return PipelineResult("waiting_for_input", inventory=inventory, gaps=(*gaps, reason))
        assert context is not None
        inputs = _pin_context(inputs, context, plan)
        bundle = source.normalize(inputs)
        # Archive all inputs, event/flag IDs and derived evidence before publication.
        payload = canonical_json(
            {
                "format": "sec-source-run-v1",
                "bundle": asdict(bundle),
                "inventory": asdict(inventory) if inventory else None,
                "fetch_results": [asdict(r) for r in results],
                "source_gaps": gaps,
                "request": {
                    k: row[k]
                    for k in (
                        "id",
                        "security_id",
                        "quote_identifier_id",
                        "history_mode",
                        "filed_cutoff",
                        "requested_periods",
                        "retrieval_vintage",
                    )
                },
            }
        ).encode()
        manifest = archive.write(
            (payload,),
            source_key="normalization",
            source_object_key=bundle.input_manifest_hash,
            params_hash=bundle.input_manifest_hash,
            capture_id=uuid4(),
            retrieved_at=datetime.now(UTC),
            max_bytes=64 * 1024 * 1024,
        )
        publication = publish_bundle(
            db,
            bundle,
            lease=lease,
            stage_id=current_stage,
            stage_manifest=manifest,
        )
        current_stage = None
        if finalize_execution:
            later = start_stage(db, lease, stage_key="valuation")
            finish_stage(
                db,
                lease,
                stage_id=later,
                outcome="unsupported",
                reason="valuation_milestones_pending",
            )
            finish_execution(
                db, lease, outcome="completed_with_gaps", reason="valuation_milestones_pending"
            )
        return PipelineResult("completed_with_gaps", publication, manifest, inventory, tuple(gaps))
    except LeaseLost:
        raise
    except (ValueError, ArchiveError) as exc:
        if current_stage is not None:
            finish_stage(
                db, lease, stage_id=current_stage, outcome="failed", reason=type(exc).__name__
            )
        if finalize_execution:
            finish_execution(db, lease, outcome="failed", reason=type(exc).__name__)
        raise


def _pin_context(
    inputs: NormalizationInput, context: SourceContext, plan: SourcePlan
) -> NormalizationInput:
    if (
        inputs.issuer_id != plan.issuer_id
        or inputs.cik != plan.cik
        or inputs.companyfacts_capture_id != context.companyfacts.capture_id
    ):
        raise ValueError("Reviewed normalization inputs differ from the fetched issuer/vintage")
    if context.retrieval_cutoff is not None and inputs.captured_before > context.retrieval_cutoff:
        raise ValueError("Normalization exceeds requested retrieval vintage")
    if context.filed_cutoff is not None and any(
        f.filed_date > context.filed_cutoff for f in inputs.filings
    ):
        raise ValueError("Reviewed filings exceed the requested filed cutoff")
    actual = {
        (r.period.period_kind, r.period.start_date, r.period.end_date) for r in inputs.requests
    }
    if any((p.kind, p.start, p.end) not in actual for p in context.requested_periods):
        raise ValueError("Reviewed normalization does not cover the requested periods")
    available = {r.capture_id for r in context.records if r.successful}
    pinned = {c.id for c in inputs.captures}
    if not available.issubset(pinned):
        raise ValueError("Normalization must pin every successful source-stage capture")
    inventory = context.inventory
    observed = Completeness(
        "unknown"
        if inventory is None
        else "complete"
        if inventory.completeness == "complete"
        else "incomplete",
        plan.inventory_start,
        plan.inventory_end,
        ("source-stage inventory unavailable",)
        if inventory is None
        else (inventory.completeness_basis, *(str(c) for c in inventory.capture_ids)),
    )
    # Only downgrade the independent review; API inventory completeness alone
    # cannot establish complete original-filing or public-event history.
    reviewed = inputs.inventory_completeness
    if (
        bool(context.gaps)
        or observed.state != "complete"
        or reviewed.boundary_start < observed.boundary_start
        or reviewed.boundary_end > observed.boundary_end
    ):
        reviewed = replace(
            reviewed,
            state="incomplete",
            evidence_references=reviewed.evidence_references + observed.evidence_references,
        )
    return replace(
        inputs,
        inventory_completeness=reviewed,
        attempt_ids=tuple(
            dict.fromkeys(
                (*inputs.attempt_ids, *(a.attempt_id for r in context.results for a in r.attempts))
            )
        ),
    )
