"""Neutral sector observations require common cohorts and passing coverage gates."""

from dataclasses import replace
from decimal import Decimal

from equity_core.sector_insights import growth_observations
from equity_core.sectors import SectorPolicy, calculate_sector

from tests.core.test_sectors import company, roster


def results():
    companies = tuple(
        company(
            str(i),
            revenue="110" if i == 0 else "9",
            prior_revenue="100" if i == 0 else "10",
            growth=".1" if i == 0 else "-.1",
        )
        for i in range(10)
    )
    policy = SectorPolicy(10, Decimal(".7"), Decimal(".8"), "insights-test")
    declared = roster(companies)
    return tuple(
        calculate_sector(declared, companies, metric=metric, method=method, policy=policy)
        for metric, method in (
            ("revenue_yoy", "total"),
            ("revenue_yoy", "median"),
            ("growth_breadth", "total"),
        )
    )


def test_growth_observation_distinguishes_aggregate_from_most_companies():
    total, median, breadth = results()
    observations = growth_observations(total, median, breadth)
    assert "Aggregate revenue grew; most observed companies declined." in observations
    assert (
        "1 of 10 observed companies grew revenue; 0 were unchanged and 9 declined." in observations
    )
    assert not any("broad-based" in text or "buy" in text for text in observations)


def test_low_coverage_or_mismatched_snapshots_suppress_financial_labels():
    total, median, breadth = results()
    assert growth_observations(replace(total, comparison_allowed=False), median, breadth) == ()
    assert growth_observations(total, replace(median, context_key="different"), breadth) == ()
    assert (
        growth_observations(total, median, replace(breadth, contributing_issuer_ids=("other",)))
        == ()
    )


def test_unchanged_companies_are_never_called_declining():
    total, median, breadth = results()
    mixed = replace(breadth, positive_count=1, zero_count=9, negative_count=0)
    observations = growth_observations(total, median, mixed)
    assert not any("most observed companies declined" in text for text in observations)
    assert "Aggregate revenue expanding." in observations
