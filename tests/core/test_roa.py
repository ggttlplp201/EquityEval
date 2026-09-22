"""Hand-computed annual ROA with original flow and balance-sheet evidence."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import ROUND_DOWN, Decimal, Inexact, localcontext

import pytest
from equity_core.metrics import return_on_assets
from equity_schema.concepts import Concept

from tests.core.metric_fixtures import balance, operand


def inputs(
    income="10", opening="80", closing="120", *, start=date(2025, 1, 1), end=date(2025, 12, 31)
):
    from datetime import timedelta

    return (
        operand(Concept.NET_INCOME_CONSOLIDATED, income, start=start, end=end),
        balance(Concept.TOTAL_ASSETS, opening, end=start - timedelta(days=1)),
        balance(Concept.TOTAL_ASSETS, closing, end=end),
    )


@pytest.mark.parametrize("income,expected", [("10", "0.1"), ("-20", "-0.2"), ("0", "0")])
def test_roa_uses_average_assets_and_keeps_loss_and_zero(income, expected):
    sources = inputs(income)
    result = return_on_assets(*sources)
    assert result.value == Decimal(expected)  # Average (80 + 120) / 2 = 100.
    assert result.unit == "fraction"
    assert result.metric_id == "return_on_assets"
    assert result.operands == sources
    assert not result.flags
    assert result.formula_revision


def test_non_january_fiscal_year_and_leap_day_are_aligned_exactly():
    sources = inputs(start=date(2023, 4, 1), end=date(2024, 3, 31))
    assert return_on_assets(*sources).value == Decimal("0.1")


@pytest.mark.parametrize("index", [0, 1, 2])
def test_one_missing_operand_never_becomes_zero(index):
    values = ["10", "80", "120"]
    values[index] = None
    sources = inputs(*values)
    result = return_on_assets(*sources)
    assert result.value is None
    assert "source_input_unavailable" in result.flags
    assert result.operands == sources


@pytest.mark.parametrize("index", [1, 2])
@pytest.mark.parametrize(
    "value,precision,flag",
    [
        ("0", "0.5", "denominator_nonpositive"),
        ("-20", "0.5", "denominator_nonpositive"),
        ("80", None, "denominator_precision_unknown"),
        ("0.5", "0.5", "denominator_indistinguishable_from_zero"),
    ],
)
def test_each_endpoint_must_be_positive_at_its_own_precision(index, value, precision, flag):
    sources = list(inputs())
    sources[index] = balance(
        Concept.TOTAL_ASSETS, value, end=sources[index].period.end_date, absolute_error=precision
    )
    result = return_on_assets(*sources)
    assert result.value is None and flag in result.flags


@pytest.mark.parametrize(
    "change,flag",
    [
        ("opening_date", "incompatible_balance_dates"),
        ("closing_date", "incompatible_balance_dates"),
        ("swapped", "incompatible_balance_dates"),
        ("quarter", "unsupported_annual_period"),
        ("ytd", "unsupported_annual_period"),
        ("weeks", "unsupported_annual_period"),
        ("duration_balance", "instant_period_required"),
        ("instant_income", "flow_period_required"),
        ("parent_income", "unexpected_concept"),
        ("current_assets", "unexpected_concept"),
        ("currency", "incompatible_units"),
        ("income_edition", "incompatible_filing_editions"),
        ("opening_edition", "incompatible_filing_editions"),
        ("history", "incompatible_history_policy"),
        ("basis", "incompatible_reporting_basis"),
        ("family", "incompatible_statement_family"),
        ("quality", "blocking_quality_flag"),
    ],
)
def test_plausible_roa_is_rejected_when_source_context_is_incompatible(change, flag):
    income, opening, closing = inputs()
    if change == "opening_date":
        opening = balance(Concept.TOTAL_ASSETS, "80", end=date(2025, 1, 1))
    elif change == "closing_date":
        closing = balance(Concept.TOTAL_ASSETS, "120", end=date(2025, 12, 30))
    elif change == "swapped":
        opening, closing = closing, opening
    elif change in {"quarter", "ytd", "weeks"}:
        end = {"quarter": date(2025, 3, 31), "ytd": date(2025, 9, 30), "weeks": date(2025, 12, 30)}[
            change
        ]
        income, opening, closing = inputs(end=end)
    elif change == "duration_balance":
        opening = operand(Concept.TOTAL_ASSETS, "80")
    elif change == "instant_income":
        income = balance(Concept.NET_INCOME_CONSOLIDATED, "10")
    elif change == "parent_income":
        income = operand(Concept.NET_INCOME_PARENT, "10")
    elif change == "current_assets":
        closing = balance(Concept.CURRENT_ASSETS, "120")
    elif change == "currency":
        income = operand(Concept.NET_INCOME_CONSOLIDATED, "10", currency="EUR")
    elif change == "income_edition":
        income = operand(Concept.NET_INCOME_CONSOLIDATED, "10", edition="other-edition")
    elif change == "opening_edition":
        opening = balance(
            Concept.TOTAL_ASSETS, "80", end=opening.period.end_date, edition="other-edition"
        )
    elif change == "history":
        query = replace(income.selection.query, captured_before=datetime(2026, 3, 2, tzinfo=UTC))
        income = replace(income, selection=replace(income.selection, query=query))
    elif change == "basis":
        income = replace(income, selection=replace(income.selection, reporting_basis="ifrs"))
    elif change == "family":
        query = replace(income.selection.query, statement_family="balance_sheet")
        income = replace(income, selection=replace(income.selection, query=query))
    elif change == "quality":
        closing = balance(Concept.TOTAL_ASSETS, "120", flags=("blocking_quality_flag",))
    result = return_on_assets(income, opening, closing)
    assert result.value is None and flag in result.flags


def test_income_needs_no_denominator_precision_and_does_not_get_relabelled():
    income, opening, closing = inputs()
    income = replace(income, precision=None)
    assert return_on_assets(income, opening, closing).value == Decimal("0.1")
    assert income.precision is None


def test_decimal_context_cannot_round_asset_average_before_division():
    sources = inputs("10", "81", "120")
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        result = return_on_assets(*sources)
    # 10 / 100.5 = 20 / 201, rounded only at the existing 50-digit ratio boundary.
    assert result.value == Decimal("0.099502487562189054726368159203980099502487562189055")


def test_unrepresentable_asset_average_is_missing_instead_of_silently_rounded():
    result = return_on_assets(*inputs("10", "1E+60", "1"))
    assert result.value is None and "unsupported_numeric_range" in result.flags


def test_minimum_date_does_not_underflow_during_endpoint_validation():
    source = operand(Concept.NET_INCOME_CONSOLIDATED, "10", start=date.min, end=date(1, 12, 31))
    _, opening, closing = inputs()
    result = return_on_assets(source, opening, closing)
    assert result.value is None and "incompatible_balance_dates" in result.flags
