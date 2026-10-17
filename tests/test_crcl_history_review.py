"""D050 incomplete retained history cannot become analysis eligibility."""

import copy
import json

import pytest

from scripts.capture_crcl_history import ACQUISITION
from scripts.review_crcl_history import review_acquisition


def test_missing_acquisition_has_exact_roster_and_no_eligibility():
    report = review_acquisition(None)
    assert len(report["bodies"]) == 47
    assert report["retainedBodyCount"] == 0
    assert report["eligibleForNormalization"] is False
    assert report["postBodyObservation"] is None
    assert all(row["value"] is None for row in report["metrics"])


def test_partial_acquisition_retains_actual_gaps_and_no_final_cutoff():
    acquisition = json.loads(ACQUISITION.read_text())
    report = review_acquisition(acquisition)
    assert report["retainedBodyCount"] == 46
    assert report["mimeCounts"] == {"text/html": 39, "application/pdf": 7}
    assert report["postBodyObservation"] is None
    assert "post_body_pair_not_captured" in report["blockers"]
    assert "ars_body_limit" in report["blockers"]
    assert report["eligibleForNormalization"] is False
    assert all(row["value"] is None for row in report["metrics"])
    assert all(row["accountingCleared"] is False for row in report["bodies"])
    assert report["mandatoryPairReview"]["submissionsMatchesPrior"] is True
    assert len(report["mandatoryPairReview"]["factsCaptures"]) == 10


def test_changed_retained_hash_and_false_complete_flag_cannot_clear():
    acquisition = json.loads(ACQUISITION.read_text())
    changed = copy.deepcopy(acquisition)
    changed["status"] = "captured_pending_review"
    changed["missingResources"] = []
    changed["groups"][0]["captures"][0]["body_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="pinned"):
        review_acquisition(changed)
