"""Hand-computed source-only calculation; no real application reads/writes."""

from dataclasses import replace
from decimal import Decimal

from tests.real_fundamentals_seed import real_manifest


def test_real_margin_reuses_signed_core_formula_and_keeps_missing_history():
    from equity_core.real_fundamentals import calculate_payload

    item = real_manifest()
    result = calculate_payload(item, history_payloads={})
    assert result.version == "s6-fundamentals-v2"
    assert result.evidence_mode == "real"
    assert Decimal(result.metrics[0].value) == Decimal(".2")  # 20 / 100
    assert result.accounting is None
    assert result.history[0].relation is None
    assert result.trend.relation is None
    assert "fixture_label" not in result.model_dump()


def test_real_zero_denominator_stays_null():
    from equity_core.real_fundamentals import calculate_payload

    item = real_manifest()
    source = item.sources[1]
    fact = replace(source.fact, value=Decimal(0), original_numeric_text="0")
    source = replace(source, selection=replace(source.selection, facts=(fact,)))
    item = item.model_copy(update={"sources": (item.sources[0], source)})
    result = calculate_payload(item, history_payloads={})
    assert result.metrics[0].value is None


def test_source_decimals_define_half_unit_uncertainty():
    import pytest
    from equity_core.real_fundamentals import precision_error

    assert precision_error("-3") == Decimal("500")
    assert precision_error("0") == Decimal("0.5")
    assert precision_error("INF") == Decimal("0")
    with pytest.raises(ValueError):
        precision_error("unknown")


def test_real_negative_income_keeps_loss_sign_and_negative_revenue_is_null():
    from equity_core.real_fundamentals import calculate_payload

    item = real_manifest()
    income = item.sources[0]
    loss = replace(income.fact, value=Decimal("-20"), original_numeric_text="-20")
    income = replace(income, selection=replace(income.selection, facts=(loss,)))
    item = item.model_copy(update={"sources": (income, item.sources[1])})
    result = calculate_payload(item, history_payloads={})
    assert Decimal(result.metrics[0].value) == Decimal("-.2")
    revenue = item.sources[1]
    negative = replace(revenue.fact, value=Decimal("-100"), original_numeric_text="-100")
    revenue = replace(revenue, selection=replace(revenue.selection, facts=(negative,)))
    result = calculate_payload(
        item.model_copy(update={"sources": (income, revenue)}), history_payloads={}
    )
    assert result.metrics[0].value is None


def test_real_wrong_concept_and_stale_policy_cannot_emit_valid_margin():
    from equity_core.real_fundamentals import calculate_payload
    from equity_schema.fundamentals_canonical import content_hash

    item = real_manifest()
    metric = item.metrics[0]
    numerator, denominator = metric.operands
    swapped = metric.model_copy(
        update={
            "operands": (
                numerator.model_copy(update={"source_indices": denominator.source_indices}),
                denominator.model_copy(update={"source_indices": numerator.source_indices}),
            )
        }
    )
    result = calculate_payload(item.model_copy(update={"metrics": (swapped,)}), history_payloads={})
    assert result.metrics[0].value is None
    context = replace(item.context, freshness=replace(item.context.freshness, max_age_days=0))
    selector = item.selector.model_copy(
        update={
            "policy_content_hash": content_hash((context, item.history_policy, item.trend_policy))
        }
    )
    result = calculate_payload(
        item.model_copy(update={"context": context, "selector": selector}), history_payloads={}
    )
    assert result.metrics[0].status == "stale"
    assert (
        result.metrics[0].value == "0.2"
    )  # Existing v1/v2 status semantics retain stale evidence.


def test_unreviewed_empty_operand_metric_matches_coverage_without_false_invalid():
    from equity_core.assessment import MetricApplicability
    from equity_core.real_fundamentals import calculate_payload
    from equity_schema.fundamentals import MetricSpec
    from equity_schema.fundamentals_canonical import content_hash

    item = real_manifest()
    rule = MetricApplicability(
        "gross_margin", None, "Reserve-income cost classification unresolved"
    )
    context = replace(
        item.context,
        profile=replace(item.context.profile, rules=(*item.context.profile.rules, rule)),
    )
    selector = item.selector.model_copy(
        update={
            "policy_content_hash": content_hash((context, item.history_policy, item.trend_policy))
        }
    )
    missing = MetricSpec(
        metric_id="gross_margin",
        operands=(),
        unit="fraction",
        calendar_evidence=None,
        revision_compatibility=None,
    )
    item = item.model_copy(
        update={"context": context, "selector": selector, "metrics": (*item.metrics, missing)}
    )
    result = calculate_payload(item, history_payloads={})
    unknown = next(m for m in result.metrics if m.metric_id == "gross_margin")
    assert (
        unknown.status == "unsupported" and unknown.applicability is None and unknown.value is None
    )
    assert "profile_applicability_unreviewed" in unknown.reasons
    assert "calculation_inputs_invalid" not in unknown.reasons
    assert result.coverage.counts["unsupported"] == 1 and result.coverage.counts["invalid"] == 0
    assert result.coverage.unresolved_count == 1 and result.coverage.fraction is None


def test_unreviewed_slot_does_not_mask_malformed_supplied_operands_or_profile():
    from datetime import date

    from equity_core.real_fundamentals import calculate_payload

    item = real_manifest()
    profile = replace(
        item.context.profile,
        rules=tuple(replace(r, applicable=None) for r in item.context.profile.rules),
    )
    context = replace(item.context, profile=profile)
    malformed = item.metrics[0].model_copy(update={"operands": item.metrics[0].operands[:1]})
    result = calculate_payload(
        item.model_copy(update={"context": context, "metrics": (malformed,)}), history_payloads={}
    )
    assert result.metrics[0].status == "invalid" and result.metrics[0].value is None
    assert "calculation_inputs_invalid" in result.metrics[0].reasons
    empty = item.metrics[0].model_copy(update={"operands": ()})
    for changed in (
        replace(profile, known_on=date(2099, 1, 1)),
        replace(profile, instrument_basis="unreviewed"),
    ):
        result = calculate_payload(
            item.model_copy(
                update={"context": replace(context, profile=changed), "metrics": (empty,)}
            ),
            history_payloads={},
        )
        assert result.metrics[0].value is None
        assert "profile_applicability_unreviewed" not in result.metrics[0].reasons
    reviewed = replace(
        context,
        profile=replace(profile, rules=tuple(replace(r, applicable=True) for r in profile.rules)),
    )
    result = calculate_payload(
        item.model_copy(update={"context": reviewed, "metrics": (empty,)}), history_payloads={}
    )
    assert result.metrics[0].status == "invalid"
