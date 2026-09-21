"""Acquisition bounds are independent of financial request options."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest
from equity_schema.bootstrap import BootstrapPlan


def plan():
    return BootstrapPlan(
        uuid4(),
        "0001876042",
        uuid4(),
        uuid4(),
        date(2025, 1, 1),
        date(2026, 9, 21),
        ("company_facts/0001876042", "submissions/0001876042"),
    )


@pytest.mark.parametrize(
    "change",
    [
        {"version": "unreviewed-v2"},
        {"cik": "1876042"},
        {"cik": "0000000000"},
        {"inventory_end": date(2027, 1, 2)},
        {"inventory_end": date(2024, 1, 1)},
        {"resources": ("company_facts/0001876042",)},
        {
            "resources": (
                "company_facts/0001876042",
                "submissions/0001876042",
                "submissions/0001876042",
            )
        },
    ],
)
def test_invalid_plan_bounds(change):
    with pytest.raises(ValueError):
        replace(plan(), **change)


@pytest.mark.parametrize(
    "key",
    [
        "company_facts/0000320193",
        "filing_document/0001876042/0001876042-26-000062/../x.htm",
        "filing_document/0001876042/0001876042-26-000062/https://example.invalid/x",
        "submissions_history/0001876042/CIK0000320193-submissions-001.json",
        "price/0001876042",
        "macro/fed",
    ],
)
def test_unreviewed_resource_shapes(key):
    base = plan()
    with pytest.raises(ValueError):
        replace(base, resources=(*base.resources, key))


def test_count_limit_and_exact_history_are_explicit():
    base = plan()
    five = tuple(f"filing_document/0001876042/0001876042-26-00006{i}/doc.htm" for i in range(5))
    assert len(replace(base, resources=(*base.resources, *five)).resources) == 7
    with pytest.raises(ValueError, match="at most"):
        replace(
            base,
            resources=(
                *base.resources,
                *five,
                "filing_document/0001876042/0001876042-26-000070/doc.htm",
            ),
        )
    assert replace(
        base,
        resources=(
            *base.resources,
            "submissions_history/0001876042/CIK0001876042-submissions-001.json",
        ),
    )
