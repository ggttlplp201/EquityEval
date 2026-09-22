"""S6 projections preserve S5 semantics and exact frozen dependency identity."""

from dataclasses import replace

import pytest
from equity_core.fundamentals import calculate_payload
from equity_schema.fundamentals import read_manifest
from equity_schema.fundamentals_canonical import canonical_json, content_hash

from tests.fundamentals_seed import manifest


def test_typed_manifest_roundtrip_and_source_calculation_are_exact():
    inputs = manifest()
    frozen = read_manifest(canonical_json(inputs))
    assert frozen == inputs
    result = calculate_payload(frozen, history_payloads={})
    assert result.metrics[0].value == "0.2"
    assert result.metrics[0].status == "valid"
    assert result.coverage.fraction == "1"
    assert result.dependency_hash == content_hash(inputs)
    assert result.history[0].p25 is None
    assert result.history[0].years == 3
    assert result.evidence[0].resolution_ids == inputs.sources[0].fact.resolution_ids
    assert result.evidence_mode == "synthetic"


@pytest.mark.parametrize(
    "amount,status",
    [
        (None, "missing"),
        ("0", "not_meaningful"),
        ("-1", "not_meaningful"),
        (".5", "not_meaningful"),
    ],
)
def test_saved_status_and_null_match_source_engine(amount, status):
    from equity_schema.concepts import Concept

    from tests.core.metric_fixtures import operand

    inputs = manifest()
    inputs = inputs.model_copy(
        update={"sources": (inputs.sources[0], operand(Concept.REVENUE, amount))}
    )
    inputs = read_manifest(canonical_json(inputs))
    result = calculate_payload(inputs, history_payloads={})
    assert result.metrics[0].status == status
    assert result.metrics[0].value is None
    assert result.metrics[0].reasons
    assert result.coverage.covered_count == (1 if status == "not_meaningful" else 0)


def test_private_source_locators_and_policy_notes_are_not_public_payload_fields():
    inputs = manifest()
    fact = replace(
        inputs.sources[0].fact,
        source_locator="/private/secret/archive",
        source_url="https://operator:secret@example.invalid/a?api_key=secret",
    )
    source = replace(
        inputs.sources[0], selection=replace(inputs.sources[0].selection, facts=(fact,))
    )
    result = calculate_payload(
        inputs.model_copy(update={"sources": (source, inputs.sources[1])}), history_payloads={}
    )
    rendered = canonical_json(result)
    assert "secret" not in rendered
    assert "/private" not in rendered
    assert result.evidence[0].source_url is None


def test_policy_source_and_time_changes_cannot_reuse_dependency_key():
    inputs = manifest()
    base = content_hash(inputs)
    mutations = [
        inputs.model_copy(
            update={"selector": inputs.selector.model_copy(update={"engine_revision": "v2"})}
        ),
        inputs.model_copy(
            update={"sources": (replace(inputs.sources[0], precision=None), inputs.sources[1])}
        ),
    ]
    assert all(content_hash(item) != base for item in mutations)
    with pytest.raises(ValueError):
        read_manifest(
            canonical_json(
                inputs.model_copy(
                    update={
                        "context": replace(
                            inputs.context,
                            freshness=replace(inputs.context.freshness, max_age_days=1),
                        )
                    }
                )
            )
        )


def test_unknown_fields_and_float_financial_values_are_rejected_before_publication():
    import json

    body = json.loads(canonical_json(manifest()))
    body["sources"][0]["unknown"] = "field"
    with pytest.raises(ValueError):
        read_manifest(canonical_json(body))
    body = json.loads(canonical_json(manifest()))
    body["sources"][0]["selection"]["facts"][0]["value"] = 1.5
    with pytest.raises((ValueError, TypeError)):
        read_manifest(json.dumps(body, separators=(",", ":"), sort_keys=True))


def test_unknown_metric_without_operands_remains_unsupported_in_roster():
    from equity_core.assessment import evaluate
    from equity_core.metrics import Calculation

    from tests.core.test_assessment import context

    result = evaluate(Calculation("unknown", None, "fraction", (), ()), context("unknown"))
    assert result.status == "unsupported"
    assert result.value is None


def test_selector_cannot_relabel_one_day_flow_as_annual():
    from datetime import date

    from equity_schema.concepts import Concept

    from tests.core.metric_fixtures import operand

    inputs = manifest()
    inputs = inputs.model_copy(
        update={
            "sources": (
                operand(Concept.OPERATING_INCOME, "20", start=date(2025, 12, 31)),
                operand(Concept.REVENUE, "100", start=date(2025, 12, 31)),
            ),
            "selector": inputs.selector.model_copy(update={"period_start": date(2025, 12, 31)}),
        }
    )
    with pytest.raises(ValueError, match="period basis"):
        calculate_payload(inputs, history_payloads={})


@pytest.mark.parametrize("quarter", [3, 4])
def test_fiscal_annual_selector_uses_full_year_not_q3_ytd(quarter):
    from equity_schema.concepts import Concept

    from tests.core.metric_fixtures import operand
    from tests.core.test_fiscal_periods import fiscal_year, proof

    year = fiscal_year()
    inputs = manifest()
    sources = tuple(
        operand(concept, value, start=year.start, end=year.quarter_ends[quarter - 1])
        for concept, value in ((Concept.OPERATING_INCOME, "20"), (Concept.REVENUE, "100"))
    )
    specs = tuple(
        item.model_copy(update={"calendar_evidence": proof((source,), (year,))})
        for item, source in zip(inputs.metrics[0].operands, sources, strict=True)
    )
    inputs = inputs.model_copy(
        update={
            "sources": sources,
            "metrics": (inputs.metrics[0].model_copy(update={"operands": specs}),),
            "selector": inputs.selector.model_copy(
                update={"period_start": year.start, "period_end": year.quarter_ends[quarter - 1]}
            ),
        }
    )
    if quarter == 3:
        with pytest.raises(ValueError, match="period basis"):
            calculate_payload(inputs, history_payloads={})
    else:
        assert calculate_payload(inputs, history_payloads={}).metrics[0].value == "0.2"


@pytest.mark.parametrize("status", ["valid", "stale", "inapplicable", "unsupported", "invalid"])
def test_all_assessments_preserve_value_reason_and_full_roster(status):
    from equity_schema.fundamentals_canonical import content_hash

    inputs = manifest()
    ctx = inputs.context
    if status == "stale":
        ctx = replace(ctx, freshness=replace(ctx.freshness, max_age_days=1))
    elif status in {"inapplicable", "unsupported"}:
        rule = replace(ctx.profile.rules[0], applicable=False if status == "inapplicable" else None)
        ctx = replace(ctx, profile=replace(ctx.profile, rules=(rule,)))
    elif status == "invalid":
        source = replace(
            inputs.sources[0],
            precision=None,
            selection=replace(
                inputs.sources[0].selection,
                facts=(replace(inputs.sources[0].fact, source_url="file:///private/fixture"),),
            ),
        )
        inputs = inputs.model_copy(update={"sources": (source, inputs.sources[1])})
    inputs = inputs.model_copy(
        update={
            "context": ctx,
            "selector": inputs.selector.model_copy(
                update={
                    "policy_content_hash": content_hash(
                        (ctx, inputs.history_policy, inputs.trend_policy)
                    )
                }
            ),
        }
    )
    result = calculate_payload(inputs, history_payloads={})
    assert result.metrics[0].status == status
    assert result.metrics[0].value == ("0.2" if status != "invalid" else None)
    assert result.coverage.counts[status] == 1
    if status != "valid":
        assert result.metrics[0].reasons
        assert not result.observations


def test_reported_segment_amount_cannot_be_labelled_consolidated_issuer():
    import json

    from equity_ingest.financial_types import canonical_json as scope_json
    from equity_ingest.financial_types import content_hash as scope_hash
    from equity_schema.fundamentals import MetricSpec

    from tests.core.test_assessment import context

    inputs = manifest()
    source = inputs.sources[1]
    descriptor = json.loads(source.scope.descriptor_json)
    descriptor["consolidation"] = "segment"
    source = replace(
        source,
        scope=replace(
            source.scope,
            scope_kind="segment",
            descriptor_json=scope_json(descriptor),
            content_sha256=scope_hash(descriptor),
        ),
    )
    metric = MetricSpec(
        metric_id="reported.revenue",
        unit="USD",
        operands=(inputs.metrics[0].operands[0],),
        calendar_evidence=None,
        revision_compatibility=None,
    )
    inputs = inputs.model_copy(
        update={"sources": (source,), "metrics": (metric,), "context": context("reported.revenue")}
    )
    with pytest.raises(ValueError, match="consolidated scope"):
        calculate_payload(inputs, history_payloads={})


def test_accounting_check_cannot_use_an_unrelated_period():
    from datetime import date

    from equity_schema.concepts import Concept

    from tests.core.metric_fixtures import balance

    inputs = manifest()
    sources = tuple(
        balance(c, v, end=date(2024, 12, 31))
        for c, v in (
            (Concept.TOTAL_ASSETS, "100"),
            (Concept.TOTAL_LIABILITIES, "70"),
            (Concept.EQUITY_INCLUDING_NONCONTROLLING_INTERESTS, "30"),
        )
    )
    inputs = inputs.model_copy(
        update={"sources": (*inputs.sources, *sources), "accounting_source_indices": (2, 3, 4)}
    )
    with pytest.raises(ValueError, match="Accounting check"):
        calculate_payload(inputs, history_payloads={})


@pytest.mark.parametrize("years", [3, 5, 10])
def test_selected_history_window_and_policy_contents_control_comparability(years):
    from datetime import UTC, date, datetime
    from uuid import uuid4

    from equity_core.history import HistoryPolicy
    from equity_schema.fundamentals import HistorySampleRef

    inputs = manifest()
    policy = HistoryPolicy(years, 1, "synthetic-history-v1")
    ctx = replace(
        inputs.context,
        as_of=date(2026, 3, 31),
        freshness=replace(inputs.context.freshness, max_age_days=999),
    )
    old = inputs.model_copy(
        update={
            "context": ctx,
            "history_policy": policy,
            "selector": inputs.selector.model_copy(
                update={
                    "as_of": ctx.as_of,
                    "evaluated_at": datetime(2026, 3, 31, tzinfo=UTC),
                    "history_years": years,
                    "policy_content_hash": content_hash((ctx, policy, inputs.trend_policy)),
                }
            ),
        }
    )
    payload = calculate_payload(old, history_payloads={})
    sid = uuid4()
    ctx = replace(ctx, as_of=date(2026, 6, 30))
    current = old.model_copy(
        update={
            "context": ctx,
            "selector": old.selector.model_copy(
                update={
                    "as_of": ctx.as_of,
                    "evaluated_at": datetime(2026, 6, 30, tzinfo=UTC),
                    "policy_content_hash": content_hash((ctx, policy, inputs.trend_policy)),
                }
            ),
            "history_samples": (
                HistorySampleRef(
                    snapshot_id=sid,
                    payload_hash=content_hash(payload),
                    quarter_end=date(2026, 3, 31),
                ),
            ),
        }
    )
    result = calculate_payload(current, history_payloads={sid: payload})
    assert result.history[0].years == years
    assert result.history[0].p50 == "0.2"
    assert result.history[0].eligible_snapshot_ids == (sid,)
    assert len(result.history[0].missing_quarter_ends) == years * 4 - 1
    # Same revision string, changed policy contents: the sample is incompatible.
    ctx = replace(ctx, freshness=replace(ctx.freshness, max_age_days=998))
    changed = current.model_copy(update={"context": ctx})
    excluded = calculate_payload(changed, history_payloads={sid: payload}).history[0]
    assert excluded.p50 is None
    assert "incompatible_series" in excluded.excluded[0][1]


def test_instrument_specific_reported_source_is_not_an_issuer_result():
    import json
    from uuid import uuid4

    from equity_ingest.financial_types import canonical_json as scope_json
    from equity_ingest.financial_types import content_hash as scope_hash
    from equity_schema.fundamentals import MetricSpec

    from tests.core.test_assessment import context

    inputs = manifest()
    source = inputs.sources[1]
    instrument = uuid4()
    descriptor = json.loads(source.scope.descriptor_json)
    descriptor["instrument"] = str(instrument)
    source = replace(
        source,
        scope=replace(
            source.scope,
            instrument_id=instrument,
            descriptor_json=scope_json(descriptor),
            content_sha256=scope_hash(descriptor),
        ),
        selection=replace(
            source.selection, query=replace(source.selection.query, instrument_id=instrument)
        ),
    )
    metric = MetricSpec(
        metric_id="reported.revenue",
        unit="USD",
        operands=(inputs.metrics[0].operands[0],),
        calendar_evidence=None,
        revision_compatibility=None,
    )
    inputs = inputs.model_copy(
        update={"sources": (source,), "metrics": (metric,), "context": context("reported.revenue")}
    )
    with pytest.raises(ValueError, match="consolidated scope"):
        calculate_payload(inputs, history_payloads={})
