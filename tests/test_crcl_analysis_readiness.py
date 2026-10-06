"""D5b projects reviewed D5a evidence without calculating a financial result."""

import copy
import json

import pytest

from scripts import export_crcl_analysis_readiness as export


def source_documents() -> tuple[dict, dict]:
    normalization = json.loads((export.ROOT / export.NORMALIZATION).read_text())
    provenance = json.loads((export.ROOT / export.PROVENANCE).read_text())
    return normalization, provenance


def test_projection_retains_two_inputs_and_publishes_zero_metrics():
    normalization, provenance = source_documents()
    result = export.project(normalization, provenance)

    assert result["kind"] == "real-crcl-analysis-readiness"
    assert result["sourceInputCount"] == 2
    assert result["publishedMetricCount"] == 0
    assert [row["exactValue"] for row in result["inputs"]] == [
        "2746642000",
        "-96435000",
    ]
    assert all(row["analysisValue"] is None for row in result["inputs"])
    assert set(result["details"]) == {"as_filed:revenue", "as_filed:operating_income"}
    assert all(result["details"][row["detailId"]]["sources"] for row in result["inputs"])
    assert result["candidateMetric"]["id"] == "operating_margin"
    assert result["candidateMetric"]["value"] is None
    assert result["candidateMetric"]["formula"] == "Operating income ÷ revenue"
    assert result["candidateMetric"]["status"] == "blocked"
    assert result["candidateMetric"]["reasonCodes"] == [
        "inventory_history_incomplete",
        "event_history_incomplete",
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        "signed_value",
        "fact_roster",
        "eligibility",
        "history_flag",
        "source_chain",
        "batch",
    ],
)
def test_projection_fails_closed_when_reviewed_evidence_changes(mutation):
    normalization, provenance = source_documents()
    normalization = copy.deepcopy(normalization)
    provenance = copy.deepcopy(provenance)

    if mutation == "signed_value":
        normalization["views"]["as_filed"]["facts"][1]["value"] = "96435000"
    elif mutation == "fact_roster":
        normalization["views"]["as_filed"]["facts"].pop()
    elif mutation == "eligibility":
        rows = normalization["details"]["as_filed:revenue"]["sections"][0]["rows"]
        next(row for row in rows if row["label"] == "Eligible for valuation")["value"] = "True"
    elif mutation == "history_flag":
        rows = normalization["details"]["eligibility"]["sections"][0]["rows"]
        rows.pop()
    elif mutation == "source_chain":
        provenance["details"]["as_filed:revenue"]["source_chain_capture_ids"].pop()
    elif mutation == "batch":
        normalization["batchId"] = "changed"

    with pytest.raises(ValueError):
        export.project(normalization, provenance)


def test_generated_artifact_is_reproducible_and_checked():
    files = export.generated()
    assert files == export.generated()
    result = json.loads(files[export.OUTPUT])
    assert result["publishedMetricCount"] == 0
    assert "0.035" not in files[export.OUTPUT]
    assert "-3.5%" not in files[export.OUTPUT]
    assert export.MANIFEST in files
