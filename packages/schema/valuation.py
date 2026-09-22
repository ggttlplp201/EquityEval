"""D038 synthetic valuation contracts. Exact sources, explicit judgments, saved outcomes."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from equity_core.valuation_types import (
    Evaluation,
    Exact,
    Frozen,
    Input,
    Interval,
    SolveResult,
    SolveSpec,
    Variable,
)
from equity_schema.fundamentals import Nonempty, SelectionKey, Sha256
from equity_schema.fundamentals_canonical import canonical_json, parse_canonical
from pydantic import AwareDatetime, Field, StringConstraints, model_validator

Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
CLAIM_KINDS = ("cash", "nonoperating_assets", "debt", "leases", "preferred", "nci", "other")
ClaimKind = Literal["cash", "nonoperating_assets", "debt", "leases", "preferred", "nci", "other"]


class ModelDefinition(Frozen):
    revision: Literal["reverse_fcff_operating_v1"]
    cash_tax: Literal["tax_on_positive_ebit_no_nol_v1"]
    terminal: Literal["gordon_growth_roic_reinvestment_v1"]
    terminal_domain: Literal["0<=g<min(risk_free,wacc,roic);wacc>0;roic>0;margin>0;tax<1"]
    forecast: Literal["nominal_annual_end_period_v1"]
    reinvestment: Literal["net_capex_plus_change_noncash_operating_wc"]
    lease_treatment: Literal["operating_lease_capitalized_consistent_ebit_v1"]
    bridge: Literal["economic_claim_values_single_common_pool_no_dilution_v1"]
    numeric: Literal["decimal80_half_even_interval_outward_v1"]
    solver: Literal["decimal_interval_model_v1"]
    engine_build: Sha256


class ScalarBinding(Frozen):
    kind: Literal["scalar"]
    value: Input


class VectorBinding(Frozen):
    kind: Literal["vector"]
    value: tuple[Input, ...]


class SolvedBinding(Frozen):
    kind: Literal["solved"]
    variable: Variable


class ScheduleBinding(Frozen):
    kind: Literal["schedule"]
    value: tuple[date, ...]


class SolverBinding(Frozen):
    kind: Literal["solver"]
    value: SolveSpec


JudgmentBinding = Annotated[
    ScalarBinding | VectorBinding | SolvedBinding | ScheduleBinding | SolverBinding,
    Field(discriminator="kind"),
]


class Judgment(Frozen):
    scenario: Nonempty
    parameter: Nonempty
    binding: JudgmentBinding
    origin: Literal["user_judgment"]
    author_id: Nonempty
    authored_at: AwareDatetime
    known_at: AwareDatetime
    unit: Literal["fraction", "currency", "years", "schedule", "solver_policy"]
    rationale: Annotated[str, StringConstraints(min_length=1, max_length=4000)]
    effective_from: date
    effective_to: date
    supporting_hashes: tuple[Sha256, ...]

    @model_validator(mode="after")
    def dates(self) -> Self:
        if self.effective_to < self.effective_from:
            raise ValueError("Judgment effective period reversed")
        return self


class Scenario(Frozen):
    """Null is permitted only at a declared solved slot; no hidden fixed fallback."""

    name: Nonempty
    revenue_anchor: Input
    growth: tuple[Input, ...] | None
    margins: tuple[Input, ...] | None
    taxes: tuple[Input, ...]
    reinvestment: tuple[Input, ...] | None
    wacc: Input
    risk_free: Input
    terminal_growth: Input
    terminal_margin: Input | None
    terminal_tax: Input
    terminal_roic: Input
    solve: SolveSpec

    @model_validator(mode="after")
    def slots(self) -> Self:
        v = self.solve.variable
        if (
            (self.growth is None) != (v == "revenue_cagr")
            or (self.reinvestment is None) != (v == "reinvestment_to_revenue")
            or (self.margins is None) != (v == "terminal_operating_margin")
            or (self.terminal_margin is None) != (v == "terminal_operating_margin")
        ):
            raise ValueError("Only the declared solved parameter may be unspecified")
        n = len(self.taxes)
        if not 5 <= n <= 10:
            raise ValueError("Public model requires 5–10 forecast years")
        if v == "terminal_operating_margin" and len(self.solve.margin_weights) != n:
            raise ValueError("Full margin fade required")
        return self


def binding_for(scenario: Scenario, parameter: str, dates: tuple[date, ...]) -> JudgmentBinding:
    """Typed identity binding only; does not infer values or provenance."""
    if parameter == "schedule":
        return ScheduleBinding(kind="schedule", value=dates)
    if parameter == "solver_policy":
        return SolverBinding(kind="solver", value=scenario.solve)
    value = getattr(scenario, parameter)
    if value is None:
        return SolvedBinding(kind="solved", variable=scenario.solve.variable)
    if isinstance(value, tuple):
        return VectorBinding(kind="vector", value=value)
    return ScalarBinding(kind="scalar", value=value)


class SensitivityGrid(Frozen):
    name: Nonempty
    reference_scenario: Nonempty
    output: Literal["reverse_implied_parameter", "conditional_reprice"]
    x_parameter: Literal[
        "wacc",
        "terminal_growth",
        "revenue_cagr",
        "terminal_operating_margin",
        "reinvestment_to_revenue",
    ]
    x_values: tuple[Input, ...]
    y_parameter: Literal[
        "wacc",
        "terminal_growth",
        "revenue_cagr",
        "terminal_operating_margin",
        "reinvestment_to_revenue",
    ]
    y_values: tuple[Input, ...]
    conditional_parameter: Input | None

    @model_validator(mode="after")
    def roster(self) -> Self:
        if (
            not self.x_values
            or not self.y_values
            or self.x_parameter == self.y_parameter
            or len(self.x_values) * len(self.y_values) > 100
            or len(set(self.x_values)) != len(self.x_values)
            or len(set(self.y_values)) != len(self.y_values)
        ):
            raise ValueError("Explicit distinct axes; maximum 100 cells per grid")
        if (self.conditional_parameter is None) != (self.output == "reverse_implied_parameter"):
            raise ValueError("Only repricing fixes the original solved parameter")
        return self


class AssumptionContent(Frozen):
    authored_at: AwareDatetime
    author_id: Nonempty
    valuation_at: AwareDatetime
    retrospective: bool
    calendar: Literal["calendar_year_equivalent"]
    leap_day: Literal["february_28"]
    forecast_dates: tuple[date, ...]
    anchor_method: Literal["explicit_carry_forward_annual_run_rate"]
    anchor_source_index: Annotated[int, Field(strict=True, ge=0)]
    scenarios: Annotated[tuple[Scenario, ...], Field(min_length=1, max_length=12)]
    sensitivities: Annotated[tuple[SensitivityGrid, ...], Field(max_length=4)]
    judgments: tuple[Judgment, ...]

    @model_validator(mode="after")
    def completeness(self) -> Self:
        if self.retrospective != (self.authored_at > self.valuation_at):
            raise ValueError("Retrospective classification follows immutable authorship")
        names = [s.name for s in self.scenarios]
        if len(set(names)) != len(names) or len({s.solve.variable for s in self.scenarios}) != 1:
            raise ValueError("Unique scenario names and one common solved variable required")
        n = len(self.forecast_dates)
        today = self.valuation_at.astimezone(UTC).date()
        expected = []
        for year in range(1, n + 1):
            try:
                expected.append(today.replace(year=today.year + year))
            except ValueError:
                expected.append(date(today.year + year, 2, 28))
        if tuple(expected) != self.forecast_dates or any(len(s.taxes) != n for s in self.scenarios):
            raise ValueError("Explicit annual anniversary forecast dates required")
        keys = {(j.scenario, j.parameter) for j in self.judgments}
        required = {
            "revenue_anchor",
            "growth",
            "margins",
            "taxes",
            "reinvestment",
            "wacc",
            "risk_free",
            "terminal_growth",
            "terminal_margin",
            "terminal_tax",
            "terminal_roic",
            "schedule",
            "solver_policy",
        }
        if keys != {(name, key) for name in names for key in required} or len(keys) != len(
            self.judgments
        ):
            raise ValueError("Every scenario/parameter requires one immutable judgment binding")
        scenarios = {scenario.name: scenario for scenario in self.scenarios}
        for judgment in self.judgments:
            if (
                judgment.author_id != self.author_id
                or judgment.authored_at != self.authored_at
                or judgment.known_at != self.authored_at
                or canonical_json(judgment.binding)
                != canonical_json(
                    binding_for(
                        scenarios[judgment.scenario], judgment.parameter, self.forecast_dates
                    )
                )
            ):
                raise ValueError("Judgment value or authorship differs from bound scenario")
            expected_unit = (
                "currency"
                if judgment.parameter == "revenue_anchor"
                else (
                    judgment.parameter
                    if judgment.parameter in ("schedule", "solver_policy")
                    else "fraction"
                )
            )
            if judgment.unit != expected_unit:
                raise ValueError("Judgment unit differs from model parameter unit")
        for grid in self.sensitivities:
            if grid.reference_scenario not in names or (
                grid.output == "reverse_implied_parameter"
                and self.scenarios[0].solve.variable in (grid.x_parameter, grid.y_parameter)
            ):
                raise ValueError("Unknown reference or solved parameter used as reverse axis")
        if len({g.name for g in self.sensitivities}) != len(self.sensitivities):
            raise ValueError("Duplicate grid name")
        return self


class AssumptionCreate(Frozen):
    parent_id: UUID | None
    idempotency_key: Nonempty
    content: AssumptionContent


class AssumptionSaved(Frozen):
    id: UUID
    parent_id: UUID | None
    content_hash: Sha256
    content: AssumptionContent


class ClaimCoverage(Frozen):
    component: ClaimKind
    disposition: Literal["included", "excluded", "unknown"]
    explanation: Nonempty
    evidence_hash: Sha256 | None


class Claim(Frozen):
    kind: ClaimKind
    coverage: tuple[ClaimCoverage, ...] | None
    economic_claim_ids: tuple[Nonempty, ...]
    state: Literal["eligible_amount", "evidenced_absence", "unavailable"]
    amount: Input | None
    currency: Currency
    as_of: date
    known_at: AwareDatetime
    captured_at: AwareDatetime
    known_basis: Literal["owner_reviewed_instant", "date_only", "unproven"]
    basis: Literal["economic_value", "absence", "unreviewed"]
    evidence_hash: Sha256
    fixture_url: Annotated[str, StringConstraints(pattern=r"^https://example\.invalid/")]
    reasons: tuple[Nonempty, ...]

    @model_validator(mode="after")
    def amount_state(self) -> Self:
        if self.state == "eligible_amount" and (
            self.amount is None
            or self.amount < 0
            or self.basis != "economic_value"
            or not self.economic_claim_ids
        ):
            raise ValueError("Eligible economic claim requires amount, basis and scope IDs")
        if self.state == "evidenced_absence" and (
            self.amount != 0 or self.basis != "absence" or not self.economic_claim_ids
        ):
            raise ValueError("Absence requires explicit zero and scoped evidence")
        if self.state == "unavailable" and (self.amount is not None or not self.reasons):
            raise ValueError("Unavailable claim requires null and reasons")
        if len(set(self.economic_claim_ids)) != len(self.economic_claim_ids):
            raise ValueError("Duplicate economic claims")
        return self


class SharePool(Frozen):
    source_basic: Input | None
    source_diluted: Input | None
    source_unit: Literal["shares", "thousand_shares", "million_shares"] | None
    source_multiplier: Input | None
    current_basic: Input | None
    current_diluted: Input | None
    currency: Currency
    as_of: date
    known_at: AwareDatetime
    captured_at: AwareDatetime
    known_basis: Literal["owner_reviewed_instant", "date_only", "unproven"]
    action_basis: Nonempty
    evidence_hash: Sha256
    fixture_url: Annotated[str, StringConstraints(pattern=r"^https://example\.invalid/")]
    complete_homogeneous_pool: bool
    no_dilutive_claims: bool
    complete_action_coverage: bool
    operating_lease_basis_matches: bool
    unrestricted_nonoperating_cash: bool
    no_crossholding_earnings_overlap: bool
    reasons: tuple[Nonempty, ...]


class PriceEvidence(Frozen):
    """Exact retained S4 selection identity plus a digest of the entire selection."""

    source_id: UUID
    field: Literal["close"]
    quote_identifier_id: UUID
    security_id: UUID
    batch_id: UUID | None
    observation_id: UUID | None
    reference_date: date
    retrieval_cutoff: AwareDatetime
    source_known_at: AwareDatetime
    selection_hash: Sha256
    value: Input | None
    currency: Currency | None
    usable: bool
    adjustment_basis: str | None
    session_basis: str | None
    action_basis: Nonempty
    reasons: tuple[Nonempty, ...]


class ValuationPolicy(Frozen):
    revision: Nonempty
    effective_at: AwareDatetime
    known_at: AwareDatetime
    applicability: Literal["reviewed_operating_fcff", "unsupported"]
    applicability_evidence: Sha256
    max_financial_age_days: Annotated[int, Field(strict=True, ge=0, le=3650)]
    max_quote_age_days: Annotated[int, Field(strict=True, ge=0, le=365)]
    max_claim_age_days: Annotated[int, Field(strict=True, ge=0, le=3650)]
    terminal_dominance_threshold: Literal["0.75"]
    sensitivity_ranking: Literal["absolute_symmetric_fraction_elasticity_v1"]


class ValuationManifest(Frozen):
    version: Literal["s7-input-v1"]
    evidence_mode: Literal["synthetic"]
    fixture_label: Literal["Synthetic integration fixture — not company data"]
    selector: SelectionKey
    source_snapshot_id: UUID
    source_payload_hash: Sha256
    source_input_hash: Sha256
    assumption_set_id: UUID
    assumptions: AssumptionContent
    model: ModelDefinition
    policy: ValuationPolicy
    price: PriceEvidence
    shares: SharePool
    claims: tuple[Claim, ...]
    bridge_captured_before: AwareDatetime
    source_eligibility_reasons: tuple[str, ...]
    source_measurement_uncertainty: tuple[tuple[Nonempty, Input | None], ...]

    @model_validator(mode="after")
    def identities(self) -> Self:
        if {c.kind for c in self.claims} != set(CLAIM_KINDS) or len(self.claims) != 7:
            raise ValueError("Complete seven-component bridge roster required")
        ids = [i for c in self.claims for i in c.economic_claim_ids]
        if len(ids) != len(set(ids)):
            raise ValueError("Economic claim overlaps/double counting are forbidden")
        if (
            self.price.security_id != self.selector.security_id
            or self.price.quote_identifier_id != self.selector.quote_identifier_id
        ):
            raise ValueError("Price identity differs from exact source identity")
        return self


def read_manifest(text: str) -> ValuationManifest:
    parse_canonical(text)
    result = ValuationManifest.model_validate_json(text)
    if canonical_json(result) != text:
        raise ValueError("Valuation manifest changed during reconstruction")
    return result


class BridgeResult(Frozen):
    eligible: bool
    market_common_value: Exact | None
    adjustment: Exact | None
    market_ev_target: Exact | None
    shares: Exact | None
    reasons: tuple[str, ...]


class ScenarioResult(Frozen):
    name: Nonempty
    solve_variable: Variable
    unit: Literal["fraction"]
    solve: SolveResult
    evaluation: Evaluation | None
    common_equity: Exact | None
    conditional_per_share: Exact | None
    reasons: tuple[str, ...]


class SensitivityCell(Frozen):
    x: Exact
    y: Exact
    value: Exact | None
    solve: SolveResult | None
    evaluation: Evaluation | None
    common_equity: Exact | None
    reasons: tuple[str, ...]


class SensitivityEffect(Frozen):
    parameter: str
    perturbations: tuple[Exact, ...]
    outputs: tuple[Exact | None, ...]
    elasticity: Exact | None
    rank: int | None
    reasons: tuple[str, ...]


class SensitivityResult(Frozen):
    name: Nonempty
    output: Literal["reverse_implied_parameter", "conditional_reprice"]
    unit: Literal["fraction", "currency_per_share"]
    cells: tuple[SensitivityCell, ...]
    request: SensitivityGrid
    effects: tuple[SensitivityEffect, ...]


class SafeAssumptions(Frozen):
    content_hash: Sha256
    authored_at: AwareDatetime
    retrospective: bool
    provenance: Literal["explicit_user_judgment"]
    scenarios: tuple[Scenario, ...]
    forecast_dates: tuple[date, ...]
    anchor_source_index: int
    anchor_method: str
    calendar: str
    leap_day: str


class ValuationPayload(Frozen):
    version: Literal["s7-result-v1"]
    evidence_mode: Literal["synthetic"]
    fixture_label: Literal["Synthetic integration fixture — not company data"]
    dependency_hash: Sha256
    model: ModelDefinition
    policy: ValuationPolicy
    assumptions: SafeAssumptions
    source_snapshot_id: UUID
    source_payload_hash: Sha256
    source_input_hash: Sha256
    source_selector: SelectionKey
    price: PriceEvidence
    shares: SharePool
    claims: tuple[Claim, ...]
    bridge_captured_before: AwareDatetime
    valuation_at: AwareDatetime
    currency: Currency
    bridge: BridgeResult
    scenarios: tuple[ScenarioResult, ...]
    scenario_dispersion: Interval | None
    numerical_uncertainty: tuple[tuple[str, tuple[Interval, ...]], ...]
    source_eligibility_reasons: tuple[str, ...]
    source_measurement_uncertainty: tuple[tuple[Nonempty, Input | None], ...]
    sensitivities: tuple[SensitivityResult, ...]
    conclusions: tuple[str, ...]
    reasons: tuple[str, ...]


class RunResponse(Frozen):
    run_id: UUID
    parent_run_id: UUID | None
    request_id: UUID
    execution_id: UUID
    input_snapshot_id: UUID
    generated_at: datetime
    compatibility_key: Sha256
    payload_hash: Sha256
    outcome: Literal["completed", "completed_with_gaps"]
    result: ValuationPayload


class RequestCreate(Frozen):
    review_id: UUID
    parent_request_id: UUID
    idempotency_key: Nonempty
    max_attempts: Annotated[int, Field(strict=True, ge=1, le=10)]


class RequestResponse(Frozen):
    request_id: UUID
    execution_id: UUID
    state: Literal[
        "queued",
        "running",
        "waiting_for_input",
        "retry_scheduled",
        "completed",
        "completed_with_gaps",
        "failed",
        "cancelled",
    ]
    stage_key: Literal["valuation"] | None
    stage_state: (
        Literal["running", "completed", "blocked", "unsupported", "failed", "cancelled"] | None
    )
    error_code: (
        Literal[
            "worker_failure",
            "cancelled",
            "lease_expired",
            "waiting_for_input",
            "retry_scheduled",
            "stage_blocked",
            "stage_unsupported",
            "stage_failed",
        ]
        | None
    )
    run_id: UUID | None


class LatestSelection(Frozen):
    security_id: UUID
    quote_identifier_id: UUID
    scope_id: UUID
    compatibility_key: Sha256


class LatestResponse(Frozen):
    run: RunResponse | None
    latest_request_id: UUID
    latest_request_state: str


class ApiError(Frozen):
    code: Literal["not_found", "conflict", "invalid_request"]
    message: Literal["N/A"]
