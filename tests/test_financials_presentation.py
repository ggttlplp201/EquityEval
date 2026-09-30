"""S8c source-copy oracles: no aggregation or invented financial statements."""

import copy
import json

import pytest

from scripts.export_financials import OUTPUT, RECIPE, build, encoded, validate_recipe


def recipe():
    return json.loads(RECIPE.read_text())


def test_deterministic_export_and_exact_source_strings():
    result = build()
    assert encoded(result) == OUTPUT.read_bytes()
    assert result == build()
    annual = result["snapshots"][0]
    assert annual["statements"][0]["rows"][0]["value"] == "100.1234567"
    assert annual["statements"][1]["period"]["period_kind"] == "instant"
    assert annual["statements"][1]["period"]["start_date"] is None
    assert annual["statements"][0]["period"]["period_kind"] == "duration"
    assert all(s["basis"] != "ttm" for s in result["snapshots"])


def test_missing_is_null_and_coverage_is_selected_lines_only():
    for snapshot in build()["snapshots"]:
        cash = snapshot["statements"][2]
        assert cash["rows"][-1]["value"] is None
        assert cash["rows"][-1]["status"] == "missing"
        assert cash["coverage"] == {"available": 2, "requested": 3, "scope": "selected_lines"}
        assert cash["rows"][-1]["quality_flags"] == ["source_not_supplied"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("basis", "ttm"),
        ("period_start", "2025-07-01"),
        ("filed_on", "2024-01-01"),
        ("retrieved_at", "2025-01-01T00:00:00Z"),
        ("known_on", "2027-01-01"),
        ("currency", "EUR"),
        ("scale", "1000"),
    ],
)
def test_rejects_incompatible_periods_units_and_dates(field, value):
    data = recipe()
    data["editions"][0][field] = value
    with pytest.raises(ValueError):
        validate_recipe(data)


@pytest.mark.parametrize(
    "mutation", ["nan", "unknown", "duplicate", "scope", "missing", "restatement"]
)
def test_rejects_ambiguous_or_invalid_source_rows(mutation):
    data = recipe()
    first = data["editions"][0]
    if mutation == "nan":
        first["values"]["revenue"] = "NaN"
    if mutation == "unknown":
        first["values"]["invented_concept"] = "12"
    if mutation == "duplicate":
        data["editions"].append(copy.deepcopy(first))
    if mutation == "scope":
        first["scope"] = "segment"
    if mutation == "missing":
        del first["values"]["revenue"]
    if mutation == "restatement":
        data["editions"][1]["supersedes"] = "quarter"
    with pytest.raises(ValueError):
        validate_recipe(data)


def test_snapshot_and_source_identity_change_with_source_content():
    data = recipe()
    before = build(data)
    data["editions"][0]["values"]["revenue"] = "101.1234567"
    after = build(data)
    assert before["snapshots"][0]["snapshot_id"] != after["snapshots"][0]["snapshot_id"]
    assert (
        before["snapshots"][0]["statements"][0]["rows"][0]["evidence"]["source_hash"]
        != after["snapshots"][0]["statements"][0]["rows"][0]["evidence"]["source_hash"]
    )


def test_revised_edition_links_exact_prior_evidence_without_future_leak():
    original, revised, quarter = build()["snapshots"]
    old = original["statements"][0]["rows"][0]
    new = revised["statements"][0]["rows"][0]
    assert new["value"] == "102.9876543"
    assert new["evidence"]["prior_evidence_id"] == old["evidence"]["evidence_id"]
    assert new["evidence"]["restatement_status"] == "restated"
    assert "102.9876543" not in json.dumps(original)
    assert quarter["statements"][0]["period"]["start_date"] == "2026-01-01"
    assert quarter["statements"][0]["period"]["end_date"] == "2026-03-31"


@pytest.mark.parametrize("original,revised", [("40", "40.0"), ("0", "-0.00")])
def test_formatting_only_edits_preserve_exact_evidence_without_false_restatement(original, revised):
    data = recipe()
    data["editions"][0]["values"]["gross_profit"] = original
    data["editions"][1]["values"]["gross_profit"] = revised
    snapshots = build(data)["snapshots"]
    row = snapshots[1]["statements"][0]["rows"][1]
    assert row["evidence"]["restatement_status"] == "repeated"
    assert row["value"] == revised
    assert row["evidence"]["prior_value"] == original


def test_all_values_link_to_the_exact_fixture_pointer_period_unit_and_snapshot():
    data = recipe()
    for edition, saved in zip(data["editions"], build()["snapshots"], strict=True):
        assert saved["scope"] == "consolidated"
        for statement in saved["statements"]:
            for row in statement["rows"]:
                evidence = row["evidence"]
                pointer = evidence["source_locator"].split("#", 1)[1]
                target = data
                for key in pointer.strip("/").split("/"):
                    target = target[int(key)] if isinstance(target, list) else target[key]
                assert target == row["value"] == evidence["original_numeric_text"]
                assert evidence["source_hash"] == saved["input_hash"]
                assert evidence["source_id"] == saved["source_id"]
                assert evidence["period"] == statement["period"]
                assert evidence["unit"]["unit_key"] == "USD"
                assert evidence["scale"] == "1"
                assert evidence["statement"] == statement["family"]
                assert evidence["known_on"] == edition["known_on"]
