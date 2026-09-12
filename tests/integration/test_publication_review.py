"""Independent review regressions for publication provenance and request fencing."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from time import sleep
from uuid import uuid4

import psycopg
import pytest
from equity_ingest import publisher
from equity_ingest.publisher import PublicationConflict, publish_bundle
from equity_ingest.sec_normalize import normalize_verified_bytes
from equity_schema.workflow import (
    LeaseLost,
    add_watchlist_stock,
    claim_next,
    create_workspace_watchlist,
    start_stage,
)
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from tests.evidence_seed import insert, seed_evidence
from tests.normalization_db_seed import seed_normalization_inputs
from tests.sec_normalization_seed import cohort_input

pytestmark = pytest.mark.integration


def _active_stage(db_admin, db, *, issuer_id=None):
    quote = seed_evidence(db_admin, issuer_id=issuer_id)
    workspace = create_workspace_watchlist(db, name="Publication review fixture")
    add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=quote["security"],
        quote_identifier_id=quote["quote"],
        idempotency_key="publication-review",
    )
    lease = claim_next(db, worker_id="publication-review", lease_seconds=30)
    assert lease is not None
    stage = start_stage(db, lease, stage_key="sec_normalization")
    return lease, stage


def test_published_manifest_preserves_preexisting_blocker_and_event_captures(db_admin, db):
    body, inputs = cohort_input("AAPL")
    seed_normalization_inputs(db_admin, inputs)
    publish_bundle(db, normalize_verified_bytes(body, inputs))
    source_filing = db.execute(
        "SELECT fv.id,f.id AS filing_id FROM filing_versions fv JOIN filings f "
        "ON f.id=fv.filing_id WHERE f.issuer_id=%s AND f.accession=%s",
        (inputs.issuer_id, inputs.filings[0].accession),
    ).fetchone()
    flag_id, event_id = uuid4(), uuid4()
    with db_admin.transaction():
        insert(
            db_admin,
            "data_quality_flags",
            id=flag_id,
            issuer_id=inputs.issuer_id,
            rule_key="test_only_existing_review_blocker",
            severity="blocking",
            message="Fictional existing review blocker; not an Apple source assertion",
            evidence_references=Jsonb(["test-only/preexisting-review"]),
            raised_at=inputs.captured_before,
        )
        insert(
            db_admin,
            "filing_events",
            id=event_id,
            issuer_id=inputs.issuer_id,
            event_kind="accounting_recast",
            announced_date=inputs.filings[0].filed_date,
            source_filing_version_id=source_filing["id"],
            evidence_locator="test-only/event-annotation",
            description="Fictional transport-of-provenance fixture; not an Apple event",
        )
        insert(
            db_admin, "filing_event_scopes", event_id=event_id, filing_id=source_filing["filing_id"]
        )
    pinned = replace(inputs, additional_quality_flag_ids=(flag_id,), filing_event_ids=(event_id,))
    bundle = normalize_verified_bytes(body, pinned)
    first = publish_bundle(db, bundle)
    again = publish_bundle(db, bundle)
    for publication in (first, again):
        assert flag_id in publication.quality_flag_ids
        assert publication.additional_quality_flag_ids == (flag_id,)
        assert publication.filing_event_ids == (event_id,)
        assert set(publication.capture_ids) == {capture.id for capture in inputs.captures}
    assert again.reused


def test_request_for_another_issuer_cannot_publish_this_company_bundle(db_admin, db):
    body, inputs = cohort_input("AAPL")
    seed_normalization_inputs(db_admin, inputs)
    lease, stage = _active_stage(db_admin, db)  # Different explicitly fictional issuer.
    before = db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"]
    with pytest.raises((PublicationConflict, LeaseLost), match="issuer"):
        publish_bundle(db, normalize_verified_bytes(body, inputs), lease=lease, stage_id=stage)
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == before


def test_reused_publication_rechecks_lease_after_waiting_for_issuer_lock(
    db_admin, db, test_database_dsn, monkeypatch
):
    body, inputs = cohort_input("AAPL")
    seed_normalization_inputs(db_admin, inputs)
    bundle = normalize_verified_bytes(body, inputs)
    publish_bundle(db, bundle)
    lease, stage = _active_stage(db_admin, db, issuer_id=inputs.issuer_id)
    renewed = Event()
    original_renew = publisher.renew_lease

    def short_renew(connection, lease_value, *, lease_seconds):
        renewed_lease = original_renew(connection, lease_value, lease_seconds=1)
        renewed.set()
        return renewed_lease

    monkeypatch.setattr(publisher, "renew_lease", short_renew)

    def competing_publication():
        with psycopg.connect(
            test_database_dsn, autocommit=True, row_factory=dict_row
        ) as connection:
            connection.execute("SET ROLE equity_runtime")
            return publish_bundle(connection, bundle, lease=lease, stage_id=stage)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with db_admin.transaction():
            db_admin.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                ("normalization:" + str(inputs.issuer_id),),
            )
            pending = pool.submit(competing_publication)
            assert renewed.wait(timeout=5)
            sleep(1.1)  # Actual lease expiry while the worker waits for the issuer lock.
        with pytest.raises(LeaseLost):
            pending.result(timeout=5)
