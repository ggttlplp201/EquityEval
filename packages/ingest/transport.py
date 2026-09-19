"""Bounded SEC transport: durable attempts, shared dispatch limits and verified archives."""

import math
import random
import re
import time
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.parse import urljoin, urlsplit
from uuid import UUID, uuid4

import httpx
from equity_ingest.archive import (
    ArchiveError,
    BodyLimitExceeded,
    ContentDecodingError,
    LocalArchive,
    TransferIncomplete,
)
from equity_ingest.contracts import (
    AttemptOutcome,
    FetchRequest,
    FetchResult,
    RawRecord,
    ResourceKind,
    SecResource,
    SourceDescriptor,
)
from equity_ingest.limiter import (
    CoordinationUnavailable,
    PermitExpired,
    RateDeferred,
    RequestLimiter,
)
from equity_schema import ingestion
from equity_schema.workflow import Database, Lease, LeaseLost


class AttemptStore(Protocol):
    def validate_record(self, record: RawRecord) -> None: ...
    def guard(self, request: FetchRequest) -> None: ...
    def prepare(
        self,
        request: FetchRequest,
        sequence: int,
        url: str,
        validator: RawRecord | None,
    ) -> UUID: ...
    def dispatched(self, request: FetchRequest, attempt_id: UUID, at: datetime) -> None: ...
    def headers(
        self,
        request: FetchRequest,
        attempt_id: UUID,
        at: datetime,
        status: int,
        headers: ingestion.ResponseHeaders,
    ) -> None: ...
    def finish(
        self,
        request: FetchRequest,
        attempt_id: UUID,
        outcome: ingestion.AttemptOutcome,
        at: datetime,
        *,
        capture: RawRecord | None = None,
        reused: UUID | None = None,
        failure: str | None = None,
    ) -> None: ...


def validate_persisted_record(database: Database, record: RawRecord) -> None:
    if database.info.transaction_status.name != "IDLE":
        raise RuntimeError("Capture validation requires an idle database connection")
    with database.transaction():
        row = database.execute(
            "SELECT c.*, p.policy_revision_id, a.response_headers "
            "FROM source_captures c JOIN capture_policy_links p ON p.capture_id=c.id "
            "LEFT JOIN source_fetch_attempts a ON a.completed_capture_id=c.id "
            "WHERE c.id=%s",
            (record.capture_id,),
        ).fetchone()
    expected = {
        "id": record.capture_id,
        "source_id": record.source_id,
        "source_object_key": record.source_object_key,
        "request_url": record.request_url,
        "request_params_hash": record.request_params_hash,
        "requested_at": record.requested_at,
        "fetched_at": record.fetched_at,
        "completed_at": record.completed_at,
        "http_status": record.http_status,
        "body_sha256": record.body_sha256,
        "byte_count": record.byte_count,
        "blob_key": record.blob_key,
        "content_type": record.content_type,
        "policy_revision_id": record.policy_revision_id,
        "terms_review_reference": record.terms_review_reference,
    }
    if row is None or any(row[key] != value for key, value in expected.items()):
        raise ArchiveError("Capture metadata does not match its persisted identity")
    headers = row["response_headers"] or {}
    if record.etag != headers.get("etag") or record.last_modified != headers.get("last_modified"):
        raise ArchiveError("Conditional validators do not match the archived capture")


class DatabaseAttemptStore:
    """Adapter to the narrow committed PostgreSQL operations; owns no transaction."""

    def __init__(self, database: Database, descriptor: SourceDescriptor) -> None:
        self.database = database
        self.descriptor = descriptor

    def validate_record(self, record: RawRecord) -> None:
        validate_persisted_record(self.database, record)

    @staticmethod
    def _lease(request: FetchRequest) -> Lease:
        if request.lease is None or request.stage_id is None:
            raise ValueError("A live fetch requires a workflow lease and stage")
        return request.lease

    def guard(self, request: FetchRequest) -> None:
        assert request.stage_id is not None
        ingestion.validate_stage_lease(self.database, self._lease(request), request.stage_id)
        with self.database.transaction():
            policy = self.database.execute(
                "SELECT source_id,review_key,licence_label,redistribution_status "
                "FROM source_policy_revisions WHERE id=%s",
                (self.descriptor.policy_revision_id,),
            ).fetchone()
        if (
            policy is None
            or policy["source_id"] != self.descriptor.source_id
            or policy["review_key"] != self.descriptor.terms_review_reference
            or policy["licence_label"] != self.descriptor.licence
            or policy["redistribution_status"] != self.descriptor.redistribution_status
        ):
            raise ValueError("Source descriptor does not match its approved policy revision")

    def prepare(
        self,
        request: FetchRequest,
        sequence: int,
        url: str,
        validator: RawRecord | None,
    ) -> UUID:
        assert request.stage_id is not None
        return ingestion.prepare_attempt(
            self.database,
            self._lease(request),
            request.stage_id,
            ingestion.AttemptRequest(
                request.logical_fetch_id,
                sequence,
                self.descriptor.source_id,
                self.descriptor.policy_revision_id,
                request.resource.object_key,
                url,
                request.resource.params_hash,
                validator.capture_id if validator else None,
                validator.etag if validator else None,
                validator.last_modified if validator else None,
            ),
        )

    def dispatched(self, request: FetchRequest, attempt_id: UUID, at: datetime) -> None:
        ingestion.mark_dispatched(self.database, self._lease(request), attempt_id, at)

    def headers(
        self,
        request: FetchRequest,
        attempt_id: UUID,
        at: datetime,
        status: int,
        headers: ingestion.ResponseHeaders,
    ) -> None:
        ingestion.record_response_headers(
            self.database,
            self._lease(request),
            attempt_id,
            at,
            status,
            headers,
        )

    def finish(
        self,
        request: FetchRequest,
        attempt_id: UUID,
        outcome: ingestion.AttemptOutcome,
        at: datetime,
        *,
        capture: RawRecord | None = None,
        reused: UUID | None = None,
        failure: str | None = None,
    ) -> None:
        metadata = (
            None
            if capture is None
            else ingestion.CaptureMetadata(
                capture.capture_id,
                capture.fetched_at,
                capture.body_sha256,
                capture.blob_key,
                capture.byte_count,
                capture.content_type,
            )
        )
        ingestion.finalize_attempt(
            self.database,
            self._lease(request),
            attempt_id,
            outcome,
            at,
            completed_capture=metadata,
            reused_capture_id=reused,
            failure_code=failure,
        )


def validate_redirect(resource: SecResource, current_url: str, location: str) -> str:
    """Redirects may not change the resolved resource identity or disclose contact elsewhere."""
    if (
        not location
        or len(location) > 2048
        or any(ord(char) <= 32 for char in location)
        or "%" in location
        or "\\" in location
        or ".." in urlsplit(location).path.split("/")
    ):
        raise ValueError("Invalid redirect")
    target = urljoin(current_url, location)
    parsed = urlsplit(target)
    if (
        parsed.scheme != "https"
        or parsed.netloc != urlsplit(resource.url).netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "%" in parsed.path
        or target != resource.url
    ):
        raise ValueError("Redirect changes the approved SEC resource")
    return target


def retry_after_seconds(value: str | None, now: datetime) -> float:
    if value is None:
        return 0.0
    if re.fullmatch(r"[0-9]+", value.strip()):
        delay = int(value.strip())
        maximum = (datetime(9999, 1, 1, tzinfo=UTC) - now).total_seconds()
        return float(delay) if delay < maximum else math.inf
    try:
        date = parsedate_to_datetime(value)
        if date.utcoffset() is None:
            return 0.0
        if date >= datetime(9999, 1, 1, tzinfo=UTC):
            return math.inf
        return max(0.0, (date - now).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return 0.0


class DispatchDeadline(TimeoutError):
    pass


class SecTransport:
    def __init__(
        self,
        descriptor: SourceDescriptor,
        archive: LocalArchive,
        limiter: RequestLimiter,
        attempts: AttemptStore,
        client: httpx.Client,
        contact: str,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
        json_body_limit: int = 32 * 1024 * 1024,
        document_body_limit: int = 64 * 1024 * 1024,
    ) -> None:
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact) or any(
            ord(char) < 32 for char in contact
        ):
            raise ValueError("SEC transport requires a configured contact email")
        if min(json_body_limit, document_body_limit) < 0:
            raise ValueError("Body limits cannot be negative")
        self.descriptor, self.archive, self.limiter = descriptor, archive, limiter
        self.attempts, self.client = attempts, client
        self._user_agent = "EquityEval/0.1 " + contact
        self.monotonic, self.now, self.sleep, self.jitter = monotonic, now, sleep, jitter
        self.json_body_limit, self.document_body_limit = json_body_limit, document_body_limit

    def _verify(self, record: RawRecord, request: FetchRequest) -> None:
        if (
            record.source_id != self.descriptor.source_id
            or record.source_object_key != request.resource.object_key
            or record.request_params_hash != request.resource.params_hash
            or record.request_url != request.resource.url
        ):
            raise ArchiveError("Capture belongs to another source or SEC resource")
        self.attempts.validate_record(record)
        self.archive.read_blob(record.blob_key, record.body_sha256, record.byte_count)

    def fetch(self, request: FetchRequest) -> FetchResult:
        if request.resource.kind not in self.descriptor.resource_kinds:
            raise ValueError("Source does not support this resource kind")
        if request.cache_mode == "replay":
            try:
                for record in request.replay_records:
                    self._verify(record, request)
            except ArchiveError:
                return FetchResult(gaps=("archive_integrity",), completeness="incomplete")
            if not request.replay_records or not all(r.successful for r in request.replay_records):
                return FetchResult(records=request.replay_records, gaps=("capture_unavailable",))
            return FetchResult(
                records=request.replay_records,
                reused_capture_ids=tuple(r.capture_id for r in request.replay_records),
            )
        cached = request.cached_record
        if cached is not None:
            try:
                self._verify(cached, request)
                if not cached.successful:
                    cached = None
            except ArchiveError:
                cached = None
        assert request.lease is not None
        worker_remaining = max(0.0, (request.lease.expires_at - self.now()).total_seconds())
        deadline = self.monotonic() + min(360.0, worker_remaining)
        records: list[RawRecord] = []
        outcomes: list[AttemptOutcome] = []
        current_id: UUID | None = None
        current_status: int | None = None
        url = request.resource.url
        validator = cached if request.cache_mode == "conditional" else None
        if validator is not None and not (validator.etag or validator.last_modified):
            validator = None
        try:
            self.attempts.guard(request)
            if (
                cached is not None
                and request.cache_mode == "reuse"
                and (self.now() - cached.fetched_at <= self.descriptor.freshness_sla)
            ):
                return FetchResult(records=(cached,), reused_capture_ids=(cached.capture_id,))
            for sequence in range(1, 4):
                current_status = None
                current_id = self.attempts.prepare(request, sequence, url, validator)
                try:
                    permit = self.limiter.acquire(deadline=deadline)
                    self.attempts.guard(request)
                    requested_at = self.now()
                    self.attempts.dispatched(request, current_id, requested_at)
                except (RateDeferred, CoordinationUnavailable, PermitExpired) as error:
                    reason = (
                        "rate_deferred"
                        if isinstance(error, RateDeferred)
                        else (
                            "permit_expired"
                            if isinstance(error, PermitExpired)
                            else "coordination_unavailable"
                        )
                    )
                    self.attempts.finish(
                        request, current_id, "cancelled", self.now(), failure=reason
                    )
                    outcomes.append(AttemptOutcome(current_id, "cancelled", reason=reason))
                    return FetchResult(
                        records=tuple(records),
                        attempts=tuple(outcomes),
                        gaps=(reason,),
                        completeness="incomplete",
                        next_eligible_at=error.next_eligible_at
                        if isinstance(error, RateDeferred)
                        else None,
                    )
                dispatch_deadline = min(deadline, self.monotonic() + 120.0)

                def check_deadline(limit: float = dispatch_deadline) -> None:
                    if self.monotonic() >= limit:
                        raise DispatchDeadline("SEC dispatch deadline exceeded")

                headers = {
                    "User-Agent": self._user_agent,
                    "Accept-Encoding": "gzip, deflate",
                    "Accept": "application/json"
                    if request.resource.kind != ResourceKind.FILING_DOCUMENT
                    else "text/html,application/xml,text/plain",
                }
                if validator is not None:
                    if validator.etag:
                        headers["If-None-Match"] = validator.etag
                    if validator.last_modified:
                        headers["If-Modified-Since"] = validator.last_modified
                timeout = max(0.001, dispatch_deadline - self.monotonic())
                try:
                    check_deadline()
                    # Build an isolated request: a caller's client defaults must never add
                    # unrelated credentials, cookies, query parameters or authorization.
                    timeout_policy = httpx.Timeout(min(30.0, timeout), connect=min(10.0, timeout))
                    http_request = httpx.Request(
                        "GET",
                        url,
                        headers=headers,
                        extensions={"timeout": timeout_policy.as_dict()},
                    )
                    # No database/network bookkeeping or request construction follows
                    # confirmation: expired permits cannot accumulate into delayed starts.
                    try:
                        self.limiter.confirm(permit)
                    except (CoordinationUnavailable, PermitExpired) as error:
                        reason = (
                            "permit_expired"
                            if isinstance(error, PermitExpired)
                            else ("coordination_unavailable")
                        )
                        self.attempts.finish(
                            request,
                            current_id,
                            "cancelled",
                            self.now(),
                            failure=reason,
                        )
                        outcomes.append(AttemptOutcome(current_id, "cancelled", reason=reason))
                        return FetchResult(
                            records=tuple(records),
                            attempts=tuple(outcomes),
                            gaps=(reason,),
                            completeness="incomplete",
                        )
                    with closing(
                        self.client.send(
                            http_request,
                            stream=True,
                            follow_redirects=False,
                            auth=None,
                        )
                    ) as response:
                        current_status = response.status_code
                        headers_at = self.now()
                        target: str | None = None
                        location = response.headers.get("location")
                        if current_status in {301, 302, 303, 307, 308} and location:
                            try:
                                target = validate_redirect(request.resource, url, location)
                            except ValueError:
                                pass
                        try:
                            evidence = ingestion.ResponseHeaders(
                                content_type=self._header(response, "content-type"),
                                content_encoding=self._header(response, "content-encoding"),
                                etag=self._header(response, "etag"),
                                last_modified=self._header(response, "last-modified"),
                                retry_after=self._header(response, "retry-after"),
                                location=target,
                            )
                        except ContentDecodingError:
                            self.attempts.headers(
                                request,
                                current_id,
                                headers_at,
                                current_status,
                                ingestion.ResponseHeaders(),
                            )
                            raise
                        self.attempts.headers(
                            request, current_id, headers_at, current_status, evidence
                        )
                        check_deadline()
                        if current_status == 304:
                            try:
                                if validator is None:
                                    raise ArchiveError(
                                        "304 has no verified conditional representation"
                                    )
                                self._verify(validator, request)
                                check_deadline()
                            except ArchiveError:
                                self.attempts.finish(
                                    request,
                                    current_id,
                                    "transport_error",
                                    self.now(),
                                    failure="invalid_not_modified",
                                )
                                outcomes.append(
                                    AttemptOutcome(
                                        current_id, "transport_error", 304, "invalid_not_modified"
                                    )
                                )
                                validator = None
                                continue
                            self.attempts.finish(
                                request,
                                current_id,
                                "not_modified",
                                self.now(),
                                reused=validator.capture_id,
                            )
                            outcomes.append(AttemptOutcome(current_id, "not_modified", 304))
                            return FetchResult(
                                records=tuple(records) + (validator,),
                                attempts=tuple(outcomes),
                                reused_capture_ids=(validator.capture_id,),
                            )
                        limit = (
                            self.document_body_limit
                            if request.resource.kind == ResourceKind.FILING_DOCUMENT
                            else self.json_body_limit
                        )
                        capture_id = uuid4()
                        length_text = response.headers.get("content-length")
                        if length_text is not None and not re.fullmatch(r"[0-9]+", length_text):
                            raise TransferIncomplete("Invalid Content-Length")
                        body = self.archive.write(
                            response.iter_raw(),
                            source_key=self.descriptor.source_key,
                            source_object_key=request.resource.object_key,
                            params_hash=request.resource.params_hash,
                            capture_id=capture_id,
                            retrieved_at=headers_at,
                            max_bytes=limit,
                            content_encoding=evidence.content_encoding,
                            expected_wire_bytes=int(length_text)
                            if length_text is not None
                            else None,
                            check_deadline=check_deadline,
                        )
                        check_deadline()
                        finished = self.now()
                        capture = RawRecord(
                            capture_id,
                            self.descriptor.source_id,
                            request.resource.object_key,
                            url,
                            request.resource.params_hash,
                            requested_at,
                            finished,
                            finished,
                            current_status,
                            body.body_sha256,
                            body.byte_count,
                            body.blob_key,
                            evidence.content_type,
                            self.descriptor.policy_revision_id,
                            self.descriptor.terms_review_reference,
                            evidence.etag,
                            evidence.last_modified,
                        )
                        if 200 <= current_status < 300:
                            self.attempts.finish(
                                request, current_id, "complete", finished, capture=capture
                            )
                            outcomes.append(AttemptOutcome(current_id, "complete", current_status))
                            records.append(capture)
                            return FetchResult(records=tuple(records), attempts=tuple(outcomes))
                        if 300 <= current_status < 400:
                            outcome: ingestion.AttemptOutcome = (
                                "redirected" if target and sequence < 3 else "redirect_refused"
                            )
                            self.attempts.finish(
                                request,
                                current_id,
                                outcome,
                                finished,
                                capture=capture,
                                failure=None if outcome == "redirected" else "redirect_refused",
                            )
                            outcomes.append(AttemptOutcome(current_id, outcome, current_status))
                            records.append(capture)
                            if outcome == "redirect_refused":
                                return FetchResult(
                                    records=tuple(records),
                                    attempts=tuple(outcomes),
                                    gaps=("redirect_refused",),
                                    completeness="incomplete",
                                )
                            assert target is not None
                            url, validator = target, None
                            continue
                        self.attempts.finish(
                            request, current_id, "http_error", finished, capture=capture
                        )
                        records.append(capture)
                        outcomes.append(AttemptOutcome(current_id, "http_error", current_status))
                        delay = retry_after_seconds(evidence.retry_after, self.now())
                        if not math.isfinite(delay):
                            self.limiter.cooldown(math.inf)
                            return FetchResult(
                                records=tuple(records),
                                attempts=tuple(outcomes),
                                gaps=("retry_after_requires_review",),
                                completeness="incomplete",
                            )
                        if current_status in {403, 429} or delay:
                            if current_status == 403:
                                delay = max(600.0, delay)
                            if current_status == 429:
                                delay = max(1.0, delay)
                            eligible = self.limiter.cooldown(delay)
                            if current_status == 403 or self.monotonic() + delay >= deadline:
                                return FetchResult(
                                    records=tuple(records),
                                    attempts=tuple(outcomes),
                                    gaps=("source_access_deferred",),
                                    completeness="incomplete",
                                    next_eligible_at=eligible,
                                )
                        if current_status not in {408, 429, 500, 502, 503, 504}:
                            return FetchResult(
                                records=tuple(records),
                                attempts=tuple(outcomes),
                                gaps=("http_error",),
                                completeness="incomplete",
                            )
                except (httpx.TransportError, DispatchDeadline, TransferIncomplete) as error:
                    reason = (
                        "dispatch_deadline"
                        if isinstance(error, DispatchDeadline)
                        else "transfer_incomplete"
                    )
                    self.attempts.finish(
                        request, current_id, "transport_error", self.now(), failure=reason
                    )
                    outcomes.append(
                        AttemptOutcome(current_id, "transport_error", current_status, reason)
                    )
                except (ArchiveError, OSError) as error:
                    outcome = (
                        "body_limit"
                        if isinstance(error, BodyLimitExceeded)
                        else (
                            "transport_error"
                            if isinstance(error, ContentDecodingError)
                            else "archive_error"
                        )
                    )
                    self.attempts.finish(request, current_id, outcome, self.now(), failure=outcome)
                    outcomes.append(AttemptOutcome(current_id, outcome, current_status, outcome))
                    return FetchResult(
                        records=tuple(records),
                        attempts=tuple(outcomes),
                        gaps=(outcome,),
                        completeness="incomplete",
                    )
                if sequence < 3:
                    delay = 2 ** (sequence - 1) + max(0.0, min(1.0, self.jitter()))
                    if not math.isfinite(delay) or self.monotonic() + delay >= deadline:
                        break
                    self.sleep(delay)
            return FetchResult(
                records=tuple(records),
                attempts=tuple(outcomes),
                gaps=("dispatch_budget_exhausted",),
                completeness="incomplete",
            )
        except LeaseLost:
            return FetchResult(
                records=tuple(records),
                attempts=tuple(outcomes),
                gaps=("lease_lost",),
                completeness="incomplete",
            )
        except CoordinationUnavailable:
            return FetchResult(
                records=tuple(records),
                attempts=tuple(outcomes),
                gaps=("coordination_unavailable",),
                completeness="incomplete",
            )

    @staticmethod
    def _header(response: httpx.Response, name: str) -> str | None:
        value = response.headers.get(name)
        if value is None:
            return None
        if len(value.encode("utf-8")) > 4096 or any(ord(char) < 32 for char in value):
            raise ContentDecodingError("Invalid allowlisted response header")
        return str(value)
