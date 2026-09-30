"""Saved real audit projection; no app database or upstream requests."""

import json

import pytest

from scripts import export_crcl_normalization as export


def test_exact_checked_projection_is_reproducible_and_keeps_history_separate():
    files = export.generated()
    assert files == export.generated()
    view = json.loads(files[export.OUTPUT])
    assert (view["factCount"], view["captureCount"], view["flagCount"]) == (2, 5, 2)
    assert [row["value"] for row in view["views"]["as_filed"]["facts"]] == [
        "2746642000",
        "-96435000",
    ]
    assert all(row["value"] is None for row in view["views"]["before_filing"]["facts"])
    assert view["views"]["original"]["facts"][0]["value"] == "2746642000"
    assert "blocking_quality_flag" in files[export.OUTPUT]
    assert "inventory_history_incomplete" in files[export.OUTPUT]
    assert "event_history_incomplete" in files[export.OUTPUT]
    for forbidden in ("blob_key", "gmail.com", "DATABASE_URL", "/Users/", "fictional-test"):
        assert forbidden not in files[export.OUTPUT]
    for value in view["views"].values():
        assert all(row["detailId"] in view["details"] for row in value["facts"])


def test_changed_audit_requires_review(tmp_path):
    path = tmp_path / export.AUDIT
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    with pytest.raises(ValueError, match="new review"):
        export.generated(tmp_path)


@pytest.mark.parametrize(
    "key,value",
    [("financial_result", True), ("exact_replay_verified", False), ("input_hash", "f" * 64)],
)
def test_failed_publication_is_not_presented_as_completed(key, value):
    audit = json.loads((export.ROOT / export.AUDIT).read_text())
    audit[key] = value
    with pytest.raises(ValueError):
        export.project(audit)
