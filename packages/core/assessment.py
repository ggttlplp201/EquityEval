"""Pure internal applicability, freshness and neutral source-metric projections.

These are caller-supplied reviewed policies, not production defaults or stored
fact statuses. The original calculation, source facts and all policies survive.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from typing import Literal, cast
from uuid import UUID

from equity_core.company import _INFORMATIONAL, _operand_problems
from equity_core.inputs import FinancialInput
from equity_core.metrics import (
    Calculation,
    ReviewedGrowthCalculation,
    _context,
    current_ratio,
    derived_gross_margin,
    free_cash_flow,
    free_cash_flow_margin,
    gross_margin,
    net_margin,
    net_working_capital,
    operating_margin,
    reported_amount,
    return_on_assets,
    revenue_growth,
)
from equity_core.periods import PeriodAmount


@dataclass(frozen=True)
class MetricApplicability:
    metric_id: str
    applicable: bool | None
    rationale: str

    def __post_init__(self) -> None:
        if (
            not _text(self.metric_id)
            or not _text(self.rationale)
            or (self.applicable is not None and type(self.applicable) is not bool)
        ):
            raise ValueError("Applicability requires an explicit disposition and rationale")


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _references(refs: tuple[str, ...]) -> bool:
    return isinstance(refs, tuple) and bool(refs) and all(_text(ref) for ref in refs)


@dataclass(frozen=True)
class ProfilePolicy:
    issuer_id: UUID
    business_model: str
    lifecycle: str
    instrument_basis: str
    revision: str
    effective_on: date
    known_on: date
    evidence_refs: tuple[str, ...]
    rules: tuple[MetricApplicability, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.issuer_id, UUID)
            or not all(
                _text(value)
                for value in (
                    self.business_model,
                    self.lifecycle,
                    self.instrument_basis,
                    self.revision,
                )
            )
            or type(self.effective_on) is not date
            or type(self.known_on) is not date
            or not _references(self.evidence_refs)
            or not isinstance(self.rules, tuple)
            or any(not isinstance(rule, MetricApplicability) for rule in self.rules)
            or len({rule.metric_id for rule in self.rules}) != len(self.rules)
        ):
            raise ValueError("Profile requires dated, versioned evidence and unique metric rules")


@dataclass(frozen=True)
class FreshnessPolicy:
    revision: str
    max_age_days: int
    evidence_refs: tuple[str, ...]
    expected_period_end: date | None = None
    expected_by: date | None = None

    def __post_init__(self) -> None:
        if (
            not _text(self.revision)
            or not _references(self.evidence_refs)
            or type(self.max_age_days) is not int
            or self.max_age_days < 0
            or (self.expected_period_end is None) != (self.expected_by is None)
            or (
                self.expected_period_end is not None
                and (
                    type(self.expected_period_end) is not date
                    or type(self.expected_by) is not date
                    or self.expected_by < self.expected_period_end
                )
            )
        ):
            raise ValueError("Freshness requires explicit age policy and a paired filing deadline")


@dataclass(frozen=True)
class EvaluationContext:
    as_of: date
    profile: ProfilePolicy
    freshness: FreshnessPolicy

    def __post_init__(self) -> None:
        if (
            type(self.as_of) is not date
            or not isinstance(self.profile, ProfilePolicy)
            or not isinstance(self.freshness, FreshnessPolicy)
        ):
            raise ValueError("Evaluation requires a frozen date and explicit reviewed policies")


Status = Literal[
    "valid", "not_meaningful", "missing", "invalid", "stale", "unsupported", "inapplicable"
]


@dataclass(frozen=True)
class MetricAssessment:
    calculation: Calculation
    context: EvaluationContext
    applicability: bool | None
    status: Status
    value: Decimal | None
    reasons: tuple[str, ...]
    evaluation_revision: str = "s5-assessment-v1"

    @property
    def usable(self) -> bool:
        return self.status == "valid" and self.applicability is True


# Registry entries route through existing calculators, never duplicate their math.
_CALCULATORS: dict[str, tuple[int, Callable[..., Calculation]]] = {
    "revenue_growth_yoy": (2, revenue_growth),
    "gross_margin": (2, gross_margin),
    "gross_margin_derived": (2, derived_gross_margin),
    "operating_margin": (2, operating_margin),
    "net_margin_consolidated": (2, net_margin),
    "free_cash_flow_ppe": (2, free_cash_flow),
    "free_cash_flow_margin_ppe": (3, free_cash_flow_margin),
    "current_ratio": (2, current_ratio),
    "net_working_capital": (2, net_working_capital),
    "return_on_assets": (3, return_on_assets),
}
SUPPORTED_METRICS = tuple(_CALCULATORS)
_BALANCE_METRICS = {"current_ratio", "net_working_capital", "return_on_assets"}
_NM = {"denominator_nonpositive", "denominator_indistinguishable_from_zero"}
_STATUSES: tuple[Status, ...] = (
    "valid",
    "not_meaningful",
    "stale",
    "missing",
    "invalid",
    "unsupported",
    "inapplicable",
)


def _known_metric(metric_id: str) -> bool:
    from equity_schema.concepts import Concept

    return metric_id in _CALCULATORS or metric_id in {
        "reported." + concept.value for concept in Concept
    }


def _rebuild(calculation: Calculation) -> tuple[Calculation | None, set[str]]:
    operands = calculation.operands
    if (
        not isinstance(operands, tuple)
        or not operands
        or any(not isinstance(item, FinancialInput | PeriodAmount) for item in operands)
    ):
        return None, {"calculation_inputs_invalid"}
    if not _known_metric(calculation.metric_id):
        return None, {"unsupported_metric_definition"}
    if calculation.metric_id.startswith("reported."):
        if len(operands) != 1:
            return None, {"calculation_inputs_invalid"}
        rebuilt = reported_amount(operands[0])
    else:
        arity, calculator = _CALCULATORS[calculation.metric_id]
        if len(operands) != arity or (
            calculation.metric_id in _BALANCE_METRICS
            and any(not isinstance(item, FinancialInput) for item in operands)
        ):
            return None, {"calculation_inputs_invalid"}
        if isinstance(calculation, ReviewedGrowthCalculation):
            if calculation.metric_id != "revenue_growth_yoy":
                return None, {"calculation_projection_mismatch"}
            rebuilt = revenue_growth(
                operands[0],
                operands[1],
                calendar_evidence=calculation.calendar_evidence,
                revision_compatibility=calculation.revision_compatibility,
            )
        else:
            rebuilt = calculator(*operands)
    problems = set()
    for source in operands:
        if isinstance(source, PeriodAmount):
            problems.update(set(_operand_problems(source)) & {"period_projection_mismatch"})
    if rebuilt != calculation:
        problems.add("calculation_projection_mismatch")
    return rebuilt, problems


def evaluate(calculation: Calculation, context: EvaluationContext) -> MetricAssessment:
    """Reproduce the formula first; never turn edited outputs into observations."""
    rule = next((r for r in context.profile.rules if r.metric_id == calculation.metric_id), None)
    applicability = rule.applicable if rule else None
    rebuilt, problems = _rebuild(calculation)
    reasons = set(calculation.flags) | problems
    value = rebuilt.value if rebuilt is not None and not problems else None
    sources: list[FinancialInput] = []
    for item in calculation.operands:
        if isinstance(item, FinancialInput):
            sources.append(item)
        elif isinstance(item, PeriodAmount):
            sources.extend(item.operands)
    if context.profile.instrument_basis != "consolidated_issuer":
        reasons.add("unsupported_profile_instrument_basis")
        problems.add("unsupported_profile_instrument_basis")
    if context.profile.effective_on > context.as_of or context.profile.known_on > context.as_of:
        reasons.add("profile_not_available_at_cutoff")
        problems.add("profile_not_available_at_cutoff")
    if any(source.selection.query.issuer_id != context.profile.issuer_id for source in sources):
        reasons.add("profile_issuer_mismatch")
        problems.add("profile_issuer_mismatch")
    if any(
        (source.selection.query.filed_cutoff or source.selection.query.captured_before.date())
        > context.as_of
        or source.period.end_date > context.as_of
        for source in sources
    ):
        reasons.add("input_after_evaluation_cutoff")
        problems.add("input_after_evaluation_cutoff")
    flags = set(calculation.flags) - _INFORMATIONAL
    status: Status
    if problems:
        status = (
            "unsupported"
            if all(flag.startswith("unsupported_") for flag in problems)
            else "invalid"
        )
        value = None
    elif applicability is None:
        status = "unsupported"
        reasons.add("profile_applicability_unreviewed")
    elif applicability is False:
        status = "inapplicable"
        reasons.add("profile_metric_inapplicable")
    elif value is None:
        missing = any(source.fact is None or source.fact.value is None for source in sources)
        if flags and flags <= _NM and all(source.precision is not None for source in sources):
            status = "not_meaningful"
        elif (
            missing
            or "denominator_precision_unknown" in flags
            or (flags <= _NM and any(source.precision is None for source in sources))
        ):
            status = "missing"
            if not missing:
                reasons.add("required_source_precision_unknown")
        elif any(
            flag.startswith("unsupported_")
            or flag in {"revision_compatibility_unproven", "incompatible_comparison_basis"}
            for flag in flags
        ):
            status = "unsupported"
        else:
            status = "invalid"
    else:
        status = "valid" if not flags else "invalid"
        if status == "invalid":
            value = None
    if status in {"valid", "not_meaningful"} and sources:
        newest_end = max(source.period.end_date for source in sources)
        policy = context.freshness
        if (context.as_of - newest_end).days > policy.max_age_days:
            reasons.add("financial_period_stale")
            status = "stale"
        if (
            policy.expected_by is not None
            and policy.expected_period_end is not None
            and context.as_of > policy.expected_by
            and newest_end < policy.expected_period_end
        ):
            reasons.add("expected_filing_missing")
            status = "stale"
    return MetricAssessment(
        calculation, context, applicability, status, value, tuple(sorted(reasons))
    )


@dataclass(frozen=True)
class MetricCoverage:
    applicable_count: int
    covered_count: int
    unresolved_count: int
    coverage: Decimal | None
    counts: tuple[tuple[Status, int], ...]
    context: EvaluationContext
    revision: str = "s5-coverage-v1"


def _checked(assessments: tuple[MetricAssessment, ...], context: EvaluationContext) -> None:
    if (
        not isinstance(assessments, tuple)
        or len({item.calculation.metric_id for item in assessments}) != len(assessments)
        or any(
            item.context != context or evaluate(item.calculation, context) != item
            for item in assessments
        )
    ):
        raise ValueError("Assessments require unique metrics and reproducible matching context")

    histories: set[tuple[object, ...]] = set()
    ends: set[date] = set()
    flow_windows: set[tuple[object, ...]] = set()
    editions: set[frozenset[UUID]] = set()
    for item in assessments:
        if item.status == "invalid" or not item.calculation.operands:
            continue
        target = cast(FinancialInput | PeriodAmount, item.calculation.operands[0])
        leaves: list[FinancialInput] = []
        for source in item.calculation.operands:
            if isinstance(source, FinancialInput):
                leaves.append(source)
            elif isinstance(source, PeriodAmount):
                leaves.extend(source.operands)
        histories.update(source.history_key for source in leaves)
        ends.add(target.period.end_date)
        if target.period.start_date is not None:
            method = "reported" if isinstance(target, FinancialInput) else target.formula_id
            if method == "direct_annual":
                method = "reported"
            flow_windows.add((target.period.start_date, target.period.end_date, method))
        editions.add(
            frozenset(
                version
                for source in leaves
                if source.period.end_date == target.period.end_date
                for version in source.selection.filing_version_ids
            )
        )
    if any(len(group) > 1 for group in (histories, ends, flow_windows, editions)):
        raise ValueError(
            "Company summary requires a coherent source selection and financial period"
        )


def coverage(
    assessments: tuple[MetricAssessment, ...], *, context: EvaluationContext
) -> MetricCoverage:
    """Use the entire applicability roster, including results the caller omitted."""
    _checked(assessments, context)
    results = {item.calculation.metric_id: item for item in assessments}
    if set(results) - {rule.metric_id for rule in context.profile.rules}:
        raise ValueError("Coverage cannot include a metric outside the applicability roster")
    counts = dict.fromkeys(_STATUSES, 0)
    applicable = covered = unresolved = 0
    for rule in context.profile.rules:
        if rule.applicable is None:
            unresolved += 1
            counts["unsupported"] += 1
        elif rule.applicable is False:
            counts["inapplicable"] += 1
        else:
            applicable += 1
            result = results.get(rule.metric_id)
            status = (
                result.status
                if result
                else "missing"
                if _known_metric(rule.metric_id)
                else "unsupported"
            )
            counts[status] += 1
            covered += status in {"valid", "not_meaningful"}
    with localcontext(_context()):
        fraction = Decimal(covered) / Decimal(applicable) if applicable and not unresolved else None
    return MetricCoverage(applicable, covered, unresolved, fraction, tuple(counts.items()), context)


@dataclass(frozen=True)
class Observation:
    rule_id: str
    topic: str
    category: str
    text: str
    metrics: tuple[MetricAssessment, ...]
    rule_revision: str = "s5-neutral-observations-v1"


def observations(assessments: tuple[MetricAssessment, ...]) -> tuple[Observation, ...]:
    if not assessments:
        return ()
    _checked(assessments, assessments[0].context)
    result = []
    for item in sorted(assessments, key=lambda item: item.calculation.metric_id):
        if not item.usable or item.value is None:
            continue
        metric = item.calculation.metric_id
        rule: tuple[str, str, str, str] | None = None
        if metric == "revenue_growth_yoy":
            rule = (
                ("revenue_grew", "revenue", "operating", "Revenue grew year over year.")
                if item.value > 0
                else (
                    ("revenue_declined", "revenue", "operating", "Revenue fell year over year.")
                    if item.value < 0
                    else (
                        "revenue_unchanged",
                        "revenue",
                        "operating",
                        "Revenue was unchanged year over year.",
                    )
                )
            )
        elif metric in {"free_cash_flow_ppe", "free_cash_flow_margin_ppe"} and item.value < 0:
            rule = (
                "cash_spending_gap",
                "cash_generation",
                "cash",
                "Operating cash flow did not cover cash PPE spending.",
            )
        elif metric == "operating_margin" and item.value < 0:
            rule = (
                "operating_loss",
                "earnings",
                "operating",
                "Operating income was negative for this period.",
            )
        elif metric in {"net_margin_consolidated", "return_on_assets"} and item.value < 0:
            rule = (
                "consolidated_loss",
                "earnings",
                "operating",
                "Consolidated net income was negative for this period.",
            )
        if rule is not None:
            result.append(Observation(*rule, (item,)))
    return tuple(result)


def review_items(assessments: tuple[MetricAssessment, ...]) -> tuple[Observation, ...]:
    """At most three distinct topics, with stable data/cash/operating priority."""
    facts = observations(assessments)
    candidates = list(
        fact
        for fact in facts
        if fact.rule_id != "revenue_grew" and fact.rule_id != "revenue_unchanged"
    )
    for item in assessments:
        if not item.usable:
            candidates.append(
                Observation(
                    "data_review",
                    "data_availability",
                    "data",
                    "Review metric availability and its evidence.",
                    (item,),
                )
            )
        elif "extreme_margin" in item.reasons:
            candidates.append(
                Observation(
                    "extreme_margin_review",
                    "extreme_margin",
                    "data",
                    "Review the reported amounts and the margin calculation.",
                    (item,),
                )
            )
    priority = {"data": 0, "cash": 1, "operating": 2}
    result: list[Observation] = []
    seen: set[str] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            priority[item.category],
            item.rule_id,
            item.metrics[0].calculation.metric_id,
        ),
    ):
        if candidate.topic not in seen:
            # Related metrics share a single review item but every evidence link survives.
            related = tuple(
                sorted(
                    {
                        item.calculation.metric_id: item
                        for other in candidates
                        if other.topic == candidate.topic
                        for item in other.metrics
                    }.values(),
                    key=lambda item: item.calculation.metric_id,
                )
            )
            result.append(
                Observation(
                    candidate.rule_id, candidate.topic, candidate.category, candidate.text, related
                )
            )
            seen.add(candidate.topic)
    return tuple(result[:3])
