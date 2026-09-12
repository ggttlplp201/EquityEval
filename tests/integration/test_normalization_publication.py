"""Real archive -> normalizer -> immutable database -> PIT, without upstream calls."""

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from equity_ingest.publisher import PublicationConflict, publish_bundle
from equity_ingest.sec_normalize import normalize_verified_bytes
from equity_schema.concepts import Concept
from equity_schema.pit import HistoryMode, PitQuery, read_statement

from tests.normalization_db_seed import seed_normalization_inputs
from tests.sec_normalization_seed import cohort_input

pytestmark = pytest.mark.integration


def test_real_apple_revenue_publishes_once_and_reads_with_provenance(db_admin, db):
    body, inputs = cohort_input("AAPL")
    seed_normalization_inputs(db_admin, inputs)
    bundle = normalize_verified_bytes(body, inputs)
    first = publish_bundle(db, bundle)
    second = publish_bundle(db, bundle)
    assert first.batch_id == second.batch_id
    assert second.reused
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 1
    record = db.execute(
        """
        SELECT c.period_id,c.scope_id,c.currency_unit_id,r.unit_id
        FROM fact_resolutions r JOIN statement_coverage c ON c.id=r.coverage_id
        WHERE c.batch_id=%s AND r.concept_std='revenue'
    """,
        (first.batch_id,),
    ).fetchone()
    selected = read_statement(
        db,
        PitQuery(
            issuer_id=inputs.issuer_id,
            period_id=record["period_id"],
            scope_id=record["scope_id"],
            unit_id=record["unit_id"],
            reporting_currency_unit_id=record["currency_unit_id"],
            statement_family="income",
            concepts=(Concept.REVENUE,),
            batch_ids=(first.batch_id,),
            capture_ids=tuple(c.id for c in inputs.captures),
            filing_event_ids=(),
            mapping_revision_id=inputs.mapping_revision_id,
            normalizer_revision=inputs.normalizer_revision,
            authority_policy_revision=inputs.authority_policy_revision,
            captured_before=inputs.captured_before,
            mode=HistoryMode.LATEST_REPORTED,
        ),
    )
    assert selected.facts[0].value == Decimal("416161000000")
    assert selected.facts[0].source_locator.startswith("/facts/us-gaap/")
    assert not selected.usable_for_valuation  # Explicit incomplete event/inventory review.


@pytest.mark.parametrize("ticker", ["MSFT", "JPM", "CRCL", "RBLX", "TSM", "KHC", "COST"])
def test_complete_cohort_bundle_satisfies_relational_scope_and_missingness(db_admin, db, ticker):
    body, inputs = cohort_input(ticker)
    seed_normalization_inputs(db_admin, inputs)
    result = publish_bundle(db, normalize_verified_bytes(body, inputs))
    assert (
        db.execute(
            """
        SELECT count(*) AS n FROM fact_resolutions r
        JOIN statement_coverage c ON c.id=r.coverage_id WHERE c.batch_id=%s
    """,
            (result.batch_id,),
        ).fetchone()["n"]
        == 40
    )


def test_tampered_output_or_unapproved_rules_cannot_publish(db_admin, db):
    body, inputs = cohort_input("AAPL")
    seed_normalization_inputs(db_admin, inputs)
    bundle = normalize_verified_bytes(body, inputs)
    with pytest.raises(PublicationConflict, match="hash"):
        publish_bundle(db, replace(bundle, output_manifest_hash="f" * 64))
    changed = replace(inputs, rules=inputs.rules[:-1])
    with pytest.raises(PublicationConflict, match="mapping"):
        publish_bundle(db, normalize_verified_bytes(body, changed))
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0


def test_pinned_capture_mismatch_rolls_back_entire_publication(db_admin, db):
    body, inputs = cohort_input("AAPL")
    seed_normalization_inputs(db_admin, inputs)
    capture = replace(inputs.captures[1], source_id=uuid4())
    bundle = normalize_verified_bytes(body, replace(inputs, captures=(inputs.captures[0], capture)))
    with pytest.raises(PublicationConflict, match="capture"):
        publish_bundle(db, bundle)
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0


def test_ordinary_share_scope_cannot_name_an_ads_security(db_admin, db):
    from tests.evidence_seed import insert

    body, inputs = cohort_input("TSM")
    insert(
        db_admin,
        "issuers",
        id=inputs.issuer_id,
        cik=inputs.cik,
        legal_name="Pinned TSM test issuer",
        first_seen_at=inputs.captured_before,
    )
    ordinary = next(r.scope for r in inputs.requests if r.scope.instrument_id is not None)
    insert(
        db_admin,
        "securities",
        id=ordinary.instrument_id,
        issuer_id=inputs.issuer_id,
        instrument_kind="ads",
        share_class_label="Test wrong identity",
    )
    seed_normalization_inputs(db_admin, inputs)
    with pytest.raises(PublicationConflict, match="instrument"):
        publish_bundle(db, normalize_verified_bytes(body, inputs))
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0


def test_legacy_capture_needs_policy_review_before_new_publication(db_admin, db, test_database_dsn):
    from alembic import command

    from tests.conftest import migration_config

    body, inputs = cohort_input("AAPL")
    seed_normalization_inputs(db_admin, inputs)
    config = migration_config(test_database_dsn)
    command.downgrade(config, "0002_watchlist")
    command.upgrade(config, "head")
    with pytest.raises(PublicationConflict, match="policy"):
        publish_bundle(db, normalize_verified_bytes(body, inputs))
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0
