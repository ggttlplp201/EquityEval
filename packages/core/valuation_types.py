"""Versioned S7a pure numerical contracts; no persistence or provider defaults."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, WithJsonSchema, model_validator


def decimal_input(value: Any) -> Decimal:
    if isinstance(value, bool | float) or not isinstance(value, Decimal | str | int):
        raise ValueError("Exact Decimal input required")
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError("Finite Decimal required")
    return number


def bounded_decimal(value: Any) -> Decimal:
    if not isinstance(value, Decimal | str):
        raise ValueError("Financial inputs require Decimal or decimal strings")
    number = decimal_input(value)
    if (
        len(number.as_tuple().digits) > 40
        or abs(number.adjusted()) > 100
        or abs(int(number.as_tuple().exponent)) > 100
    ):
        raise ValueError("decimal_dcf_v1 input bounds exceeded")
    return number


Exact = Annotated[Decimal, BeforeValidator(decimal_input), WithJsonSchema({"type": "string"})]
Input = Annotated[
    Decimal,
    BeforeValidator(bounded_decimal),
    WithJsonSchema(
        {
            "type": "string",
            "format": "decimal_dcf_input",
            "pattern": r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$",
        }
    ),
]
Variable = Literal["revenue_cagr", "terminal_operating_margin", "reinvestment_to_revenue"]


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Forecast(Frozen):
    """Resolved numerical primitive. Public run validation separately requires N=5..10."""

    revenue_anchor: Exact
    growth: tuple[Exact, ...]
    margins: tuple[Exact, ...]
    taxes: tuple[Exact, ...]
    reinvestment: tuple[Exact, ...]
    wacc: Exact
    risk_free: Exact
    terminal_growth: Exact
    terminal_margin: Exact
    terminal_tax: Exact
    terminal_roic: Exact

    @model_validator(mode="after")
    def domains(self) -> Self:
        numbers = (
            self.revenue_anchor,
            *self.growth,
            *self.margins,
            *self.taxes,
            *self.reinvestment,
            self.wacc,
            self.risk_free,
            self.terminal_growth,
            self.terminal_margin,
            self.terminal_tax,
            self.terminal_roic,
        )
        # External Scenario inputs are capped at 40 digits. Internal solved values
        # retain the 80-digit representative; never round it out of its interval.
        if any(abs(v.adjusted()) > 100 or len(v.as_tuple().digits) > 80 for v in numbers):
            raise ValueError("Internal Decimal bounds exceeded")
        n = len(self.growth)
        if not 1 <= n <= 10 or any(
            len(v) != n for v in (self.margins, self.taxes, self.reinvestment)
        ):
            raise ValueError("Complete equal forecast vectors required")
        if self.revenue_anchor <= 0 or self.wacc <= 0 or self.terminal_roic <= 0:
            raise ValueError("Positive anchor, WACC and terminal ROIC required by model v1")
        if not 0 <= self.terminal_growth < min(self.risk_free, self.wacc, self.terminal_roic):
            raise ValueError("Model v1 terminal growth domain")
        if not 0 < self.terminal_margin <= 1 or not 0 <= self.terminal_tax < 1:
            raise ValueError("Model v1 terminal margin/tax domain")
        if any(g <= -1 for g in self.growth) or any(k < 0 for k in self.reinvestment):
            raise ValueError("Model v1 growth/reinvestment domain")
        if any(not 0 <= t <= 1 for t in self.taxes):
            raise ValueError("Tax rates must be fractions")
        return self


class SolveSpec(Frozen):
    variable: Variable
    lower: Input
    upper: Input
    absolute_tolerance: Input
    relative_tolerance: Input
    width_tolerance: Input
    max_iterations: Annotated[int, Field(strict=True, ge=1, le=256)]
    max_subdivisions: Annotated[int, Field(strict=True, ge=1, le=4096)]
    max_evaluations: Annotated[int, Field(strict=True, ge=1, le=10000)]
    margin_weights: tuple[Input, ...]
    anchor_margin: Input | None

    @model_validator(mode="after")
    def domain(self) -> Self:
        if (
            self.lower >= self.upper
            or self.absolute_tolerance <= 0
            or self.relative_tolerance < 0
            or self.width_tolerance <= 0
        ):
            raise ValueError("Ordered bounds and explicit positive absolute/width tolerances")
        if self.variable == "terminal_operating_margin":
            if (
                not 0 < self.lower < self.upper <= 1
                or self.anchor_margin is None
                or not self.margin_weights
                or self.margin_weights[-1] != 1
                or any(not 0 <= w <= 1 for w in self.margin_weights)
                or tuple(sorted(self.margin_weights)) != self.margin_weights
            ):
                raise ValueError(
                    "Explicit monotone margin fade and positive margin domain required"
                )
        elif self.margin_weights or self.anchor_margin is not None:
            raise ValueError("Margin fade only belongs to the margin solve")
        if self.variable == "revenue_cagr" and self.lower <= -1:
            raise ValueError("Growth domain must exceed -1")
        if self.variable == "reinvestment_to_revenue" and self.lower < 0:
            raise ValueError("Reinvestment domain cannot be negative")
        return self


class Interval(Frozen):
    lower: Exact
    upper: Exact

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.lower > self.upper:
            raise ValueError("Unordered interval")
        return self


class ForecastRow(Frozen):
    year: int
    revenue: Exact
    ebit: Exact
    cash_tax: Exact
    nopat: Exact
    reinvestment: Exact
    fcff: Exact
    pv: Exact


class Evaluation(Frozen):
    rows: tuple[ForecastRow, ...]
    terminal_revenue: Exact
    terminal_nopat: Exact
    terminal_reinvestment: Exact
    terminal_fcff: Exact
    terminal_value: Exact
    pv_terminal: Exact
    pv_explicit: Exact
    operating_ev: Exact
    terminal_contribution: Exact | None
    terminal_dominant: bool | None
    reasons: tuple[str, ...]


class ProofRegion(Frozen):
    domain: Interval
    residual: Interval
    derivative: Interval
    disposition: Literal["excluded", "unique_root", "unresolved"]
    left_residual: Interval | None
    right_residual: Interval | None
    root: Interval | None


class SolveResult(Frozen):
    state: Literal[
        "converged", "no_solution_in_domain", "non_unique", "inconclusive", "unavailable"
    ]
    representative: Exact | None
    interval: Interval | None
    residual: Interval | None
    root_intervals: tuple[Interval, ...]
    unresolved_domains: tuple[Interval, ...]
    proof: tuple[ProofRegion, ...]
    proof_revision: Literal["decimal_interval_model_v1"]
    evaluations: int
    subdivisions: int
    iterations: int
    reasons: tuple[str, ...]

    @model_validator(mode="after")
    def scalar_requires_certificate(self) -> Self:
        if self.state == "converged":
            if (
                self.representative is None
                or self.interval is None
                or self.residual is None
                or not self.interval.lower <= self.representative <= self.interval.upper
                or len(self.root_intervals) != 1
                or not self.proof
            ):
                raise ValueError("Converged scalar requires retained interval and proof")
        elif self.representative is not None or self.interval is not None:
            raise ValueError("Only certified unique convergence has a headline scalar")
        return self
