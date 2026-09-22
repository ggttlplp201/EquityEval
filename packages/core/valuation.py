"""Pure Decimal FCFF and bounded model-specific interval root isolation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DecimalException,
    localcontext,
)
from typing import Literal

from equity_core.valuation_types import (
    Evaluation,
    Forecast,
    ForecastRow,
    Interval,
    ProofRegion,
    SolveResult,
    SolveSpec,
)

D = Decimal
# Versioned algorithm settings, not market/financial assumptions.
CONTEXT = Context(prec=80, rounding=ROUND_HALF_EVEN, Emin=-9999, Emax=9999)


def evaluate(inputs: Forecast) -> Evaluation:
    inputs = Forecast.model_validate(inputs.model_dump())
    with localcontext(CONTEXT):
        revenue = inputs.revenue_anchor
        rows = []
        for year, (growth, margin, tax, k) in enumerate(
            zip(inputs.growth, inputs.margins, inputs.taxes, inputs.reinvestment, strict=True), 1
        ):
            revenue *= 1 + growth
            ebit = revenue * margin
            cash_tax = max(ebit, D(0)) * tax
            nopat = ebit - cash_tax
            reinvestment = revenue * k
            fcff = nopat - reinvestment
            rows.append(
                ForecastRow(
                    year=year,
                    revenue=revenue,
                    ebit=ebit,
                    cash_tax=cash_tax,
                    nopat=nopat,
                    reinvestment=reinvestment,
                    fcff=fcff,
                    pv=fcff / (1 + inputs.wacc) ** year,
                )
            )
        tr = revenue * (1 + inputs.terminal_growth)
        tn = tr * inputs.terminal_margin * (1 - inputs.terminal_tax)
        ti = tn * inputs.terminal_growth / inputs.terminal_roic
        tf = tn - ti
        tv = tf / (inputs.wacc - inputs.terminal_growth)
        pv = tv / (1 + inputs.wacc) ** len(rows)
        explicit = sum((r.pv for r in rows), D(0))
        ev = explicit + pv
        ratio = pv / ev if ev > 0 else None
        return Evaluation(
            rows=tuple(rows),
            terminal_revenue=tr,
            terminal_nopat=tn,
            terminal_reinvestment=ti,
            terminal_fcff=tf,
            terminal_value=tv,
            pv_terminal=pv,
            pv_explicit=explicit,
            operating_ev=ev,
            terminal_contribution=ratio,
            terminal_dominant=ratio > D(".75") if ratio is not None else None,
            reasons=("terminal_ratio_not_meaningful",) if ratio is None else (),
        )


@dataclass(frozen=True)
class Bounds:
    """Outward-rounded interval operations. Inputs are exact decimal endpoints."""

    lo: Decimal
    hi: Decimal

    @classmethod
    def point(cls, value: Decimal | int) -> Bounds:
        return cls(D(value), D(value))

    def public(self) -> Interval:
        return Interval(lower=self.lo, upper=self.hi)

    def __add__(self, other: Bounds) -> Bounds:
        with localcontext(CONTEXT) as ctx:
            ctx.rounding = ROUND_FLOOR
            lo = self.lo + other.lo
            ctx.rounding = ROUND_CEILING
            hi = self.hi + other.hi
        return Bounds(lo, hi)

    def __neg__(self) -> Bounds:
        return Bounds(self.hi.copy_negate(), self.lo.copy_negate())

    def __sub__(self, other: Bounds) -> Bounds:
        return self + -other

    def __mul__(self, other: Bounds) -> Bounds:
        with localcontext(CONTEXT) as ctx:
            ctx.rounding = ROUND_FLOOR
            lo = min(a * b for a in (self.lo, self.hi) for b in (other.lo, other.hi))
            ctx.rounding = ROUND_CEILING
            hi = max(a * b for a in (self.lo, self.hi) for b in (other.lo, other.hi))
        return Bounds(lo, hi)

    def __truediv__(self, other: Bounds) -> Bounds:
        if other.lo <= 0 <= other.hi:
            raise ArithmeticError("Interval denominator crosses zero")
        with localcontext(CONTEXT) as ctx:
            ctx.rounding = ROUND_FLOOR
            lo = min(a / b for a in (self.lo, self.hi) for b in (other.lo, other.hi))
            ctx.rounding = ROUND_CEILING
            hi = max(a / b for a in (self.lo, self.hi) for b in (other.lo, other.hi))
        return Bounds(lo, hi)

    def power(self, exponent: int) -> Bounds:
        result = Bounds.point(1)
        for _ in range(exponent):
            result = result * self
        return result

    def sign(self) -> int:
        return 1 if self.lo > 0 else -1 if self.hi < 0 else 0


@dataclass(frozen=True)
class Dual:
    value: Bounds
    derivative: Bounds

    @classmethod
    def constant(cls, value: Decimal | int) -> Dual:
        return cls(Bounds.point(value), Bounds.point(0))

    def __add__(self, other: Dual) -> Dual:
        return Dual(self.value + other.value, self.derivative + other.derivative)

    def __sub__(self, other: Dual) -> Dual:
        return Dual(self.value - other.value, self.derivative - other.derivative)

    def __mul__(self, other: Dual) -> Dual:
        return Dual(
            self.value * other.value, self.derivative * other.value + self.value * other.derivative
        )

    def __truediv__(self, other: Dual) -> Dual:
        return Dual(
            self.value / other.value,
            (self.derivative * other.value - self.value * other.derivative) / other.value.power(2),
        )

    def positive(self) -> Dual:
        if self.value.lo >= 0:
            return self
        if self.value.hi <= 0:
            return Dual.constant(0)
        # Generalized derivative includes both pieces at the continuous tax kink.
        return Dual(
            Bounds(D(0), self.value.hi),
            Bounds(min(D(0), self.derivative.lo), max(D(0), self.derivative.hi)),
        )


def _residual(inputs: Forecast, spec: SolveSpec, domain: Bounds, target: Decimal) -> Dual:
    c = Dual.constant
    x = Dual(domain, Bounds.point(1))
    revenue = c(inputs.revenue_anchor)
    total = c(0)
    discount = c(1)
    for i in range(len(inputs.growth)):
        g = x if spec.variable == "revenue_cagr" else c(inputs.growth[i])
        k = x if spec.variable == "reinvestment_to_revenue" else c(inputs.reinvestment[i])
        if spec.variable == "terminal_operating_margin":
            assert spec.anchor_margin is not None
            weight = c(spec.margin_weights[i])
            margin = (c(1) - weight) * c(spec.anchor_margin) + weight * x
        else:
            margin = c(inputs.margins[i])
        revenue = revenue * (c(1) + g)
        ebit = revenue * margin
        nopat = ebit - ebit.positive() * c(inputs.taxes[i])
        discount = discount * (c(1) + c(inputs.wacc))
        total = total + (nopat - revenue * k) / discount
    terminal_margin = (
        x if spec.variable == "terminal_operating_margin" else c(inputs.terminal_margin)
    )
    tn = (
        revenue
        * (c(1) + c(inputs.terminal_growth))
        * terminal_margin
        * (c(1) - c(inputs.terminal_tax))
    )
    terminal = (
        (tn - tn * c(inputs.terminal_growth) / c(inputs.terminal_roic))
        / (c(inputs.wacc) - c(inputs.terminal_growth))
        / discount
    )
    return total + terminal - c(target)


class BudgetExhausted(Exception):
    pass


@dataclass
class Solver:
    inputs: Forecast
    spec: SolveSpec
    target: Decimal
    evaluations: int = 0
    iterations: int = 0
    subdivisions: int = 0

    def at(self, bounds: Bounds) -> Dual:
        if self.evaluations >= self.spec.max_evaluations:
            raise BudgetExhausted
        self.evaluations += 1
        return _residual(self.inputs, self.spec, bounds, self.target)

    def refine(self, bracket: Bounds, left_sign: int) -> tuple[Bounds, Bounds] | None:
        tolerance = self.spec.absolute_tolerance + self.spec.relative_tolerance * abs(self.target)
        for _ in range(self.spec.max_iterations):
            self.iterations += 1
            residual = self.at(bracket).value
            if (
                bracket.hi - bracket.lo <= self.spec.width_tolerance
                and max(abs(residual.lo), abs(residual.hi)) <= tolerance
            ):
                return bracket, residual
            mid = (bracket.lo + bracket.hi) / 2
            if mid in (bracket.lo, bracket.hi):
                return None
            sign = self.at(Bounds.point(mid)).value.sign()
            if sign:
                bracket = Bounds(mid, bracket.hi) if sign == left_sign else Bounds(bracket.lo, mid)
            else:
                # Never infer an exact root from a rounded residual. Enclose it by
                # two certified opposite signs, or leave the old region unresolved.
                low, high = (bracket.lo + mid) / 2, (mid + bracket.hi) / 2
                ls, hs = (
                    self.at(Bounds.point(low)).value.sign(),
                    self.at(Bounds.point(high)).value.sign(),
                )
                if ls == left_sign and hs == -left_sign:
                    bracket = Bounds(low, high)
                else:
                    return None
        return None

    def partition(self) -> list[Bounds]:
        cuts = {self.spec.lower, self.spec.upper}
        if self.spec.variable == "terminal_operating_margin":
            assert self.spec.anchor_margin is not None
            for weight in self.spec.margin_weights:
                if weight > 0:
                    # Keep both outward endpoints when a rational kink is not
                    # exactly representable. Its narrow band uses generalized slopes.
                    kink = (
                        -Bounds.point(self.spec.anchor_margin)
                        * (Bounds.point(1) - Bounds.point(weight))
                    ) / Bounds.point(weight)
                    cuts.update(
                        v for v in (kink.lo, kink.hi) if self.spec.lower < v < self.spec.upper
                    )
        ordered = sorted(cuts)
        self.subdivisions = len(ordered) - 2
        return [Bounds(a, b) for a, b in zip(ordered, ordered[1:], strict=False)]

    def run(self) -> SolveResult:
        pending = [Bounds(self.spec.lower, self.spec.upper)]
        proofs: list[ProofRegion] = []
        roots: list[Bounds] = []
        residuals: list[Bounds] = []
        unresolved = False
        reason = "uncertified_domain"
        current: Bounds | None = None
        try:
            partition = self.partition()
            if self.subdivisions > self.spec.max_subdivisions:
                self.subdivisions = 0
                raise BudgetExhausted
            pending = list(reversed(partition))
            while pending:
                current = pending.pop()
                result = self.at(current)
                left = right = None
                root = None
                disposition: Literal["excluded", "unique_root", "unresolved"] = "unresolved"
                if result.value.sign():
                    disposition = "excluded"
                elif result.derivative.sign():
                    left = self.at(Bounds.point(current.lo)).value
                    right = self.at(Bounds.point(current.hi)).value
                    if left.sign() and left.sign() == right.sign():
                        disposition = "excluded"
                    elif left.sign() * right.sign() == -1:
                        refined = self.refine(current, left.sign())
                        if refined:
                            root, residual = refined
                            roots.append(root)
                            residuals.append(residual)
                            disposition = "unique_root"
                if disposition == "unresolved":
                    mid = (current.lo + current.hi) / 2
                    if (
                        self.subdivisions < self.spec.max_subdivisions
                        and mid not in (current.lo, current.hi)
                        and current.hi - current.lo > self.spec.width_tolerance
                    ):
                        self.subdivisions += 1
                        pending.extend((Bounds(mid, current.hi), Bounds(current.lo, mid)))
                        current = None
                        continue
                    unresolved = True
                proofs.append(
                    ProofRegion(
                        domain=current.public(),
                        residual=result.value.public(),
                        derivative=result.derivative.public(),
                        disposition=disposition,
                        left_residual=left.public() if left else None,
                        right_residual=right.public() if right else None,
                        root=root.public() if root else None,
                    )
                )
                current = None
        except (BudgetExhausted, DecimalException, ArithmeticError) as exc:
            unresolved = True
            reason = (
                "evaluation_budget" if isinstance(exc, BudgetExhausted) else "numeric_precision"
            )
        # Retain every unvisited region on exhaustion, without fabricated residuals.
        remaining = ([current] if current else []) + pending
        reasons = (reason,) if unresolved or remaining else ()
        state: Literal["converged", "no_solution_in_domain", "non_unique", "inconclusive"]
        state = (
            "inconclusive"
            if reasons
            else "non_unique"
            if len(roots) > 1
            else "converged"
            if roots
            else "no_solution_in_domain"
        )
        # Candidate intervals remain separate from a certified whole-domain result.
        chosen = roots[0] if state == "converged" else None
        return SolveResult(
            state=state,
            representative=(chosen.lo + chosen.hi) / 2 if chosen else None,
            interval=chosen.public() if chosen else None,
            residual=residuals[0].public() if chosen else None,
            root_intervals=tuple(r.public() for r in roots),
            unresolved_domains=tuple(r.public() for r in remaining)
            + tuple(p.domain for p in proofs if p.disposition == "unresolved"),
            proof=tuple(proofs),
            proof_revision="decimal_interval_model_v1",
            evaluations=self.evaluations,
            subdivisions=self.subdivisions,
            iterations=self.iterations,
            reasons=reasons,
        )


def solve(inputs: Forecast, spec: SolveSpec, target: Decimal) -> SolveResult:
    inputs = Forecast.model_validate(inputs.model_dump())
    spec = SolveSpec.model_validate(spec.model_dump())
    if not isinstance(target, Decimal) or not target.is_finite():
        raise ValueError("Finite Decimal target required")
    if spec.variable == "terminal_operating_margin" and len(spec.margin_weights) != len(
        inputs.growth
    ):
        raise ValueError("Margin fade must cover every forecast year")
    with localcontext(CONTEXT):
        return Solver(inputs, spec, target).run()


def scenario_span(results: tuple[SolveResult, ...]) -> Interval | None:
    if len(results) < 2 or any(r.state != "converged" for r in results):
        return None
    values = [r.representative for r in results if r.representative is not None]
    return Interval(lower=min(values), upper=max(values))
