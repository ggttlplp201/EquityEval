import pytest

from scripts import prepare_crcl_current as subject


def test_observation_gap_blocks_preparation_without_changing_historical_flags():
    from scripts.normalize_crcl import load_preparation

    old, _ = load_preparation()
    with pytest.raises(ValueError):
        subject.prepare()
    result = subject.generated()
    assert result["status"] == "blocked"
    assert result["inputHash"] is None and result["outputHash"] is None
    assert result["batchId"] is None
    assert result["reasonCodes"] == ["inventory_observation_precedes_evidence_cutoff"]
    assert old.original_history_complete is False
    assert {f.rule_key for f in old.quality_flags} == {
        "inventory_history_incomplete",
        "event_history_incomplete",
    }


def test_incomplete_registration_review_cannot_prepare(monkeypatch):
    monkeypatch.setattr(subject, "review", lambda root: {"candidateBatch": {"status": "blocked"}})
    with pytest.raises(ValueError):
        subject.prepare()
