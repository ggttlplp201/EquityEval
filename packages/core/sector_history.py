"""Pure dated membership and sector-history projections, without source discovery."""

from calendar import monthrange
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from hashlib import sha256
from typing import Literal

from equity_core.history import HistoryBand, HistoryPoint, HistoryPolicy, historical_band


def _aware(value: datetime) -> bool:
    return (
        isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None
    )


@dataclass(frozen=True)
class MembershipAssignment:
    issuer_id: str
    sector_id: str | None
    industry_id: str | None
    effective_from: date
    effective_to: date | None
    known_at: datetime
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.issuer_id, str)
            or not self.issuer_id.strip()
            or any(
                item is not None and (not isinstance(item, str) or not item.strip())
                for item in (self.sector_id, self.industry_id)
            )
            or (self.industry_id is not None and self.sector_id is None)
            or type(self.effective_from) is not date
            or (
                self.effective_to is not None
                and (
                    type(self.effective_to) is not date or self.effective_to <= self.effective_from
                )
            )
            or not _aware(self.known_at)
            or not isinstance(self.source_refs, tuple)
            or not self.source_refs
            or any(not isinstance(item, str) or not item.strip() for item in self.source_refs)
        ):
            raise ValueError("Membership requires dated, immutable classification evidence")


@dataclass(frozen=True)
class SelectedMembership:
    issuer_id: str
    sector_id: str | None
    industry_id: str | None
    evidence: tuple[MembershipAssignment, ...]
    flags: tuple[str, ...] = ()


def select_membership(
    issuer_ids: tuple[str, ...],
    assignments: tuple[MembershipAssignment, ...],
    *,
    as_of: date,
    known_before: datetime,
) -> tuple[SelectedMembership, ...]:
    """Inclusive UTC calendar date; known-before cannot widen historical knowledge."""
    if (
        not isinstance(issuer_ids, tuple)
        or any(not isinstance(item, str) or not item.strip() for item in issuer_ids)
        or not isinstance(assignments, tuple)
        or any(not isinstance(item, MembershipAssignment) for item in assignments)
        or type(as_of) is not date
        or not _aware(known_before)
    ):
        raise ValueError("Membership selection requires immutable evidence and an aware cutoff")
    cutoff = min(known_before, datetime.combine(as_of, time.max, tzinfo=UTC))
    result = []
    for issuer in sorted(set(issuer_ids)):
        evidence = tuple(
            dict.fromkeys(
                item
                for item in assignments
                if item.issuer_id == issuer
                and item.effective_from <= as_of
                and (item.effective_to is None or as_of < item.effective_to)
                and item.known_at <= cutoff
            )
        )
        classifications = {(item.sector_id, item.industry_id) for item in evidence}
        if not classifications:
            result.append(
                SelectedMembership(issuer, None, None, (), ("classification_unavailable",))
            )
        elif len(classifications) != 1:
            result.append(
                SelectedMembership(issuer, None, None, evidence, ("classification_conflict",))
            )
        else:
            sector, industry = next(iter(classifications))
            result.append(
                SelectedMembership(
                    issuer,
                    sector,
                    industry,
                    evidence,
                    () if sector else ("classification_unavailable",),
                )
            )
    return tuple(result)


@dataclass(frozen=True)
class SectorHistoryPoint:
    """An evaluated quarter and its pinned membership/source evidence.

    ``series_key`` includes universe/taxonomy, sector level, metric/method,
    currency, accounting mode, applicability, freshness and coverage policies.
    Actual membership may change between historical observations.
    """

    quarter_end: date
    value: Decimal | None
    series_key: str
    input_hash: str
    membership_hash: str
    membership_mode: Literal["historical", "current_members"]
    comparison_allowed: bool
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.quarter_end) is not date
            or not isinstance(self.series_key, str)
            or not self.series_key.strip()
            or any(
                not isinstance(value, str)
                or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value)
                for value in (self.input_hash, self.membership_hash)
            )
            or self.membership_mode not in ("historical", "current_members")
            or type(self.comparison_allowed) is not bool
            or not isinstance(self.flags, tuple)
            or any(not isinstance(flag, str) or not flag.strip() for flag in self.flags)
        ):
            raise ValueError("Sector history requires a pinned evaluated observation")


@dataclass(frozen=True)
class SectorHistorySeries:
    points: tuple[HistoryPoint, ...]
    band: HistoryBand
    membership_mode: str
    years: int
    snapshot_id: str
    source_points: tuple[SectorHistoryPoint, ...]


def sector_history(
    points: tuple[SectorHistoryPoint, ...],
    *,
    as_of: date,
    series_key: str,
    years: int,
    membership_mode: Literal["historical", "current_members"],
    policy_revision: str,
) -> SectorHistorySeries:
    """Graph gaps and a separately gated three-year, twelve-quarter history band.

    This pure projection does not establish durable storage or verify a provider's
    membership/filing archive. Its caller must freeze those evaluated inputs first.
    """
    if (
        not isinstance(points, tuple)
        or any(not isinstance(p, SectorHistoryPoint) for p in points)
        or type(years) is not int
        or years not in (1, 3, 5)
        or membership_mode not in ("historical", "current_members")
        or type(as_of) is not date
        or as_of.year <= max(3, years)
    ):
        raise ValueError("Sector graph history requires an explicit 1/3/5-year window and mode")
    projected = []
    for point in points:
        flags = list(point.flags)
        if not point.comparison_allowed:
            flags.append("coverage_gate_failed")
        if point.membership_mode != membership_mode:
            flags.append("membership_mode_mismatch")
        # Pin both financial and membership evidence in sample identity. Conflicting
        # memberships for a quarter must not collapse into an apparent duplicate.
        identity = sha256((point.input_hash + point.membership_hash).encode()).hexdigest()
        projected.append(
            HistoryPoint(
                point.quarter_end,
                point.value,
                point.series_key,
                identity,
                tuple(sorted(set(flags))),
            )
        )
    samples = tuple(projected)
    selection = historical_band(
        samples,
        as_of=as_of,
        series_key=series_key,
        policy=HistoryPolicy(max(3, years), 1, policy_revision),
    )
    band = historical_band(
        samples, as_of=as_of, series_key=series_key, policy=HistoryPolicy(3, 12, policy_revision)
    )
    if membership_mode == "current_members":
        band = replace(
            band,
            p25=None,
            p50=None,
            p75=None,
            flags=tuple(sorted(set(band.flags + ("current_members_history",)))),
        )
    start = as_of.replace(
        year=as_of.year - years, day=min(as_of.day, monthrange(as_of.year - years, as_of.month)[1])
    )
    eligible = {point.quarter_end: point for point in selection.eligible}
    displayed = []
    for day in selection.expected_quarter_ends:
        if day <= start:
            continue
        if day in eligible:
            displayed.append(eligible[day])
        else:
            excluded = tuple(
                item
                for item in selection.excluded
                if item.point.quarter_end == day and item.point.series_key == series_key
            )
            gap_flags = tuple(sorted({reason for item in excluded for reason in item.reasons}))
            hashes = sorted(item.point.input_hash for item in excluded)
            displayed.append(
                HistoryPoint(
                    day,
                    None,
                    series_key,
                    sha256(repr(hashes).encode()).hexdigest(),
                    gap_flags or ("missing_observation",),
                )
            )
    canonical = tuple(
        sorted(
            (
                p.quarter_end.isoformat(),
                repr(p.value),
                p.series_key,
                p.input_hash,
                p.membership_hash,
                p.membership_mode,
                p.comparison_allowed,
                p.flags,
            )
            for p in points
        )
    )
    snapshot_id = sha256(
        repr((as_of, series_key, years, membership_mode, policy_revision, canonical)).encode()
    ).hexdigest()
    return SectorHistorySeries(tuple(displayed), band, membership_mode, years, snapshot_id, points)
