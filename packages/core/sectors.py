"""Pure sector calculations over trusted, already evaluated company snapshots.

Source selection, membership history and production profile approval belong to
upstream services. This module preserves the declared roster independently of
metric availability. Individual company ratios are supplied by the shared
fundamentals engine and checked against their ordered operand hashes, never
recalculated here. Currency support is explicitly USD; no FX is inferred.
"""

import re
from bisect import bisect_right
from dataclasses import dataclass, replace
from datetime import date
from decimal import Context, Decimal, DecimalException, localcontext
from hashlib import sha256
from typing import Literal

from equity_core.company import CompanyMetric, EvidenceValue, evidence_issues
from equity_core.history import _quantile, _within_numeric_limits
from equity_core.metrics import _context
from equity_core.periods import _exact_sum

MetricId = Literal[
    "pe",
    "ps",
    "pfcf",
    "revenue_yoy",
    "operating_margin",
    "fcf_margin",
    "growth_breadth",
    "profit_breadth",
    "cash_breadth",
]
Method = Literal["total", "median", "mean"]
_METRICS = frozenset(
    (
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
)
_INFO = frozenset(("revised_view", "earliest_available", "extreme_margin", "gross_profit_derived"))


@dataclass(frozen=True)
class CompanySnapshot:
    issuer_id: str
    snapshot_id: str
    context_key: str
    applicable_metrics: tuple[str, ...]
    market_cap: EvidenceValue
    prior_market_cap: EvidenceValue
    common_income: EvidenceValue
    revenue: EvidenceValue
    prior_revenue: EvidenceValue
    operating_income: EvidenceValue
    fcf: EvidenceValue
    company_metrics: tuple[CompanyMetric, ...]


@dataclass(frozen=True)
class SectorRoster:
    issuer_ids: tuple[str, ...]
    context_key: str
    complete: bool
    evaluation_date: date
    input_hash: str
    lineage_refs: tuple[str, ...]
    prior_evaluation_date: date | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.issuer_ids, tuple)
            or any(not isinstance(i, str) or not i.strip() for i in self.issuer_ids)
            or not self.context_key.strip()
            or not self.input_hash.strip()
            or type(self.complete) is not bool
            or type(self.evaluation_date) is not date
            or not isinstance(self.lineage_refs, tuple)
            or not self.lineage_refs
            or any(not isinstance(i, str) or not i.strip() for i in self.lineage_refs)
        ):
            raise ValueError("A sector roster requires explicit immutable identity and evidence")
        if self.prior_evaluation_date is not None and (
            type(self.prior_evaluation_date) is not date
            or self.prior_evaluation_date >= self.evaluation_date
        ):
            raise ValueError("Prior capitalization needs an earlier explicit comparison date")


@dataclass(frozen=True)
class SectorPolicy:
    minimum_contributors: int
    minimum_issuer_coverage: Decimal
    minimum_cap_coverage: Decimal
    revision: str

    def __post_init__(self) -> None:
        if type(self.minimum_contributors) is not int or self.minimum_contributors < 1:
            raise ValueError("Minimum contributors must be a positive integer")
        if any(
            not isinstance(v, Decimal) or not v.is_finite() or not 0 <= v <= 1
            for v in (self.minimum_issuer_coverage, self.minimum_cap_coverage)
        ):
            raise ValueError("Coverage gates require explicit finite Decimal fractions")
        if not isinstance(self.revision, str) or not self.revision.strip():
            raise ValueError("A comparison policy revision is required")


@dataclass(frozen=True)
class IssuerExclusion:
    issuer_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CompanyObservation:
    issuer_id: str
    snapshot_id: str
    value: Decimal
    input_hash: str


@dataclass(frozen=True)
class SectorMetric:
    metric_id: str
    method: str
    value: Decimal | None
    numerator_total: Decimal | None
    denominator_total: Decimal | None
    n: int
    k: int
    v: int
    issuer_coverage: Decimal | None
    cap_coverage: Decimal | None
    ratio_eligibility: Decimal | None
    meaningful_company_count: int
    full_market_cap: Decimal | None
    contributing_market_cap: Decimal | None
    eligible_issuer_ids: tuple[str, ...]
    contributing_issuer_ids: tuple[str, ...]
    excluded: tuple[IssuerExclusion, ...]
    distribution_excluded: tuple[IssuerExclusion, ...]
    distribution: tuple[CompanyObservation, ...]
    p25: Decimal | None
    p50: Decimal | None
    p75: Decimal | None
    positive_count: int
    zero_count: int
    negative_count: int
    sign_basis: str
    zero_denominator_count: int
    comparison_allowed: bool
    flags: tuple[str, ...]
    financial_date_range: tuple[date, date] | None
    quote_date_range: tuple[date, date] | None
    context_key: str
    cohort_id: str
    policy_revision: str
    roster: SectorRoster
    company_snapshots: tuple[CompanySnapshot, ...]


def _sum(values: tuple[Decimal, ...]) -> Decimal:
    return _exact_sum(values, (1,) * len(values)) if values else Decimal(0)


def _fraction(numerator: Decimal, denominator: Decimal) -> Decimal:
    with localcontext(_context()):
        return numerator / denominator


def _companies(
    roster: SectorRoster, companies: tuple[CompanySnapshot, ...]
) -> tuple[dict[str, CompanySnapshot], dict[str, tuple[str, ...]]]:
    if not isinstance(companies, tuple) or any(
        not isinstance(c, CompanySnapshot) for c in companies
    ):
        raise ValueError("Company snapshots require an immutable tuple")
    selected: dict[str, CompanySnapshot] = {}
    rejected: dict[str, tuple[str, ...]] = {}
    for issuer in sorted(set(roster.issuer_ids)):
        matches = tuple(c for c in companies if c.issuer_id == issuer)
        if not matches:
            rejected[issuer] = ("company_snapshot_missing",)
        elif any(c != matches[0] for c in matches):
            rejected[issuer] = ("conflicting_issuer_snapshots",)
        elif (
            not matches[0].snapshot_id
            or matches[0].context_key != roster.context_key
            or not isinstance(matches[0].applicable_metrics, tuple)
            or not isinstance(matches[0].company_metrics, tuple)
        ):
            rejected[issuer] = ("company_context_mismatch",)
        else:
            selected[issuer] = matches[0]
    return selected, rejected


def _cap(company: CompanySnapshot, roster: SectorRoster, *, prior: bool = False) -> Decimal | None:
    amount = company.prior_market_cap if prior else company.market_cap
    cutoff = roster.prior_evaluation_date if prior else roster.evaluation_date
    if cutoff is None or evidence_issues(
        amount, basis="common_equity", evaluation_date=cutoff, instant=True, require_precision=False
    ):
        return None
    return amount.value if amount.value is not None and amount.value > 0 else None


def _spec(metric: str) -> tuple[tuple[str, ...], str | None, str | None, str | None]:
    pairs = {
        "pe": ("market_cap", "common_income"),
        "ps": ("market_cap", "revenue"),
        "pfcf": ("market_cap", "fcf"),
        "operating_margin": ("operating_income", "revenue"),
        "fcf_margin": ("fcf", "revenue"),
        "revenue_yoy": ("revenue", "prior_revenue"),
        "growth_breadth": ("revenue", "prior_revenue"),
    }
    if metric in pairs:
        pair = pairs[metric]
        return pair, pair[0], pair[1], "revenue_yoy" if metric == "growth_breadth" else metric
    return (("common_income" if metric == "profit_breadth" else "fcf",), None, None, None)


def _basis(field: str) -> str:
    return {
        "market_cap": "common_equity",
        "common_income": "income_available_common",
        "fcf": "cash_ppe_fcf",
    }.get(field, "consolidated_flow")


def _input_issues(
    company: CompanySnapshot,
    roster: SectorRoster,
    metric: str,
    fields: tuple[str, ...],
    denominator: str | None,
) -> tuple[str, ...]:
    issues: set[str] = set()
    if metric not in company.applicable_metrics:
        issues.add("unsupported_profile")
    for field in fields:
        value: EvidenceValue = getattr(company, field)
        issues.update(
            evidence_issues(
                value,
                basis=_basis(field),
                evaluation_date=roster.evaluation_date,
                instant=field == "market_cap",
                require_precision=field == denominator,
            )
        )
        if field == "market_cap" and not issues and value.value is not None and value.value <= 0:
            issues.add("market_cap_nonpositive")
    flow_periods = {
        (getattr(company, f).period_start, getattr(company, f).period_end)
        for f in fields
        if f not in ("market_cap", "prior_revenue")
    }
    if len(flow_periods) > 1:
        issues.add("incompatible_periods")
    return tuple(sorted(issues))


def _company_metric(
    company: CompanySnapshot, metric: str, fields: tuple[str, ...]
) -> tuple[CompanyObservation | None, tuple[str, ...]]:
    matches = tuple(m for m in company.company_metrics if m.metric_id == metric)
    if len(matches) != 1:
        return None, ("company_metric_not_unique",)
    result = matches[0]
    if result.operand_hashes != tuple(getattr(company, f).input_hash for f in fields):
        return None, ("company_metric_input_mismatch",)
    reasons = set(result.flags) - _INFO
    if (
        not result.usable
        or not isinstance(result.value, Decimal)
        or not result.value.is_finite()
        or not _within_numeric_limits(result.value)
        or not isinstance(result.input_hash, str)
        or re.fullmatch(r"[a-f0-9]{64}", result.input_hash) is None
    ):
        reasons.add("company_metric_unavailable")
    if (
        not reasons
        and result.value is not None
        and metric in ("pe", "ps", "pfcf")
        and result.value <= 0
    ):
        reasons.add("company_multiple_nonpositive")
    if reasons:
        return None, tuple(sorted(reasons))
    assert result.value is not None
    return CompanyObservation(
        company.issuer_id, company.snapshot_id, result.value, result.input_hash
    ), ()


def _dates(values: list[date]) -> tuple[date, date] | None:
    return (min(values), max(values)) if values else None


def calculate_sector(
    roster: SectorRoster,
    companies: tuple[CompanySnapshot, ...],
    *,
    metric: str,
    method: Method,
    policy: SectorPolicy,
) -> SectorMetric:
    """Evaluate one metric/method over the complete declared issuer roster."""
    if metric not in _METRICS or method not in ("total", "median", "mean"):
        raise ValueError("Unknown sector metric or aggregation method")
    fields, numerator, denominator, company_metric = _spec(metric)
    selected, base_rejections = _companies(roster, companies)
    complete: dict[str, CompanySnapshot] = {}
    contributions: dict[str, CompanySnapshot] = {}
    excluded = dict(base_rejections)
    distribution_excluded = dict(base_rejections)
    distribution: list[CompanyObservation] = []
    flags: set[str] = set()
    positive = zero = negative = zero_denominators = 0
    sign_basis = (
        "revenue_yoy"
        if metric in ("revenue_yoy", "growth_breadth")
        else numerator
        if metric in ("operating_margin", "fcf_margin")
        else denominator or fields[0]
    )
    assert sign_basis is not None
    for issuer, company in selected.items():
        issues = _input_issues(company, roster, metric, fields, denominator)
        if issues:
            excluded[issuer] = distribution_excluded[issuer] = issues
            continue
        complete[issuer] = company
        for field in fields:
            flags.update(set(getattr(company, field).flags) & _INFO)
        sign_field = (
            numerator if metric in ("operating_margin", "fcf_margin") else denominator or fields[0]
        )
        assert sign_field is not None
        value_for_sign = getattr(company, sign_field).value
        if denominator is not None:
            zero_denominators += getattr(company, denominator).value == 0
        assert value_for_sign is not None
        observation = None
        if company_metric is not None:
            metric_issues: tuple[str, ...]
            if denominator is not None and getattr(company, denominator).value <= 0:
                metric_issues = ("company_denominator_nonpositive",)
            elif (
                denominator is not None
                and getattr(company, denominator).value
                <= getattr(company, denominator).absolute_error
            ):
                metric_issues = ("company_denominator_indistinguishable_from_zero",)
            else:
                observation, metric_issues = _company_metric(company, company_metric, fields)
            if observation is not None:
                distribution.append(observation)
            else:
                distribution_excluded[issuer] = metric_issues
        growth = metric in ("revenue_yoy", "growth_breadth")
        if growth and observation is None:
            excluded[issuer] = distribution_excluded[issuer]
            continue
        if growth:
            assert observation is not None
            value_for_sign = observation.value
        positive += value_for_sign > 0
        zero += value_for_sign == 0
        negative += value_for_sign < 0
        if company_metric is None or method == "total" or observation is not None:
            contributions[issuer] = company
        else:
            excluded[issuer] = distribution_excluded[issuer]
    n, k, v = len(set(roster.issuer_ids)), len(complete), len(contributions)
    value = numerator_total = denominator_total = None
    values = sorted(item.value for item in distribution)
    p25 = p50 = p75 = None
    try:
        if values:
            p25, p50, p75 = (
                _quantile(values, p) for p in (Decimal(".25"), Decimal(".5"), Decimal(".75"))
            )
        if v:
            if metric in ("profit_breadth", "cash_breadth", "growth_breadth"):
                numerator_total, denominator_total = Decimal(positive), Decimal(v)
                value = _fraction(numerator_total, denominator_total)
            elif method == "median":
                value = p50
            elif method == "mean":
                numerator_total, denominator_total = _sum(tuple(values)), Decimal(v)
                value = _fraction(numerator_total, denominator_total)
            else:
                assert numerator is not None and denominator is not None
                numerator_total = _sum(
                    tuple(getattr(c, numerator).value for c in contributions.values())
                )
                denominator_total = _sum(
                    tuple(getattr(c, denominator).value for c in contributions.values())
                )
                error = _sum(
                    tuple(getattr(c, denominator).absolute_error for c in contributions.values())
                )
                if denominator_total <= 0:
                    flags.add("denominator_nonpositive")
                elif denominator_total <= error:
                    flags.add("denominator_indistinguishable_from_zero")
                else:
                    # Form the exact monetary change first. Dividing before
                    # subtracting one can erase a small but real aggregate change.
                    dividend = (
                        _exact_sum((numerator_total, denominator_total), (1, -1))
                        if metric == "revenue_yoy"
                        else numerator_total
                    )
                    value = _fraction(dividend, denominator_total)
        else:
            flags.add("no_contributors")
    except (DecimalException, ValueError):
        value = None
        flags.add("unsupported_numeric_range")
    full_cap = contributing_cap = cap_coverage = None
    try:
        caps = {issuer: _cap(company, roster) for issuer, company in selected.items()}
        if n and len(caps) == n and all(v is not None for v in caps.values()):
            full_cap = _sum(tuple(v for v in caps.values() if v is not None))
            contributing_cap = _sum(
                tuple(
                    cap
                    for issuer, cap in caps.items()
                    if issuer in contributions and cap is not None
                )
            )
            cap_coverage = _fraction(contributing_cap, full_cap)
        else:
            flags.add("full_capitalization_unknown")
        issuer_coverage = _fraction(Decimal(k), Decimal(n)) if n else None
        ratio_eligibility = (
            _fraction(Decimal(len(distribution)), Decimal(k)) if k and company_metric else None
        )
    except (DecimalException, ValueError):
        issuer_coverage = ratio_eligibility = None
        flags.add("unsupported_numeric_range")
    if v < policy.minimum_contributors:
        flags.add("small_sample")
    if not roster.complete:
        flags.add("partial_sector_universe")
    gate = (
        roster.complete
        and value is not None
        and v >= policy.minimum_contributors
        and issuer_coverage is not None
        and issuer_coverage >= policy.minimum_issuer_coverage
        and cap_coverage is not None
        and cap_coverage >= policy.minimum_cap_coverage
    )
    if not gate:
        flags.add("limited_coverage")
    finance_dates = [
        getattr(c, f).period_end
        for c in contributions.values()
        for f in fields
        if f != "market_cap" and getattr(c, f).period_end is not None
    ]
    quote_dates = [
        c.market_cap.period_end
        for c in contributions.values()
        if c.market_cap.period_end is not None
    ]
    cohort = "|".join(
        (
            roster.input_hash,
            metric,
            method,
            *(f"{i}:{c.snapshot_id}" for i, c in contributions.items()),
        )
    )
    return SectorMetric(
        metric,
        method,
        value,
        numerator_total,
        denominator_total,
        n,
        k,
        v,
        issuer_coverage,
        cap_coverage,
        ratio_eligibility,
        len(distribution),
        full_cap,
        contributing_cap,
        tuple(complete),
        tuple(contributions),
        tuple(IssuerExclusion(i, r) for i, r in sorted(excluded.items())),
        tuple(IssuerExclusion(i, r) for i, r in sorted(distribution_excluded.items())),
        tuple(sorted(distribution, key=lambda item: (item.value, item.issuer_id))),
        p25,
        p50,
        p75,
        positive,
        zero,
        negative,
        sign_basis,
        zero_denominators,
        gate,
        tuple(sorted(flags)),
        _dates(finance_dates),
        _dates(quote_dates),
        roster.context_key,
        sha256(cohort.encode()).hexdigest(),
        policy.revision,
        roster,
        companies,
    )


@dataclass(frozen=True)
class Concentration:
    current_top_five: tuple[str, ...] | None
    prior_top_five: tuple[str, ...] | None
    current_share: Decimal | None
    current_top_five_cap: Decimal | None
    full_market_cap: Decimal | None
    growth_without_top_five: SectorMetric | None
    current_date: date
    prior_date: date | None
    flags: tuple[str, ...]
    roster: SectorRoster
    company_snapshots: tuple[CompanySnapshot, ...]


def calculate_concentration(
    roster: SectorRoster, companies: tuple[CompanySnapshot, ...], *, policy: SectorPolicy
) -> Concentration:
    """Current concentration and growth excluding prior-date leaders, never known subsets.

    Rankings require every declared issuer's capitalization. Ties use issuer ID;
    the prior leaders are frozen before matching both revenue periods. Incomplete
    universes cannot establish which five are the sector's largest issuers.
    """
    selected, rejected = _companies(roster, companies)
    n = len(set(roster.issuer_ids))
    flags: set[str] = set()
    current_ids = prior_ids = None
    share = current_top_cap = full_cap = None
    adjusted_growth = None
    if not roster.complete:
        flags.add("partial_sector_universe")
    elif n and not rejected:
        for prior in (False, True):
            caps = {i: _cap(c, roster, prior=prior) for i, c in selected.items()}
            if any(v is None for v in caps.values()):
                flags.add(
                    "prior_capitalization_unknown" if prior else "current_capitalization_unknown"
                )
                continue
            known_caps = {i: v for i, v in caps.items() if v is not None}
            ordered = tuple(sorted(known_caps, key=lambda i: (known_caps[i].copy_negate(), i)))[:5]
            if prior:
                prior_ids = ordered
            else:
                try:
                    full_cap = _sum(tuple(known_caps.values()))
                    current_top_cap = _sum(tuple(known_caps[i] for i in ordered))
                    share = _fraction(current_top_cap, full_cap)
                    current_ids = ordered
                except (DecimalException, ValueError):
                    share = current_top_cap = full_cap = None
                    flags.add("unsupported_numeric_range")
        if prior_ids is not None:
            remaining = tuple(i for i in sorted(set(roster.issuer_ids)) if i not in prior_ids)
            manifest = sha256(
                (roster.input_hash + "|exclude-prior-top-five|" + "|".join(prior_ids)).encode()
            ).hexdigest()
            subset = replace(
                roster,
                issuer_ids=remaining,
                input_hash=manifest,
                lineage_refs=roster.lineage_refs + ("prior-top-five:" + ",".join(prior_ids),),
            )
            adjusted_growth = calculate_sector(
                subset, companies, metric="revenue_yoy", method="total", policy=policy
            )
    else:
        flags.update(("current_capitalization_unknown", "prior_capitalization_unknown"))
    return Concentration(
        current_ids,
        prior_ids,
        share,
        current_top_cap,
        full_cap,
        adjusted_growth,
        roster.evaluation_date,
        roster.prior_evaluation_date,
        tuple(sorted(flags)),
        roster,
        companies,
    )


@dataclass(frozen=True)
class HistogramBin:
    lower: Decimal
    upper: Decimal
    count: int
    issuer_ids: tuple[str, ...]
    upper_inclusive: bool


def histogram(
    observations: tuple[CompanyObservation, ...], *, bin_count: int = 8
) -> tuple[HistogramBin, ...]:
    """Equal-width full-range bins; left-inclusive, last upper boundary inclusive.

    Bin boundaries retain sufficient precision to distinguish supplied endpoint
    digits. Repeating interior divisions are rounded only at that bounded precision;
    actual point membership is decided here, never by browser arithmetic. A single
    observed value receives one closed bin. No trimming or axis clipping occurs.
    """
    if type(bin_count) is not int or not 1 <= bin_count <= 100:
        raise ValueError("Histogram bin count must be between 1 and 100")
    if (
        not isinstance(observations, tuple)
        or any(
            not isinstance(p, CompanyObservation)
            or not isinstance(p.value, Decimal)
            or not p.value.is_finite()
            or not _within_numeric_limits(p.value)
            or not p.issuer_id
            or not p.snapshot_id
            or not p.input_hash
            for p in observations
        )
        or len({p.issuer_id for p in observations}) != len(observations)
    ):
        raise ValueError("Histogram requires unique evidence-bearing finite company observations")
    if not observations:
        return ()
    minimum = min(p.value for p in observations)
    maximum = max(p.value for p in observations)
    if minimum == maximum:
        ids = tuple(sorted(p.issuer_id for p in observations))
        return (HistogramBin(minimum, maximum, len(ids), ids, True),)
    low_exp, high_exp = minimum.as_tuple().exponent, maximum.as_tuple().exponent
    assert isinstance(low_exp, int) and isinstance(high_exp, int)
    precision = max(50, max(minimum.adjusted(), maximum.adjusted()) - min(low_exp, high_exp) + 10)
    with localcontext(Context(prec=precision, Emin=-9999, Emax=9999)):
        span = maximum - minimum
        boundaries = tuple(
            minimum + span * Decimal(i) / Decimal(bin_count) for i in range(bin_count)
        ) + (maximum,)
    members: list[list[str]] = [[] for _ in range(bin_count)]
    for point in observations:
        index = min(bisect_right(boundaries, point.value) - 1, bin_count - 1)
        members[index].append(point.issuer_id)
    return tuple(
        HistogramBin(
            boundaries[i],
            boundaries[i + 1],
            len(members[i]),
            tuple(sorted(members[i])),
            i == bin_count - 1,
        )
        for i in range(bin_count)
    )
