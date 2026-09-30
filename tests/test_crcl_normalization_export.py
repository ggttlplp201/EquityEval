"""Saved real audit projection; no app database or upstream requests."""

import json

import pytest

from scripts import export_crcl_normalization as export


def test_exact_checked_projection_is_reproducible_and_keeps_history_separate():
    files = export.generated()
    assert files == export.generated()
    view = json.loads(files[export.OUTPUT])
    provenance = json.loads(files[export.PROVENANCE_AUDIT])
    assert len(provenance["details"]["as_filed:revenue"]["source_chain_capture_ids"]) == 3
    assert provenance["details"]["before_filing:revenue"]["source_chain_capture_ids"] == []
    assert "value_source_capture_ids" not in files[export.PROVENANCE_AUDIT]
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


@pytest.mark.parametrize("mode", ["as_filed", "original"])
def test_value_provenance_excludes_amendment_and_quarter(mode):
    view = json.loads(export.generated()[export.OUTPUT])
    for fact in view["views"][mode]["facts"]:
        detail = view["details"][fact["detailId"]]
        assert len(detail["sources"]) == 3
        assert [item["label"] for item in detail["sources"]] == [
            "Company Facts · selected observation",
            "Original 10-K · precision cross-check",
            "Submissions · filing metadata",
        ]
        assert len({item["transform"] for item in detail["sources"]}) == 3
        assert "reviewed S3 mapping → PIT selection" in detail["sources"][0]["transform"]
        assert all("reviewed S3 mapping" not in item["transform"] for item in detail["sources"][1:])
        assert [item["accession"] for item in detail["reviewContext"]] == [
            "0001876042-26-000228",
            "0001876042-26-000248",
        ]
        assert not {item["url"] for item in detail["sources"]} & {
            item["url"] for item in detail["reviewContext"]
        }
        assert all("PIT selection" not in item["transform"] for item in detail["reviewContext"])


def test_missing_selection_and_batch_details_do_not_claim_selected_value_provenance():
    view = json.loads(export.generated()[export.OUTPUT])
    for key in ("publication", "eligibility"):
        assert view["details"][key]["sources"] == []
        assert len(view["details"][key]["reviewContext"]) == 5
    for fact in view["views"]["before_filing"]["facts"]:
        detail = view["details"][fact["detailId"]]
        assert detail["sources"] == []
        assert detail["reviewContext"] == []
        text = json.dumps(detail)
        for future in (
            "2,746,642",
            "96,435",
            "2746642000",
            "96435000",
            "Original literal",
            "Scale",
            "Decimals",
            "c-1",
            "crcl-20251231.htm",
        ):
            assert future not in text
