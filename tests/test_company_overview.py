"""Metadata compatibility must fail closed without altering saved finance."""

from copy import deepcopy

import pytest

from scripts.export_company_overview import FIELDS, build, classify, encoded


def identity():
    return {field: "exact-same-evidence" for field in FIELDS}


def test_exact_affirmative_match_only():
    item = identity()
    assert classify(item, item) == ("compatible", [])
    assert classify(item, None) == ("unavailable", ["destination_missing"])


@pytest.mark.parametrize("field", FIELDS)
def test_each_dimension_is_required_and_exact(field):
    left, right = identity(), identity()
    right[field] = "other"
    assert classify(left, right) == ("separate", [f"{field}: mismatch"])
    left[field] = right[field] = None
    assert classify(left, right) == ("separate", [f"{field}: proof unavailable"])


def test_checked_manifest_preserves_separate_identities_and_hashes():
    manifest = build()
    assert len(manifest["entries"]) == 168
    assert len(manifest["files"]) == 4
    entry = next(iter(manifest["entries"].values()))
    assert entry["cards"][0]["status"] == "ready"
    assert all(card["status"] == "separate" for card in entry["cards"][1:])
    assert all("?" not in card["href"] for card in entry["cards"][1:])
    assert entry["identity"]["security_id"] is None
    assert entry["identity"]["retrieved_at"] is None
    assert manifest["destinations"]["valuation"]["declared"]["source_payload_hash"] == "c" * 64
    assert manifest["destinations"]["valuation"]["local_payload_sha256"] != "c" * 64
    assert encoded(manifest) == encoded(deepcopy(manifest))
    for descriptor in manifest["destinations"].values():
        assert "metrics" not in descriptor
        assert "statements" not in descriptor
        assert "price" not in descriptor


def test_absent_destination_is_unavailable_and_no_link(tmp_path):
    import shutil

    from scripts.export_company_overview import FEATURES, FILES

    for key, name in FILES.items():
        if key == "financials":
            continue
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FEATURES / name, path)
    result = build(tmp_path)
    for entry in result["entries"].values():
        card = next(c for c in entry["cards"] if c["id"] == "financials")
        assert card["status"] == "unavailable"
        assert card["href"] is None
        assert entry["counts"]["unavailable"] == 1


def test_incomplete_nested_lineage_never_matches():
    left = identity()
    left["lineage"] = {"snapshot": None}
    assert classify(left, left) == ("separate", ["lineage: proof unavailable"])
