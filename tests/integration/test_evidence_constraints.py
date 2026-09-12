"""Behavior contracts for the reviewed immutable evidence foundation."""

from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest

from tests.evidence_seed import insert, publish, seed_evidence

pytestmark = pytest.mark.integration


def test_instant_period_nulls_are_one_identity(db_admin):
    insert(db_admin, "periods", id=uuid4(), period_kind="instant", end_date="2024-12-31")
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert(db_admin, "periods", id=uuid4(), period_kind="instant", end_date="2024-12-31")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_values_are_not_missing(db_admin, value):
    with pytest.raises(psycopg.errors.CheckViolation):
        seed_evidence(db_admin, value=Decimal(value))


def test_numeric_value_preserves_arbitrary_precision(db_admin):
    expected = Decimal("99999999999999999999999.000000000000000123456789")
    ids = seed_evidence(db_admin, value=expected, publish_batch=True)
    actual = db_admin.execute(
        "SELECT numeric_value FROM source_observations WHERE id=%s", (ids["observation"],)
    ).fetchone()["numeric_value"]
    assert actual == expected


@pytest.mark.parametrize("status", ["observed", "source_nil", "missing", "ambiguous"])
def test_zero_nil_absence_and_conflict_are_distinct(db_admin, status):
    ids = seed_evidence(db_admin, value=Decimal(0), status=status, publish_batch=True)
    row = db_admin.execute(
        "SELECT r.status,o.value_state,o.numeric_value FROM fact_resolutions r "
        "LEFT JOIN source_observations o ON o.id=r.selected_observation_id WHERE r.id=%s",
        (ids["resolution"],),
    ).fetchone()
    assert row["status"] == status
    assert row["numeric_value"] == (Decimal(0) if status == "observed" else None)
    assert row["value_state"] == {"observed": "numeric", "source_nil": "source_nil"}.get(status)


def test_unknown_concept_rejected(db_admin):
    with pytest.raises(psycopg.errors.CheckViolation):
        seed_evidence(db_admin, concept="invented_free_cash_flow")


def test_cross_issuer_coverage_is_rejected(db_admin):
    first = seed_evidence(db_admin)
    second = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation):
        db_admin.execute(
            "INSERT INTO statement_coverage SELECT %s,batch_id,%s,period_id,statement_family,"
            "period_label,reporting_basis,scope_id,currency_unit_id,authority_class,assurance,"
            "coverage_state,evidence_locator FROM statement_coverage WHERE id=%s",
            (uuid4(), second["filing_version"], first["coverage"]),
        )


def test_publication_requires_missingness_flag(db_admin):
    ids = seed_evidence(db_admin)
    insert(
        db_admin,
        "fact_resolutions",
        id=uuid4(),
        coverage_id=ids["coverage"],
        concept_std="gross_profit",
        semantic_scope_id=ids["scope"],
        unit_id=ids["unit"],
        status="missing",
        reason="The latest source has no gross profit tag",
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="flag"):
        publish(db_admin, ids["batch"])


def test_selected_observation_cannot_cross_period(db_admin):
    ids = seed_evidence(db_admin)
    other = seed_evidence(
        db_admin,
        issuer_id=ids["issuer"],
        scope_id=ids["scope"],
        start_date="2023-01-01",
        end_date="2023-12-31",
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        insert(
            db_admin,
            "fact_resolutions",
            id=uuid4(),
            coverage_id=ids["coverage"],
            concept_std="gross_profit",
            semantic_scope_id=ids["scope"],
            unit_id=ids["unit"],
            status="observed",
            selected_observation_id=other["observation"],
        )


def test_published_batch_cannot_gain_more_children(db_admin):
    ids = seed_evidence(db_admin, publish_batch=True)
    with pytest.raises(psycopg.errors.CheckViolation, match="sealed"):
        insert(
            db_admin,
            "fact_resolutions",
            id=uuid4(),
            coverage_id=ids["coverage"],
            concept_std="gross_profit",
            semantic_scope_id=ids["scope"],
            unit_id=ids["unit"],
            status="missing",
            reason="Late insertion would change a saved batch",
        )


@pytest.mark.parametrize(
    "table,key",
    [
        ("source_observations", "observation"),
        ("fact_resolutions", "resolution"),
        ("source_captures", "capture"),
    ],
)
def test_runtime_cannot_rewrite_evidence(db_admin, db, table, key):
    ids = seed_evidence(db_admin, publish_batch=True)
    db_admin.commit()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute(
            psycopg.sql.SQL("DELETE FROM {} WHERE id=%s").format(psycopg.sql.Identifier(table)),
            (ids[key],),
        )


def test_even_owner_cannot_rewrite_published_evidence(db_admin):
    ids = seed_evidence(db_admin, publish_batch=True)
    with pytest.raises(psycopg.errors.CheckViolation, match="immutable"):
        db_admin.execute(
            "UPDATE source_observations SET numeric_value=200 WHERE id=%s", (ids["observation"],)
        )


def clone_row(connection, table, row_id, **overrides):
    from psycopg.types.json import Jsonb

    row = connection.execute(
        psycopg.sql.SQL("SELECT * FROM {} WHERE id=%s").format(psycopg.sql.Identifier(table)),
        (row_id,),
    ).fetchone()
    values = dict(row)
    values["id"] = uuid4()
    values.update(overrides)
    for key in (
        "descriptor_json",
        "raw_dimensions",
        "transform_metadata",
        "raw_metadata",
        "evidence_references",
    ):
        if key in values and values[key] is not None:
            values[key] = Jsonb(values[key])
    insert(connection, table, **values)
    return values["id"]


def test_success_capture_requires_archived_body(db_admin):
    ids = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation):
        clone_row(
            db_admin,
            "source_captures",
            ids["capture"],
            body_sha256=None,
            blob_key=None,
            byte_count=None,
        )


def test_unknown_dimensions_cannot_be_known_empty(db_admin):
    ids = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation):
        clone_row(
            db_admin,
            "source_observations",
            ids["observation"],
            source_locator="other",
            context_knowledge="unknown",
        )


def test_selected_observation_cannot_have_unknown_scope(db_admin):
    ids = seed_evidence(db_admin)
    observation = clone_row(
        db_admin,
        "source_observations",
        ids["observation"],
        source_locator="unknown-scope",
        semantic_scope_id=None,
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        clone_row(
            db_admin,
            "fact_resolutions",
            ids["resolution"],
            concept_std="gross_profit",
            selected_observation_id=observation,
        )


def test_selected_observation_cannot_change_currency(db_admin):
    ids = seed_evidence(db_admin)
    twd = uuid4()
    insert(
        db_admin,
        "units",
        id=twd,
        unit_key="TWD",
        numerator_measures=["iso4217:TWD"],
        denominator_measures=[],
    )
    observation = clone_row(
        db_admin, "source_observations", ids["observation"], source_locator="twd-value", unit_id=twd
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="currency"):
        clone_row(
            db_admin,
            "fact_resolutions",
            ids["resolution"],
            concept_std="gross_profit",
            selected_observation_id=observation,
            unit_id=twd,
        )


def test_scope_content_hash_collision_is_explicit(db_admin):
    ids = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation, match="collision"):
        clone_row(
            db_admin, "semantic_scopes", ids["scope"], descriptor_json={"ownership": "parent"}
        )


def test_scope_cannot_attach_another_issuers_instrument(db_admin):
    ids = seed_evidence(db_admin)
    other = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        clone_row(
            db_admin,
            "semantic_scopes",
            ids["scope"],
            content_sha256="d" * 64,
            instrument_id=other["security"],
        )


def test_ads_relationship_cannot_cross_issuer(db_admin):
    ids = seed_evidence(db_admin)
    other = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation, match="issuer"):
        insert(
            db_admin,
            "security_relationships",
            id=uuid4(),
            security_id=ids["security"],
            underlying_security_id=other["security"],
            valid_from="2020-01-01",
            underlying_units=5,
            instrument_units=1,
            source_capture_id=ids["capture"],
        )


def test_quote_intervals_are_half_open_and_do_not_overlap(db_admin):
    ids = seed_evidence(db_admin)
    symbol = str(uuid4())
    clone_row(
        db_admin,
        "security_identifiers",
        ids["quote"],
        symbol=symbol,
        valid_from="2020-01-01",
        valid_to="2021-01-01",
    )
    clone_row(
        db_admin,
        "security_identifiers",
        ids["quote"],
        symbol=symbol,
        valid_from="2021-01-01",
        valid_to="2022-01-01",
    )
    with pytest.raises(psycopg.errors.ExclusionViolation):
        clone_row(
            db_admin,
            "security_identifiers",
            ids["quote"],
            symbol=symbol,
            valid_from="2020-12-31",
            valid_to="2021-02-01",
        )


def test_publication_requires_every_selected_capture_in_manifest(db_admin):
    ids = seed_evidence(db_admin)
    capture = clone_row(db_admin, "source_captures", ids["capture"])
    observation = clone_row(
        db_admin, "source_observations", ids["observation"], source_capture_id=capture
    )
    clone_row(
        db_admin,
        "fact_resolutions",
        ids["resolution"],
        concept_std="gross_profit",
        selected_observation_id=observation,
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="manifest"):
        publish(db_admin, ids["batch"])


def test_failed_capture_in_manifest_blocks_publication(db_admin):
    ids = seed_evidence(db_admin)
    capture = clone_row(db_admin, "source_captures", ids["capture"], http_status=503)
    insert(
        db_admin,
        "normalization_inputs",
        batch_id=ids["batch"],
        source_capture_id=capture,
        role="failed_payload",
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="archived input"):
        publish(db_admin, ids["batch"])


def test_failed_batch_cannot_publish_later(db_admin):
    ids = seed_evidence(db_admin)
    db_admin.execute("UPDATE normalization_batches SET state='failed' WHERE id=%s", (ids["batch"],))
    with pytest.raises(psycopg.errors.CheckViolation, match="immutable"):
        publish(db_admin, ids["batch"])


def test_runtime_can_publish_but_cannot_approve_mapping(db_admin, db):
    ids = seed_evidence(db_admin)
    db_admin.commit()
    publish(db, ids["batch"])
    db.commit()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        clone_row(
            db,
            "mapping_revisions",
            ids["mapping"],
            revision_key=str(uuid4()),
            content_sha256="e" * 64,
        )


def test_non_reliance_needs_an_explicit_affected_filing(db_admin):
    ids = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation, match="explicit affected filing"):
        with db_admin.transaction():
            event = seed_event(db_admin, ids)
            insert(db_admin, "filing_event_scopes", event_id=event, period_id=ids["period"])


def test_formal_restatement_requires_supporting_event(db_admin):
    first = seed_evidence(db_admin)
    later = seed_evidence(
        db_admin, issuer_id=first["issuer"], scope_id=first["scope"], filed_date="2025-03-01"
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        insert(
            db_admin,
            "fact_revision_links",
            earlier_resolution_id=first["resolution"],
            later_resolution_id=later["resolution"],
            relation_kind="error_restatement",
            rationale="A changed number alone does not establish an error",
            evidence_reference="test:/changed-number",
        )


def test_revision_graph_rejects_cycles(db_admin):
    first = seed_evidence(db_admin)
    later = seed_evidence(
        db_admin, issuer_id=first["issuer"], scope_id=first["scope"], filed_date="2025-03-01"
    )
    insert(
        db_admin,
        "fact_revision_links",
        earlier_resolution_id=first["resolution"],
        later_resolution_id=later["resolution"],
        relation_kind="comparative_revision",
        rationale="Source explicitly identifies a revised comparative",
        evidence_reference="test:/1",
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="cycle"):
        insert(
            db_admin,
            "fact_revision_links",
            earlier_resolution_id=later["resolution"],
            later_resolution_id=first["resolution"],
            relation_kind="comparative_revision",
            rationale="A reverse edge would create a cycle",
            evidence_reference="test:/2",
        )


def seed_event(db_admin, ids):
    event = uuid4()
    insert(
        db_admin,
        "filing_events",
        id=event,
        issuer_id=ids["issuer"],
        event_kind="non_reliance",
        announced_date="2025-03-01",
        source_filing_version_id=ids["filing_version"],
        evidence_locator="test:/non-reliance",
        description="Fictional explicit notice",
    )
    return event


def test_event_scope_set_seals_at_commit(db_admin):
    ids = seed_evidence(db_admin)
    with db_admin.transaction():
        event = seed_event(db_admin, ids)
        insert(
            db_admin,
            "filing_event_scopes",
            event_id=event,
            filing_id=ids["filing"],
            period_id=ids["period"],
        )
    with pytest.raises(psycopg.errors.CheckViolation, match="sealed"):
        insert(
            db_admin,
            "filing_event_scopes",
            event_id=event,
            filing_id=ids["filing"],
            concept_std="gross_profit",
        )


def test_event_cannot_commit_without_affected_scope(db_admin):
    ids = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation, match="affected scope"):
        with db_admin.transaction():
            seed_event(db_admin, ids)


def test_concurrent_revision_links_cannot_make_a_cycle(db_admin):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    first = seed_evidence(db_admin)
    later = seed_evidence(
        db_admin, issuer_id=first["issuer"], scope_id=first["scope"], filed_date="2025-03-01"
    )
    barrier = Barrier(2)

    def add_edge(earlier_id, later_id):
        with psycopg.connect(db_admin.info.dsn, autocommit=True) as connection:
            connection.execute("SET statement_timeout='5s'")
            barrier.wait(timeout=5)
            try:
                insert(
                    connection,
                    "fact_revision_links",
                    earlier_resolution_id=earlier_id,
                    later_resolution_id=later_id,
                    relation_kind="comparative_revision",
                    rationale="Concurrent graph integrity test",
                    evidence_reference="test:/race",
                )
            except psycopg.errors.CheckViolation as error:
                assert "cycle" in str(error)
                return "cycle"
            return "inserted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        forward = executor.submit(add_edge, first["resolution"], later["resolution"])
        backward = executor.submit(add_edge, later["resolution"], first["resolution"])
        assert sorted([forward.result(timeout=10), backward.result(timeout=10)]) == [
            "cycle",
            "inserted",
        ]


def test_selected_candidate_cannot_be_recorded_as_rejected(db_admin):
    ids = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation, match="selected candidate"):
        insert(
            db_admin,
            "resolution_candidates",
            resolution_id=ids["resolution"],
            observation_id=ids["observation"],
            rule_reference="test:/approved-rule",
            disposition="rejected",
            explanation="Contradicts the recorded selection",
        )


@pytest.mark.parametrize(
    "unit_key,numerator,denominator,concept",
    [
        ("USD/shares", ["iso4217:USD"], ["xbrli:shares"], "eps_basic"),
        ("shares", ["xbrli:shares"], [], "weighted_average_shares_basic"),
    ],
)
def test_reporting_currency_is_distinct_from_share_and_eps_units(
    db_admin, unit_key, numerator, denominator, concept
):
    ids = seed_evidence(db_admin)
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
        source_locator="test:/" + concept,
        unit_id=unit,
    )
    resolution = clone_row(
        db_admin,
        "fact_resolutions",
        ids["resolution"],
        concept_std=concept,
        unit_id=unit,
        selected_observation_id=observation,
    )
    publish(db_admin, ids["batch"])
    row = db_admin.execute(
        "SELECT r.unit_id,c.currency_unit_id FROM fact_resolutions r "
        "JOIN statement_coverage c ON c.id=r.coverage_id WHERE r.id=%s",
        (resolution,),
    ).fetchone()
    assert row["unit_id"] == unit
    assert row["currency_unit_id"] == ids["unit"]


@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE"])
def test_revision_graph_rejects_fixed_snapshot_writes(db_admin, isolation):
    first = seed_evidence(db_admin)
    later = seed_evidence(db_admin, issuer_id=first["issuer"], scope_id=first["scope"])
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="READ COMMITTED"):
        with db_admin.transaction():
            db_admin.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
            db_admin.execute("SELECT count(*) FROM fact_revision_links")
            insert(
                db_admin,
                "fact_revision_links",
                earlier_resolution_id=first["resolution"],
                later_resolution_id=later["resolution"],
                relation_kind="comparative_revision",
                rationale="Fixed snapshot could hide the other edge after advisory lock wait",
                evidence_reference="test:/fixed-snapshot",
            )


def test_listing_closure_preserves_raw_history_and_allows_ticker_reuse(db_admin, db):
    original = seed_evidence(db_admin)
    other = seed_evidence(db_admin)
    raw = db_admin.execute(
        "SELECT * FROM security_identifiers WHERE id=%s", (original["quote"],)
    ).fetchone()
    closure = db.execute(
        "SELECT close_security_identifier(%s,%s,%s) AS id",
        (original["quote"], "2025-01-01", original["capture"]),
    ).fetchone()["id"]
    reused = clone_row(
        db_admin,
        "security_identifiers",
        other["quote"],
        symbol=raw["symbol"],
        exchange_code=raw["exchange_code"],
        valid_from="2025-01-01",
    )
    assert (
        db.execute(
            "SELECT valid_to FROM security_identifiers WHERE id=%s", (original["quote"],)
        ).fetchone()["valid_to"]
        is None
    )
    assert (
        db.execute(
            "SELECT source_capture_id FROM security_identifier_closures WHERE id=%s", (closure,)
        ).fetchone()["source_capture_id"]
        == original["capture"]
    )
    rows = db.execute(
        "SELECT security_id,current_valid_to FROM security_identifier_validity "
        "WHERE quote_identifier_id IN (%s,%s) ORDER BY valid_from",
        (original["quote"], reused),
    ).fetchall()
    assert rows[0]["security_id"] == original["security"]
    assert str(rows[0]["current_valid_to"]) == "2025-01-01"
    assert rows[1]["security_id"] == other["security"]
    assert rows[1]["current_valid_to"] is None


@pytest.mark.parametrize("end", ["2019-12-31", "2020-01-01", "infinity"])
def test_listing_closure_rejects_invalid_end(db_admin, db, end):
    ids = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "SELECT close_security_identifier(%s,%s,%s)", (ids["quote"], end, ids["capture"])
        )


def test_listing_cannot_close_twice(db_admin, db):
    ids = seed_evidence(db_admin)
    db.execute(
        "SELECT close_security_identifier(%s,%s,%s)", (ids["quote"], "2025-01-01", ids["capture"])
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="closed"):
        db.execute(
            "SELECT close_security_identifier(%s,%s,%s)",
            (ids["quote"], "2025-02-01", ids["capture"]),
        )


def test_listing_closure_rejects_archived_error_response(db_admin, db):
    ids = seed_evidence(db_admin)
    failed = clone_row(db_admin, "source_captures", ids["capture"], http_status=503)
    with pytest.raises(psycopg.errors.CheckViolation, match="successful"):
        db.execute(
            "SELECT close_security_identifier(%s,%s,%s)", (ids["quote"], "2025-01-01", failed)
        )


def test_runtime_cannot_edit_current_listing_projection(db_admin, db):
    ids = seed_evidence(db_admin)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute(
            "UPDATE security_identifier_validity SET current_valid_to=%s "
            "WHERE quote_identifier_id=%s",
            ("2025-01-01", ids["quote"]),
        )


def test_listing_closure_and_projection_roll_back_together(db_admin, db):
    ids = seed_evidence(db_admin)
    with pytest.raises(RuntimeError), db.transaction():
        db.execute(
            "SELECT close_security_identifier(%s,%s,%s)",
            (ids["quote"], "2025-01-01", ids["capture"]),
        )
        raise RuntimeError("Simulated failure before transaction commit")
    assert db.execute("SELECT count(*) AS n FROM security_identifier_closures").fetchone()["n"] == 0
    assert (
        db.execute(
            "SELECT current_valid_to FROM security_identifier_validity "
            "WHERE quote_identifier_id=%s",
            (ids["quote"],),
        ).fetchone()["current_valid_to"]
        is None
    )


def test_competing_ticker_reuses_have_one_winner(db_admin, db):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from psycopg.rows import dict_row

    original = seed_evidence(db_admin)
    first = seed_evidence(db_admin)
    second = seed_evidence(db_admin)
    symbol = db.execute(
        "SELECT symbol FROM security_identifiers WHERE id=%s", (original["quote"],)
    ).fetchone()["symbol"]
    db.execute(
        "SELECT close_security_identifier(%s,%s,%s)",
        (original["quote"], "2025-01-01", original["capture"]),
    )
    barrier = Barrier(2)

    def reuse(ids):
        with psycopg.connect(
            db_admin.info.dsn, autocommit=True, row_factory=dict_row
        ) as connection:
            connection.execute("SET ROLE equity_runtime")
            connection.execute("SET statement_timeout='5s'")
            barrier.wait(timeout=5)
            try:
                clone_row(
                    connection,
                    "security_identifiers",
                    ids["quote"],
                    symbol=symbol,
                    valid_from="2025-01-01",
                )
            except psycopg.errors.ExclusionViolation:
                return "conflict"
            return "inserted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reuse, (first, second)))
    assert sorted(results) == ["conflict", "inserted"]
    assert (
        db.execute(
            "SELECT count(*) AS n FROM security_identifiers WHERE symbol=%s", (symbol,)
        ).fetchone()["n"]
        == 2
    )
