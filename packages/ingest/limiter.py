"""One Redis-clock SEC dispatch budget shared by every worker and SEC hostname."""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError


class CoordinationUnavailable(RuntimeError):
    """No request may be sent when the shared coordinator is unavailable."""


class PermitExpired(RuntimeError):
    """A grant cannot be used after expiry; it must be reacquired."""


class RateDeferred(RuntimeError):
    def __init__(self, next_eligible_at: datetime) -> None:
        super().__init__("The shared SEC budget is unavailable before this fetch deadline")
        self.next_eligible_at = next_eligible_at


@dataclass(frozen=True)
class Permit:
    token: str


class RequestLimiter(Protocol):
    def acquire(self, *, deadline: float) -> Permit: ...
    def confirm(self, permit: Permit) -> datetime: ...
    def cooldown(self, seconds: float) -> datetime: ...


# A pending grant is exclusive, short-lived, and must be consumed just before dispatch.
# State loss creates a full one-second quiet period before any new grant is issued.
# All configured rates share the same key; the first configuration is pinned.
RESERVE = """
local t=redis.call('TIME'); local now=tonumber(t[1])+tonumber(t[2])/1000000
local rate=tonumber(ARGV[1]); local token=ARGV[2]
if redis.call('EXISTS',KEYS[1])==0 then
 redis.call('HSET',KEYS[1],'rate',rate,'blocked',now+1,'last',0)
end
if tonumber(redis.call('HGET',KEYS[1],'rate'))~=rate then return {-1,'0'} end
local blocked=tonumber(redis.call('HGET',KEYS[1],'blocked') or '0')
local last=tonumber(redis.call('HGET',KEYS[1],'last') or '0')
local expires=tonumber(redis.call('HGET',KEYS[1],'expires') or '0')
local ready=math.max(blocked,last+1/rate,expires)
if ready>now then return {0,tostring(ready-now),tostring(ready)} end
redis.call('HSET',KEYS[1],'pending',token,'expires',now+0.05)
return {1,tostring(now)}
"""
CONFIRM = """
local t=redis.call('TIME'); local now=tonumber(t[1])+tonumber(t[2])/1000000
if redis.call('HGET',KEYS[1],'pending')~=ARGV[1] then return {0,tostring(now)} end
if tonumber(redis.call('HGET',KEYS[1],'expires') or '0')<now then
 redis.call('HDEL',KEYS[1],'pending','expires'); return {0,tostring(now)}
end
local blocked=tonumber(redis.call('HGET',KEYS[1],'blocked') or '0')
if blocked>now then return {0,tostring(now)} end
redis.call('ZREMRANGEBYSCORE',KEYS[2],'-inf',now-1)
if redis.call('ZCARD',KEYS[2])>=10 then return {0,tostring(now)} end
redis.call('ZADD',KEYS[2],now,ARGV[1])
redis.call('HSET',KEYS[1],'last',now)
redis.call('HDEL',KEYS[1],'pending','expires')
return {1,tostring(now)}
"""
COOLDOWN = """
local t=redis.call('TIME'); local now=tonumber(t[1])+tonumber(t[2])/1000000
local target=ARGV[1]=='review' and 253370764800 or now+tonumber(ARGV[1])
local until_at=math.max(target,tonumber(redis.call('HGET',KEYS[1],'blocked') or '0'))
if redis.call('EXISTS',KEYS[1])==0 then
 redis.call('HSET',KEYS[1],'rate',ARGV[2],'last',0)
end
redis.call('HSET',KEYS[1],'blocked',until_at)
redis.call('HDEL',KEYS[1],'pending','expires')
return tostring(until_at)
"""


class RedisRateLimiter:
    def __init__(
        self,
        client: Redis,
        *,
        key: str = "sec:user",
        requests_per_second: int = 5,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if type(requests_per_second) is not int or not 1 <= requests_per_second <= 10:
            raise ValueError("SEC dispatch configuration must be between 1 and 10 requests/second")
        if not key or "{" in key or "}" in key:
            raise ValueError("Explicit shared limiter identity required")
        options = client.connection_pool.connection_kwargs
        for option in ("socket_timeout", "socket_connect_timeout"):
            value = options.get(option)
            if not isinstance(value, (int, float)) or not 0 < value <= 5:
                raise ValueError(
                    "Redis coordinator requires connect/read timeouts of at most 5 seconds"
                )
        self.client = client
        self.rate = requests_per_second
        self.keys = [f"equity:{{{key}}}:rate", f"equity:{{{key}}}:starts"]
        self.monotonic = monotonic
        self.sleep = sleep

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        key: str = "sec:user",
        requests_per_second: int = 5,
    ) -> "RedisRateLimiter":
        return cls(
            Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5),
            key=key,
            requests_per_second=requests_per_second,
        )

    def _eval(self, script: str, *args: Any) -> Any:
        try:
            return self.client.eval(script, len(self.keys), *self.keys, *args)
        except RedisError as exc:
            raise CoordinationUnavailable("Shared SEC coordination failed") from exc

    def acquire(self, *, deadline: float) -> Permit:
        while True:
            token = uuid4().hex
            result = self._eval(RESERVE, self.rate, token)
            if int(result[0]) == -1:
                raise CoordinationUnavailable("Workers disagree on the shared SEC rate policy")
            if int(result[0]) == 1:
                if self.monotonic() >= deadline:
                    raise RateDeferred(datetime.fromtimestamp(float(result[1]), UTC))
                return Permit(token)
            delay = float(result[1])
            next_time = datetime.fromtimestamp(float(result[2]), UTC)
            if self.monotonic() + delay >= deadline:
                raise RateDeferred(next_time)
            self.sleep(max(0.001, delay))

    def confirm(self, permit: Permit) -> datetime:
        result = self._eval(CONFIRM, permit.token)
        if not int(result[0]):
            raise PermitExpired("SEC dispatch grant expired or was revoked")
        return datetime.fromtimestamp(float(result[1]), UTC)

    def cooldown(self, seconds: float) -> datetime:
        if math.isnan(seconds) or seconds < 0:
            raise ValueError("Cooldown must not be negative or NaN")
        maximum = datetime(9999, 1, 1, tzinfo=UTC).timestamp() - time.time()
        # An unrepresentable Retry-After blocks dispatch until explicit operator review;
        # it must never be shortened into a retry earlier than the server requested.
        requested = "review" if not math.isfinite(seconds) or seconds >= maximum else seconds
        result = self._eval(COOLDOWN, requested, self.rate)
        return datetime.fromtimestamp(float(result), UTC)
