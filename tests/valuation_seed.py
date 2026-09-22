"""Fictional S7a oracles; integration replaces references with retained evidence."""

from datetime import UTC, date, datetime
from decimal import Decimal as D
from uuid import uuid4

from equity_schema.valuation import (
    AssumptionContent,
    Claim,
    ClaimCoverage,
    Judgment,
    ModelDefinition,
    PriceEvidence,
    Scenario,
    SharePool,
    ValuationManifest,
    ValuationPolicy,
    binding_for,
)

from tests.core.test_valuation import spec
from tests.fundamentals_seed import manifest as fundamentals_manifest


def model():
    return ModelDefinition(
        revision="reverse_fcff_operating_v1",
        cash_tax="tax_on_positive_ebit_no_nol_v1",
        terminal="gordon_growth_roic_reinvestment_v1",
        terminal_domain="0<=g<min(risk_free,wacc,roic);wacc>0;roic>0;margin>0;tax<1",
        forecast="nominal_annual_end_period_v1",
        reinvestment="net_capex_plus_change_noncash_operating_wc",
        lease_treatment="operating_lease_capitalized_consistent_ebit_v1",
        bridge="economic_claim_values_single_common_pool_no_dilution_v1",
        numeric="decimal80_half_even_interval_outward_v1",
        solver="decimal_interval_model_v1",
        engine_build="a" * 64,
    )


def assumptions():
    stamp = datetime(2026, 2, 28, tzinfo=UTC)
    scenarios = tuple(
        Scenario(
            name=name,
            revenue_anchor=D(100),
            growth=(D(".1"),) * 5,
            margins=None,
            taxes=(D(".25"),) * 5,
            reinvestment=(D(k),) * 5,
            wacc=D(".1"),
            risk_free=D(".04"),
            terminal_growth=D(".02"),
            terminal_margin=None,
            terminal_tax=D(".25"),
            terminal_roic=D(".08"),
            solve=spec("terminal_operating_margin", ".1", ".3"),
        )
        for name, k in [
            ("low investment", ".025"),
            ("reference", ".05"),
            ("high investment", ".075"),
        ]
    )
    keys = [
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
    ]
    return AssumptionContent(
        authored_at=stamp,
        author_id="private-fixture-author",
        valuation_at=stamp,
        retrospective=False,
        calendar="calendar_year_equivalent",
        leap_day="february_28",
        forecast_dates=tuple(date(2026 + y, 2, 28) for y in range(1, 6)),
        anchor_method="explicit_carry_forward_annual_run_rate",
        anchor_source_index=1,
        scenarios=scenarios,
        sensitivities=(),
        judgments=tuple(
            Judgment(
                scenario=scenario.name,
                parameter=k,
                binding=binding_for(scenario, k, tuple(date(2026 + y, 2, 28) for y in range(1, 6))),
                origin="user_judgment",
                author_id="private-fixture-author",
                authored_at=stamp,
                known_at=stamp,
                unit="currency"
                if k == "revenue_anchor"
                else k
                if k in ("schedule", "solver_policy")
                else "fraction",
                rationale="Private fictional rationale",
                effective_from=stamp.date(),
                effective_to=date(2031, 2, 28),
                supporting_hashes=(),
            )
            for scenario in scenarios
            for k in keys
        ),
    )


def manifest():
    a = assumptions()
    source = fundamentals_manifest()
    selector = source.selector
    stamp = a.valuation_at
    claims = tuple(
        Claim(
            kind=k,
            coverage=tuple(
                ClaimCoverage(
                    component=component,
                    disposition="included" if component == k and value != "0" else "excluded",
                    explanation="Fictional reviewed scope: " + component,
                    evidence_hash="b" * 64,
                )
                for component in (
                    "cash",
                    "nonoperating_assets",
                    "debt",
                    "leases",
                    "preferred",
                    "nci",
                    "other",
                )
            ),
            economic_claim_ids=(f"fictional:{k}",),
            state="evidenced_absence" if value == "0" else "eligible_amount",
            amount=D(value),
            currency="USD",
            as_of=stamp.date(),
            known_at=stamp,
            captured_at=stamp,
            known_basis="owner_reviewed_instant",
            basis="absence" if value == "0" else "economic_value",
            evidence_hash="b" * 64,
            fixture_url="https://example.invalid/claims/" + k,
            reasons=(),
        )
        for k, value in zip(
            ("cash", "nonoperating_assets", "debt", "leases", "preferred", "nci", "other"),
            ("20", "5", "30", "10", "2", "3", "0"),
            strict=True,
        )
    )
    return ValuationManifest(
        version="s7-input-v1",
        evidence_mode="synthetic",
        fixture_label="Synthetic integration fixture — not company data",
        selector=selector,
        source_snapshot_id=uuid4(),
        source_payload_hash="c" * 64,
        source_input_hash="d" * 64,
        assumption_set_id=uuid4(),
        assumptions=a,
        model=model(),
        policy=ValuationPolicy(
            revision="fictional-policy-v1",
            effective_at=stamp,
            known_at=stamp,
            applicability="reviewed_operating_fcff",
            applicability_evidence="e" * 64,
            max_financial_age_days=365,
            max_quote_age_days=1,
            max_claim_age_days=1,
            terminal_dominance_threshold="0.75",
            sensitivity_ranking="absolute_symmetric_fraction_elasticity_v1",
        ),
        price=PriceEvidence(
            source_id=uuid4(),
            field="close",
            quote_identifier_id=selector.quote_identifier_id,
            security_id=selector.security_id,
            batch_id=uuid4(),
            observation_id=uuid4(),
            reference_date=stamp.date(),
            retrieval_cutoff=stamp,
            source_known_at=stamp,
            selection_hash="f" * 64,
            value=D("17.34375"),
            currency="USD",
            usable=True,
            adjustment_basis="unadjusted",
            session_basis="regular",
            action_basis="fictional-unsplit-v1",
            reasons=(),
        ),
        shares=SharePool(
            source_basic=D(10),
            source_diluted=D(10),
            source_unit="shares",
            source_multiplier=D(1),
            current_basic=D(10),
            current_diluted=D(10),
            currency="USD",
            as_of=stamp.date(),
            known_at=stamp,
            captured_at=stamp,
            known_basis="owner_reviewed_instant",
            action_basis="fictional-unsplit-v1",
            evidence_hash="b" * 64,
            fixture_url="https://example.invalid/shares",
            complete_homogeneous_pool=True,
            no_dilutive_claims=True,
            complete_action_coverage=True,
            operating_lease_basis_matches=True,
            unrestricted_nonoperating_cash=True,
            no_crossholding_earnings_overlap=True,
            reasons=(),
        ),
        claims=claims,
        bridge_captured_before=stamp,
        source_eligibility_reasons=(),
        source_measurement_uncertainty=(("revenue_anchor", D(".5")),),
    )


def reauthor(content, stamp, author=None):
    author = author or content.author_id
    return content.model_copy(
        update={
            "authored_at": stamp,
            "author_id": author,
            "retrospective": stamp > content.valuation_at,
            "judgments": tuple(
                j.model_copy(update={"author_id": author, "authored_at": stamp, "known_at": stamp})
                for j in content.judgments
            ),
        }
    )


def stamp_body(body, stamp):
    body["authored_at"] = stamp
    for judgment in body["judgments"]:
        judgment["authored_at"] = stamp
        judgment["known_at"] = stamp
