"""Explicit fictional source inputs for S8b; no saved financial outputs or test imports."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from equity_core.assessment import (
    EvaluationContext,
    FreshnessPolicy,
    MetricApplicability,
    ProfilePolicy,
)
from equity_core.history import HistoryPolicy
from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_core.trends import TrendPolicy
from equity_ingest.financial_types import ScopeSpec
from equity_ingest.sec_normalize import period_spec, unit_spec
from equity_schema.concepts import Concept
from equity_schema.fundamentals import (
    CaptureInput,
    InputManifest,
    MetricSpec,
    OperandSpec,
    SelectionKey,
    read_manifest,
)
from equity_schema.fundamentals_canonical import canonical_json, content_hash
from equity_schema.pit import HistoryMode, PitQuery, SelectedFact, StatementSelection


def identity(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, "equityeval:s8b:fictional:" + name)


def source(
    concept: Concept,
    value: str | None,
    start: date | None,
    end: date,
    as_of: date,
    vintage: str,
    invalid: bool = False,
) -> FinancialInput:
    period, unit = period_spec(start, end), unit_spec("USD")
    descriptor = {
        "consolidation": "consolidated",
        "instrument": None,
        "context_knowledge": "unknown",
        "scope_evidence": "fictional reviewed scope",
        "cash_scope": "not_applicable",
        "revenue_basis": "reported_complete_scope",
        "payment_basis": "actual_cash_payment"
        if concept == Concept.CAPITAL_EXPENDITURES_PPE
        else "as_reported",
    }
    scope = ScopeSpec(
        identity(canonical_json(descriptor)),
        identity("issuer"),
        None,
        "consolidated",
        1,
        canonical_json(descriptor),
        content_hash(descriptor),
    )
    capture = identity(f"capture:{vintage}")
    family = (
        "balance_sheet"
        if start is None
        else "cash_flow"
        if concept in {Concept.CASH_FROM_OPERATING_ACTIVITIES, Concept.CAPITAL_EXPENDITURES_PPE}
        else "income"
    )
    captured = datetime.combine(as_of, datetime.min.time(), tzinfo=UTC)
    query = PitQuery(
        identity("issuer"),
        period.id,
        scope.id,
        unit.id,
        family,
        (concept,),
        (identity(f"batch:{vintage}"),),
        (capture,),
        (),
        identity("mapping"),
        "s8b-fictional-normalizer-v1",
        "s8b-fictional-authority-v1",
        captured,
        HistoryMode.AS_FILED_BY_DATE,
        filed_cutoff=as_of,
        reporting_currency_unit_id=unit.id,
    )
    observation = identity(f"{vintage}:{concept.value}:{start}:{end}:{value}")
    fact = SelectedFact(
        concept,
        Decimal(value) if value is not None else None,
        "observed" if value is not None else "missing",
        resolution_ids=(identity(f"resolution:{observation}"),),
        observation_ids=(observation,) if value is not None else (),
        accession=f"0000000001-{as_of.year % 100:02d}-000001",
        filed_date=date(as_of.year, 1, 31),
        source_url="file:///private/invalid"
        if invalid
        else "https://example.invalid/s8b-fictional-filing",
        source_locator="/fictional/" + concept.value,
        capture_ids=(capture,),
        source_hashes=(vintage,),
        source_tag="fictional:" + concept.value,
        original_numeric_text=value,
        transform_json='{"operation":"identity_decimal","scale_applied":false}',
    )
    selection = StatementSelection(
        query,
        (identity(f"coverage:{observation}"),),
        (identity(f"edition:{vintage}"),),
        (fact,),
        (),
        (),
        (),
        value is not None,
        "us_gaap",
        content_hash((query, fact)),
    )
    precision = (
        None
        if value is None
        else PrecisionEvidence(
            Decimal("0.0001"), (observation,), ("fictional:precision",), "synthetic_fixture"
        )
    )
    return FinancialInput(selection, concept, period, unit, scope, precision)


def manifest(
    amounts: dict[str, str],
    *,
    basis: Literal["annual", "instant"],
    as_of: date,
    years: Literal[3, 5, 10],
    case: str = "valid",
) -> InputManifest:
    vintage = content_hash((amounts, basis, as_of, case))
    year = as_of.year - 1
    start, end = date(year, 1, 1), date(year, 12, 31)
    if basis == "instant":
        specs = [
            ("reported.current_assets", "USD", ("current_assets",)),
            ("reported.current_liabilities", "USD", ("current_liabilities",)),
            ("current_ratio", "multiple", ("current_assets", "current_liabilities")),
            ("net_working_capital", "USD", ("current_assets", "current_liabilities")),
        ]
    else:
        specs = [
            ("reported.revenue", "USD", ("revenue",)),
            ("revenue_growth_yoy", "fraction", ("revenue", "prior_revenue")),
            ("gross_margin", "fraction", ("gross_profit", "revenue")),
            ("operating_margin", "fraction", ("operating_income", "revenue")),
            ("net_margin_consolidated", "fraction", ("net_income_consolidated", "revenue")),
            ("reported.cash_from_operating_activities", "USD", ("cash_from_operating_activities",)),
            (
                "free_cash_flow_ppe",
                "USD",
                ("cash_from_operating_activities", "capital_expenditures_ppe"),
            ),
            (
                "free_cash_flow_margin_ppe",
                "fraction",
                ("cash_from_operating_activities", "capital_expenditures_ppe", "revenue"),
            ),
            (
                "return_on_assets",
                "fraction",
                ("net_income_consolidated", "opening_assets", "total_assets"),
            ),
            ("trailing_pe", "multiple", ()),
        ]
    keys = list(dict.fromkeys(key for _, _, keys in specs for key in keys))
    sources = []
    for key in keys:
        concept = Concept(
            "revenue"
            if key == "prior_revenue"
            else "total_assets"
            if key == "opening_assets"
            else key
        )
        value = amounts[key]
        selected_value = (
            None
            if case == "missing" and key == "revenue"
            else "0"
            if case == "not_meaningful" and key == "revenue"
            else value
        )
        instant = basis == "instant" or key in {"opening_assets", "total_assets"}
        source_start = (
            None if instant else date(year - 1, 1, 1) if key == "prior_revenue" else start
        )
        source_end = date(year - 1, 12, 31) if key in {"prior_revenue", "opening_assets"} else end
        sources.append(
            source(
                concept,
                selected_value,
                source_start,
                source_end,
                as_of,
                vintage=vintage,
                invalid=case == "invalid" and key == "operating_income",
            )
        )
    metrics = tuple(
        MetricSpec(
            metric_id=mid,
            unit=unit,
            operands=tuple(
                OperandSpec(
                    method="selected",
                    source_indices=(keys.index(key),),
                    calendar_evidence=None,
                    revision_compatibility=None,
                )
                for key in keys_
            ),
            calendar_evidence=None,
            revision_compatibility=None,
        )
        for mid, unit, keys_ in specs
    )
    profile = ProfilePolicy(
        identity("issuer"),
        "fictional industrial",
        "established",
        "consolidated_issuer",
        "s8b-fictional-profile-v1",
        date(2020, 1, 1),
        date(2020, 1, 1),
        ("fictional:profile",),
        tuple(
            MetricApplicability(
                m.metric_id,
                not (case == "inapplicable" and m.metric_id == "gross_margin"),
                "Explicit fictional example policy",
            )
            for m in metrics
        ),
    )
    context = EvaluationContext(
        as_of,
        profile,
        FreshnessPolicy(
            "s8b-fictional-freshness-v1", 1 if case == "stale" else 999, ("fictional:freshness",)
        ),
    )
    history = HistoryPolicy(years, years * 4, "s8b-fictional-history-v1")
    trend = TrendPolicy(Decimal(".01"), "s8b-fictional-trend-v1", ("fictional:trend",))
    evaluated = datetime.combine(as_of, datetime.min.time(), tzinfo=UTC)
    selector = SelectionKey(
        issuer_id=identity("issuer"),
        security_id=identity("security"),
        quote_identifier_id=identity("quote"),
        period_basis=basis,
        period_start=None if basis == "instant" else start,
        period_end=end,
        reporting_basis="us_gaap",
        currency="USD",
        history_mode="as_filed_by_date",
        filed_cutoff=as_of,
        captured_before=evaluated,
        as_of=as_of,
        evaluated_at=evaluated,
        profile_revision=profile.revision,
        freshness_revision=context.freshness.revision,
        history_revision=history.revision,
        trend_revision=trend.revision,
        policy_content_hash=content_hash((context, history, trend)),
        history_years=years,
        engine_revision="s8b-fictional-existing-s6a-core-v1",
    )
    result = InputManifest(
        version="s6-input-v1",
        evidence_mode="synthetic",
        fixture_label="Synthetic integration fixture — not company data",
        selector=selector,
        context=context,
        history_policy=history,
        trend_policy=trend,
        captures=(
            CaptureInput(
                capture_id=identity(f"capture:{vintage}"),
                fetched_at=evaluated,
                body_sha256=vintage,
            ),
        ),
        sources=tuple(sources),
        metrics=metrics,
        trend_inputs=(),
        history_samples=(),
        accounting_source_indices=(),
    )
    return read_manifest(canonical_json(result))
