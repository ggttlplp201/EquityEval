"""Compose SEC and market source stages on one fenced watchlist execution."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from equity_schema.workflow import (
    Database,
    Lease,
    finish_execution,
    finish_stage,
    renew_lease,
    retry_execution,
    start_stage,
)

from .archive import ArchiveError, LocalArchive
from .contracts import RawRecord
from .market_pipeline import MarketPipelineResult, MarketReview, run_market_stages
from .market_sources import MarketSource
from .pipeline import InputBuilder, PipelineResult, ReadableSource, SourcePlan, run_source_stages


@dataclass(frozen=True)
class AnalysisSourcesResult:
    sec: PipelineResult
    market: MarketPipelineResult
    state: str
    gaps: tuple[str, ...]


def run_analysis_stages(
    db: Database,
    lease: Lease,
    sec_source: ReadableSource,
    archive: LocalArchive,
    sec_plan: SourcePlan,
    build_inputs: InputBuilder,
    market_sources: Mapping[UUID, MarketSource],
    market_review: MarketReview,
    *,
    sec_replay_records: tuple[RawRecord, ...] | None = None,
    market_replay_records: tuple[RawRecord, ...] | None = None,
) -> AnalysisSourcesResult:
    """Unavailable sources keep their own gaps; completed sibling evidence survives."""
    try:
        sec = run_source_stages(
            db,
            lease,
            sec_source,
            archive,
            sec_plan,
            build_inputs,
            replay_records=sec_replay_records,
            finalize_execution=False,
        )
    except (ValueError, ArchiveError) as exc:
        sec = PipelineResult("failed", gaps=("sec_source_" + type(exc).__name__,))
        stage = start_stage(db, lease, stage_key="sec_sources")
        finish_stage(db, lease, stage_id=stage, outcome="blocked", reason=sec.gaps[0])
    lease = renew_lease(db, lease, lease_seconds=360)
    market = run_market_stages(
        db,
        lease,
        archive,
        market_sources,
        market_review,
        replay_records=market_replay_records,
        finalize_execution=False,
    )
    gaps = tuple(dict.fromkeys((*sec.gaps, *market.gaps, "valuation_milestones_pending")))
    lease = renew_lease(db, lease, lease_seconds=360)
    if sec.state == "deferred" or market.state == "deferred":
        deferred = [v for v in (sec.next_eligible_at, market.next_eligible_at) if v is not None]
        delay = min(
            86400,
            max(1, ceil((max(deferred) - datetime.now(UTC)).total_seconds()) if deferred else 30),
        )
        retry_execution(db, lease, error_code="analysis_source_deferred", delay_seconds=delay)
        row = db.execute(
            "SELECT terminal_outcome FROM analysis_request_state WHERE request_id=%s",
            (lease.request_id,),
        ).fetchone()
        state = "failed" if row and row["terminal_outcome"] == "failed" else "retry_scheduled"
    else:
        stage = start_stage(db, lease, stage_key="valuation")
        finish_stage(
            db, lease, stage_id=stage, outcome="unsupported", reason="valuation_milestones_pending"
        )
        if sec.state == "waiting_for_input":
            finish_execution(
                db, lease, outcome="waiting_for_input", reason="reviewed_mapping_required"
            )
            state = "waiting_for_input"
        else:
            finish_execution(
                db, lease, outcome="completed_with_gaps", reason="valuation_milestones_pending"
            )
            state = "completed_with_gaps"
    return AnalysisSourcesResult(sec, market, state, gaps)
