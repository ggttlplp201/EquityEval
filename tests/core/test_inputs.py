"""The core projects pinned source evidence without inventing a usable fact."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest
from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_ingest.financial_types import canonical_json, content_hash
from equity_schema.concepts import Concept
from equity_schema.pit import HistoryMode

from tests.core.metric_fixtures import identity, operand


def test_matched_observed_input_retains_source_evidence_and_value():
    item = operand(Concept.REVENUE, "125.00")
    assert isinstance(item, FinancialInput)
    assert item.fact is item.selection.facts[0]
    assert item.value == Decimal("125.00")
    assert item.flags == item.blocking_flags == ()
    assert item.precision.absolute_error == Decimal("0.5")
    assert item.fact.original_numeric_text == "125.00"


@pytest.mark.parametrize(
    "scenario", ["absent", "duplicate", "missing", "nil", "aggregate", "fact_flag"]
)
def test_unusable_input_preserves_raw_record_and_all_source_flags(scenario):
    item = operand(Concept.REVENUE, "125")
    fact = item.fact
    selection = item.selection
    if scenario == "absent":
        selection = replace(selection, facts=())
    elif scenario == "duplicate":
        selection = replace(selection, facts=(fact, fact))
    elif scenario == "missing":
        selection = replace(selection, facts=(replace(fact, status="missing"),))
    elif scenario == "nil":
        selection = replace(selection, facts=(replace(fact, status="source_nil"),))
    elif scenario == "aggregate":
        selection = replace(selection, flags=("unresolved_concept",), usable_for_valuation=False)
    else:
        selection = replace(selection, facts=(replace(fact, flags=("source_warning",)),))
    item = replace(item, selection=selection)
    assert item.selection is selection
    assert item.value is None
    assert item.blocking_flags
    assert set(selection.flags).issubset(item.flags)
    if item.fact:
        assert set(item.fact.flags).issubset(item.flags)
        assert item.fact.value == Decimal("125")


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        125,
        1.25,
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_observed_input_requires_a_finite_decimal_without_coercion(value):
    item = operand(Concept.REVENUE, "125")
    fact = replace(item.fact, value=value)
    projected = replace(item, selection=replace(item.selection, facts=(fact,)))
    assert projected.fact is fact
    assert projected.value is None
    assert "input_value_invalid" in projected.blocking_flags


@pytest.mark.parametrize("label", ["revised_view", "earliest_available"])
def test_existing_history_labels_alone_are_nonblocking(label):
    item = operand(Concept.REVENUE, "0", absolute_error=None)
    item = replace(item, selection=replace(item.selection, flags=(label,)))
    assert item.value == Decimal("0")
    assert item.flags == (label,)
    assert not item.blocking_flags
    assert item.precision is None


@pytest.mark.parametrize(
    "mismatch",
    [
        "period_id",
        "unit_id",
        "scope_id",
        "issuer",
        "instrument",
        "concept",
        "scope_hash",
        "scope_schema",
        "scope_kind",
        "descriptor_instrument",
        "descriptor_not_object",
        "scope_evidence",
        "period_order",
        "instant_start",
        "duration_start",
        "unit_measures",
    ],
)
def test_projection_rejects_mismatched_or_invalid_source_context(mismatch):
    item = operand(Concept.REVENUE, "125")
    if mismatch in {"period_id", "unit_id", "scope_id"}:
        field = mismatch.removesuffix("_id")
        item = replace(item, **{field: replace(getattr(item, field), id=identity("different"))})
    elif mismatch == "issuer":
        item = replace(item, scope=replace(item.scope, issuer_id=identity("different")))
    elif mismatch == "instrument":
        item = replace(item, scope=replace(item.scope, instrument_id=identity("different")))
    elif mismatch == "concept":
        item = replace(
            item,
            selection=replace(
                item.selection,
                query=replace(item.selection.query, concepts=(Concept.OPERATING_INCOME,)),
            ),
        )
    elif mismatch == "scope_hash":
        item = replace(item, scope=replace(item.scope, content_sha256="a" * 64))
    elif mismatch == "scope_schema":
        item = replace(item, scope=replace(item.scope, descriptor_schema_version=2))
    elif mismatch == "scope_kind":
        item = replace(item, scope=replace(item.scope, scope_kind="parent"))
    elif mismatch in {"descriptor_instrument", "descriptor_not_object", "scope_evidence"}:
        import json

        descriptor = json.loads(item.scope.descriptor_json)
        if mismatch == "descriptor_instrument":
            descriptor["instrument"] = str(identity("different"))
        elif mismatch == "scope_evidence":
            descriptor["scope_evidence"] = ""
        else:
            descriptor = []
        item = replace(
            item,
            scope=replace(
                item.scope,
                descriptor_json=canonical_json(descriptor),
                content_sha256=content_hash(descriptor),
            ),
        )
    elif mismatch == "period_order":
        item = replace(item, period=replace(item.period, start_date=date(2026, 1, 1)))
    elif mismatch == "instant_start":
        item = replace(item, period=replace(item.period, period_kind="instant"))
    elif mismatch == "duration_start":
        item = replace(item, period=replace(item.period, start_date=None))
    else:
        item = replace(item, unit=replace(item.unit, numerator_measures=("iso4217:EUR",)))
    assert item.value is None
    assert item.blocking_flags
    assert item.fact.value == Decimal("125")


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("resolution_ids", ()),
        ("observation_ids", ()),
        ("observation_ids", (identity("one"), identity("two"))),
        ("capture_ids", ()),
        ("capture_ids", (identity("outside-manifest"),)),
        ("resolution_ids", ("not-a-uuid",)),
        ("accession", None),
        ("filed_date", None),
        ("filed_date", date(2026, 3, 2)),
        ("source_url", None),
        ("source_url", "/relative/filing"),
        ("source_url", "javascript:unsafe"),
        ("source_locator", ""),
        ("source_hashes", ()),
        ("source_hashes", ("unverified",)),
        ("source_tag", None),
        ("original_numeric_text", None),
        ("transform_json", None),
        ("transform_json", "not json"),
        ("transform_json", "[]"),
    ],
)
def test_observed_input_requires_complete_provenance(field, replacement):
    item = operand(Concept.REVENUE, "125")
    fact = replace(item.fact, **{field: replacement})
    item = replace(item, selection=replace(item.selection, facts=(fact,)))
    assert item.value is None
    assert "input_provenance_invalid" in item.blocking_flags
    assert item.fact is fact


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("coverage_ids", ()),
        ("filing_version_ids", ()),
        ("filing_version_ids", (identity("first"), identity("second"))),
        ("input_hash", "unverified"),
        ("reporting_basis", None),
    ],
)
def test_observed_input_requires_a_pinned_edition_and_selection_evidence(field, replacement):
    item = operand(Concept.REVENUE, "125")
    selection = replace(item.selection, **{field: replacement})
    item = replace(item, selection=selection)
    assert item.value is None
    assert "input_selection_evidence_invalid" in item.blocking_flags


def test_filing_date_cannot_be_later_than_capture_or_filed_cutoff():
    item = operand(Concept.REVENUE, "125")
    captured_before = item.selection.query.captured_before - timedelta(days=30)
    query = replace(item.selection.query, captured_before=captured_before)
    assert replace(item, selection=replace(item.selection, query=query)).value is None
    query = replace(item.selection.query, filed_cutoff=date(2026, 1, 31))
    assert replace(item, selection=replace(item.selection, query=query)).value is None


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("absolute_error", Decimal("-0.01")),
        ("absolute_error", Decimal("NaN")),
        ("absolute_error", Decimal("sNaN")),
        ("absolute_error", Decimal("Infinity")),
        ("absolute_error", 0.5),
        ("absolute_error", True),
        ("observation_ids", ()),
        ("observation_ids", ("not-a-uuid",)),
        ("observation_ids", (identity("same"), identity("same"))),
        ("evidence_refs", ()),
        ("evidence_refs", ("",)),
        ("evidence_refs", ("  ",)),
        ("evidence_refs", ["reference"]),
        ("method", ""),
        ("method", " "),
    ],
)
def test_precision_requires_explicit_valid_source_evidence(field, replacement):
    precision = operand(Concept.REVENUE, "125").precision
    with pytest.raises(ValueError):
        replace(precision, **{field: replacement})


def test_precision_must_match_exactly_the_selected_observations():
    item = operand(Concept.REVENUE, "125")
    precision = replace(item.precision, observation_ids=(identity("other-observation"),))
    item = replace(item, precision=precision)
    assert item.precision is precision
    assert item.value is None
    assert "input_precision_mismatch" in item.blocking_flags


def test_unknown_precision_stays_unknown_and_explicit_exact_precision_is_retained():
    item = operand(Concept.REVENUE, "125.000", absolute_error=None)
    assert item.precision is None
    assert item.value == Decimal("125.000")
    precision = PrecisionEvidence(
        Decimal("0"), item.fact.observation_ids, ("source:explicit-exact",), "exact_source_value"
    )
    item = replace(item, precision=precision)
    assert item.value == Decimal("125.000")
    assert item.precision.absolute_error == Decimal("0")


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("issuer_id", identity("other-issuer")),
        ("security_id", identity("other-security")),
        ("mode", HistoryMode.LATEST_REPORTED),
        ("filed_cutoff", date(2026, 2, 27)),
        (
            "captured_before",
            operand(Concept.REVENUE, "1").selection.query.captured_before + timedelta(seconds=1),
        ),
        ("batch_ids", (identity("other-batch"),)),
        ("capture_ids", (identity("other-capture"),)),
        ("filing_event_ids", (identity("other-event"),)),
        ("mapping_revision_id", identity("other-mapping")),
        ("normalizer_revision", "different"),
        ("authority_policy_revision", "different"),
        ("additional_quality_flag_ids", (identity("additional-flag"),)),
        ("audited_required", True),
        ("allow_reviewed_equivalent", True),
        ("original_history_complete", True),
    ],
)
def test_history_key_includes_every_pinned_common_policy(field, replacement):
    item = operand(Concept.REVENUE, "125")
    changed = replace(
        item,
        selection=replace(
            item.selection, query=replace(item.selection.query, **{field: replacement})
        ),
    )
    assert item.history_key != changed.history_key


def test_history_key_ignores_concept_period_scope_and_manifest_order():
    revenue = operand(Concept.REVENUE, "125")
    capex = operand(
        Concept.CAPITAL_EXPENDITURES_PPE,
        "12",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
    )
    assert revenue.history_key == capex.history_key
    query = replace(revenue.selection.query, batch_ids=(identity("first"), identity("second")))
    first = replace(revenue, selection=replace(revenue.selection, query=query))
    second = replace(
        first,
        selection=replace(
            first.selection, query=replace(query, batch_ids=tuple(reversed(query.batch_ids)))
        ),
    )
    assert first.history_key == second.history_key
    assert hash(first.history_key) == hash(second.history_key)


@pytest.mark.parametrize("field", ["period", "unit", "scope", "issuer", "mapping"])
def test_identity_values_must_be_uuids_even_when_equal(field):
    item = operand(Concept.REVENUE, "125")
    query = item.selection.query
    if field in {"period", "unit", "scope"}:
        item = replace(item, **{field: replace(getattr(item, field), id="same-invalid-id")})
        query = replace(query, **{field + "_id": "same-invalid-id"})
    elif field == "issuer":
        item = replace(item, scope=replace(item.scope, issuer_id="same-invalid-id"))
        query = replace(query, issuer_id="same-invalid-id")
    else:
        query = replace(query, mapping_revision_id="invalid-id")
    item = replace(item, selection=replace(item.selection, query=query))
    assert item.value is None
    assert "input_identity_invalid" in item.blocking_flags


def test_reporting_currency_must_match_the_selected_monetary_unit():
    item = operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "120")
    query = replace(item.selection.query, reporting_currency_unit_id=identity("EUR-statement"))
    item = replace(item, selection=replace(item.selection, query=query))
    assert item.fact.value == Decimal("120")
    assert item.value is None
    assert "input_reporting_currency_mismatch" in item.blocking_flags


def test_different_statement_reporting_currencies_cannot_produce_fcf():
    from equity_core.metrics import free_cash_flow

    cfo = operand(Concept.CASH_FROM_OPERATING_ACTIVITIES, "120")
    capex = operand(Concept.CAPITAL_EXPENDITURES_PPE, "20")
    query = replace(capex.selection.query, reporting_currency_unit_id=identity("EUR-statement"))
    capex = replace(capex, selection=replace(capex.selection, query=query))
    assert free_cash_flow(cfo, capex).value is None
    assert cfo.history_key != capex.history_key


def test_implicit_monetary_reporting_currency_matches_reader_fallback():
    explicit = operand(Concept.REVENUE, "125")
    query = replace(explicit.selection.query, reporting_currency_unit_id=None)
    implicit = replace(explicit, selection=replace(explicit.selection, query=query))
    assert implicit.value == Decimal("125")
    assert implicit.history_key == explicit.history_key
