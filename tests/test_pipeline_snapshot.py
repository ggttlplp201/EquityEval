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


@pytest.fixture
def search():
    return json.loads((ROOT / exporter.SEARCH).read_text())


def test_search_notes_remain_distinct_from_archived_evidence(audits, search):
    data = exporter.project_search(search, audits[1])
    assert len(data["sources"]) == 4
    assert "not archived application evidence" in data["basis"]
    assert "2025-06-05" in data["effectiveDateRule"]
    assert "cannot be backdated" in data["effectiveDateRule"]
    assert "no explicit quotation-currency field" in data["sources"][1]["finding"]
    assert data == exporter.project_search(deepcopy(search), deepcopy(audits[1]))
    assert exporter.export() == exporter.export()


@pytest.mark.parametrize(
    "key,value",
    [
        ("cik", "0000000001"),
        ("issuer", "Another issuer"),
        ("symbol", "OTHER"),
        ("exchange_code", "LSE"),
        ("share_class", "Class B common stock"),
        ("listing_start", "2026-09-21"),
    ],
)
def test_search_cannot_bind_same_symbol_to_another_identity_or_date(audits, search, key, value):
    search["target"][key] = value
    with pytest.raises(ValueError, match="bind to the reviewed"):
        exporter.project_search(search, audits[1])


@pytest.mark.parametrize(
    "key,value",
    [
        ("registration_ready", True),
        ("quote_currency", "USD"),
        ("quote_currency_valid_from", "2025-06-05"),
        ("quote_currency_valid_from", "2026-09-21"),
        ("new_capture_ids", ["unarchived-web-response"]),
        ("new_policy_revision_ids", ["website-is-reachable"]),
        ("outcome", "registered"),
    ],
)
def test_search_cannot_promote_web_observations_into_registration(audits, search, key, value):
    search[key] = value
    with pytest.raises(ValueError, match="not new capture, currency or registration evidence"):
        exporter.project_search(search, audits[1])


@pytest.mark.parametrize("meaning", ["reporting", "offering-price", "index", "broker-display"])
def test_currency_hints_of_other_meanings_do_not_fill_gap(audits, search, meaning):
    # Search annotations do not acquire the authority of source captures.
    search["sources"][0]["currency_hint"] = {"value": "USD", "meaning": meaning}
    data = exporter.project_search(search, audits[1])
    assert "currency_hint" not in json.dumps(data)
    projected = exporter.project(*audits)
    assert projected["identityFields"][-1]["value"] is None
    assert projected["stages"][3]["status"] == "blocked"


def test_search_projection_excludes_unreviewed_private_metadata(audits, search):
    search["private_note"] = "private-test-marker"
    search["sources"][0]["blob_key"] = "/private/raw/test.gz"
    search["sources"][0]["contact"] = "private-person@example.invalid"
    rendered = json.dumps(exporter.project_search(search, audits[1]))
    assert all(text not in rendered for text in ("private-", "blob_key", "/private/"))


def test_search_rejects_duplicate_sources_and_false_capture_claims(audits, search):
    duplicate = deepcopy(search)
    duplicate["sources"].append(duplicate["sources"][0])
    with pytest.raises(ValueError, match="unique"):
        exporter.project_search(duplicate, audits[1])
    search["sources"][0]["application_evidence"] = "new-capture"
    with pytest.raises(ValueError, match="cannot claim new captures"):
        exporter.project_search(search, audits[1])


@pytest.mark.parametrize("nested", [False, True])
def test_search_rejects_unreviewed_links_including_related_sources(audits, search, nested):
    source = search["sources"][1]
    target = source["related_urls"][0] if nested else source
    target["url"] = "https://www.nyse.com.evil.invalid/quote/CRCL"
    with pytest.raises(ValueError, match="public research URLs"):
        exporter.project_search(search, audits[1])


def test_search_drift_cannot_silently_update_ui(tmp_path):
    for relative in (exporter.ACQUISITION, exporter.REVIEW, exporter.SEARCH):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    with (tmp_path / exporter.SEARCH).open("a") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="D3f search changed"):
        exporter.export(tmp_path)


def test_optional_application_check_reuses_review_and_refuses_count_drift(monkeypatch, audits):
    from scripts import review_crcl_identity

    actual = deepcopy(audits[1])
    monkeypatch.setattr(review_crcl_identity, "application_review", lambda: actual)
    exporter.verify_application()
    exporter.verify_application()
    actual["database_snapshot"]["security_identifiers"]["count"] = 1
    with pytest.raises(ValueError, match="drifted"):
        exporter.verify_application()


def test_optional_application_check_refuses_hash_drift_even_with_same_counts(monkeypatch, audits):
    from scripts import review_crcl_identity

    actual = deepcopy(audits[1])
    actual["database_snapshot"]["source_captures"]["sha256"] = "0" * 64
    monkeypatch.setattr(review_crcl_identity, "application_review", lambda: actual)
    with pytest.raises(ValueError, match="drifted"):
        exporter.verify_application()


def test_application_verification_failure_never_writes_or_exposes_driver_details(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    monkeypatch.setattr(exporter, "export", lambda: "not written")

    def fail():
        raise RuntimeError("postgresql://private:secret@localhost/example")

    monkeypatch.setattr(exporter, "verify_application", fail)
    monkeypatch.setattr("sys.argv", ["export_pipeline_snapshot", "--verify-application"])
    with pytest.raises(SystemExit) as error:
        exporter.main()
    assert error.value.code == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Application snapshot verification failed (RuntimeError).\n"
    assert not (tmp_path / exporter.OUTPUT).exists()
