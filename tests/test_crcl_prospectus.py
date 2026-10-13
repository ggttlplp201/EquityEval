from scripts import review_crcl_prospectus as review


def test_exact_prospectus_plan_rejects_source_expansion():
    import pytest

    rows = review.plan()
    assert rows[0]["resourceKey"] == review.KEY
    assert review.groups(rows) == ((review.KEY,),)
    with pytest.raises(ValueError):
        review.groups(rows + rows)


def test_statement_period_unit_sign_changes_are_not_matches():
    import pytest

    text = (
        review.Q1_HEADER + " Total revenue and reserve income 578,573 365,094 "
        "Operating income from continuing operations 92,940 52,319"
    )
    assert len(review.check_q1_table(text)) == 2
    for before, after in [
        ("March 31", "June 30"),
        ("thousands", "millions"),
        ("92,940", "(92,940)"),
        ("2025 2024", "2024 2025"),
    ]:
        with pytest.raises(ValueError):
            review.check_q1_table(text.replace(before, after))


def test_saved_review_proves_selected_pairs_but_not_registration_history():
    from scripts.export_crcl_prospectus import project

    result = project(review.review())
    assert result["comparison"]["status"] == "matched_tested_operands"
    assert len(result["comparison"]["laterComparisons"]) == 6
    assert len(result["q1FactsVintages"]) == 13
    assert result["q1FactsMatch"] is True
    assert len(result["registrationRoster"]) == 8
    assert len(result["missingBodies"]) == 7
    assert result["candidateBatch"]["reasonCodes"] == ["registration_history_unreviewed"]
    assert all(r["resourceKey"] != review.KEY for r in result["missingBodies"])
    assert all(r["source"]["label"] == "SEC Company Facts" for r in result["q1FactsVintages"])
    assert result["operatingMargin"] is None
    assert result["candidateBatch"]["batchId"] is None


def test_partial_and_unavailable_evidence_never_claim_statement_match():
    import copy
    import json

    acquisition = json.loads((review.ROOT / review.ACQUISITION).read_bytes())
    partial = copy.deepcopy(acquisition)
    partial["groups"][0]["captures"] = [
        c for c in partial["groups"][0]["captures"] if c["source_object_key"] != review.KEY
    ]
    for item in (None, partial):
        result = review.review_acquisition(item)
        assert result["comparison"] is None
        assert result["q1FactsMatch"] is False
        assert "prospectus_body_unreviewed" in result["candidateBatch"]["reasonCodes"]
        assert "seven" not in result["nextStep"]
        assert "unavailable" in result["conclusion"]
        assert "statements" not in result["details"]
        assert len(result["missingBodies"]) == 8
    result = review.review_acquisition(None)
    assert result["inventoryObservedAt"] is None
    assert result["registrationRosterMatches"] is False


def test_changed_capture_cannot_reuse_pinned_review():
    import copy
    import json

    import pytest
    from equity_ingest.archive import ArchiveError

    original = json.loads((review.ROOT / review.ACQUISITION).read_bytes())
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
            captures[-1]["source_object_key"] = "unapproved"
        with pytest.raises((ValueError, ArchiveError)):
            review.review_acquisition(changed)


def test_projection_tampering_cannot_clear_gate():
    import copy

    import pytest

    from scripts.export_crcl_prospectus import project

    original = review.review()
    for field, value in [
        ("operatingMargin", "0.1"),
        ("missingBodies", []),
        ("q1FactsMatch", False),
    ]:
        changed = copy.deepcopy(original)
        changed[field] = value
        with pytest.raises(ValueError):
            project(changed)


def test_failed_prerequisite_records_honest_blocked_attempt(tmp_path, monkeypatch):
    import json

    from scripts import capture_crcl_prospectus as capture

    monkeypatch.setattr(capture, "ROOT", tmp_path)
    (tmp_path / "docs/research").mkdir(parents=True)

    def unavailable():
        raise RuntimeError("unavailable")

    monkeypatch.setattr(capture, "verify_previous", unavailable)
    capture.capture()
    result = json.loads((tmp_path / review.ACQUISITION).read_bytes())
    assert result["kind"] == "d5g-governed-prospectus-acquisition"
    assert result["status"] == "blocked"
    assert result["originalRowsPreserved"] is None
    assert result["groups"] == []


def test_changed_registration_inventory_never_establishes_current_coverage(monkeypatch):
    original = review.registration_roster
    calls = 0

    def changed(document):
        nonlocal calls
        calls += 1
        rows = original(document)
        if calls == 2:
            rows[0] = {**rows[0], "resourceKey": "changed-edition"}
        return rows

    monkeypatch.setattr(review, "registration_roster", changed)
    result = review.review()
    assert result["registrationRosterMatches"] is False
    assert "current_inventory_incomplete" in result["candidateBatch"]["reasonCodes"]
    assert "seven" not in result["nextStep"]
