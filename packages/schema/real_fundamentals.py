"""D048 real source-only v2 contracts; synthetic v1 remains unchanged."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from equity_core.assessment import EvaluationContext
from equity_core.history import HistoryPolicy
from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_core.trends import TrendPolicy
from equity_ingest.financial_types import PeriodSpec, ScopeSpec, UnitSpec
from equity_schema.fundamentals import (
    CaptureInput,
    HistorySampleRef,
    MetricSpec,
    PublicAccounting,
    PublicCoverage,
    PublicEvidence,
    PublicHistory,
    PublicMetric,
    PublicObservation,
    PublicTrend,
)
from equity_schema.fundamentals_canonical import canonical_json, content_hash, parse_canonical
from equity_schema.pit import StatementSelection
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Sha256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
DecimalString = Annotated[
    str, StringConstraints(pattern=r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
]
Nonempty = Annotated[str, StringConstraints(min_length=1, max_length=250)]
Status = Literal[
    "valid", "not_meaningful", "missing", "invalid", "stale", "unsupported", "inapplicable"
]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RealSelectionKey(FrozenModel):
    issuer_id: UUID
    security_id: UUID
    selection_kind: Literal["issuer_fundamentals"]
    period_basis: Literal["annual", "quarter", "ttm", "instant"]
    period_start: date | None
    period_end: date
    reporting_basis: Literal["us_gaap", "ifrs"]
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    history_mode: Literal["as_filed_by_date", "original_as_filed", "latest_reported"]
    filed_cutoff: date | None
    captured_before: datetime
    as_of: date
    evaluated_at: datetime
    profile_revision: Nonempty
    freshness_revision: Nonempty
    history_revision: Nonempty
    trend_revision: Nonempty
    policy_content_hash: Sha256
    history_years: Literal[3, 5, 10]
    engine_revision: Nonempty

    @model_validator(mode="after")
    def validate_context(self) -> Self:
        if self.captured_before.utcoffset() is None or self.evaluated_at.utcoffset() is None:
            raise ValueError("Explicit timezone required")
        if self.captured_before > self.evaluated_at:
            raise ValueError("Capture cutoff exceeds frozen evaluation")
        if self.evaluated_at.astimezone(UTC).date() != self.as_of or self.period_end > self.as_of:
            raise ValueError("Frozen evaluation and financial dates are inconsistent")
        if (self.period_basis == "instant") != (self.period_start is None):
            raise ValueError("Period basis and duration must agree")
        if self.period_start is not None and self.period_start > self.period_end:
            raise ValueError("Invalid financial window")
        if self.history_mode == "as_filed_by_date" and self.filed_cutoff is None:
            raise ValueError("Filed cutoff required")
        if self.history_mode == "latest_reported" and self.filed_cutoff is not None:
            raise ValueError("Latest-reported cannot carry a filed cutoff")
        if self.filed_cutoff is not None and self.filed_cutoff > self.as_of:
            raise ValueError("Filed cutoff exceeds evaluation date")
        return self


class RetainedPolicyEvidence(FrozenModel):
    capture_id: UUID
    body_sha256: Sha256
    locator: Nonempty
    purpose: Nonempty


class RetainedPrecisionEvidence(FrozenModel):
    input_index: Annotated[int, Field(strict=True, ge=0)]
    capture_id: UUID
    body_sha256: Sha256
    source_url: str
    fetched_at: datetime
    accession: str
    qualified_tag: Nonempty
    context_id: Nonempty
    unit_id: Nonempty
    locator: str
    decimals: str
    scale: int
    sign: Literal["-"] | None


class RealInputManifest(FrozenModel):
    version: Literal["s6-input-v2"]
    evidence_mode: Literal["real"]
    selector: RealSelectionKey
    policy_evidence: tuple[RetainedPolicyEvidence, ...]
    precision_evidence: tuple[RetainedPrecisionEvidence, ...]
    context: EvaluationContext
    history_policy: HistoryPolicy
    trend_policy: TrendPolicy
    captures: tuple[CaptureInput, ...]
    sources: tuple[FinancialInput, ...]
    metrics: tuple[MetricSpec, ...]
    trend_inputs: tuple[MetricSpec, ...]
    history_samples: tuple[HistorySampleRef, ...]
    accounting_source_indices: tuple[Annotated[int, Field(strict=True, ge=0)], ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        selector = self.selector
        captures = {c.capture_id: c for c in self.captures}
        evidence: tuple[RetainedPolicyEvidence | RetainedPrecisionEvidence, ...] = (
            *self.policy_evidence,
            *self.precision_evidence,
        )
        if not self.policy_evidence or any(
            e.capture_id not in captures or captures[e.capture_id].body_sha256 != e.body_sha256
            for e in evidence
        ):
            raise ValueError("Real policy/precision evidence must resolve to retained captures")
        if len({e.input_index for e in self.precision_evidence}) != len(
            self.precision_evidence
        ) or any(e.input_index >= len(self.sources) for e in self.precision_evidence):
            raise ValueError("Precision evidence has duplicate or unknown source indices")
        if (
            self.context.as_of != selector.as_of
            or self.context.profile.issuer_id != selector.issuer_id
            or self.context.profile.revision != selector.profile_revision
            or self.context.freshness.revision != selector.freshness_revision
            or self.history_policy.revision != selector.history_revision
            or self.trend_policy.revision != selector.trend_revision
            or self.history_policy.years != selector.history_years
        ):
            raise ValueError("Selector and explicit policies disagree")
        if (
            content_hash((self.context, self.history_policy, self.trend_policy))
            != selector.policy_content_hash
        ):
            raise ValueError("Policy contents do not match selector")
        ids = tuple(metric.metric_id for metric in self.metrics)
        if len(set(ids)) != len(ids) or set(ids) != {
            rule.metric_id for rule in self.context.profile.rules
        }:
            raise ValueError("Metric requests must exactly cover the applicability roster")
        used = set(self.accounting_source_indices)
        for metric in (*self.metrics, *self.trend_inputs):
            for operand in metric.operands:
                used.update(operand.source_indices)
        if used != set(range(len(self.sources))) or len(self.accounting_source_indices) not in {
            0,
            3,
        }:
            raise ValueError(
                "Source references must be exact and accounting inputs have arity three"
            )
        if len({item.snapshot_id for item in self.history_samples}) != len(self.history_samples):
            raise ValueError("Duplicate historical snapshot reference")
        if (
            len({c.capture_id for c in self.captures}) != len(self.captures)
            or {c.capture_id for c in self.captures}
            != {i for s in self.sources for i in s.selection.query.capture_ids}
            or any(
                c.fetched_at.utcoffset() is None or c.fetched_at > selector.captured_before
                for c in self.captures
            )
        ):
            raise ValueError("Capture metadata must cover exact pinned source evidence")
        for source in self.sources:
            q = source.selection.query
            if (
                q.issuer_id != selector.issuer_id
                or q.security_id not in {None, selector.security_id}
                or q.captured_before != selector.captured_before
                or q.filed_cutoff != selector.filed_cutoff
                or q.mode != selector.history_mode
                or source.selection.reporting_basis not in {None, selector.reporting_basis}
                or (
                    source.unit.numerator_measures == ("iso4217:" + source.unit.unit_key,)
                    and source.unit.unit_key != selector.currency
                )
            ):
                raise ValueError("Source selection differs from the pinned selector")
        return self


# FinancialInput intentionally imports transfer objects only for static typing.
# Supply those exact existing classes for strict nested Pydantic reconstruction.
RealInputManifest.model_rebuild(
    _types_namespace={
        "StatementSelection": StatementSelection,
        "PeriodSpec": PeriodSpec,
        "ScopeSpec": ScopeSpec,
        "UnitSpec": UnitSpec,
        "PrecisionEvidence": PrecisionEvidence,
    }
)


def read_manifest(text: str) -> RealInputManifest:
    parse_canonical(text)
    manifest = RealInputManifest.model_validate_json(text)
    if canonical_json(manifest) != text:
        raise ValueError("Input fields or representations changed during typed reconstruction")
    return manifest


class RealFundamentalsPayload(FrozenModel):
    version: Literal["s6-fundamentals-v2"]
    evidence_mode: Literal["real"]
    selector: RealSelectionKey
    precision_evidence: tuple[RetainedPrecisionEvidence, ...]
    policy_evidence: tuple[RetainedPolicyEvidence, ...]
    dependency_hash: Sha256
    comparison_policy_hash: Sha256
    metrics: tuple[PublicMetric, ...]
    evidence: tuple[PublicEvidence, ...]
    coverage: PublicCoverage
    observations: tuple[PublicObservation, ...]
    review_items: tuple[PublicObservation, ...]
    history: tuple[PublicHistory, ...]
    trend: PublicTrend
    accounting: PublicAccounting | None


class RealSnapshotResponse(FrozenModel):
    snapshot_id: UUID
    request_id: UUID
    execution_id: UUID
    input_snapshot_id: UUID
    generated_at: datetime
    compatibility_key: Sha256
    payload_hash: Sha256
    outcome: Literal["completed", "completed_with_gaps"]
    result: RealFundamentalsPayload


class RealNoResult(FrozenModel):
    code: Literal["snapshot_not_found", "no_compatible_snapshot"]
    message: Literal["N/A"]


class RealLatestResponse(FrozenModel):
    snapshot: RealSnapshotResponse
    latest_request_id: UUID
    latest_request_state: Literal[
        "queued",
        "running",
        "waiting_for_input",
        "retry_scheduled",
        "completed",
        "completed_with_gaps",
        "failed",
        "cancelled",
    ]


class RealLatestSelection(FrozenModel):
    security_id: UUID
    compatibility_key: Sha256
