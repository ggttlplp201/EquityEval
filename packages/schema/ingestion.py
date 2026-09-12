"""Short committed S3 transport persistence operations; never performs network I/O.

An idle connection is required so preparation and dispatch evidence cannot remain
inside a caller transaction while network work starts. Runtime writes use the
reviewed database functions and the current W1 stage/lease fence.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from equity_schema.workflow import Database, Lease, LeaseLost
from psycopg.errors import ObjectNotInPrerequisiteState
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

AttemptOutcome = Literal[
    "complete",
    "not_modified",
    "redirected",
    "http_error",
    "transport_error",
    "body_limit",
    "redirect_refused",
    "archive_error",
    "cancelled",
    "interrupted_unknown",
]


@dataclass(frozen=True)
class AttemptRequest:
    logical_fetch_id: UUID
    sequence: int
    source_id: UUID
    policy_revision_id: UUID
    source_object_key: str
    request_url: str
    request_params_hash: str
    validator_capture_id: UUID | None = None
    if_none_match: str | None = None
    if_modified_since: str | None = None


@dataclass(frozen=True)
class ResponseHeaders:
    content_type: str | None = None
    content_encoding: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    retry_after: str | None = None
    location: str | None = None


@dataclass(frozen=True)
class CaptureMetadata:
    capture_id: UUID
    fetched_at: datetime
    body_sha256: str
    blob_key: str
    byte_count: int
    content_type: str | None = None


@dataclass(frozen=True)
class QuarantineEvidence:
    body_sha256: str
    byte_count: int
    blob_key: str


def _json(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        _aware(value)
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items() if item is not None}
    return value


def _aware(value: datetime) -> None:
    if value.utcoffset() is None:
        raise ValueError("Transport evidence timestamps require an explicit timezone")


def _invoke(db: Database, statement: str, args: tuple[Any, ...]) -> Any:
    if db.info.transaction_status is not TransactionStatus.IDLE:
        raise RuntimeError("Source transport operations require an idle database connection")
    try:
        with db.transaction():
            row = db.execute(statement, args).fetchone()
            if row is None:
                raise RuntimeError("Source transport function returned no result")
            return row["result"]
    except ObjectNotInPrerequisiteState as error:
        if str(error).startswith("lease lost"):
            raise LeaseLost(str(error).splitlines()[0]) from error
        raise


def validate_stage_lease(db: Database, lease: Lease, stage_id: UUID) -> None:
    _invoke(
        db, "SELECT ingestion_validate_stage(%s,%s) AS result", (Jsonb(lease.as_json()), stage_id)
    )


def prepare_attempt(db: Database, lease: Lease, stage_id: UUID, request: AttemptRequest) -> UUID:
    return UUID(
        str(
            _invoke(
                db,
                "SELECT ingestion_prepare(%s,%s,%s) AS result",
                (Jsonb(lease.as_json()), stage_id, Jsonb(_json(asdict(request)))),
            )
        )
    )


def mark_dispatched(db: Database, lease: Lease, attempt_id: UUID, requested_at: datetime) -> None:
    _aware(requested_at)
    _invoke(
        db,
        "SELECT ingestion_dispatch(%s,%s,%s) AS result",
        (Jsonb(lease.as_json()), attempt_id, requested_at),
    )


def record_response_headers(
    db: Database,
    lease: Lease,
    attempt_id: UUID,
    headers_received_at: datetime,
    http_status: int,
    headers: ResponseHeaders,
) -> None:
    _aware(headers_received_at)
    _invoke(
        db,
        "SELECT ingestion_headers(%s,%s,%s,%s,%s) AS result",
        (
            Jsonb(lease.as_json()),
            attempt_id,
            headers_received_at,
            http_status,
            Jsonb(_json(asdict(headers))),
        ),
    )


def finalize_attempt(
    db: Database,
    lease: Lease,
    attempt_id: UUID,
    outcome: AttemptOutcome,
    finished_at: datetime,
    *,
    completed_capture: CaptureMetadata | None = None,
    reused_capture_id: UUID | None = None,
    failure_code: str | None = None,
    failure_detail: str | None = None,
    quarantine: QuarantineEvidence | None = None,
) -> UUID | None:
    _aware(finished_at)
    result = _invoke(
        db,
        "SELECT ingestion_finalize(%s,%s,%s,%s,%s,%s,%s,%s,%s) AS result",
        (
            Jsonb(lease.as_json()),
            attempt_id,
            outcome,
            finished_at,
            Jsonb(_json(asdict(completed_capture))) if completed_capture else None,
            reused_capture_id,
            failure_code,
            failure_detail,
            Jsonb(_json(asdict(quarantine))) if quarantine else None,
        ),
    )
    return UUID(str(result)) if result is not None else None


def recover_interrupted_attempt(db: Database, attempt_id: UUID) -> bool:
    return bool(_invoke(db, "SELECT ingestion_recover(%s) AS result", (attempt_id,)))
