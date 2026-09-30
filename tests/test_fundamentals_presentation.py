"""S8b presents validated S6a core output, never browser financial calculations."""

import json
from decimal import Decimal

import pytest
from equity_schema.fundamentals import FundamentalsPayload

from scripts.export_fundamentals import OUTPUT, build, encoded


@pytest.fixture(scope="module")
def bundle():
    return build()


def selected(bundle, example="reference", years=3, as_of="2026-06-30"):
    return next(
        row
        for row in bundle["snapshots"]
        if row["example"] == example
        and row["years"] == years
        and row["payload"]["selector"]["as_of"] == as_of
    )


def test_hand_calculated_amounts_and_ratios(bundle):
    payload = FundamentalsPayload.model_validate(selected(bundle)["payload"])
    metrics = {m.metric_id: m for m in payload.metrics}
    assert metrics["operating_margin"].value == "0.2"
    assert metrics["free_cash_flow_ppe"].value == "-8"
    assert metrics["free_cash_flow_margin_ppe"].value == "-0.08"
    assert metrics["revenue_growth_yoy"].value == "0.25"
    assert metrics["return_on_assets"].value == "0.1"
    balance = FundamentalsPayload.model_validate(selected(bundle, "balance")["payload"])
    assert balance.selector.period_basis == "instant"
    assert next(m.value for m in balance.metrics if m.metric_id == "current_ratio") == "2"


def test_all_seven_statuses_and_coverage_preserved(bundle):
    statuses = set()
    for row in bundle["snapshots"]:
        payload = FundamentalsPayload.model_validate(row["payload"])
        statuses.update(m.status for m in payload.metrics)
        for status, count in payload.coverage.counts.items():
            assert count == sum(m.status == status for m in payload.metrics)
    assert statuses == {
        "valid",
        "not_meaningful",
        "missing",
        "invalid",
        "stale",
        "unsupported",
        "inapplicable",
    }


def test_history_keeps_saved_windows_bands_and_exclusions(bundle):
    for years in (3, 5, 10):
        p = selected(bundle, years=years)["payload"]
        h = next(h for h in p["history"] if h["metric_id"] == "operating_margin")
        assert h["years"] == years
        assert h["window_start"] == f"{2026 - years}-06-30"
        assert h["minimum_samples"] == years * 4
        assert len(h["eligible_snapshot_ids"]) == 12
        assert len(h["missing_quarter_ends"]) == years * 4 - 12
        assert (Decimal(h["p50"]) if h["p50"] is not None else None) == (
            Decimal("0.2") if years == 3 else None
        )
        if years == 3:
            assert Decimal(h["p25"]) == Decimal("0.155")
            assert Decimal(h["p75"]) == Decimal("0.225")
        assert any("after_as_of" in reasons for _, reasons in h["excluded"])
        if years != 3:
            assert "insufficient_history" in h["reasons"]


def test_earlier_saved_selection_excludes_future_financial_values(bundle):
    early = selected(bundle, as_of="2026-03-31")
    assert "987654321" not in json.dumps(early)
    assert all(e["period_end"] <= "2026-03-31" for e in early["payload"]["evidence"])
    assert all(e["filed_on"] <= "2026-03-31" for e in early["payload"]["evidence"])
    assert any(
        "after_as_of" in reasons for _, reasons in early["payload"]["history"][0]["excluded"]
    )
    assert early["snapshot_id"] != selected(bundle)["snapshot_id"]


def test_deterministic_validated_export_and_exact_public_evidence(bundle):
    assert encoded(bundle) == encoded(build()) == OUTPUT.read_bytes()
    assert bundle["fictional"] is True
    for row in bundle["snapshots"]:
        assert FundamentalsPayload.model_validate(row["payload"]).evidence_mode == "synthetic"
        assert row["payload_hash"] and row["input_snapshot_id"]
        assert row["payload"]["evidence"]
    assert b"private/" not in encoded(bundle)


def test_fictional_source_identities_are_content_bound(bundle):
    records = {}
    for row in bundle["snapshots"]:
        for evidence in row["payload"]["evidence"]:
            for observation in evidence["observation_ids"]:
                source = (
                    evidence["value"],
                    evidence["source_url"],
                    evidence["source_hashes"],
                    evidence["scope_hash"],
                    evidence["period_start"],
                    evidence["period_end"],
                )
                assert observation not in records or records[observation] == source
                records[observation] = source
    normal = selected(bundle)["payload"]["evidence"][0]
    changed = selected(bundle, "not_meaningful")["payload"]["evidence"][0]
    assert normal["capture_ids"] != changed["capture_ids"]
    assert normal["source_hashes"] != changed["source_hashes"]


@pytest.mark.parametrize("duplicate", ["example", "date"])
def test_recipe_rejects_ambiguous_selection_metadata(duplicate):
    from scripts.export_fundamentals import INPUT, Recipe

    body = json.loads(INPUT.read_text())
    if duplicate == "example":
        body["examples"].append(body["examples"][0])
    else:
        body["examples"][0]["dates"].append(body["examples"][0]["dates"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        Recipe.model_validate(body)


def test_export_rejects_duplicate_saved_selection_keys(bundle):
    from scripts.export_fundamentals import validate_selection_keys

    with pytest.raises(ValueError, match="Duplicate"):
        validate_selection_keys([bundle["snapshots"][0], bundle["snapshots"][0]])
