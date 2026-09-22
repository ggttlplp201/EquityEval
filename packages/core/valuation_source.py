"""Reuse S5 source eligibility for an explicit annual run-rate assumption anchor."""

import calendar
from datetime import UTC, datetime

from equity_core.inputs import FinancialInput
from equity_core.metrics import _source_issues
from equity_schema.concepts import Concept
from equity_schema.fundamentals import SelectionKey


def anchor_reasons(
    source: FinancialInput, selector: SelectionKey, valuation_at: datetime
) -> tuple[str, ...]:
    reasons = _source_issues((source,), (Concept.REVENUE,))
    if (
        source.fact is None
        or source.fact.filed_date is None
        or source.fact.filed_date >= valuation_at.astimezone(UTC).date()
    ):
        reasons.add("anchor_intraday_publication_unproven")
    start, end = source.period.start_date, source.period.end_date
    if (
        start is None
        or start.day != 1
        or end.day != calendar.monthrange(end.year, end.month)[1]
        or (end.year - start.year) * 12 + end.month - start.month + 1 != 12
        or start != selector.period_start
        or end != selector.period_end
    ):
        reasons.add("unsupported_anchor_calendar")
    if source.precision is None:
        reasons.add("anchor_precision_unknown")
    elif source.value is not None and source.value <= source.precision.absolute_error:
        reasons.add("anchor_not_distinguishable_from_zero")
    return tuple(sorted(reasons))
