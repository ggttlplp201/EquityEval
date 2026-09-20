"""Pure source-metric arithmetic with exact input lineage; no source selection or I/O."""

from __future__ import annotations

import calendar
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DecimalException,
    Inexact,
    Subnormal,
    Underflow,
    localcontext,
)
from typing import TYPE_CHECKING

from equity_core.inputs import FinancialInput
from equity_schema.concepts import Concept

if TYPE_CHECKING:
    from equity_core.periods import PeriodAmount

    FinancialOperand = FinancialInput | PeriodAmount


@dataclass(frozen=True)
class Calculation:
    metric_id: str
    value: Decimal | None
    unit: str
    operands: tuple[FinancialOperand, ...]
    flags: tuple[str, ...] = ()
    formula_revision: str = "s5-source-metrics-v1"


def _denominator(input_value: FinancialOperand) -> set[str]:
    value = input_value.value
    if value is None:
        return {"source_input_unavailable"}
    if value <= 0:
        return {"denominator_nonpositive"}
    if input_value.precision is None:
        return {"denominator_precision_unknown"}
    if value <= input_value.precision.absolute_error:
        return {"denominator_indistinguishable_from_zero"}
    return set()


def _source_issues(
    operands: tuple[FinancialInput, ...],
    expected: tuple[Concept, ...],
    *,
    same_period: bool = True,
) -> set[str]:
    problems = {flag for item in operands for flag in item.blocking_flags}
    if any(item.value is None for item in operands):
        problems.add("source_input_unavailable")
    if tuple(item.concept for item in operands) != expected:
        problems.add("unexpected_concept")
    if len({item.history_key for item in operands}) != 1:
        problems.add("incompatible_history_policy")
    if len({item.selection.reporting_basis for item in operands}) != 1:
        problems.add("incompatible_reporting_basis")
    if any(item.selection.reporting_basis not in {"us_gaap", "ifrs"} for item in operands):
        problems.add("unsupported_reporting_basis")
    units = {
        (item.unit.unit_key, item.unit.numerator_measures, item.unit.denominator_measures)
        for item in operands
    }
    if len(units) != 1 or any(
        re.fullmatch(r"[A-Z]{3}", item.unit.unit_key) is None
        or item.unit.numerator_measures != (f"iso4217:{item.unit.unit_key}",)
        or item.unit.denominator_measures
        for item in operands
    ):
        problems.add("incompatible_units")
    if any(
        item.period.period_kind != "duration" or item.period.start_date is None for item in operands
    ):
        problems.add("flow_period_required")
    if same_period:
        if len({(item.period.start_date, item.period.end_date) for item in operands}) != 1:
            problems.add("incompatible_periods")
        if len({frozenset(item.selection.filing_version_ids) for item in operands}) != 1:
            problems.add("incompatible_filing_editions")
    for item in operands:
        cash = item.concept in {
            Concept.CASH_FROM_OPERATING_ACTIVITIES,
            Concept.CAPITAL_EXPENDITURES_PPE,
        }
        if item.selection.query.statement_family != ("cash_flow" if cash else "income"):
            problems.add("incompatible_statement_family")
        try:
            scope = json.loads(item.scope.descriptor_json)
        except (ValueError, TypeError):
            scope = {}
        required = {
            "consolidation",
            "instrument",
            "context_knowledge",
            "scope_evidence",
            "cash_scope",
            "payment_basis",
            "revenue_basis",
        }
        payment = (
            "actual_cash_payment"
            if item.concept == Concept.CAPITAL_EXPENDITURES_PPE
            else "as_reported"
        )
        if (
            not isinstance(scope, dict)
            or set(scope) != required
            or item.scope.scope_kind != "consolidated"
            or item.scope.instrument_id is not None
            or scope.get("consolidation") != "consolidated"
            or scope.get("instrument") is not None
            or scope.get("payment_basis") != payment
            or scope.get("cash_scope") != "not_applicable"
            or scope.get("revenue_basis") != "reported_complete_scope"
        ):
            problems.add("unsupported_semantic_scope")
    return problems


def _issues(
    operands: tuple[FinancialOperand, ...],
    expected: tuple[Concept, ...],
    *,
    same_period: bool = True,
) -> set[str]:
    leaves: list[FinancialInput] = []
    concepts: list[Concept] = []
    for item, concept in zip(operands, expected, strict=True):
        sources = (item,) if isinstance(item, FinancialInput) else item.operands
        leaves.extend(sources)
        concepts.extend((concept,) * len(sources))
    if all(isinstance(item, FinancialInput) for item in operands):
        return _source_issues(tuple(leaves), expected, same_period=same_period)
    problems = _source_issues(tuple(leaves), tuple(concepts), same_period=False)
    problems.update(flag for item in operands for flag in item.blocking_flags)
    if any(item.value is None for item in operands):
        problems.add("source_input_unavailable")
    if tuple(item.concept for item in operands) != expected:
        problems.add("unexpected_concept")
    if same_period:
        if len({(item.period.start_date, item.period.end_date) for item in operands}) != 1:
            problems.add("incompatible_periods")
        assemblies = {
            (
                "selected",
                item.period.start_date,
                item.period.end_date,
                tuple(item.selection.filing_version_ids),
            )
            if isinstance(item, FinancialInput)
            else item.assembly_key
            for item in operands
        }
        if len(assemblies) != 1:
            problems.add("incompatible_period_assemblies")
    return problems


def _context(*, exact: bool = False) -> Context:
    context = Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999, Emax=999)
    context.traps[Subnormal] = True
    context.traps[Underflow] = True
    context.traps[Inexact] = exact
    return context


def _difference(left: Decimal, right: Decimal) -> Decimal:
    # Monetary subtraction must not silently erase reported significant digits.
    with localcontext(_context(exact=True)):
        return left - right


def _calculate(
    metric: str,
    operands: tuple[FinancialOperand, ...],
    problems: set[str],
    operation: Callable[[tuple[Decimal, ...]], Decimal],
    *,
    unit: str = "fraction",
    margin: bool = False,
    extra_flags: tuple[str, ...] = (),
) -> Calculation:
    flags = {flag for item in operands for flag in item.flags} | set(extra_flags)
    values: list[Decimal] = []
    for item in operands:
        amount = item.value
        if amount is None:
            problems.add("source_input_unavailable")
        else:
            values.append(amount)
    value = None
    if not problems:
        try:
            with localcontext(_context()):
                value = operation(tuple(values))
                if not value.is_finite():
                    value = None
                    problems.add("unsupported_numeric_range")
        except DecimalException:
            problems.add("unsupported_numeric_range")
    if margin and value is not None and value.copy_abs() > 1:
        flags.add("extreme_margin")
    return Calculation(metric, value, unit, operands, tuple(sorted(flags | problems)))


def _reported_margin(
    metric: str,
    concept: Concept,
    numerator: FinancialOperand,
    revenue: FinancialOperand,
) -> Calculation:
    operands = (numerator, revenue)
    problems = _issues(operands, (concept, Concept.REVENUE)) | _denominator(revenue)
    return _calculate(metric, operands, problems, lambda values: values[0] / values[1], margin=True)


def operating_margin(income: FinancialOperand, revenue: FinancialOperand) -> Calculation:
    return _reported_margin("operating_margin", Concept.OPERATING_INCOME, income, revenue)


def gross_margin(profit: FinancialOperand, revenue: FinancialOperand) -> Calculation:
    return _reported_margin("gross_margin", Concept.GROSS_PROFIT, profit, revenue)


def net_margin(income: FinancialOperand, revenue: FinancialOperand) -> Calculation:
    return _reported_margin(
        "net_margin_consolidated", Concept.NET_INCOME_CONSOLIDATED, income, revenue
    )


def derived_gross_margin(revenue: FinancialOperand, cost: FinancialOperand) -> Calculation:
    """Explicit derived result, never a replacement reported GROSS_PROFIT fact."""
    operands = (revenue, cost)
    problems = _issues(operands, (Concept.REVENUE, Concept.COST_OF_REVENUE)) | _denominator(revenue)
    return _calculate(
        "gross_margin_derived",
        operands,
        problems,
        lambda values: _difference(values[0], values[1]) / values[0],
        margin=True,
        extra_flags=("gross_profit_derived",),
    )


def _cash_issues(cfo: FinancialOperand, capex: FinancialOperand) -> set[str]:
    problems = _issues(
        (cfo, capex), (Concept.CASH_FROM_OPERATING_ACTIVITIES, Concept.CAPITAL_EXPENDITURES_PPE)
    )
    if capex.value is not None and capex.value < 0:
        problems.add("negative_cash_ppe_capex")
    return problems


def free_cash_flow(cfo: FinancialOperand, capex: FinancialOperand) -> Calculation:
    """CFO less reported cash PPE purchases, not FCFF or issuer-adjusted FCF."""
    return _calculate(
        "free_cash_flow_ppe",
        (cfo, capex),
        _cash_issues(cfo, capex),
        lambda values: _difference(values[0], values[1]),
        unit=cfo.unit.unit_key,
    )


def free_cash_flow_margin(
    cfo: FinancialOperand, capex: FinancialOperand, revenue: FinancialOperand
) -> Calculation:
    operands = (cfo, capex, revenue)
    problems = (
        _cash_issues(cfo, capex)
        | _issues(
            operands,
            (
                Concept.CASH_FROM_OPERATING_ACTIVITIES,
                Concept.CAPITAL_EXPENDITURES_PPE,
                Concept.REVENUE,
            ),
        )
        | _denominator(revenue)
    )
    return _calculate(
        "free_cash_flow_margin_ppe",
        operands,
        problems,
        lambda values: _difference(values[0], values[1]) / values[2],
        margin=True,
    )


def reported_amount(source: FinancialOperand) -> Calculation:
    """Expose a selected amount without inventing missing denominator precision."""
    flags = set(source.flags)
    if source.value is None:
        flags.add("source_input_unavailable")
    return Calculation(
        "reported." + source.concept.value,
        source.value,
        source.unit.unit_key,
        (source,),
        tuple(sorted(flags)),
    )


def _comparison_period(current: FinancialOperand, prior: FinancialOperand) -> bool:
    """Only exact comparable calendar-month quarters/years; never infer fiscal calendars."""
    start, end = current.period.start_date, current.period.end_date
    old_start, old_end = prior.period.start_date, prior.period.end_date
    if (
        type(start) is not date
        or type(end) is not date
        or type(old_start) is not date
        or type(old_end) is not date
        or start.year <= 1
    ):
        return False
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    if start.day != 1 or months not in {3, 12}:
        return False
    if end.day != calendar.monthrange(end.year, end.month)[1]:
        return False
    if months == 3 and start.month not in {1, 4, 7, 10}:
        return False
    previous_start = date(start.year - 1, start.month, 1)
    previous_end = date(end.year - 1, end.month, calendar.monthrange(end.year - 1, end.month)[1])
    return old_start == previous_start and old_end == previous_end


def revenue_growth(current: FinancialOperand, prior: FinancialOperand) -> Calculation:
    operands = (current, prior)
    problems = _issues(
        operands, (Concept.REVENUE, Concept.REVENUE), same_period=False
    ) | _denominator(prior)
    if not _comparison_period(current, prior):
        problems.add("unsupported_comparison_periods")
    return _calculate(
        "revenue_growth_yoy",
        operands,
        problems,
        lambda values: _difference(values[0], values[1]) / values[1],
    )
