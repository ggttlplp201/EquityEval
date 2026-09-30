"""Presentation preserves evaluated results; it never reconstructs financial ratios."""

from copy import deepcopy
from decimal import Decimal

import pytest

from scripts.export_sector_explorer import (
    bar,
    distribution,
    export,
    focused_domain,
    history,
    scatter,
)


def evaluated(metric="pe", status="eligible", value="150"):
    return {
        "asOf": "2026-06-30",
        "metricId": metric,
        "method": "total",
        "sectorId": "fictional",
        "value": value,
        "status": status,
        "reasons": [],
        "N": 12,
        "K": 12,
        "V": 12,
        "issuerCoverage": "1",
        "capCoverage": "1",
        "marketCap": "1200",
        "numeratorTotal": "1200",
        "denominatorTotal": "8",
        "detailId": "frozen",
        "companies": [
            {
                "id": "one",
                "ticker": "FICT",
                "name": "Fictional",
                "value": "150",
                "status": "eligible",
                "reasons": [],
                "detailId": "frozen",
            }
        ],
        "distribution": {
            "bins": [
                {"id": "bin", "lower": "100", "upper": "200", "count": 1, "companyIds": ["one"]}
            ],
            "p25": "150",
            "p50": "150",
            "p75": "150",
            "excluded": [],
        },
    }


def raw_bundle():
    return {
        "fictional": True,
        "context": {"asOfDates": ["2026-06-30"], "membershipMode": "Current members’ history"},
        "sectors": [{"id": "fictional", "label": "Fictional", "color": "#217a69"}],
        "metrics": [
            {"id": "pe", "label": "P/E", "definition": "Matching totals", "unit": "multiple"}
        ],
        "methods": [{"id": "total", "label": "Sector total", "definition": "Matching totals"}],
        "evaluations": [evaluated(), evaluated("revenue_growth", value="0.1")],
        "history": [
            dict(evaluated(), asOf="2025-12-31"),
            dict(evaluated(status="missing", value=None), asOf="2026-03-31"),
            evaluated(),
        ],
        "market": [evaluated()],
        "details": {
            "frozen": {
                "title": "Fictional",
                "subtitle": "Snapshot",
                "sections": [{"heading": "Inputs", "rows": [{"label": "Value", "value": "150"}]}],
                "sources": [
                    {
                        "label": "Synthetic",
                        "capturedAt": "2026-06-30",
                        "transform": "fixture",
                        "licence": "Fictional",
                    }
                ],
            }
        },
    }


def test_snapshot_values_and_lineage_pass_through_without_ratio_recalculation():
    raw = raw_bundle()
    before = deepcopy(raw)
    result = export(raw)
    row = result["views"]["2026-06-30|pe|total"]["rows"][0]
    assert row["value"] == "150"  # Already evaluated, not 1200 / 8 reimplemented here.
    assert row["valueLabel"] == "150.00×"
    assert row["detailId"] == "frozen"
    assert row["countsLabel"] == "N 12 · K 12 · V 12"
    assert raw == before


def test_missing_or_nm_value_is_not_a_zero_length_bar():
    assert bar(None, (Decimal(0), Decimal(200))) is None
    assert bar("0", (Decimal(0), Decimal(200))) == {"left": 0.0, "width": 0.0, "endpoint": 0.0}
    data = raw_bundle()
    data["evaluations"][0].update(value=None, status="nm")
    row = export(data)["views"]["2026-06-30|pe|total"]["rows"][0]
    assert row["valueLabel"] == "N/M" and row["bar"] is None


def test_limited_values_remain_visible_but_never_enter_scatter():
    data = raw_bundle()
    data["evaluations"][0]["status"] = "limited"
    result = export(data)["views"]["2026-06-30|pe|total"]
    assert result["rows"][0]["valueLabel"] == "150.00×"
    assert result["rows"][0]["bar"] is not None
    assert result["scatter"]["points"] == []
    assert result["scatter"]["unavailable"][0]["reason"] == "Limited coverage"


def test_history_paths_end_at_missing_observations():
    result = history(raw_bundle(), "2026-06-30", "pe", "total", "multiple", 1)
    series = result["series"][0]
    scale = result["scales"]["fictional"]
    assert scale["yBySector"]["fictional"][1] is None
    assert series["segments"] == [[0], [2]]


def test_history_selection_scales_share_one_exact_domain_without_rounded_label_loss():
    data = raw_bundle()
    data["sectors"].append({"id": "other", "label": "Other", "color": "#999999"})
    exact = ["6.7741", "6.7749"]
    data["history"] = [
        dict(evaluated(value=exact[0]), asOf="2025-12-31", sectorId="fictional"),
        dict(evaluated(value=exact[1]), asOf="2026-06-30", sectorId="fictional"),
        dict(evaluated(value="10"), asOf="2025-12-31", sectorId="other"),
        dict(evaluated(value="11"), asOf="2026-06-30", sectorId="other"),
    ]
    result = history(data, "2026-06-30", "pe", "total", "multiple", 1)

    focused = result["scales"]["fictional"]
    assert focused["yBySector"]["fictional"][0] != focused["yBySector"]["fictional"][1]
    assert [point["valueLabel"] for point in result["series"][0]["points"]] == ["6.77×", "6.77×"]

    shared = result["scales"]["fictional|other"]
    fictional_y = shared["yBySector"]["fictional"]
    other_y = shared["yBySector"]["other"]
    assert min(fictional_y) > max(other_y)
    assert "other|fictional" not in result["scales"]


def test_history_constant_percentage_scale_uses_percentage_sized_padding():
    data = raw_bundle()
    data["metrics"] = [
        {
            "id": "profit_breadth",
            "label": "Profit breadth",
            "definition": "Fictional",
            "unit": "fraction",
        }
    ]
    data["history"] = [
        dict(evaluated(metric="profit_breadth", value="0.9167"), asOf="2025-12-31"),
        dict(evaluated(metric="profit_breadth", value="0.9167"), asOf="2026-06-30"),
    ]
    result = history(data, "2026-06-30", "profit_breadth", "total", "fraction", 1)
    labels = [tick["label"] for tick in result["scales"]["fictional"]["yAxis"]["ticks"]]
    assert labels[0].endswith("%") and labels[-1].endswith("%")
    assert float(labels[0][:-1]) > 80
    assert float(labels[-1][:-1]) < 100


def test_history_negative_domain_keeps_sign_and_observed_range_visible():
    low, high = focused_domain([Decimal("-0.20"), Decimal("-0.10")], "fraction")
    assert low < Decimal("-0.20")
    assert Decimal("-0.10") < high < 0


def test_distribution_uses_supplied_bins_and_company_memberships():
    result = distribution(evaluated(), "multiple")
    assert result["bins"][0]["companyIds"] == ["one"]
    assert result["bins"][0]["countLabel"] == "1"
    assert result["markers"][1]["valueLabel"] == "150.00×"
    assert result["companies"][0]["detailId"] == "frozen"
    assert result["companies"][0]["position"] is not None


def test_scatter_axes_use_same_method_and_frozen_values():
    result = scatter(raw_bundle(), "2026-06-30", "total")
    assert result["points"][0]["xLabel"] == "150.00×"
    assert result["points"][0]["yLabel"] == "10.00%"
    assert "Sector total" in result["xLabel"] and "Sector total" in result["yLabel"]


def test_unmarked_fixture_or_missing_source_details_is_rejected():
    data = raw_bundle()
    data["fictional"] = False
    with pytest.raises(ValueError, match="fictional"):
        export(data)
    data["fictional"] = True
    data["details"] = {}
    with pytest.raises(ValueError, match="source detail"):
        export(data)


def test_single_value_distribution_has_visible_bar_and_no_invented_interval():
    raw = evaluated()
    raw["distribution"]["bins"][0].update(lower="150", upper="150", count=12)
    result = distribution(raw, "multiple")
    assert result["bins"][0]["width"] == 24
    assert result["bins"][0]["height"] > 0
    assert result["bins"][0]["label"] == "150.00× (single value)"
    assert result["bins"][0]["countLabel"] == "12"
