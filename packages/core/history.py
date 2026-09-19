"""Pure history bands for already evaluated, evidence-backed metric samples.

The caller supplies comparable samples: ``series_key`` identifies the metric,
unit/currency, accounting mode, formula and split/share basis; ``input_hash``
pins the caller's evaluated input set. This module does not fetch or select
financial facts, verify that evidence, choose trading sessions, or fill gaps.
All supplied quality flags exclude a sample. Conflicting observations for one
quarter are all excluded; exact repeated evidence cannot increase sample count.

Windows are (as_of minus the explicit calendar years, as_of], with February 29
clamped to February 28 where required. Only completed calendar quarter ends
contribute. Percentiles interpolate at (n - 1) * p using an independent
Decimal context with enough precision for exact bounded interpolation. This
interpolation describes the observed distribution; it does not invent missing
quarter samples.

Finite Decimals are limited to 1000 coefficient digits, absolute stored exponent
1000 and absolute adjusted exponent 1000. These computational limits exclude
extreme inputs with ``numeric_range_exceeded`` before arithmetic. They are not
financial-quality thresholds; upstream metric evaluation supplies those flags.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, Inexact, localcontext
from typing import Literal


@dataclass(frozen=True)
class HistoryPoint:
    quarter_end: date
    value: Decimal | None
    series_key: str
    input_hash: str
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.quarter_end) is not date:
            raise ValueError("History samples require exact dates")
        if not isinstance(self.series_key, str) or not isinstance(self.input_hash, str):
            raise ValueError("History sample identity fields require strings")
        _check_flags(self.flags)


@dataclass(frozen=True)
class HistoryPolicy:
    """Explicit caller policy; no production sample-count default is implied."""

    years: int
    minimum_samples: int
    revision: str

    def __post_init__(self) -> None:
        if type(self.years) is not int or self.years not in (3, 5, 10):
            raise ValueError("History window must explicitly be 3, 5 or 10 years")
        if type(self.minimum_samples) is not int or not 1 <= self.minimum_samples <= 4 * self.years:
            raise ValueError("History minimum must fit the selected window")
        if not isinstance(self.revision, str) or not self.revision.strip():
            raise ValueError("History policy requires an explicit revision")


@dataclass(frozen=True)
class ExcludedHistoryPoint:
    point: HistoryPoint
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class HistoryBand:
    """Selected window, sample coverage, exclusions and its P25/P50/P75 range."""

    years: int
    window_start: date
    window_end: date
    series_key: str
    policy_revision: str
    minimum_samples: int
    eligible: tuple[HistoryPoint, ...]
    excluded: tuple[ExcludedHistoryPoint, ...]
    expected_quarter_ends: tuple[date, ...]
    missing_quarter_ends: tuple[date, ...]
    p25: Decimal | None
    p50: Decimal | None
    p75: Decimal | None
    flags: tuple[str, ...] = ()


def _check_flags(flags: tuple[str, ...]) -> None:
    if not isinstance(flags, tuple) or any(
        not isinstance(flag, str) or not flag.strip() for flag in flags
    ):
        raise ValueError("Quality flags require an immutable tuple of nonempty strings")


def _within_numeric_limits(value: Decimal) -> bool:
    """Bound work and exponent spread, not economically meaningful metric values."""
    parts = value.as_tuple()
    assert isinstance(parts.exponent, int)
    return (
        len(parts.digits) <= 1000 and abs(parts.exponent) <= 1000 and abs(value.adjusted()) <= 1000
    )


def _quantile(values: list[Decimal], proportion: Decimal) -> Decimal:
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        position = Decimal(len(values) - 1) * proportion
        lower = int(position)
        weight = position - Decimal(lower)
        if not weight:
            return values[lower]
        left, right = values[lower], values[lower + 1]
        left_exponent, right_exponent = left.as_tuple().exponent, right.as_tuple().exponent
        assert isinstance(left_exponent, int) and isinstance(right_exponent, int)
        # Quarter weights need at most two extra decimal places. Preserve the
        # full endpoint span plus carry space, including cancellation of large
        # opposite signs; rounding endpoints could invert a later comparison.
        precision = max(
            50, max(left.adjusted(), right.adjusted()) - min(left_exponent, right_exponent) + 4
        )
        exact = Context(prec=precision, rounding=ROUND_HALF_EVEN)
        exact.traps[Inexact] = True
        with localcontext(exact):
            return left * (Decimal(1) - weight) + right * weight


def _identity(point: HistoryPoint) -> tuple[str, str, str, tuple[str, ...]]:
    return (point.series_key, repr(point.value), repr(point.input_hash), point.flags)


def historical_band(
    points: tuple[HistoryPoint, ...], *, as_of: date, series_key: str, policy: HistoryPolicy
) -> HistoryBand:
    """Calculate the own-history middle range without interpreting investment merit."""
    if not isinstance(policy, HistoryPolicy):
        raise ValueError("An explicit history policy is required")
    if type(as_of) is not date or as_of.year <= policy.years:
        raise ValueError("History date must define a representable window")
    if not isinstance(points, tuple) or any(
        not isinstance(point, HistoryPoint) for point in points
    ):
        raise ValueError("History requires an immutable tuple of typed samples")
    if not isinstance(series_key, str) or not series_key.strip():
        raise ValueError("An explicit comparable series identity is required")
    start_year = as_of.year - policy.years
    start = as_of.replace(
        year=start_year, day=min(as_of.day, monthrange(start_year, as_of.month)[1])
    )
    identities: dict[date, set[tuple[str, str, str, tuple[str, ...]]]] = {}
    for point in points:
        if point.series_key == series_key and start < point.quarter_end <= as_of:
            identities.setdefault(point.quarter_end, set()).add(_identity(point))
    conflicting = {day for day, variants in identities.items() if len(variants) > 1}
    seen: set[date] = set()
    eligible_list: list[HistoryPoint] = []
    excluded_list: list[ExcludedHistoryPoint] = []
    for point in sorted(points, key=lambda sample: (sample.quarter_end, _identity(sample))):
        reasons = list(point.flags)
        if point.quarter_end <= start:
            reasons.append("outside_window")
        elif point.quarter_end > as_of:
            reasons.append("after_as_of")
        if (point.quarter_end.month, point.quarter_end.day) not in (
            (3, 31),
            (6, 30),
            (9, 30),
            (12, 31),
        ):
            reasons.append("not_quarter_end")
        if point.series_key != series_key:
            reasons.append("incompatible_series")
        if not isinstance(point.input_hash, str) or not point.input_hash.strip():
            reasons.append("missing_lineage")
        if point.value is None:
            reasons.append("missing_value")
        elif not isinstance(point.value, Decimal):
            reasons.append("invalid_value_type")
        elif not point.value.is_finite():
            reasons.append("nonfinite_value")
        elif not _within_numeric_limits(point.value):
            reasons.append("numeric_range_exceeded")
        if point.series_key == series_key and point.quarter_end in conflicting:
            reasons.append("conflicting_quarter")
        elif not reasons and point.quarter_end in seen:
            reasons.append("duplicate_sample")
        if reasons:
            excluded_list.append(ExcludedHistoryPoint(point, tuple(sorted(set(reasons)))))
        else:
            eligible_list.append(point)
            seen.add(point.quarter_end)
    eligible, excluded = tuple(eligible_list), tuple(excluded_list)
    expected = tuple(
        day
        for year in range(start.year, as_of.year + 1)
        for month, end in ((3, 31), (6, 30), (9, 30), (12, 31))
        if start < (day := date(year, month, end)) <= as_of
    )
    missing = tuple(day for day in expected if day not in {point.quarter_end for point in eligible})
    values = sorted(point.value for point in eligible if point.value is not None)
    sufficient = len(values) >= policy.minimum_samples
    return HistoryBand(
        policy.years,
        start,
        as_of,
        series_key,
        policy.revision,
        policy.minimum_samples,
        eligible,
        excluded,
        expected,
        missing,
        _quantile(values, Decimal(".25")) if sufficient else None,
        _quantile(values, Decimal(".5")) if sufficient else None,
        _quantile(values, Decimal(".75")) if sufficient else None,
        () if sufficient else ("insufficient_history",),
    )


@dataclass(frozen=True)
class HistoryComparison:
    relation: Literal["below", "within", "above"] | None
    value: Decimal | None
    input_hash: str
    series_key: str
    band: HistoryBand
    flags: tuple[str, ...] = ()


def compare_to_history(
    value: Decimal | None,
    band: HistoryBand,
    *,
    series_key: str,
    input_hash: str,
    flags: tuple[str, ...] = (),
) -> HistoryComparison:
    """Describe position against own history, never fair value or an investment action."""
    _check_flags(flags)
    reasons = list(flags) + list(band.flags)
    if series_key != band.series_key:
        reasons.append("incompatible_series")
    if not isinstance(input_hash, str) or not input_hash.strip():
        reasons.append("missing_lineage")
    if value is None:
        reasons.append("missing_value")
    elif not isinstance(value, Decimal):
        reasons.append("invalid_value_type")
    elif not value.is_finite():
        reasons.append("nonfinite_value")
    elif not _within_numeric_limits(value):
        reasons.append("numeric_range_exceeded")
    if band.p25 is None or band.p75 is None:
        reasons.append("comparison_unavailable")
    if reasons:
        return HistoryComparison(
            None,
            value if isinstance(value, Decimal) and value.is_finite() else None,
            input_hash,
            series_key,
            band,
            tuple(sorted(set(reasons))),
        )
    assert value is not None and band.p25 is not None and band.p75 is not None
    relation: Literal["below", "within", "above"] = (
        "below" if value < band.p25 else "above" if value > band.p75 else "within"
    )
    return HistoryComparison(relation, value, input_hash, series_key, band)
