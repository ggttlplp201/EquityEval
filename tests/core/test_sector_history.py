"""Synthetic membership and history cannot borrow future classifications."""

from datetime import UTC, date, datetime

from equity_core.sector_history import MembershipAssignment, select_membership


def test_membership_selection_uses_both_effective_and_known_dates():
    old = MembershipAssignment(
        "issuer-a",
        "energy",
        "oil",
        date(2020, 1, 1),
        None,
        datetime(2020, 1, 2, tzinfo=UTC),
        ("synthetic:old",),
    )
    future = MembershipAssignment(
        "issuer-a",
        "technology",
        "software",
        date(2025, 1, 1),
        None,
        datetime(2025, 8, 1, tzinfo=UTC),
        ("synthetic:later",),
    )
    result = select_membership(
        ("issuer-a", "issuer-b"),
        (old, future),
        as_of=date(2025, 6, 30),
        known_before=datetime(2025, 7, 1, tzinfo=UTC),
    )
    assert result[0].sector_id == "energy"
    assert result[0].evidence == (old,)
    assert result[1].sector_id is None
    assert result[1].flags == ("classification_unavailable",)


def test_membership_conflicts_and_date_boundaries_are_explicit():
    from dataclasses import replace

    old = MembershipAssignment(
        "a",
        "energy",
        "oil",
        date(2020, 1, 1),
        date(2025, 7, 1),
        datetime(2020, 1, 1, tzinfo=UTC),
        ("synthetic:old",),
    )
    new = replace(
        old,
        sector_id="technology",
        industry_id="software",
        effective_from=date(2025, 7, 1),
        effective_to=None,
        known_at=datetime(2025, 7, 1, tzinfo=UTC),
    )
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    before = select_membership(
        ("a", "a"), (old, new, old), as_of=date(2025, 6, 30), known_before=cutoff
    )
    assert len(before) == 1 and before[0].sector_id == "energy"
    after = select_membership(("a",), (old, new), as_of=date(2025, 7, 1), known_before=cutoff)
    assert after[0].sector_id == "technology"
    conflict = select_membership(
        ("a",),
        (old, replace(new, effective_from=date(2025, 6, 1), known_at=old.known_at)),
        as_of=date(2025, 6, 30),
        known_before=cutoff,
    )
    assert conflict[0].sector_id is None and conflict[0].flags == ("classification_conflict",)
    assert before[0].sector_id == "energy"  # A later selection cannot mutate it.


def test_membership_rejects_missing_source_and_unpinned_knowledge_time():
    from dataclasses import replace

    import pytest

    assignment = MembershipAssignment(
        "a",
        "energy",
        None,
        date(2020, 1, 1),
        None,
        datetime(2020, 1, 1, tzinfo=UTC),
        ("synthetic:source",),
    )
    for changes in (
        {"source_refs": ()},
        {"known_at": datetime(2020, 1, 1)},
        {"effective_to": date(2019, 1, 1)},
        {"issuer_id": ""},
    ):
        with pytest.raises(ValueError):
            replace(assignment, **changes)
    with pytest.raises(ValueError):
        select_membership(
            ("a",), (assignment,), as_of=date(2025, 1, 1), known_before=datetime(2025, 1, 1)
        )


def test_sector_history_requires_twelve_eligible_points_and_preserves_gaps():
    from decimal import Decimal

    from equity_core.sector_history import SectorHistoryPoint, sector_history

    dates = tuple(
        date(y, m, d)
        for y in range(2023, 2027)
        for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))
        if date(2023, 6, 30) < date(y, m, d) <= date(2026, 6, 30)
    )
    points = tuple(
        SectorHistoryPoint(
            day, Decimal(i + 1), "pe-total-v1", str(i).zfill(64), "a" * 64, "historical", True
        )
        for i, day in enumerate(dates)
    )
    result = sector_history(
        points,
        as_of=date(2026, 6, 30),
        series_key="pe-total-v1",
        years=3,
        membership_mode="historical",
        policy_revision="test-v1",
    )
    assert result.band.p25 == Decimal("3.75")
    assert result.band.p50 == Decimal("6.5")
    assert result.band.p75 == Decimal("9.25")
    assert len(result.points) == 12
    missing = sector_history(
        points[:5] + points[6:],
        as_of=date(2026, 6, 30),
        series_key="pe-total-v1",
        years=3,
        membership_mode="historical",
        policy_revision="test-v1",
    )
    assert missing.band.p25 is None
    assert len(missing.points) == 12 and missing.points[5].value is None
    assert "missing_observation" in missing.points[5].flags
    assert result.snapshot_id != missing.snapshot_id
    assert result.points[5].value == Decimal(6)


def test_current_members_plot_has_no_historical_sector_percentiles():
    from dataclasses import replace
    from decimal import Decimal

    from equity_core.sector_history import SectorHistoryPoint, sector_history

    dates = tuple(
        date(y, m, d)
        for y in range(2023, 2027)
        for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))
        if date(2023, 6, 30) < date(y, m, d) <= date(2026, 6, 30)
    )
    points = tuple(
        SectorHistoryPoint(
            day, Decimal(i), "pe-total-v1", str(i).zfill(64), "a" * 64, "current_members", True
        )
        for i, day in enumerate(dates)
    )
    kwargs = dict(
        as_of=date(2026, 6, 30), series_key="pe-total-v1", years=1, policy_revision="test-v1"
    )
    current = sector_history(points, membership_mode="current_members", **kwargs)
    assert len(current.points) == 4 and all(p.value is not None for p in current.points)
    assert current.band.p25 is None and "current_members_history" in current.band.flags
    historical = sector_history(points, membership_mode="historical", **kwargs)
    assert all(p.value is None for p in historical.points)
    assert all("membership_mode_mismatch" in p.flags for p in historical.points)
    eligible = tuple(replace(p, membership_mode="historical") for p in points)
    bad = eligible[:-1] + (replace(eligible[-1], comparison_allowed=False),)
    failed = sector_history(bad, membership_mode="historical", **kwargs)
    assert failed.points[-1].value is None
    assert "coverage_gate_failed" in failed.points[-1].flags
    assert failed.band.p25 is None


def test_history_conflicting_membership_is_gap_and_revision_changes_snapshot():
    from dataclasses import replace
    from decimal import Decimal

    from equity_core.sector_history import SectorHistoryPoint, sector_history

    point = SectorHistoryPoint(
        date(2026, 6, 30), Decimal(20), "pe-total-v1", "1" * 64, "a" * 64, "historical", True
    )
    kwargs = dict(
        as_of=date(2026, 6, 30),
        series_key="pe-total-v1",
        years=1,
        membership_mode="historical",
        policy_revision="test-v1",
    )
    one = sector_history((point, point), **kwargs)
    assert one.points[-1].value == Decimal(20)
    revised = replace(point, membership_hash="b" * 64)
    conflict = sector_history((point, revised), **kwargs)
    assert conflict.points[-1].value is None
    assert "conflicting_quarter" in conflict.points[-1].flags
    changed = sector_history((revised,), **kwargs)
    assert changed.snapshot_id != one.snapshot_id
    assert one.source_points[0].membership_hash == "a" * 64
    incompatible = sector_history((replace(point, series_key="pe-median-v1"),), **kwargs)
    assert incompatible.points[-1].value is None
