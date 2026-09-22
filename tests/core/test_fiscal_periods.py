"""Reviewed fictional fiscal calendars; no real issuer calendar is inferred."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from equity_core.company import evidence_from_operand
from equity_core.fiscal import FiscalCalendarEvidence, FiscalYear
from equity_core.metrics import operating_margin
from equity_core.periods import (
    annual_amount,
    quarter_from_ytd,
    ttm_from_annual_ytd,
    ttm_from_quarters,
)
from equity_schema.concepts import Concept

from tests.core.metric_fixtures import identity, operand


def fiscal_year(start=date(2024, 12, 29), weeks=(13, 13, 13, 14), label="FY25"):
    end = start - timedelta(days=1)
    ends = []
    for count in weeks:
        end += timedelta(weeks=count)
        ends.append(end)
    return FiscalYear(label, start, tuple(ends), "weeks")


def proof(sources, years):
    return FiscalCalendarEvidence(
        identity("issuer"),
        years,
        tuple(sorted({s.selection.input_hash for s in sources})),
        date(2026, 2, 1),
        datetime(2026, 2, 2, tzinfo=UTC),
        ("synthetic:filing-fiscal-calendar",),
        "synthetic-calendar-v1",
    )


def fiscal_quarters(year, concept=Concept.REVENUE):
    starts = (year.start, *(end + timedelta(days=1) for end in year.quarter_ends[:-1]))
    return tuple(
        operand(concept, str(10 * (i + 1)), start=start, end=end)
        for i, (start, end) in enumerate(zip(starts, year.quarter_ends, strict=True))
    )


@pytest.mark.parametrize("weeks", [(13, 13, 13, 13), (13, 13, 13, 14), (14, 13, 13, 13)])
def test_reviewed_week_year_annual_and_four_quarter_totals(weeks):
    year = fiscal_year(weeks=weeks)
    qs = fiscal_quarters(year)
    annual = operand(Concept.REVENUE, "100", start=year.start, end=year.quarter_ends[-1])
    assert annual_amount(annual).value is None
    result = annual_amount(annual, calendar_evidence=proof((annual,), (year,)))
    assert result.value == Decimal("100")
    assert result.operands == (annual,)
    result = ttm_from_quarters(qs, calendar_evidence=proof(qs, (year,)))
    assert result.value == Decimal("100")  # 10 + 20 + 30 + 40; no day scaling.
    assert result.precision.absolute_error == Decimal("2")
    assert evidence_from_operand(result).usable
    assert result.calendar_evidence.years == (year,)


def test_non_january_month_quarters_require_explicit_fiscal_calendar():
    year = FiscalYear(
        "FY25",
        date(2024, 11, 1),
        (date(2025, 1, 31), date(2025, 4, 30), date(2025, 7, 31), date(2025, 10, 31)),
        "months",
    )
    qs = fiscal_quarters(year)
    assert ttm_from_quarters(qs).value is None
    assert ttm_from_quarters(qs, calendar_evidence=proof(qs, (year,))).value == Decimal("100")


def test_week_ytd_subtraction_and_annual_bridge_retain_coefficients():
    first = fiscal_year(date(2023, 12, 31), (13, 13, 13, 13), "FY24")
    second = fiscal_year()
    annual = operand(Concept.REVENUE, "100", start=first.start, end=first.quarter_ends[-1])
    prior = operand(Concept.REVENUE, "20", start=first.start, end=first.quarter_ends[0])
    current = operand(Concept.REVENUE, "30", start=second.start, end=second.quarter_ends[0])
    sources = (annual, current, prior)
    result = ttm_from_annual_ytd(*sources, calendar_evidence=proof(sources, (first, second)))
    assert result.value == Decimal("110")  # 100 + 30 - 20, not 150.
    assert result.coefficients == (1, 1, -1)
    assert result.precision.absolute_error == Decimal("1.5")
    assert evidence_from_operand(result).usable
    cumulative = operand(Concept.REVENUE, "75", start=second.start, end=second.quarter_ends[1])
    q2 = quarter_from_ytd(
        cumulative, current, calendar_evidence=proof((cumulative, current), (second,))
    )
    assert q2.value == Decimal("45")
    assert q2.period.start_date == second.quarter_ends[0] + timedelta(days=1)
    assert q2.precision.absolute_error == Decimal("1")
    assert evidence_from_operand(q2).usable


@pytest.mark.parametrize(
    "change", ["issuer", "hash", "known", "captured", "transition", "bad_weeks"]
)
def test_calendar_cannot_bypass_source_identity_pit_or_unsupported_year(change):
    year = fiscal_year()
    qs = fiscal_quarters(year)
    calendar = proof(qs, (year,))
    if change == "issuer":
        calendar = replace(calendar, issuer_id=identity("different-issuer"))
    elif change == "hash":
        calendar = replace(calendar, input_hashes=("b" * 64,))
    elif change == "known":
        calendar = replace(
            calendar, known_on=date(2026, 3, 2), captured_at=datetime(2026, 3, 2, tzinfo=UTC)
        )
    elif change == "captured":
        calendar = replace(calendar, captured_at=datetime(2026, 3, 2, tzinfo=UTC))
    elif change == "transition":
        calendar = replace(calendar, years=(replace(year, kind="transition"),))
    else:
        calendar = replace(
            calendar,
            years=(
                replace(
                    year,
                    quarter_ends=(
                        *year.quarter_ends[:3],
                        year.quarter_ends[-1] + timedelta(days=1),
                    ),
                ),
            ),
        )
    result = ttm_from_quarters(qs, calendar_evidence=calendar)
    assert result.value is None
    assert result.calendar_evidence == calendar
    assert result.operands == qs


@pytest.mark.parametrize(
    "change", ["gap", "overlap", "order", "missing", "edition", "currency", "precision"]
)
def test_reviewed_calendar_does_not_relax_existing_input_guards(change):
    year = fiscal_year()
    qs = fiscal_quarters(year)
    if change == "order":
        qs = (qs[1], qs[0], *qs[2:])
    elif change == "overlap":
        qs = (qs[0], qs[0], *qs[2:])
    else:
        old = qs[-1]
        kwargs = {"start": old.period.start_date, "end": old.period.end_date}
        if change == "gap":
            kwargs["start"] += timedelta(days=1)
        if change == "edition":
            kwargs["edition"] = "different"
        if change == "currency":
            kwargs["currency"] = "EUR"
        if change == "precision":
            kwargs["absolute_error"] = None
        qs = (*qs[:-1], operand(Concept.REVENUE, None if change == "missing" else "40", **kwargs))
    result = ttm_from_quarters(qs, calendar_evidence=proof(qs, (year,)))
    if change == "precision":
        assert result.value == Decimal("100")
        assert result.precision is None
    else:
        assert result.value is None


def test_matching_fiscal_assemblies_integrate_with_margin_and_reject_other_calendar():
    year = fiscal_year()
    rev = fiscal_quarters(year)
    income = fiscal_quarters(year, Concept.OPERATING_INCOME)
    r = ttm_from_quarters(rev, calendar_evidence=proof(rev, (year,)))
    n = ttm_from_quarters(income, calendar_evidence=proof(income, (year,)))
    assert operating_margin(n, r).value == Decimal("1")
    other = replace(
        n, calendar_evidence=replace(n.calendar_evidence, review_revision="another-review")
    )
    assert operating_margin(other, r).value is None
    forged = replace(r, value=Decimal("999"))
    assert not evidence_from_operand(forged).usable


def test_irregular_transition_and_mismatched_ytd_do_not_become_annual_or_ttm():
    first = fiscal_year(date(2023, 12, 31), (13, 13, 13, 13), "FY24")
    second = fiscal_year()
    annual = operand(Concept.REVENUE, "100", start=first.start, end=first.quarter_ends[-1])
    prior = operand(Concept.REVENUE, "20", start=first.start, end=first.quarter_ends[0])
    current = operand(Concept.REVENUE, "70", start=second.start, end=second.quarter_ends[1])
    sources = (annual, current, prior)
    assert (
        ttm_from_annual_ytd(*sources, calendar_evidence=proof(sources, (first, second))).value
        is None
    )
    assert (
        quarter_from_ytd(
            current, prior, calendar_evidence=proof((current, prior), (first, second))
        ).value
        is None
    )


def test_calendar_structure_requires_immutable_evidence_and_ordered_years():
    year = fiscal_year()
    qs = fiscal_quarters(year)
    base = proof(qs, (year,))
    for patch in (
        {"evidence_refs": ()},
        {"years": [year]},
        {"years": (year, year)},
        {"input_hashes": ("not-a-hash",)},
        {"captured_at": datetime(2026, 2, 2)},
        {"review_revision": ""},
    ):
        with pytest.raises(ValueError):
            replace(base, **patch)


def test_fiscal_growth_requires_equal_exposure_and_reviewed_editions():
    from equity_core.metrics import revenue_growth
    from equity_core.periods import RevisionCompatibility

    previous = fiscal_year(date(2023, 12, 31), (13, 13, 13, 13), "FY24")
    current = fiscal_year()
    old = operand(
        Concept.REVENUE, "100", start=previous.start, end=previous.quarter_ends[0], edition="old"
    )
    new = operand(Concept.REVENUE, "120", start=current.start, end=current.quarter_ends[0])
    calendar = proof((new, old), (previous, current))
    blocked = revenue_growth(new, old, calendar_evidence=calendar)
    assert blocked.value is None
    revision = RevisionCompatibility(
        (new.selection.input_hash, old.selection.input_hash), ("synthetic:revision-check",), "v1"
    )
    result = revenue_growth(new, old, calendar_evidence=calendar, revision_compatibility=revision)
    assert result.value == Decimal("0.2")
    assert result.calendar_evidence == calendar
    assert result.revision_compatibility == revision
    old_annual = operand(
        Concept.REVENUE, "100", start=previous.start, end=previous.quarter_ends[-1]
    )
    new_annual = operand(Concept.REVENUE, "120", start=current.start, end=current.quarter_ends[-1])
    unequal = revenue_growth(
        new_annual,
        old_annual,
        calendar_evidence=proof((new_annual, old_annual), (previous, current)),
    )
    assert unequal.value is None
    assert "unsupported_comparison_periods" in unequal.flags


def test_growth_does_not_treat_revision_of_same_period_as_growth():
    from equity_core.metrics import revenue_growth

    year = fiscal_year()
    old, new = (
        operand(Concept.REVENUE, amount, start=year.start, end=year.quarter_ends[0])
        for amount in ("100", "120")
    )
    result = revenue_growth(new, old, calendar_evidence=proof((new, old), (year,)))
    assert result.value is None


def test_calendar_changes_remain_unsupported_even_with_nonoverlapping_dates():
    first = fiscal_year(date(2023, 12, 31), (13, 13, 13, 13), "FY24")
    second = FiscalYear(
        "FY25",
        date(2025, 1, 1),
        (date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31)),
        "months",
    )
    source = operand(Concept.REVENUE, "100")
    result = annual_amount(source, calendar_evidence=proof((source,), (first, second)))
    assert result.value is None
    assert "unsupported_fiscal_calendar" in result.flags
