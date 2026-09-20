"""Hand-calculated Sector Explorer expectations; all issuer data is fictional."""

from dataclasses import replace
from datetime import date
from decimal import Decimal, Inexact, localcontext
from hashlib import sha256

import pytest
from equity_core.company import CompanyMetric, EvidenceValue
from equity_core.sectors import (
    CompanyObservation,
    CompanySnapshot,
    SectorPolicy,
    SectorRoster,
    calculate_concentration,
    calculate_sector,
    histogram,
)

D = Decimal
AS_OF = date(2026, 3, 31)
POLICY = SectorPolicy(10, D("0.70"), D("0.80"), "fixture-gates-v1")
ALL = (
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


def amount(issuer, name, value, basis="consolidated_flow", *, prior=False, instant=False):
    return EvidenceValue(
        None if value is None else D(value),
        D(0),
        sha256(f"{issuer}-{name}".encode()).hexdigest(),
        None if instant else date(2024 if prior else 2025, 1, 1),
        date(2025 if prior else 2026, 3, 31) if instant else date(2024 if prior else 2025, 12, 31),
        value is not None,
        (),
        "USD",
        basis,
    )


def company(
    issuer, earnings="10", *, cap="100", pe="10", revenue="100", prior_revenue="100", growth="0"
):
    cap_input = amount(issuer, "cap", cap, "common_equity", instant=True)
    income = amount(issuer, "income", earnings, "income_available_common")
    rev = amount(issuer, "revenue", revenue)
    prior = amount(issuer, "prior-revenue", prior_revenue, prior=True)
    return CompanySnapshot(
        issuer,
        f"snapshot-{issuer}",
        "fixture-context",
        ALL,
        cap_input,
        amount(issuer, "prior-cap", cap, "common_equity", prior=True, instant=True),
        income,
        rev,
        prior,
        amount(issuer, "op-income", "20"),
        amount(issuer, "fcf", "10", "cash_ppe_fcf"),
        (
            CompanyMetric(
                "pe",
                None if pe is None else D(pe),
                sha256(f"pe-{issuer}".encode()).hexdigest(),
                (cap_input.input_hash, income.input_hash),
                pe is not None,
            ),
            CompanyMetric(
                "revenue_yoy",
                None if growth is None else D(growth),
                sha256(f"growth-{issuer}".encode()).hexdigest(),
                (rev.input_hash, prior.input_hash),
                growth is not None,
            ),
        ),
    )


def roster(companies, *, complete=True):
    return SectorRoster(
        tuple(c.issuer_id for c in companies),
        "fixture-context",
        complete,
        AS_OF,
        "fixture-roster-hash",
        ("fixture-only-roster",),
        date(2025, 3, 31),
    )


def evaluate(companies, metric="pe", method="total", *, selected_roster=None, policy=POLICY):
    return calculate_sector(
        selected_roster or roster(companies),
        tuple(companies),
        metric=metric,
        method=method,
        policy=policy,
    )


def test_source_three_company_case_keeps_losses_and_distinguishes_methods():
    firms = (company("a"), company("b", "1", pe="100"), company("c", "-9", pe=None))
    total = evaluate(firms)
    assert (total.value, total.numerator_total, total.denominator_total) == (D(150), D(300), D(2))
    assert (total.n, total.k, total.v) == (3, 3, 3)
    assert total.issuer_coverage == total.cap_coverage == D(1)
    assert total.meaningful_company_count == 2
    assert total.p25 == D("32.5") and total.p50 == D(55) and total.p75 == D("77.5")
    assert not total.comparison_allowed and "small_sample" in total.flags
    for method in ("median", "mean"):
        typical = evaluate(firms, method=method)
        assert typical.value == D(55)
        assert (typical.n, typical.k, typical.v) == (3, 3, 2)
        assert typical.ratio_eligibility == D("0." + "6" * 49 + "7")
    breadth = evaluate(firms, "profit_breadth")
    assert breadth.value == D("0." + "6" * 49 + "7")
    assert (breadth.positive_count, breadth.zero_count, breadth.negative_count) == (2, 0, 1)


def test_zero_aggregate_earnings_is_not_zero_pe():
    firms = (company("a"), company("b", "1", pe="100"), company("c", "-11", pe=None))
    result = evaluate(firms)
    assert result.value is None and result.denominator_total == 0
    assert (result.n, result.k, result.v) == (3, 3, 3)
    assert "denominator_nonpositive" in result.flags


def test_missing_earnings_removes_same_issuer_from_both_sums():
    firms = (company("a"), company("b", "1", pe="100"), company("c", None, pe=None))
    result = evaluate(firms)
    assert result.numerator_total == D(200) and result.denominator_total == D(11)
    assert result.contributing_issuer_ids == ("a", "b")
    assert (result.n, result.k, result.v) == (3, 2, 2)
    assert result.excluded[0].issuer_id == "c"


def with_metric(firm, metric, value, fields):
    datum = CompanyMetric(
        metric,
        None if value is None else D(value),
        sha256(f"{firm.issuer_id}-{metric}".encode()).hexdigest(),
        tuple(getattr(firm, f).input_hash for f in fields),
        value is not None,
    )
    return replace(
        firm,
        company_metrics=tuple(m for m in firm.company_metrics if m.metric_id != metric) + (datum,),
    )


def test_growth_matches_both_periods_and_does_not_call_narrow_growth_broad():
    firms = (company("leader", revenue="110", prior_revenue="100", growth=".1"),) + tuple(
        company(f"decliner-{i}", revenue="9", prior_revenue="10", growth="-.1") for i in range(9)
    )
    total = evaluate(firms, "revenue_yoy")
    assert total.numerator_total == 191 and total.denominator_total == 190
    assert total.value.quantize(D(".000001")) == D(".005263")
    assert evaluate(firms, "revenue_yoy", "median").value == D("-.1")
    breadth = evaluate(firms, "growth_breadth")
    assert breadth.value == D(".1")
    assert (breadth.positive_count, breadth.zero_count, breadth.negative_count) == (1, 0, 9)
    assert breadth.comparison_allowed


def test_growth_zero_prior_base_is_complete_but_not_contributing():
    firms = (
        company("valid", revenue="110", prior_revenue="100", growth=".1"),
        company("zero-base", revenue="10", prior_revenue="0", growth=None),
    )
    for metric in ("revenue_yoy", "growth_breadth"):
        result = evaluate(firms, metric)
        assert (result.n, result.k, result.v) == (2, 2, 1)
        assert result.contributing_issuer_ids == ("valid",)
        assert "company_denominator_nonpositive" in result.excluded[0].reasons


def test_other_multiples_and_margins_preserve_negative_cash_and_operating_losses():
    a = company("a")
    b = company("b", revenue="200")
    b = replace(
        b,
        fcf=replace(b.fcf, value=D(-5)),
        operating_income=replace(b.operating_income, value=D(-20)),
    )
    for metric, fields, av, bv, total, median in (
        (
            "ps",
            ("market_cap", "revenue"),
            "1",
            ".5",
            "0.66666666666666666666666666666666666666666666666667",
            ".75",
        ),
        ("pfcf", ("market_cap", "fcf"), "10", None, "40", "10"),
        ("operating_margin", ("operating_income", "revenue"), ".2", "-.1", "0", ".05"),
        (
            "fcf_margin",
            ("fcf", "revenue"),
            ".1",
            "-.025",
            "0.016666666666666666666666666666666666666666666666667",
            ".0375",
        ),
    ):
        firms = (with_metric(a, metric, av, fields), with_metric(b, metric, bv, fields))
        assert evaluate(firms, metric).value == D(total)
        assert evaluate(firms, metric, "median").value == D(median)
    breadth = evaluate((a, b), "cash_breadth")
    assert breadth.value == D(".5")
    assert (breadth.positive_count, breadth.zero_count, breadth.negative_count) == (1, 0, 1)


def test_amount_zero_is_not_a_loss_or_missing_for_breadth():
    zero = company("zero", "0", pe=None)
    missing = company("missing", None, pe=None)
    result = evaluate((company("profit"), zero, missing), "profit_breadth")
    assert (result.n, result.k, result.v) == (3, 2, 2)
    assert result.value == D(".5")
    assert (result.positive_count, result.zero_count, result.negative_count) == (1, 1, 0)


@pytest.mark.parametrize("method", ["total", "median", "mean"])
def test_explicit_coverage_gate_boundaries_and_unknown_full_cap(method):
    firms = tuple(company(f"known-{i}", "2", cap="20") for i in range(14)) + tuple(
        company(f"missing-{i}", None, cap="20" if i == 5 else "10", pe=None) for i in range(6)
    )
    result = evaluate(firms, method=method)
    assert (result.n, result.k, result.v) == (20, 14, 14)
    assert result.issuer_coverage == D(".70") and result.cap_coverage == D(".80")
    assert result.comparison_allowed
    for policy in (
        replace(POLICY, minimum_contributors=15),
        replace(POLICY, minimum_issuer_coverage=D(".70001")),
        replace(POLICY, minimum_cap_coverage=D(".80001")),
    ):
        limited = evaluate(firms, method=method, policy=policy)
        assert limited.value == 10 and not limited.comparison_allowed
    absent_cap = firms[:-1] + (
        replace(firms[-1], market_cap=replace(firms[-1].market_cap, value=None, usable=False)),
    )
    unknown = evaluate(absent_cap, method=method)
    assert unknown.value == 10 and unknown.cap_coverage is None
    assert unknown.full_market_cap is None and not unknown.comparison_allowed
    partial = evaluate(firms, method=method, selected_roster=roster(firms, complete=False))
    assert partial.value == 10 and "partial_sector_universe" in partial.flags
    assert not partial.comparison_allowed


def test_exact_duplicate_listing_deduplicates_and_conflict_never_selects_first():
    a, b = company("a"), company("b")
    duplicate = evaluate((a, b, a))
    assert (duplicate.n, duplicate.k, duplicate.v) == (2, 2, 2)
    assert duplicate.numerator_total == 200
    conflict = replace(a, snapshot_id="different-immutable-snapshot")
    first = evaluate((a, b, conflict))
    reversed_input = evaluate((conflict, b, a))
    assert first.value == reversed_input.value == 10
    assert (first.n, first.k, first.v) == (2, 1, 1)
    assert first.cap_coverage is None
    assert first.excluded[0].reasons == ("conflicting_issuer_snapshots",)
    assert first.cohort_id == reversed_input.cohort_id


def test_missing_company_snapshot_remains_in_roster_and_fullcap_denominator():
    a, b = company("a"), company("b")
    result = evaluate((a,), selected_roster=roster((a, b)))
    assert (result.n, result.k, result.v) == (2, 1, 1)
    assert result.cap_coverage is None
    assert result.excluded[0].reasons == ("company_snapshot_missing",)


@pytest.mark.parametrize(
    "change",
    [
        {"usable": False, "flags": ("stale",)},
        {"currency": "EUR"},
        {"basis": "consolidated_flow"},
        {"period_end": date(2026, 12, 31)},
        {"absolute_error": None},
    ],
)
def test_incompatible_income_evidence_stays_excluded_and_known_roster_stays(change):
    a, b = company("a"), company("b")
    b = replace(b, common_income=replace(b.common_income, **change))
    result = evaluate((a, b))
    assert (result.n, result.k, result.v) == (2, 1, 1)
    assert result.numerator_total == 100 and result.denominator_total == 10
    assert result.cap_coverage == D(".5")
    assert result.excluded[0].reasons


def test_unsupported_profile_and_informational_flags_are_distinct():
    a, b = company("a"), company("b")
    a = replace(a, common_income=replace(a.common_income, flags=("revised_view",)))
    b = replace(b, applicable_metrics=("profit_breadth",))
    result = evaluate((a, b))
    assert (result.n, result.k, result.v) == (2, 1, 1)
    assert result.value == 10 and result.cap_coverage == D(".5")
    assert "revised_view" in result.flags
    assert result.excluded[0].reasons == ("unsupported_profile",)


def test_company_ratio_must_match_ordered_operands_and_be_finite():
    a = company("a")
    pe = a.company_metrics[0]
    for bad in (
        replace(pe, operand_hashes=tuple(reversed(pe.operand_hashes))),
        replace(pe, value=D("NaN")),
        replace(pe, value=D("Infinity")),
    ):
        result = evaluate((replace(a, company_metrics=(bad,)),), method="median")
        assert result.k == 1 and result.v == 0 and result.value is None
        assert result.distribution == ()


def test_incompatible_within_company_flow_periods_are_not_aggregated():
    a = company("a")
    a = replace(
        a,
        operating_income=replace(
            a.operating_income, period_start=date(2024, 1, 1), period_end=date(2024, 12, 31)
        ),
    )
    a = with_metric(a, "operating_margin", ".2", ("operating_income", "revenue"))
    result = evaluate((a,), "operating_margin")
    assert result.k == 0 and result.value is None
    assert "incompatible_periods" in result.excluded[0].reasons


def test_nonpositive_cap_cannot_be_used_in_aggregate_multiple():
    result = evaluate((company("a", cap="-100", pe=None),))
    assert result.k == 0 and result.v == 0 and result.value is None


def test_nearzero_aggregate_keeps_totals_but_does_not_emit_multiple():
    a = company("a", "10")
    b = company("b", "-9.9", pe=None)
    a = replace(a, common_income=replace(a.common_income, absolute_error=D(".1")))
    b = replace(b, common_income=replace(b.common_income, absolute_error=D(".1")))
    result = evaluate((a, b))
    assert result.numerator_total == 200 and result.denominator_total == D(".1")
    assert result.value is None and "denominator_indistinguishable_from_zero" in result.flags


def test_empty_roster_has_no_fabricated_coverage():
    result = evaluate(())
    assert result.value is result.issuer_coverage is result.cap_coverage is None
    assert (result.n, result.k, result.v) == (0, 0, 0)


def concentration_firms():
    firms = []
    for i, cap in enumerate(("1", "2", "3", "4", "5", "100")):
        firm = company(
            chr(97 + i),
            cap=cap,
            revenue="20" if i == 5 else "100",
            prior_revenue="10" if i == 5 else "100",
            growth="1" if i == 5 else "0",
        )
        firm = replace(firm, prior_market_cap=replace(firm.prior_market_cap, value=D(100 - i * 10)))
        firms.append(firm)
    return tuple(firms)


def test_concentration_uses_current_caps_but_growth_exclusion_freezes_prior_leaders():
    firms = concentration_firms()
    result = calculate_concentration(roster(firms), firms, policy=POLICY)
    assert result.current_top_five == ("f", "e", "d", "c", "b")
    assert result.current_share.quantize(D(".000001")) == D(".991304")
    assert result.prior_top_five == ("a", "b", "c", "d", "e")
    assert result.growth_without_top_five.value == 1
    assert result.growth_without_top_five.contributing_issuer_ids == ("f",)
    assert result.growth_without_top_five.numerator_total == 20
    assert result.growth_without_top_five.denominator_total == 10
    assert result.current_date == AS_OF and result.prior_date == date(2025, 3, 31)


def test_top_five_requires_all_roster_caps_at_the_relevant_date():
    firms = concentration_firms()
    absent_prior = firms[:-1] + (
        replace(
            firms[-1],
            prior_market_cap=replace(firms[-1].prior_market_cap, value=None, usable=False),
        ),
    )
    result = calculate_concentration(roster(firms), absent_prior, policy=POLICY)
    assert result.current_share is not None
    assert result.prior_top_five is None and result.growth_without_top_five is None
    for changed_roster in (
        replace(roster(firms), prior_evaluation_date=None),
        roster(firms, complete=False),
    ):
        unavailable = calculate_concentration(changed_roster, firms, policy=POLICY)
        assert unavailable.prior_top_five is None and unavailable.growth_without_top_five is None
    future = replace(
        firms[-1], prior_market_cap=replace(firms[-1].prior_market_cap, period_end=AS_OF)
    )
    result = calculate_concentration(roster(firms), firms[:-1] + (future,), policy=POLICY)
    assert result.prior_top_five is None


def test_top_five_ties_are_deterministic_and_empty_remaining_cohort_is_not_zero():
    firms = tuple(company(i) for i in ("z", "b", "a"))
    result = calculate_concentration(roster(firms), firms, policy=POLICY)
    assert result.current_top_five == result.prior_top_five == ("a", "b", "z")
    assert result.current_share == 1
    assert result.growth_without_top_five.value is None
    assert result.growth_without_top_five.v == 0


def point(issuer, value):
    return CompanyObservation(
        issuer, f"snapshot-{issuer}", D(value), sha256(issuer.encode()).hexdigest()
    )


def test_histogram_preserves_every_point_boundaries_and_outliers():
    points = (point("a", "0"), point("b", "1"), point("c", "2"), point("d", "100"))
    bins = histogram(points, bin_count=4)
    assert len(bins) == 4
    assert [(b.lower, b.upper, b.count) for b in bins] == [
        (D(0), D(25), 3),
        (D(25), D(50), 0),
        (D(50), D(75), 0),
        (D(75), D(100), 1),
    ]
    assert bins[-1].issuer_ids == ("d",) and bins[-1].upper_inclusive
    assert not bins[0].upper_inclusive
    exact_edges = histogram((point("a", "0"), point("b", "25"), point("c", "100")), bin_count=4)
    assert exact_edges[0].issuer_ids == ("a",) and exact_edges[1].issuer_ids == ("b",)
    assert sorted(i for b in exact_edges for i in b.issuer_ids) == ["a", "b", "c"]


def test_histogram_singleton_empty_and_unrounded_high_precision():
    assert histogram(()) == ()
    value = "1." + "0" * 49 + "1"
    bins = histogram((point("a", value), point("b", value)))
    assert len(bins) == 1 and bins[0].lower == bins[0].upper == D(value)
    assert bins[0].count == 2 and bins[0].upper_inclusive
    for bad in (D("NaN"), D("Infinity"), D("1e1001")):
        with pytest.raises(ValueError):
            histogram((point("a", bad),))


def test_numeric_results_ignore_ambient_decimal_context():
    firms = (company("a"), company("b", "1", pe="100"), company("c", "-9", pe=None))
    expected = evaluate(firms)
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.traps[Inexact] = True
        actual = evaluate(firms)
        assert actual.value == expected.value and actual.p25 == expected.p25
        assert evaluate(firms, "profit_breadth").value == D("0." + "6" * 49 + "7")
        assert histogram((point("a", "0"), point("b", "1")), bin_count=3)[-1].upper == 1


def test_median_has_no_aggregate_sum_division_tooltip_and_mean_has_its_own_totals():
    firms = (company("a", "100", pe="1"), company("b", "50", pe="2"), company("c", "1", pe="100"))
    median = evaluate(firms, method="median")
    mean = evaluate(firms, method="mean")
    assert median.value == 2
    assert median.numerator_total is None and median.denominator_total is None
    assert mean.numerator_total == 103 and mean.denominator_total == 3


def test_mean_and_median_refuse_individual_denominator_indistinguishable_from_zero():
    firm = company("a", "0.1", pe="1000")
    firm = replace(firm, common_income=replace(firm.common_income, absolute_error=D(".1")))
    for method in ("mean", "median"):
        result = evaluate((firm,), method=method)
        assert result.k == 1 and result.v == 0 and result.value is None
        assert "company_denominator_indistinguishable_from_zero" in result.excluded[0].reasons


def test_market_reference_uses_issuers_instead_of_average_of_sector_bars():
    firms = (company("a"), company("b", "1", pe="100"), company("unclassified", "1", pe="100"))
    market = evaluate(firms)
    assert market.value == 25
    assert market.numerator_total == 300 and market.denominator_total == 12
    assert "unclassified" in market.contributing_issuer_ids


def test_sign_counts_name_their_basis_and_separate_zero_denominators():
    a = company("loss")
    a = replace(a, operating_income=replace(a.operating_income, value=D(-20)))
    a = with_metric(a, "operating_margin", "-.2", ("operating_income", "revenue"))
    b = company("zero-revenue", revenue="0")
    b = replace(b, operating_income=replace(b.operating_income, value=D(0)))
    result = evaluate((a, b), "operating_margin")
    assert result.sign_basis == "operating_income"
    assert (result.positive_count, result.zero_count, result.negative_count) == (0, 1, 1)
    assert result.zero_denominator_count == 1
    assert evaluate((a,), "pe").sign_basis == "common_income"


def test_company_metric_requires_evidence_hash_and_exact_input_identity():
    firm = company("a")
    invalid = replace(firm.company_metrics[0], input_hash="merely-nonempty")
    result = evaluate((replace(firm, company_metrics=(invalid,)),), method="median")
    assert result.value is None and result.v == 0


@pytest.mark.parametrize("delta", [1, -1])
def test_aggregate_growth_retains_small_exact_change_beside_large_unchanged_issuer(delta):
    firms = (
        company(
            "changed",
            revenue=str(10**40 + delta),
            prior_revenue=str(10**40),
            growth="1e-40" if delta > 0 else "-1e-40",
        ),
        company("large", revenue="1e100", prior_revenue="1e100", growth="0"),
    )
    expected = D("1e-100") if delta > 0 else D("-1e-100")
    ordinary = evaluate(firms, "revenue_yoy")
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.traps[Inexact] = True
        hostile = evaluate(firms, "revenue_yoy")
    assert ordinary.value == hostile.value == expected
    assert ordinary.numerator_total == D(str(10**100 + 10**40 + delta))
    assert ordinary.denominator_total == D(str(10**100 + 10**40))
