"""Adversarial selectors: plausible values must not conceal incompatible evidence."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from equity_schema.concepts import Concept
from equity_schema.pit import HistoryMode, PitQuery, read_statement, read_statements
from psycopg.types.json import Jsonb

from tests.evidence_seed import insert, publish, seed_evidence
from tests.integration.test_evidence_constraints import clone_row

pytestmark = pytest.mark.integration


def query(*seeds, **changes):
    first = seeds[0]
    fields = dict(
        issuer_id=first["issuer"],
        period_id=first["period"],
        scope_id=first["scope"],
        unit_id=first["unit"],
        statement_family="income",
        concepts=(Concept.REVENUE,),
        batch_ids=tuple(seed["batch"] for seed in seeds),
        capture_ids=tuple(seed["capture"] for seed in seeds),
        filing_event_ids=(),
        mapping_revision_id=first["mapping"],
        normalizer_revision="test-v1",
        authority_policy_revision="test-v1",
        captured_before=datetime(2026, 9, 13, tzinfo=UTC),
        mode=HistoryMode.AS_FILED_BY_DATE,
        filed_cutoff=date(2025, 4, 1),
    )
    fields.update(changes)
    return PitQuery(**fields)


def another(db, first, **options):
    return seed_evidence(
        db,
        issuer_id=first["issuer"],
        security_id=first["security"],
        scope_id=first["scope"],
        mapping_id=first["mapping"],
        **options,
    )


@pytest.mark.parametrize("status", ["missing", "source_nil", "ambiguous"])
def test_latest_missing_does_not_resurrect_old_value(db_admin, db, status):
    old = seed_evidence(db_admin, value=Decimal("91"), publish_batch=True)
    new = another(db_admin, old, status=status, filed_date="2025-03-01", publish_batch=True)
    result = read_statement(db, query(old, new))
    assert result.facts[0].status == status
    assert result.facts[0].value is None
    assert not result.usable_for_valuation
    assert result.coverage_ids == (new["coverage"],)


def test_latest_unknown_currency_blocks_prior_known_currency(db_admin, db):
    old = seed_evidence(db_admin, publish_batch=True)
    new = another(db_admin, old, status="missing", filed_date="2025-03-01")
    # Build an unresolved coverage through immutable insert, not alteration of the old statement.
    clone_row(
        db_admin,
        "statement_coverage",
        new["coverage"],
        currency_unit_id=None,
        coverage_state="unresolved",
    )
    publish(db_admin, new["batch"])
    result = read_statement(db, query(old, new))
    assert "unresolved_coverage" in result.flags
    assert result.facts[0].value is None


def test_preliminary_earnings_do_not_displace_definitive_statement(db_admin, db):
    old = seed_evidence(db_admin, value=Decimal("91"), publish_batch=True)
    new = another(
        db_admin,
        old,
        value=Decimal("110"),
        filed_date="2025-03-01",
        authority_class="preliminary",
        publish_batch=True,
    )
    assert read_statement(db, query(old, new)).facts[0].value == Decimal("91")


@pytest.mark.parametrize("verified", [False, True])
def test_same_day_editions_require_verified_acceptance_order(db_admin, db, verified):
    basis = "verified_timezone" if verified else "unverified"
    first = seed_evidence(
        db_admin,
        value=Decimal("91"),
        acceptance_at=datetime(2025, 2, 1, 12, tzinfo=UTC),
        acceptance_time_basis=basis,
        publish_batch=True,
    )
    second = another(
        db_admin,
        first,
        value=Decimal("110"),
        acceptance_at=datetime(2025, 2, 1, 17, tzinfo=UTC),
        acceptance_time_basis=basis,
        publish_batch=True,
    )
    result = read_statement(db, query(first, second))
    if verified:
        assert result.facts[0].value == Decimal("110")
    else:
        assert result.facts[0].value is None
        assert "ambiguous_filing_order" in result.flags


@pytest.mark.parametrize(
    "unit_key,numerator,denominator,concept",
    [
        ("USD/shares", ["iso4217:USD"], ["xbrli:shares"], Concept.EPS_BASIC),
        ("shares", ["xbrli:shares"], [], Concept.WEIGHTED_AVERAGE_SHARES_BASIC),
    ],
)
def test_reporting_currency_and_fact_units_are_independent(
    db_admin, db, unit_key, numerator, denominator, concept
):
    ids = seed_evidence(db_admin, value=Decimal("2.25"))
    unit = uuid4()
    insert(
        db_admin,
        "units",
        id=unit,
        unit_key=unit_key,
        numerator_measures=numerator,
        denominator_measures=denominator,
    )
    observation = clone_row(
        db_admin,
        "source_observations",
        ids["observation"],
        source_locator="test:/per-share",
        unit_id=unit,
    )
    clone_row(
        db_admin,
        "fact_resolutions",
        ids["resolution"],
        concept_std=concept.value,
        unit_id=unit,
        selected_observation_id=observation,
    )
    publish(db_admin, ids["batch"])
    result = read_statement(
        db, query(ids, concepts=(concept,), unit_id=unit, reporting_currency_unit_id=ids["unit"])
    )
    assert result.facts[0].value == Decimal("2.25")


def test_nonexistent_pinned_event_is_not_silently_ignored(db_admin, db):
    ids = seed_evidence(db_admin, publish_batch=True)
    result = read_statement(db, query(ids, filing_event_ids=(uuid4(),)))
    assert not result.usable_for_valuation
    assert "incompatible_event_manifest" in result.flags


def test_pinned_global_blocking_flag_stops_valuation(db_admin, db):
    ids = seed_evidence(db_admin, publish_batch=True)
    flag = uuid4()
    insert(
        db_admin,
        "data_quality_flags",
        id=flag,
        issuer_id=ids["issuer"],
        period_id=ids["period"],
        rule_key="test.unreliable",
        severity="blocking",
        message="Review required",
        evidence_references=Jsonb(["test:/review"]),
        raised_at=datetime(2026, 9, 12, tzinfo=UTC),
    )
    result = read_statement(db, query(ids, additional_quality_flag_ids=(flag,)))
    assert result.facts[0].value == Decimal("100")
    assert not result.usable_for_valuation
    assert flag in result.quality_flag_ids


def test_pinned_batch_revision_is_not_implicitly_reinterpreted(db_admin, db):
    ids = seed_evidence(db_admin, publish_batch=True)
    result = read_statement(db, query(ids, normalizer_revision="different-normalizer"))
    assert "incompatible_batch_revision" in result.flags
    assert result.facts[0].value is None


def test_superseded_financial_capture_cannot_return_via_metadata_role(db_admin, db):
    ids = seed_evidence(db_admin)
    newer = clone_row(
        db_admin,
        "source_captures",
        ids["capture"],
        requested_at=datetime(2026, 9, 12, 1, tzinfo=UTC),
        completed_at=datetime(2026, 9, 12, 1, tzinfo=UTC),
        fetched_at=datetime(2026, 9, 12, 1, tzinfo=UTC),
        body_sha256="e" * 64,
    )
    insert(
        db_admin,
        "normalization_inputs",
        batch_id=ids["batch"],
        source_capture_id=ids["capture"],
        role="filing_metadata",
    )
    insert(
        db_admin,
        "normalization_inputs",
        batch_id=ids["batch"],
        source_capture_id=newer,
        role="financial_payload",
    )
    publish(db_admin, ids["batch"])
    result = read_statement(db, query(ids, capture_ids=(ids["capture"], newer)))
    assert not result.usable_for_valuation
    assert "incompatible_source_roles" in result.flags


def test_equal_time_different_source_bytes_are_ambiguous(db_admin, db):
    ids = seed_evidence(db_admin)
    different = clone_row(db_admin, "source_captures", ids["capture"], body_sha256="e" * 64)
    insert(
        db_admin,
        "normalization_inputs",
        batch_id=ids["batch"],
        source_capture_id=different,
        role="financial_payload",
    )
    publish(db_admin, ids["batch"])
    result = read_statement(db, query(ids, capture_ids=(ids["capture"], different)))
    assert "ambiguous_capture_vintage" in result.flags
    assert result.facts[0].value is None


def test_multiple_families_cannot_silently_mix_editions(db_admin, db):
    income = seed_evidence(db_admin, publish_batch=True)
    cash_flow = another(
        db_admin, income, statement_family="cash_flow", filed_date="2025-03-01", publish_batch=True
    )
    result = read_statements(
        db, (query(income, cash_flow), query(income, cash_flow, statement_family="cash_flow"))
    )
    assert all(item.facts[0].value == Decimal("100") for item in result.statements)
    assert "mixed_statement_editions" in result.flags
    assert not result.usable_for_valuation


def test_multiple_statement_queries_cannot_mix_history_modes(db_admin, db):
    ids = seed_evidence(db_admin, publish_batch=True)
    with pytest.raises(ValueError, match="one pinned"):
        read_statements(db, (query(ids), query(ids, mode=HistoryMode.LATEST_REPORTED)))


def test_capture_cannot_be_used_before_its_completion(db_admin, db):
    ids = seed_evidence(db_admin)
    late = clone_row(
        db_admin,
        "source_captures",
        ids["capture"],
        completed_at=datetime(2026, 9, 12, 2, tzinfo=UTC),
    )
    insert(
        db_admin,
        "normalization_inputs",
        batch_id=ids["batch"],
        source_capture_id=late,
        role="auxiliary",
    )
    publish(db_admin, ids["batch"])
    result = read_statement(
        db,
        query(
            ids,
            capture_ids=(ids["capture"], late),
            captured_before=datetime(2026, 9, 12, 1, tzinfo=UTC),
        ),
    )
    assert "capture_unavailable" in result.flags
    assert not result.usable_for_valuation
