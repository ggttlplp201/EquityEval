"""S7a independent hand oracles and adversarial Decimal solver contracts."""

from decimal import Decimal as D
from decimal import localcontext

import pytest
from equity_core.valuation import evaluate, scenario_span, solve
from equity_core.valuation_types import Forecast, SolveSpec


def forecast(years=5, **changes):
    values = dict(
        revenue_anchor=D("100"),
        growth=(D(".10"),) * years,
        margins=(D(".20"),) * years,
        taxes=(D(".25"),) * years,
        reinvestment=(D(".05"),) * years,
        wacc=D(".10"),
        risk_free=D(".04"),
        terminal_growth=D(".02"),
        terminal_margin=D(".20"),
        terminal_tax=D(".25"),
        terminal_roic=D(".08"),
    )
    values.update(changes)
    return Forecast(**values)


def spec(variable="revenue_cagr", lower="0", upper=".20", **changes):
    values = dict(
        variable=variable,
        lower=D(lower),
        upper=D(upper),
        absolute_tolerance=D("1e-18"),
        relative_tolerance=D("1e-20"),
        width_tolerance=D("1e-20"),
        max_iterations=256,
        max_subdivisions=4096,
        max_evaluations=10000,
        margin_weights=(),
        anchor_margin=None,
    )
    if variable == "terminal_operating_margin":
        values.update(margin_weights=(D(1),) * 5, anchor_margin=D(".2"))
    values.update(changes)
    return SolveSpec(**values)


def test_h01_no_growth_three_period_primitive():
    result = evaluate(forecast(3, growth=(D(0),) * 3))
    assert [r.fcff for r in result.rows] == [D(10)] * 3
    assert result.terminal_revenue == D(102)
    assert result.terminal_nopat == D("15.3")
    assert result.terminal_reinvestment == D("3.825")
    assert result.terminal_fcff == D("11.475")
    assert result.terminal_value == D("143.4375")
    with localcontext() as ctx:
        ctx.prec = 80
        assert abs(result.operating_ev - D("176.5375") / D("1.331")) < D("1e-70")
    assert result.terminal_dominant


@pytest.mark.parametrize("years,expected,dominant", [(3, "173.4375", True), (5, "193.4375", False)])
def test_h02_h03_growth_hand_oracle(years, expected, dominant):
    result = evaluate(forecast(years))
    assert [r.pv for r in result.rows] == [D(10)] * years
    assert result.pv_terminal == D("143.4375")
    assert result.operating_ev == D(expected)
    assert result.terminal_dominant is dominant
    if years == 5:
        assert result.terminal_fcff == D("18.48060225")
        assert result.terminal_value == D("231.007528125")


@pytest.mark.parametrize(
    "variable,lower,upper,expected",
    [
        ("revenue_cagr", "0", ".20", ".10"),
        ("reinvestment_to_revenue", "0", ".10", ".05"),
        ("terminal_operating_margin", ".10", ".30", ".20"),
    ],
)
def test_h04_all_single_unknowns_certified(variable, lower, upper, expected):
    result = solve(forecast(), spec(variable, lower, upper), D("193.4375"))
    assert result.state == "converged", result
    assert result.interval.lower <= D(expected) <= result.interval.upper
    assert result.interval.lower <= result.representative <= result.interval.upper
    assert result.interval.upper - result.interval.lower <= D("1e-20")
    assert result.proof and result.evaluations > 0
    assert result.residual.lower <= 0 <= result.residual.upper


def test_h04_scenarios_hold_same_target_and_keep_numeric_intervals():
    results = tuple(
        solve(
            forecast(reinvestment=(D(k),) * 5),
            spec("terminal_operating_margin", ".10", ".30"),
            D("193.4375"),
        )
        for k in (".025", ".05", ".075")
    )
    assert all(r.state == "converged" for r in results)
    with localcontext() as ctx:
        ctx.prec = 80
        for result, expected in zip(results, (D(659) / 3495, D(".2"), D(739) / 3495), strict=True):
            assert result.interval.lower <= expected <= result.interval.upper
    span = scenario_span(results)
    assert span.lower == results[0].representative
    assert span.upper == results[2].representative
    assert scenario_span(results[:1]) is None
    failed = solve(forecast(), spec(max_evaluations=1), D("193.4375"))
    assert scenario_span((*results, failed)) is None


def test_h05_negative_cashflows_have_two_growth_roots():
    inputs = forecast(
        margins=(D("-1.1"), D(0), D(0), D(0), D(0)),
        taxes=(D(0),) * 5,
        reinvestment=(D(0),) * 5,
        terminal_margin=D(".161051"),
        terminal_tax=D(0),
        terminal_growth=D(0),
    )
    result = solve(inputs, spec(lower="-.99", upper="0"), D(-20))
    assert result.state == "non_unique", result
    assert len(result.root_intervals) == 2
    assert result.representative is None
    assert result.proof


def test_loss_does_not_create_tax_refund_or_clamp_cashflow():
    result = evaluate(forecast(growth=(D(0),) * 5, margins=(D("-.1"),) * 5))
    assert result.rows[0].cash_tax == 0
    assert result.rows[0].nopat == -10
    assert result.rows[0].fcff == -15


@pytest.mark.parametrize(
    "change",
    [
        {"revenue_anchor": D(0)},
        {"growth": (D(-1),) * 5},
        {"wacc": D(0)},
        {"terminal_growth": D(".04")},
        {"terminal_roic": D(0)},
        {"terminal_tax": D(1)},
        {"terminal_margin": D(0)},
        {"reinvestment": (D("-.1"),) * 5},
        {"revenue_anchor": 1.5},
        {"wacc": D("NaN")},
        {"wacc": D("1e101")},
    ],
)
def test_invalid_domains_never_produce_values(change):
    with pytest.raises(ValueError):
        forecast(**change)


def test_no_solution_in_declared_domain_is_certified():
    result = solve(forecast(), spec("reinvestment_to_revenue", "0", ".1"), D(1000))
    assert result.state == "no_solution_in_domain"
    assert result.representative is None
    assert result.proof


def test_budget_exhaustion_has_no_headline_scalar():
    result = solve(forecast(), spec(max_evaluations=1), D("193.4375"))
    assert result.state == "inconclusive"
    assert result.representative is None
    assert result.evaluations <= 1


def test_caller_decimal_context_cannot_change_saved_math():
    expected = evaluate(forecast())
    solved = solve(forecast(), spec(), D("193.4375"))
    with localcontext() as ctx:
        ctx.prec = 6
        ctx.rounding = "ROUND_DOWN"
        assert evaluate(forecast()) == expected
        assert solve(forecast(), spec(), D("193.4375")) == solved


def test_terminal_growth_changes_reinvestment_not_only_denominator():
    # At ROIC == WACC, terminal value is independent of g for fixed NOPAT_N.
    low = evaluate(forecast(terminal_growth=D(0), terminal_roic=D(".10")))
    high = evaluate(forecast(terminal_growth=D(".03"), terminal_roic=D(".10")))
    # Revenue N+1 also changes: TV / (1+g) is invariant, not TV itself.
    with localcontext() as ctx:
        ctx.prec = 80
        assert abs(high.terminal_value / D("1.03") - low.terminal_value) < D("1e-70")


def test_nontrivial_margin_fade_has_independent_linear_oracle():
    s = spec(
        "terminal_operating_margin",
        ".1",
        ".4",
        anchor_margin=D(".1"),
        margin_weights=(D(0), D(".25"), D(".5"), D(".75"), D(1)),
    )
    result = solve(forecast(), s, D("193.4375"))
    assert result.state == "converged"
    with localcontext() as ctx:
        ctx.prec = 80
        expected = D(213) / 965  # EV = 904.6875*m - 6.25
        assert result.interval.lower <= expected <= result.interval.upper


@pytest.mark.parametrize(
    "margin,ratio,dominant",
    [
        (".5", ".75", False),
        (".49999", None, True),
        ("-.1", None, True),
        ("-1.5", None, None),
        ("-2", None, None),
    ],
)
def test_terminal_dominance_strict_boundary_and_signed_components(margin, ratio, dominant):
    result = evaluate(
        forecast(
            1,
            margins=(D(margin),),
            taxes=(D(0),),
            reinvestment=(D(0),),
            terminal_margin=D(".15"),
            terminal_tax=D(0),
            terminal_growth=D(0),
        )
    )
    assert result.pv_terminal == D(150)
    assert result.terminal_dominant is dominant
    if ratio:
        assert result.terminal_contribution == D(ratio)
    if dominant is None:
        assert result.terminal_contribution is None
        assert result.reasons == ("terminal_ratio_not_meaningful",)
    if margin == "-.1":
        assert result.terminal_contribution > 1


def test_boundary_root_remains_honestly_inconclusive_without_existence_certificate():
    result = solve(forecast(), spec(lower=".10", upper=".20"), D("193.4375"))
    assert result.state == "inconclusive"
    assert result.representative is None
    assert result.unresolved_domains


@pytest.mark.parametrize("continuum", [False, True])
def test_tangent_or_continuum_is_never_excluded_by_endpoint_signs(continuum):
    inputs = forecast(
        margins=(D(0), D(0), D(0), D(0), D(-1))
        if continuum
        else (D("-.022"), D(".0121"), D(0), D(0), D(-1)),
        taxes=(D(0),) * 5,
        reinvestment=(D(0),) * 5,
        terminal_margin=D(".1"),
        terminal_tax=D(0),
        terminal_growth=D(0),
    )
    # Non-continuum residual is (z-1)^2 at target -1; continuum EV is zero.
    result = solve(
        inputs, spec(lower="-.5", upper=".5", max_evaluations=100), D(0) if continuum else D(-1)
    )
    assert result.state == "inconclusive"
    assert result.representative is None
    assert result.unresolved_domains


@pytest.mark.parametrize("absolute,width", [("1e-40", "1"), ("1e9", "1e-40")])
def test_neither_width_nor_residual_tolerance_alone_can_converge(absolute, width):
    result = solve(
        forecast(),
        spec(
            absolute_tolerance=D(absolute),
            relative_tolerance=D(0),
            width_tolerance=D(width),
            max_evaluations=20,
        ),
        D("193.4375"),
    )
    assert result.state == "inconclusive"
    assert result.evaluations <= 20


def test_certified_regions_cover_whole_domain_without_hidden_gap():
    result = solve(forecast(), spec(), D("193.4375"))
    regions = sorted(result.proof, key=lambda p: p.domain.lower)
    assert regions[0].domain.lower == 0
    assert regions[-1].domain.upper == D(".2")
    assert all(a.domain.upper == b.domain.lower for a, b in zip(regions, regions[1:], strict=False))
    assert all(p.disposition != "unresolved" for p in regions)


def test_margin_tax_kinks_are_explicit_certified_domain_boundaries():
    s = spec(
        "terminal_operating_margin",
        ".05",
        ".4",
        anchor_margin=D("-.1"),
        margin_weights=(D(0), D(".25"), D(".5"), D(".75"), D(1)),
    )
    result = solve(forecast(), s, D("134.0625"))
    assert result.state == "converged"
    assert result.interval.lower <= D(".2") <= result.interval.upper
    for kink in (D(".1"), D(".3")):
        assert any(p.domain.lower == kink or p.domain.upper == kink for p in result.proof)
        assert not any(p.domain.lower < kink < p.domain.upper for p in result.proof)
