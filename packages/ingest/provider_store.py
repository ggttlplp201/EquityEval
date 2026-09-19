"""Durable provider dispatch reservations under immutable W1 intent.

Only short database transactions are owned here. Account quotas reserve the
maximum permitted wire bytes for every prepared attempt, including cancelled
and interrupted attempts; a restart cannot erase consumption evidence.
"""

from calendar import monthrange
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from equity_ingest.archive import ArchiveError
from equity_ingest.contracts import RawRecord
from equity_ingest.provider_contracts import (
    PROVIDER_WIRE_LIMIT,
    FredResource,
    PriceResource,
    ProviderDescriptor,
    ProviderFetchRequest,
    ProviderKind,
    ProviderResource,
    TreasuryResource,
)
from equity_ingest.transport import validate_persisted_record
from equity_schema import ingestion
from equity_schema.market_data import json_value
from equity_schema.workflow import Database, Lease, LeaseLost
from psycopg.errors import CheckViolation, ObjectNotInPrerequisiteState
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

Request = ProviderFetchRequest[ProviderResource]


def _aware(value: datetime) -> None:
    if value.utcoffset() is None:
        raise ValueError("Provider evidence timestamps require an explicit timezone")


class ProviderBudgetExceeded(PermissionError):
    """No further dispatch reservation is permitted under the reviewed bounds."""


class DatabaseProviderStore:
    def __init__(self, database: Database, descriptor: ProviderDescriptor) -> None:
        self.database, self.descriptor = database, descriptor

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        if self.database.info.transaction_status != TransactionStatus.IDLE:
            raise RuntimeError("Provider transport requires an idle database connection")
        try:
            with self.database.transaction():
                yield
        except ObjectNotInPrerequisiteState as error:
            if str(error).startswith("lease lost"):
                raise LeaseLost("lease lost during provider operation") from None
            raise PermissionError("Provider policy or attempt is unavailable") from None
        except CheckViolation:
            raise PermissionError("Provider request is outside its reviewed policy") from None

    @staticmethod
    def _lease(request: Request) -> Lease:
        if request.lease is None or request.stage_id is None:
            raise ValueError("Live provider fetch requires a lease and stage")
        return request.lease

    def _policy(
        self,
        policy_id: UUID,
        object_key: str,
        *,
        active: bool,
        series: str | None = None,
        normalized: bool = False,
    ) -> None:
        self.database.execute(
            "SELECT market_validate_policy(%s,%s,%s,%s,%s,%s)",
            (policy_id, self.descriptor.source_id, object_key, series, normalized, active),
        )

    def _descriptor(self) -> str:
        row = self.database.execute(
            "SELECT p.source_id,p.review_key,p.licence_label,p.redistribution_status,"
            "s.source_key,s.name,s.base_url FROM source_policy_revisions p "
            "JOIN sources s ON s.id=p.source_id WHERE p.id=%s",
            (self.descriptor.policy_revision_id,),
        ).fetchone()
        expected = {
            "source_id": self.descriptor.source_id,
            "review_key": self.descriptor.terms_review_reference,
            "licence_label": self.descriptor.licence,
            "redistribution_status": self.descriptor.redistribution_status,
            "source_key": self.descriptor.source_key,
            "name": self.descriptor.name,
        }
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise PermissionError("Source descriptor differs from its reviewed policy")
        return str(row["base_url"])

    def validate_record(self, record: RawRecord) -> None:
        if record.source_id != self.descriptor.source_id:
            raise ArchiveError("Capture belongs to another provider")
        validate_persisted_record(self.database, record)
        with self._transaction():
            # Historical capture permission is its original immutable grant.
            self._policy(record.policy_revision_id, record.source_object_key, active=False)

    def _guard(self, request: Request) -> None:
        lease = self._lease(request)
        resource = request.resource
        expected_type = {
            ProviderKind.TREASURY: TreasuryResource,
            ProviderKind.TIINGO: PriceResource,
            ProviderKind.FRED: FredResource,
        }[self.descriptor.provider]
        if type(resource) is not expected_type:
            raise PermissionError("Unreviewed provider resource type")
        self.database.execute(
            "SELECT ingestion_validate_stage(%s,%s)",
            (Jsonb(lease.as_json()), request.stage_id),
        )
        base_url = self._descriptor().rstrip("/")
        parsed = urlsplit(base_url)
        canonical = urlsplit(resource.url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != canonical.netloc
            or parsed.query
            or parsed.fragment
            or not (resource.url == base_url or resource.url.startswith(base_url + "/"))
        ):
            raise PermissionError("Provider resource differs from registered source URL")
        plan = self.database.execute(
            "SELECT * FROM analysis_requests WHERE id=%s", (lease.request_id,)
        ).fetchone()
        if (
            plan is None
            or plan["market_plan_revision"] != "s4-market-data-v1"
            or plan["retrieval_vintage"] is not None
        ):
            raise PermissionError("Live request differs from immutable market plan")
        self._policy(self.descriptor.policy_revision_id, resource.object_key, active=True)
        if isinstance(resource, PriceResource):
            if self.descriptor.quota is None:
                raise PermissionError("Tiingo account quota must be explicitly reviewed")
            if (
                plan["price_source_id"] != self.descriptor.source_id
                or plan["quote_identifier_id"] != resource.quote_identifier_id
                or plan["security_id"] != resource.security_id
                or plan["price_start"] != resource.start
                or plan["price_end"] != resource.end
            ):
                raise PermissionError("Price resource differs from immutable plan")
            binding = self.database.execute(
                "SELECT b.id FROM provider_quote_bindings b "
                "JOIN security_identifiers q ON q.id=b.quote_identifier_id "
                "JOIN source_captures c ON c.id=b.identity_capture_id "
                "WHERE b.source_id=%s AND b.quote_identifier_id=%s AND b.security_id=%s "
                "AND b.provider_symbol=%s AND b.valid_from<=%s "
                "AND (b.valid_to IS NULL OR b.valid_to>%s) "
                "AND q.valid_from<=%s AND (q.valid_to IS NULL OR q.valid_to>%s) "
                "AND NOT EXISTS(SELECT FROM security_identifier_closures x "
                "WHERE x.quote_identifier_id=q.id AND x.valid_to<=%s) "
                "AND b.reviewed_at<=clock_timestamp() AND c.http_status BETWEEN 200 AND 299 "
                "AND c.completed_at<=clock_timestamp() LIMIT 1",
                (
                    self.descriptor.source_id,
                    resource.quote_identifier_id,
                    resource.security_id,
                    resource.provider_symbol,
                    resource.start,
                    resource.end,
                    resource.start,
                    resource.end,
                    resource.end,
                ),
            ).fetchone()
            if binding is None:
                raise PermissionError("No reviewed quote binding covers the full price window")
            self._policy(
                self.descriptor.policy_revision_id,
                resource.object_key,
                active=True,
                normalized=True,
            )
        else:
            if plan["macro_source_id"] != self.descriptor.source_id:
                raise PermissionError("Macro source differs from immutable plan")
            if isinstance(resource, FredResource):
                if (
                    resource.series_id not in plan["macro_series_keys"]
                    or resource.start != plan["macro_start"]
                    or resource.end != plan["macro_end"]
                ):
                    raise PermissionError("FRED resource differs from immutable plan")
                wire_day = (
                    plan["macro_source_as_of_date"] or plan["requested_at"].astimezone(UTC).date()
                )
                if resource.source_as_of != wire_day:
                    raise PermissionError("FRED source vintage differs from immutable intent")
                self._policy(
                    self.descriptor.policy_revision_id,
                    resource.object_key,
                    series=resource.series_id,
                    active=True,
                    normalized=True,
                )
            elif isinstance(resource, TreasuryResource):
                first = date(int(resource.month[:4]), int(resource.month[4:]), 1)
                last = first.replace(day=monthrange(first.year, first.month)[1])
                if (
                    first > plan["macro_end"]
                    or last < plan["macro_start"]
                    or plan["macro_source_as_of_date"] is not None
                    or not set(plan["macro_series_keys"]) <= {"BC_2YEAR", "BC_10YEAR"}
                ):
                    raise PermissionError("Treasury month or series differs from immutable plan")
                for series in plan["macro_series_keys"]:
                    self._policy(
                        self.descriptor.policy_revision_id,
                        resource.object_key,
                        series=series,
                        active=True,
                        normalized=True,
                    )

    def guard(self, request: Request) -> None:
        with self._transaction():
            self._guard(request)

    def _reserve(self, request: Request) -> None:
        lease = self._lease(request)
        consumed = self.database.execute(
            "SELECT count(*) AS n FROM source_fetch_attempts a "
            "JOIN analysis_stage_attempts s ON s.id=a.stage_attempt_id "
            "JOIN analysis_executions e ON e.id=s.execution_id "
            "WHERE e.request_id=%s AND a.source_id=%s AND a.source_object_key=%s "
            "AND a.request_params_hash=%s",
            (
                lease.request_id,
                self.descriptor.source_id,
                request.resource.object_key,
                request.resource.params_hash,
            ),
        ).fetchone()
        assert consumed is not None
        if consumed["n"] >= 3:
            raise ProviderBudgetExceeded("Immutable request has consumed its three attempts")
        if self.descriptor.provider != ProviderKind.TIINGO:
            return
        quota = self.descriptor.quota
        assert quota is not None
        counts = self.database.execute(
            "SELECT count(*) FILTER (WHERE prepared_at>=now()-interval '1 hour') AS hourly,"
            "count(*) FILTER (WHERE prepared_at>=now()-interval '1 day') AS daily,"
            "count(*) AS monthly, count(DISTINCT source_object_key) AS symbols,"
            "bool_or(source_object_key=%s) AS symbol_seen FROM source_fetch_attempts "
            "WHERE source_id=%s AND prepared_at>=now()-interval '31 days'",
            (request.resource.object_key, self.descriptor.source_id),
        ).fetchone()
        assert counts is not None
        if (
            counts["hourly"] >= quota.hourly_requests
            or counts["daily"] >= quota.daily_requests
            or counts["monthly"] >= quota.monthly_requests
            or (counts["monthly"] + 1) * PROVIDER_WIRE_LIMIT > quota.monthly_wire_bytes
        ):
            raise ProviderBudgetExceeded("Reviewed account request or wire-byte quota exhausted")
        if counts["symbols"] + (0 if counts["symbol_seen"] else 1) > quota.monthly_symbols:
            raise ProviderBudgetExceeded("Reviewed account symbols quota exhausted")

    def prepare(
        self, request: Request, sequence: int, url: str, validator: RawRecord | None
    ) -> UUID:
        lease = self._lease(request)
        if url != request.resource.url:
            raise PermissionError("Provider request URL differs from the typed resource")
        if validator is not None:
            self.validate_record(validator)
            if (
                validator.request_url != url
                or validator.request_params_hash != request.resource.params_hash
                or validator.source_object_key != request.resource.object_key
                or not validator.successful
            ):
                raise PermissionError("Conditional capture differs from requested resource")
        with self._transaction():
            # Same lock serializes policy activation/disable and all reservations
            # for this configured source account; no network I/O occurs here.
            self.database.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,904))",
                (str(self.descriptor.source_id),),
            )
            self._guard(request)
            existing = self.database.execute(
                "SELECT id FROM source_fetch_attempts WHERE logical_fetch_id=%s AND sequence_no=%s",
                (request.logical_fetch_id, sequence),
            ).fetchone()
            if existing is None:
                self._reserve(request)
            prepared = ingestion.AttemptRequest(
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
            )
            row = self.database.execute(
                "SELECT ingestion_prepare(%s,%s,%s) AS id",
                (Jsonb(lease.as_json()), request.stage_id, Jsonb(json_value(asdict(prepared)))),
            ).fetchone()
            assert row is not None
            return UUID(str(row["id"]))

    def _attempt(self, request: Request, attempt_id: UUID) -> dict[str, Any]:
        self._descriptor()
        row = self.database.execute(
            "SELECT * FROM source_fetch_attempts WHERE id=%s", (attempt_id,)
        ).fetchone()
        expected = {
            "source_id": self.descriptor.source_id,
            "policy_revision_id": self.descriptor.policy_revision_id,
            "source_object_key": request.resource.object_key,
            "request_params_hash": request.resource.params_hash,
            "request_url": request.resource.url,
            "logical_fetch_id": request.logical_fetch_id,
            "stage_attempt_id": request.stage_id,
        }
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise PermissionError("Provider attempt differs from its prepared request")
        self._policy(row["policy_revision_id"], row["source_object_key"], active=False)
        return row

    def dispatched(self, request: Request, attempt_id: UUID, at: datetime) -> None:
        _aware(at)
        with self._transaction():
            self._guard(request)
            self._attempt(request, attempt_id)
            self.database.execute(
                "SELECT ingestion_dispatch(%s,%s,%s)",
                (Jsonb(self._lease(request).as_json()), attempt_id, at),
            )

    def headers(
        self,
        request: Request,
        attempt_id: UUID,
        at: datetime,
        status: int,
        headers: ingestion.ResponseHeaders,
    ) -> None:
        _aware(at)
        with self._transaction():
            self._attempt(request, attempt_id)
            self.database.execute(
                "SELECT ingestion_headers(%s,%s,%s,%s,%s)",
                (
                    Jsonb(self._lease(request).as_json()),
                    attempt_id,
                    at,
                    status,
                    Jsonb(
                        {key: value for key, value in asdict(headers).items() if value is not None}
                    ),
                ),
            )

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
    ) -> None:
        _aware(at)
        with self._transaction():
            attempt = self._attempt(request, attempt_id)
            metadata = None
            if capture is not None:
                expected = {
                    "source_id": self.descriptor.source_id,
                    "policy_revision_id": self.descriptor.policy_revision_id,
                    "terms_review_reference": self.descriptor.terms_review_reference,
                    "source_object_key": request.resource.object_key,
                    "request_url": request.resource.url,
                    "request_params_hash": request.resource.params_hash,
                    "requested_at": attempt["requested_at"],
                    "http_status": attempt["http_status"],
                    "completed_at": at,
                    "content_type": attempt["response_headers"].get("content_type"),
                }
                if any(getattr(capture, key) != value for key, value in expected.items()):
                    raise PermissionError("Completed capture differs from prepared attempt")
                metadata = ingestion.CaptureMetadata(
                    capture.capture_id,
                    capture.fetched_at,
                    capture.body_sha256,
                    capture.blob_key,
                    capture.byte_count,
                    capture.content_type,
                )
            self.database.execute(
                "SELECT ingestion_finalize(%s,%s,%s,%s,%s,%s,%s,NULL,NULL)",
                (
                    Jsonb(self._lease(request).as_json()),
                    attempt_id,
                    outcome,
                    at,
                    Jsonb(json_value(asdict(metadata))) if metadata else None,
                    reused,
                    failure,
                ),
            )
