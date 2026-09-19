"""Hand-computed history bands over already evaluated, fictional metric samples."""

from datetime import date
from decimal import Decimal

import pytest
from equity_core.history import HistoryPoint, HistoryPolicy, historical_band

SERIES = "reported_diluted_pe:USD:common:split-basis-1"


def point(year, month, numeric, **changes):
    day = 31 if month in (3, 12) else 30
    values = dict(
        quarter_end=date(year, month, day),
        value=Decimal(numeric) if numeric is not None else None,
        series_key=SERIES,
        input_hash=f"fictional-{year}-{month}",
        flags=(),
    )
    values.update(changes)
    return HistoryPoint(**values)


def test_linear_interpolation_and_selected_window_are_explicit():
    samples = tuple(
        point(2025, month, value)
        for month, value in zip((3, 6, 9, 12), (10, 20, 30, 40), strict=True)
    )
    result = historical_band(
        samples,
        as_of=date(2025, 12, 31),
        series_key=SERIES,
        policy=HistoryPolicy(years=3, minimum_samples=4, revision="fixture-v1"),
    )
    assert (result.p25, result.p50, result.p75) == (Decimal("17.5"), Decimal("25"), Decimal("32.5"))
    assert result.window_start == date(2022, 12, 31) and result.window_end == date(2025, 12, 31)
    assert result.years == 3 and result.policy_revision == "fixture-v1"
    assert result.eligible == samples and not result.flags


def test_three_five_and_ten_year_options_use_the_entire_selected_window():
    samples = tuple(
        point(year, month, year) for year in range(2010, 2027) for month in (3, 6, 9, 12)
    )
    for years, required in ((3, 12), (5, 20), (10, 40)):
        result = historical_band(
            samples,
            as_of=date(2025, 12, 31),
            series_key=SERIES,
            policy=HistoryPolicy(years, required, "full-quarter-fixture"),
        )
        assert result.years == years and len(result.eligible) == required
        assert result.window_start == date(2025 - years, 12, 31)
        assert result.eligible[0].quarter_end == date(2026 - years, 3, 31)
        assert result.eligible[-1].quarter_end == date(2025, 12, 31)
        assert all(
            result.window_start < p.quarter_end <= result.window_end for p in result.eligible
        )
        assert len(result.excluded) == len(samples) - required


def test_insufficient_history_never_pads_or_shortens_any_requested_window():
    for years, required in ((3, 12), (5, 20), (10, 40)):
        samples = tuple(
            point(year, month, year)
            for year in range(2025 - years, 2026)
            for month in (3, 6, 9, 12)
            if (year, month) != (2025, 12)
        )
        result = historical_band(
            samples,
            as_of=date(2025, 12, 31),
            series_key=SERIES,
            policy=HistoryPolicy(years, required, "full-quarter-fixture"),
        )
        assert (result.p25, result.p50, result.p75) == (None, None, None)
        assert result.flags == ("insufficient_history",) and len(result.eligible) == required - 1
        assert result.years == years and len(result.expected_quarter_ends) == required
        assert result.missing_quarter_ends == (date(2025, 12, 31),)
    empty = historical_band(
        (),
        as_of=date(2025, 12, 31),
        series_key=SERIES,
        policy=HistoryPolicy(3, 12, "empty-fixture"),
    )
    assert empty.p25 is None and len(empty.missing_quarter_ends) == 12


def test_unusable_or_incompatible_samples_are_excluded_with_their_evidence():
    good = tuple(
        point(2025, month, value)
        for month, value in zip((3, 6, 9, 12), (10, 20, 30, 40), strict=True)
    )
    cases = (
        (point(2024, 3, None), "missing_value"),
        (point(2024, 3, "NaN"), "nonfinite_value"),
        (point(2024, 3, "Infinity"), "nonfinite_value"),
        (point(2024, 3, 900, value=1.5), "invalid_value_type"),
        (point(2024, 3, 900, flags=("stale",)), "stale"),
        (point(2024, 3, 900, input_hash=""), "missing_lineage"),
        (point(2024, 3, 900, series_key="adjusted_pe"), "incompatible_series"),
        (point(2024, 3, 900, quarter_end=date(2024, 3, 30)), "not_quarter_end"),
    )
    for bad, reason in cases:
        result = historical_band(
            (*good, bad),
            as_of=date(2025, 12, 31),
            series_key=SERIES,
            policy=HistoryPolicy(3, 4, "eligibility-fixture"),
        )
        assert result.eligible == good and result.p25 == Decimal("17.5")
        assert len(result.excluded) == 1 and result.excluded[0].point == bad
        assert reason in result.excluded[0].reasons


def test_duplicate_quarters_cannot_inflate_counts_or_select_a_convenient_value():
    good = tuple(
        point(2025, month, value)
        for month, value in zip((3, 6, 9, 12), (10, 20, 30, 40), strict=True)
    )
    policy = HistoryPolicy(3, 4, "duplicate-fixture")
    repeated = historical_band(
        (*good, good[0]), as_of=date(2025, 12, 31), series_key=SERIES, policy=policy
    )
    assert repeated.eligible == good and repeated.p25 == Decimal("17.5")
    assert repeated.excluded[0].reasons == ("duplicate_sample",)
    conflicting = (*good, point(2025, 3, 999, input_hash="different-evidence"))
    result = historical_band(
        conflicting, as_of=date(2025, 12, 31), series_key=SERIES, policy=policy
    )
    assert len(result.eligible) == 3 and result.p25 is None
    assert result.flags == ("insufficient_history",)
    assert date(2025, 3, 31) in result.missing_quarter_ends
    assert all("conflicting_quarter" in sample.reasons for sample in result.excluded)
    assert result == historical_band(
        tuple(reversed(conflicting)), as_of=date(2025, 12, 31), series_key=SERIES, policy=policy
    )


def test_middle_range_comparison_treats_percentile_equality_as_within():
    from equity_core.history import compare_to_history

    samples = tuple(
        point(2025, month, value)
        for month, value in zip((3, 6, 9, 12), (10, 20, 30, 40), strict=True)
    )
    band = historical_band(
        samples,
        as_of=date(2025, 12, 31),
        series_key=SERIES,
        policy=HistoryPolicy(3, 4, "comparison-fixture"),
    )
    for value, relation in (
        ("17.49", "below"),
        ("17.5", "within"),
        ("25", "within"),
        ("32.5", "within"),
        ("32.51", "above"),
    ):
        result = compare_to_history(Decimal(value), band, series_key=SERIES, input_hash="current")
        assert result.relation == relation and not result.flags
        assert result.input_hash == "current" and result.band == band


def test_unusable_current_metrics_or_insufficient_history_cannot_receive_a_comparison():
    from equity_core.history import compare_to_history

    samples = tuple(
        point(2025, month, value)
        for month, value in zip((3, 6, 9, 12), (10, 20, 30, 40), strict=True)
    )
    band = historical_band(
        samples,
        as_of=date(2025, 12, 31),
        series_key=SERIES,
        policy=HistoryPolicy(3, 4, "comparison-fixture"),
    )
    cases = (
        (None, SERIES, "current", (), "missing_value"),
        (Decimal("NaN"), SERIES, "current", (), "nonfinite_value"),
        (1.5, SERIES, "current", (), "invalid_value_type"),
        (Decimal(1), SERIES, "current", ("stale",), "stale"),
        (Decimal(1), "adjusted_pe", "current", (), "incompatible_series"),
        (Decimal(1), SERIES, "", (), "missing_lineage"),
    )
    for value, series, lineage, flags, reason in cases:
        result = compare_to_history(value, band, series_key=series, input_hash=lineage, flags=flags)
        assert result.relation is None and reason in result.flags
    missing = historical_band(
        (),
        as_of=date(2025, 12, 31),
        series_key=SERIES,
        policy=HistoryPolicy(3, 12, "comparison-fixture"),
    )
    result = compare_to_history(Decimal(1), missing, series_key=SERIES, input_hash="current")
    assert result.relation is None and "insufficient_history" in result.flags


def test_policy_and_date_contract_rejects_implicit_or_impossible_choices():
    for years, minimum, revision in (
        (4, 12, "v1"),
        (True, 4, "v1"),
        (3, 0, "v1"),
        (3, 13, "v1"),
        (3, True, "v1"),
        (3, 12, ""),
    ):
        with pytest.raises(ValueError):
            HistoryPolicy(years, minimum, revision)
    policy = HistoryPolicy(3, 12, "v1")
    for samples, as_of, series in (
        ([], date(2025, 12, 31), SERIES),
        ((), date(2, 1, 1), SERIES),
        ((), date(2025, 12, 31), ""),
    ):
        with pytest.raises(ValueError):
            historical_band(samples, as_of=as_of, series_key=series, policy=policy)
    with pytest.raises(ValueError):
        point(2025, 3, 1, flags=["stale"])


def test_numeric_resource_limits_exclude_extreme_inputs_before_percentile_arithmetic():
    from equity_core.history import compare_to_history

    good = tuple(
        point(2025, month, value)
        for month, value in zip((3, 6, 9, 12), (10, 20, 30, 40), strict=True)
    )
    policy = HistoryPolicy(3, 4, "numeric-limits-fixture")
    for value in (Decimal("1e1001"), Decimal("1e-1001"), Decimal("9" * 1001)):
        result = historical_band(
            (*good, point(2024, 3, value)),
            as_of=date(2025, 12, 31),
            series_key=SERIES,
            policy=policy,
        )
        assert result.p25 == Decimal("17.5") and len(result.eligible) == 4
        assert result.excluded[0].reasons == ("numeric_range_exceeded",)
        comparison = compare_to_history(value, result, series_key=SERIES, input_hash="current")
        assert comparison.relation is None and "numeric_range_exceeded" in comparison.flags


def test_leap_day_as_of_preserves_calendar_year_window_and_completed_quarters():
    samples = tuple(
        point(year, month, year) for year in range(2020, 2025) for month in (3, 6, 9, 12)
    )
    result = historical_band(
        samples,
        as_of=date(2024, 2, 29),
        series_key=SERIES,
        policy=HistoryPolicy(3, 12, "leap-fixture"),
    )
    assert result.window_start == date(2021, 2, 28) and result.window_end == date(2024, 2, 29)
    assert len(result.eligible) == 12 and len(result.expected_quarter_ends) == 12
    assert result.eligible[0].quarter_end == date(2021, 3, 31)
    assert result.eligible[-1].quarter_end == date(2023, 12, 31)
    assert not result.missing_quarter_ends
    assert all(
        "after_as_of" in p.reasons for p in result.excluded if p.point.quarter_end.year == 2024
    )


def test_history_arithmetic_is_independent_of_callers_decimal_context():
    from decimal import ROUND_DOWN, Inexact, localcontext

    samples = tuple(
        point(2025, month, value)
        for month, value in zip((3, 6, 9, 12), ("10.1", "20.2", "30.3", "40.4"), strict=True)
    )
    with localcontext() as ambient:
        ambient.prec = 2
        ambient.rounding = ROUND_DOWN
        ambient.Emax = 2
        ambient.Emin = -2
        ambient.traps[Inexact] = True
        before = repr(ambient)
        result = historical_band(
            samples,
            as_of=date(2025, 12, 31),
            series_key=SERIES,
            policy=HistoryPolicy(3, 4, "context-fixture"),
        )
        assert (result.p25, result.p50, result.p75) == (
            Decimal("17.675"),
            Decimal("25.25"),
            Decimal("32.825"),
        )
        assert repr(ambient) == before


def test_generic_history_allows_eligible_negative_zero_and_singleton_values():
    from equity_core.history import compare_to_history

    series = "reported_operating_margin:dimensionless:formula-v1"
    for value in ("-12.5", "0", "40"):
        sample = point(2025, 12, value, series_key=series)
        result = historical_band(
            (sample,),
            as_of=date(2025, 12, 31),
            series_key=series,
            policy=HistoryPolicy(3, 1, "single-observation-fixture"),
        )
        assert result.p25 == result.p50 == result.p75 == Decimal(value)
        assert len(result.missing_quarter_ends) == 11
        assert not result.flags
        comparison = compare_to_history(
            Decimal(value), result, series_key=series, input_hash="current"
        )
        assert comparison.relation == "within"


def test_history_preserves_source_digits_at_percentile_boundaries():
    from equity_core.history import compare_to_history

    value = Decimal("1." + "0" * 49 + "1")
    samples = (point(2025, 3, value), point(2025, 6, value))
    band = historical_band(
        samples,
        as_of=date(2025, 6, 30),
        series_key=SERIES,
        policy=HistoryPolicy(3, 2, "high-precision-fixture"),
    )
    assert band.p25 == band.p50 == band.p75 == value
    assert (
        compare_to_history(value, band, series_key=SERIES, input_hash="current").relation
        == "within"
    )


def test_history_interpolation_preserves_tiny_differences_and_extreme_cancellation():
    for low, high, expected in (
        (
            "1." + "0" * 49 + "1",
            "1." + "0" * 49 + "5",
            tuple(Decimal("1." + "0" * 49 + digit) for digit in ("2", "3", "4")),
        ),
        ("-1e1000", "1e1000", (Decimal("-5e999"), Decimal(0), Decimal("5e999"))),
        (
            "-" + "9" * 60,
            "1e60",
            (
                Decimal("-" + "4" + "9" * 59 + ".25"),
                Decimal("0.5"),
                Decimal("5" + "0" * 59 + ".25"),
            ),
        ),
    ):
        band = historical_band(
            (point(2025, 3, low), point(2025, 6, high)),
            as_of=date(2025, 6, 30),
            series_key=SERIES,
            policy=HistoryPolicy(3, 2, "exact-interpolation-fixture"),
        )
        assert (band.p25, band.p50, band.p75) == expected
