"""Fake SEC HTTP through real Redis, PostgreSQL policy/fences and on-disk archives."""

import gzip
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import FetchRequest, ResourceKind, SecResource, SourceDescriptor
from equity_ingest.limiter import RedisRateLimiter
from equity_ingest.transport import DatabaseAttemptStore, SecTransport
from equity_schema.ingestion import recover_interrupted_attempt
from equity_schema.workflow import (
    add_watchlist_stock,
    cancel_request,
    claim_next,
    create_workspace_watchlist,
    start_stage,
)
from redis import Redis

from tests.evidence_seed import seed_evidence

pytestmark = pytest.mark.integration


@pytest.fixture
def live_transport(db_admin, db, redis_url, tmp_path):
    ids = seed_evidence(db_admin)
    policy = db_admin.execute(
        "SELECT policy_revision_id FROM capture_policy_links WHERE capture_id=%s",
        (ids["capture"],),
    ).fetchone()["policy_revision_id"]
    workspace = create_workspace_watchlist(db, name="Transport integration")
    queued = add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key="transport",
    )
    lease = claim_next(db, worker_id="transport-test")
    stage = start_stage(db, lease, stage_key="source_fetch")
    key = "test:" + uuid4().hex
    descriptor = SourceDescriptor(
        ids["source"],
        str(ids["source"]),
        "Fictional transport source",
        policy,
        "test-only",
        "Fictional test evidence only",
        "unknown",
        tuple(ResourceKind),
        timedelta(minutes=15),
        limiter_key=key,
    )
    resource = SecResource(ids["issuer"], "1", ResourceKind.COMPANY_FACTS)
    request = FetchRequest(uuid4(), resource, lease, stage)
    limiter = RedisRateLimiter(
        Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1), key=key
    )
    archive = LocalArchive(tmp_path)
    store = DatabaseAttemptStore(db, descriptor)

    def make(handler):
        return SecTransport(
            descriptor,
            archive,
            limiter,
            store,
            httpx.Client(transport=httpx.MockTransport(handler)),
            "test@example.invalid",
            jitter=lambda: 0,
            sleep=lambda _: None,
        )

    yield make, request, queued, archive
    limiter.client.delete(*limiter.keys)


def response(status=200, body=b'{"cik":1}', headers=None):
    return httpx.Response(status, stream=httpx.ByteStream(body), headers=headers or {})


def test_complete_capture_and_304_pass_database_guards(db, live_transport):
    make, request, _, archive = live_transport
    original = make(
        lambda _: response(
            body=gzip.compress(b'{"cik":1}'),
            headers={
                "Content-Encoding": "gzip",
                "Content-Type": "application/json",
                "ETag": '"v1"',
            },
        )
    ).fetch(request)
    assert original.usable
    record = original.records[0]
    assert archive.read_blob(record.blob_key, record.body_sha256, record.byte_count) == b'{"cik":1}'
    count = db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"]
    reused = make(lambda _: response(304, b"", {"ETag": '"v1"'})).fetch(
        replace(request, logical_fetch_id=uuid4(), cache_mode="conditional", cached_record=record),
    )
    assert reused.records == (record,) and reused.usable
    assert db.execute("SELECT count(*) AS n FROM source_captures").fetchone()["n"] == count
    assert db.execute(
        "SELECT state,reused_capture_id FROM source_fetch_attempts WHERE id=%s",
        (reused.attempts[0].attempt_id,),
    ).fetchone() == {"state": "not_modified", "reused_capture_id": record.capture_id}


def test_forged_capture_metadata_cannot_be_reused(db, live_transport):
    make, request, _, archive = live_transport
    record = make(lambda _: response(headers={"ETag": '"v1"'})).fetch(request).records[0]
    body = archive.write(
        [b'{"cik":999}'],
        source_key="tampered",
        source_object_key=request.resource.object_key,
        params_hash=request.resource.params_hash,
        capture_id=uuid4(),
        retrieved_at=datetime.now(UTC),
        max_bytes=1024,
    )
    tampered = replace(
        record, body_sha256=body.body_sha256, blob_key=body.blob_key, byte_count=body.byte_count
    )

    def handler(http_request):
        assert "If-None-Match" not in http_request.headers
        return response()

    result = make(handler).fetch(
        replace(
            request,
            logical_fetch_id=uuid4(),
            cache_mode="conditional",
            cached_record=tampered,
        )
    )
    assert result.usable and result.records[0].capture_id != record.capture_id
    assert result.records[0].body_sha256 == record.body_sha256


def test_cancelled_during_transfer_cannot_publish_late_blob(db, live_transport):
    make, request, queued, archive = live_transport

    class Cancelling(httpx.SyncByteStream):
        def __iter__(self):
            cancel_request(db, request_id=queued.request_id)
            yield b"complete body after cancellation"

    result = make(lambda _: httpx.Response(200, stream=Cancelling())).fetch(request)
    assert result.gaps == ("lease_lost",) and not result.records
    row = db.execute(
        "SELECT id,state,completed_capture_id FROM source_fetch_attempts WHERE logical_fetch_id=%s",
        (request.logical_fetch_id,),
    ).fetchone()
    assert row["state"] == "in_progress" and row["completed_capture_id"] is None
    assert list(archive.root.rglob("*.gz"))
    assert recover_interrupted_attempt(db, row["id"])


@pytest.mark.parametrize("status", [302, 300])
def test_refused_3xx_body_is_archived_but_not_financial_success(db, live_transport, status):
    make, request, _, _ = live_transport
    result = make(
        lambda _: response(status, headers={"Location": "https://example.invalid/"})
    ).fetch(request)
    assert result.gaps == ("redirect_refused",) and not result.usable
    assert len(result.records) == 1 and result.records[0].http_status == status
    assert (
        db.execute(
            "SELECT completed_capture_id FROM source_fetch_attempts WHERE id=%s",
            (result.attempts[0].attempt_id,),
        ).fetchone()["completed_capture_id"]
        == result.records[0].capture_id
    )


def test_interrupted_200_keeps_status_and_no_capture(db, live_transport):
    make, request, _, archive = live_transport

    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield b"partial"
            raise httpx.RemoteProtocolError("stream ended before declared response completion")

    result = make(lambda _: httpx.Response(200, stream=Broken())).fetch(request)
    assert not result.usable and len(result.attempts) == 3
    rows = db.execute(
        "SELECT state,http_status,completed_capture_id FROM source_fetch_attempts "
        "WHERE logical_fetch_id=%s",
        (request.logical_fetch_id,),
    ).fetchall()
    assert (
        rows == [{"state": "transport_error", "http_status": 200, "completed_capture_id": None}] * 3
    )
    assert not list(archive.root.rglob("*.gz"))


@pytest.mark.parametrize(
    "claims",
    [
        {"licence": "Public domain without restrictions"},
        {"redistribution_status": "allowed"},
    ],
)
def test_descriptor_cannot_overstate_pinned_source_policy(db, live_transport, claims):
    make, request, _, _ = live_transport
    descriptor = replace(make(lambda _: response()).descriptor, **claims)
    with pytest.raises(ValueError, match="approved policy revision"):
        DatabaseAttemptStore(db, descriptor).guard(request)
    assert db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"] == 0
