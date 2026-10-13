import pytest

from scripts import review_crcl_registration as review


def test_pinned_registration_scope_obeys_bootstrap_cap_and_cannot_expand():
    rows = review.plan()
    groups = review.groups(rows)
    assert [len(group) for group in groups] == [5, 2]
    assert tuple(key for group in groups for key in group) == review.KEYS
    for changed in (rows[:-1], rows + rows[:1], list(reversed(rows))):
        with pytest.raises(ValueError):
            review.groups(changed)


def test_two_completed_groups_are_verified_without_rewriting_original_summary():
    import copy
    import json

    saved = json.loads((review.ROOT / review.ACQUISITION).read_bytes())
    assert saved["status"] == "incomplete"  # Immutable original one-group summary bug.
    assert review.acquisition_complete(saved) is True
    for changed in (copy.deepcopy(saved), copy.deepcopy(saved)):
        changed["groups"][-1]["captures"].pop()
        assert review.acquisition_complete(changed) is False
    changed = copy.deepcopy(saved)
    changed["groups"][0]["result"]["gaps"] = ["missing"]
    assert review.acquisition_complete(changed) is False


def test_complete_statement_checks_reject_plausible_wrong_period_unit_or_sign():
    from scripts.review_crcl_prospectus import ANNUAL_HEADER, ANNUAL_VALUES

    text = (
        ANNUAL_HEADER + " Total revenue and reserve income from continuing operations "
        "1,676,253 1,450,466 772,052 "
        "Operating income (loss) from continuing operations 167,158 269,528 (38,116)"
    )
    assert len(review.annual_rows(text)) == len(ANNUAL_VALUES)
    for before, after in [
        ("2024 2023", "2023 2024"),
        ("thousands", "millions"),
        ("167,158", "(167,158)"),
    ]:
        with pytest.raises(ValueError):
            review.annual_rows(text.replace(before, after))


def test_saved_review_checks_all_bodies_editions_and_keeps_metric_absent():
    result = review.review()
    assert len(result["documents"]) == 7
    assert all(d["status"] == "reviewed" for d in result["documents"])
    assert len(result["periodicComparisons"]) == 18
    assert len(result["q1FactsVintages"]) == 15
    assert result["candidateBatch"]["status"] == "blocked"
    assert result["candidateBatch"]["reasonCodes"] == [
        "inventory_observation_precedes_evidence_cutoff"
    ]
    assert result["operatingMargin"] is None
    assert result["candidateBatch"]["batchId"] is None


def test_absent_or_partial_registration_body_never_clears_preparation():
    import json

    saved = json.loads((review.ROOT / review.ACQUISITION).read_bytes())
    saved["groups"][-1]["captures"].pop()
    for acquisition in (None, saved):
        result = review.review_acquisition(acquisition)
        assert result["candidateBatch"]["status"] == "blocked"
        assert "registration_body_unreviewed" in result["candidateBatch"]["reasonCodes"]
        assert "incomplete" in result["conclusion"]
        assert result["operatingMargin"] is None


def test_changed_registration_capture_is_not_a_reviewed_body():
    import copy
    import json

    from equity_ingest.archive import ArchiveError

    saved = json.loads((review.ROOT / review.ACQUISITION).read_bytes())
    for mutation in ("hash", "duplicate", "time", "scope"):
        changed = copy.deepcopy(saved)
        captures = changed["groups"][0]["captures"]
        if mutation == "hash":
            captures[-1]["body_sha256"] = "0" * 64
        if mutation == "duplicate":
            captures.append(captures[-1])
        if mutation == "time":
            captures[-1]["completed_at"] = "2026-09-21T00:00:00+00:00"
        if mutation == "scope":
            captures[-1]["source_object_key"] = review.KEYS[-1]
        with pytest.raises((ValueError, ArchiveError)):
            review.review_acquisition(changed)


def test_missing_runtime_stays_blocked_without_claiming_preservation(tmp_path, monkeypatch):
    import json

    from scripts import capture_crcl_registration as capture

    monkeypatch.setattr(capture, "ROOT", tmp_path)
    (tmp_path / "docs/research").mkdir(parents=True)

    def unavailable():
        raise RuntimeError("unavailable")

    monkeypatch.setattr(capture, "verify_previous", unavailable)
    capture.capture()
    result = json.loads((tmp_path / review.ACQUISITION).read_bytes())
    assert result["status"] == "blocked"
    assert result["originalRowsPreserved"] is None
    assert not review.acquisition_complete(result)


def test_every_periodic_comparison_resolves_to_filing_provenance():
    result = review.review()
    sources = {
        s["captureId"]: s for s in result["details"]["comparisons"]["sources"] if "captureId" in s
    }
    for comparison in result["periodicComparisons"]:
        source = sources[comparison["captureId"]]
        assert source["accession"]
        assert source["url"].startswith("https://www.sec.gov/Archives/")
        assert source["capturedAt"]
        assert source["sha256"] == comparison["sha256"]


def test_date_equality_does_not_erase_inventory_observation_gap():
    scope = review.time_scope("2026-10-13T22:27:06+00:00", "2026-10-13T22:27:07+00:00")
    assert scope["state"] == "blocked"
    assert scope["fullDayCoverage"] is False
    assert review.time_scope(None, None)["state"] == "blocked"
    assert (
        review.time_scope("2026-10-13T22:27:07+00:00", "2026-10-13T22:27:07+00:00")["state"]
        == "observation_covers_retained_evidence"
    )


def test_export_rejects_changed_or_promoted_evidence():
    import copy
    import json

    import pytest

    from scripts.export_crcl_registration import project

    saved = json.loads((review.ROOT / review.REPORT).read_text())
    assert project(saved) == saved
    for field, value in [("operatingMargin", "0.1"), ("conclusion", "safe")]:
        changed = copy.deepcopy(saved)
        changed[field] = value
        with pytest.raises(ValueError):
            project(changed)


def test_next_step_names_both_mandatory_resources():
    requirement = review.time_scope(None, None)["requirement"]
    assert "company_facts/0001876042" in requirement
    assert "submissions/0001876042" in requirement
    assert "both captured after all retained bodies" in requirement
