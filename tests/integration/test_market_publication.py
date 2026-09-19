"""Real database publication of fictional, fully archived market evidence."""

import gzip
import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from equity_ingest.archive import ArchiveError, LocalArchive
from equity_ingest.market_normalize import (
    market_input_hash,
    market_output_hash,
    normalize_tiingo,
    normalize_treasury,
)
from equity_ingest.market_publisher import publish_market_bundle
from equity_ingest.publisher import PublicationConflict
from equity_schema.market_data import disable_policy
from equity_schema.workflow import (
    LeaseLost,
    MarketDataRequestPlan,
    RequestOptions,
    add_watchlist_stock,
    claim_next,
    create_workspace_watchlist,
    start_stage,
)
from psycopg.pq import TransactionStatus

from tests.evidence_seed import insert, seed_evidence
from tests.test_market_normalize import market_input, price_body, treasury_xml


def _stage(db, ids, inputs):
    definition = inputs.series_definition
    plan = MarketDataRequestPlan(
        "s4-market-data-v1",
        price_source_id=inputs.source_id if definition is None else None,
        price_start=inputs.requested_start if definition is None else None,
        price_end=inputs.requested_end if definition is None else None,
        macro_source_id=inputs.source_id if definition else None,
        macro_series_keys=(definition.source_series_key,) if definition else (),
        macro_start=inputs.requested_start if definition else None,
        macro_end=inputs.requested_end if definition else None,
        macro_source_as_of_date=inputs.source_as_of_date,
    )
    workspace = create_workspace_watchlist(db, name="Archived market publication fixture")
    add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key=uuid4().hex,
        options=RequestOptions(market_plan=plan, retrieval_vintage=inputs.retrieval_cutoff),
    )
    lease = claim_next(db, worker_id=uuid4().hex, lease_seconds=300)
    assert lease
    stage = start_stage(
        db,
        lease,
        stage_key="macro_normalization_0000000000000000" if definition else "price_normalization",
    )
    return lease, stage


def prepared(db_admin, db, tmp_path, *, kind="macro", cutoff=None):
    ids = seed_evidence(db_admin)
    origin = "https://home.treasury.gov" if kind == "macro" else "https://api.tiingo.com"
    ids["source"] = uuid4()
    insert(
        db_admin,
        "sources",
        id=ids["source"],
        source_key=uuid4().hex,
        name="Fictional market publication source",
        base_url=origin,
        terms_review_reference="test-only",
        content_scope="Fictional test data only",
    )
    archive = LocalArchive(tmp_path / "archive")
    body = treasury_xml() if kind == "macro" else price_body()
    inputs = market_input(body, kind="treasury" if kind == "macro" else "price")
    captures = []
    for template, content in zip(inputs.captures, (body, b"reviewed"), strict=True):
        from equity_ingest.provider_contracts import PriceResource, TreasuryResource

        resource = (
            TreasuryResource(inputs.treasury_month)
            if kind == "macro"
            else PriceResource(
                ids["quote"], ids["security"], "TEST", inputs.requested_start, inputs.requested_end
            )
        )
        capture = replace(
            template,
            id=uuid4(),
            source_id=ids["source"],
            request_url=resource.url if template.role == "observations" else origin + "/reviewed",
        )
        archived = archive.write(
            [content],
            source_key="fictional",
            source_object_key=capture.source_object_key,
            params_hash="a" * 64,
            capture_id=capture.id,
            retrieved_at=capture.fetched_at,
            max_bytes=len(content),
        )
        insert(
            db_admin,
            "source_captures",
            id=capture.id,
            source_id=capture.source_id,
            source_object_key=capture.source_object_key,
            request_url=capture.request_url,
            request_params_hash="a" * 64,
            requested_at=capture.fetched_at,
            fetched_at=capture.fetched_at,
            completed_at=capture.completed_at,
            http_status=200,
            body_sha256=archived.body_sha256,
            blob_key=archived.blob_key,
            byte_count=archived.byte_count,
            content_type="application/octet-stream",
            terms_review_reference="test-only",
        )
        captures.append(capture)
    policy = db.execute(
        "SELECT policy_revision_id FROM capture_policy_links WHERE capture_id=%s",
        (captures[0].id,),
    ).fetchone()["policy_revision_id"]
    definition = inputs.series_definition
    binding, context = inputs.quote_binding, inputs.quote_context
    inputs = replace(
        inputs,
        source_id=ids["source"],
        policy_revision_id=policy,
        captures=tuple(captures),
        retrieval_cutoff=cutoff,
        series_definition=replace(
            definition, id=uuid4(), source_id=ids["source"], metadata_capture_id=captures[1].id
        )
        if definition
        else None,
        quote_binding=replace(
            binding,
            id=uuid4(),
            source_id=ids["source"],
            quote_identifier_id=ids["quote"],
            security_id=ids["security"],
            identity_capture_id=captures[1].id,
        )
        if binding
        else None,
        quote_context=replace(
            context,
            quote_identifier_id=ids["quote"],
            security_id=ids["security"],
            venue="TEST",
            valid_from=date(2020, 1, 1),
        )
        if context
        else None,
    )
    bundle = normalize_treasury(body, inputs) if definition else normalize_tiingo(body, inputs)
    lease, stage = _stage(db, ids, inputs)
    return ids, archive, bundle, lease, stage


def rehash(bundle):
    bundle = replace(bundle, input_manifest_hash=market_input_hash(bundle.inputs))
    return replace(bundle, output_manifest_hash=market_output_hash(bundle))


def assert_unpublished(db, stage):
    assert db.execute("SELECT count(*) AS n FROM market_data_batches").fetchone()["n"] == 0
    assert (
        db.execute("SELECT state FROM analysis_stage_attempts WHERE id=%s", (stage,)).fetchone()[
            "state"
        ]
        == "running"
    )


@pytest.mark.parametrize("kind", ["macro", "price"])
def test_archived_exact_numeric_publication_and_atomic_stage(db_admin, db, tmp_path, kind):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path, kind=kind)
    published = publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert not published.reused
    assert published.capture_ids == tuple(c.id for c in bundle.inputs.captures)
    manifest = json.loads(archive.read(published.manifest))
    assert manifest["schema"] == "market-publication-v1"
    assert manifest["normalization"]["input_manifest_hash"] == bundle.input_manifest_hash
    assert manifest["normalization"]["output_manifest_hash"] == bundle.output_manifest_hash
    assert len(manifest["evidence"]["captures"]) == 2
    table = "macro_observations" if kind == "macro" else "price_daily"
    row = db.execute(f"SELECT * FROM {table} WHERE batch_id=%s", (published.batch_id,)).fetchone()
    if kind == "macro":
        assert row["value"] == Decimal("4.2500")
        assert row["original_value_text"] == "4.2500"
    else:
        assert row["close"] == Decimal("100") and row["adj_close"] == Decimal("50")
        assert row["close_text"] == "100" and row["adj_close_text"] == "50"
    batch = db.execute(
        "SELECT * FROM market_data_batches WHERE id=%s", (published.batch_id,)
    ).fetchone()
    assert (
        batch["state"] == "published" and batch["manifest_blob_key"] == published.manifest.blob_key
    )
    stage_row = db.execute("SELECT * FROM analysis_stage_attempts WHERE id=%s", (stage,)).fetchone()
    assert stage_row["state"] == "completed"
    assert (
        json.loads(stage_row["error_code"])["manifest_body_sha256"]
        == published.manifest.body_sha256
    )
    assert json.loads(stage_row["error_code"])["batch_id"] == str(published.batch_id)


def test_identical_rerun_reuses_manifest_and_batch(db_admin, db, tmp_path):
    ids, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    first = publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    next_stage = start_stage(db, lease, stage_key="macro_normalization_1111111111111111")
    second = publish_market_bundle(db, bundle, lease=lease, stage_id=next_stage, archive=archive)
    assert second.reused and first.batch_id == second.batch_id and first.manifest == second.manifest
    assert db.execute("SELECT count(*) AS n FROM macro_observations").fetchone()["n"] == 1
    assert len(list(archive.root.glob("market-manifest/**/*.gz"))) == 1


@pytest.mark.parametrize("which", ["observation", "metadata"])
def test_archive_tampering_prevents_any_publication(db_admin, db, tmp_path, which):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    capture = bundle.inputs.captures[which == "metadata"]
    key = db.execute("SELECT blob_key FROM source_captures WHERE id=%s", (capture.id,)).fetchone()[
        "blob_key"
    ]
    (archive.root / key).write_bytes(gzip.compress(b"wrong but syntactically plausible"))
    with pytest.raises(ArchiveError):
        publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)


@pytest.mark.parametrize("which", ["input", "output"])
def test_hash_mutation_is_rejected(db_admin, db, tmp_path, which):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    bundle = replace(bundle, **{which + "_manifest_hash": "0" * 64})
    with pytest.raises(PublicationConflict, match="hash"):
        publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)


def test_forged_capture_snapshot_rejected_even_after_rehash(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    captures = (
        replace(bundle.inputs.captures[0], request_url="https://example.invalid/other"),
        bundle.inputs.captures[1],
    )
    bundle = rehash(replace(bundle, inputs=replace(bundle.inputs, captures=captures)))
    with pytest.raises(PublicationConflict, match="capture"):
        publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)


@pytest.mark.parametrize(
    "field,value", [("quote_currency", "EUR"), ("venue", "OTHER"), ("instrument_kind", "ads")]
)
def test_registered_quote_interpretation_must_match(db_admin, db, tmp_path, field, value):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path, kind="price")
    context = replace(bundle.inputs.quote_context, **{field: value})
    bundle = rehash(replace(bundle, inputs=replace(bundle.inputs, quote_context=context)))
    with pytest.raises(PublicationConflict, match="quote"):
        publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)


def test_wrong_capture_policy_pin_rejected(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    bundle = rehash(replace(bundle, inputs=replace(bundle.inputs, policy_revision_id=uuid4())))
    with pytest.raises(PublicationConflict, match="policy"):
        publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)


def test_cutoff_and_source_mismatch_fail_closed(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    for change in (
        {"retrieval_cutoff": datetime(2026, 9, 11, tzinfo=UTC)},
        {"source_id": uuid4()},
    ):
        wrong = rehash(replace(bundle, inputs=replace(bundle.inputs, **change)))
        with pytest.raises(PublicationConflict):
            publish_market_bundle(db, wrong, lease=lease, stage_id=stage, archive=archive)
        assert_unpublished(db, stage)


def test_stale_lease_cannot_publish_or_finish_stage(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    lease = replace(lease, fencing_token=lease.fencing_token + 1)
    with pytest.raises(LeaseLost):
        publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)


def test_disabled_provider_retained_history_remains_replayable(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    disable_policy(
        db_admin, bundle.inputs.policy_revision_id, actor="fixture", reason="No new fetches"
    )
    result = publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert result.batch_id


def test_archive_io_happens_outside_database_transaction(db_admin, db, tmp_path, monkeypatch):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    original_read, original_write = archive.read_blob, archive.write
    calls = []

    def read(*args, **kwargs):
        assert db.info.transaction_status == TransactionStatus.IDLE
        calls.append("read")
        return original_read(*args, **kwargs)

    def write(*args, **kwargs):
        assert db.info.transaction_status == TransactionStatus.IDLE
        calls.append("write")
        return original_write(*args, **kwargs)

    monkeypatch.setattr(archive, "read_blob", read)
    monkeypatch.setattr(archive, "write", write)
    publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert calls.count("read") >= 2 and calls.count("write") == 1


def test_current_quote_closure_mismatch_prevents_publication(db_admin, db, tmp_path):
    ids, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path, kind="price")
    insert(
        db_admin,
        "security_identifier_closures",
        id=uuid4(),
        quote_identifier_id=ids["quote"],
        valid_to=date(2024, 1, 1),
        source_capture_id=ids["capture"],
    )
    with pytest.raises(PublicationConflict, match="quote"):
        publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)


def test_future_quote_closure_does_not_change_historical_context(db_admin, db, tmp_path):
    cutoff = datetime(2026, 9, 12, 12, tzinfo=UTC)
    ids, archive, bundle, lease, stage = prepared(
        db_admin, db, tmp_path, kind="price", cutoff=cutoff
    )
    late_id = uuid4()
    late_at = cutoff + timedelta(days=1)
    insert(
        db_admin,
        "source_captures",
        id=late_id,
        source_id=ids["source"],
        source_object_key="closure",
        request_url="https://api.tiingo.com/closure",
        request_params_hash="a" * 64,
        requested_at=late_at,
        fetched_at=late_at,
        completed_at=late_at,
        http_status=200,
        body_sha256=hashlib.sha256(b"closure").hexdigest(),
        byte_count=7,
        blob_key="test-only/not-pinned-future-closure.gz",
        terms_review_reference="test-only",
    )
    insert(
        db_admin,
        "security_identifier_closures",
        id=uuid4(),
        quote_identifier_id=ids["quote"],
        valid_to=date(2024, 1, 1),
        source_capture_id=late_id,
    )
    assert publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive).batch_id


def test_failed_sql_publication_reuses_verified_orphan_manifest(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    stale = replace(lease, fencing_token=lease.fencing_token + 1)
    with pytest.raises(LeaseLost):
        publish_market_bundle(db, bundle, lease=stale, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)
    paths = list(archive.root.glob("market-manifest/**/*.gz"))
    assert len(paths) == 1
    result = publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    assert archive.root / result.manifest.blob_key == paths[0]
    assert not result.reused


def test_reuse_verifies_existing_manifest_bytes(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    first = publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    next_stage = start_stage(db, lease, stage_key="macro_normalization_1111111111111111")
    (archive.root / first.manifest.blob_key).write_bytes(gzip.compress(b"forged manifest"))
    with pytest.raises(ArchiveError):
        publish_market_bundle(db, bundle, lease=lease, stage_id=next_stage, archive=archive)
    assert (
        db.execute(
            "SELECT state FROM analysis_stage_attempts WHERE id=%s", (next_stage,)
        ).fetchone()["state"]
        == "running"
    )
    assert db.execute("SELECT count(*) AS n FROM market_data_batches").fetchone()["n"] == 1


def test_operational_disable_does_not_change_existing_manifest(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    first = publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    disable_policy(
        db_admin, bundle.inputs.policy_revision_id, actor="fixture", reason="Stop future dispatch"
    )
    next_stage = start_stage(db, lease, stage_key="macro_normalization_1111111111111111")
    second = publish_market_bundle(db, bundle, lease=lease, stage_id=next_stage, archive=archive)
    assert second.reused and second.manifest == first.manifest


def test_manifest_and_batch_reuse_survive_database_timezone_roundtrip(db_admin, db, tmp_path):
    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    first = publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    local = ZoneInfo("America/Los_Angeles")
    shifted = replace(
        bundle.inputs,
        captures=tuple(
            replace(
                c,
                fetched_at=c.fetched_at.astimezone(local),
                completed_at=c.completed_at.astimezone(local),
            )
            for c in bundle.inputs.captures
        ),
    )
    body = archive.read_blob(
        db.execute(
            "SELECT blob_key FROM source_captures WHERE id=%s", (shifted.captures[0].id,)
        ).fetchone()["blob_key"],
        shifted.captures[0].body_sha256,
        shifted.captures[0].byte_count,
    )
    replay = normalize_treasury(body, shifted)
    next_stage = start_stage(db, lease, stage_key="macro_normalization_1111111111111111")
    second = publish_market_bundle(db, replay, lease=lease, stage_id=next_stage, archive=archive)
    assert second.reused and second.batch_id == first.batch_id
    assert second.manifest == first.manifest


def failed_attempt(db, bundle, lease, stage, *, finish=True):
    from equity_ingest.provider_contracts import TreasuryResource
    from equity_schema.ingestion import AttemptRequest, finalize_attempt, prepare_attempt

    resource = TreasuryResource(bundle.inputs.treasury_month)
    attempt = prepare_attempt(
        db,
        lease,
        stage,
        AttemptRequest(
            uuid4(),
            1,
            bundle.inputs.source_id,
            bundle.inputs.policy_revision_id,
            resource.object_key,
            resource.url,
            resource.params_hash,
        ),
    )
    if finish:
        finalize_attempt(
            db,
            lease,
            attempt,
            "cancelled",
            datetime.now(UTC),
            failure_code="fictional_transport_failure",
        )
    return attempt


def test_failed_request_publishes_unavailable_batch_and_attempt_provenance(db_admin, db, tmp_path):
    from equity_ingest.market_normalize import unavailable_market_bundle
    from equity_schema.market_selection import select_macro

    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    first = publish_market_bundle(db, bundle, lease=lease, stage_id=stage, archive=archive)
    next_stage = start_stage(db, lease, stage_key="macro_normalization_1111111111111111")
    attempt = failed_attempt(db, bundle, lease, next_stage)
    inputs = replace(bundle.inputs, captures=(bundle.inputs.captures[1],), attempt_ids=(attempt,))
    unavailable = unavailable_market_bundle(inputs, "source_request_failed")
    latest = publish_market_bundle(
        db, unavailable, lease=lease, stage_id=next_stage, archive=archive
    )
    assert latest.batch_id != first.batch_id
    manifest = json.loads(archive.read(latest.manifest))
    assert manifest["evidence"]["attempts"][0]["id"] == str(attempt)
    assert manifest["evidence"]["attempts"][0]["state"] == "cancelled"
    result = select_macro(
        db, inputs.source_id, inputs.series_definition.source_series_key, date(2026, 9, 10)
    )
    assert result.batch_id == latest.batch_id and not result.usable
    assert result.value is None and result.attempt_ids == (attempt,)


def test_unfinished_attempt_cannot_be_published_as_immutable_outcome(db_admin, db, tmp_path):
    from equity_ingest.market_normalize import unavailable_market_bundle

    _, archive, bundle, lease, stage = prepared(db_admin, db, tmp_path)
    attempt = failed_attempt(db, bundle, lease, stage, finish=False)
    unavailable = unavailable_market_bundle(
        replace(bundle.inputs, captures=(bundle.inputs.captures[1],), attempt_ids=(attempt,)),
        "source_request_failed",
    )
    with pytest.raises(PublicationConflict, match="attempt"):
        publish_market_bundle(db, unavailable, lease=lease, stage_id=stage, archive=archive)
    assert_unpublished(db, stage)
