from scripts import review_crcl_leadership as review


def test_plan_pins_only_reviewed_parent_exhibit():
    rows = review.plan()
    assert [row["resourceKey"] for row in rows] == [review.KEY]
    assert review.groups(rows) == ((review.KEY,),)


def test_unavailable_acquisition_does_not_clear_event_or_batch():
    result = review.review_acquisition(None)
    assert result["event"]["status"] == "unavailable"
    assert result["candidateBatch"]["status"] == "blocked"
    assert "linked_body_unreviewed" in result["candidateBatch"]["reasonCodes"]
    assert result["inventoryObservedAt"] is None
    assert result["operatingMargin"] is None


def test_saved_review_closes_only_exhibit_and_retains_accounting_gate():
    from scripts.export_crcl_leadership import project

    result = project(review.review())
    assert result["event"]["status"] == "reviewed"
    assert result["candidateBatch"]["reasonCodes"] == ["affected_line_scope_unresolved"]
    assert result["accounting"]["periodicBodiesScanned"] == 6
    assert len(result["accounting"]["q1SourceKeys"]) == 1
    assert result["nextSource"] == review.PROSPECTUS
    assert result["candidateBatch"]["batchId"] is None


def test_changed_body_duplicate_scope_and_backdated_capture_fail_closed():
    import copy
    import json

    import pytest
    from equity_ingest.archive import ArchiveError

    from scripts.normalize_crcl import ROOT

    original = json.loads((ROOT / review.ACQUISITION).read_text())
    for mutation in ("hash", "duplicate", "timestamp", "scope"):
        changed = copy.deepcopy(original)
        captures = changed["groups"][0]["captures"]
        if mutation == "hash":
            captures[-1]["body_sha256"] = "0" * 64
        if mutation == "duplicate":
            captures.append(copy.deepcopy(captures[-1]))
        if mutation == "timestamp":
            captures[-1]["completed_at"] = "2026-09-21T00:00:00+00:00"
        if mutation == "scope":
            captures[-1]["source_object_key"] = review.PROSPECTUS
        with pytest.raises((ValueError, ArchiveError)):
            review.review_acquisition(changed)


def test_partial_without_body_never_inherits_complete_event():
    import json

    from scripts.normalize_crcl import ROOT

    acquisition = json.loads((ROOT / review.ACQUISITION).read_text())
    acquisition["groups"][0]["captures"] = acquisition["groups"][0]["captures"][:2]
    result = review.review_acquisition(acquisition)
    assert result["event"]["status"] == "unavailable"
    assert "linked_body_unreviewed" in result["candidateBatch"]["reasonCodes"]
    assert "acquisition_or_preservation_incomplete" in result["candidateBatch"]["reasonCodes"]
    assert "leadership" not in result["details"]
    assert "unavailable" in result["conclusion"]


def test_projection_mutation_cannot_publish_metric_or_clear_gate():
    import copy

    import pytest

    from scripts.export_crcl_leadership import project

    for field, value in [
        ("operatingMargin", "0.1"),
        ("publishedMetricCount", 1),
        ("candidateBatch", {"status": "eligible"}),
    ]:
        changed = copy.deepcopy(review.review())
        changed[field] = value
        with pytest.raises(ValueError):
            project(changed)


def test_unavailable_runtime_records_blocked_attempt(tmp_path, monkeypatch):
    import json

    from scripts import capture_crcl_leadership as capture

    monkeypatch.setattr(capture, "ROOT", tmp_path)
    (tmp_path / "docs/research").mkdir(parents=True)

    def unavailable():
        raise RuntimeError("unavailable")

    monkeypatch.setattr(capture, "verify_previous", unavailable)
    capture.capture()
    result = json.loads((tmp_path / review.ACQUISITION).read_text())
    assert result["kind"] == "d5f-governed-leadership-acquisition"
    assert result["status"] == "blocked"
    assert result["originalRowsPreserved"] is None
    assert result["groups"] == []


def test_q1_facts_records_exact_later_edition_and_rejects_changed_scope():
    import copy

    doc = {"cik": 1876042, "facts": {"us-gaap": {}}}
    for concept in ("Revenues", "OperatingIncomeLoss"):
        doc["facts"]["us-gaap"][concept] = {
            "units": {
                "USD": [
                    {
                        "start": "2025-01-01",
                        "end": "2025-03-31",
                        "accn": "0001876042-26-000150",
                        "form": "10-Q",
                        "filed": "2026-05-11",
                        "val": 1,
                    }
                ]
            }
        }
    assert review.q1_facts_review(doc)["status"] == "later_comparative_only"
    for change in ("edition", "unit", "missing"):
        altered = copy.deepcopy(doc)
        units = altered["facts"]["us-gaap"]["Revenues"]["units"]
        if change == "edition":
            units["USD"][0]["accn"] = "earlier-unreviewed"
        if change == "unit":
            units["EUR"] = units.pop("USD")
        if change == "missing":
            units["USD"] = []
        assert review.q1_facts_review(altered)["status"] == "edition_review_required"


def test_every_retained_facts_vintage_has_correct_source_and_initial_attempts():
    result = review.review()
    rows = result["q1FactsVintages"]
    assert len(rows) == 12
    assert {"33df6650-2ca9-4668-b513-19f04d421c86", "a68a6927-0fc8-4cd0-885f-6d5458090841"} <= {
        r["captureId"] for r in rows
    }
    assert all(r["source"]["label"] == "SEC Company Facts" for r in rows)
    assert all(r["status"] == "later_comparative_only" for r in rows)
