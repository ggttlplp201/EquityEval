"""Hand-checked history, missingness and vintage regression before selector code."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from equity_schema.concepts import Concept
from equity_schema.pit import HistoryMode, PitQuery, read_statement

from tests.khc_seed import seed_khc

pytestmark = pytest.mark.integration


def query(ids, cutoff=date(2018, 2, 17), **changes):
    fields = dict(
        issuer_id=ids["issuer"],
        period_id=ids["period"],
        scope_id=ids["parent_scope"],
        unit_id=ids["unit"],
        statement_family="income",
        concepts=(Concept.NET_INCOME_PARENT,),
        batch_ids=(ids["batch"],),
        capture_ids=(ids["capture"],),
        filing_event_ids=(ids["non_reliance_event"],),
        mapping_revision_id=ids["mapping"],
        normalizer_revision="khc-fixture-v1",
        authority_policy_revision="periodic-v1",
        captured_before=datetime(2026, 9, 12, tzinfo=UTC),
        mode=HistoryMode.AS_FILED_BY_DATE,
        filed_cutoff=cutoff,
    )
    fields.update(changes)
    return PitQuery(**fields)


def test_khc_original_then_restatement_without_overwriting(db_admin, db):
    ids = seed_khc(db_admin)
    original = read_statement(db, query(ids))
    revised = read_statement(db, query(ids, date(2019, 6, 8)))
    assert original.facts[0].value == Decimal("10999000000")
    assert revised.facts[0].value == Decimal("10941000000")
    assert original.facts[0].accession == "0001637459-18-000015"
    assert revised.facts[0].accession == "0001637459-19-000049"
    assert original.facts[0].source_url.endswith("CIK0001637459.json")
    assert original.facts[0].source_locator.startswith("/facts/us-gaap/NetIncomeLoss/")
    assert read_statement(db, query(ids)) == original
    assert original.input_hash != revised.input_hash


def test_retrieved_in_2026_does_not_exist_in_2018_vintage(db_admin, db):
    ids = seed_khc(db_admin)
    result = read_statement(db, query(ids, captured_before=datetime(2018, 2, 17, tzinfo=UTC)))
    assert result.facts[0].value is None
    assert "capture_unavailable" in result.flags
    assert not result.usable_for_valuation


def test_non_reliance_uses_public_announcement_not_private_determination(db_admin, db):
    ids = seed_khc(db_admin)
    before = read_statement(db, query(ids, date(2019, 5, 3)))
    after = read_statement(db, query(ids, date(2019, 5, 7)))
    assert before.usable_for_valuation
    assert after.facts[0].value == Decimal("10999000000")  # retain evidence
    assert "non_reliance" in after.flags
    assert not after.usable_for_valuation


def test_original_remains_non_reliable_after_replacement(db_admin, db):
    ids = seed_khc(db_admin)
    result = read_statement(db, query(ids, date(2019, 6, 8), mode=HistoryMode.ORIGINAL_AS_FILED))
    assert result.facts[0].value == Decimal("10999000000")
    assert {"non_reliance", "earliest_available"} <= set(result.flags)
    assert not result.usable_for_valuation
    assert read_statement(db, query(ids, date(2019, 6, 8))).usable_for_valuation


def test_consolidated_is_not_parent_income(db_admin, db):
    ids = seed_khc(db_admin)
    result = read_statement(
        db,
        query(
            ids,
            date(2019, 6, 8),
            scope_id=ids["consolidated_scope"],
            concepts=(Concept.NET_INCOME_CONSOLIDATED,),
        ),
    )
    assert result.facts[0].value == Decimal("10932000000")


def test_missing_requested_concept_does_not_become_zero(db_admin, db):
    ids = seed_khc(db_admin)
    result = read_statement(db, query(ids, concepts=(Concept.GROSS_PROFIT,)))
    assert result.facts[0].value is None
    assert result.facts[0].status == "missing"
    assert "unresolved_concept" in result.flags


def test_vintage_requires_timezone_and_as_filed_requires_cutoff(db_admin):
    ids = seed_khc(db_admin)
    with pytest.raises(ValueError, match="timezone"):
        query(ids, captured_before=datetime(2026, 9, 12))
    with pytest.raises(ValueError, match="cutoff"):
        query(ids, None)
