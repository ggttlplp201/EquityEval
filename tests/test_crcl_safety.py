"""D5c keeps historical knowledge separate from retrospective content review."""

import copy
import json
from datetime import datetime
from uuid import UUID

import pytest
from equity_ingest.sec_inventory import parse_submissions

from scripts import review_crcl_safety as safety


def document():
    rows = {
        "accessionNumber": ["0001876042-26-000062", "0001876042-26-000078"],
        "filingDate": ["2026-03-09", "2026-03-17"],
        "reportDate": ["2025-12-31", "2026-03-16"],
        "form": ["10-K", "8-K"],
        "primaryDocument": ["crcl-20251231.htm", "crcl-20260316.htm"],
        "acceptanceDateTime": ["2026-03-09T12:36:51Z", "2026-03-17T12:06:38Z"],
        "items": ["", "5.02,9.01"],
    }
    return parse_submissions(
        json.dumps({"cik": "0001876042", "filings": {"recent": rows, "files": []}}).encode(),
        expected_cik="0001876042",
        capture_id=UUID("0e93340d-a10c-40eb-b463-047c23be58bf"),
    )


def test_advertised_inventory_never_means_event_documents_are_reviewed():
    result = safety.scope_inventory(document(), {})
    assert len(result) == 2
    assert [row["bodyStatus"] for row in result] == ["missing", "missing"]
    assert result[1]["items"] == "5.02,9.01"
    assert all(row["eventReview"] == "not_reviewed" for row in result)


def test_october_retrieval_cannot_satisfy_september_knowledge_cutoff():
    assert safety.within_historical_cutoff("2026-09-21T17:07:36.842185+00:00")
    assert not safety.within_historical_cutoff("2026-10-12T20:00:00+00:00")
    with pytest.raises(ValueError):
        safety.within_historical_cutoff("2026-09-21T17:00:00")


def test_retained_body_is_not_a_substantive_event_review():
    rows = safety.scope_inventory(
        document(),
        {
            "0001876042-26-000078": {
                "capture_id": "test",
                "completed_at": "2026-10-12T20:00:00+00:00",
            }
        },
    )
    event = rows[1]
    assert event["bodyStatus"] == "retrospective_only"
    assert event["availableAtHistoricalCutoff"] is False
    assert event["eventReview"] == "not_reviewed"


def test_acquisition_groups_cover_only_missing_pinned_documents_with_existing_cap():
    rows = safety.scope_inventory(document(), {})
    groups = safety.capture_groups(rows)
    assert len(groups) == 1
    assert len(groups[0]) == 2
    assert all(key.startswith("filing_document/0001876042/") for key in groups[0])
    with pytest.raises(ValueError):
        safety.capture_groups([rows[0], rows[0]])


def test_profile_is_dated_descriptive_and_does_not_activate_generic_rules():
    profile = safety.business_profile(UUID("91a2c4c4-c5d8-40cc-8172-32bc311d9780"))
    assert profile.known_on > safety.CUTOFF.date()
    assert profile.effective_on == profile.known_on
    assert next(rule for rule in profile.rules if rule.metric_id == "operating_margin").applicable
    assert all(
        rule.applicable is None for rule in profile.rules if rule.metric_id != "operating_margin"
    )
    assert "stablecoin" in profile.business_model.lower()


def test_saved_safety_projection_has_no_numeric_publication_and_exact_roster():
    from scripts import export_crcl_safety as export

    review = json.loads((safety.ROOT / safety.REPORT).read_text())
    result = export.project(review)
    assert result["historicalDecision"]["status"] == "blocked"
    assert result["retrospectiveDecision"]["status"] == "incomplete"
    assert result["operatingMargin"] is None
    assert result["publishedMetricCount"] == 0
    assert len(result["filings"]) == 19
    assert sum(row["availableAtHistoricalCutoff"] for row in result["filings"]) == 3
    assert datetime.fromisoformat(result["historicalRetrievalCutoff"]) == safety.CUTOFF
    assert result["profile"]["known_on"] == "2026-10-12"
    assert all(result["details"][check["detailId"]] for check in result["checks"])
    assert export.generated() == export.generated()


@pytest.mark.parametrize("mutation", ["cutoff", "roster", "completeness", "publication", "profile"])
def test_changed_evidence_requires_new_review(mutation):
    from scripts import export_crcl_safety as export

    review = copy.deepcopy(json.loads((safety.ROOT / safety.REPORT).read_text()))
    if mutation == "cutoff":
        review["historicalRetrievalCutoff"] = "2026-10-12T20:00:00+00:00"
    elif mutation == "roster":
        review["filings"].pop()
    elif mutation == "completeness":
        review["historicalDecision"]["status"] = "passed"
    elif mutation == "publication":
        review["operatingMargin"] = "0"
    else:
        review["profile"]["known_on"] = "2026-09-21"
    with pytest.raises(ValueError):
        export.project(review)


def test_reclassification_scope_does_not_clear_the_operating_margin_operands():
    review = json.loads((safety.ROOT / safety.REPORT).read_text())
    assert "reclassification_scope_unresolved" in review["retrospectiveDecision"]["reasonCodes"]
    check = next(item for item in review["checks"] if item["id"] == "reclassifications")
    assert check["status"] == "blocked"
    evidence = review["details"]["reclassifications"]
    assert len(evidence["sources"]) == 5
    assert all(
        "total assets, total liabilities and net income" in row["value"]
        for row in evidence["sections"][0]["rows"][1:]
    )


def test_runtime_failure_is_saved_without_claiming_no_application_writes(tmp_path, monkeypatch):
    from scripts import capture_crcl_safety as capture

    monkeypatch.setattr(capture, "ROOT", tmp_path)
    (tmp_path / safety.ACQUISITION).parent.mkdir(parents=True)
    monkeypatch.setattr(
        capture, "_capture", lambda: (_ for _ in ()).throw(RuntimeError("private runtime details"))
    )
    capture.capture()
    result = json.loads((tmp_path / safety.ACQUISITION).read_text())
    assert result["status"] == "blocked"
    assert result["groups"] == []
    assert result["originalRowsPreserved"] is None
    assert result["errorType"] == "RuntimeError"
    assert "private runtime details" not in json.dumps(result)
    with pytest.raises(ValueError, match="already exists"):
        capture.capture()


def test_partial_acquisition_keeps_missing_bodies_and_unverified_preservation_blocked():
    rows = safety.scope_inventory(document(), {})
    codes = safety.acquisition_blockers(rows, {"groups": [], "originalRowsPreserved": None})
    assert codes == [
        "missing_primary_bodies",
        "acquisition_incomplete",
        "application_preservation_unverified",
    ]
    assert safety.acquisition_blockers(rows, None) == [
        "missing_primary_bodies",
        "acquisition_incomplete",
        "application_preservation_unverified",
    ]
    assert (
        safety.acquisition_blockers(
            [],
            {
                "groups": [{}] * 4,
                "originalRowsPreserved": True,
                "status": "captured_pending_review",
            },
        )
        == []
    )


def test_partial_review_replays_available_evidence_and_lists_every_missing_body(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    saved = json.loads((safety.ROOT / safety.REPORT).read_text())
    audit = safety.read_audit(safety.ROOT)
    rows = saved["filings"]
    fields = {
        "accessionNumber": "accession",
        "filingDate": "filedDate",
        "reportDate": "reportPeriodEnd",
        "form": "form",
        "acceptanceDateTime": "acceptedAt",
        "items": "items",
    }
    recent = {name: [row[key] or "" for row in rows] for name, key in fields.items()}
    recent["primaryDocument"] = [row["resourceKey"].rsplit("/", 1)[1] for row in rows]
    inventory = json.dumps(
        {"cik": "0001876042", "filings": {"recent": recent, "files": []}}
    ).encode()
    quote = (
        "Certain prior period amounts have been reclassified in order to conform with "
        "the current period presentation. These had no impact on previously reported "
        "total assets, total liabilities and net income."
    )
    annual = " ".join(value for key, value in safety.QUOTES.items() if key != "amendment")
    by_key = {
        safety.RESOURCES[0]: b"{}",
        safety.RESOURCES[1]: inventory,
        safety.RESOURCES[2]: f"<html>{annual} {quote}</html>".encode(),
        safety.RESOURCES[3]: f"<html>{safety.QUOTES['amendment']}</html>".encode(),
        safety.RESOURCES[4]: f"<html>{quote}</html>".encode(),
    }
    by_blob = {row["blob_key"]: by_key[row["source_object_key"]] for row in audit["captures"]}

    class FixtureArchive:
        def __init__(self, _root):
            pass

        def read_blob(self, key, *_):
            return by_blob[key]

    monkeypatch.setattr(safety, "LocalArchive", FixtureArchive)
    monkeypatch.setattr(safety, "read_audit", lambda _: audit)
    monkeypatch.setattr(
        safety,
        "prepare",
        lambda *_: (
            SimpleNamespace(
                input_manifest_hash=safety.INPUT_HASH, output_manifest_hash=safety.OUTPUT_HASH
            ),
            None,
        ),
    )
    monkeypatch.setattr(safety, "readiness_generated", lambda _: {})
    target = tmp_path / safety.ACQUISITION
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "groups": [{"captures": []}],
                "status": "incomplete",
                "originalRowsPreserved": True,
                "note": "Partial capture",
            }
        )
    )
    review = safety.review(tmp_path)
    assert review == safety.review(tmp_path)
    assert review["retrospectiveDecision"]["status"] == "blocked"
    assert len(review["missingPrimaryBodies"]) == 16
    assert review["freshInventory"] is None
    assert review["operatingMargin"] is None
    assert len(review["details"]["reclassifications"]["sources"]) == 2
    assert review["details"]["events"]["sources"] == []
    assert "two newly discovered" not in review["nextStep"]
    assert "Capture and review fresh Submissions inventory" in review["nextStep"]
