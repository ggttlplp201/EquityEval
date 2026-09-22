"""Corrective S7 acceptance: independent binding, scope and share-unit regressions."""

from decimal import Decimal as D

import pytest
from equity_core.valuation_payload import bridge
from equity_schema.valuation import AssumptionContent
from pydantic import ValidationError

from tests.valuation_seed import manifest


def test_scenario_value_cannot_change_without_its_judgment_binding():
    content = manifest().assumptions.model_dump()
    content["scenarios"][0]["wacc"] = D(".11")
    with pytest.raises(ValidationError):
        AssumptionContent.model_validate(content)


def test_arbitrary_distinct_claim_ids_do_not_prove_debt_excludes_leases():
    inputs = manifest()
    debt = inputs.claims[2].model_copy(update={"coverage": None})
    assert not bridge(
        inputs.model_copy(update={"claims": (*inputs.claims[:2], debt, *inputs.claims[3:])})
    ).eligible


def test_share_count_requires_source_scale_evidence():
    inputs = manifest()
    shares = inputs.shares.model_copy(update={"source_unit": None, "source_multiplier": None})
    assert not bridge(inputs.model_copy(update={"shares": shares})).eligible


@pytest.mark.parametrize("defect", ["value", "scenario", "origin", "known_at", "missing"])
def test_judgment_provenance_and_exact_scenario_roster(defect):
    content = manifest().assumptions.model_dump()
    judgment = next(j for j in content["judgments"] if j["parameter"] == "wacc")
    if defect == "value":
        judgment["binding"]["value"] = D(".12")
    elif defect == "scenario":
        judgment["scenario"] = "unknown scenario"
    elif defect == "origin":
        judgment["origin"] = "consensus"
    elif defect == "known_at":
        from datetime import timedelta

        judgment["known_at"] += timedelta(days=1)
    else:
        content["judgments"] = content["judgments"][1:]
    with pytest.raises(ValidationError):
        AssumptionContent.model_validate(content)


@pytest.mark.parametrize("defect", ["included", "unknown", "missing", "no_evidence", "duplicate"])
def test_debt_scope_must_prove_exclusion_of_separately_subtracted_leases(defect):
    inputs = manifest()
    debt = inputs.claims[2]
    coverage = list(debt.coverage)
    i = next(i for i, row in enumerate(coverage) if row.component == "leases")
    if defect in ("included", "unknown"):
        coverage[i] = coverage[i].model_copy(update={"disposition": defect})
    elif defect == "missing":
        coverage.pop(i)
    elif defect == "no_evidence":
        coverage[i] = coverage[i].model_copy(update={"evidence_hash": None})
    else:
        coverage[i] = coverage[0]
    debt = debt.model_copy(update={"coverage": tuple(coverage)})
    result = bridge(
        inputs.model_copy(update={"claims": (*inputs.claims[:2], debt, *inputs.claims[3:])})
    )
    assert not result.eligible
    assert "claim_scope_unproven_or_overlapping:debt" in result.reasons
    assert result.market_ev_target is None


@pytest.mark.parametrize(
    "unit,multiplier,source",
    [
        ("shares", "1", "10"),
        ("thousand_shares", "1000", "0.01"),
        ("million_shares", "1000000", "0.00001"),
    ],
)
def test_share_unit_scaling_preserves_exact_economics(unit, multiplier, source):
    inputs = manifest()
    shares = inputs.shares.model_copy(
        update={
            "source_unit": unit,
            "source_multiplier": D(multiplier),
            "source_basic": D(source),
            "source_diluted": D(source),
        }
    )
    result = bridge(inputs.model_copy(update={"shares": shares}))
    assert result.eligible
    assert result.shares == D(10)
    assert result.market_common_value == D("173.4375")
    assert result.market_ev_target == D("193.4375")


@pytest.mark.parametrize(
    "change",
    [
        {"source_multiplier": D(1000)},
        {"source_basic": D(".01")},
        {"source_diluted": D(9)},
        {"source_multiplier": None},
    ],
)
def test_inconsistent_share_scale_never_produces_a_target(change):
    inputs = manifest()
    result = bridge(inputs.model_copy(update={"shares": inputs.shares.model_copy(update=change)}))
    assert not result.eligible
    assert result.market_ev_target is None


def test_currency_is_not_a_share_unit():
    from equity_schema.valuation import SharePool

    shares = manifest().shares.model_dump()
    shares["source_unit"] = "USD"
    with pytest.raises(ValidationError):
        SharePool.model_validate(shares)


def test_public_result_omits_all_bound_judgment_identity_and_rationale():
    from equity_core.valuation_payload import calculate_payload
    from equity_schema.fundamentals_canonical import canonical_json

    inputs = manifest()
    assert len(inputs.assumptions.judgments) == 39
    assert {j.binding.kind for j in inputs.assumptions.judgments} == {
        "scalar",
        "vector",
        "solved",
        "schedule",
        "solver",
    }
    public = canonical_json(calculate_payload(inputs))
    assert "private-fixture-author" not in public
    assert "Private fictional rationale" not in public


@pytest.mark.parametrize("change", ["vector", "fade", "scenario_attribution"])
def test_vector_fade_and_scenario_attribution_cannot_drift_from_bindings(change):
    body = manifest().assumptions.model_dump()
    if change == "vector":
        body["scenarios"][0]["growth"] = (D(".12"),) * 5
    elif change == "fade":
        body["scenarios"][0]["solve"]["margin_weights"] = (D(".5"), D(".5"), D(".5"), D(".5"), D(1))
    else:
        row = next(
            j
            for j in body["judgments"]
            if j["scenario"] == "low investment" and j["parameter"] == "reinvestment"
        )
        row["binding"]["value"] = (D(".075"),) * 5
    with pytest.raises(ValidationError):
        AssumptionContent.model_validate(body)
