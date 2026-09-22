from decimal import Decimal as D

import pytest
from equity_core.valuation_payload import bridge, calculate_payload
from equity_schema.fundamentals_canonical import canonical_json
from equity_schema.valuation import read_manifest

from tests.valuation_seed import manifest


def test_bridge_hand_oracle_and_separate_uncertainties():
    inputs = manifest()
    result = bridge(inputs)
    assert result.eligible and result.adjustment == -20
    assert result.market_common_value == D("173.4375")
    assert result.market_ev_target == D("193.4375")
    payload = calculate_payload(inputs)
    assert payload.scenario_dispersion is not None
    assert len(payload.numerical_uncertainty) == 3
    assert payload.source_measurement_uncertainty == (("revenue_anchor", D(".5")),)
    public = canonical_json(payload)
    assert "private-fixture-author" not in public
    assert "Private fictional rationale" not in public
    assert payload.model.cash_tax == "tax_on_positive_ebit_no_nol_v1"


@pytest.mark.parametrize(
    "kind", ["cash", "nonoperating_assets", "debt", "leases", "preferred", "nci", "other"]
)
def test_any_missing_claim_blocks_entire_bridge(kind):
    inputs = manifest()
    claims = tuple(
        c.model_copy(
            update=dict(
                state="unavailable", amount=None, basis="unreviewed", reasons=("missing_claim",)
            )
        )
        if c.kind == kind
        else c
        for c in inputs.claims
    )
    inputs = read_manifest(canonical_json(inputs.model_copy(update={"claims": claims})))
    result = calculate_payload(inputs)
    assert result.bridge.market_ev_target is None
    assert result.bridge.adjustment is None
    assert all(
        s.solve.state == "unavailable" and s.conditional_per_share is None for s in result.scenarios
    )
    assert result.scenario_dispersion is None


@pytest.mark.parametrize(
    "change",
    [
        {"current_basic": D(0)},
        {"current_diluted": D(11)},
        {"no_dilutive_claims": False},
        {"complete_homogeneous_pool": False},
        {"complete_action_coverage": False},
        {"operating_lease_basis_matches": False},
        {"unrestricted_nonoperating_cash": False},
        {"no_crossholding_earnings_overlap": False},
    ],
)
def test_incomplete_share_or_operating_basis_never_passes(change):
    inputs = manifest()
    inputs = inputs.model_copy(update={"shares": inputs.shares.model_copy(update=change)})
    assert not bridge(inputs).eligible


def test_empty_roster_and_overlapping_claims_are_rejected():
    inputs = manifest()
    with pytest.raises(ValueError):
        read_manifest(canonical_json(inputs.model_copy(update={"claims": ()})))
    duplicate = inputs.claims[1].model_copy(
        update={"economic_claim_ids": inputs.claims[0].economic_claim_ids}
    )
    with pytest.raises(ValueError):
        read_manifest(
            canonical_json(
                inputs.model_copy(
                    update={"claims": (inputs.claims[0], duplicate, *inputs.claims[2:])}
                )
            )
        )


@pytest.mark.parametrize(
    "change",
    [
        {"currency": None},
        {"adjustment_basis": "total_return"},
        {"value": None},
        {"usable": False},
        {"action_basis": "other"},
    ],
)
def test_quote_currency_and_action_basis_must_be_explicit(change):
    inputs = manifest()
    inputs = inputs.model_copy(update={"price": inputs.price.model_copy(update=change)})
    assert not bridge(inputs).eligible


def test_conditional_sensitivity_grid_keeps_its_units_and_invalid_cells():
    from equity_schema.valuation import SensitivityGrid

    inputs = manifest()
    grid = SensitivityGrid(
        name="conditional margins",
        reference_scenario="reference",
        output="conditional_reprice",
        x_parameter="terminal_operating_margin",
        x_values=(D(".1"), D(".2"), D(".3")),
        y_parameter="revenue_cagr",
        y_values=(D(".1"),),
        conditional_parameter=D(".2"),
    )
    inputs = inputs.model_copy(
        update={"assumptions": inputs.assumptions.model_copy(update={"sensitivities": (grid,)})}
    )
    result = calculate_payload(inputs)
    assert result.sensitivities[0].unit == "currency_per_share"
    assert [c.value for c in result.sensitivities[0].cells] == [
        D("6.421875"),
        D("17.34375"),
        D("28.265625"),
    ]


def test_negative_conditional_cell_retains_signed_components_and_reason():
    from equity_schema.valuation import SensitivityGrid

    inputs = manifest()
    grid = SensitivityGrid(
        name="negative equity",
        reference_scenario="reference",
        output="conditional_reprice",
        x_parameter="reinvestment_to_revenue",
        x_values=(D(1),),
        y_parameter="wacc",
        y_values=(D(".1"),),
        conditional_parameter=D(".2"),
    )
    inputs = inputs.model_copy(
        update={"assumptions": inputs.assumptions.model_copy(update={"sensitivities": (grid,)})}
    )
    cell = calculate_payload(inputs).sensitivities[0].cells[0]
    assert cell.value == D("-30.15625")
    assert "nonpositive_common_equity" in cell.reasons
    assert cell.evaluation.operating_ev == D("-281.5625")
    assert cell.evaluation.pv_terminal == D("143.4375")
    assert cell.evaluation.terminal_contribution is None
    assert "terminal_ratio_not_meaningful" in cell.reasons


def test_date_only_same_day_anchor_cannot_be_used_at_midnight():
    from dataclasses import replace

    from equity_core.valuation_source import anchor_reasons

    from tests.fundamentals_seed import manifest as source_manifest

    source = source_manifest()
    anchor = source.sources[1]
    fact = replace(anchor.fact, filed_date=source.selector.as_of)
    anchor = replace(anchor, selection=replace(anchor.selection, facts=(fact,)))
    assert "anchor_intraday_publication_unproven" in anchor_reasons(
        anchor, source.selector, source.selector.evaluated_at
    )


@pytest.mark.parametrize("change", [{"known_basis": "unproven"}, {"known_basis": "date_only"}])
def test_same_day_unproved_claim_or_share_knowledge_is_unavailable(change):
    inputs = manifest()
    assert not bridge(
        inputs.model_copy(update={"shares": inputs.shares.model_copy(update=change)})
    ).eligible
    changed = inputs.claims[0].model_copy(update=change)
    assert not bridge(inputs.model_copy(update={"claims": (changed, *inputs.claims[1:])})).eligible


def test_bridge_capture_vintage_is_independent_and_enforced():
    from datetime import timedelta

    inputs = manifest()
    later = inputs.bridge_captured_before + timedelta(days=100)
    changed = inputs.claims[0].model_copy(update={"captured_at": later})
    future = inputs.model_copy(update={"claims": (changed, *inputs.claims[1:])})
    assert not bridge(future).eligible
    # A new explicitly pinned capture vintage can reconstruct earlier known data;
    # the reviewed instant evidence remains independent of local retrieval.
    assert bridge(future.model_copy(update={"bridge_captured_before": later})).eligible


def test_reverse_cells_reprice_with_changed_axes_and_keep_diagnostics():
    from equity_schema.valuation import SensitivityGrid

    inputs = manifest()
    grid = SensitivityGrid(
        name="reverse diagnostics",
        reference_scenario="reference",
        output="reverse_implied_parameter",
        x_parameter="wacc",
        x_values=("0.09", "0.1"),
        y_parameter="terminal_growth",
        y_values=("0.01", "0.02"),
        conditional_parameter=None,
    )
    inputs = inputs.model_copy(
        update={"assumptions": inputs.assumptions.model_copy(update={"sensitivities": (grid,)})}
    )
    for cell in calculate_payload(inputs).sensitivities[0].cells:
        assert cell.solve.state == "converged"
        assert cell.evaluation is not None
        assert abs(cell.evaluation.operating_ev - D("193.4375")) < D("1e-8")
        assert abs(cell.common_equity - D("173.4375")) < D("1e-8")
        assert cell.evaluation.terminal_contribution is not None
