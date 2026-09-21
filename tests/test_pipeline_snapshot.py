"""The development pipeline view projects reviewed evidence, never live or private data."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts import export_pipeline_snapshot as exporter

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def audits():
    return (
        json.loads((ROOT / exporter.ACQUISITION).read_text()),
        json.loads((ROOT / exporter.REVIEW).read_text()),
    )


def test_shipped_typed_fixture_matches_pinned_audits():
    assert (ROOT / exporter.OUTPUT).read_text() == exporter.export(ROOT)


def test_cumulative_counts_are_distinct_from_five_current_captures(audits):
    data = exporter.project(*audits)
    assert {item["id"]: item["value"] for item in data["counts"]} == {
        "source_captures": 12,
        "source_fetch_attempts": 12,
        "analysis_requests": 3,
        "issuers": 1,
        "securities": 1,
        "security_identifiers": 0,
        "watchlist_memberships": 0,
        "normalization_batches": 0,
    }
    assert len(data["captures"]) == len(data["plan"]["resources"]) == 5
    assert [stage["status"] for stage in data["stages"]] == [
        "verified",
        "verified",
        "gap",
        "blocked",
        "not-started",
        "not-started",
    ]


def test_identity_and_missing_currency_keep_their_exact_source_evidence(audits):
    data = exporter.project(*audits)
    fields = {field["id"]: field for field in data["identityFields"]}
    assert {key: field["value"] for key, field in fields.items()} == {
        "cik": "0001876042",
        "name": "Circle Internet Group, Inc.",
        "symbol": "CRCL",
        "exchange_code": "NYSE",
        "share_class": "Class A common stock",
        "valid_from": "2025-06-05",
        "quote_currency": None,
    }
    assert fields["quote_currency"]["evidence"] == []
    assert fields["quote_currency"]["status"] == "unsubstantiated"
    for key in exporter.FIELD_LABELS:
        original = audits[1]["fields"][key]["evidence"]
        assert fields[key]["evidence"] == [
            {"captureId": row["capture_id"], "locator": row["locator"], "excerpt": row["value"]}
            for row in original
        ]
    for mapped, source in zip(data["captures"], audits[1]["captures"], strict=True):
        assert mapped["sha256"] == source["body_sha256"]
        assert mapped["capturedAt"] == exporter.utc_label(source["completed_at"])


def test_sanitization_is_an_allowlist_even_when_extra_private_fields_exist(audits):
    acquisition, review = deepcopy(audits)
    for audit in (acquisition, review):
        audit["contact"] = "private-person@example.invalid"
        audit["database_url"] = "postgresql://private:secret@localhost/db"
        for item in audit["captures"]:
            item["blob_key"] = "/private/raw/archive.gz"
            item["private_note"] = "sensitive-test-marker"
    output = json.dumps(exporter.project(acquisition, review))
    for excluded in (
        "blob_key",
        "/private/",
        "private-person",
        "postgresql:",
        "sensitive-test-marker",
        "database_snapshot",
        "source_policy_revisions",
    ):
        assert excluded not in output


@pytest.mark.parametrize(
    "url",
    [
        "file:///private/raw",
        "javascript:alert(1)",
        "https://data.sec.gov.evil.invalid/",
        "https://person@data.sec.gov/",
        "https://data.sec.gov/?secret=value",
    ],
)
def test_nonpublic_or_unreviewed_source_links_are_refused(audits, url):
    acquisition, review = audits
    acquisition["captures"][0]["request_url"] = url
    review["captures"][0]["request_url"] = url
    with pytest.raises(ValueError, match="public SEC"):
        exporter.project(acquisition, review)


@pytest.mark.parametrize(
    "key,value",
    [
        ("registration_ready", True),
        ("financial_result", True),
        ("ordinary_request_eligible", True),
        ("request_id", "unrelated"),
    ],
)
def test_incompatible_review_cannot_be_relabelled_as_this_snapshot(audits, key, value):
    acquisition, review = audits
    review[key] = value
    with pytest.raises(ValueError, match="reviewed blocked"):
        exporter.project(acquisition, review)


def test_inferred_currency_is_rejected(audits):
    acquisition, review = audits
    review["fields"]["quote_currency"]["value"] = "USD"
    with pytest.raises(ValueError, match="remain missing"):
        exporter.project(acquisition, review)


def test_orphan_evidence_is_rejected(audits):
    acquisition, review = audits
    review["fields"]["symbol"]["evidence"][0]["capture_id"] = "other-issuer"
    with pytest.raises(ValueError, match="displayed source capture"):
        exporter.project(acquisition, review)


def test_audit_drift_requires_review_instead_of_implicitly_updating_ui(tmp_path, audits):
    for relative, body in zip((exporter.ACQUISITION, exporter.REVIEW), audits, strict=True):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="audit changed"):
        exporter.export(tmp_path)
