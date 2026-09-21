"""Hand-checked UTC slot arithmetic before D036 scheduler implementation."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from equity_schema.filing_scheduler import ScheduleConfig, slot_times

from tests.test_filing_monitor import plan_fixture


def config():
    return ScheduleConfig(
        plan_fixture(), datetime(2026, 9, 21, 21, tzinfo=UTC), 3600, 0, 3, 1, 3600
    )


def test_exact_hourly_slots_and_cutoff():
    c = config()
    nominal, due = slot_times(c, UUID(int=1), UUID(int=2), 2)
    assert nominal == due == datetime(2026, 9, 21, 23, tzinfo=UTC)
    assert slot_times(c, UUID(int=1), UUID(int=2), 3)[0].day == 22


def test_deterministic_jitter_and_timezone_equivalence():
    c = replace(config(), jitter_seconds=60)
    a = slot_times(c, UUID(int=1), UUID(int=2), 0)
    assert a == slot_times(c, UUID(int=1), UUID(int=2), 0)
    # Published v1 encoding vector: SHA256 begins 61f0278f3de0befe; modulo 61 = 50.
    assert a[1] - a[0] == timedelta(seconds=50)
    assert timedelta(0) <= a[1] - a[0] <= timedelta(seconds=60)
    assert ScheduleConfig.from_json(c.as_json()) == c


@pytest.mark.parametrize(
    "change",
    [
        {"cadence_seconds": True},
        {"cadence_seconds": 299},
        {"jitter_seconds": 61},
        {"budget_units": 2},
        {"max_attempts": 4},
        {"lag_seconds": 3599},
        {"anchor": datetime(2026, 9, 21)},
        {"version": "unknown"},
    ],
)
def test_invalid_configuration(change):
    with pytest.raises(ValueError):
        replace(config(), **change)


def test_negative_slot_rejected():
    with pytest.raises(ValueError):
        slot_times(config(), UUID(int=1), UUID(int=2), -1)
