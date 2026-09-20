"""Generate explicitly fictional Sector Explorer inputs through the shared core.

The constructed statement and capitalization amounts are test illustrations, not
company facts, licensed market data, source coverage, or an investment opinion.
"""

from __future__ import annotations

import calendar
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from equity_core.company import (
    EvidenceValue,
    equity_multiple,
    evidence_from_fcf,
    evidence_from_operand,
    metric_from_calculation,
)
from equity_core.history import compare_to_history
from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_core.metrics import (
    free_cash_flow,
    free_cash_flow_margin,
    operating_margin,
    revenue_growth,
)
from equity_core.periods import PeriodAmount, ttm_from_quarters
from equity_core.sector_history import SectorHistoryPoint, sector_history
from equity_core.sector_insights import growth_observations
from equity_core.sectors import (
    CompanySnapshot,
    Method,
    SectorMetric,
    SectorPolicy,
    SectorRoster,
    calculate_concentration,
    calculate_sector,
    histogram,
)
from equity_ingest.financial_types import ScopeSpec, canonical_json, content_hash
from equity_ingest.sec_normalize import period_spec, unit_spec
from equity_schema.concepts import Concept
from equity_schema.pit import HistoryMode, PitQuery, SelectedFact, StatementSelection

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 6, 30)
ALTERNATE_AS_OF = date(2026, 3, 31)
POLICY = SectorPolicy(10, Decimal("0.7"), Decimal("0.8"), "fictional-coverage-policy-v1")
METRIC_IDS = (
    "pe",
    "ps",
    "pfcf",
    "revenue_yoy",
    "operating_margin",
    "fcf_margin",
    "growth_breadth",
    "profit_breadth",
    "cash_breadth",
)
SECTORS = (
    ("computing", "Computing", "#587fc7"),
    ("health", "Health", "#2e998c"),
    ("industry", "Industry", "#bc8b44"),
    ("energy", "Energy", "#ac644f"),
    ("consumer", "Consumer", "#946ca8"),
    ("property-finance", "Property & finance", "#818ca0"),
    ("unclassified", "Unclassified", "#7d858b"),
)
CONTEXT = "fictional-universe:illustrative-taxonomy-v1:current-membership:USD:as-filed-v1"


def identity(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, "equityeval:sector-fixture:" + label)


def json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal | UUID):
        return str(value)
    raise TypeError(f"Unsupported fixture type: {type(value).__name__}")


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=json_default).encode()
    ).hexdigest()


def quarter_end(index: int) -> date:
    year, quarter = divmod(index, 4)
    month = (quarter + 1) * 3
    return date(year, month, calendar.monthrange(year, month)[1])


def source(
    issuer: str, concept: Concept, value: Decimal, start: date, end: date, evaluation_date: date
) -> FinancialInput:
    """Build a synthetic selection with explicit fake-source provenance."""
    issuer_id = identity(issuer)
    period, unit = period_spec(start, end), unit_spec("USD")
    descriptor = {
        "consolidation": "consolidated",
        "instrument": None,
        "context_knowledge": "unknown",
        "scope_evidence": "fictional reviewed fixture scope",
        "cash_scope": "not_applicable",
        "payment_basis": "actual_cash_payment"
        if concept == Concept.CAPITAL_EXPENDITURES_PPE
        else "as_reported",
        "revenue_basis": "reported_complete_scope",
    }
    scope = ScopeSpec(
        identity(issuer + canonical_json(descriptor)),
        issuer_id,
        None,
        "consolidated",
        1,
        canonical_json(descriptor),
        content_hash(descriptor),
    )
    capture = identity(issuer + str(evaluation_date) + "capture")
    family = (
        "cash_flow"
        if concept in {Concept.CASH_FROM_OPERATING_ACTIVITIES, Concept.CAPITAL_EXPENDITURES_PPE}
        else "income"
    )
    query = PitQuery(
        issuer_id,
        period.id,
        scope.id,
        unit.id,
        family,
        (concept,),
        (identity(issuer + str(evaluation_date) + "batch"),),
        (capture,),
        (),
        identity("fixture-mapping"),
        "fictional-normalizer-v1",
        "fictional-authority-v1",
        datetime.combine(evaluation_date, datetime.min.time(), tzinfo=UTC),
        HistoryMode.AS_FILED_BY_DATE,
        filed_cutoff=evaluation_date,
        reporting_currency_unit_id=unit.id,
    )
    original = {
        "fictional": True,
        "issuer": issuer,
        "concept": concept.value,
        "value": value,
        "period_start": start,
        "period_end": end,
        "evaluation_date": evaluation_date,
    }
    observation = identity(digest(original))
    fact = SelectedFact(
        concept,
        value,
        "observed",
        (identity("resolution-" + str(observation)),),
        (observation,),
        accession=f"9999999999-{evaluation_date.year % 100:02d}-000001",
        filed_date=evaluation_date,
        source_url="https://example.invalid/equityeval-fictional-fixture",
        source_locator="/fictional/" + issuer + "/" + concept.value + "/" + str(end),
        capture_ids=(capture,),
        source_hashes=(digest(original),),
        source_tag="fixture:" + concept.value,
        original_numeric_text=str(value),
        transform_json='{"fictional":true,"operation":"explicit_fixture_amount"}',
    )
    selection = StatementSelection(
        query,
        (identity("coverage-" + str(observation)),),
        (identity(issuer + str(evaluation_date) + "fixture-edition"),),
        (fact,),
        (),
        (),
        (),
        True,
        "us_gaap",
        digest({"query": asdict(query), "fact": asdict(fact), "fictional": True}),
    )
    precision = PrecisionEvidence(
        Decimal("0.5"),
        (observation,),
        ("fixture:explicit-half-unit-uncertainty",),
        "fictional_explicit_precision",
    )
    return FinancialInput(selection, concept, period, unit, scope, precision)


def flow(
    issuer: str, concept: Concept, amount: Decimal, end: date, evaluation_date: date
) -> PeriodAmount:
    last = end.year * 4 + end.month // 3 - 1
    quarters = tuple(
        source(
            issuer, concept, amount, date(bound.year, bound.month - 2, 1), bound, evaluation_date
        )
        for index in range(last - 3, last + 1)
        if (bound := quarter_end(index))
    )
    return ttm_from_quarters(quarters)


def evaluated(
    issuer: str,
    field: str,
    value: Decimal | None,
    end: date,
    *,
    start: date | None = None,
    basis: str,
    usable: bool = True,
    flags: tuple[str, ...] = (),
) -> EvidenceValue:
    """Explicit future-input projection, never a substitute normalized fact."""
    return EvidenceValue(
        value,
        Decimal("0.5") if value is not None else None,
        digest(
            {
                "fictional": True,
                "issuer": issuer,
                "field": field,
                "value": value,
                "start": start,
                "end": end,
                "basis": basis,
                "usable": usable,
                "flags": flags,
            }
        ),
        start,
        end,
        usable and value is not None,
        flags,
        "USD",
        basis,
    )


def company(issuer: str, sector: str, member: int, as_of: date) -> CompanySnapshot:
    # These operations vary explicit fictional input amounts, not valuation outputs.
    time_step = (as_of.year - 2021) * 4 + as_of.month // 3
    sector_offsets = {
        "computing": (10, 1500, 12),
        "health": (25, 800, 6),
        "industry": (35, 100, 4),
        "energy": (55, -400, 7),
        "consumer": (45, 350, 3),
        "property-finance": (20, 1800, 8),
        "unclassified": (5, 500, 5),
    }
    sales_offset, cap_offset, income_offset = sector_offsets[sector]
    revenue_quarter = Decimal(100 + member * 9 + time_step * 2 + sales_offset)
    prior_quarter = Decimal(90 + member * 8 + time_step)
    operating_quarter = Decimal(15 + member * 2 + income_offset)
    cfo_quarter = Decimal(20 + member * 2)
    capex_quarter = Decimal(8 + member)
    if sector == "energy" and member in {2, 3}:
        cfo_quarter = Decimal(2)
        operating_quarter = Decimal(-4)
    sales = flow(issuer, Concept.REVENUE, revenue_quarter, as_of, as_of)
    prior_end = date(as_of.year - 1, as_of.month, as_of.day)
    prior_sales = flow(issuer, Concept.REVENUE, prior_quarter, prior_end, as_of)
    operating = flow(issuer, Concept.OPERATING_INCOME, operating_quarter, as_of, as_of)
    cfo = flow(issuer, Concept.CASH_FROM_OPERATING_ACTIVITIES, cfo_quarter, as_of, as_of)
    capex = flow(issuer, Concept.CAPITAL_EXPENDITURES_PPE, capex_quarter, as_of, as_of)
    revenue, prior_revenue = evidence_from_operand(sales), evidence_from_operand(prior_sales)
    income = evidence_from_operand(operating)
    cash = evidence_from_fcf(free_cash_flow(cfo, capex))
    cap_value = Decimal(3000 + member * 550 + time_step * 50 + cap_offset)
    common_value = Decimal(140 + member * 15 + time_step)
    if sector == "computing" and member == 11:
        common_value = Decimal(-80)
    cap = evaluated(issuer, "future_common_equity_value", cap_value, as_of, basis="common_equity")
    prior_cap = evaluated(
        issuer,
        "future_common_equity_value",
        cap_value - Decimal(300),
        prior_end,
        basis="common_equity",
    )
    common = evaluated(
        issuer,
        "future_income_available_common",
        common_value,
        as_of,
        start=sales.period.start_date,
        basis="income_available_common",
    )
    applicable: tuple[str, ...] = METRIC_IDS
    if sector == "health" and member == 11:
        cap = evaluated(
            issuer,
            "future_common_equity_value",
            None,
            as_of,
            basis="common_equity",
            usable=False,
            flags=("market_cap_missing",),
        )
    if sector == "property-finance":
        applicable = ("pe", "profit_breadth")
    if sector == "consumer" and member == 11:
        common = evaluated(
            issuer,
            "future_income_available_common",
            common_value,
            as_of,
            start=sales.period.start_date,
            basis="income_available_common",
            usable=False,
            flags=("stale_financials",),
        )
    metrics = (
        equity_multiple("pe", cap, common, as_of=as_of),
        equity_multiple("ps", cap, revenue, as_of=as_of),
        equity_multiple("pfcf", cap, cash, as_of=as_of),
        metric_from_calculation(
            revenue_growth(sales, prior_sales), "revenue_yoy", (revenue, prior_revenue)
        ),
        metric_from_calculation(
            operating_margin(operating, sales), "operating_margin", (income, revenue)
        ),
        metric_from_calculation(
            free_cash_flow_margin(cfo, capex, sales), "fcf_margin", (cash, revenue)
        ),
    )
    snapshot_id = digest(
        {
            "fictional": True,
            "issuer": issuer,
            "as_of": as_of,
            "context": CONTEXT,
            "applicable_metrics": applicable,
            "market_cap": asdict(cap),
            "prior_market_cap": asdict(prior_cap),
            "common_income": asdict(common),
            "revenue": asdict(revenue),
            "prior_revenue": asdict(prior_revenue),
            "operating_income": asdict(income),
            "fcf": asdict(cash),
            "company_metrics": tuple(asdict(item) for item in metrics),
        }
    )
    return CompanySnapshot(
        issuer,
        snapshot_id,
        CONTEXT,
        applicable,
        cap,
        prior_cap,
        common,
        revenue,
        prior_revenue,
        income,
        cash,
        metrics,
    )


def roster(issuers: tuple[str, ...], as_of: date, label: str) -> SectorRoster:
    return SectorRoster(
        issuers,
        CONTEXT,
        True,
        as_of,
        digest({"fictional": True, "issuers": issuers, "as_of": as_of, "label": label}),
        ("fixture:complete-fictional-roster", "fixture:illustrative-unlicensed-taxonomy"),
        date(as_of.year - 1, as_of.month, as_of.day),
    )


CATALOG = (
    (
        "pe",
        "P/E",
        "multiple",
        (
            "Common equity market value / income available to common shareholders. "
            "Losses stay in total earnings; company P/E requires positive earnings."
        ),
    ),
    (
        "ps",
        "P/S",
        "multiple",
        "Common equity market value / consolidated trailing-twelve-month revenue.",
    ),
    (
        "pfcf",
        "P/FCF",
        "multiple",
        ("Common equity market value / trailing CFO less cash purchases of PPE. This is not FCFF."),
    ),
    (
        "revenue_growth",
        "Revenue growth",
        "fraction",
        "Same-cohort trailing revenue / comparable prior-year trailing revenue, minus one.",
    ),
    (
        "operating_margin",
        "Operating margin",
        "fraction",
        "Trailing operating income / trailing consolidated revenue.",
    ),
    (
        "fcf_margin",
        "FCF margin",
        "fraction",
        "Trailing CFO less cash PPE purchases / trailing consolidated revenue.",
    ),
    (
        "growth_breadth",
        "Growth breadth",
        "fraction",
        "Companies with positive comparable revenue growth / eligible companies.",
    ),
    (
        "profit_breadth",
        "Profit breadth",
        "fraction",
        "Companies with positive income available to common / eligible companies.",
    ),
    (
        "cash_breadth",
        "Cash-flow breadth",
        "fraction",
        "Companies with positive CFO-minus-cash-PPE FCF / eligible companies.",
    ),
)
METHODS = (
    {
        "id": "total",
        "label": "Sector total",
        "definition": (
            "Ratio of matching-cohort sums; retains usable zero and negative flow "
            "amounts. Breadth uses eligible-company counts."
        ),
    },
    {
        "id": "median",
        "label": "Median company",
        "definition": (
            "Median of meaningful individual company ratios. Invalid or "
            "nonpositive multiple denominators are excluded. Breadth remains a "
            "count-based share."
        ),
    },
    {
        "id": "mean",
        "label": "Mean company",
        "definition": (
            "Arithmetic mean of meaningful company ratios; sensitive to extreme "
            "values. Breadth remains a count-based share."
        ),
    },
)


def status(value: Decimal | None, flags: tuple[str, ...], *, comparable: bool = True) -> str:
    """Summarize presentation only; all evidence reasons remain attached.

    Mixed unavailable causes use the explicit priority stale, unsupported,
    not meaningful, then missing. Available-but-limited values retain limited.
    """
    if value is not None:
        return "eligible" if comparable else "limited"
    if any("stale" in flag for flag in flags):
        return "stale"
    if any("unsupported" in flag for flag in flags):
        return "unsupported"
    if any("nonpositive" in flag or "indistinguishable" in flag for flag in flags):
        return "nm"
    return "missing"


def field_text(value: object) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, tuple):
        return ", ".join(str(item) for item in value) or "None"
    return str(value)


def company_detail(snapshot: CompanySnapshot, metric_id: str) -> dict[str, Any]:
    values = (
        snapshot.market_cap,
        snapshot.prior_market_cap,
        snapshot.common_income,
        snapshot.revenue,
        snapshot.prior_revenue,
        snapshot.operating_income,
        snapshot.fcf,
    )
    labels = (
        "Common equity market value",
        "Prior common equity market value",
        "Income available to common",
        "TTM revenue",
        "Prior TTM revenue",
        "TTM operating income",
        "TTM CFO minus cash PPE purchases",
    )
    sections = [
        {
            "heading": "Fictional company snapshot",
            "rows": [
                {"label": "Issuer", "value": snapshot.issuer_id},
                {"label": "Snapshot ID", "value": snapshot.snapshot_id},
                {"label": "Context", "value": snapshot.context_key},
                {
                    "label": "Source type",
                    "value": "Invented demonstration inputs; no actual company, price or filing.",
                },
            ],
        }
    ]
    for label, amount in zip(labels, values, strict=True):
        sections.append(
            {
                "heading": label,
                "rows": [
                    {"label": "Value (USD)", "value": field_text(amount.value)},
                    {
                        "label": "Absolute source uncertainty",
                        "value": field_text(amount.absolute_error),
                    },
                    {"label": "Basis", "value": amount.basis},
                    {
                        "label": "Period",
                        "value": f"{amount.period_start or 'Point'} to {amount.period_end}",
                    },
                    {"label": "Input manifest SHA256", "value": amount.input_hash},
                    {"label": "Flags", "value": field_text(amount.flags)},
                ],
            }
        )
    sections.append(
        {
            "heading": "Shared company calculations",
            "rows": [
                {
                    "label": item.metric_id,
                    "value": f"{field_text(item.value)}; flags={field_text(item.flags)}; "
                    f"result={item.input_hash}; operands={field_text(item.operand_hashes)}",
                }
                for item in snapshot.company_metrics
            ],
        }
    )
    sections.append(
        {
            "heading": "Transform and prerequisite limits",
            "rows": [
                {
                    "label": "Source flows",
                    "value": (
                        "Four contiguous fictional calendar quarters are assembled with "
                        "ttm_from_quarters before margins, growth and FCF use the shared "
                        "fundamentals engine."
                    ),
                },
                {
                    "label": "P/E inputs",
                    "value": (
                        "Market value and income available to common are explicit synthetic "
                        "evaluated projections. No normalized common-income concept or live "
                        "market-cap provider is implemented by this fixture."
                    ),
                },
                {
                    "label": "Replay",
                    "value": (
                        "Run scripts/build_sector_fixture.py for the exact source inputs and "
                        "stable hashes. Fixture policy fixes half-unit uncertainty per "
                        "reported quarter."
                    ),
                },
            ],
        }
    )
    return {
        "title": snapshot.issuer_id + " · " + metric_id,
        "subtitle": "Fictional evidence only",
        "sections": sections,
        "sources": [
            {
                "label": "EquityEval deterministic synthetic fixture",
                "capturedAt": str(snapshot.market_cap.period_end),
                "transform": (
                    "Explicit invented raw amounts → existing source selection projection "
                    "→ quarter assembly → shared fundamentals calculations."
                ),
                "licence": (
                    "Synthetic demonstration data; no provider licence or "
                    "production coverage claimed."
                ),
            }
        ],
    }


def metric_detail(result: SectorMetric, sector_label: str) -> dict[str, Any]:
    rows = [
        ("Method", result.method),
        ("Metric", result.metric_id),
        ("Value", result.value),
        ("Numerator total", result.numerator_total),
        ("Denominator total", result.denominator_total),
        ("Declared universe N", result.n),
        ("Complete inputs K", result.k),
        ("Contributors V", result.v),
        ("Issuer coverage K/N", result.issuer_coverage),
        ("Cap coverage", result.cap_coverage),
        ("Meaningful company ratios", result.meaningful_company_count),
        ("Sign count basis", result.sign_basis),
        ("Zero denominator count", result.zero_denominator_count),
        (
            "Positive / zero / negative",
            f"{result.positive_count} / {result.zero_count} / {result.negative_count}",
        ),
        ("Policy", result.policy_revision),
        ("Cohort ID", result.cohort_id),
        ("Roster hash", result.roster.input_hash),
        ("Financial date range", result.financial_date_range),
        ("Equity date range", result.quote_date_range),
        ("Flags", result.flags),
    ]
    return {
        "title": sector_label + " · " + result.metric_id,
        "subtitle": "Fictional snapshot · " + result.roster.evaluation_date.isoformat(),
        "sections": [
            {
                "heading": "Calculation and coverage",
                "rows": [{"label": key, "value": field_text(value)} for key, value in rows],
            },
            {
                "heading": "Roster company snapshots (includes excluded issuers)",
                "rows": [
                    {"label": item.issuer_id, "value": item.snapshot_id}
                    for item in result.company_snapshots
                ],
            },
            {
                "heading": "Aggregate exclusions",
                "rows": [
                    {"label": item.issuer_id, "value": field_text(item.reasons)}
                    for item in result.excluded
                ],
            },
            {
                "heading": "Company ratio exclusions",
                "rows": [
                    {"label": item.issuer_id, "value": field_text(item.reasons)}
                    for item in result.distribution_excluded
                ],
            },
        ],
        "sources": [
            {
                "label": "Complete fictional roster and evaluated company snapshots",
                "capturedAt": result.roster.evaluation_date.isoformat(),
                "transform": (
                    "Shared equity_core.calculate_sector; ratio of matching sums or "
                    "separately selected meaningful-company distribution."
                ),
                "licence": (
                    "Synthetic demonstration data; illustrative taxonomy is "
                    "not licensed GICS or ICB."
                ),
            }
        ],
    }


def evaluation(
    result: SectorMetric,
    sector_id: str,
    label: str,
    metric_id: str,
    details: dict[str, Any],
    *,
    include_companies: bool,
) -> dict[str, Any]:
    detail_id = "|".join((str(result.roster.evaluation_date), sector_id, metric_id, result.method))
    details[detail_id] = metric_detail(result, label)
    display_reasons = tuple(
        sorted(
            set(result.flags)
            | (
                {reason for exclusion in result.excluded for reason in exclusion.reasons}
                if result.value is None
                else set()
            )
        )
    )
    details[detail_id]["sections"][0]["rows"].append(
        {
            "label": "Unavailable display priority",
            "value": (
                "Mixed causes show stale, then unsupported, then not meaningful, "
                "then missing; all causes remain listed."
            ),
        }
    )
    row: dict[str, Any] = {
        "asOf": result.roster.evaluation_date.isoformat(),
        "sectorId": sector_id,
        "metricId": metric_id,
        "method": result.method,
        "value": result.value,
        "status": status(result.value, display_reasons, comparable=result.comparison_allowed),
        "reasons": list(display_reasons),
        "N": result.n,
        "K": result.k,
        "V": result.v,
        "issuerCoverage": result.issuer_coverage,
        "capCoverage": result.cap_coverage,
        "ratioEligibility": result.ratio_eligibility,
        "numeratorTotal": result.numerator_total,
        "denominatorTotal": result.denominator_total,
        "marketCap": result.full_market_cap,
        "detailId": detail_id,
    }
    if include_companies:
        observations = {item.issuer_id: item for item in result.distribution}
        reasons = {item.issuer_id: item.reasons for item in result.distribution_excluded}
        rows = []
        for snapshot in result.company_snapshots:
            item = observations.get(snapshot.issuer_id)
            company_flags = reasons.get(snapshot.issuer_id, ())
            if metric_id in {"profit_breadth", "cash_breadth"}:
                company_flags = company_flags or ("unsupported_individual_breadth_ratio",)
            company_id = f"company|{result.roster.evaluation_date}|{snapshot.issuer_id}"
            if company_id not in details:
                details[company_id] = company_detail(snapshot, "shared fundamentals snapshot")
            value = item.value if item is not None else None
            rows.append(
                {
                    "id": snapshot.issuer_id,
                    "ticker": "DEMO-" + snapshot.issuer_id.upper(),
                    "name": "Fictional " + snapshot.issuer_id.replace("-", " ").title(),
                    "value": value,
                    "status": status(value, company_flags),
                    "reasons": list(company_flags),
                    "detailId": company_id,
                    "snapshotId": snapshot.snapshot_id,
                }
            )
        reason_counts: dict[str, int] = {}
        for exclusion in result.distribution_excluded:
            for reason in exclusion.reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        row["companies"] = rows
        row["distribution"] = {
            "bins": [
                {
                    "id": str(index),
                    "lower": item.lower,
                    "upper": item.upper,
                    "count": item.count,
                    "companyIds": list(item.issuer_ids),
                }
                for index, item in enumerate(histogram(result.distribution))
            ],
            "p25": result.p25,
            "p50": result.p50,
            "p75": result.p75,
            "excluded": [
                {"label": key, "count": count} for key, count in sorted(reason_counts.items())
            ],
        }
    return row


def build_raw() -> dict[str, Any]:
    """Produce the complete deterministic illustration; never fetch actual data."""
    details: dict[str, Any] = {}
    evaluations, market, history = [], [], []
    cache: dict[date, tuple[CompanySnapshot, ...]] = {}
    current_index = AS_OF.year * 4 + AS_OF.month // 3 - 1
    dates = tuple(quarter_end(index) for index in range(current_index - 19, current_index + 1))
    series: dict[tuple[str, str, Method], list[SectorHistoryPoint]] = {}
    methods: tuple[Method, ...] = ("total", "median", "mean")
    groups: list[tuple[str, str, str, str | None]] = [
        (sector, label, color, None) for sector, label, color in SECTORS
    ]
    groups.extend(
        (sector + "-" + suffix, label + " · " + industry, color, sector)
        for sector, label, color in SECTORS
        if sector != "unclassified"
        for suffix, industry in (("a", "Established businesses"), ("b", "Emerging businesses"))
    )
    for as_of in dates:
        snapshots = tuple(
            company(f"{sector}-{member + 1:02d}", sector, member, as_of)
            for sector, _, _ in SECTORS
            for member in range(12)
        )
        cache[as_of] = snapshots
        for sector_id, label, _, parent_id in groups:
            selected = tuple(
                item
                for item in snapshots
                if item.issuer_id.startswith((parent_id or sector_id) + "-")
                and (
                    parent_id is None
                    or (int(item.issuer_id.rsplit("-", 1)[1]) <= 6) == sector_id.endswith("-a")
                )
            )
            selected_roster = roster(tuple(item.issuer_id for item in selected), as_of, sector_id)
            concentration = calculate_concentration(selected_roster, selected, policy=POLICY)
            observations: tuple[str, ...] = ()
            if as_of in (AS_OF, ALTERNATE_AS_OF):
                observations = growth_observations(
                    calculate_sector(
                        selected_roster,
                        selected,
                        metric="revenue_yoy",
                        method="total",
                        policy=POLICY,
                    ),
                    calculate_sector(
                        selected_roster,
                        selected,
                        metric="revenue_yoy",
                        method="median",
                        policy=POLICY,
                    ),
                    calculate_sector(
                        selected_roster,
                        selected,
                        metric="growth_breadth",
                        method="total",
                        policy=POLICY,
                    ),
                )
            for metric_id, _, _, _ in CATALOG:
                metric = "revenue_yoy" if metric_id == "revenue_growth" else metric_id
                for method in methods:
                    result = calculate_sector(
                        selected_roster, selected, metric=metric, method=method, policy=POLICY
                    )
                    key = (sector_id, metric_id, method)
                    series_key = "|".join((CONTEXT, sector_id, metric_id, method, POLICY.revision))
                    # A missing source example leaves a break, never an interpolated observation.
                    missing = (
                        as_of in {date(2023, 9, 30), date(2024, 3, 31)} and sector_id == "computing"
                    )
                    flags = (
                        ("fictional_missing_snapshot",)
                        if missing
                        else tuple(
                            flag
                            for flag in result.flags
                            if flag not in {"revised_view", "earliest_available", "extreme_margin"}
                        )
                    )
                    series.setdefault(key, []).append(
                        SectorHistoryPoint(
                            as_of,
                            None if missing else result.value,
                            series_key,
                            result.cohort_id,
                            selected_roster.input_hash,
                            "current_members",
                            result.comparison_allowed and not missing,
                            flags,
                        )
                    )
                    if as_of in (AS_OF, ALTERNATE_AS_OF):
                        row = evaluation(
                            result, sector_id, label, metric_id, details, include_companies=True
                        )
                        row["observations"] = observations
                        details[row["detailId"]]["sections"].append(
                            {
                                "heading": "Coverage-gated growth observations",
                                "rows": [
                                    {"label": "Observation", "value": text} for text in observations
                                ]
                                or [
                                    {
                                        "label": "Unavailable",
                                        "value": (
                                            "Coverage or cohort compatibility does not "
                                            "support a growth summary."
                                        ),
                                    }
                                ],
                            }
                        )
                        row["concentration"] = {
                            "currentTopFiveShare": concentration.current_share,
                            "currentDate": concentration.current_date,
                            "priorTopFiveIds": concentration.prior_top_five,
                            "priorDate": concentration.prior_date,
                            "growthExTopFive": concentration.growth_without_top_five.value
                            if concentration.growth_without_top_five is not None
                            else None,
                            "reasons": tuple(
                                sorted(
                                    set(concentration.flags)
                                    | (
                                        set(concentration.growth_without_top_five.flags)
                                        if concentration.growth_without_top_five is not None
                                        else set()
                                    )
                                )
                            ),
                        }
                        prior_growth = concentration.growth_without_top_five
                        details[row["detailId"]]["sections"].append(
                            {
                                "heading": "Concentration and growth without prior leaders",
                                "rows": [
                                    {
                                        "label": "Current top-five share",
                                        "value": field_text(concentration.current_share),
                                    },
                                    {
                                        "label": "Current top-five cap / full cap",
                                        "value": " / ".join(
                                            map(
                                                field_text,
                                                (
                                                    concentration.current_top_five_cap,
                                                    concentration.full_market_cap,
                                                ),
                                            )
                                        ),
                                    },
                                    {
                                        "label": "Current leaders",
                                        "value": field_text(concentration.current_top_five),
                                    },
                                    {
                                        "label": "Current capitalization date",
                                        "value": str(concentration.current_date),
                                    },
                                    {
                                        "label": "Prior leaders excluded from growth",
                                        "value": field_text(concentration.prior_top_five),
                                    },
                                    {
                                        "label": "Prior ranking date",
                                        "value": field_text(concentration.prior_date),
                                    },
                                    {
                                        "label": "Revenue growth excluding prior leaders",
                                        "value": field_text(
                                            prior_growth.value if prior_growth is not None else None
                                        ),
                                    },
                                    {
                                        "label": "Adjusted cohort ID",
                                        "value": field_text(
                                            prior_growth.cohort_id
                                            if prior_growth is not None
                                            else None
                                        ),
                                    },
                                    {
                                        "label": "Adjusted numerator / denominator",
                                        "value": " / ".join(
                                            map(
                                                field_text,
                                                (
                                                    prior_growth.numerator_total
                                                    if prior_growth is not None
                                                    else None,
                                                    prior_growth.denominator_total
                                                    if prior_growth is not None
                                                    else None,
                                                ),
                                            )
                                        ),
                                    },
                                    {
                                        "label": "Adjusted comparison allowed",
                                        "value": str(
                                            prior_growth.comparison_allowed
                                            if prior_growth is not None
                                            else False
                                        ),
                                    },
                                    {
                                        "label": "Flags",
                                        "value": field_text(row["concentration"]["reasons"]),
                                    },
                                    {
                                        "label": "Method",
                                        "value": (
                                            "Current top-five capitalization / "
                                            "full capitalization; growth excludes "
                                            "leaders ranked at the explicit prior "
                                            "date, using the "
                                            "matching remaining cohort. Coverage gates still apply."
                                        ),
                                    },
                                ],
                            }
                        )
                        evaluations.append(row)
        if as_of in (AS_OF, ALTERNATE_AS_OF):
            full_roster = roster(
                tuple(item.issuer_id for item in snapshots), as_of, "whole-fictional-universe"
            )
            for metric_id, _, _, _ in CATALOG:
                metric = "revenue_yoy" if metric_id == "revenue_growth" else metric_id
                for method in methods:
                    result = calculate_sector(
                        full_roster, snapshots, metric=metric, method=method, policy=POLICY
                    )
                    market.append(
                        evaluation(
                            result,
                            "market",
                            "Whole fictional universe",
                            metric_id,
                            details,
                            include_companies=False,
                        )
                    )
    for (sector_id, metric_id, method), points in series.items():
        projected = sector_history(
            tuple(points),
            as_of=AS_OF,
            series_key=points[0].series_key,
            years=5,
            membership_mode="current_members",
            policy_revision=POLICY.revision,
        )
        for selected_date in (AS_OF, ALTERNATE_AS_OF):
            comparison_series = (
                projected
                if selected_date == AS_OF
                else sector_history(
                    tuple(points),
                    as_of=selected_date,
                    series_key=points[0].series_key,
                    years=3,
                    membership_mode="current_members",
                    policy_revision=POLICY.revision,
                )
            )
            selected_row = next(
                row
                for row in evaluations
                if row["asOf"] == str(selected_date)
                and row["sectorId"] == sector_id
                and row["metricId"] == metric_id
                and row["method"] == method
            )
            comparison = compare_to_history(
                selected_row["value"],
                comparison_series.band,
                series_key=points[0].series_key,
                input_hash=comparison_series.snapshot_id,
            )
            details[selected_row["detailId"]]["sections"].append(
                {
                    "heading": "Three-year history comparison policy",
                    "rows": [
                        {
                            "label": "Eligible quarters",
                            "value": str(len(comparison_series.band.eligible)),
                        },
                        {
                            "label": "Required quarters",
                            "value": str(comparison_series.band.minimum_samples),
                        },
                        {
                            "label": "P25 / median / P75",
                            "value": " / ".join(
                                field_text(value)
                                for value in (
                                    comparison_series.band.p25,
                                    comparison_series.band.p50,
                                    comparison_series.band.p75,
                                )
                            ),
                        },
                        {"label": "Comparison", "value": comparison.relation or "Unavailable"},
                        {"label": "Flags", "value": field_text(comparison.flags)},
                        {
                            "label": "Membership mode",
                            "value": (
                                "Current members backcast; historical valuation labels suppressed."
                            ),
                        },
                    ],
                }
            )
        for point in projected.points:
            detail_id = (
                "history|"
                + str(point.quarter_end)
                + "|"
                + sector_id
                + "|"
                + metric_id
                + "|"
                + method
            )
            details[detail_id] = {
                "title": sector_id + " historical " + metric_id,
                "subtitle": "Fictional current-members backcast; not point-in-time sector history",
                "sections": [
                    {
                        "heading": "Observation evidence",
                        "rows": [
                            {"label": "Value", "value": field_text(point.value)},
                            {"label": "Quarter end", "value": str(point.quarter_end)},
                            {"label": "Pinned sample", "value": point.input_hash},
                            {"label": "Series snapshot", "value": projected.snapshot_id},
                            {"label": "Flags", "value": field_text(point.flags)},
                            {
                                "label": "Membership limitation",
                                "value": (
                                    "Current fictional members are backcast. Historical percentile "
                                    "verdicts are suppressed; actual dated membership is a "
                                    "production "
                                    "prerequisite."
                                ),
                            },
                        ],
                    }
                ],
                "sources": [
                    {
                        "label": "Deterministic fictional quarterly snapshots",
                        "capturedAt": str(point.quarter_end),
                        "transform": (
                            "Shared fundamentals → sector calculation → sector_history coverage "
                            "gate and explicit gap projection."
                        ),
                        "licence": (
                            "Synthetic inputs only; no historical production coverage claimed."
                        ),
                    }
                ],
            }
            history.append(
                {
                    "asOf": str(point.quarter_end),
                    "metricId": metric_id,
                    "method": method,
                    "sectorId": sector_id,
                    "value": point.value,
                    "status": status(point.value, point.flags),
                    "reasons": list(point.flags),
                    "detailId": detail_id,
                }
            )
    payload: dict[str, Any] = {
        "fictional": True,
        "context": {
            "title": "Sector Explorer",
            "universe": "84 fictional issuers · complete demonstration roster",
            "taxonomy": "Illustrative taxonomy v1 · not GICS or ICB",
            "membershipMode": "Current fictional members backcast; survivorship bias",
            "period": "Trailing twelve months · four exact calendar quarters",
            "currency": "USD",
            "rulesVersion": "sector-fixture-v1",
            "policyVersion": POLICY.revision,
            "asOfDates": [AS_OF.isoformat(), ALTERNATE_AS_OF.isoformat()],
            "defaultAsOf": AS_OF.isoformat(),
            "defaultSectorId": "computing",
            "sourceSnapshotId": digest(
                {str(key): [item.snapshot_id for item in values] for key, values in cache.items()}
            ),
            "prerequisites": [
                "Licensed and complete issuer universe with dated sector/industry membership",
                "Reviewed common-equity capitalization, corporate actions and quote calendar",
                "Income available to common-shareholder source contract",
                "Audited point-in-time financial/precision coverage and sector applicability",
                "Persistent snapshots, shared production API and live provider rights",
            ],
        },
        "sectors": [
            {
                "id": sector,
                "label": label,
                "color": color,
                **({"parentId": parent} if parent else {}),
            }
            for sector, label, color, parent in groups
        ],
        "metrics": [
            {"id": key, "label": label, "unit": unit, "definition": definition}
            for key, label, unit, definition in CATALOG
        ],
        "methods": list(METHODS),
        "evaluations": evaluations,
        "market": market,
        "history": history,
        "details": details,
    }
    return payload


def main() -> None:
    output = ROOT / "var" / "sector-explorer-raw.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_raw(), default=json_default, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote explicitly fictional Sector Explorer source bundle: {output}")


if __name__ == "__main__":
    main()
