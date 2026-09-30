"""D5a publication tests in the disposable DB with invented capture identities."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import psycopg
import pytest
from equity_ingest.financial_types import content_hash
from equity_ingest.publisher import PublicationConflict, publish_bundle
from psycopg.rows import dict_row

from scripts.normalize_crcl import prepare
from scripts.publish_crcl_normalization import (
    readback,
    register_mapping,
    rows_snapshot,
    verify_preserved,
)
from tests.evidence_seed import insert
from tests.test_crcl_normalization import retained as retained

pytestmark = pytest.mark.integration


@pytest.fixture
def prepared(retained, db_admin):
    audit, archive = retained
    bundle, _ = prepare(audit, archive)
    inputs = bundle.inputs
    insert(
        db_admin,
        "issuers",
        id=inputs.issuer_id,
        cik=inputs.cik,
        legal_name="Fictional D5a test identity",
        first_seen_at=inputs.captured_before,
    )
    source = inputs.captures[0].source_id
    insert(
        db_admin,
        "sources",
        id=source,
        source_key=str(source),
        name="Fictional D5a source",
        base_url="https://example.invalid",
        terms_review_reference="fictional-d5a",
        content_scope="Tests only",
    )
    for capture in inputs.captures:
        insert(
            db_admin,
            "source_captures",
            id=capture.id,
            source_id=source,
            source_object_key=capture.source_object_key,
            request_url=capture.request_url,
            request_params_hash="0" * 64,
            requested_at=capture.fetched_at,
            completed_at=capture.completed_at,
            fetched_at=capture.fetched_at,
            http_status=200,
            body_sha256=capture.body_sha256,
            blob_key="fictional-test-only.gz",
            byte_count=capture.byte_count,
            content_type="application/json",
            terms_review_reference="fictional-d5a",
        )
    return bundle


def test_owner_approval_publication_replay_and_three_pit_modes(prepared, db_admin, db):
    before = rows_snapshot(db_admin)
    approval = register_mapping(db_admin, prepared)
    assert approval["approved_at"] > prepared.inputs.captured_before
    assert approval == register_mapping(db_admin, prepared)
    first = publish_bundle(db, prepared)
    second = publish_bundle(db, prepared)
    assert first.batch_id == second.batch_id and second.reused and not first.reused
    selected = readback(db, prepared, first.batch_id)
    assert not selected["as_filed"]["usable_for_valuation"]
    assert {str(row["value"]) for row in selected["as_filed"]["facts"]} == {
        "2746642000",
        "-96435000",
    }
    assert all(row["value"] is None for row in selected["before_filing"]["facts"])
    assert "earliest_available" in selected["original"]["flags"]
    assert db.execute("SELECT count(*) AS n FROM filing_events").fetchone()["n"] == 0
    assert db.execute("SELECT count(*) AS n FROM filing_versions").fetchone()["n"] == 3
    verify_preserved(before, rows_snapshot(db_admin))


def test_mapping_drift_and_wrong_identity_do_not_publish(prepared, db_admin, db):
    register_mapping(db_admin, prepared)
    with pytest.raises(PublicationConflict):
        publish_bundle(db, replace(prepared, output_manifest_hash="f" * 64))
    with pytest.raises(ValueError, match="mapping"):
        register_mapping(
            db_admin,
            replace(prepared, inputs=replace(prepared.inputs, mapping_revision_id=uuid4())),
        )
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0


def test_mid_publication_failure_rolls_back_every_row(prepared, db_admin, db, monkeypatch):
    from equity_ingest import publisher

    register_mapping(db_admin, prepared)
    before = rows_snapshot(db_admin)
    original = publisher._insert

    def failing(connection, table, values, **kwargs):
        if table == "fact_resolutions":
            raise RuntimeError("Injected late failure")
        return original(connection, table, values, **kwargs)

    monkeypatch.setattr(publisher, "_insert", failing)
    with pytest.raises(RuntimeError, match="Injected"):
        publish_bundle(db, prepared)
    assert rows_snapshot(db_admin) == before


def test_concurrent_replay_publishes_once(prepared, db_admin, test_database_dsn):
    register_mapping(db_admin, prepared)

    def publish(_):
        with psycopg.connect(
            test_database_dsn, autocommit=True, row_factory=dict_row
        ) as connection:
            return publish_bundle(connection, prepared)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, range(2)))
    assert len({result.batch_id for result in results}) == 1
    assert sorted(result.reused for result in results) == [False, True]
    assert content_hash(rows_snapshot(db_admin))


@pytest.fixture
def application_runtime(prepared, test_database_dsn, monkeypatch):
    from types import SimpleNamespace

    from sqlalchemy.engine import make_url

    from scripts import publish_crcl_normalization as app

    monkeypatch.setattr(app, "load_preparation", lambda: (prepared, {}))
    monkeypatch.setattr(app, "INPUT_HASH", prepared.input_manifest_hash)
    monkeypatch.setattr(app, "OUTPUT_HASH", prepared.output_manifest_hash)
    monkeypatch.setattr(app, "read_audit", lambda _: {})
    monkeypatch.setattr(app, "verify_database_evidence", lambda *_: None)
    monkeypatch.setattr(
        app.app_postgres,
        "configuration",
        lambda: (SimpleNamespace(database="fictional"), make_url(test_database_dsn)),
    )
    monkeypatch.setattr(app.app_postgres, "guard", lambda _: None)
    monkeypatch.setattr(app.app_postgres, "verify", lambda _: None)
    monkeypatch.setattr(
        app.app_postgres,
        "owner_connection",
        lambda *_: psycopg.connect(test_database_dsn, autocommit=True, row_factory=dict_row),
    )
    return app


def test_full_application_orchestration_with_disposable_runtime(application_runtime):
    app = application_runtime
    report = app.application("publish")
    assert report["exact_replay_verified"]
    assert report["prior_rows_preserved"]
    verified = app.application("verify")
    assert verified["before"] == verified["after"]
    assert verified["selections"] == report["selections"]
    assert verified["batch"] == report["batch"]


@pytest.mark.parametrize("field", ["approved_by", "reviewed_scope"])
@pytest.mark.parametrize("action", ["publish", "verify"])
def test_mapping_approval_identity_is_required_for_replay_and_verify(
    prepared, db_admin, db, application_runtime, field, action
):
    from datetime import UTC, datetime

    from scripts.normalize_crcl import REVIEW
    from scripts.publish_crcl_normalization import REVISION

    values = dict(
        id=prepared.inputs.mapping_revision_id,
        revision_key=REVISION,
        content_sha256=content_hash(prepared.inputs.rules),
        code_revision=prepared.inputs.normalizer_revision,
        approved_at=datetime.now(UTC),
        approved_by="D039 / reviewed D5a proposal",
        reviewed_scope=REVIEW + " — two CRCL FY2025 consolidated income concepts only",
    )
    values[field] = "Unreviewed altered approval"
    insert(db_admin, "mapping_revisions", **values)
    if action == "verify":
        publish_bundle(db, prepared)
    before = rows_snapshot(db_admin)
    with pytest.raises(ValueError, match="mapping"):
        application_runtime.application(action)
    assert rows_snapshot(db_admin) == before
