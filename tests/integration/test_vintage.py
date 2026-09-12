"""Real-source-capture selection contracts before any upstream adapters exist."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from equity_schema.vintage import SourceObject, prepare_capture_manifest

from tests.evidence_seed import insert, seed_evidence

pytestmark = pytest.mark.integration
BASE = datetime(2026, 9, 12, tzinfo=UTC)


def add_capture(connection, ids, *, at, **overrides):
    values = dict(
        connection.execute(
            "SELECT * FROM source_captures WHERE id=%s", (ids["capture"],)
        ).fetchone()
    )
    values.update(id=uuid4(), requested_at=at, fetched_at=at, completed_at=at)
    values.update(overrides)
    insert(connection, "source_captures", **values)
    return values["id"]


def requirement(connection, ids, *, role="financial_payload"):
    key = connection.execute(
        "SELECT source_object_key FROM source_captures WHERE id=%s", (ids["capture"],)
    ).fetchone()["source_object_key"]
    return SourceObject(source_id=ids["source"], source_object_key=key, role=role)


def test_selects_latest_complete_capture_inside_cutoff(db_admin, db):
    ids = seed_evidence(db_admin)
    requested = (requirement(db_admin, ids),)
    correction = add_capture(db_admin, ids, at=BASE + timedelta(hours=1), body_sha256="b" * 64)
    add_capture(db_admin, ids, at=BASE + timedelta(hours=3), body_sha256="c" * 64)
    before = prepare_capture_manifest(db, requirements=requested, captured_before=BASE)
    after = prepare_capture_manifest(
        db, requirements=requested, captured_before=BASE + timedelta(hours=2)
    )
    assert before.capture_ids == (ids["capture"],)
    assert after.capture_ids == (correction,)
    assert after.requirements == requested and after.usable
    assert after.flags == after.failed_capture_ids == ()
    assert prepare_capture_manifest(db, requirements=requested, captured_before=BASE) == before


def test_retrieval_in_2026_cannot_supply_a_2018_vintage(db_admin, db):
    ids = seed_evidence(db_admin)
    result = prepare_capture_manifest(
        db,
        requirements=(requirement(db_admin, ids),),
        captured_before=datetime(2018, 1, 1, tzinfo=UTC),
    )
    assert result.capture_ids == ()
    assert "capture_unavailable" in result.flags
    assert not result.usable


def test_capture_not_finished_at_cutoff_cannot_replace_complete_source(db_admin, db):
    ids = seed_evidence(db_admin)
    add_capture(
        db_admin,
        ids,
        at=BASE + timedelta(hours=1),
        completed_at=BASE + timedelta(hours=3),
        body_sha256="b" * 64,
    )
    result = prepare_capture_manifest(
        db, requirements=(requirement(db_admin, ids),), captured_before=BASE + timedelta(hours=2)
    )
    assert result.capture_ids == (ids["capture"],)


def test_same_timestamp_different_bytes_is_ambiguous_without_old_fallback(db_admin, db):
    ids = seed_evidence(db_admin)
    at = BASE + timedelta(hours=1)
    add_capture(db_admin, ids, at=at, body_sha256="b" * 64)
    add_capture(db_admin, ids, at=at, body_sha256="c" * 64)
    result = prepare_capture_manifest(
        db, requirements=(requirement(db_admin, ids),), captured_before=at
    )
    assert result.capture_ids == ()
    assert "ambiguous_capture_vintage" in result.flags
    assert not result.usable


def test_byte_identical_ties_co_reference_in_deterministic_order(db_admin, db):
    ids = seed_evidence(db_admin)
    at = BASE + timedelta(hours=1)
    first = add_capture(db_admin, ids, at=at, body_sha256="b" * 64)
    second = add_capture(db_admin, ids, at=at, body_sha256="b" * 64)
    result = prepare_capture_manifest(
        db, requirements=(requirement(db_admin, ids),), captured_before=at
    )
    assert result.capture_ids == tuple(sorted((first, second), key=str))
    assert result.usable and not result.flags


def test_newer_failed_attempt_preserves_old_capture_with_freshness_evidence(db_admin, db):
    ids = seed_evidence(db_admin)
    failure = add_capture(
        db_admin,
        ids,
        at=BASE + timedelta(hours=1),
        http_status=503,
        fetched_at=None,
        body_sha256=None,
        blob_key=None,
        byte_count=None,
    )
    result = prepare_capture_manifest(
        db, requirements=(requirement(db_admin, ids),), captured_before=BASE + timedelta(hours=2)
    )
    assert result.capture_ids == (ids["capture"],)
    assert result.failed_capture_ids == (failure,)
    assert "newer_capture_failed" in result.flags
    assert result.usable  # valid historical evidence with an explicit freshness warning


def test_failure_before_latest_success_is_not_current_freshness_failure(db_admin, db):
    ids = seed_evidence(db_admin)
    add_capture(
        db_admin,
        ids,
        at=BASE + timedelta(hours=1),
        http_status=None,
        fetched_at=None,
        body_sha256=None,
        blob_key=None,
        byte_count=None,
    )
    latest = add_capture(db_admin, ids, at=BASE + timedelta(hours=2))
    result = prepare_capture_manifest(
        db, requirements=(requirement(db_admin, ids),), captured_before=BASE + timedelta(hours=3)
    )
    assert result.capture_ids == (latest,)
    assert result.failed_capture_ids == result.flags == ()


def test_object_and_source_identity_do_not_substitute_unrelated_captures(db_admin, db):
    ids = seed_evidence(db_admin)
    requested = (
        requirement(db_admin, ids),
        SourceObject(ids["source"], "different-object", "financial_payload"),
        SourceObject(uuid4(), requirement(db_admin, ids).source_object_key, "financial_payload"),
    )
    result = prepare_capture_manifest(db, requirements=requested, captured_before=BASE)
    assert result.capture_ids == (ids["capture"],)
    assert result.requirements == requested
    assert "capture_unavailable" in result.flags and not result.usable


def test_two_roles_share_capture_without_duplicate_fetch_or_capture_ids(db_admin, db):
    ids = seed_evidence(db_admin)
    requested = (requirement(db_admin, ids, role="filing_metadata"), requirement(db_admin, ids))
    before = db_admin.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"]
    result = prepare_capture_manifest(db, requirements=requested, captured_before=BASE)
    assert result.capture_ids == (ids["capture"],)
    assert result.requirements == requested and result.usable
    assert db_admin.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == before


def test_validation_and_transaction_ownership(db_admin, db):
    ids = seed_evidence(db_admin)
    item = requirement(db_admin, ids)
    with pytest.raises(ValueError, match="timezone"):
        prepare_capture_manifest(db, requirements=(item,), captured_before=datetime(2026, 9, 12))
    with pytest.raises(ValueError, match="requirements"):
        prepare_capture_manifest(db, requirements=(item, item), captured_before=BASE)
    with pytest.raises(ValueError, match="requirements"):
        prepare_capture_manifest(db, requirements=(), captured_before=BASE)
    with db.transaction():
        db.execute("SELECT 1")
        with pytest.raises(ValueError, match="idle"):
            prepare_capture_manifest(db, requirements=(item,), captured_before=BASE)


def test_cache_revalidation_does_not_manufacture_a_new_retrieval(db_admin, db):
    ids = seed_evidence(db_admin)
    add_capture(
        db_admin,
        ids,
        at=BASE + timedelta(hours=1),
        http_status=304,
        fetched_at=None,
        body_sha256=None,
        blob_key=None,
        byte_count=None,
    )
    result = prepare_capture_manifest(
        db, requirements=(requirement(db_admin, ids),), captured_before=BASE + timedelta(hours=2)
    )
    assert result.capture_ids == (ids["capture"],)
    assert result.failed_capture_ids == ()
    assert result.usable


def test_only_failed_attempts_return_explicit_gap_and_failure_evidence(db_admin, db):
    ids = seed_evidence(db_admin)
    failure = add_capture(
        db_admin,
        ids,
        at=BASE + timedelta(hours=1),
        source_object_key="unavailable-object",
        http_status=None,
        fetched_at=None,
        body_sha256=None,
        blob_key=None,
        byte_count=None,
    )
    requested = (SourceObject(ids["source"], "unavailable-object", "financial_payload"),)
    result = prepare_capture_manifest(
        db, requirements=requested, captured_before=BASE + timedelta(hours=2)
    )
    assert result.capture_ids == () and not result.usable
    assert result.failed_capture_ids == (failure,)
    assert {"capture_unavailable", "capture_failed"} <= set(result.flags)
