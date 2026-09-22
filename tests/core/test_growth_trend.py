"""Versioned trend display sensitivity, with no universal investment threshold."""

from dataclasses import replace
from datetime import date
from decimal import ROUND_UP, Decimal, Inexact, localcontext

import pytest
from equity_core.assessment import evaluate
from equity_core.metrics import revenue_growth
from equity_core.trends import TrendPolicy, growth_trend
from equity_schema.concepts import Concept

from tests.core.metric_fixtures import operand
from tests.core.test_assessment import context


def rates(values=("110", "112", "114")):
    ctx = context("revenue_growth_yoy", max_age=400)
    return tuple(
        evaluate(
            revenue_growth(
                operand(
                    Concept.REVENUE,
                    value,
                    start=date(2025, month, 1),
                    end=date(2025, month + 2, day),
                ),
                operand(
                    Concept.REVENUE,
                    "100",
                    start=date(2024, month, 1),
                    end=date(2024, month + 2, day),
                ),
            ),
            ctx,
        )
        for value, month, day in zip(values, (4, 7, 10), (30, 30, 31), strict=True)
    )


def policy(tolerance=".01"):
    return TrendPolicy(Decimal(tolerance), "synthetic-trend-v1", ("synthetic:display-policy",))


@pytest.mark.parametrize(
    "values,expected,changes",
    [
        (("110", "112", "114"), "rising", (".02", ".02")),
        (("114", "112", "110"), "falling", ("-.02", "-.02")),
        (("110", "111", "110"), "broadly_stable", (".01", "-.01")),
        (("110", "112", "111"), "mixed", (".02", "-.01")),
        (("90", "92", "94"), "rising", (".02", ".02")),
        (("100", "100", "100"), "broadly_stable", ("0", "0")),
    ],
)
def test_three_rates_use_strict_tolerance_and_retain_all_context(values, expected, changes):
    inputs = rates(values)
    result = growth_trend(inputs, policy=policy())
    assert result.relation == expected
    assert result.changes == tuple(Decimal(v) for v in changes)
    assert result.metrics == inputs
    assert result.policy == policy()
    assert not result.flags


@pytest.mark.parametrize(
    "change",
    ["few", "out_of_order", "duplicate", "stale", "edited", "profile", "annual", "currency"],
)
def test_trend_does_not_compare_partial_or_incompatible_inputs(change):
    inputs = rates()
    if change == "few":
        inputs = inputs[:2]
    elif change == "out_of_order":
        inputs = tuple(reversed(inputs))
    elif change == "duplicate":
        inputs = (inputs[0], inputs[0], inputs[2])
    elif change == "stale":
        ctx = replace(
            inputs[0].context, freshness=replace(inputs[0].context.freshness, max_age_days=1)
        )
        inputs = tuple(evaluate(item.calculation, ctx) for item in inputs)
    elif change == "edited":
        inputs = (*inputs[:2], replace(inputs[-1], value=Decimal("9")))
    elif change == "profile":
        ctx = replace(
            inputs[-1].context, profile=replace(inputs[-1].context.profile, revision="different")
        )
        inputs = (*inputs[:2], evaluate(inputs[-1].calculation, ctx))
    elif change == "annual":
        calc = revenue_growth(
            operand(Concept.REVENUE, "114"),
            operand(Concept.REVENUE, "100", start=date(2024, 1, 1), end=date(2024, 12, 31)),
        )
        inputs = (*inputs[:2], evaluate(calc, inputs[0].context))
    else:
        calc = revenue_growth(
            operand(Concept.REVENUE, "114", start=date(2025, 10, 1), currency="EUR"),
            operand(
                Concept.REVENUE,
                "100",
                start=date(2024, 10, 1),
                end=date(2024, 12, 31),
                currency="EUR",
            ),
        )
        inputs = (*inputs[:2], evaluate(calc, inputs[0].context))
    result = growth_trend(inputs, policy=policy())
    assert result.relation is None
    assert result.changes == ()
    assert result.flags
    assert result.metrics == inputs


def test_tolerance_is_explicit_versioned_and_context_independent():
    inputs = rates()
    assert growth_trend(inputs, policy=policy(".02")).relation == "broadly_stable"
    with localcontext() as ctx:
        ctx.prec = 1
        ctx.rounding = ROUND_UP
        ctx.traps[Inexact] = True
        result = growth_trend(inputs, policy=policy())
    assert result.relation == "rising"
    for value in ("-1", "NaN", "Infinity"):
        with pytest.raises(ValueError):
            policy(value)


def test_trend_needs_review_across_reporting_editions():
    from equity_core.periods import RevisionCompatibility

    originals = rates()
    inputs = []
    all_sources = []
    for index, item in enumerate(originals):
        new_sources = tuple(
            operand(
                Concept.REVENUE,
                str(source.value),
                start=source.period.start_date,
                end=source.period.end_date,
                edition="edition-" + str(index),
            )
            for source in item.calculation.operands
        )
        all_sources.extend(new_sources)
        inputs.append(evaluate(revenue_growth(*new_sources), item.context))
    metrics = tuple(inputs)
    assert growth_trend(metrics, policy=policy()).relation is None
    proof = RevisionCompatibility(
        tuple(s.selection.input_hash for s in all_sources), ("synthetic:trend-review",), "v1"
    )
    reviewed = growth_trend(metrics, policy=policy(), revision_compatibility=proof)
    assert reviewed.relation == "rising"
    assert reviewed.revision_compatibility is proof
