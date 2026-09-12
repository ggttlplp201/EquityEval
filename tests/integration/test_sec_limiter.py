"""Shared Redis state, including independent processes; no upstream HTTP requests."""

import multiprocessing
import time
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from equity_ingest.limiter import (
    CoordinationUnavailable,
    PermitExpired,
    RateDeferred,
    RedisRateLimiter,
)
from redis import Redis

pytestmark = pytest.mark.integration


def dispatch_worker(url, key, count, queue):
    limiter = RedisRateLimiter(
        Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1), key=key
    )
    stamps = []
    for _ in range(count):
        permit = limiter.acquire(deadline=time.monotonic() + 15)
        started = limiter.confirm(permit)
        stamps.append((started.timestamp(), time.time()))
    queue.put(stamps)


def test_shared_budget_across_processes_measures_request_starts(redis_url):
    key = "test:" + uuid4().hex
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    processes = [
        context.Process(target=dispatch_worker, args=(redis_url, key, 3, queue)) for _ in range(3)
    ]
    try:
        for process in processes:
            process.start()
        points = sorted(point for _ in processes for point in queue.get(timeout=20))
        for process in processes:
            process.join(timeout=5)
            assert process.exitcode == 0
        server_starts = [point[0] for point in points]
        actual_starts = sorted(point[1] for point in points)
        assert len(points) == 9
        assert all(
            right - left >= 0.19
            for left, right in zip(server_starts, server_starts[1:], strict=False)
        )
        assert all(
            sum(start <= other < start + 1 for other in actual_starts) <= 10
            for start in actual_starts
        )
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1).delete(
            f"equity:{{{key}}}:rate", f"equity:{{{key}}}:starts"
        )


def test_expired_grants_and_shared_cooldowns(redis_url):
    redis = Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
    key = "test:" + uuid4().hex
    first, second = RedisRateLimiter(redis, key=key), RedisRateLimiter(redis, key=key)
    try:
        permit = first.acquire(deadline=time.monotonic() + 3)
        time.sleep(0.06)
        with pytest.raises(PermitExpired):
            first.confirm(permit)
        first.confirm(first.acquire(deadline=time.monotonic() + 3))
        eligible = first.cooldown(2)
        with pytest.raises(RateDeferred) as deferred:
            second.acquire(deadline=time.monotonic() + 0.1)
        assert abs((deferred.value.next_eligible_at - eligible).total_seconds()) < 0.001
        assert eligible > datetime.now(UTC)
    finally:
        redis.delete(*first.keys)


def test_coordinator_failure_and_conflicting_config_fail_closed(redis_url):
    with pytest.raises(CoordinationUnavailable):
        RedisRateLimiter(
            Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.1, socket_timeout=0.1)
        ).acquire(deadline=time.monotonic() + 1)
    redis = Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
    key = "test:" + uuid4().hex
    first = RedisRateLimiter(redis, key=key)
    try:
        first.confirm(first.acquire(deadline=time.monotonic() + 3))
        with pytest.raises(CoordinationUnavailable):
            RedisRateLimiter(redis, key=key, requests_per_second=10).acquire(
                deadline=time.monotonic() + 1
            )
    finally:
        redis.delete(*first.keys)


def test_state_loss_requires_quiet_window(redis_url):
    redis = Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
    limiter = RedisRateLimiter(redis, key="test:" + uuid4().hex)
    try:
        limiter.confirm(limiter.acquire(deadline=time.monotonic() + 3))
        redis.delete(*limiter.keys)
        with pytest.raises(RateDeferred):
            limiter.acquire(deadline=time.monotonic() + 0.1)
    finally:
        redis.delete(*limiter.keys)


def test_long_retry_after_is_not_shortened_and_unrepresentable_wait_fails_closed(redis_url):
    limiter = RedisRateLimiter.from_url(redis_url, key="test:" + uuid4().hex)
    try:
        until = limiter.cooldown(864000)
        assert (until - datetime.now(UTC)).total_seconds() > 863999
        until = limiter.cooldown(float("inf"))
        assert until.year == 9999
        with pytest.raises(RateDeferred) as stopped:
            limiter.acquire(deadline=time.monotonic() + 0.1)
        assert stopped.value.next_eligible_at.year == 9999
    finally:
        limiter.client.delete(*limiter.keys)


def test_unbounded_redis_io_is_rejected_before_dispatch(redis_url):
    with pytest.raises(ValueError, match="timeouts"):
        RedisRateLimiter(Redis.from_url(redis_url))
