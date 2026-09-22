"""Explicit reviewed fiscal boundaries, never inferred from a flow's day count."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from equity_core.inputs import FinancialInput


@dataclass(frozen=True)
class FiscalYear:
    label: str
    start: date
    quarter_ends: tuple[date, ...]
    kind: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.label, str)
            or not self.label.strip()
            or type(self.start) is not date
            or self.start == date.min
            or not isinstance(self.quarter_ends, tuple)
            or len(self.quarter_ends) != 4
            or any(type(end) is not date or end == date.max for end in self.quarter_ends)
            or tuple(sorted(set(self.quarter_ends))) != self.quarter_ends
            or self.start > self.quarter_ends[0]
            or self.kind not in {"months", "weeks", "transition"}
        ):
            raise ValueError("Fiscal year requires four ordered, explicitly reviewed boundaries")

    @property
    def supported(self) -> bool:
        starts = (self.start, *(end + timedelta(days=1) for end in self.quarter_ends[:-1]))
        if self.kind == "weeks":
            days = tuple(
                (end - start).days + 1 for start, end in zip(starts, self.quarter_ends, strict=True)
            )
            return all(count in {91, 98} for count in days) and sum(days) in {364, 371}
        if self.kind == "months":
            return all(
                start.day == 1
                and end.day == calendar.monthrange(end.year, end.month)[1]
                and (end.year - start.year) * 12 + end.month - start.month + 1 == 3
                for start, end in zip(starts, self.quarter_ends, strict=True)
            )
        return False


@dataclass(frozen=True)
class FiscalCalendarEvidence:
    """Internal caller-reviewed calendar proof for exactly these selected inputs.

    Calendar facts have their own availability/capture dates; they cannot arrive
    after the input selection's PIT cutoff. This is not a source/calendar loader.
    """

    issuer_id: UUID
    years: tuple[FiscalYear, ...]
    input_hashes: tuple[str, ...]
    known_on: date
    captured_at: datetime
    evidence_refs: tuple[str, ...]
    review_revision: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.issuer_id, UUID)
            or not isinstance(self.years, tuple)
            or not self.years
            or any(not isinstance(year, FiscalYear) for year in self.years)
            or len({year.label for year in self.years}) != len(self.years)
            or any(
                left.quarter_ends[-1] >= right.start
                for left, right in zip(self.years, self.years[1:], strict=False)
            )
            or not isinstance(self.input_hashes, tuple)
            or not self.input_hashes
            or len(set(self.input_hashes)) != len(self.input_hashes)
            or any(
                not isinstance(item, str) or re.fullmatch(r"[0-9a-f]{64}", item) is None
                for item in self.input_hashes
            )
            or type(self.known_on) is not date
            or not isinstance(self.captured_at, datetime)
            or self.captured_at.utcoffset() is None
            or self.known_on > self.captured_at.date()
            or not isinstance(self.evidence_refs, tuple)
            or not self.evidence_refs
            or any(not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs)
            or not isinstance(self.review_revision, str)
            or not self.review_revision.strip()
        ):
            raise ValueError("Fiscal calendar requires immutable source-bound review evidence")

    @property
    def comparison_key(self) -> tuple[object, ...]:
        # Selection hashes differ by concept. All calendar facts and policy must agree.
        return (
            self.issuer_id,
            self.years,
            self.known_on,
            self.captured_at,
            self.evidence_refs,
            self.review_revision,
        )

    def problems(self, sources: tuple[FinancialInput, ...]) -> set[str]:
        problems = set()
        if set(self.input_hashes) != {source.selection.input_hash for source in sources}:
            problems.add("fiscal_calendar_input_mismatch")
        if any(source.selection.query.issuer_id != self.issuer_id for source in sources):
            problems.add("fiscal_calendar_issuer_mismatch")
        if any(
            self.captured_at > source.selection.query.captured_before
            or self.known_on
            > (source.selection.query.filed_cutoff or source.selection.query.captured_before.date())
            for source in sources
        ):
            problems.add("fiscal_calendar_not_known_at_cutoff")
        if (
            any(not year.supported for year in self.years)
            or len({year.kind for year in self.years}) != 1
        ):
            problems.add("unsupported_fiscal_calendar")
        return problems

    def match(self, source: FinancialInput, *, cumulative: bool) -> tuple[int, int] | None:
        """Return reviewed year/quarter ordinals, never a day-count classification."""
        if source.period.period_kind != "duration":
            return None
        for year_index, year in enumerate(self.years):
            for quarter, end in enumerate(year.quarter_ends):
                start = (
                    year.start
                    if cumulative or quarter == 0
                    else year.quarter_ends[quarter - 1] + timedelta(days=1)
                )
                if source.period.start_date == start and source.period.end_date == end:
                    return year_index, quarter + 1
        return None

    def comparable(self, current: FinancialInput, prior: FinancialInput) -> bool:
        for cumulative in (False, True):
            c = self.match(current, cumulative=cumulative)
            p = self.match(prior, cumulative=cumulative)
            if c is None or p is None or c[0] != p[0] + 1 or c[1] != p[1]:
                continue
            if cumulative and c[1] != 4:
                continue  # YTD is not standalone quarter/year growth.
            old_year, new_year = self.years[p[0]], self.years[c[0]]
            if old_year.quarter_ends[-1].toordinal() + 1 != new_year.start.toordinal():
                continue
            if old_year.kind != new_year.kind:
                continue
            if new_year.kind == "weeks" and (
                current.period.start_date is None
                or prior.period.start_date is None
                or current.period.end_date - current.period.start_date
                != prior.period.end_date - prior.period.start_date
            ):
                continue
            return True
        return False
