"""Pure calendar-month period amounts; reported selections remain untouched."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Context, Decimal, DecimalException, Inexact, localcontext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from equity_ingest.financial_types import ScopeSpec, UnitSpec

from equity_core.fiscal import FiscalCalendarEvidence
from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_core.metrics import _issues
from equity_schema.concepts import Concept


@dataclass(frozen=True)
class RevisionCompatibility:
    """Reviewed cross-filing compatibility; pinned selections and evidence are required.

    A shared query vintage alone never proves comparable restatement treatment.
    The caller must review these exact selections before supplying this record.
    """

    input_hashes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    review_revision: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.input_hashes, tuple)
            or not self.input_hashes
            or any(
                not isinstance(item, str) or re.fullmatch(r"[0-9a-f]{64}", item) is None
                for item in self.input_hashes
            )
            or len(set(self.input_hashes)) != len(self.input_hashes)
            or not isinstance(self.evidence_refs, tuple)
            or not self.evidence_refs
            or any(not isinstance(item, str) or not item.strip() for item in self.evidence_refs)
            or not isinstance(self.review_revision, str)
            or not self.review_revision.strip()
        ):
            raise ValueError(
                "Revision compatibility requires unique selection hashes and reviewed evidence"
            )


@dataclass(frozen=True)
class PeriodWindow:
    start_date: date | None
    end_date: date
    period_kind: str = "duration"


@dataclass(frozen=True)
class PeriodAmount:
    """Derived amount with every original selection, never a normalized fact."""

    value: Decimal | None
    operands: tuple[FinancialInput, ...]
    coefficients: tuple[int, ...]
    period: PeriodWindow
    precision: PrecisionEvidence | None
    flags: tuple[str, ...]
    formula_id: str
    formula_revision: str = "s5-period-amounts-v1"
    revision_compatibility: RevisionCompatibility | None = None
    calendar_evidence: FiscalCalendarEvidence | None = None

    @property
    def concept(self) -> Concept:
        return self.operands[0].concept

    @property
    def unit(self) -> UnitSpec:
        return self.operands[0].unit

    @property
    def scope(self) -> ScopeSpec:
        return self.operands[0].scope

    @property
    def history_key(self) -> tuple[object, ...]:
        return self.operands[0].history_key

    @property
    def reporting_basis(self) -> str | None:
        return self.operands[0].selection.reporting_basis

    @property
    def statement_family(self) -> str:
        return self.operands[0].selection.query.statement_family

    @property
    def assembly_key(self) -> tuple[object, ...]:
        return (
            self.formula_id,
            self.formula_revision,
            self.calendar_evidence.comparison_key if self.calendar_evidence else None,
            tuple(
                (
                    source.period.start_date,
                    source.period.end_date,
                    coefficient,
                    tuple(sorted(source.selection.filing_version_ids, key=str)),
                )
                for source, coefficient in zip(self.operands, self.coefficients, strict=True)
            ),
        )

    @property
    def blocking_flags(self) -> tuple[str, ...]:
        return tuple(
            flag for flag in self.flags if flag not in {"revised_view", "earliest_available"}
        )


_SUPPORTED_FLOWS = frozenset(
    {
        Concept.REVENUE,
        Concept.COST_OF_REVENUE,
        Concept.GROSS_PROFIT,
        Concept.OPERATING_INCOME,
        Concept.NET_INCOME_CONSOLIDATED,
        Concept.CASH_FROM_OPERATING_ACTIVITIES,
        Concept.CAPITAL_EXPENDITURES_PPE,
    }
)


def _month_span(source: FinancialInput) -> int | None:
    start, end = source.period.start_date, source.period.end_date
    if (
        source.period.period_kind != "duration"
        or type(start) is not date
        or type(end) is not date
        or start > end
        or start.day != 1
        or end.day != calendar.monthrange(end.year, end.month)[1]
    ):
        return None
    return (end.year - start.year) * 12 + end.month - start.month + 1


def _problems(operands: tuple[FinancialInput, ...]) -> set[str]:
    problems = _issues(operands, (operands[0].concept,) * len(operands), same_period=False)
    if any(source.concept not in _SUPPORTED_FLOWS for source in operands):
        problems.add("unsupported_period_concept")
    if any(
        source.concept == Concept.CAPITAL_EXPENDITURES_PPE
        and source.value is not None
        and source.value.is_finite()
        and source.value < 0
        for source in operands
    ):
        problems.add("negative_cash_ppe_capex")
    if len({(item.scope.id, item.scope.content_sha256) for item in operands}) != 1:
        problems.add("incompatible_period_scope")
    observation_ids = tuple(
        identifier
        for source in operands
        if source.fact is not None
        for identifier in source.fact.observation_ids
    )
    if len(observation_ids) != len(set(observation_ids)):
        problems.add("duplicate_period_observation")
    return problems


def annual_amount(
    source: FinancialInput, *, calendar_evidence: FiscalCalendarEvidence | None = None
) -> PeriodAmount:
    problems = _problems((source,))
    if calendar_evidence is not None:
        problems.update(calendar_evidence.problems((source,)))
        match = calendar_evidence.match(source, cumulative=True)
        annual = match is not None and match[1] == 4
    else:
        annual = _month_span(source) == 12
    if not annual:
        problems.add("unsupported_annual_period")
    return PeriodAmount(
        None if problems else source.value,
        (source,),
        (1,),
        PeriodWindow(source.period.start_date, source.period.end_date),
        source.precision,
        tuple(sorted(set(source.flags) | problems)),
        "direct_annual",
        calendar_evidence=calendar_evidence,
    )


def _exact_sum(values: tuple[Decimal, ...], coefficients: tuple[int, ...]) -> Decimal:
    if any(
        not value.is_finite()
        or len(value.as_tuple().digits) > 1000
        or not isinstance(value.as_tuple().exponent, int)
        or abs(int(value.as_tuple().exponent)) > 1000
        or abs(value.adjusted()) > 1000
        for value in values
    ):
        raise ValueError("Unsupported numeric range")
    precision = max(
        50,
        max(value.adjusted() for value in values)
        - min(int(value.as_tuple().exponent) for value in values)
        + 4,
    )
    context = Context(prec=precision, Emin=-9999, Emax=9999)
    context.traps[Inexact] = True
    with localcontext(context):
        return sum(
            (
                value if coefficient == 1 else value.copy_negate()
                for value, coefficient in zip(values, coefficients, strict=True)
            ),
            Decimal(0),
        )


def _assemble(
    sources: tuple[FinancialInput, ...],
    coefficients: tuple[int, ...],
    window: PeriodWindow,
    formula: str,
    problems: set[str],
    revision_compatibility: RevisionCompatibility | None = None,
    calendar_evidence: FiscalCalendarEvidence | None = None,
) -> PeriodAmount:
    flags = set(problems) | {flag for source in sources for flag in source.flags}
    value = None
    precision = None
    if not problems:
        values = tuple(source.value for source in sources if source.value is not None)
        precisions = tuple(source.precision for source in sources if source.precision is not None)
        try:
            value = _exact_sum(values, coefficients)
            if len(precisions) == len(sources):
                precision = PrecisionEvidence(
                    _exact_sum(
                        tuple(item.absolute_error for item in precisions), (1,) * len(precisions)
                    ),
                    tuple(
                        sorted(
                            {
                                identifier
                                for item in precisions
                                for identifier in item.observation_ids
                            },
                            key=str,
                        )
                    ),
                    tuple(sorted({ref for item in precisions for ref in item.evidence_refs})),
                    "sum_absolute_errors:s5-period-amounts-v1",
                )
        except (DecimalException, ValueError):
            value = None
            precision = None
            flags.add("unsupported_numeric_range")
    if sources[0].concept == Concept.CAPITAL_EXPENDITURES_PPE and value is not None and value < 0:
        value = None
        flags.add("negative_cash_ppe_capex")
    return PeriodAmount(
        value,
        sources,
        coefficients,
        window,
        precision,
        tuple(sorted(flags)),
        formula,
        revision_compatibility=revision_compatibility,
        calendar_evidence=calendar_evidence,
    )


def _revision_problems(
    sources: tuple[FinancialInput, ...],
    proof: RevisionCompatibility | None,
) -> set[str]:
    if proof is not None:
        if set(proof.input_hashes) != {source.selection.input_hash for source in sources}:
            return {"revision_compatibility_mismatch"}
        return set()
    if len({source.selection.filing_version_ids for source in sources}) != 1:
        return {"revision_compatibility_unproven"}
    return set()


def ttm_from_quarters(
    sources: tuple[FinancialInput, ...],
    *,
    revision_compatibility: RevisionCompatibility | None = None,
    calendar_evidence: FiscalCalendarEvidence | None = None,
) -> PeriodAmount:
    if not isinstance(sources, tuple) or not sources:
        raise ValueError("A nonempty immutable tuple of quarterly source inputs is required")
    problems = _problems(sources) | _revision_problems(sources, revision_compatibility)
    if len(sources) != 4:
        problems.add("four_quarters_required")
    if calendar_evidence is not None:
        problems.update(calendar_evidence.problems(sources))
        if any(calendar_evidence.match(source, cumulative=False) is None for source in sources):
            problems.add("unsupported_quarter_period")
    elif any(
        _month_span(source) != 3
        or source.period.start_date is None
        or source.period.start_date.month not in {1, 4, 7, 10}
        for source in sources
    ):
        problems.add("unsupported_quarter_period")
    if not problems and any(
        right.period.start_date is None
        or left.period.end_date.toordinal() + 1 != right.period.start_date.toordinal()
        for left, right in zip(sources, sources[1:], strict=False)
    ):
        problems.add("noncontiguous_quarters")
    return _assemble(
        sources,
        (1,) * len(sources),
        PeriodWindow(sources[0].period.start_date, sources[-1].period.end_date),
        "sum_four_quarters",
        problems,
        revision_compatibility,
        calendar_evidence,
    )


def quarter_from_ytd(
    current: FinancialInput,
    prior: FinancialInput,
    *,
    calendar_evidence: FiscalCalendarEvidence | None = None,
) -> PeriodAmount:
    """Derive one fiscal quarter from two same-edition cumulative amounts."""
    sources = (current, prior)
    problems = _problems(sources)
    current_span, prior_span = _month_span(current), _month_span(prior)
    valid_periods = (
        current_span in {6, 9, 12}
        and prior_span in {3, 6, 9}
        and current_span is not None
        and prior_span is not None
        and current_span - prior_span == 3
        and current.period.start_date == prior.period.start_date
    )
    if calendar_evidence is not None:
        problems.update(calendar_evidence.problems(sources))
        current_label = calendar_evidence.match(current, cumulative=True)
        prior_label = calendar_evidence.match(prior, cumulative=True)
        valid_periods = (
            current_label is not None
            and prior_label is not None
            and current_label[0] == prior_label[0]
            and current_label[1] == prior_label[1] + 1
        )
    if not valid_periods:
        problems.add("incompatible_ytd_periods")
    if current.selection.filing_version_ids != prior.selection.filing_version_ids:
        problems.add("incompatible_filing_editions")
    start = prior.period.end_date + timedelta(days=1) if valid_periods else None
    return _assemble(
        sources,
        (1, -1),
        PeriodWindow(start, current.period.end_date),
        "ytd_difference",
        problems,
        calendar_evidence=calendar_evidence,
    )


def ttm_from_annual_ytd(
    annual: FinancialInput,
    current_ytd: FinancialInput,
    prior_ytd: FinancialInput,
    *,
    revision_compatibility: RevisionCompatibility | None = None,
    calendar_evidence: FiscalCalendarEvidence | None = None,
) -> PeriodAmount:
    """Annual plus current fiscal YTD less the comparable prior fiscal YTD."""
    sources = (annual, current_ytd, prior_ytd)
    problems = _problems(sources) | _revision_problems(sources, revision_compatibility)
    current_span = _month_span(current_ytd)
    valid_periods = (
        _month_span(annual) == 12
        and current_span in {3, 6, 9}
        and _month_span(prior_ytd) == current_span
        and prior_ytd.period.start_date == annual.period.start_date
        and type(annual.period.end_date) is date
        and annual.period.end_date < date.max
        and annual.period.end_date + timedelta(days=1) == current_ytd.period.start_date
    )
    if calendar_evidence is not None:
        problems.update(calendar_evidence.problems(sources))
        a = calendar_evidence.match(annual, cumulative=True)
        c = calendar_evidence.match(current_ytd, cumulative=True)
        p = calendar_evidence.match(prior_ytd, cumulative=True)
        valid_periods = (
            a is not None
            and c is not None
            and p is not None
            and a[1] == 4
            and a[0] == p[0]
            and c[0] == a[0] + 1
            and c[1] == p[1]
            and c[1] in {1, 2, 3}
            and current_ytd.period.start_date is not None
            and annual.period.end_date.toordinal() + 1 == current_ytd.period.start_date.toordinal()
        )
    if not valid_periods:
        problems.add("incompatible_annual_ytd_periods")
    start = prior_ytd.period.end_date + timedelta(days=1) if valid_periods else None
    return _assemble(
        sources,
        (1, 1, -1),
        PeriodWindow(start, current_ytd.period.end_date),
        "annual_ytd_bridge",
        problems,
        revision_compatibility,
        calendar_evidence,
    )
