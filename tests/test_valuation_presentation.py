"""S8a presentation uses unchanged S7 public payloads and independent oracles."""

import json
from decimal import Decimal as D

from equity_schema.valuation import ValuationPayload

from scripts.export_valuation import build, encoded


def test_reference_bridge_and_conditional_sensitivity_oracles():
    bundle = build()
    payload = ValuationPayload.model_validate(bundle["examples"][0]["payload"])
    assert payload.bridge.market_common_value == D("173.4375")
    assert payload.bridge.market_ev_target == D("193.4375")
    assert payload.bridge.adjustment == D("-20")
    assert payload.scenarios[1].solve.representative == D(".2")
    assert payload.scenarios[1].evaluation.pv_terminal == D("143.4375")
    grid = payload.sensitivities[1]
    assert [cell.value for cell in grid.cells if cell.y == D(".05")] == [
        D("6.421875"),
        D("17.34375"),
        D("28.265625"),
    ]
    assert payload.scenario_dispersion is not None
    assert len(payload.assumptions.scenarios) == 3


def test_states_and_uncertainties_survive_projection():
    examples = {row["id"]: row["payload"] for row in build()["examples"]}
    for state in ("unavailable", "inconclusive", "no_solution_in_domain", "non_unique"):
        payload = ValuationPayload.model_validate(examples[state])
        assert payload.scenarios[0].solve.state == state
        assert payload.scenarios[0].solve.representative is None
        assert payload.scenario_dispersion is None
    payload = ValuationPayload.model_validate(examples["reference"])
    assert payload.numerical_uncertainty
    assert payload.source_measurement_uncertainty == (("revenue_anchor", D(".5")),)
    assert examples["missing"] is None


def test_export_is_deterministic_public_and_generated_file_matches():
    from scripts.export_valuation import OUTPUT

    first = encoded(build())
    assert first == encoded(build()) == OUTPUT.read_bytes()
    assert b"private-fixture-author" not in first
    assert b"Private fictional rationale" not in first
    bundle = json.loads(first)
    assert bundle["fictional"] is True
    for row in bundle["examples"]:
        if row["payload"]:
            assert ValuationPayload.model_validate(row["payload"]).evidence_mode == "synthetic"
