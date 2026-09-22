"""Synthetic, source-shaped operands; none of these values describe a company."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_ingest.financial_types import ScopeSpec, canonical_json, content_hash
from equity_ingest.sec_normalize import period_spec, unit_spec
from equity_schema.concepts import Concept
from equity_schema.pit import HistoryMode, PitQuery, SelectedFact, StatementSelection


def identity(name):
    return uuid5(NAMESPACE_URL, "equityeval:synthetic-core:" + name)


def operand(
    concept,
    value,
    *,
    start=date(2025, 1, 1),
    end=date(2025, 12, 31),
    currency="USD",
    absolute_error="0.5",
    flags=(),
    edition="annual-2025",
):
    issuer = identity("issuer")
    period = period_spec(start, end)
    unit = unit_spec(currency)
    kind = "parent" if concept == Concept.NET_INCOME_PARENT else "consolidated"
    descriptor = {
        "consolidation": kind,
        "instrument": None,
        "context_knowledge": "unknown",
        "scope_evidence": "synthetic reviewed scope",
        "cash_scope": "not_applicable",
        "payment_basis": "actual_cash_payment"
        if concept == Concept.CAPITAL_EXPENDITURES_PPE
        else "as_reported",
        "revenue_basis": "reported_complete_scope",
    }
    scope = ScopeSpec(
        identity(canonical_json(descriptor)),
        issuer,
        None,
        kind,
        1,
        canonical_json(descriptor),
        content_hash(descriptor),
    )
    family = (
        "cash_flow"
        if concept
        in {
            Concept.CASH_FROM_OPERATING_ACTIVITIES,
            Concept.CAPITAL_EXPENDITURES_PPE,
        }
        else "income"
    )
    capture = identity("capture")
    query = PitQuery(
        issuer,
        period.id,
        scope.id,
        unit.id,
        family,
        (concept,),
        (identity("batch"),),
        (capture,),
        (),
        identity("mapping"),
        "normalizer-v1",
        "authority-v1",
        datetime(2026, 3, 1, tzinfo=UTC),
        HistoryMode.AS_FILED_BY_DATE,
        filed_cutoff=date(2026, 2, 28),
        reporting_currency_unit_id=unit.id,
    )
    observation = identity(concept.value + str(start) + str(end))
    fact = SelectedFact(
        concept,
        Decimal(value) if value is not None else None,
        "observed" if value is not None else "missing",
        resolution_ids=(identity("resolution-" + str(observation)),),
        observation_ids=(observation,) if value is not None else (),
        accession="0000000001-26-000001",
        filed_date=date(2026, 2, 1),
        source_url="https://example.invalid/synthetic-filing",
        source_locator="/synthetic/" + concept.value,
        capture_ids=(capture,),
        source_hashes=("a" * 64,),
        source_tag="synthetic:" + concept.value,
        original_numeric_text=value,
        transform_json="{}",
    )
    selection = StatementSelection(
        query,
        (identity("coverage-" + str(observation)),),
        (identity(edition),),
        (fact,),
        flags,
        (),
        (),
        not flags and value is not None,
        "us_gaap",
        content_hash({"concept": concept, "value": value, "start": start, "end": end}),
    )
    precision = (
        None
        if absolute_error is None or value is None
        else PrecisionEvidence(
            absolute_error=Decimal(absolute_error),
            observation_ids=(observation,),
            evidence_refs=("synthetic:source-rounding-evidence",),
            method="synthetic_fixture",
        )
    )
    return FinancialInput(selection, concept, period, unit, scope, precision)


def balance(concept, value, **kwargs):
    """A selected instant balance using the same synthetic source evidence."""
    source = operand(concept, value, start=None, **kwargs)
    query = replace(source.selection.query, statement_family="balance_sheet")
    return replace(source, selection=replace(source.selection, query=query))
