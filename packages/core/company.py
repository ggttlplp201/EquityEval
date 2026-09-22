"""Shared evaluated company evidence and multiples; no selection or I/O."""

from __future__ import annotations

import calendar
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, DecimalException, localcontext
from uuid import UUID

from equity_core.inputs import FinancialInput
from equity_core.metrics import Calculation, _context, _issues, free_cash_flow
from equity_core.periods import (
    _SUPPORTED_FLOWS,
    PeriodAmount,
    annual_amount,
    quarter_from_ytd,
    ttm_from_annual_ytd,
    ttm_from_quarters,
)


@dataclass(frozen=True)
class EvidenceValue:
    value: Decimal | None
    absolute_error: Decimal | None
    input_hash: str
    period_start: date | None
    period_end: date | None
    usable: bool
    flags: tuple[str, ...] = ()
    currency: str = "USD"
    basis: str = "consolidated_flow"


@dataclass(frozen=True)
class CompanyMetric:
    metric_id: str
    value: Decimal | None
    input_hash: str
    operand_hashes: tuple[str, ...]
    usable: bool
    flags: tuple[str, ...] = ()


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal | UUID):
        return str(value)
    raise TypeError("Unsupported source manifest value")


def _digest(kind: str, payload: object) -> str:
    manifest = {"revision": "s5-company-evidence-v1", "kind": kind, "payload": payload}
    text = json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(text.encode()).hexdigest()


_INFORMATIONAL = frozenset(
    {"revised_view", "earliest_available", "extreme_margin", "gross_profit_derived"}
)


def _numeric(value: object) -> bool:
    return (
        isinstance(value, Decimal)
        and value.is_finite()
        and len(value.as_tuple().digits) <= 1000
        and isinstance(value.as_tuple().exponent, int)
        and abs(int(value.as_tuple().exponent)) <= 1000
        and abs(value.adjusted()) <= 1000
    )


def evidence_issues(
    amount: EvidenceValue,
    *,
    basis: str,
    evaluation_date: date,
    instant: bool = False,
    require_precision: bool = True,
) -> tuple[str, ...]:
    """Validate evaluated USD annual/TTM flows or an exact-date equity point.

    Amount signs are retained. A loss remains a valid aggregate constituent;
    the individual multiple separately requires a positive denominator.
    """
    if type(evaluation_date) is not date:
        raise ValueError("An explicit evaluation date is required")
    problems = set(amount.flags) - _INFORMATIONAL
    if amount.usable is not True:
        problems.add("evidence_unusable")
    if (
        not isinstance(amount.input_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", amount.input_hash) is None
    ):
        problems.add("evidence_hash_invalid")
    if not _numeric(amount.value):
        problems.add("evidence_value_invalid")
    if amount.currency != "USD":
        problems.add("unsupported_currency")
    if amount.basis != basis:
        problems.add("incompatible_evidence_basis")
    if amount.absolute_error is None:
        if require_precision:
            problems.add("source_precision_unknown")
    elif not _numeric(amount.absolute_error) or amount.absolute_error < 0:
        problems.add("source_precision_invalid")
    start, end = amount.period_start, amount.period_end
    if instant:
        if start is not None or type(end) is not date or end != evaluation_date:
            problems.add("incompatible_equity_date")
    elif (
        type(start) is not date
        or type(end) is not date
        or start > end
        or end > evaluation_date
        or start.day != 1
        or end.day != calendar.monthrange(end.year, end.month)[1]
        or (end.year - start.year) * 12 + end.month - start.month + 1 != 12
    ):
        problems.add("unsupported_flow_period")
    return tuple(sorted(problems))


def equity_multiple(
    metric_id: str, cap: EvidenceValue, denominator: EvidenceValue, *, as_of: date
) -> CompanyMetric:
    bases = {"pe": "income_available_common", "ps": "consolidated_flow", "pfcf": "cash_ppe_fcf"}
    problems = set(
        evidence_issues(
            cap, basis="common_equity", evaluation_date=as_of, instant=True, require_precision=False
        )
    )
    problems.update(
        evidence_issues(
            denominator, basis=bases.get(metric_id, "unsupported"), evaluation_date=as_of
        )
    )
    if metric_id not in bases:
        problems.add("unsupported_equity_multiple")
    if _numeric(cap.value) and cap.value is not None and cap.value <= 0:
        problems.add("nonpositive_equity_value")
    if _numeric(denominator.value) and denominator.value is not None:
        if denominator.value <= 0:
            problems.add("denominator_nonpositive")
        elif (
            _numeric(denominator.absolute_error)
            and denominator.absolute_error is not None
            and denominator.value <= denominator.absolute_error
        ):
            problems.add("denominator_indistinguishable_from_zero")
    value = None
    if not problems:
        assert cap.value is not None and denominator.value is not None
        try:
            with localcontext(_context()):
                value = cap.value / denominator.value
        except DecimalException:
            problems.add("unsupported_numeric_range")
    flags = set(cap.flags) | set(denominator.flags) | problems
    return CompanyMetric(
        metric_id,
        value,
        _digest(
            "equity_multiple",
            {
                "metric_id": metric_id,
                "cap": asdict(cap),
                "denominator": asdict(denominator),
                "as_of": as_of,
            },
        ),
        (cap.input_hash, denominator.input_hash),
        value is not None and not problems,
        tuple(sorted(flags)),
    )


def _operand_problems(source: FinancialInput | PeriodAmount) -> set[str]:
    problems = _issues((source,), (source.concept,), same_period=False)
    if source.concept not in _SUPPORTED_FLOWS:
        problems.add("unsupported_evidence_concept")
    if isinstance(source, PeriodAmount):
        inputs = source.operands
        rebuilt = None
        if source.formula_id == "direct_annual" and len(inputs) == 1:
            rebuilt = annual_amount(inputs[0], calendar_evidence=source.calendar_evidence)
        elif source.formula_id == "sum_four_quarters":
            rebuilt = ttm_from_quarters(
                inputs,
                revision_compatibility=source.revision_compatibility,
                calendar_evidence=source.calendar_evidence,
            )
        elif source.formula_id == "ytd_difference" and len(inputs) == 2:
            rebuilt = quarter_from_ytd(
                inputs[0], inputs[1], calendar_evidence=source.calendar_evidence
            )
        elif source.formula_id == "annual_ytd_bridge" and len(inputs) == 3:
            rebuilt = ttm_from_annual_ytd(
                inputs[0],
                inputs[1],
                inputs[2],
                revision_compatibility=source.revision_compatibility,
                calendar_evidence=source.calendar_evidence,
            )
        if rebuilt != source:
            problems.add("period_projection_mismatch")
    return problems


def evidence_from_operand(source: FinancialInput | PeriodAmount) -> EvidenceValue:
    """Project supported monetary flows without inferring common-share earnings."""
    problems = _operand_problems(source)
    flags = tuple(sorted(set(source.flags) | problems))
    value = source.value if not problems else None
    return EvidenceValue(
        value,
        source.precision.absolute_error if source.precision is not None else None,
        _digest("financial_operand", asdict(source)),
        source.period.start_date,
        source.period.end_date,
        value is not None and not problems,
        flags,
        source.unit.unit_key,
    )


def evidence_from_fcf(calculation: Calculation) -> EvidenceValue:
    """Project the existing CFO-minus-cash-PPE calculation, retaining its manifest."""
    flags = set(calculation.flags)
    problems: set[str] = set()
    sources: tuple[FinancialInput | PeriodAmount, ...] = calculation.operands
    if calculation.metric_id != "free_cash_flow_ppe" or len(sources) != 2:
        problems.add("unsupported_fcf_projection")
    elif free_cash_flow(sources[0], sources[1]) != calculation:
        problems.add("fcf_projection_mismatch")
    for source in sources:
        problems.update(_operand_problems(source))
    problems.update(flags - _INFORMATIONAL)
    if not _numeric(calculation.value):
        problems.add("calculation_value_unavailable")
    error = None
    if not problems and all(source.precision is not None for source in sources):
        try:
            with localcontext(_context(exact=True)):
                error = sum(
                    (
                        source.precision.absolute_error
                        for source in sources
                        if source.precision is not None
                    ),
                    Decimal(0),
                )
        except DecimalException:
            problems.add("unsupported_numeric_range")
    value = calculation.value if not problems else None
    return EvidenceValue(
        value,
        error,
        _digest("fcf_calculation", asdict(calculation)),
        sources[0].period.start_date if sources else None,
        sources[0].period.end_date if sources else None,
        value is not None and not problems,
        tuple(sorted(flags | problems)),
        calculation.unit,
        "cash_ppe_fcf",
    )


def metric_from_calculation(
    calculation: Calculation,
    metric_id: str,
    operands: tuple[EvidenceValue, ...],
) -> CompanyMetric:
    """Project a trusted engine result and verify every supplied evidence operand.

    Company and sector views share the existing evaluated metric. This function
    does not introduce another division engine or infer new financial concepts.
    """
    aliases = {
        "revenue_yoy": "revenue_growth_yoy",
        "revenue_growth": "revenue_growth_yoy",
        "net_margin": "net_margin_consolidated",
        "fcf_margin": "free_cash_flow_margin_ppe",
    }
    supported = {
        "revenue_growth_yoy",
        "gross_margin",
        "gross_margin_derived",
        "operating_margin",
        "net_margin_consolidated",
        "free_cash_flow_margin_ppe",
    }
    target = aliases.get(metric_id, metric_id)
    problems = set(calculation.flags) - _INFORMATIONAL
    if target not in supported or calculation.metric_id != target:
        problems.add("calculation_metric_mismatch")
    if calculation.unit != "fraction" or calculation.formula_revision != "s5-source-metrics-v1":
        problems.add("unsupported_calculation_projection")
    sources: tuple[FinancialInput | PeriodAmount, ...] = calculation.operands
    expected: tuple[EvidenceValue, ...]
    if target == "free_cash_flow_margin_ppe" and len(sources) == 3:
        expected = (
            evidence_from_fcf(free_cash_flow(sources[0], sources[1])),
            evidence_from_operand(sources[2]),
        )
    else:
        expected = tuple(evidence_from_operand(source) for source in sources)
    if operands != expected:
        problems.add("calculation_operand_mismatch")
    if not expected or any(not item.usable for item in expected):
        problems.add("calculation_operand_unavailable")
    if not _numeric(calculation.value):
        problems.add("calculation_value_unavailable")
    value = calculation.value if not problems else None
    return CompanyMetric(
        metric_id,
        value,
        _digest(
            "metric_projection",
            {
                "metric_id": metric_id,
                "calculation": asdict(calculation),
                "operands": tuple(asdict(item) for item in operands),
            },
        ),
        tuple(item.input_hash for item in operands),
        value is not None and not problems,
        tuple(sorted(set(calculation.flags) | problems)),
    )
