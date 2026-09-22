"""Hand-calculated balance-sheet metrics over existing selected-source inputs."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import ROUND_DOWN, Decimal, Inexact, localcontext

import pytest
from equity_core.metrics import current_ratio, net_working_capital
from equity_ingest.financial_types import canonical_json, content_hash
from equity_schema.concepts import Concept

from tests.core.metric_fixtures import balance, operand


def pair(assets="150", liabilities="100", **kwargs):
    return (
        balance(Concept.CURRENT_ASSETS, assets, **kwargs),
        balance(Concept.CURRENT_LIABILITIES, liabilities, **kwargs),
    )


def test_current_ratio_and_working_capital_retain_same_date_sources():
    inputs = pair()
    ratio = current_ratio(*inputs)
    capital = net_working_capital(*inputs)
    assert ratio.value == Decimal("1.5")
    assert ratio.unit == "multiple"
    assert capital.value == Decimal("50")
    assert capital.unit == "USD"
    for result in (ratio, capital):
        assert result.operands == inputs
        assert not result.flags
        assert result.formula_revision


@pytest.mark.parametrize(
    "assets,liabilities,ratio,capital",
    [
        ("50", "100", "0.5", "-50"),
        ("0", "100", "0", "-100"),
        ("100", "0", None, "100"),
        ("0", "0", None, "0"),
    ],
)
def test_deficits_and_zero_balances_are_not_missing(assets, liabilities, ratio, capital):
    inputs = pair(assets, liabilities)
    r = current_ratio(*inputs)
    assert r.value == (Decimal(ratio) if ratio is not None else None)
    assert net_working_capital(*inputs).value == Decimal(capital)
    if ratio is None:
        assert "denominator_nonpositive" in r.flags


@pytest.mark.parametrize("function", [current_ratio, net_working_capital])
@pytest.mark.parametrize("missing", [0, 1])
def test_missing_balances_remain_missing(function, missing):
    inputs = pair(None if missing == 0 else "150", None if missing == 1 else "100")
    result = function(*inputs)
    assert result.value is None and "source_input_unavailable" in result.flags
    assert result.operands == inputs


@pytest.mark.parametrize("function", [current_ratio, net_working_capital])
@pytest.mark.parametrize("assets,liabilities", [("-1", "100"), ("150", "-1")])
def test_negative_reported_balance_is_flagged_without_correction(function, assets, liabilities):
    inputs = pair(assets, liabilities)
    result = function(*inputs)
    assert result.value is None and "negative_current_balance" in result.flags
    assert result.operands[0].fact.value == Decimal(assets)
    assert result.operands[1].fact.value == Decimal(liabilities)


def test_ratio_uses_existing_source_precision_guard_but_subtraction_needs_no_estimate():
    unknown = pair(absolute_error=None)
    assert current_ratio(*unknown).value is None
    assert "denominator_precision_unknown" in current_ratio(*unknown).flags
    assert net_working_capital(*unknown).value == Decimal("50")
    tiny = pair("150", "0.5")
    assert current_ratio(*tiny).value is None
    assert "denominator_indistinguishable_from_zero" in current_ratio(*tiny).flags
    assert net_working_capital(*tiny).value == Decimal("149.5")


@pytest.mark.parametrize("function", [current_ratio, net_working_capital])
@pytest.mark.parametrize(
    "change,flag",
    [
        ("currency", "incompatible_units"),
        ("date", "incompatible_periods"),
        ("edition", "incompatible_filing_editions"),
        ("history", "incompatible_history_policy"),
        ("basis", "incompatible_reporting_basis"),
        ("duration", "instant_period_required"),
        ("family", "incompatible_statement_family"),
        ("parent", "unsupported_semantic_scope"),
        ("concept", "unexpected_concept"),
        ("quality", "blocking_quality_flag"),
    ],
)
def test_plausible_numbers_with_incompatible_evidence_never_produce_a_ratio(function, change, flag):
    assets, liabilities = pair()
    if change == "currency":
        liabilities = balance(Concept.CURRENT_LIABILITIES, "100", currency="EUR")
    elif change == "date":
        liabilities = balance(Concept.CURRENT_LIABILITIES, "100", end=date(2024, 12, 31))
    elif change == "edition":
        liabilities = balance(Concept.CURRENT_LIABILITIES, "100", edition="other-edition")
    elif change == "history":
        query = replace(
            liabilities.selection.query, captured_before=datetime(2026, 3, 2, tzinfo=UTC)
        )
        liabilities = replace(liabilities, selection=replace(liabilities.selection, query=query))
    elif change == "basis":
        liabilities = replace(
            liabilities, selection=replace(liabilities.selection, reporting_basis="ifrs")
        )
    elif change == "duration":
        liabilities = operand(Concept.CURRENT_LIABILITIES, "100")
    elif change == "family":
        query = replace(liabilities.selection.query, statement_family="income")
        liabilities = replace(liabilities, selection=replace(liabilities.selection, query=query))
    elif change == "parent":
        import json

        descriptor = {**json.loads(liabilities.scope.descriptor_json), "consolidation": "parent"}
        liabilities = replace(
            liabilities,
            scope=replace(
                liabilities.scope,
                scope_kind="parent",
                descriptor_json=canonical_json(descriptor),
                content_sha256=content_hash(descriptor),
            ),
        )
    elif change == "concept":
        assets = balance(Concept.TOTAL_ASSETS, "150")
    elif change == "quality":
        liabilities = balance(Concept.CURRENT_LIABILITIES, "100", flags=("blocking_quality_flag",))
    result = function(assets, liabilities)
    assert result.value is None and flag in result.flags


def test_calculation_is_independent_of_callers_decimal_context():
    inputs = pair("100", "30")
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        assert current_ratio(*inputs).value == Decimal("3." + "3" * 49)
        assert net_working_capital(*inputs).value == Decimal("70")


def test_unrepresentable_working_capital_is_a_gap_not_rounded_zero():
    inputs = pair("1E+1000", "1")
    for result in (current_ratio(*inputs), net_working_capital(*inputs)):
        assert result.value is None and "unsupported_numeric_range" in result.flags
