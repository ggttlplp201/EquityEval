"""Approved S6a typed input and public result contracts; no I/O or financial math."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from equity_core.assessment import EvaluationContext
from equity_core.fiscal import FiscalCalendarEvidence
from equity_core.history import HistoryPolicy
from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_core.periods import RevisionCompatibility
from equity_core.trends import TrendPolicy
from equity_ingest.financial_types import PeriodSpec, ScopeSpec, UnitSpec
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


class SelectionKey(FrozenModel):
    issuer_id: UUID
    security_id: UUID
    quote_identifier_id: UUID
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


class OperandSpec(FrozenModel):
    method: Literal["selected", "annual", "quarters", "ytd", "annual_ytd"]
    source_indices: tuple[Annotated[int, Field(strict=True, ge=0)], ...]
    calendar_evidence: FiscalCalendarEvidence | None
    revision_compatibility: RevisionCompatibility | None


class MetricSpec(FrozenModel):
    metric_id: Nonempty
    unit: Nonempty
    operands: tuple[OperandSpec, ...]
    calendar_evidence: FiscalCalendarEvidence | None
    revision_compatibility: RevisionCompatibility | None


class HistorySampleRef(FrozenModel):
    snapshot_id: UUID
    payload_hash: Sha256
    quarter_end: date


class CaptureInput(FrozenModel):
    capture_id: UUID
    fetched_at: datetime
    body_sha256: Sha256


class InputManifest(FrozenModel):
    version: Literal["s6-input-v1"]
    evidence_mode: Literal["synthetic"]
    fixture_label: Literal["Synthetic integration fixture — not company data"]
    selector: SelectionKey
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
InputManifest.model_rebuild(
    _types_namespace={
        "StatementSelection": StatementSelection,
        "PeriodSpec": PeriodSpec,
        "ScopeSpec": ScopeSpec,
        "UnitSpec": UnitSpec,
        "PrecisionEvidence": PrecisionEvidence,
    }
)


def read_manifest(text: str) -> InputManifest:
    parse_canonical(text)
    manifest = InputManifest.model_validate_json(text)
    if canonical_json(manifest) != text:
        raise ValueError("Input fields or representations changed during typed reconstruction")
    return manifest


class PublicEvidence(FrozenModel):
    input_index: int
    concept: Nonempty
    source_url: str | None
    accession: str | None
    filed_on: date | None
    capture_ids: tuple[UUID, ...]
    retrieved_at: tuple[datetime, ...]
    source_tag: str | None
    original_numeric_text: DecimalString | None
    normalization_operation: Literal["identity_decimal"] | None
    transform_hash: Sha256 | None
    mapping_revision_id: UUID
    normalizer_revision: str
    selection_hash: Sha256
    scope_kind: str
    scope_hash: Sha256
    source_hashes: tuple[Sha256, ...]
    resolution_ids: tuple[UUID, ...]
    observation_ids: tuple[UUID, ...]
    period_start: date | None
    period_end: date
    unit: Nonempty
    value: DecimalString | None
    absolute_error: DecimalString | None
    flags: tuple[str, ...]


class PublicOperand(FrozenModel):
    input_indices: tuple[int, ...]
    coefficients: tuple[int, ...]
    period_start: date | None
    period_end: date
    value: DecimalString | None
    absolute_error: DecimalString | None
    formula_id: str
    formula_revision: str
    reasons: tuple[str, ...]
    review_hash: Sha256


class PublicMetric(FrozenModel):
    metric_id: Nonempty
    value: DecimalString | None
    unit: Nonempty
    status: Status
    applicability: bool | None
    reasons: tuple[str, ...]
    formula_revision: Nonempty
    input_hash: Sha256
    input_indices: tuple[int, ...]
    operands: tuple[PublicOperand, ...]

    @model_validator(mode="after")
    def validate_value(self) -> Self:
        if self.status == "valid" and self.value is None:
            raise ValueError("Valid metric requires a value")
        if self.status in {"not_meaningful", "missing", "invalid"} and self.value is not None:
            raise ValueError("Unavailable numeric result must be null")
        if self.status != "valid" and not self.reasons:
            raise ValueError("Unavailable metric requires reasons")
        return self


class PublicObservation(FrozenModel):
    rule_id: Nonempty
    rule_revision: Nonempty
    topic: Nonempty
    category: Nonempty
    text: str
    metric_ids: tuple[str, ...]


class PublicCoverage(FrozenModel):
    applicable_count: int
    covered_count: int
    unresolved_count: int
    fraction: DecimalString | None
    counts: dict[Status, int]
    revision: Nonempty


class PublicHistory(FrozenModel):
    metric_id: Nonempty
    years: Literal[3, 5, 10]
    minimum_samples: int
    window_start: date
    window_end: date
    eligible_snapshot_ids: tuple[UUID, ...]
    excluded: tuple[tuple[UUID, tuple[str, ...]], ...]
    missing_quarter_ends: tuple[date, ...]
    p25: DecimalString | None
    p50: DecimalString | None
    p75: DecimalString | None
    relation: Literal["below", "within", "above"] | None
    reasons: tuple[str, ...]


class PublicTrend(FrozenModel):
    period_ends: tuple[date, ...]
    input_indices: tuple[int, ...]
    rates: tuple[DecimalString | None, ...]
    input_statuses: tuple[Status, ...]
    input_reasons: tuple[tuple[str, ...], ...]
    relation: Literal["rising", "falling", "broadly_stable", "mixed"] | None
    changes: tuple[DecimalString, ...]
    reasons: tuple[str, ...]
    rule_revision: Nonempty


class PublicAccounting(FrozenModel):
    period_end: date
    residual: DecimalString | None
    tolerance: DecimalString | None
    matches: bool | None
    input_indices: tuple[int, ...]
    reasons: tuple[str, ...]
    rule_revision: Nonempty


class FundamentalsPayload(FrozenModel):
    version: Literal["s6-fundamentals-v1"]
    evidence_mode: Literal["synthetic"]
    fixture_label: Literal["Synthetic integration fixture — not company data"]
    selector: SelectionKey
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


class SnapshotResponse(FrozenModel):
    snapshot_id: UUID
    request_id: UUID
    execution_id: UUID
    input_snapshot_id: UUID
    generated_at: datetime
    compatibility_key: Sha256
    payload_hash: Sha256
    outcome: Literal["completed", "completed_with_gaps"]
    result: FundamentalsPayload


class NoResult(FrozenModel):
    code: Literal["snapshot_not_found", "no_compatible_snapshot"]
    message: str


class LatestResponse(FrozenModel):
    snapshot: SnapshotResponse
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


class LatestSelection(FrozenModel):
    security_id: UUID
    compatibility_key: Sha256
    scope_id: UUID
