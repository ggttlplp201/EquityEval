"""Neutral, coverage-gated observations over evaluated sector growth results."""

from equity_core.sectors import SectorMetric


def growth_observations(
    total: SectorMetric, median: SectorMetric, breadth: SectorMetric
) -> tuple[str, ...]:
    """Describe the supplied matched cohort; never infer investment merit.

    Snapshot evidence and policies must agree before combining these perspectives.
    These are labels on trusted results, not a new growth or scoring engine.
    """
    results = (total, median, breadth)
    if (
        tuple((r.metric_id, r.method) for r in results)
        != (("revenue_yoy", "total"), ("revenue_yoy", "median"), ("growth_breadth", "total"))
        or any(not r.comparison_allowed or r.value is None for r in results)
        or any(
            r.context_key != total.context_key
            or r.roster != total.roster
            or r.policy_revision != total.policy_revision
            or r.contributing_issuer_ids != total.contributing_issuer_ids
            or r.company_snapshots != total.company_snapshots
            for r in results
        )
    ):
        return ()
    assert total.value is not None and median.value is not None
    if total.value > 0 and breadth.negative_count * 2 > breadth.v:
        aggregate = "Aggregate revenue grew; most observed companies declined."
    elif total.value > 0:
        aggregate = "Aggregate revenue expanding."
    elif total.value < 0:
        aggregate = "Aggregate revenue contracting."
    else:
        aggregate = "Aggregate revenue unchanged."
    typical = (
        "Median company revenue grew."
        if median.value > 0
        else "Median company revenue declined."
        if median.value < 0
        else "Median company revenue was unchanged."
    )
    return (
        aggregate,
        typical,
        f"{breadth.positive_count} of {breadth.v} observed companies grew revenue; "
        f"{breadth.zero_count} were unchanged and {breadth.negative_count} declined.",
    )
