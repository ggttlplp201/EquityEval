"""D036 internal fixed-scope UTC scheduling; no financial or public API contract."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from equity_schema.filing_monitor import FilingMonitorPlan, timestamp
from equity_schema.workflow import Database
from psycopg.types.json import Jsonb

VERSION = "sec-filing-schedule-v1"


@dataclass(frozen=True)
class ScheduleConfig:
    plan: FilingMonitorPlan
    anchor: datetime
    cadence_seconds: int
    jitter_seconds: int
    budget_units: int
    max_attempts: int
    lag_seconds: int
    active: bool = False
    version: str = VERSION

    def __post_init__(self) -> None:
        timestamp(self.anchor)
        if self.version != VERSION or not isinstance(self.plan, FilingMonitorPlan):
            raise ValueError("Unknown schedule contract")
        fields = (
            self.cadence_seconds,
            self.jitter_seconds,
            self.budget_units,
            self.max_attempts,
            self.lag_seconds,
        )
        if any(type(v) is not int for v in fields) or type(self.active) is not bool:
            raise ValueError("Schedule bounds require integers and a boolean state")
        if not 300 <= self.cadence_seconds <= 86400:
            raise ValueError("Cadence must be 300..86400 seconds")
        if not 0 <= self.jitter_seconds <= min(60, self.cadence_seconds // 10):
            raise ValueError("Jitter exceeds bounded cadence")
        if not 1 <= self.max_attempts <= 3 or not self.reserved_units <= self.budget_units <= 10000:
            raise ValueError("Budget must cover one bounded poll")
        if not self.cadence_seconds <= self.lag_seconds <= 86400 * 30:
            raise ValueError("Lag threshold must be cadence..30 days")
        if self.anchor < self.plan.baseline.cutoff:
            raise ValueError("Anchor precedes approved baseline")

    @property
    def reserved_units(self) -> int:
        return 3 * len(self.plan.resources) * self.max_attempts

    def as_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "plan": self.plan.as_json(),
            "anchor": timestamp(self.anchor),
            "cadence_seconds": self.cadence_seconds,
            "jitter_seconds": self.jitter_seconds,
            "budget_units": self.budget_units,
            "max_attempts": self.max_attempts,
            "lag_seconds": self.lag_seconds,
            "active": self.active,
        }

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "ScheduleConfig":
        fields = dict(value)
        fields["plan"] = FilingMonitorPlan.from_json(fields["plan"])
        fields["anchor"] = datetime.fromisoformat(fields["anchor"])
        return cls(**fields)


def slot_times(
    config: ScheduleConfig, schedule: UUID, revision: UUID, index: int
) -> tuple[datetime, datetime]:
    if type(index) is not int or index < 0:
        raise ValueError("Slot index must be nonnegative")
    nominal = config.anchor.astimezone(UTC) + timedelta(seconds=index * config.cadence_seconds)
    encoded = f"{VERSION}\n{schedule}\n{revision}\n{index}".encode()
    jitter = int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") % (
        config.jitter_seconds + 1
    )
    return nominal, nominal + timedelta(seconds=jitter)


def create_schedule(
    db: Database, *, workspace: UUID, security: UUID, key: str, config: ScheduleConfig, review: str
) -> UUID:
    with db.transaction():
        row = db.execute(
            "SELECT scheduler_create(%s,%s,%s,%s,%s) AS id",
            (workspace, security, key, Jsonb(config.as_json()), review),
        ).fetchone()
        assert row is not None
        return UUID(str(row["id"]))


def revise_schedule(
    db: Database, schedule: UUID, *, epoch: int, key: str, config: ScheduleConfig, reason: str
) -> UUID:
    with db.transaction():
        row = db.execute(
            "SELECT scheduler_revise(%s,%s,%s,%s,%s) AS id",
            (schedule, epoch, key, Jsonb(config.as_json()), reason),
        ).fetchone()
        assert row is not None
        return UUID(str(row["id"]))


def tick(db: Database, schedule: UUID) -> dict[str, Any]:
    with db.transaction():
        row = db.execute("SELECT scheduler_tick(%s) AS value", (schedule,)).fetchone()
        assert row is not None
        value: dict[str, Any] = row["value"]
        return value
