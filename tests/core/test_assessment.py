"""Fictional explicit policies, never production profile or freshness defaults."""

from dataclasses import replace
from datetime import date
from decimal import ROUND_UP, Decimal, Inexact, localcontext

import pytest
from equity_core.assessment import (
    EvaluationContext,
    FreshnessPolicy,
    MetricApplicability,
    ProfilePolicy,
    coverage,
    evaluate,
    observations,
    review_items,
)
from equity_core.metrics import (
    Calculation,
    current_ratio,
    free_cash_flow,
    free_cash_flow_margin,
    net_margin,
    operating_margin,
    revenue_growth,
)
from equity_schema.concepts import Concept

from tests.core.metric_fixtures import balance, identity, operand


def context(*metric_ids, max_age=59, applicability=True, business="operating_company"):
    profile = ProfilePolicy(
        identity("issuer"),
        business,
        "established",
        "consolidated_issuer",
        "synthetic-profile-v1",
        date(2020, 1, 1),
        date(2020, 1, 1),
        ("synthetic:profile-review",),
        tuple(
            MetricApplicability(metric, applicability, "synthetic reviewed applicability")
            for metric in metric_ids
        ),
    )
    freshness = FreshnessPolicy("synthetic-age-v1", max_age, ("synthetic:age-policy",))
    return EvaluationContext(date(2026, 2, 28), profile, freshness)


def margin(income="20", revenue="100", **kwargs):
    return operating_margin(
        operand(Concept.OPERATING_INCOME, income, **kwargs),
        operand(Concept.REVENUE, revenue, **kwargs),
    )


def test_freshness_boundary_and_retained_stale_fact_do_not_change_source():
    calculation = margin()
    fresh = evaluate(calculation, context("operating_margin"))
    assert fresh.status == "valid"
    assert fresh.value == Decimal(".2")
    assert fresh.usable
    stale = evaluate(calculation, context("operating_margin", max_age=58))
    assert stale.status == "stale"
    assert stale.value == Decimal(".2")
    assert stale.calculation is calculation
    assert not stale.usable
    assert observations((stale,)) == ()
    assert review_items((stale,))[0].category == "data"
    assert calculation.operands[0].value == Decimal("20")


def test_expected_filing_deadline_is_explicit_and_checked_at_frozen_as_of():
    base = context("operating_margin")
    policy = replace(
        base.freshness, expected_period_end=date(2026, 1, 31), expected_by=date(2026, 2, 28)
    )
    on_due_date = evaluate(margin(), replace(base, freshness=policy))
    assert on_due_date.status == "valid"
    overdue = evaluate(
        margin(), replace(base, freshness=replace(policy, expected_by=date(2026, 2, 27)))
    )
    assert overdue.status == "stale"
    assert "expected_filing_missing" in overdue.reasons


@pytest.mark.parametrize(
    "revenue,precision,status",
    [
        ("0", ".5", "not_meaningful"),
        ("-1", ".5", "not_meaningful"),
        (".5", ".5", "not_meaningful"),
        ("100", None, "missing"),
        (None, ".5", "missing"),
    ],
)
def test_complete_nonmeaningful_inputs_count_as_covered_but_not_rankable(
    revenue, precision, status
):
    calc = operating_margin(
        operand(Concept.OPERATING_INCOME, "20"),
        operand(Concept.REVENUE, revenue, absolute_error=precision),
    )
    ctx = context("operating_margin")
    result = evaluate(calc, ctx)
    assert result.status == status
    assert result.value is None
    assert not result.usable
    summary = coverage((result,), context=ctx)
    assert summary.applicable_count == 1
    assert summary.covered_count == (1 if status == "not_meaningful" else 0)
    assert summary.coverage == Decimal(1 if status == "not_meaningful" else 0)
    assert not observations((result,))


def test_coverage_uses_policy_roster_and_cannot_hide_missing_metrics():
    ctx = context("operating_margin", "free_cash_flow_ppe", "return_on_equity")
    result = evaluate(margin(), ctx)
    summary = coverage((result,), context=ctx)
    assert summary.applicable_count == 3
    assert summary.covered_count == 1
    assert dict(summary.counts) == {
        "valid": 1,
        "not_meaningful": 0,
        "stale": 0,
        "missing": 1,
        "invalid": 0,
        "unsupported": 1,
        "inapplicable": 0,
    }
    assert summary.coverage == Decimal("0." + "3" * 50)
    with pytest.raises(ValueError):
        coverage((result, result), context=ctx)


def test_profile_not_source_availability_controls_applicability():
    calculation = margin()
    unreviewed = evaluate(
        calculation, context("operating_margin", applicability=None, business="bank")
    )
    assert unreviewed.status == "unsupported"
    assert unreviewed.value == Decimal(".2")
    assert not observations((unreviewed,))
    assert "profile_applicability_unreviewed" in unreviewed.reasons
    excluded_context = context("operating_margin", applicability=False, business="bank")
    excluded = evaluate(calculation, excluded_context)
    assert excluded.status == "inapplicable"
    assert coverage((excluded,), context=excluded_context).coverage is None
    assert coverage((unreviewed,), context=unreviewed.context).coverage is None
    missing = evaluate(margin(revenue=None), context("operating_margin"))
    assert missing.applicability is True
    assert coverage((missing,), context=missing.context).applicable_count == 1


@pytest.mark.parametrize(
    "patch",
    [
        "issuer",
        "future_profile",
        "future_effective",
        "future_cutoff",
        "altered_value",
        "unknown_formula",
        "unknown_metric",
        "flagged_source",
        "unit",
    ],
)
def test_unreviewed_or_edited_context_never_drives_financial_observations(patch):
    calc = margin()
    ctx = context("operating_margin")
    if patch == "issuer":
        ctx = replace(ctx, profile=replace(ctx.profile, issuer_id=identity("other")))
    elif patch == "future_profile":
        ctx = replace(ctx, profile=replace(ctx.profile, known_on=date(2026, 3, 1)))
    elif patch == "future_effective":
        ctx = replace(ctx, profile=replace(ctx.profile, effective_on=date(2026, 3, 1)))
    elif patch == "future_cutoff":
        ctx = replace(ctx, as_of=date(2026, 2, 27))
    elif patch == "altered_value":
        calc = replace(calc, value=Decimal(".9"))
    elif patch == "unknown_formula":
        calc = replace(calc, formula_revision="future")
    elif patch == "unknown_metric":
        calc = replace(calc, metric_id="return_on_equity")
        ctx = context("return_on_equity")
    elif patch == "flagged_source":
        calc = margin(flags=("accounting_mismatch",))
    else:
        calc = replace(calc, unit="USD")
    result = evaluate(calc, ctx)
    assert result.status in {"invalid", "unsupported"}
    assert not result.usable
    assert not observations((result,))


def test_f1_extreme_loss_and_cash_fixtures_are_neutral_and_exact():
    operating = margin("-72700000", "1000000")
    cfo = operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "12000000")
    capex = operand(Concept.CAPITAL_EXPENDITURES_PPE, "20000000")
    revenue = operand(Concept.REVENUE, "100000000")
    ctx = context("operating_margin", "free_cash_flow_ppe", "free_cash_flow_margin_ppe")
    results = tuple(
        evaluate(calc, ctx)
        for calc in (
            operating,
            free_cash_flow(cfo, capex),
            free_cash_flow_margin(cfo, capex, revenue),
        )
    )
    assert [item.value for item in results] == [
        Decimal("-72.7"),
        Decimal("-8000000"),
        Decimal("-.08"),
    ]
    assert all(item.status == "valid" for item in results)
    facts = observations(results)
    assert any(item.rule_id == "operating_loss" for item in facts)
    assert any(item.rule_id == "cash_spending_gap" for item in facts)
    prompts = review_items(results)
    assert len([item for item in prompts if item.topic == "cash_generation"]) == 1
    assert any(item.rule_id == "extreme_margin_review" for item in prompts)
    assert all(item.rule_revision and item.metrics for item in facts + prompts)
    assert not any(
        word in " ".join(item.text.lower() for item in facts + prompts)
        for word in ("buy", "sell", "bargain", "value trap", "overvalued", "bankrupt")
    )


def test_review_priority_deduplication_and_three_item_limit_are_stable():
    cfo = operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "12")
    capex = operand(Concept.CAPITAL_EXPENDITURES_PPE, "20")
    rev = operand(Concept.REVENUE, "100")
    calcs = (
        margin("-20"),
        net_margin(operand(Concept.NET_INCOME_CONSOLIDATED, "-10"), rev),
        free_cash_flow(cfo, capex),
        free_cash_flow_margin(cfo, capex, rev),
        current_ratio(
            balance(Concept.CURRENT_ASSETS, "10"), balance(Concept.CURRENT_LIABILITIES, None)
        ),
    )
    ctx = context(*(calc.metric_id for calc in calcs))
    results = tuple(evaluate(calc, ctx) for calc in calcs)
    prompts = review_items(results)
    assert len(prompts) == 3
    assert [p.category for p in prompts] == ["data", "cash", "operating"]
    assert prompts == review_items(tuple(reversed(results)))
    assert len({p.topic for p in prompts}) == len(prompts)


def test_growth_observation_keeps_negative_rate_without_multiple_or_value_judgment():
    calc = revenue_growth(
        operand(Concept.REVENUE, "88"),
        operand(Concept.REVENUE, "100", start=date(2024, 1, 1), end=date(2024, 12, 31)),
    )
    result = evaluate(calc, context("revenue_growth_yoy"))
    assert result.value == Decimal("-.12")
    assert observations((result,))[0].rule_id == "revenue_declined"


def test_coverage_and_numeric_evaluation_ignore_hostile_decimal_context():
    ctx = context("operating_margin", "gross_margin", "net_margin_consolidated")
    normal = evaluate(margin(), ctx)
    expected = coverage((normal,), context=ctx)
    with localcontext() as ambient:
        ambient.prec = 2
        ambient.rounding = ROUND_UP
        ambient.traps[Inexact] = True
        result = evaluate(margin(), ctx)
        actual = coverage((result,), context=ctx)
    assert actual == expected


def test_policy_input_validation_and_unsupported_arity_are_explicit():
    ctx = context("operating_margin")
    for patch in (
        {"max_age_days": -1},
        {"max_age_days": True},
        {"revision": ""},
        {"evidence_refs": ()},
        {"expected_by": date(2026, 2, 1)},
    ):
        with pytest.raises(ValueError):
            replace(ctx.freshness, **patch)
    with pytest.raises(ValueError):
        replace(ctx.profile, rules=(*ctx.profile.rules, ctx.profile.rules[0]))
    malformed = Calculation("operating_margin", Decimal(".2"), "fraction", ())
    assert evaluate(malformed, ctx).status == "invalid"


def test_profile_cannot_apply_company_metrics_to_unreviewed_instrument_basis():
    ctx = context("operating_margin")
    ctx = replace(ctx, profile=replace(ctx.profile, instrument_basis="direct_token"))
    result = evaluate(margin(), ctx)
    assert result.status == "unsupported"
    assert not observations((result,))


def test_period_projection_is_reproduced_before_assessment():
    from equity_core.periods import annual_amount

    income = annual_amount(operand(Concept.OPERATING_INCOME, "20"))
    revenue = annual_amount(operand(Concept.REVENUE, "100"))
    forged = replace(income, value=Decimal("90"))
    calculation = operating_margin(forged, revenue)
    assert calculation.value == Decimal(".9")  # Assessment must verify retained assembly inputs.
    result = evaluate(calculation, context("operating_margin"))
    assert result.status == "invalid"
    assert result.value is None
    assert "period_projection_mismatch" in result.reasons


def test_stale_nonmeaningful_source_does_not_inflate_current_coverage():
    ctx = context("operating_margin", max_age=1)
    result = evaluate(margin(revenue="0"), ctx)
    assert result.status == "stale"
    assert coverage((result,), context=ctx).covered_count == 0


@pytest.mark.parametrize(
    "change,status",
    [("missing", "missing"), ("irregular", "unsupported"), ("precision", "missing")],
)
def test_period_wrappers_preserve_natural_gap_classification(change, status):
    from equity_core.periods import annual_amount

    income = operand(Concept.OPERATING_INCOME, None if change == "missing" else "20")
    revenue = operand(
        Concept.REVENUE, "100", absolute_error=None if change == "precision" else ".5"
    )
    if change == "irregular":
        income = operand(Concept.OPERATING_INCOME, "20", start=date(2025, 1, 2))
        revenue = operand(Concept.REVENUE, "100", start=date(2025, 1, 2))
    calc = operating_margin(annual_amount(income), annual_amount(revenue))
    result = evaluate(calc, context("operating_margin"))
    assert result.status == status
    assert result.value is None
    assert "period_projection_mismatch" not in result.reasons


@pytest.mark.parametrize("change", ["currency", "quarter", "history", "end_date"])
def test_company_summaries_cannot_mix_selection_contexts(change):
    ctx = context("operating_margin", "net_margin_consolidated", max_age=500)
    kwargs = {}
    if change == "currency":
        kwargs["currency"] = "EUR"
    elif change == "quarter":
        kwargs["start"] = date(2025, 10, 1)
    elif change == "end_date":
        kwargs["start"] = date(2024, 1, 1)
        kwargs["end"] = date(2024, 12, 31)
    income = operand(Concept.NET_INCOME_CONSOLIDATED, "10", **kwargs)
    revenue = operand(Concept.REVENUE, "100", **kwargs)
    if change == "history":
        income, revenue = (
            replace(
                source,
                selection=replace(
                    source.selection,
                    query=replace(source.selection.query, filed_cutoff=date(2026, 2, 27)),
                ),
            )
            for source in (income, revenue)
        )
    results = (evaluate(margin(), ctx), evaluate(net_margin(income, revenue), ctx))
    assert all(item.status == "valid" for item in results)
    for summary in (
        lambda: coverage(results, context=ctx),
        lambda: observations(results),
        lambda: review_items(results),
    ):
        with pytest.raises(ValueError, match="selection"):
            summary()
