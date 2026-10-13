"D5e current-window review cannot promote missing or changed evidence."

import pytest

from scripts import review_crcl_current as current


def test_only_the_two_reviewed_later_primary_documents_are_planned():
    planned = current.plan()
    assert [row["accession"] for row in planned] == ["0001876042-26-000276", "0001876042-26-000279"]
    assert all(row["form"] == "8-K" for row in planned)
    assert [row["resourceKey"].rsplit("/", 1)[1] for row in planned] == [
        "crcl-20260917.htm",
        "crcl-20260925.htm",
    ]
    assert [len(group) for group in current.groups(planned)] == [2]
    with pytest.raises(ValueError):
        current.groups([planned[0], planned[0]])


def test_changed_prior_roster_fails_closed(tmp_path):
    target = tmp_path / current.PRIOR_REPORT
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    with pytest.raises(ValueError, match="Pinned D5d"):
        current.plan(tmp_path)


def test_prerequisite_failure_records_unknown_preservation_and_cannot_retry(tmp_path, monkeypatch):
    import json

    from scripts import capture_crcl_current as capture

    monkeypatch.setattr(capture, "ROOT", tmp_path)
    target = tmp_path / capture.ACQUISITION
    target.parent.mkdir(parents=True)

    def unavailable():
        raise RuntimeError("private connection details")

    monkeypatch.setattr(capture, "verify_previous", unavailable)
    capture.capture()
    report = json.loads(target.read_bytes())
    assert report["status"] == "blocked"
    assert report["originalRowsPreserved"] is None
    assert report["groups"] == []
    assert report["errorType"] == "RuntimeError"
    assert "private" not in target.read_text()
    with pytest.raises(ValueError):
        capture.capture()


def test_new_or_missing_annual_edition_cannot_clear_the_candidate():
    records = [
        {
            "start": "2025-01-01",
            "end": "2025-12-31",
            "val": 2746642000,
            "accn": "0001876042-26-000062",
            "form": "10-K",
            "filed": "2026-03-09",
        }
    ]
    assert current.annual_edition_check(records, "2746642000")["status"] == "matched"
    for changed in (
        [],
        [{**records[0], "accn": "new"}],
        [{**records[0], "val": 1}],
        [{**records[0], "start": "2025-04-01"}],
        [{**records[0], "form": "10-K/A"}],
    ):
        assert current.annual_edition_check(changed, "2746642000")["status"] == "blocked"


def test_missing_linked_body_and_unknown_reconciliation_block_new_batch():
    result = current.candidate_decision(
        missing_bodies=["filing_document/missing"],
        accounting_complete=False,
        inventory_complete=True,
        acquisition_complete=True,
    )
    assert result["status"] == "blocked"
    assert result["batchId"] is None
    assert set(result["reasonCodes"]) == {
        "linked_body_unreviewed",
        "affected_line_scope_unresolved",
    }


def test_unavailable_current_acquisition_does_not_claim_complete_coverage():
    result = current.review_acquisition(None)
    assert result["candidateBatch"]["status"] == "blocked"
    assert result["inventoryObservedAt"] is None
    assert result["retrievalCutoff"] is None
    assert all(row["status"] == "missing" for row in result["events"])
    assert result["operatingMargin"] is None
    assert result["currentInventory"] is None
    assert "current_inventory_incomplete" in result["candidateBatch"]["reasonCodes"]


def test_affected_line_reconciliation_requires_two_distinct_matching_editions():
    rows = [
        {
            "captureId": "first",
            "concept": "Revenues",
            "start": "2025-01-01",
            "end": "2025-06-30",
            "unit": "USD",
            "scale": 3,
            "literalThousands": "1,236,651",
        },
        {
            "captureId": "second",
            "concept": "Revenues",
            "start": "2025-01-01",
            "end": "2025-06-30",
            "unit": "USD",
            "scale": 3,
            "literalThousands": "1,236,651",
        },
    ]
    assert current.reconcile_editions(rows)["status"] == "matched"
    for changed in (
        [rows[0]],
        [rows[0], rows[0]],
        [rows[0], {**rows[1], "unit": "EUR"}],
        [rows[0], {**rows[1], "end": "2025-03-31"}],
        [rows[0], {**rows[1], "literalThousands": "1,000"}],
    ):
        assert current.reconcile_editions(changed)["status"] == "unconfirmed"


def test_current_inventory_rejects_changed_primary_identity_and_new_events():
    from datetime import datetime

    from tests.test_crcl_safety import document

    doc = document()
    expected = [
        {
            "accession": f.accession,
            "form": f.form,
            "filedDate": str(f.filed_date),
            "resourceKey": f"filing_document/0001876042/{f.accession}/{f.primary_document}",
        }
        for f in doc.filings
    ]
    cutoff = datetime.fromisoformat("2026-10-13T05:01:15+00:00")
    assert current.review_inventory(doc, expected, cutoff)["status"] == "matched_scoped_roster"
    changed = [
        {**r, "resourceKey": r["resourceKey"] + "/wrong"} if i == 0 else r
        for i, r in enumerate(expected)
    ]
    assert current.review_inventory(doc, changed, cutoff)["status"] == "blocked"
    result = current.review_inventory(doc, expected[:1], cutoff)
    assert result["status"] == "blocked"
    assert result["unexpectedAccessions"] == [expected[1]["accession"]]


def test_checked_current_projection_preserves_no_publication_and_exact_blockers():
    import copy
    import json

    from scripts.export_crcl_current import project

    data = json.loads((current.ROOT / current.REPORT).read_bytes())
    assert project(data)["candidateBatch"]["batchId"] is None
    assert data["operatingMargin"] is None
    assert data["currentInventory"]["count"] == 21
    assert data["missingBodies"][0]["resourceKey"].endswith("/final_leadershiptransiti.htm")
    assert [r["status"] for r in data["affectedLineChecks"]] == [
        "unconfirmed",
        "unconfirmed",
        "matched",
        "matched",
        "matched",
        "matched",
    ]
    assert all(r["status"] == "matched" for r in data["annualEditionChecks"])
    changed = copy.deepcopy(data)
    changed["candidateBatch"]["status"] = "eligible"
    with pytest.raises(ValueError):
        project(changed)


def test_unavailable_review_does_not_invent_cfo_exhibit_or_body_completion():
    result = current.review_acquisition(None)
    assert result["missingBodies"] == []
    assert "CFO" not in result["nextStep"]
    assert "unavailable" in result["conclusion"]
