"""Adversarial filing metadata comparisons; no network or inferred financial values."""

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from equity_ingest.filing_monitor import compare_inventories
from equity_ingest.sec_inventory import assemble_inventory, parse_submissions
from equity_schema.filing_monitor import FORMS, FilingMonitorPlan, MonitorBaseline


def plan_fixture():
    return FilingMonitorPlan(
        uuid4(),
        "0001876042",
        uuid4(),
        uuid4(),
        date(2025, 1, 1),
        date(2026, 9, 21),
        datetime(2026, 9, 21, tzinfo=UTC),
        tuple(FORMS),
        ("submissions/0001876042",),
        MonitorBaseline(
            "initial_seed",
            uuid4(),
            uuid4(),
            "a" * 64,
            datetime(2026, 9, 20, tzinfo=UTC),
            seed_approval_id=uuid4(),
            plan_sha256="b" * 64,
            capture_id=uuid4(),
        ),
    )


def filing(n=1, **changes):
    return {
        "accessionNumber": f"0001628280-26-{n:06d}",
        "form": "10-Q",
        "filingDate": "2026-08-05",
        "reportDate": "2026-06-30",
        "primaryDocument": "report.htm",
        "acceptanceDateTime": "2026-08-05T13:00:00Z",
        **changes,
    }


def submissions(rows=(), history=()):
    keys = tuple(filing())
    return {
        "cik": 1876042,
        "filings": {
            "recent": {key: [row.get(key, "") for row in rows] for key in keys},
            "files": list(history),
        },
    }


def inventory(rows, plan):
    root = parse_submissions(
        json.dumps(submissions(rows)).encode(), expected_cik=plan.cik, capture_id=uuid4()
    )
    return assemble_inventory(
        root, (), boundary_start=plan.inventory_start, boundary_end=plan.inventory_end
    )


def compare(old, new, plan=None):
    plan = plan or plan_fixture()
    return compare_inventories(inventory(old, plan), inventory(new, plan), plan)


def test_no_change_ignores_row_order_and_source_capture_identity():
    assert compare([filing(), filing(2)], [filing(2), filing()])["outcome"] == "no_change"


@pytest.mark.parametrize(
    "at,included",
    [
        ("2026-09-20T23:59:59Z", True),
        ("2026-09-21T00:00:00Z", True),
        ("2026-09-21T00:00:00.000001Z", False),
    ],
)
def test_acceptance_cutoff_inclusive(at, included):
    result = compare([], [filing(acceptanceDateTime=at)])
    assert result["outcome"] == ("new_filing" if included else "no_change")
    assert bool(result["excluded_after_cutoff"]["current"]) != included


def test_late_backdated_addition_and_amendment_are_separate_editions():
    result = compare(
        [filing()], [filing(), filing(2, filingDate="2025-02-01"), filing(3, form="10-K/A")]
    )
    assert result["outcome"] == "mixed_changes"
    assert len(result["new_filings"]) == len(result["amendments"]) == 1
    assert "no restatement" in result["amendment_meaning"]


@pytest.mark.parametrize(
    "changed",
    [
        {"form": "10-K"},
        {"filingDate": "2026-08-06"},
        {"reportDate": "2026-03-31"},
        {"primaryDocument": "other.htm"},
        {"acceptanceDateTime": "2026-08-05T13:00:01Z"},
        {"acceptanceDateTime": "2026-08-05T13:00:00+00:00"},
    ],
)
def test_existing_accession_metadata_changes_block_complete_result(changed):
    result = compare([filing()], [filing(**changed)])
    assert result["outcome"] == "incomplete" and not result["baseline_eligible"]
    assert result["metadata_changes"]


@pytest.mark.parametrize("at", ["", "2026-08-05T13:00:00"])
def test_unverified_acceptance_never_becomes_no_change(at):
    result = compare([], [filing(acceptanceDateTime=at)])
    assert result["outcome"] == "incomplete"
    assert "current_acceptance_unverified" in result["flags"]


@pytest.mark.parametrize(
    "rows,flag",
    [([], "baseline_accession_missing"), ([filing(), filing()], "current_duplicate_accession")],
)
def test_missing_and_duplicate_accessions(rows, flag):
    result = compare([filing()], rows)
    assert result["outcome"] == "incomplete" and flag in result["flags"]


def test_out_of_scope_forms_and_filed_dates_do_not_create_change():
    assert (
        compare([], [filing(form="8-K"), filing(2, filingDate="2024-12-31")])["outcome"]
        == "no_change"
    )


def test_incomplete_baseline_cannot_advance():
    plan = plan_fixture()
    old = replace(inventory([], plan), completeness="incomplete", flags=("missing_history",))
    result = compare_inventories(old, inventory([], plan), plan)
    assert result["outcome"] == "incomplete" and "baseline_inventory_incomplete" in result["flags"]


def test_plan_roundtrip_canonical_order_and_tagged_baseline():
    plan = plan_fixture()
    assert FilingMonitorPlan.from_json(plan.as_json()) == plan
    assert plan.forms == tuple(sorted(FORMS))
    with pytest.raises(ValueError):
        replace(plan.baseline, manifest_id=uuid4())
    prior = MonitorBaseline(
        "prior_monitor_result",
        uuid4(),
        uuid4(),
        "c" * 64,
        plan.baseline.cutoff,
        manifest_id=uuid4(),
    )
    assert MonitorBaseline.from_json(prior.as_json()) == prior
    with pytest.raises(ValueError):
        replace(prior, capture_id=uuid4())


@pytest.mark.parametrize(
    "changes",
    [
        {"cik": "1876042"},
        {"resources": ("company_facts/0001876042",)},
        {"forms": ("10-Q", "10-Q")},
        {"forms": ("8-K",)},
        {"inventory_start": date(2020, 1, 1)},
        {"cutoff": datetime(2026, 9, 21)},
        {"version": "v2"},
        {
            "resources": (
                "submissions/0001876042",
                "submissions_history/0000000001/CIK0000000001-submissions-001.json",
            )
        },
    ],
)
def test_plan_rejects_unpinned_scope(changes):
    with pytest.raises(ValueError):
        replace(plan_fixture(), **changes)


def test_baseline_later_than_poll_is_rejected():
    plan = plan_fixture()
    with pytest.raises(ValueError):
        replace(plan, baseline=replace(plan.baseline, cutoff=plan.cutoff + timedelta(seconds=1)))
