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
        "filing_document/0001876042/0001876042-26-000062/payload.exe",
        "filing_document/0001876042/0001876042-26-000062/report",
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


def test_crcl_history_v2_matches_reviewed_finite_roster():
    import json
    from pathlib import Path

    scope = json.loads(Path("docs/design/d5l/inventory-scope.json").read_text())
    for group in scope["groups"]:
        candidate = replace(
            plan(),
            version="sec-crcl-history-bootstrap-v2",
            inventory_start=date.fromisoformat(group["inventoryStart"]),
            inventory_end=date.fromisoformat(group["inventoryEnd"]),
            resources=tuple(group["resources"]),
        )
        assert candidate.resources == tuple(sorted(group["resources"]))


@pytest.mark.parametrize(
    "key",
    [
        "filing_document/0001876042/0000000000-24-002161/filename2.pdf",
        "filing_document/0001876042/0001876042-26-000062/crcl-20251231.htm",
        "submissions_history/0001876042/CIK0001876042-submissions-001.json",
    ],
)
def test_crcl_history_v2_rejects_resources_outside_exact_roster(key):
    base = plan()
    with pytest.raises(ValueError):
        replace(base, version="sec-crcl-history-bootstrap-v2", resources=(*base.resources, key))


def test_v1_pdf_rejection_is_preserved():
    base = plan()
    with pytest.raises(ValueError):
        replace(
            base,
            resources=(
                *base.resources,
                "filing_document/0001876042/0000000000-24-002161/filename1.pdf",
            ),
        )


def test_exact_pdf_resource_identity_without_generic_pdf_support():
    from equity_ingest.contracts import ResourceKind, SecResource
    from equity_schema.crcl_history import CRCL_HISTORY_PDFS

    for key in CRCL_HISTORY_PDFS:
        _, cik, accession, filename = key.split("/")
        resource = SecResource(
            plan().issuer_id, cik, ResourceKind.FILING_DOCUMENT, filename, accession
        )
        assert resource.object_key == key
        assert resource.url == (
            "https://www.sec.gov/Archives/edgar/data/1876042/"
            + accession.replace("-", "")
            + "/"
            + filename
        )
    for cik, accession, filename in [
        ("0001876042", "0000000000-24-002161", "filename2.pdf"),
        ("0000320193", "0000000000-24-002161", "filename1.pdf"),
        ("0001876042", "0000000000-24-002162", "filename1.pdf"),
    ]:
        with pytest.raises(ValueError):
            SecResource(plan().issuer_id, cik, ResourceKind.FILING_DOCUMENT, filename, accession)


def test_crcl_history_v2_rejects_other_issuer_and_six_bodies():
    from equity_schema.crcl_history import CRCL_HISTORY_DOCUMENTS

    with pytest.raises(ValueError):
        replace(
            plan(),
            version="sec-crcl-history-bootstrap-v2",
            cik="0000320193",
            resources=("company_facts/0000320193", "submissions/0000320193"),
        )
    with pytest.raises(ValueError, match="at most"):
        replace(
            plan(),
            version="sec-crcl-history-bootstrap-v2",
            resources=(*plan().resources, *sorted(CRCL_HISTORY_DOCUMENTS)[:6]),
        )
