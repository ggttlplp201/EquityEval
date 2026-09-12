"""No SEC requests: complete HTTP boundaries through a fake streamed HTTP transport."""

import gzip
import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import FetchRequest, ResourceKind, SecResource, SourceDescriptor
from equity_ingest.limiter import CoordinationUnavailable, Permit, PermitExpired, RateDeferred
from equity_ingest.transport import SecTransport, retry_after_seconds
from equity_schema.workflow import Lease, LeaseLost


class Clock:
    def __init__(self):
        self.seconds = 0.0

    def monotonic(self):
        return self.seconds

    def now(self):
        return datetime(2026, 9, 12, tzinfo=UTC) + timedelta(seconds=self.seconds)

    def sleep(self, seconds):
        self.seconds += seconds


class Limiter:
    def __init__(self, clock):
        self.clock = clock
        self.starts = []
        self.blocked = 0
        self.failure = None

    def acquire(self, *, deadline):
        if self.failure:
            raise self.failure
        if self.blocked >= deadline:
            raise RateDeferred(
                self.clock.now() + timedelta(seconds=self.blocked - self.clock.seconds)
            )
        self.clock.sleep(max(0, self.blocked - self.clock.seconds))
        self.granted_at = self.clock.seconds
        return Permit("test")

    def confirm(self, permit):
        if self.clock.seconds - self.granted_at > 0.05:
            raise PermitExpired("expired")
        self.starts.append(self.clock.seconds)
        return self.clock.now()

    def cooldown(self, seconds):
        self.blocked = self.clock.seconds + seconds
        return (
            datetime(9999, 1, 1, tzinfo=UTC)
            if math.isinf(seconds)
            else (self.clock.now() + timedelta(seconds=seconds))
        )


class Store:
    def __init__(self):
        self.rows = {}
        self.lost = False
        self.lose_on_headers = False
        self.lose_on_finish = False

    def validate_record(self, record):
        pass

    def guard(self, request):
        if self.lost:
            raise LeaseLost("lease lost")

    def prepare(self, request, sequence, url, validator):
        self.guard(request)
        identifier = uuid4()
        self.rows[identifier] = {
            "sequence": sequence,
            "url": url,
            "state": "prepared",
            "validator": validator,
        }
        return identifier

    def dispatched(self, request, attempt_id, at):
        self.guard(request)
        self.rows[attempt_id].update(state="in_progress", requested_at=at)

    def headers(self, request, attempt_id, at, status, headers):
        self.guard(request)
        self.rows[attempt_id].update(http_status=status, headers=headers)
        if self.lose_on_headers:
            self.lost = True

    def finish(self, request, attempt_id, outcome, at, *, capture=None, reused=None, failure=None):
        if self.lose_on_finish:
            self.lost = True
        self.guard(request)
        self.rows[attempt_id].update(state=outcome, capture=capture, reused=reused, failure=failure)


@pytest.fixture
def setup(tmp_path):
    clock = Clock()
    store = Store()
    limiter = Limiter(clock)
    descriptor = SourceDescriptor(
        uuid4(),
        "sec",
        "SEC",
        uuid4(),
        "SEC-v1",
        "public",
        "allowed",
        tuple(ResourceKind),
        timedelta(minutes=15),
    )
    resource = SecResource(uuid4(), "320193", ResourceKind.COMPANY_FACTS)
    lease = Lease(uuid4(), uuid4(), 1, 1, "test", clock.now() + timedelta(minutes=10))
    request = FetchRequest(uuid4(), resource, lease, uuid4())
    return clock, store, limiter, descriptor, request, LocalArchive(tmp_path)


def transport(setup, handler, **kwargs):
    clock, store, limiter, descriptor, _, archive = setup
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SecTransport(
        descriptor,
        archive,
        limiter,
        store,
        client,
        "test@example.invalid",
        now=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        jitter=lambda: 0,
        **kwargs,
    )


def response(status=200, body=b'{"cik":320193}', headers=None):
    return httpx.Response(status, stream=httpx.ByteStream(body), headers=headers or {})


def test_success_archives_before_capture_publication_and_replays_without_http(setup):
    calls = []

    def handler(request):
        calls.append(request)
        assert next(iter(setup[1].rows.values()))["state"] == "in_progress"
        return response(
            body=gzip.compress(b'{"val":1.00}\r\n'),
            headers={"Content-Encoding": "gzip", "ETag": '"v1"'},
        )

    client = transport(setup, handler)
    result = client.fetch(setup[4])
    assert result.usable and len(calls) == 1
    record = result.successful_records[0]
    assert (
        client.archive.read_blob(record.blob_key, record.body_sha256, record.byte_count)
        == b'{"val":1.00}\r\n'
    )
    assert next(iter(setup[1].rows.values()))["capture"] == record
    replay = replace(
        setup[4],
        cache_mode="replay",
        lease=None,
        stage_id=None,
        replay_records=(record,),
        retrieval_cutoff=setup[0].now(),
    )
    assert client.fetch(replay).records == (record,)
    assert len(calls) == 1
    assert "test@example.invalid" not in str(setup[1].rows)


def test_retry_archives_http_error_and_returns_later_success(setup):
    statuses = iter([503, 200])
    client = transport(setup, lambda _: response(next(statuses)))
    result = client.fetch(setup[4])
    assert result.usable
    assert [a.http_status for a in result.attempts] == [503, 200]
    assert [r.http_status for r in result.records] == [503, 200]
    assert len(setup[2].starts) == 2


def test_three_dispatch_budget_includes_redirects(setup):
    client = transport(setup, lambda _: response(302, headers={"Location": setup[4].resource.url}))
    result = client.fetch(setup[4])
    assert [a.outcome for a in result.attempts] == ["redirected", "redirected", "redirect_refused"]
    assert len(setup[2].starts) == 3
    assert not result.usable


@pytest.mark.parametrize(
    "location",
    [
        "https://example.org/x",
        "https://www.sec.gov/x",
        "/submissions/CIK0000320193.json",
        "https://data.sec.gov@evil.test/x",
        "//127.0.0.1/x",
    ],
)
def test_redirect_cannot_change_resource_or_leak_contact(setup, location):
    calls = []

    def handler(request):
        calls.append(request)
        return response(302, headers={"Location": location})

    result = transport(setup, handler).fetch(setup[4])
    assert result.gaps == ("redirect_refused",)
    assert len(calls) == 1
    assert next(iter(setup[1].rows.values()))["headers"].location is None


def test_conditional_304_preserves_capture_identity_and_time(setup):
    client = transport(setup, lambda _: response(headers={"ETag": '"v1"'}))
    original = client.fetch(setup[4]).records[0]
    setup[0].sleep(10)

    def handler(request):
        assert request.headers["If-None-Match"] == '"v1"'
        return response(304, body=b"")

    request = replace(
        setup[4], logical_fetch_id=uuid4(), cache_mode="conditional", cached_record=original
    )
    result = transport(setup, handler).fetch(request)
    assert result.records == (original,)
    assert result.reused_capture_ids == (original.capture_id,)
    assert result.attempts[0].outcome == "not_modified"
    assert result.records[0].fetched_at < setup[0].now()


def test_unsolicited_304_recovers_unconditionally_within_budget(setup):
    statuses = iter([304, 200])
    result = transport(setup, lambda _: response(next(statuses))).fetch(setup[4])
    assert result.usable and len(result.attempts) == 2
    assert result.attempts[0].reason == "invalid_not_modified"


def test_corrupt_cached_archive_cannot_satisfy_304(setup):
    original = (
        transport(setup, lambda _: response(headers={"ETag": '"v1"'})).fetch(setup[4]).records[0]
    )
    (setup[5].root / original.blob_key).write_bytes(b"corrupt")
    seen = []

    def handler(request):
        seen.append(request)
        assert "If-None-Match" not in request.headers
        return response()

    result = transport(setup, handler).fetch(
        replace(
            setup[4], logical_fetch_id=uuid4(), cache_mode="conditional", cached_record=original
        )
    )
    assert result.usable and result.records[0].capture_id != original.capture_id
    assert len(seen) == 1


def test_403_sets_shared_ten_minute_cooldown_and_stops(setup):
    result = transport(setup, lambda _: response(403)).fetch(setup[4])
    assert len(result.attempts) == 1
    assert result.next_eligible_at == setup[0].now() + timedelta(minutes=10)
    assert setup[2].blocked == 600


def test_retry_after_exceeding_budget_defers_without_another_dispatch(setup):
    result = transport(setup, lambda _: response(429, headers={"Retry-After": "400"})).fetch(
        setup[4]
    )
    assert len(result.attempts) == 1
    assert result.next_eligible_at == setup[0].now() + timedelta(seconds=400)


@pytest.mark.parametrize(
    "failure", [CoordinationUnavailable("unavailable"), PermitExpired("expired")]
)
def test_missing_coordinator_or_expired_permit_sends_nothing(setup, failure):
    setup[2].failure = failure
    result = transport(setup, lambda _: pytest.fail("HTTP must not dispatch")).fetch(setup[4])
    assert not result.usable
    assert next(iter(setup[1].rows.values()))["state"] == "cancelled"


def test_lost_lease_before_dispatch_and_after_body_never_publishes(setup):
    setup[1].lost = True
    result = transport(setup, lambda _: pytest.fail("HTTP must not dispatch")).fetch(setup[4])
    assert result.gaps == ("lease_lost",) and not setup[1].rows
    setup[1].lost = False
    setup[1].lose_on_finish = True
    result = transport(setup, lambda _: response()).fetch(setup[4])
    assert result.gaps == ("lease_lost",) and not result.records
    assert next(iter(setup[1].rows.values()))["state"] == "in_progress"
    assert list(setup[5].root.rglob("*.gz"))  # Complete unreferenced evidence stays unselected.


def test_truncated_200_and_decoding_limit_preserve_actual_status(setup):
    result = transport(
        setup,
        lambda _: response(body=gzip.compress(b"body")[:-2], headers={"Content-Encoding": "gzip"}),
    ).fetch(setup[4])
    assert result.gaps == ("transport_error",)
    assert result.attempts[0].http_status == 200
    assert not list(setup[5].root.rglob("*.gz"))
    result = transport(setup, lambda _: response(body=b"too big"), json_body_limit=2).fetch(
        replace(setup[4], logical_fetch_id=uuid4())
    )
    assert result.gaps == ("body_limit",) and not result.records


def test_deadline_during_stream_prevents_capture_publication(setup):
    class Delayed(httpx.SyncByteStream):
        def __iter__(self):
            yield b"first"
            setup[0].sleep(121)
            yield b"late"

    result = transport(setup, lambda _: httpx.Response(200, stream=Delayed())).fetch(setup[4])
    assert not result.usable
    assert all(outcome.reason == "dispatch_deadline" for outcome in result.attempts)
    assert not list(setup[5].root.rglob("*.gz"))


def test_same_body_new_200_retains_distinct_retrieval_identity(setup):
    client = transport(setup, lambda _: response())
    first = client.fetch(setup[4]).records[0]
    setup[0].sleep(1)
    second = client.fetch(replace(setup[4], logical_fetch_id=uuid4())).records[0]
    assert first.body_sha256 == second.body_sha256
    assert first.capture_id != second.capture_id
    assert first.fetched_at < second.fetched_at


def test_http_date_retry_after_and_invalid_values():
    now = datetime(2026, 9, 12, tzinfo=UTC)
    assert retry_after_seconds("Sat, 12 Sep 2026 00:01:00 GMT", now) == 60
    assert retry_after_seconds("not a date", now) == 0
    assert retry_after_seconds("99999999999999999", now) == math.inf
    assert retry_after_seconds("864000", now) == 864000


def test_client_defaults_cannot_send_unrelated_credentials_or_query(setup):
    clock, store, limiter, descriptor, request, archive = setup

    def handler(http_request):
        assert "Authorization" not in http_request.headers
        assert "Cookie" not in http_request.headers
        assert str(http_request.url) == request.resource.url
        return response()

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        auth=("example-user", "example-password"),
        headers={"Authorization": "Bearer fictional-test-token"},
        cookies={"unrelated": "fictional-cookie"},
        params={"unexpected": "field"},
    )
    fetcher = SecTransport(
        descriptor,
        archive,
        limiter,
        store,
        client,
        "test@example.invalid",
        now=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    assert fetcher.fetch(request).usable


def test_wait_beyond_workflow_lease_defers_without_dispatch(setup):
    setup[2].blocked = 40
    request = replace(
        setup[4], lease=replace(setup[4].lease, expires_at=setup[0].now() + timedelta(seconds=30))
    )
    result = transport(setup, lambda _: pytest.fail("Lease deadline prevents HTTP")).fetch(request)
    assert result.gaps == ("rate_deferred",)
    assert setup[0].seconds == 0


def test_known_status_survives_invalid_response_header(setup):
    result = transport(setup, lambda _: response(headers={"ETag": "x" * 4097})).fetch(setup[4])
    assert result.gaps == ("transport_error",)
    assert next(iter(setup[1].rows.values()))["http_status"] == 200


def test_unrepresentable_retry_after_blocks_for_explicit_review(setup):
    result = transport(setup, lambda _: response(429, headers={"Retry-After": "9" * 100})).fetch(
        setup[4]
    )
    assert result.gaps == ("retry_after_requires_review",)
    assert math.isinf(setup[2].blocked)
    assert len(result.attempts) == 1 and result.next_eligible_at is None


def test_slow_request_preparation_cannot_use_expired_dispatch_grant(setup, monkeypatch):
    original = httpx.Request

    def slow_request(*args, **kwargs):
        setup[0].sleep(0.06)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "Request", slow_request)
    result = transport(setup, lambda _: pytest.fail("Expired permit must not dispatch")).fetch(
        setup[4]
    )
    assert result.gaps == ("permit_expired",)
    assert setup[2].starts == []
