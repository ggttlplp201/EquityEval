"""Hand-calculated behavior, specified before source metric arithmetic."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from equity_core.metrics import operating_margin
from equity_ingest.financial_types import canonical_json, content_hash
from equity_schema.concepts import Concept

from tests.core.metric_fixtures import operand


def test_operating_margin_keeps_extreme_loss_and_both_operands():
    revenue = operand(Concept.REVENUE, "1000000")
    income = operand(Concept.OPERATING_INCOME, "-72700000")
    result = operating_margin(income, revenue)
    assert result.value == Decimal("-72.7")  # A fraction: -7,270%, not -72.7%.
    assert result.unit == "fraction"
    assert result.operands == (income, revenue)
    assert "extreme_margin" in result.flags
    assert result.formula_revision


@pytest.mark.parametrize(
    "amount,precision,reason",
    [
        ("0", "0.5", "denominator_nonpositive"),
        ("-10", "0.5", "denominator_nonpositive"),
        (None, None, "source_input_unavailable"),
        ("100", None, "denominator_precision_unknown"),
        ("0.5", "0.5", "denominator_indistinguishable_from_zero"),
    ],
)
def test_margin_does_not_rank_unsuitable_or_unknown_denominators(amount, precision, reason):
    revenue = operand(Concept.REVENUE, amount, absolute_error=precision)
    result = operating_margin(operand(Concept.OPERATING_INCOME, "10"), revenue)
    assert result.value is None
    assert reason in result.flags
    assert result.operands[1] == revenue


@pytest.mark.parametrize(
    "change,reason",
    [
        ("currency", "incompatible_units"),
        ("period", "incompatible_periods"),
        ("edition", "incompatible_filing_editions"),
        ("history", "incompatible_history_policy"),
        ("basis", "incompatible_reporting_basis"),
        ("parent", "unsupported_semantic_scope"),
        ("wrong_concept", "unexpected_concept"),
    ],
)
def test_margin_rejects_plausible_numbers_from_incompatible_evidence(change, reason):
    revenue = operand(Concept.REVENUE, "100")
    income = operand(Concept.OPERATING_INCOME, "10")
    if change == "currency":
        income = operand(Concept.OPERATING_INCOME, "10", currency="EUR")
    elif change == "period":
        income = operand(
            Concept.OPERATING_INCOME, "10", start=date(2024, 1, 1), end=date(2024, 12, 31)
        )
    elif change == "edition":
        income = operand(Concept.OPERATING_INCOME, "10", edition="later-revision")
    elif change == "history":
        query = replace(income.selection.query, captured_before=datetime(2026, 3, 2, tzinfo=UTC))
        income = replace(income, selection=replace(income.selection, query=query))
    elif change == "basis":
        income = replace(income, selection=replace(income.selection, reporting_basis="ifrs"))
    elif change == "parent":
        import json

        descriptor = {**json.loads(income.scope.descriptor_json), "consolidation": "parent"}
        income = replace(
            income,
            scope=replace(
                income.scope,
                scope_kind="parent",
                descriptor_json=canonical_json(descriptor),
                content_sha256=content_hash(descriptor),
            ),
        )
    elif change == "wrong_concept":
        income = operand(Concept.NET_INCOME_PARENT, "10")
    result = operating_margin(income, revenue)
    assert result.value is None
    assert reason in result.flags


def test_margin_preserves_a_blocking_source_failure_and_its_raw_amount():
    income = operand(Concept.OPERATING_INCOME, "10", flags=("blocking_quality_flag",))
    result = operating_margin(income, operand(Concept.REVENUE, "100"))
    assert result.value is None
    assert "blocking_quality_flag" in result.flags
    assert result.operands[0].fact.value == Decimal("10")


def test_cash_ppe_free_cash_flow_preserves_distinct_cash_scopes():
    from equity_core.metrics import free_cash_flow, free_cash_flow_margin

    cfo = operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "12000000")
    capex = operand(Concept.CAPITAL_EXPENDITURES_PPE, "20000000")
    revenue = operand(Concept.REVENUE, "100000000")
    assert cfo.scope.id != capex.scope.id
    result = free_cash_flow(cfo, capex)
    assert result.value == Decimal("-8000000")
    assert result.unit == "USD"
    assert result.operands == (cfo, capex)
    assert free_cash_flow_margin(cfo, capex, revenue).value == Decimal("-0.08")


@pytest.mark.parametrize("capex,expected", [("0", "12000000"), (None, None), ("-20", None)])
def test_capex_zero_missing_and_anomalous_sign_are_distinct(capex, expected):
    from equity_core.metrics import free_cash_flow

    result = free_cash_flow(
        operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "12000000"),
        operand(Concept.CAPITAL_EXPENDITURES_PPE, capex),
    )
    assert result.value == (Decimal(expected) if expected is not None else None)
    if capex == "-20":
        assert "negative_cash_ppe_capex" in result.flags
    if capex is None:
        assert "source_input_unavailable" in result.flags


def test_reported_and_derived_gross_profit_keep_different_lineage():
    from equity_core.metrics import derived_gross_margin, gross_margin, net_margin, reported_amount

    revenue = operand(Concept.REVENUE, "100")
    gross = operand(Concept.GROSS_PROFIT, "40")
    cost = operand(Concept.COST_OF_REVENUE, "60")
    direct = gross_margin(gross, revenue)
    derived = derived_gross_margin(revenue, cost)
    assert direct.value == derived.value == Decimal("0.4")
    assert direct.operands == (gross, revenue)
    assert derived.operands == (revenue, cost)
    assert "gross_profit_derived" in derived.flags
    assert direct.metric_id != derived.metric_id
    assert gross_margin(operand(Concept.GROSS_PROFIT, None), revenue).value is None
    assert net_margin(operand(Concept.NET_INCOME_CONSOLIDATED, "10"), revenue).value == Decimal(
        "0.1"
    )
    assert net_margin(operand(Concept.NET_INCOME_PARENT, "10"), revenue).value is None
    unprecise = operand(Concept.REVENUE, "100", absolute_error=None)
    assert reported_amount(unprecise).value == Decimal("100")
    assert reported_amount(unprecise).unit == "USD"


@pytest.mark.parametrize(
    "start,end,prior_start,prior_end,expected",
    [
        (date(2025, 1, 1), date(2025, 12, 31), date(2024, 1, 1), date(2024, 12, 31), "0.25"),
        (date(2025, 1, 1), date(2025, 3, 31), date(2024, 1, 1), date(2024, 3, 31), "0.25"),
        (date(2025, 1, 1), date(2025, 6, 30), date(2024, 1, 1), date(2024, 6, 30), None),
        (date(2025, 1, 1), date(2025, 3, 31), date(2023, 1, 1), date(2023, 3, 31), None),
        (date(2024, 9, 29), date(2025, 9, 27), date(2023, 10, 1), date(2024, 9, 28), None),
    ],
)
def test_revenue_growth_uses_comparable_periods_without_guessing_fiscal_alignment(
    start, end, prior_start, prior_end, expected
):
    from equity_core.metrics import revenue_growth

    current = operand(Concept.REVENUE, "125", start=start, end=end)
    prior = operand(Concept.REVENUE, "100", start=prior_start, end=prior_end, edition="prior")
    result = revenue_growth(current, prior)
    assert result.value == (Decimal(expected) if expected is not None else None)
    assert result.operands == (current, prior)
    if expected is None:
        assert "unsupported_comparison_periods" in result.flags


@pytest.mark.parametrize("prior", ["0", "-100", None])
def test_growth_has_no_percentage_for_nonpositive_or_missing_base(prior):
    from equity_core.metrics import revenue_growth

    result = revenue_growth(
        operand(Concept.REVENUE, "125"),
        operand(Concept.REVENUE, prior, start=date(2024, 1, 1), end=date(2024, 12, 31)),
    )
    assert result.value is None
    assert result.flags


def test_ratio_is_independent_of_callers_decimal_context():
    from decimal import ROUND_DOWN, Inexact, localcontext

    income, revenue = operand(Concept.OPERATING_INCOME, "1"), operand(Concept.REVENUE, "3")
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        result = operating_margin(income, revenue)
    assert result.value == Decimal("0." + "3" * 50)


@pytest.mark.parametrize("amount", ["1E+1001", "1E-1001"])
def test_unsupported_magnitude_does_not_overflow_or_round_to_plausible_zero(amount):
    result = operating_margin(
        operand(Concept.OPERATING_INCOME, amount),
        operand(Concept.REVENUE, "1", absolute_error="0"),
    )
    assert result.value is None
    assert "unsupported_numeric_range" in result.flags


def test_monetary_difference_does_not_silently_lose_source_digits():
    from equity_core.metrics import free_cash_flow

    result = free_cash_flow(
        operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "1E+60"),
        operand(Concept.CAPITAL_EXPENDITURES_PPE, "1"),
    )
    assert result.value is None
    assert "unsupported_numeric_range" in result.flags


def test_growth_retains_invalid_source_period_as_a_gap():
    from equity_core.metrics import revenue_growth

    current = operand(Concept.REVENUE, "120")
    prior = operand(Concept.REVENUE, "100", start=date(2024, 1, 1), end=date(2024, 12, 31))
    current = replace(current, period=replace(current.period, start_date="2025-01-01"))
    result = revenue_growth(current, prior)
    assert result.value is None
    assert "input_period_invalid" in result.flags
    assert "unsupported_comparison_periods" in result.flags


def test_existing_margins_accept_derived_period_amounts_without_rewriting_sources():
    from equity_core.periods import annual_amount

    revenue = annual_amount(operand(Concept.REVENUE, "100"))
    income = annual_amount(operand(Concept.OPERATING_INCOME, "20"))
    result = operating_margin(income, revenue)
    assert result.value == Decimal(".2")
    assert result.operands == (income, revenue)
    assert result.operands[0].operands[0].fact.value == Decimal("20")


def test_ttm_cash_metrics_reuse_calculations_and_keep_quarter_sources():
    from equity_core.metrics import free_cash_flow, free_cash_flow_margin
    from equity_core.periods import ttm_from_quarters

    def ttm(concept, value):
        return ttm_from_quarters(
            tuple(
                operand(concept, value, start=date(2025, month, 1), end=date(2025, month + 2, day))
                for month, day in ((1, 31), (4, 30), (7, 30), (10, 31))
            )
        )

    cfo, capex, revenue = (
        ttm(Concept.CASH_FROM_OPERATING_ACTIVITIES, "3"),
        ttm(Concept.CAPITAL_EXPENDITURES_PPE, "5"),
        ttm(Concept.REVENUE, "25"),
    )
    result = free_cash_flow(cfo, capex)
    assert result.value == Decimal("-8")
    assert free_cash_flow_margin(cfo, capex, revenue).value == Decimal("-.08")
    assert len(result.operands[0].operands) == 4
    assert cfo.scope.id != capex.scope.id


def test_same_dates_do_not_make_different_period_assemblies_compatible():
    from equity_core.periods import annual_amount, ttm_from_quarters

    income = annual_amount(operand(Concept.OPERATING_INCOME, "20"))
    revenue = ttm_from_quarters(
        tuple(
            operand(
                Concept.REVENUE, "25", start=date(2025, month, 1), end=date(2025, month + 2, day)
            )
            for month, day in ((1, 31), (4, 30), (7, 30), (10, 31))
        )
    )
    result = operating_margin(income, revenue)
    assert result.value is None
    assert "incompatible_period_assemblies" in result.flags
