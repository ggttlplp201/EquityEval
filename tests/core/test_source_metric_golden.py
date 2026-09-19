"""Archived normalization evidence projected into pure calculations.

These fixtures construct selection-shaped records from the reviewed normalization
bundle. They are not a replacement test of the database PIT reader or publication:
those already have separate real-database integration coverage.
"""

from decimal import Decimal

import pytest
from equity_core.inputs import FinancialInput
from equity_core.metrics import free_cash_flow, net_margin, reported_amount
from equity_ingest.financial_types import content_hash, evidence_id
from equity_ingest.sec_normalize import normalize_verified_bytes
from equity_schema.concepts import Concept
from equity_schema.pit import HistoryMode, PitQuery, SelectedFact, StatementSelection

from tests.core.metric_fixtures import operand
from tests.sec_normalization_seed import cohort_input


def project(bundle, concept):
    resolution = next(row for row in bundle.resolutions if row.concept_std == concept)
    coverage = next(row for row in bundle.coverage if row.id == resolution.coverage_id)
    period = next(row for row in bundle.periods if row.id == coverage.period_id)
    unit = next(row for row in bundle.units if row.id == resolution.unit_id)
    scope = next(row for row in bundle.scopes if row.id == resolution.semantic_scope_id)
    filing = next(row for row in bundle.filings if row.id == coverage.filing_version_id)
    observation = next(
        (row for row in bundle.observations if row.id == resolution.selected_observation_id), None
    )
    capture = next(
        (
            row
            for row in bundle.inputs.captures
            if observation is not None and row.id == observation.source_capture_id
        ),
        None,
    )
    fact = SelectedFact(
        concept=concept,
        value=observation.numeric_value if observation is not None else None,
        status=resolution.status,
        resolution_ids=(resolution.id,),
        observation_ids=(observation.id,) if observation is not None else (),
        accession=filing.accession,
        filed_date=filing.filed_date,
        source_url=capture.request_url if capture is not None else None,
        source_locator=observation.source_locator if observation is not None else None,
        capture_ids=(capture.id,) if capture is not None else (),
        source_hashes=(capture.body_sha256,) if capture is not None else (),
        source_tag=f"{observation.namespace}:{observation.tag}"
        if observation is not None
        else None,
        original_numeric_text=observation.original_numeric_text
        if observation is not None
        else None,
        transform_json=observation.transform_metadata if observation is not None else None,
        reason=resolution.reason,
    )
    query = PitQuery(
        issuer_id=bundle.inputs.issuer_id,
        period_id=period.id,
        scope_id=scope.id,
        unit_id=unit.id,
        statement_family=coverage.statement_family,
        concepts=(concept,),
        batch_ids=(evidence_id("synthetic-published-batch", bundle.output_manifest_hash),),
        capture_ids=tuple(row.id for row in bundle.inputs.captures),
        filing_event_ids=bundle.inputs.filing_event_ids,
        mapping_revision_id=bundle.inputs.mapping_revision_id,
        normalizer_revision=bundle.inputs.normalizer_revision,
        authority_policy_revision=bundle.inputs.authority_policy_revision,
        captured_before=bundle.inputs.captured_before,
        mode=HistoryMode.LATEST_REPORTED,
        instrument_id=scope.instrument_id,
        additional_quality_flag_ids=bundle.inputs.additional_quality_flag_ids,
        reporting_currency_unit_id=coverage.currency_unit_id,
    )
    # Match the PIT reader's applicable resolution, period, and batch flags.
    quality = tuple(
        row
        for row in bundle.quality_flags
        if row.resolution_id == resolution.id
        or (row.resolution_id is None and row.period_id in {None, period.id})
        or row.id in bundle.inputs.additional_quality_flag_ids
    )
    flags = {"revised_view"}
    if fact.status != "observed":
        flags.add("unresolved_concept")
    if any(row.severity in {"error", "blocking"} for row in quality):
        flags.add("blocking_quality_flag")
    selection = StatementSelection(
        query=query,
        coverage_ids=(coverage.id,),
        filing_version_ids=(filing.id,),
        facts=(fact,),
        flags=tuple(sorted(flags)),
        quality_flag_ids=tuple(row.id for row in quality),
        event_ids=(),
        usable_for_valuation=fact.status == "observed" and not (flags - {"revised_view"}),
        reporting_basis=coverage.reporting_basis,
        input_hash=content_hash(
            {"fixture": bundle.output_manifest_hash, "query": query, "fact": fact}
        ),
    )
    return FinancialInput(selection, concept, period, unit, scope)


def normalized(ticker):
    body, source = cohort_input(ticker)
    return normalize_verified_bytes(body, source)


def test_aapl_archived_operands_remain_blocked_by_incomplete_source_history():
    bundle = normalized("AAPL")
    cfo = project(bundle, Concept.CASH_FROM_OPERATING_ACTIVITIES)
    capex = project(bundle, Concept.CAPITAL_EXPENDITURES_PPE)
    result = free_cash_flow(cfo, capex)
    assert cfo.fact.value == Decimal("111482000000")
    assert capex.fact.value == Decimal("12715000000")
    assert cfo.value is capex.value is result.value is None
    assert result.operands == (cfo, capex)
    assert cfo.scope.id != capex.scope.id  # Different reviewed payment-basis semantics.
    assert cfo.precision is capex.precision is None
    assert "blocking_quality_flag" in result.flags
    history_rows = tuple(
        row
        for row in bundle.quality_flags
        if row.rule_key in {"inventory_history_incomplete", "event_history_incomplete"}
        and row.period_id in {None, cfo.period.id}
    )
    assert {row.rule_key for row in history_rows} == {
        "inventory_history_incomplete",
        "event_history_incomplete",
    }
    history_flags = {row.id for row in history_rows}
    assert history_flags.issubset(cfo.selection.quality_flag_ids)
    assert history_flags.issubset(capex.selection.quality_flag_ids)
    for item in result.operands:
        assert item.fact.capture_ids == (bundle.inputs.companyfacts_capture_id,)
        assert item.fact.observation_ids
        assert item.fact.original_numeric_text
        assert item.fact.source_url
        assert item.fact.source_hashes


@pytest.mark.parametrize("ticker", ["AAPL", "MSFT"])
def test_parent_income_never_fills_missing_consolidated_income(ticker):
    bundle = normalized(ticker)
    consolidated = project(bundle, Concept.NET_INCOME_CONSOLIDATED)
    parent = project(bundle, Concept.NET_INCOME_PARENT)
    revenue = project(bundle, Concept.REVENUE)
    assert parent.fact.value is not None
    assert parent.value is reported_amount(parent).value is None
    assert "blocking_quality_flag" in parent.flags
    assert consolidated.value is None
    assert consolidated.fact.status == "missing"
    result = net_margin(consolidated, revenue)
    assert result.value is None
    assert result.operands == (consolidated, revenue)
    assert "unresolved_concept" in result.flags


def test_synthetic_complete_evidence_context_cfo_less_ppe_capex_arithmetic():
    """Hand calculation only: synthetic identities make no source-eligibility claim."""
    cfo = operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "111482000000", absolute_error=None)
    capex = operand(Concept.CAPITAL_EXPENDITURES_PPE, "12715000000", absolute_error=None)
    assert free_cash_flow(cfo, capex).value == Decimal("98767000000")
