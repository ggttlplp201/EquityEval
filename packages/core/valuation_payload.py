"""Pure S7 composition: complete bridge, named solves and explicit sensitivity cells."""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal, DecimalException, localcontext
from typing import Any

from equity_core.valuation import CONTEXT, evaluate, scenario_span, solve
from equity_core.valuation_sensitivity import elasticity, ranks
from equity_core.valuation_types import Forecast, SolveResult
from equity_schema.fundamentals_canonical import content_hash
from equity_schema.valuation import (
    BridgeResult,
    SafeAssumptions,
    Scenario,
    ScenarioResult,
    SensitivityCell,
    SensitivityEffect,
    SensitivityGrid,
    SensitivityResult,
    ValuationManifest,
    ValuationPayload,
)

D = Decimal


def bridge(inputs: ValuationManifest) -> BridgeResult:
    """All-or-nothing dated economic-claim eligibility. No missing zero defaults."""
    inputs = ValuationManifest.model_validate(inputs.model_dump())
    a, p, s, policy = inputs.assumptions, inputs.price, inputs.shares, inputs.policy
    at = a.valuation_at
    day = at.astimezone(UTC).date()
    currency = inputs.selector.currency
    reasons = list(inputs.source_eligibility_reasons)
    if policy.applicability != "reviewed_operating_fcff":
        reasons.append("unsupported_operating_model")
    if policy.known_at > at or policy.effective_at > at:
        reasons.append("policy_not_known_or_effective")
    if not 0 <= (day - inputs.selector.period_end).days <= policy.max_financial_age_days:
        reasons.append("ineligible_financial_age")
    if inputs.selector.filed_cutoff is None or inputs.selector.filed_cutoff > day:
        reasons.append("financial_known_cutoff")
    if (
        not p.usable
        or p.value is None
        or p.value <= 0
        or p.observation_id is None
        or p.batch_id is None
        or p.currency != currency
        or p.adjustment_basis not in ("unadjusted", "split_only", "split_and_dividend", "unknown")
        or not p.session_basis
    ):
        reasons.append("ineligible_quote")
    if (
        p.source_known_at > at
        or not 0 <= (day - p.reference_date).days <= policy.max_quote_age_days
    ):
        reasons.append("quote_time_or_freshness")
    if (
        s.current_basic is None
        or s.current_basic <= 0
        or s.current_basic != s.current_diluted
        or s.currency != currency
        or not all(
            (
                s.complete_homogeneous_pool,
                s.no_dilutive_claims,
                s.complete_action_coverage,
                s.operating_lease_basis_matches,
                s.unrestricted_nonoperating_cash,
                s.no_crossholding_earnings_overlap,
            )
        )
    ):
        reasons.append("ineligible_common_pool_or_operating_basis")
    if (
        s.captured_at > inputs.bridge_captured_before
        or s.known_basis == "unproven"
        or (s.known_basis == "date_only" and s.known_at.astimezone(UTC).date() >= day)
    ):
        reasons.append("share_capture_or_publication_unproven")
    if s.action_basis != p.action_basis:
        reasons.append("price_share_action_mismatch")
    if s.known_at > at or not 0 <= (day - s.as_of).days <= policy.max_claim_age_days:
        reasons.append("share_time_or_freshness")
    multiplier = {"shares": D(1), "thousand_shares": D(1000), "million_shares": D(1000000)}.get(
        s.source_unit or ""
    )
    if (
        multiplier is None
        or s.source_multiplier != multiplier
        or s.source_basic is None
        or s.source_diluted is None
    ):
        reasons.append("share_source_unit_unproven")
    else:
        with localcontext(CONTEXT):
            if (
                s.source_basic * multiplier != s.current_basic
                or s.source_diluted * multiplier != s.current_diluted
            ):
                reasons.append("share_normalization_mismatch")
    for claim in inputs.claims:
        coverage = claim.coverage or ()
        if (
            len(coverage) != 7
            or {row.component for row in coverage} != {c.kind for c in inputs.claims}
            or any(
                row.evidence_hash is None
                or row.disposition
                != (
                    "included"
                    if row.component == claim.kind and claim.state == "eligible_amount"
                    else "excluded"
                )
                for row in coverage
            )
        ):
            reasons.append("claim_scope_unproven_or_overlapping:" + claim.kind)
        if (
            claim.state == "unavailable"
            or claim.captured_at > inputs.bridge_captured_before
            or claim.known_basis == "unproven"
            or (claim.known_basis == "date_only" and claim.known_at.astimezone(UTC).date() >= day)
            or claim.currency != currency
            or claim.known_at > at
            or not 0 <= (day - claim.as_of).days <= policy.max_claim_age_days
        ):
            reasons.append("ineligible_claim:" + claim.kind)
    if reasons:
        return BridgeResult(
            eligible=False,
            market_common_value=None,
            adjustment=None,
            market_ev_target=None,
            shares=None,
            reasons=tuple(reasons),
        )
    with localcontext(CONTEXT):
        amounts = {c.kind: c.amount for c in inputs.claims}
        assert all(v is not None for v in amounts.values())
        adjustment = sum(
            (
                c.amount if c.kind in ("cash", "nonoperating_assets") else -c.amount
                for c in inputs.claims
                if c.amount is not None
            ),
            D(0),
        )
        assert p.value is not None and s.current_basic is not None
        market = p.value * s.current_basic
        return BridgeResult(
            eligible=True,
            market_common_value=market,
            adjustment=adjustment,
            market_ev_target=market - adjustment,
            shares=s.current_basic,
            reasons=(),
        )


def resolved(scenario: Scenario, parameter: Decimal) -> Forecast:
    n = len(scenario.taxes)
    values: dict[str, Any] = scenario.model_dump(exclude={"name", "solve"})
    with localcontext(CONTEXT):
        if scenario.solve.variable == "revenue_cagr":
            values["growth"] = (parameter,) * n
        elif scenario.solve.variable == "reinvestment_to_revenue":
            values["reinvestment"] = (parameter,) * n
        else:
            anchor = scenario.solve.anchor_margin
            assert anchor is not None
            values["margins"] = tuple(
                (1 - w) * anchor + w * parameter for w in scenario.solve.margin_weights
            )
            values["terminal_margin"] = parameter
    return Forecast.model_validate(values)


def unavailable(reasons: tuple[str, ...]) -> SolveResult:
    return SolveResult(
        state="unavailable",
        representative=None,
        interval=None,
        residual=None,
        root_intervals=(),
        unresolved_domains=(),
        proof=(),
        proof_revision="decimal_interval_model_v1",
        evaluations=0,
        subdivisions=0,
        iterations=0,
        reasons=reasons,
    )


def calculate_scenario(scenario: Scenario, linked: BridgeResult) -> ScenarioResult:
    result = unavailable(linked.reasons)
    evaluated = None
    equity = per_share = None
    if linked.eligible:
        assert linked.market_ev_target is not None
        try:
            result = solve(
                resolved(scenario, scenario.solve.lower), scenario.solve, linked.market_ev_target
            )
            if result.representative is not None:
                evaluated = evaluate(resolved(scenario, result.representative))
                assert linked.adjustment is not None and linked.shares is not None
                with localcontext(CONTEXT):
                    equity = evaluated.operating_ev + linked.adjustment
                    per_share = equity / linked.shares
        except (ValueError, DecimalException, ArithmeticError):
            result = unavailable(("invalid_model_inputs",))
    return ScenarioResult(
        name=scenario.name,
        solve_variable=scenario.solve.variable,
        unit="fraction",
        solve=result,
        evaluation=evaluated,
        common_equity=equity,
        conditional_per_share=per_share,
        reasons=result.reasons
        + (evaluated.reasons if evaluated is not None else ())
        + (("nonpositive_common_equity",) if equity is not None and equity <= 0 else ()),
    )


def _changed(values: dict[str, Any], parameter: str, value: Decimal, scenario: Scenario) -> None:
    years = len(scenario.taxes)
    if parameter == "revenue_cagr":
        values["growth"] = (value,) * years
    elif parameter == "reinvestment_to_revenue":
        values["reinvestment"] = (value,) * years
    elif parameter == "terminal_operating_margin":
        values["terminal_margin"] = value
        if scenario.solve.variable == "terminal_operating_margin":
            anchor = scenario.solve.anchor_margin
            assert anchor is not None
            with localcontext(CONTEXT):
                values["margins"] = tuple(
                    (1 - w) * anchor + w * value for w in scenario.solve.margin_weights
                )
    else:
        values[parameter] = value


def calculate_sensitivity_cell(
    inputs: ValuationManifest, linked: BridgeResult, grid: SensitivityGrid, x: Decimal, y: Decimal
) -> SensitivityCell:
    scenario = next(s for s in inputs.assumptions.scenarios if s.name == grid.reference_scenario)
    value = None
    result = None
    evaluated = None
    equity = None
    reasons = linked.reasons
    if linked.eligible:
        try:
            at = (
                grid.conditional_parameter
                if grid.conditional_parameter is not None
                else scenario.solve.lower
            )
            values = resolved(scenario, at).model_dump()
            for parameter, v in ((grid.x_parameter, x), (grid.y_parameter, y)):
                _changed(values, parameter, v, scenario)
            forecast = Forecast.model_validate(values)
            with localcontext(CONTEXT):
                if grid.output == "reverse_implied_parameter":
                    assert linked.market_ev_target is not None
                    result = solve(forecast, scenario.solve, linked.market_ev_target)
                    value = result.representative
                    reasons = result.reasons
                    if value is not None:
                        _changed(values, scenario.solve.variable, value, scenario)
                        evaluated = evaluate(Forecast.model_validate(values))
                        assert linked.adjustment is not None
                        equity = evaluated.operating_ev + linked.adjustment
                        reasons += evaluated.reasons + (
                            ("nonpositive_common_equity",) if equity <= 0 else ()
                        )
                else:
                    assert linked.adjustment is not None and linked.shares is not None
                    evaluated = evaluate(forecast)
                    equity = evaluated.operating_ev + linked.adjustment
                    value = equity / linked.shares
                    reasons = evaluated.reasons + (
                        ("nonpositive_common_equity",) if equity <= 0 else ()
                    )
        except (ValueError, DecimalException, ArithmeticError):
            reasons = ("invalid_sensitivity_cell",)
    return SensitivityCell(
        x=x,
        y=y,
        value=value,
        solve=result,
        evaluation=evaluated,
        common_equity=equity,
        reasons=reasons,
    )


def summarize_sensitivity(
    grid: SensitivityGrid, cells: tuple[SensitivityCell, ...]
) -> SensitivityResult:
    xmid, ymid = len(grid.x_values) // 2, len(grid.y_values) // 2
    xoutputs = tuple(cells[i * len(grid.y_values) + ymid].value for i in range(len(grid.x_values)))
    youtputs = tuple(cells[xmid * len(grid.y_values) + i].value for i in range(len(grid.y_values)))
    elasticities = (elasticity(grid.x_values, xoutputs), elasticity(grid.y_values, youtputs))
    positions = ranks(elasticities)
    effects = tuple(
        SensitivityEffect(
            parameter=parameter,
            perturbations=values,
            outputs=outputs,
            elasticity=e,
            rank=rank,
            reasons=() if e is not None else ("ineligible_three_point_elasticity",),
        )
        for parameter, values, outputs, e, rank in zip(
            (grid.x_parameter, grid.y_parameter),
            (grid.x_values, grid.y_values),
            (xoutputs, youtputs),
            elasticities,
            positions,
            strict=True,
        )
    )
    return SensitivityResult(
        name=grid.name,
        output=grid.output,
        unit="fraction" if grid.output == "reverse_implied_parameter" else "currency_per_share",
        cells=tuple(cells),
        request=grid,
        effects=effects,
    )


def calculate_sensitivities(
    inputs: ValuationManifest, linked: BridgeResult
) -> tuple[SensitivityResult, ...]:
    return tuple(
        summarize_sensitivity(
            grid,
            tuple(
                calculate_sensitivity_cell(inputs, linked, grid, x, y)
                for x in grid.x_values
                for y in grid.y_values
            ),
        )
        for grid in inputs.assumptions.sensitivities
    )


def assemble_payload(
    inputs: ValuationManifest,
    linked: BridgeResult,
    scenarios: tuple[ScenarioResult, ...],
    sensitivities: tuple[SensitivityResult, ...],
) -> ValuationPayload:
    return ValuationPayload(
        version="s7-result-v1",
        evidence_mode=inputs.evidence_mode,
        fixture_label=inputs.fixture_label,
        dependency_hash=content_hash(inputs),
        model=inputs.model,
        policy=inputs.policy,
        assumptions=SafeAssumptions(
            content_hash=content_hash(inputs.assumptions),
            authored_at=inputs.assumptions.authored_at,
            retrospective=inputs.assumptions.retrospective,
            provenance="explicit_user_judgment",
            scenarios=inputs.assumptions.scenarios,
            forecast_dates=inputs.assumptions.forecast_dates,
            anchor_source_index=inputs.assumptions.anchor_source_index,
            anchor_method=inputs.assumptions.anchor_method,
            calendar=inputs.assumptions.calendar,
            leap_day=inputs.assumptions.leap_day,
        ),
        source_snapshot_id=inputs.source_snapshot_id,
        source_payload_hash=inputs.source_payload_hash,
        source_input_hash=inputs.source_input_hash,
        source_selector=inputs.selector,
        price=inputs.price,
        shares=inputs.shares,
        claims=inputs.claims,
        bridge_captured_before=inputs.bridge_captured_before,
        valuation_at=inputs.assumptions.valuation_at,
        currency=inputs.selector.currency,
        bridge=linked,
        scenarios=scenarios,
        scenario_dispersion=scenario_span(tuple(s.solve for s in scenarios)),
        numerical_uncertainty=tuple((s.name, s.solve.root_intervals) for s in scenarios),
        source_eligibility_reasons=inputs.source_eligibility_reasons,
        source_measurement_uncertainty=inputs.source_measurement_uncertainty,
        sensitivities=sensitivities,
        conclusions=tuple(
            "Conditional implied " + s.solve_variable + " for scenario " + s.name
            for s in scenarios
            if s.solve.state == "converged"
        ),
        reasons=linked.reasons,
    )


def calculate_payload(inputs: ValuationManifest) -> ValuationPayload:
    inputs = ValuationManifest.model_validate(inputs.model_dump())
    linked = bridge(inputs)
    return assemble_payload(
        inputs,
        linked,
        tuple(calculate_scenario(s, linked) for s in inputs.assumptions.scenarios),
        calculate_sensitivities(inputs, linked),
    )
