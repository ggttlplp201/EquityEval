"""D5i current publication in disposable storage; no application database mutation."""

from dataclasses import replace

import pytest
from equity_ingest.publisher import PublicationConflict, publish_bundle

from tests.evidence_seed import insert

pytestmark = pytest.mark.integration


@pytest.fixture
def current_pair(db_admin):
    from scripts.normalize_crcl import load_preparation
    from scripts.prepare_crcl_observation import prepare
    from scripts.publish_crcl_normalization import register_mapping

    new, _ = prepare()
    old, _ = load_preparation()
    inputs = new.inputs
    insert(
        db_admin,
        "issuers",
        id=inputs.issuer_id,
        cik=inputs.cik,
        legal_name="Fictional D5i test identity",
        first_seen_at=inputs.captured_before,
    )
    source = inputs.captures[0].source_id
    insert(
        db_admin,
        "sources",
        id=source,
        source_key=str(source),
        name="Fictional D5i source",
        base_url="https://example.invalid",
        terms_review_reference="fictional-d5i",
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
            terms_review_reference="fictional-d5i",
        )
    register_mapping(db_admin, old)
    return old, new


def test_current_batch_replay_readback_and_old_flags_are_preserved(current_pair, db_admin, db):
    from scripts.publish_crcl_normalization import readback as old_readback
    from scripts.publish_crcl_normalization import rows_snapshot, verify_preserved
    from scripts.publish_crcl_observation import readback

    old, new = current_pair
    old_result = publish_bundle(db, old)
    before = rows_snapshot(db_admin)
    first = publish_bundle(db, new)
    replay = publish_bundle(db, new)
    assert replay.reused and replay.batch_id == first.batch_id != old_result.batch_id
    selections = readback(db, new, first.batch_id)
    assert selections["as_filed"]["usable_for_valuation"]
    assert not old_readback(db, old, old_result.batch_id)["as_filed"]["usable_for_valuation"]
    assert all(f["value"] is None for f in selections["before_filing"]["facts"])
    verify_preserved(before, rows_snapshot(db_admin))
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 2


def test_current_forged_bundle_does_not_publish(current_pair, db_admin, db):
    from scripts.publish_crcl_normalization import rows_snapshot

    _, new = current_pair
    before = rows_snapshot(db_admin)
    with pytest.raises(PublicationConflict):
        publish_bundle(db, replace(new, output_manifest_hash="f" * 64))
    assert rows_snapshot(db_admin) == before
