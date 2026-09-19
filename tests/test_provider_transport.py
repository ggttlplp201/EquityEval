"""Fake HTTP only: permissions, secret isolation and complete provider archives."""

import gzip
from dataclasses import replace
from datetime import date, timedelta
from uuid import uuid4

import httpx
import pytest
from equity_ingest.archive import LocalArchive
from equity_ingest.provider_contracts import (
    FredResource,
    ProviderDescriptor,
    ProviderFetchRequest,
    ProviderKind,
    TreasuryResource,
)
from equity_ingest.provider_transport import ProviderTransport
from equity_schema.workflow import Lease

from tests.test_ingest_transport import Clock, Limiter, Store, response


class PolicyStore(Store):
    def __init__(self):
        super().__init__()
        self.denied = False

    def guard(self, request):
        super().guard(request)
        if self.denied:
            raise PermissionError("source policy is inactive")


@pytest.fixture
def setup(tmp_path):
    clock = Clock()
    store = PolicyStore()
    limiter = Limiter(clock)
    descriptor = ProviderDescriptor(
        uuid4(),
        "treasury",
        "Treasury",
        uuid4(),
        "fixture-policy",
        "Fictional test-only grant",
        "unknown",
        ProviderKind.TREASURY,
        timedelta(hours=1),
    )
    lease = Lease(uuid4(), uuid4(), 1, 1, "test", clock.now() + timedelta(minutes=10))
    request = ProviderFetchRequest(uuid4(), TreasuryResource("202609"), lease, uuid4())
    return clock, store, limiter, descriptor, request, LocalArchive(tmp_path)


def fetcher(setup, handler, **kwargs):
    clock, store, limiter, descriptor, _, archive = setup
    return ProviderTransport(
        descriptor,
        archive,
        limiter,
        store,
        httpx.Client(
            transport=httpx.MockTransport(handler),
            headers={"Authorization": "UNRELATED"},
            cookies={"unrelated": "cookie"},
            params={"unrelated": "value"},
        ),
        now=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        **kwargs,
    )


def fred_setup(setup):
    clock, store, limiter, descriptor, request, archive = setup
    descriptor = replace(descriptor, provider=ProviderKind.FRED, source_key="fred")
    resource = FredResource("DGS10", date(2024, 1, 1), date(2024, 1, 31), date(2024, 2, 1))
    return clock, store, limiter, descriptor, replace(request, resource=resource), archive


def test_archives_complete_original_entity_then_replays_without_http(setup):
    calls = []

    def handler(request):
        calls.append(request)
        assert "Authorization" not in request.headers and "Cookie" not in request.headers
        assert "unrelated" not in str(request.url)
        return response(
            body=gzip.compress(b"<complete>4.25</complete>"),
            headers={"Content-Encoding": "gzip", "ETag": '"v1"'},
        )

    source = fetcher(setup, handler)
    result = source.fetch(setup[4])
    record = result.successful_records[0]
    assert source.read_verified(record) == b"<complete>4.25</complete>"
    replay = replace(
        setup[4],
        cache_mode="replay",
        lease=None,
        stage_id=None,
        replay_records=(record,),
        retrieval_cutoff=record.completed_at,
    )
    assert source.fetch(replay).records == (record,)
    assert len(calls) == 1


def test_inactive_policy_and_missing_key_prevent_dispatch(setup):
    setup[1].denied = True
    result = fetcher(setup, lambda _: pytest.fail("no HTTP")).fetch(setup[4])
    assert result.gaps == ("source_policy_unavailable",)
    assert not setup[1].rows
    f = fred_setup(setup)
    f[1].denied = False
    assert fetcher(f, lambda _: pytest.fail("no HTTP")).fetch(f[4]).gaps == ("credentials_missing",)


def test_fred_key_only_on_wire_and_never_in_public_identity(setup):
    setup = fred_setup(setup)
    key = "FICTIONAL_SECRET_0123456789"

    def handler(request):
        assert request.url.params["api_key"] == key
        return response(body=b'{"observations":[]}')

    result = fetcher(setup, handler, api_key=key).fetch(setup[4])
    assert result.usable
    assert key not in repr(result) and key not in repr(setup[1].rows)
    assert "api_key" not in result.records[0].request_url
    assert key not in str(list(setup[5].root.rglob("*")))


@pytest.mark.parametrize("compressed", [False, True])
def test_reflected_key_across_body_chunks_is_not_archived(setup, compressed):
    setup = fred_setup(setup)
    key = "FICTIONAL_SECRET_0123456789"
    body = b'{"error":"' + key.encode() + b'"}'
    if compressed:
        body = gzip.compress(body)

    class Chunks(httpx.SyncByteStream):
        def __iter__(self):
            for i in range(0, len(body), 3):
                yield body[i : i + 3]

    def handler(_):
        return httpx.Response(
            403, stream=Chunks(), headers={"Content-Encoding": "gzip"} if compressed else {}
        )

    result = fetcher(setup, handler, api_key=key).fetch(setup[4])
    assert result.gaps == ("unsafe_reflected_secret",)
    assert key not in repr(result) and key not in repr(setup[1].rows)
    assert not list(setup[5].root.rglob("*.gz"))
    assert not list(setup[5].root.rglob(".partial-*"))


def test_redirect_refused_without_following_or_recording_secret_location(setup):
    setup = fred_setup(setup)
    key = "FICTIONAL_SECRET_0123456789"
    calls = []

    def handler(request):
        calls.append(request)
        return response(302, b"", {"Location": "https://other.invalid/?api_key=" + key})

    result = fetcher(setup, handler, api_key=key).fetch(setup[4])
    assert result.gaps == ("redirect_refused",) and len(calls) == 1
    assert key not in repr(setup[1].rows)


def test_truncation_and_false_304_cannot_publish_success(setup):
    source = fetcher(setup, lambda _: response(body=b"short", headers={"Content-Length": "10"}))
    assert source.fetch(setup[4]).gaps == ("transfer_incomplete",)
    assert not list(setup[5].root.rglob("*.gz"))
    source = fetcher(setup, lambda _: response(304, b""))
    result = source.fetch(replace(setup[4], logical_fetch_id=uuid4()))
    assert not result.usable
    assert len(result.attempts) <= 3


def test_429_retry_after_preserves_budget_and_complete_error_body(setup):
    source = fetcher(setup, lambda _: response(429, b"busy", {"Retry-After": "400"}))
    result = source.fetch(setup[4])
    assert result.next_eligible_at == setup[0].now() + timedelta(seconds=400)
    assert len(result.attempts) == 1 and result.records[0].http_status == 429


def test_policy_disable_during_fetch_does_not_erase_authorized_complete_capture(setup):
    # Fake store models pinned finalize permission separately from dispatch activation.
    original_finish = setup[1].finish

    def finish(*args, **kwargs):
        setup[1].denied = False
        original_finish(*args, **kwargs)
        setup[1].denied = True

    setup[1].finish = finish

    def handler(_):
        setup[1].denied = True
        return response()

    # Headers/finalize are pinned operations; activation is checked before dispatch.
    original_headers = setup[1].headers

    def headers(*args, **kwargs):
        setup[1].denied = False
        original_headers(*args, **kwargs)
        setup[1].denied = True

    setup[1].headers = headers
    result = fetcher(setup, handler).fetch(setup[4])
    assert result.usable


def test_http_library_logs_never_expose_query_credential(setup, caplog, monkeypatch):
    import logging

    monkeypatch.setattr(logging.getLogger("httpx"), "disabled", False)
    setup = fred_setup(setup)
    key = "FICTIONAL_SECRET_0123456789"
    with caplog.at_level("DEBUG"):
        result = fetcher(setup, lambda _: response(body=b'{"observations":[]}'), api_key=key).fetch(
            setup[4]
        )
    assert result.usable
    assert key not in caplog.text


def test_transport_body_limits_cannot_exceed_account_reservation(setup):
    from equity_ingest.provider_contracts import PROVIDER_BODY_LIMIT

    with pytest.raises(ValueError):
        fetcher(setup, lambda _: response(), body_limit=PROVIDER_BODY_LIMIT + 1)


def test_budget_denial_is_distinct_from_source_permission(setup):
    from equity_ingest.provider_store import ProviderBudgetExceeded

    def exhausted(*args):
        raise ProviderBudgetExceeded("fixture")

    setup[1].prepare = exhausted
    result = fetcher(setup, lambda _: pytest.fail("no dispatch")).fetch(setup[4])
    assert result.gaps == ("provider_budget_exhausted",)


def test_auth_log_suppression_ends_after_fetch(setup, caplog, monkeypatch):
    import logging

    setup = fred_setup(setup)
    key = "FICTIONAL_SECRET_0123456789"
    monkeypatch.setattr(logging.getLogger("httpx"), "disabled", False)
    with caplog.at_level("INFO"):
        fetcher(setup, lambda _: response(), api_key=key).fetch(setup[4])
        logging.getLogger("httpx").info("independent public diagnostic")
    assert key not in caplog.text
    assert "independent public diagnostic" in caplog.text
