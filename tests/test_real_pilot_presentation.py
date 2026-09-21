"""Real-source display must preserve exact evidence and fail closed on drift."""

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.export_real_pilot import build_crcl_observations, export

ROOT = Path(__file__).resolve().parents[1]


def test_crcl_amounts_match_hand_read_filing_literals_with_sign_and_scale():
    # CRCL 2025 10-K c-1/usd: 2,746,642 * 10^3 and -(96,435 * 10^3).
    result = build_crcl_observations(ROOT)
    amounts = {item["id"]: item for item in result["amounts"]}
    assert amounts["revenue"]["value"] == "2746642000"
    assert amounts["operating_income"]["value"] == "-96435000"
    assert amounts["operating_income"]["valueLabel"] == "$-96,435,000"
    assert all(
        item["statusLabel"] == "Observed · calculation eligibility blocked"
        for item in amounts.values()
    )
    assert result["observedFiling"]["filed"] == "2026-03-09"
    assert result["observedFiling"]["periodStart"] == "2025-01-01"
    assert result["observedFiling"]["periodEnd"] == "2025-12-31"
    assert result["observedFiling"]["capturedAt"] == "2026-09-11T14:27:04.146547+00:00"
    assert set(result["flags"]) >= {"inventory_history_incomplete", "event_history_incomplete"}


def test_source_details_keep_repetitions_original_sign_dates_and_both_hashes():
    result = build_crcl_observations(ROOT)
    for amount in result["amounts"]:
        detail = result["details"][amount["detailId"]]
        rows = {r["label"]: r["value"] for s in detail["sections"] for r in s["rows"]}
        assert rows["Context"] == "c-1"
        assert rows["Unit"] == "usd · iso4217:USD"
        assert rows["Decimals"] == "-3"
        assert rows["Scale"] == "3"
        assert len(detail["sources"]) == 2
        assert rows["Original filing SHA256"] == (
            "2708bc61b370372a3339229fe0d0977048e11faa7cfc59a4e2509a8082ae35be"
        )
        assert rows["Publication"] == "Offline normalization only; no published PIT selection"
        assert rows["Calculation eligibility"] == "Blocked"
        assert rows["Whole-document extraction"] == "Incomplete"
        assert rows["Extraction issue count"] == "249"
        assert rows["Capture completion timestamp"].startswith("Unknown")
        if amount["id"] == "operating_income":
            assert rows["Sign"] == "-"
            assert rows["Literal"] == "96,435"
        else:
            assert rows["Matching filing occurrences"] == "2"


def test_all_seven_stay_in_order_and_missing_metrics_never_become_zero():
    result = export(ROOT)
    assert result["kind"] == "real-source-pilot"
    assert [row["ticker"] for row in result["companies"]] == [
        "CRCL",
        "MSTR",
        "COIN",
        "HOOD",
        "USAR",
        "MP",
        "GOOGL",
    ]
    assert all(metric["value"] is None for row in result["companies"] for metric in row["metrics"])
    assert all(not row["amounts"] for row in result["companies"][1:])
    assert result["companies"][0]["filing"]["periodEnd"] != "2025-12-31"
    assert result["companies"][0]["observedFiling"]["periodEnd"] == "2025-12-31"
    for row in result["companies"]:
        assert set(row["history"]) == {"3", "5", "10"}
        assert all("0 eligible" in window["coverageLabel"] for window in row["history"].values())


def test_shipped_artifact_is_reproducible_and_contains_no_demo_financials():
    import json

    expected = export(ROOT)
    shipped = json.loads((ROOT / "apps/web/src/features/pilot/evidence.json").read_text())
    assert shipped == expected
    assert "fictional" not in shipped
    assert len(shipped["details"]) == 2


def test_tampered_archive_is_rejected_before_display(tmp_path):
    import json
    import shutil

    destination = tmp_path / "docs/research/s1/evidence"
    shutil.copytree(ROOT / "docs/research/s1/evidence", destination)
    manifest = json.loads((destination / "filing-manifest.json").read_text())
    selected = next(row for row in manifest["requests"] if row["id"] == "CRCL-filing")
    (destination / selected["raw_file"]).write_bytes(b"not a gzip archive")
    with pytest.raises(Exception, match="missing or corrupt"):
        build_crcl_observations(tmp_path)


def test_incorrect_source_scope_or_filing_selection_blocks_amount(monkeypatch):
    from dataclasses import replace

    import scripts.export_real_pilot as module

    original = module.select_filing_fact

    def changed(*args, **kwargs):
        return replace(original(*args, **kwargs), value=None, status="unsupported")

    monkeypatch.setattr(module, "select_filing_fact", changed)
    result = build_crcl_observations(ROOT)
    assert all(row["value"] is None for row in result["amounts"])
    assert "original_filing_crosscheck_failed" in result["flags"]


def test_bad_issuer_catalog_is_rejected_before_join(monkeypatch):
    import scripts.export_real_pilot as module

    original = module.load_catalog

    def wrong(root):
        result = deepcopy(original(root))
        result["companies"][0]["cik"] = "0001652044"
        return result

    monkeypatch.setattr(module, "load_catalog", wrong)
    with pytest.raises(ValueError, match="identity"):
        export(ROOT)
