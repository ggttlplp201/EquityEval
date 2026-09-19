"""Bounded market HTTP transport. Public evidence never contains credentials."""

import logging
import math
import re
import time
from collections.abc import Callable
from contextlib import closing
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

import httpx
from equity_schema import ingestion
from equity_schema.workflow import LeaseLost

from .archive import (
    ArchiveError,
    BodyLimitExceeded,
    ContentDecodingError,
    LocalArchive,
    TransferIncomplete,
)
from .contracts import AttemptOutcome, FetchResult, RawRecord
from .limiter import CoordinationUnavailable, PermitExpired, RateDeferred, RequestLimiter
from .provider_contracts import (
    PROVIDER_BODY_LIMIT,
    ProviderDescriptor,
    ProviderFetchRequest,
    ProviderKind,
    ProviderResource,
)
from .provider_store import ProviderBudgetExceeded
from .transport import DispatchDeadline, retry_after_seconds

Request = ProviderFetchRequest[ProviderResource]

# HTTP library debug/info logs can contain raw query keys or response headers.
# Suppress those logs only in the current authenticated retrieval context; retain
# our credential-free durable attempt log and other threads' library diagnostics.
_PRIVATE_HTTP: ContextVar[bool] = ContextVar("equity_private_provider_http", default=False)


class _PrivateHttpFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _PRIVATE_HTTP.get()


_PRIVATE_FILTER = _PrivateHttpFilter()


def _protect_http_logs() -> None:
    for name in ("httpx", *tuple(logging.Logger.manager.loggerDict)):
        if name == "httpx" or name == "httpcore" or name.startswith("httpcore."):
            logging.getLogger(name).addFilter(_PRIVATE_FILTER)


class ProviderAttemptStore(Protocol):
    def validate_record(self, record: RawRecord) -> None: ...
    def guard(self, request: Request) -> None: ...
    def prepare(
        self, request: Request, sequence: int, url: str, validator: RawRecord | None
    ) -> UUID: ...
    def dispatched(self, request: Request, attempt_id: UUID, at: datetime) -> None: ...
    def headers(
        self,
        request: Request,
        attempt_id: UUID,
        at: datetime,
        status: int,
        headers: ingestion.ResponseHeaders,
    ) -> None: ...
    def finish(
        self,
        request: Request,
        attempt_id: UUID,
        outcome: ingestion.AttemptOutcome,
        at: datetime,
        *,
        capture: RawRecord | None = None,
        reused: UUID | None = None,
        failure: str | None = None,
    ) -> None: ...


class ReflectedSecret(ArchiveError):
    pass


class ProviderTransport:
    def __init__(
        self,
        descriptor: ProviderDescriptor,
        archive: LocalArchive,
        limiter: RequestLimiter,
        attempts: ProviderAttemptStore,
        client: httpx.Client,
        *,
        api_key: str | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        body_limit: int = 32 * 1024 * 1024,
    ) -> None:
        if type(body_limit) is not int or not 1 <= body_limit <= PROVIDER_BODY_LIMIT:
            raise ValueError("Positive finite response bound required")
        if api_key is not None and not re.fullmatch(r"[A-Za-z0-9_-]{16,512}", api_key):
            raise ValueError("Invalid credential format")
        self.descriptor, self.archive, self.limiter = descriptor, archive, limiter
        self.attempts, self.client, self._api_key = attempts, client, api_key
        self.now, self.monotonic, self.sleep = now, monotonic, sleep
        self.body_limit = (
            min(body_limit, 8 * 1024 * 1024)
            if descriptor.provider == ProviderKind.TREASURY
            else body_limit
        )

    def read_verified(self, record: RawRecord) -> bytes:
        if record.source_id != self.descriptor.source_id:
            raise ArchiveError("Capture belongs to another source")
        self.attempts.validate_record(record)
        return self.archive.read_blob(record.blob_key, record.body_sha256, record.byte_count)

    def _verify(self, record: RawRecord, request: Request) -> None:
        if (
            record.request_url != request.resource.url
            or record.request_params_hash != request.resource.params_hash
            or record.source_object_key != request.resource.object_key
        ):
            raise ArchiveError("Capture belongs to another resource or request")
        self.read_verified(record)

    def _header(self, response: httpx.Response, name: str) -> str | None:
        value = response.headers.get(name)
        if value is None:
            return None
        if self._api_key and self._api_key in value:
            raise ReflectedSecret("Response contains a credential")
        if len(value.encode()) > 4096 or any(ord(c) < 32 for c in value):
            raise ContentDecodingError("Invalid allowlisted response header")
        return str(value)

    def _scanner(self) -> Callable[[bytes], None]:
        secret = self._api_key.encode() if self._api_key else b""
        tail = b""

        def scan(chunk: bytes) -> None:
            nonlocal tail
            if secret:
                combined = tail + chunk
                if secret in combined:
                    raise ReflectedSecret("Response contains a credential")
                tail = combined[-(len(secret) - 1) :]

        return scan

    def fetch(self, request: Request) -> FetchResult:
        _protect_http_logs()
        token = _PRIVATE_HTTP.set(self._api_key is not None)
        try:
            return self._fetch(request)
        finally:
            _PRIVATE_HTTP.reset(token)

    def _fetch(self, request: Request) -> FetchResult:
        if request.resource.provider != self.descriptor.provider:
            raise ValueError("Provider does not match the resource")
        if request.cache_mode == "replay":
            try:
                for record in request.replay_records:
                    self._verify(record, request)
            except (ArchiveError, PermissionError):
                return FetchResult(gaps=("archive_integrity",), completeness="incomplete")
            if not request.replay_records or not all(r.successful for r in request.replay_records):
                return FetchResult(records=request.replay_records, gaps=("capture_unavailable",))
            return FetchResult(
                records=request.replay_records,
                reused_capture_ids=tuple(r.capture_id for r in request.replay_records),
            )
        if self.descriptor.provider != ProviderKind.TREASURY and not self._api_key:
            return FetchResult(gaps=("credentials_missing",), completeness="incomplete")
        if self.descriptor.provider == ProviderKind.TIINGO and self.descriptor.quota is None:
            return FetchResult(gaps=("account_quota_unreviewed",), completeness="incomplete")
        cached = request.cached_record
        if cached is not None:
            try:
                self._verify(cached, request)
                if not cached.successful:
                    cached = None
            except (ArchiveError, PermissionError):
                cached = None
        assert request.lease is not None
        deadline = self.monotonic() + min(
            360.0, max(0.0, (request.lease.expires_at - self.now()).total_seconds())
        )
        records: list[RawRecord] = []
        outcomes: list[AttemptOutcome] = []
        validator = cached if request.cache_mode == "conditional" else None
        if validator is not None and not (validator.etag or validator.last_modified):
            validator = None

        def result(reason: str, eligible: datetime | None = None) -> FetchResult:
            return FetchResult(
                records=tuple(records),
                attempts=tuple(outcomes),
                gaps=(reason,),
                completeness="incomplete",
                next_eligible_at=eligible,
            )

        try:
            self.attempts.guard(request)
            if (
                cached
                and request.cache_mode == "reuse"
                and self.now() - cached.fetched_at <= self.descriptor.freshness_sla
            ):
                return FetchResult(records=(cached,), reused_capture_ids=(cached.capture_id,))
            for sequence in range(1, 4):
                identifier = self.attempts.prepare(
                    request, sequence, request.resource.url, validator
                )
                status: int | None = None
                try:
                    permit = self.limiter.acquire(deadline=deadline)
                    self.attempts.guard(request)
                    requested_at = self.now()
                    self.attempts.dispatched(request, identifier, requested_at)
                    dispatch_deadline = min(deadline, self.monotonic() + 120.0)

                    def check_deadline(limit: float = dispatch_deadline) -> None:
                        if self.monotonic() >= limit:
                            raise DispatchDeadline("Provider dispatch deadline exceeded")

                    check_deadline()
                    headers = {"User-Agent": "EquityEval/0.1", "Accept-Encoding": "gzip, deflate"}
                    params = dict(request.resource.params)
                    if self.descriptor.provider == ProviderKind.FRED:
                        assert self._api_key is not None
                        params["api_key"] = self._api_key
                    elif self.descriptor.provider == ProviderKind.TIINGO:
                        headers["Authorization"] = "Token " + str(self._api_key)
                    if validator:
                        if validator.etag:
                            headers["If-None-Match"] = validator.etag
                        if validator.last_modified:
                            headers["If-Modified-Since"] = validator.last_modified
                    timeout = max(0.001, dispatch_deadline - self.monotonic())
                    http_request = httpx.Request(
                        "GET",
                        request.resource.url,
                        params=params,
                        headers=headers,
                        extensions={
                            "timeout": httpx.Timeout(
                                min(30.0, timeout), connect=min(10.0, timeout)
                            ).as_dict()
                        },
                    )
                    self.limiter.confirm(permit)
                    with closing(
                        self.client.send(
                            http_request, stream=True, follow_redirects=False, auth=None
                        )
                    ) as response:
                        status, received_at = response.status_code, self.now()
                        # Redirect targets are not evidence fields for authenticated providers.
                        evidence = ingestion.ResponseHeaders(
                            content_type=self._header(response, "content-type"),
                            content_encoding=self._header(response, "content-encoding"),
                            etag=self._header(response, "etag"),
                            last_modified=self._header(response, "last-modified"),
                            retry_after=self._header(response, "retry-after"),
                        )
                        self.attempts.headers(request, identifier, received_at, status, evidence)
                        check_deadline()
                        if status == 304:
                            try:
                                if validator is None:
                                    raise ArchiveError("No verified conditional capture")
                                self._verify(validator, request)
                                check_deadline()
                            except (ArchiveError, PermissionError):
                                self.attempts.finish(
                                    request,
                                    identifier,
                                    "transport_error",
                                    self.now(),
                                    failure="invalid_not_modified",
                                )
                                outcomes.append(
                                    AttemptOutcome(
                                        identifier, "transport_error", 304, "invalid_not_modified"
                                    )
                                )
                                validator = None
                                continue
                            self.attempts.finish(
                                request,
                                identifier,
                                "not_modified",
                                self.now(),
                                reused=validator.capture_id,
                            )
                            outcomes.append(AttemptOutcome(identifier, "not_modified", 304))
                            return FetchResult(
                                records=(*records, validator),
                                attempts=tuple(outcomes),
                                reused_capture_ids=(validator.capture_id,),
                            )
                        length = response.headers.get("content-length")
                        if length is not None and not re.fullmatch(r"[0-9]{1,20}", length):
                            raise TransferIncomplete("Invalid response length")
                        capture_id = uuid4()
                        body = self.archive.write(
                            response.iter_raw(),
                            source_key=self.descriptor.source_key,
                            source_object_key=request.resource.object_key,
                            params_hash=request.resource.params_hash,
                            capture_id=capture_id,
                            retrieved_at=received_at,
                            max_bytes=self.body_limit,
                            content_encoding=evidence.content_encoding,
                            expected_wire_bytes=int(length) if length is not None else None,
                            check_deadline=check_deadline,
                            validate_decoded=self._scanner(),
                        )
                        check_deadline()
                        at = self.now()
                        capture = RawRecord(
                            capture_id,
                            self.descriptor.source_id,
                            request.resource.object_key,
                            request.resource.url,
                            request.resource.params_hash,
                            requested_at,
                            at,
                            at,
                            status,
                            body.body_sha256,
                            body.byte_count,
                            body.blob_key,
                            evidence.content_type,
                            self.descriptor.policy_revision_id,
                            self.descriptor.terms_review_reference,
                            evidence.etag,
                            evidence.last_modified,
                        )
                        outcome: ingestion.AttemptOutcome = (
                            "complete"
                            if 200 <= status < 300
                            else "redirect_refused"
                            if 300 <= status < 400
                            else "http_error"
                        )
                        self.attempts.finish(
                            request,
                            identifier,
                            outcome,
                            at,
                            capture=capture,
                            failure="redirect_refused" if outcome == "redirect_refused" else None,
                        )
                        records.append(capture)
                        outcomes.append(AttemptOutcome(identifier, outcome, status))
                        if outcome == "complete":
                            return FetchResult(records=tuple(records), attempts=tuple(outcomes))
                        if outcome == "redirect_refused":
                            return result("redirect_refused")
                        delay = retry_after_seconds(evidence.retry_after, self.now())
                        if not math.isfinite(delay):
                            self.limiter.cooldown(math.inf)
                            return result("retry_after_requires_review")
                        if status in {403, 429} or delay:
                            delay = max(600.0 if status == 403 else 1.0, delay)
                            eligible = self.limiter.cooldown(delay)
                            if status == 403 or self.monotonic() + delay >= deadline:
                                return result("source_access_deferred", eligible)
                        if status not in {408, 429, 500, 502, 503, 504}:
                            return result("http_error")
                except (RateDeferred, CoordinationUnavailable, PermitExpired) as error:
                    reason = (
                        "rate_deferred"
                        if isinstance(error, RateDeferred)
                        else "permit_expired"
                        if isinstance(error, PermitExpired)
                        else "coordination_unavailable"
                    )
                    self.attempts.finish(
                        request, identifier, "cancelled", self.now(), failure=reason
                    )
                    outcomes.append(AttemptOutcome(identifier, "cancelled", status, reason))
                    return result(
                        reason, error.next_eligible_at if isinstance(error, RateDeferred) else None
                    )
                except PermissionError:
                    self.attempts.finish(
                        request,
                        identifier,
                        "cancelled",
                        self.now(),
                        failure="source_policy_unavailable",
                    )
                    outcomes.append(
                        AttemptOutcome(identifier, "cancelled", status, "source_policy_unavailable")
                    )
                    return result("source_policy_unavailable")
                except (ArchiveError, OSError, httpx.TransportError, DispatchDeadline) as error:
                    reason = (
                        "unsafe_reflected_secret"
                        if isinstance(error, ReflectedSecret)
                        else "body_limit"
                        if isinstance(error, BodyLimitExceeded)
                        else "transfer_incomplete"
                        if isinstance(error, (TransferIncomplete, httpx.TransportError))
                        else "dispatch_deadline"
                        if isinstance(error, DispatchDeadline)
                        else "archive_error"
                    )
                    failure_outcome: ingestion.AttemptOutcome = (
                        "body_limit"
                        if reason == "body_limit"
                        else "transport_error"
                        if reason in {"transfer_incomplete", "dispatch_deadline"}
                        else "archive_error"
                    )
                    self.attempts.finish(
                        request, identifier, failure_outcome, self.now(), failure=reason
                    )
                    outcomes.append(AttemptOutcome(identifier, failure_outcome, status, reason))
                    # An incomplete or unsafe response is never substituted with a cache value.
                    return result(reason)
                if sequence < 3:
                    delay = float(2 ** (sequence - 1))
                    if self.monotonic() + delay >= deadline:
                        break
                    self.sleep(delay)
            return result("dispatch_budget_exhausted")
        except LeaseLost:
            return result("lease_lost")
        except ProviderBudgetExceeded:
            return result("provider_budget_exhausted")
        except PermissionError:
            return result("source_policy_unavailable")
