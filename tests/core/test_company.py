"""Shared company calculations and evaluated evidence keep exact source lineage."""

from datetime import date
from decimal import Decimal

from equity_core.company import EvidenceValue, equity_multiple

AS_OF = date(2026, 3, 1)


def evidence(
    value,
    *,
    basis="consolidated_flow",
    error="0.5",
    start=date(2025, 1, 1),
    end=date(2025, 12, 31),
    input_hash="a" * 64,
):
    return EvidenceValue(
        Decimal(value) if value is not None else None,
        Decimal(error) if error is not None else None,
        input_hash,
        start,
        end,
        value is not None,
        basis=basis,
    )


def test_company_ps_uses_exact_cap_and_twelve_month_sales_evidence():
    cap = evidence("500", basis="common_equity", start=None, end=AS_OF, input_hash="b" * 64)
    sales = evidence("100")
    result = equity_multiple("ps", cap, sales, as_of=AS_OF)
    assert result.value == Decimal("5")
    assert result.usable
    assert result.metric_id == "ps"
    assert result.operand_hashes == (cap.input_hash, sales.input_hash)
    assert len(result.input_hash) == 64
    assert result == equity_multiple("ps", cap, sales, as_of=AS_OF)


def test_multiple_excludes_bad_denominators_without_erasing_raw_loss_amounts():
    from dataclasses import replace

    from equity_core.company import evidence_issues

    cap = evidence("500", basis="common_equity", start=None, end=AS_OF, input_hash="b" * 64)
    for value, error in (("0", "0.5"), ("-10", "0.5"), ("0.5", "0.5"), ("10", None), (None, "0.5")):
        income = evidence(value, basis="income_available_common", error=error)
        result = equity_multiple("pe", cap, income, as_of=AS_OF)
        assert result.value is None
        assert not result.usable
        assert result.flags
    loss = evidence("-10", basis="income_available_common")
    assert not evidence_issues(loss, basis="income_available_common", evaluation_date=AS_OF)
    zero = replace(loss, value=Decimal(0))
    assert not evidence_issues(zero, basis="income_available_common", evaluation_date=AS_OF)


def test_evidence_safeguards_reject_invalid_dates_basis_hash_currency_and_quality():
    from dataclasses import replace

    from equity_core.company import evidence_issues

    base = evidence("100")
    for amount in (
        replace(base, input_hash="unproven"),
        replace(base, currency="EUR"),
        replace(base, usable=False),
        replace(base, flags=("stale",)),
        replace(base, basis="income_available_common"),
        replace(base, value=Decimal("NaN")),
        replace(base, value=1.0),
        replace(base, absolute_error=Decimal("-1")),
        replace(base, period_end=date(2026, 4, 1)),
        replace(base, period_start=None),
        replace(base, period_start=date(2026, 1, 1)),
        replace(base, absolute_error=None),
    ):
        assert evidence_issues(amount, basis="consolidated_flow", evaluation_date=AS_OF)
    assert not evidence_issues(
        replace(base, absolute_error=None),
        basis="consolidated_flow",
        evaluation_date=AS_OF,
        require_precision=False,
    )
    assert not evidence_issues(
        replace(base, flags=("revised_view", "earliest_available", "extreme_margin")),
        basis="consolidated_flow",
        evaluation_date=AS_OF,
    )


def test_source_projection_preserves_ttm_lineage_precision_and_never_relabels_common_income():
    from dataclasses import replace

    from equity_core.company import evidence_from_operand
    from equity_core.periods import ttm_from_quarters
    from equity_schema.concepts import Concept

    from tests.core.metric_fixtures import operand

    sources = tuple(
        operand(Concept.REVENUE, value, start=start, end=end)
        for value, start, end in (
            ("10", date(2025, 1, 1), date(2025, 3, 31)),
            ("20", date(2025, 4, 1), date(2025, 6, 30)),
            ("30", date(2025, 7, 1), date(2025, 9, 30)),
            ("40", date(2025, 10, 1), date(2025, 12, 31)),
        )
    )
    amount = ttm_from_quarters(sources)
    result = evidence_from_operand(amount)
    assert result.value == Decimal("100")
    assert result.absolute_error == Decimal("2")
    assert result.usable
    assert result.period_start == date(2025, 1, 1)
    assert result.period_end == date(2025, 12, 31)
    assert result == evidence_from_operand(amount)
    assert (
        result.input_hash
        != evidence_from_operand(replace(amount, formula_revision="different")).input_hash
    )
    income = evidence_from_operand(operand(Concept.NET_INCOME_CONSOLIDATED, "20"))
    assert income.basis == "consolidated_flow"
    parent = evidence_from_operand(operand(Concept.NET_INCOME_PARENT, "20"))
    assert not parent.usable
    assert parent.value is None
    unknown = evidence_from_operand(operand(Concept.REVENUE, "100", absolute_error=None))
    assert unknown.usable
    assert unknown.absolute_error is None


def test_fcf_evidence_and_margin_projection_preserve_compound_numerator_lineage():
    from dataclasses import replace

    from equity_core.company import (
        evidence_from_fcf,
        evidence_from_operand,
        metric_from_calculation,
    )
    from equity_core.metrics import free_cash_flow, free_cash_flow_margin
    from equity_schema.concepts import Concept

    from tests.core.metric_fixtures import operand

    cfo = operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "12")
    capex = operand(Concept.CAPITAL_EXPENDITURES_PPE, "20")
    sales = operand(Concept.REVENUE, "100")
    fcf_calculation = free_cash_flow(cfo, capex)
    fcf = evidence_from_fcf(fcf_calculation)
    assert fcf.value == Decimal("-8")
    assert fcf.absolute_error == Decimal("1")
    assert fcf.usable and fcf.basis == "cash_ppe_fcf"
    margin = free_cash_flow_margin(cfo, capex, sales)
    revenue = evidence_from_operand(sales)
    result = metric_from_calculation(margin, "fcf_margin", (fcf, revenue))
    assert result.value == Decimal("-0.08")
    assert result.usable
    assert result.operand_hashes == (fcf.input_hash, revenue.input_hash)
    tampered = metric_from_calculation(
        margin, "fcf_margin", (replace(fcf, value=Decimal("8")), revenue)
    )
    assert not tampered.usable and tampered.value is None
    assert "calculation_operand_mismatch" in tampered.flags
    unknown = evidence_from_fcf(free_cash_flow(replace(cfo, precision=None), capex))
    assert unknown.value == Decimal("-8") and unknown.absolute_error is None


def test_multiple_never_mixes_point_dates_bases_or_short_periods_and_is_context_independent():
    from dataclasses import replace
    from decimal import ROUND_UP, Inexact, localcontext

    cap = evidence("500", basis="common_equity", start=None, end=AS_OF, input_hash="b" * 64)
    sales = evidence("100")
    for bad_cap, bad_sales, metric in (
        (replace(cap, period_end=date(2026, 2, 28)), sales, "ps"),
        (replace(cap, value=Decimal(0)), sales, "ps"),
        (replace(cap, period_start=date(2025, 1, 1)), sales, "ps"),
        (cap, replace(sales, period_start=date(2025, 10, 1)), "ps"),
        (cap, sales, "pe"),
        (cap, sales, "pfcf"),
        (cap, sales, "ev_ebitda"),
        (replace(cap, value=Decimal("1e1001")), sales, "ps"),
        (cap, replace(sales, value=Decimal("1e-1000"), absolute_error=Decimal(0)), "ps"),
    ):
        result = equity_multiple(metric, bad_cap, bad_sales, as_of=AS_OF)
        assert not result.usable
        assert result.value is None
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_UP
        context.traps[Inexact] = True
        result = equity_multiple("ps", cap, replace(sales, value=Decimal("300")), as_of=AS_OF)
    assert result.value == Decimal("1." + "6" * 48 + "7")
    assert result.usable


def test_metric_projection_rejects_wrong_alias_operand_and_preserves_unavailable_result():
    from dataclasses import replace

    from equity_core.company import evidence_from_operand, metric_from_calculation
    from equity_core.metrics import operating_margin, revenue_growth
    from equity_schema.concepts import Concept

    from tests.core.metric_fixtures import operand

    current = operand(Concept.REVENUE, "120")
    prior = operand(Concept.REVENUE, "100", start=date(2024, 1, 1), end=date(2024, 12, 31))
    inputs = (evidence_from_operand(current), evidence_from_operand(prior))
    calculation = revenue_growth(current, prior)
    result = metric_from_calculation(calculation, "revenue_yoy", inputs)
    assert result.value == Decimal("0.2") and result.usable
    assert not metric_from_calculation(calculation, "operating_margin", inputs).usable
    assert not metric_from_calculation(calculation, "revenue_yoy", tuple(reversed(inputs))).usable
    income = operand(Concept.OPERATING_INCOME, "-7270")
    unknown_sales = replace(current, precision=None)
    unavailable = operating_margin(income, unknown_sales)
    result = metric_from_calculation(
        unavailable,
        "operating_margin",
        (evidence_from_operand(income), evidence_from_operand(unknown_sales)),
    )
    assert result.value is None and not result.usable
    assert "denominator_precision_unknown" in result.flags


def test_projection_detects_changed_period_values_and_changed_fcf_calculation():
    from dataclasses import replace

    from equity_core.company import evidence_from_fcf, evidence_from_operand
    from equity_core.metrics import free_cash_flow
    from equity_core.periods import annual_amount
    from equity_schema.concepts import Concept

    from tests.core.metric_fixtures import operand

    annual = annual_amount(operand(Concept.REVENUE, "100"))
    changed = evidence_from_operand(replace(annual, value=Decimal("200")))
    assert changed.value is None and not changed.usable
    assert "period_projection_mismatch" in changed.flags
    cfo = operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "20")
    capex = operand(Concept.CAPITAL_EXPENDITURES_PPE, "5")
    calculation = free_cash_flow(cfo, capex)
    changed = evidence_from_fcf(replace(calculation, value=Decimal("100")))
    assert changed.value is None and not changed.usable
    assert "fcf_projection_mismatch" in changed.flags
