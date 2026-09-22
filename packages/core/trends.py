"""Neutral trends over three comparable evaluated quarterly revenue YoY rates."""

import calendar
from dataclasses import dataclass
from decimal import Decimal, DecimalException
from typing import cast

from equity_core.assessment import MetricAssessment, _references, _text, evaluate
from equity_core.inputs import FinancialInput
from equity_core.metrics import ReviewedGrowthCalculation, _difference, _selection_issues
from equity_core.periods import RevisionCompatibility, _revision_problems
from equity_schema.concepts import Concept


@dataclass(frozen=True)
class TrendPolicy:
    tolerance: Decimal
    revision: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.tolerance, Decimal)
            or not self.tolerance.is_finite()
            or self.tolerance < 0
            or not _text(self.revision)
            or not _references(self.evidence_refs)
        ):
            raise ValueError("Trend tolerance requires a finite nonnegative versioned policy")


@dataclass(frozen=True)
class GrowthTrend:
    relation: str | None
    changes: tuple[Decimal, ...]
    metrics: tuple[MetricAssessment, ...]
    policy: TrendPolicy
    flags: tuple[str, ...]
    revision_compatibility: RevisionCompatibility | None = None
    rule_revision: str = "s5-revenue-trend-v1"


def _quarter(item: MetricAssessment) -> FinancialInput | None:
    calculation = item.calculation
    if calculation.metric_id != "revenue_growth_yoy" or not calculation.operands:
        return None
    source = calculation.operands[0]
    if not isinstance(source, FinancialInput):
        return None
    if isinstance(calculation, ReviewedGrowthCalculation) and calculation.calendar_evidence:
        return source if calculation.calendar_evidence.match(source, cumulative=False) else None
    selected = cast(FinancialInput, source)
    start, end = selected.period.start_date, selected.period.end_date
    if (
        start is not None
        and start.day == 1
        and start.month in {1, 4, 7, 10}
        and end.day == calendar.monthrange(end.year, end.month)[1]
        and (end.year - start.year) * 12 + end.month - start.month + 1 == 3
    ):
        return selected
    return None


def growth_trend(
    metrics: tuple[MetricAssessment, ...],
    *,
    policy: TrendPolicy,
    revision_compatibility: RevisionCompatibility | None = None,
) -> GrowthTrend:
    flags: set[str] = set()
    if not isinstance(metrics, tuple) or not isinstance(policy, TrendPolicy):
        raise ValueError("Trend requires immutable metrics and an explicit policy")
    if len(metrics) != 3:
        flags.add("three_quarterly_rates_required")
    sources = tuple(_quarter(item) for item in metrics)
    if any(source is None for source in sources):
        flags.add("unsupported_trend_periods")
    calendars = {
        item.calculation.calendar_evidence.comparison_key
        if isinstance(item.calculation, ReviewedGrowthCalculation)
        and item.calculation.calendar_evidence is not None
        else None
        for item in metrics
    }
    if len(calendars) > 1:
        flags.add("incompatible_trend_calendar")
    if metrics and any(item.context != metrics[0].context for item in metrics):
        flags.add("incompatible_trend_context")
    if any(not item.usable or evaluate(item.calculation, item.context) != item for item in metrics):
        flags.add("trend_input_unavailable")
    leaves = tuple(
        source
        for item in metrics
        for source in item.calculation.operands
        if isinstance(source, FinancialInput)
    )
    if leaves:
        flags.update(_selection_issues(leaves, (Concept.REVENUE,) * len(leaves)))
        flags.update(_revision_problems(leaves, revision_compatibility))
    if not flags:
        for left, right in zip(sources, sources[1:], strict=False):
            assert left is not None and right is not None
            if (
                right.period.start_date is None
                or left.period.end_date.toordinal() + 1 != right.period.start_date.toordinal()
            ):
                flags.add("nonconsecutive_trend_quarters")
    # All dates, values, formula revisions and policies stay attached even on failure.
    changes: tuple[Decimal, ...] = ()
    relation = None
    if not flags:
        values = tuple(item.value for item in metrics if item.value is not None)
        if len(values) != 3:
            flags.add("trend_input_unavailable")
        else:
            try:
                changes = (_difference(values[1], values[0]), _difference(values[2], values[1]))
                if all(change > policy.tolerance for change in changes):
                    relation = "rising"
                elif all(change < policy.tolerance.copy_negate() for change in changes):
                    relation = "falling"
                elif all(change.copy_abs() <= policy.tolerance for change in changes):
                    relation = "broadly_stable"
                else:
                    relation = "mixed"
            except DecimalException:
                changes = ()
                flags.add("unsupported_numeric_range")
    return GrowthTrend(
        relation, changes, metrics, policy, tuple(sorted(flags)), revision_compatibility
    )
