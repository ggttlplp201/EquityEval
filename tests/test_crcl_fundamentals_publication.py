"""Pinned real candidate and preservation checks before application writes."""

import pytest

from scripts.normalize_crcl import ROOT


def test_pinned_real_candidate_replays_existing_formula():
    from scripts.publish_crcl_fundamentals import checked_candidate

    manifest, payload = checked_candidate(ROOT)
    assert manifest.selector.captured_before.isoformat().startswith("2026-10-15T21:59:05.195192")
    assert next(m for m in payload.metrics if m.metric_id == "operating_margin").status == "valid"
    assert payload.coverage.counts["unsupported"] == 9


def test_changed_candidate_is_rejected(tmp_path):
    from scripts.publish_crcl_fundamentals import PREPARATION, checked_candidate

    target = tmp_path / PREPARATION
    target.parent.mkdir(parents=True)
    target.write_text((ROOT / PREPARATION).read_text().replace("2746642000", "2746642001"))
    with pytest.raises(ValueError):
        checked_candidate(tmp_path)


def test_preservation_rejects_old_row_changes_and_source_additions():
    from scripts.publish_crcl_fundamentals import verify_preserved

    before = {"source_captures": ["a"], "analysis_requests": ["b"]}
    verify_preserved(before, {"source_captures": ["a"], "analysis_requests": ["b", "c"]})
    with pytest.raises(ValueError):
        verify_preserved(before, {"source_captures": ["a", "c"], "analysis_requests": ["b"]})
    with pytest.raises(ValueError):
        verify_preserved(before, {"source_captures": ["a"], "analysis_requests": ["changed"]})


def test_each_unresolved_metric_names_exact_operands_and_applicability_requirement():
    from scripts.prepare_crcl_fundamentals import REQUIREMENTS

    assert set(REQUIREMENTS) == {
        "revenue_growth_yoy",
        "gross_margin",
        "gross_margin_derived",
        "net_margin_consolidated",
        "free_cash_flow_ppe",
        "free_cash_flow_margin_ppe",
        "current_ratio",
        "net_working_capital",
        "return_on_assets",
    }
    expected = {
        "revenue_growth_yoy": ("FY2024 total revenue", "reserve-income"),
        "gross_margin": ("gross profit", "distribution"),
        "gross_margin_derived": ("cost of revenue", "distribution"),
        "net_margin_consolidated": ("consolidated net income", "tax"),
        "free_cash_flow_ppe": ("operating cash flow", "PPE purchases", "token-holder"),
        "free_cash_flow_margin_ppe": ("operating cash flow", "PPE purchases", "total revenue"),
        "current_ratio": ("current assets", "current liabilities", "segregated"),
        "net_working_capital": ("current assets", "current liabilities", "segregated"),
        "return_on_assets": (
            "consolidated net income",
            "opening",
            "closing",
            "total assets",
            "reserve",
        ),
    }
    for metric, terms in expected.items():
        assert all(term in REQUIREMENTS[metric] for term in terms)
        assert "review" in REQUIREMENTS[metric]
