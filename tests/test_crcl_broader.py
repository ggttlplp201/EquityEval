"""D5k broader source eligibility remains bounded and rejects plausible substitutions."""

from decimal import Decimal

import pytest


def test_broader_review_separates_current_operands_from_unproved_history():
    from scripts.review_crcl_broader import review

    data = review()
    assert data["status"] == "ready_for_fy2025_preparation"
    assert data["sourceObservation"] == "2026-10-15T21:59:05.195192+00:00"
    assert data["operands"]["net_income_consolidated"]["value"] == "-69518000"
    assert data["parentNetIncome"] == "-69508000"
    assert len(data["operands"]) == 10
    assert len(data["eligibleMetrics"]) == 6
    assert set(data["blockedMetrics"]) == {
        "gross_margin",
        "gross_margin_derived",
        "revenue_growth_yoy",
        "return_on_assets",
    }
    assert any(item["resourceKey"].endswith(".pdf") for item in data["missingHistoryBodies"])
    assert data["historicalAnalysisEligible"] is False
    assert data["factsVintages"]
    assert all(row["consistent"] for row in data["balanceComparisons"])


def test_broader_preparation_uses_only_exact_annual_and_closing_periods():
    from scripts.prepare_crcl_broader import prepare

    bundle, proof = prepare()
    assert len(bundle.resolutions) == 10
    assert not bundle.quality_flags
    assert {r.period.end_date.isoformat() for r in bundle.inputs.requests} == {"2025-12-31"}
    assert {r.statement_family for r in bundle.inputs.requests} == {
        "income",
        "cash_flow",
        "balance_sheet",
    }
    assert bundle.inputs.inventory_completeness.boundary_start.isoformat() == "2025-12-31"
    observations = {o.id: o for o in bundle.observations}
    values = {
        r.concept_std.value: observations[r.selected_observation_id].numeric_value
        for r in bundle.resolutions
    }
    assert values["net_income_consolidated"] == Decimal("-69518000")
    assert values["capital_expenditures_ppe"] == Decimal("12432000")
    assert len(proof) == 10


def test_broader_changed_facts_and_missing_scope_fail_closed():
    from scripts.review_crcl_broader import selected_facts, validate_selected_facts

    document, _ = selected_facts()
    import copy

    changed = copy.deepcopy(document)
    rows = changed["facts"]["us-gaap"]["ProfitLoss"]["units"]["USD"]
    row = next(r for r in rows if r.get("start") == "2025-01-01" and r["end"] == "2025-12-31")
    row["val"] = -69508000
    with pytest.raises(ValueError):
        validate_selected_facts(changed)
    changed = copy.deepcopy(document)
    del changed["facts"]["us-gaap"]["PaymentsToAcquirePropertyPlantAndEquipment"]
    with pytest.raises(ValueError):
        validate_selected_facts(changed)


def test_broader_preparation_does_not_clear_a_changed_review(monkeypatch):
    from scripts import prepare_crcl_broader as module
    from scripts.review_crcl_broader import review

    result = review()
    result["status"] = "blocked"
    monkeypatch.setattr(module, "review", lambda: result)
    with pytest.raises(ValueError):
        module.prepare()


@pytest.mark.parametrize("change", ["sign", "period", "unit", "accession"])
def test_broader_plausible_wrong_cash_operand_is_rejected(change):
    from copy import deepcopy

    from scripts.review_crcl_broader import selected_facts, validate_selected_facts

    original, _ = selected_facts()
    changed = deepcopy(original)
    concept = changed["facts"]["us-gaap"]["PaymentsToAcquirePropertyPlantAndEquipment"]
    row = next(
        r
        for r in concept["units"]["USD"]
        if r.get("start") == "2025-01-01" and r["end"] == "2025-12-31"
    )
    if change == "sign":
        row["val"] = -row["val"]
    elif change == "period":
        row["start"] = "2025-04-01"
    elif change == "unit":
        concept["units"]["EUR"] = concept["units"].pop("USD")
    else:
        row["accn"] = "0001876042-26-000150"
    with pytest.raises(ValueError):
        validate_selected_facts(changed)


def test_expanded_body_review_is_not_inherited_two_concept_clearance():
    from scripts.review_crcl_broader import retained
    from scripts.review_crcl_broader_events import review_bodies

    rows, bodies = retained()
    result = review_bodies(rows, bodies)
    assert len(result["bodyDispositions"]) == 41
    assert all(len(r["conceptEffects"]) == 10 for r in result["bodyDispositions"])
    assert {c["concept"] for c in result["editionComparisons"]} >= {
        "net_income_consolidated",
        "cash_from_operating_activities",
        "capital_expenditures_ppe",
        "current_assets",
        "current_liabilities",
    }
    assert all(c["consistent"] for c in result["editionComparisons"])
    assert result["annualCashFlowLimitation"]
    affected = next(
        r for r in rows if r["source_object_key"].endswith("/final_circlereportsfourt.htm")
    )
    changed = dict(bodies)
    changed[affected["capture_id"]] = changed[affected["capture_id"]].replace(b"69,518", b"69,508")
    with pytest.raises(ValueError, match="reviewed body"):
        review_bodies(rows, changed)
    with pytest.raises(ValueError, match="roster"):
        review_bodies([r for r in rows if r != affected], bodies)
