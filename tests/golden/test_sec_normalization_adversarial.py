"""Cases where a plausible number must instead remain unavailable."""

import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from equity_ingest.financial_types import content_hash
from equity_ingest.sec_normalize import (
    bundle_output_hash,
    normalization_input_hash,
    normalize_verified_bytes,
)
from equity_schema.concepts import Concept

from tests.sec_normalization_seed import cohort_input


@pytest.fixture
def one_revenue():
    _, inputs = cohort_input("AAPL")
    request = next(request for request in inputs.requests if Concept.REVENUE in request.concepts)
    request = replace(request, concepts=(Concept.REVENUE,))
    rules = tuple(rule for rule in inputs.rules if rule.concept == Concept.REVENUE)
    return replace(inputs, requests=(request,), rules=rules)


def source_row():
    return {
        "start": "2024-09-29",
        "end": "2025-09-27",
        "val": 416161000000,
        "accn": "0000320193-25-000079",
        "filed": "2025-10-31",
        "form": "10-K",
    }


def normalize_rows(inputs, rows, *, cik=320193, token=None):
    payload = {
        "cik": cik,
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": rows}}
            }
        },
    }
    body = json.dumps(payload).encode()
    if token is not None:
        body = body.replace(b'"val": 416161000000', b'"val": ' + token)
    capture = replace(
        inputs.captures[0], body_sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body)
    )
    return normalize_verified_bytes(body, replace(inputs, captures=(capture, *inputs.captures[1:])))


@pytest.mark.parametrize(
    "value,reason",
    [
        (None, "json_null_without_reviewed_nil_semantics"),
        (True, "unparseable_source_value"),
        ("123", "unparseable_source_value"),
    ],
)
def test_bad_source_values_do_not_become_numeric_or_source_nil(one_revenue, value, reason):
    row = source_row()
    row["val"] = value
    result = normalize_rows(one_revenue, [row])
    assert result.resolutions[0].status == "missing"
    assert result.resolutions[0].reason == reason
    assert result.observations[0].value_state == "unparseable"
    assert result.observations[0].numeric_value is None


def test_missing_value_field_remains_distinct_from_null(one_revenue):
    row = source_row()
    del row["val"]
    result = normalize_rows(one_revenue, [row])
    assert result.resolutions[0].reason == "missing_value_field"
    assert result.observations[0].original_numeric_text is None


@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"-Infinity"])
def test_nonfinite_tokens_raise_a_gap_with_original_evidence(one_revenue, token):
    result = normalize_rows(one_revenue, [source_row()], token=token)
    assert result.resolutions[0].status == "missing"
    assert result.observations[0].original_numeric_text == token.decode()


def test_zero_is_observed_and_exact_lexical_form_survives(one_revenue):
    result = normalize_rows(one_revenue, [source_row()], token=b"-0.000e+0")
    assert result.resolutions[0].status == "observed"
    assert result.observations[0].numeric_value == 0
    assert result.observations[0].original_numeric_text == "-0.000e+0"


def test_equivalent_duplicate_selects_one_original_array_position(one_revenue):
    result = normalize_rows(one_revenue, [source_row(), source_row()])
    assert result.resolutions[0].status == "observed"
    assert len(result.observations) == len(result.candidates) == 2
    selected = next(
        candidate for candidate in result.candidates if candidate.disposition == "selected"
    )
    observation = next(item for item in result.observations if item.id == selected.observation_id)
    assert observation.source_locator.endswith("/0")


@pytest.mark.parametrize("change", [{"val": 416161000001}, {"fp": "FY"}])
def test_different_value_or_provenance_is_not_an_equivalent_duplicate(one_revenue, change):
    result = normalize_rows(one_revenue, [source_row(), {**source_row(), **change}])
    assert result.resolutions[0].status == "ambiguous"
    assert result.resolutions[0].selected_observation_id is None


def test_matching_fiscal_focus_cannot_replace_an_exact_period(one_revenue):
    row = {**source_row(), "start": "2023-10-01", "end": "2024-09-28", "fy": 2025, "fp": "FY"}
    result = normalize_rows(one_revenue, [row])
    assert result.resolutions[0].status == "missing"
    assert result.candidates[0].explanation == "different_period_or_unit"


def test_response_issuer_mismatch_is_not_empty_success(one_revenue):
    with pytest.raises(ValueError, match="does not match"):
        normalize_rows(one_revenue, [source_row()], cik=19617)


def test_actual_source_cik_string_type_is_retained(one_revenue):
    result = normalize_rows(one_revenue, [source_row()], cik="0000320193")
    metadata = json.loads(result.observations[0].raw_metadata)
    assert metadata["source_cik_type"] == "string"
    assert metadata["source_cik_json"] == '"0000320193"'


def test_changed_filing_metadata_cannot_bind_to_old_version(one_revenue):
    result = normalize_rows(one_revenue, [{**source_row(), "filed": "2025-11-01"}])
    assert result.resolutions[0].status == "ambiguous"
    assert result.resolutions[0].reason == "filing_metadata_conflict"


def test_unreviewed_era_is_explicitly_unsupported(one_revenue):
    result = normalize_rows(replace(one_revenue, rules=()), [source_row()])
    assert result.resolutions[0].status == "unsupported_scope"
    assert result.resolutions[0].selected_observation_id is None


def test_input_cutoff_rejects_a_capture_not_yet_completed(one_revenue):
    inputs = replace(
        one_revenue, captured_before=one_revenue.captures[0].completed_at - timedelta(seconds=1)
    )
    with pytest.raises(ValueError, match="unavailable"):
        normalize_rows(inputs, [source_row()])


def test_unknown_authority_and_history_emit_pinnable_blocking_flags(one_revenue):
    request = replace(
        one_revenue.requests[0], authority_class="unknown", coverage_state="unresolved"
    )
    result = normalize_rows(replace(one_revenue, requests=(request,)), [source_row()])
    assert {
        "unresolved_coverage",
        "event_history_incomplete",
        "inventory_history_incomplete",
    }.issubset({flag.rule_key for flag in result.quality_flags})
    assert all(flag.severity == "error" for flag in result.quality_flags)
    assert result.original_history_complete is False


def test_hashes_ignore_allocated_output_ids_but_keep_new_capture_vintage(one_revenue):
    first = normalize_rows(one_revenue, [source_row()])
    # Only the transient coverage request identity changes; semantic output is equal.
    changed_request = replace(one_revenue.requests[0], id=uuid4())
    reallocated = normalize_rows(replace(one_revenue, requests=(changed_request,)), [source_row()])
    assert first.input_manifest_hash == reallocated.input_manifest_hash
    assert first.output_manifest_hash == reallocated.output_manifest_hash
    newer = replace(
        one_revenue.captures[0],
        id=uuid4(),
        fetched_at=one_revenue.captures[0].fetched_at + timedelta(seconds=1),
        completed_at=one_revenue.captures[0].completed_at + timedelta(seconds=1),
    )
    new_inputs = replace(
        one_revenue,
        companyfacts_capture_id=newer.id,
        captures=(newer, *one_revenue.captures[1:]),
        filings=(replace(one_revenue.filings[0], metadata_capture_id=newer.id),),
    )
    new_vintage = normalize_rows(new_inputs, [source_row()])
    assert first.input_manifest_hash != new_vintage.input_manifest_hash
    assert first.output_manifest_hash != new_vintage.output_manifest_hash
    assert bundle_output_hash(first) == first.output_manifest_hash
    assert normalization_input_hash(first.inputs) == first.input_manifest_hash


def test_mapping_content_revision_is_not_an_output_number(one_revenue):
    changed_rule = replace(one_revenue.rules[0], rationale="A separately reviewed rationale")
    assert content_hash((changed_rule,)) != content_hash(one_revenue.rules)
    assert normalization_input_hash(
        replace(one_revenue, rules=(changed_rule,))
    ) != normalization_input_hash(one_revenue)


def test_khc_original_and_revised_2017_income_stay_separate():
    from datetime import date

    from equity_ingest.financial_types import evidence_id
    from equity_ingest.sec_normalize import period_spec, reviewed_cohort_rules

    body, inputs = cohort_input("KHC")
    period = period_spec(date(2017, 1, 1), date(2017, 12, 30))
    filings, requests = [], []
    for accession, filed in [
        ("0001637459-18-000015", date(2018, 2, 16)),
        ("0001637459-19-000049", date(2019, 6, 7)),
    ]:
        filing = replace(
            inputs.filings[0],
            id=evidence_id("test-version", accession),
            filing_id=evidence_id("test-filing", accession),
            accession=accession,
            filed_date=filed,
            report_period_end=period.end_date,
            metadata_hash=content_hash([accession, filed]),
        )
        filings.append(filing)
        for concept in (Concept.NET_INCOME_PARENT, Concept.NET_INCOME_CONSOLIDATED):
            original = next(request for request in inputs.requests if concept in request.concepts)
            requests.append(
                replace(
                    original,
                    id=uuid4(),
                    filing_version_id=filing.id,
                    period=period,
                    concepts=(concept,),
                )
            )
    inputs = replace(
        inputs,
        filings=tuple(filings),
        requests=tuple(requests),
        rules=reviewed_cohort_rules(inputs.cik, tuple(filings), tuple(requests)),
    )
    result = normalize_verified_bytes(body, inputs)
    observations = {observation.id: observation for observation in result.observations}
    file_ids = {filing.id: filing.accession for filing in result.filings}
    actual = {
        (
            file_ids[observations[resolution.selected_observation_id].filing_version_id],
            resolution.concept_std,
        ): observations[resolution.selected_observation_id].numeric_value
        for resolution in result.resolutions
    }
    assert actual == {
        ("0001637459-18-000015", Concept.NET_INCOME_PARENT): 10999000000,
        ("0001637459-18-000015", Concept.NET_INCOME_CONSOLIDATED): 10990000000,
        ("0001637459-19-000049", Concept.NET_INCOME_PARENT): 10941000000,
        ("0001637459-19-000049", Concept.NET_INCOME_CONSOLIDATED): 10932000000,
    }


def test_tsm_2024_is_explicit_and_preserves_cash_payment_and_ordinary_eps_scope():
    from datetime import date
    from decimal import Decimal

    from equity_ingest.financial_types import evidence_id
    from equity_ingest.sec_normalize import period_spec, reviewed_cohort_rules

    body, inputs = cohort_input("TSM")
    period = period_spec(date(2024, 1, 1), date(2024, 12, 31))
    filing = replace(
        inputs.filings[0],
        id=evidence_id("test-version", "TSM2024"),
        filing_id=evidence_id("test-filing", "TSM2024"),
        accession="0001193125-25-083423",
        filed_date=date(2025, 4, 17),
        report_period_end=period.end_date,
        metadata_hash=content_hash(["0001193125-25-083423", "2025-04-17"]),
    )
    expected = {
        Concept.INTEREST_EXPENSE: Decimal("10495400000"),
        Concept.SHARE_BASED_COMPENSATION: Decimal("1242700000"),
        Concept.DIVIDENDS_PAID: Decimal("363055200000"),
        Concept.EPS_BASIC: Decimal("44.68"),
        Concept.EPS_DILUTED: Decimal("44.67"),
    }
    requests = tuple(
        replace(
            next(request for request in inputs.requests if concept in request.concepts),
            id=uuid4(),
            filing_version_id=filing.id,
            period=period,
            concepts=(concept,),
            coverage_state="covered",
        )
        for concept in expected
    )
    inputs = replace(
        inputs,
        filings=(filing,),
        requests=requests,
        rules=reviewed_cohort_rules(inputs.cik, (filing,), requests),
    )
    result = normalize_verified_bytes(body, inputs)
    observations = {item.id: item for item in result.observations}
    assert {
        resolution.concept_std: observations[resolution.selected_observation_id].numeric_value
        for resolution in result.resolutions
    } == expected
    # An equity-appropriation amount is retained only as a rejected candidate.
    rejected = [
        candidate
        for candidate in result.candidates
        if observations[candidate.observation_id].tag == "DividendsPaid"
    ]
    assert rejected and all(candidate.disposition == "rejected" for candidate in rejected)


@pytest.mark.parametrize(
    "ticker,concept,changes",
    [
        ("RBLX", Concept.NET_INCOME_PARENT, {"consolidation": "consolidated"}),
        ("CRCL", Concept.CASH_AND_CASH_EQUIVALENTS, {"cash_scope": "including_holder_reserves"}),
        ("JPM", Concept.REVENUE, {"revenue_basis": "gross_before_interest"}),
        ("TSM", Concept.COMMON_SHARES_OUTSTANDING, {"consolidation": "american_depositary_shares"}),
    ],
)
def test_reviewed_factory_cannot_bless_a_different_economic_scope(ticker, concept, changes):
    from equity_ingest.financial_types import canonical_json
    from equity_ingest.sec_normalize import reviewed_cohort_rules

    body, inputs = cohort_input(ticker)
    original = next(request for request in inputs.requests if concept in request.concepts)
    descriptor = {**json.loads(original.scope.descriptor_json), **changes}
    scope = replace(
        original.scope,
        id=uuid4(),
        scope_kind=descriptor["consolidation"],
        descriptor_json=canonical_json(descriptor),
        content_sha256=content_hash(descriptor),
    )
    request = replace(original, scope=scope, concepts=(concept,))
    rules = reviewed_cohort_rules(inputs.cik, inputs.filings, (request,))
    result = normalize_verified_bytes(body, replace(inputs, requests=(request,), rules=rules))
    assert result.resolutions[0].status == "unsupported_scope"
    assert result.resolutions[0].selected_observation_id is None


def test_selected_filing_day_review_is_not_complete_original_history():
    from equity_ingest.financial_types import Completeness

    body, inputs = cohort_input("KHC")
    filed = inputs.filings[0].filed_date
    selected_day_only = Completeness(
        "complete", filed, filed, ("Only selected filing day reviewed",)
    )
    result = normalize_verified_bytes(
        body,
        replace(
            inputs, inventory_completeness=selected_day_only, event_completeness=selected_day_only
        ),
    )
    assert result.original_history_complete is False
    assert {"inventory_history_incomplete", "event_history_incomplete"}.issubset(
        {flag.rule_key for flag in result.quality_flags}
    )


def test_history_review_requires_period_end_through_retrieval_assessment_date():
    from datetime import date

    from equity_ingest.financial_types import Completeness

    body, inputs = cohort_input("KHC")
    earliest = min(request.period.end_date for request in inputs.requests)
    through_selected = Completeness(
        "complete",
        earliest,
        inputs.filings[0].filed_date,
        ("History only through selected filing",),
    )
    incomplete = normalize_verified_bytes(
        body,
        replace(
            inputs, inventory_completeness=through_selected, event_completeness=through_selected
        ),
    )
    assert incomplete.original_history_complete is False
    reviewed_window = Completeness(
        "complete",
        earliest,
        date(2026, 9, 12),
        ("Explicit synthetic full-window review assertion",),
    )
    complete = normalize_verified_bytes(
        body,
        replace(inputs, inventory_completeness=reviewed_window, event_completeness=reviewed_window),
    )
    assert complete.original_history_complete is True


def test_approved_rule_pack_cannot_move_to_another_comparative_period(one_revenue):
    from datetime import date

    from equity_ingest.sec_normalize import period_spec

    period = period_spec(date(2023, 10, 1), date(2024, 9, 28))
    request = replace(one_revenue.requests[0], period=period)
    result = normalize_rows(
        replace(one_revenue, requests=(request,)),
        [{**source_row(), "start": "2023-10-01", "end": "2024-09-28"}],
    )
    assert result.resolutions[0].status == "unsupported_scope"


def test_approved_rule_pack_binds_scope_content_not_only_scope_uuid(one_revenue):
    from equity_ingest.financial_types import canonical_json

    original = one_revenue.requests[0]
    descriptor = {**json.loads(original.scope.descriptor_json), "consolidation": "parent"}
    changed = replace(
        original.scope,
        scope_kind="parent",
        descriptor_json=canonical_json(descriptor),
        content_sha256=content_hash(descriptor),
    )
    request = replace(original, scope=changed)  # Same UUID and pre-approved rule pack.
    result = normalize_rows(replace(one_revenue, requests=(request,)), [source_row()])
    assert result.resolutions[0].status == "unsupported_scope"


@pytest.mark.parametrize("change", [{"statement_family": "cash_flow"}, {"reporting_basis": "ifrs"}])
def test_approved_rule_pack_binds_statement_and_accounting_basis(one_revenue, change):
    request = replace(one_revenue.requests[0], **change)
    result = normalize_rows(replace(one_revenue, requests=(request,)), [source_row()])
    assert result.resolutions[0].status == "unsupported_scope"


@pytest.mark.parametrize("field,value", [("scope_kind", "parent"), ("instrument_id", uuid4())])
def test_approved_rule_pack_binds_scope_columns_as_well_as_descriptor(one_revenue, field, value):
    request = one_revenue.requests[0]
    scope = replace(request.scope, **{field: value})
    result = normalize_rows(
        replace(one_revenue, requests=(replace(request, scope=scope),)), [source_row()]
    )
    assert result.resolutions[0].status == "unsupported_scope"
