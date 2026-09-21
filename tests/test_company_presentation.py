"""Company presentation preserves frozen company evidence and real history gaps."""

from copy import deepcopy

import pytest

from scripts.export_company_fundamentals import export


def raw_bundle():
    details, evaluations = {}, []
    for as_of, pe in (("2026-03-31", "140"), ("2026-06-30", "150")):
        detail_id = f"company|{as_of}|one"
        snapshot_id = "snapshot-" + as_of
        details[detail_id] = {
            "title": "Fictional one",
            "subtitle": "Fictional evidence only",
            "sections": [
                {
                    "heading": "Fictional company snapshot",
                    "rows": [
                        {"label": "Issuer", "value": "one"},
                        {"label": "Snapshot ID", "value": snapshot_id},
                        {"label": "Context", "value": "fixed-context"},
                    ],
                },
                {
                    "heading": "TTM revenue",
                    "rows": [
                        {"label": "Value (USD)", "value": "1000"},
                        {"label": "Absolute source uncertainty", "value": "2"},
                        {"label": "Basis", "value": "consolidated_flow"},
                        {"label": "Period", "value": "2025-07-01 to 2026-06-30"},
                        {"label": "Input manifest SHA256", "value": "revenue-input-hash"},
                        {"label": "Flags", "value": "None"},
                    ],
                },
                {
                    "heading": "Shared company calculations",
                    "rows": [
                        {
                            "label": "pe",
                            "value": f"{pe}; flags=None; result=result-hash; operands=cap, income",
                        }
                    ],
                },
            ],
            "sources": [
                {
                    "label": "Synthetic",
                    "capturedAt": as_of,
                    "transform": "existing core",
                    "licence": "Fictional",
                }
            ],
        }
        evaluations.append(
            {
                "asOf": as_of,
                "metricId": "pe",
                "method": "total",
                "sectorId": "fictional",
                "companies": [
                    {
                        "id": "one",
                        "ticker": "DEMO-ONE",
                        "name": "Fictional one",
                        "value": pe,
                        "status": "eligible",
                        "reasons": [],
                        "detailId": detail_id,
                        "snapshotId": snapshot_id,
                    }
                ],
            }
        )
    return {
        "fictional": True,
        "context": {
            "asOfDates": ["2026-06-30", "2026-03-31"],
            "defaultAsOf": "2026-06-30",
            "sourceSnapshotId": "original-source-snapshot",
            "membershipMode": "Current fictional members backcast; survivorship bias",
        },
        "metrics": [
            {"id": "pe", "label": "P/E", "unit": "multiple", "definition": "Cap/common income"}
        ],
        "sectors": [{"id": "fictional", "label": "Fictional"}],
        "evaluations": evaluations,
        "details": details,
    }


def test_values_snapshots_and_evidence_are_passed_through():
    raw = raw_bundle()
    before = deepcopy(raw)
    bundle = export(raw)
    view = bundle["views"]["2026-06-30|one"]
    assert view["snapshotId"] == "snapshot-2026-06-30"
    assert view["detailId"] == "company|2026-06-30|one"
    assert view["metrics"][0]["value"] == "150"
    assert view["metrics"][0]["valueLabel"] == "150.00×"
    assert view["amounts"][0]["valueLabel"] == "$1,000.00"
    assert view["amounts"][0]["inputHash"] == "revenue-input-hash"
    assert bundle["context"]["sourceSnapshotId"] == "original-source-snapshot"
    assert bundle["details"] == raw["details"]
    assert raw == before


def test_long_windows_are_explicitly_partial_and_have_no_fabricated_points():
    history = export(raw_bundle())["views"]["2026-06-30|one"]["history"]
    for years, quarters in (("3", 12), ("5", 20), ("10", 40)):
        window = history[years]
        chart = window["charts"]["pe"]
        assert window["windowStart"] == f"{2026 - int(years)}-06-30"
        assert window["windowEnd"] == "2026-06-30"
        assert len(window["missingDates"]) == quarters - 2
        assert window["coverageLabel"] == f"2 of {quarters} quarter-end snapshots available"
        assert [point["date"] for point in chart["points"]] == ["2026-03-31", "2026-06-30"]
        assert len(chart["paths"]) == 1
        assert chart["points"][0]["detailId"] == "company|2026-03-31|one"
    earlier = export(raw_bundle())["views"]["2026-03-31|one"]["history"]["3"]
    assert [point["date"] for point in earlier["charts"]["pe"]["points"]] == ["2026-03-31"]


def test_unavailable_metric_keeps_sources_and_never_becomes_zero():
    raw = raw_bundle()
    raw["evaluations"][1]["companies"][0].update(
        value=None, status="unsupported", reasons=["unsupported_profile"]
    )
    view = export(raw)["views"]["2026-06-30|one"]
    metric = view["metrics"][0]
    assert metric["value"] is None and metric["valueLabel"] == "—"
    assert metric["status"] == "unsupported"
    assert metric["detailId"] == view["detailId"]
    assert view["amounts"][0]["value"] == "1000"
    chart = view["history"]["3"]["charts"]["pe"]
    assert chart["points"][1]["y"] is None
    assert chart["unavailableDates"] == ["2026-06-30"]
    assert all("L" not in path for path in chart["paths"])


def test_absent_company_metric_is_explicitly_missing_not_inferred_from_amounts():
    raw = raw_bundle()
    raw["metrics"].append(
        {"id": "ps", "label": "P/S", "unit": "multiple", "definition": "Cap/revenue"}
    )
    view = export(raw)["views"]["2026-06-30|one"]
    metric = next(metric for metric in view["metrics"] if metric["id"] == "ps")
    assert metric["value"] is None and metric["status"] == "missing"
    assert metric["reasonCodes"] == ["company_metric_not_supplied"]


def test_duplicate_sector_projections_must_agree():
    raw = raw_bundle()
    duplicate = deepcopy(raw["evaluations"][0])
    duplicate["method"] = "median"
    raw["evaluations"].append(duplicate)
    assert len(export(raw)["companies"]) == 1
    duplicate["companies"][0]["value"] = "999"
    with pytest.raises(ValueError, match="Conflicting company"):
        export(raw)


@pytest.mark.parametrize("failure", ["fictional", "source", "snapshot", "calculation"])
def test_missing_or_inconsistent_evidence_fails_closed(failure):
    raw = raw_bundle()
    detail = raw["details"]["company|2026-06-30|one"]
    if failure == "fictional":
        raw["fictional"] = False
    elif failure == "source":
        detail["sources"] = []
    elif failure == "snapshot":
        detail["sections"][0]["rows"][1]["value"] = "wrong-snapshot"
    else:
        detail["sections"][-1]["rows"][0]["value"] = "999; flags=None; result=r; operands=c, i"
    with pytest.raises(ValueError):
        export(raw)


def test_history_does_not_connect_over_absent_quarter():
    raw = raw_bundle()
    raw["evaluations"][0]["asOf"] = "2025-12-31"
    row = raw["evaluations"][0]["companies"][0]
    previous_id = row["detailId"]
    row["detailId"] = "company|2025-12-31|one"
    row["snapshotId"] = "snapshot-2025-12-31"
    detail = raw["details"].pop(previous_id)
    detail["sources"][0]["capturedAt"] = "2025-12-31"
    detail["sections"][0]["rows"][1]["value"] = row["snapshotId"]
    raw["details"][row["detailId"]] = detail
    chart = export(raw)["views"]["2026-06-30|one"]["history"]["3"]["charts"]["pe"]
    assert len(chart["paths"]) == 2
    assert all("L" not in path for path in chart["paths"])


def test_shipped_company_projection_matches_every_existing_sector_company_value():
    import gzip
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sector = json.loads(
        gzip.decompress((root / "apps/web/src/features/sectors/fixture.json.gz").read_bytes())
    )
    company = json.loads(
        gzip.decompress((root / "apps/web/src/features/company/fixture.json.gz").read_bytes())
    )
    expected_ids = {key for key in sector["details"] if key.startswith("company|")}
    assert set(company["details"]) == expected_ids
    assert company["context"]["sourceSnapshotId"] == sector["context"]["sourceSnapshotId"]
    assert all(company["details"][key] == sector["details"][key] for key in expected_ids)
    checked = set()
    for view in sector["views"].values():
        metric_id = {"revenue_growth": "revenue_yoy"}.get(view["metricId"], view["metricId"])
        if metric_id not in {metric["id"] for metric in company["metrics"]}:
            continue
        for distribution in view["distributions"].values():
            for row in distribution["companies"]:
                company_view = company["views"][view["asOf"] + "|" + row["id"]]
                metric = next(item for item in company_view["metrics"] if item["id"] == metric_id)
                assert (metric["value"], metric["status"], metric["detailId"]) == (
                    row["value"],
                    row["status"],
                    row["detailId"],
                )
                assert company_view["snapshotId"] == row["snapshotId"]
                checked.add((view["asOf"], row["id"], metric_id))
    assert len(checked) == 168 * 6


def test_observation_cannot_relabel_later_snapshot_as_earlier_date():
    raw = raw_bundle()
    raw["evaluations"][1]["asOf"] = "2025-12-31"
    with pytest.raises(ValueError, match="date"):
        export(raw)


def test_non_quarter_observation_cannot_inflate_quarter_coverage():
    raw = raw_bundle()
    raw["evaluations"][1]["asOf"] = "2026-06-29"
    row = raw["evaluations"][1]["companies"][0]
    old_id = row["detailId"]
    row["detailId"] = "company|2026-06-29|one"
    raw["details"][row["detailId"]] = raw["details"].pop(old_id)
    with pytest.raises(ValueError, match="quarter"):
        export(raw)
