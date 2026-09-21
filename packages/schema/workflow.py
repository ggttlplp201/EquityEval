"""Durable local watchlist requests; no upstream access or financial computation.

Database functions own atomic state transitions. These functions use short
transactions (or savepoints inside an explicit caller transaction). Workers must
leave those scopes before doing I/O. This is an internal storage interface, not
an HTTP API contract.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from equity_schema.bootstrap import BootstrapPlan
from psycopg import Connection
from psycopg.errors import ObjectNotInPrerequisiteState
from psycopg.types.json import Jsonb

HistoryMode = Literal["as_filed_by_date", "original_as_filed", "latest_reported"]
StageOutcome = Literal["completed", "blocked", "unsupported", "failed", "cancelled"]
ExecutionOutcome = Literal["completed", "completed_with_gaps", "waiting_for_input", "failed"]
Database = Connection[dict[str, Any]]


class LeaseLost(RuntimeError):
    """The worker no longer owns the current unexpired request attempt."""


@dataclass(frozen=True)
class RequestedPeriod:
    kind: Literal["instant", "duration"]
    end: date
    start: date | None = None

    def __post_init__(self) -> None:
        if self.kind == "instant":
            if self.start is not None:
                raise ValueError("An instant must not have a start date")
        elif self.kind == "duration":
            if self.start is None or self.start > self.end:
                raise ValueError("A duration needs start <= end")
        else:
            raise ValueError("Unknown period kind")

    def as_json(self) -> dict[str, str | None]:
        return {
            "kind": self.kind,
            "end": self.end.isoformat(),
            "start": self.start.isoformat() if self.start else None,
        }


MARKET_PLAN_REVISION = "s4-market-data-v1"


@dataclass(frozen=True)
class MarketDataRequestPlan:
    """Reviewed provider/date intent pinned before an execution is queued."""

    market_plan_revision: str
    price_source_id: UUID | None = None
    price_start: date | None = None
    price_end: date | None = None
    macro_source_id: UUID | None = None
    macro_series_keys: tuple[str, ...] = ()
    macro_start: date | None = None
    macro_end: date | None = None
    macro_source_as_of_date: date | None = None

    def __post_init__(self) -> None:
        if self.market_plan_revision != MARKET_PLAN_REVISION:
            raise ValueError("Unknown market plan revision")
        if self.price_source_id is None and self.macro_source_id is None:
            raise ValueError("Market plan requires a price or macro source")
        for source in (self.price_source_id, self.macro_source_id):
            if source is not None and not isinstance(source, UUID):
                raise ValueError("Market sources require UUID identities")
        for source, start, end in (
            (self.price_source_id, self.price_start, self.price_end),
            (self.macro_source_id, self.macro_start, self.macro_end),
        ):
            if source is None:
                if start is not None or end is not None:
                    raise ValueError("Dates require a source")
            elif type(start) is not date or type(end) is not date or start > end:
                raise ValueError("Market source requires ordered exact dates")
        if self.macro_source_as_of_date is not None and (
            self.macro_source_id is None or type(self.macro_source_as_of_date) is not date
        ):
            raise ValueError("Source vintage requires a macro source and exact date")
        if (
            not isinstance(self.macro_series_keys, tuple)
            or any(
                not isinstance(key, str) or not key.strip() or key != key.strip()
                for key in self.macro_series_keys
            )
            or len(set(self.macro_series_keys)) != len(self.macro_series_keys)
        ):
            raise ValueError("Macro series must be distinct exact nonempty keys")
        if bool(self.macro_series_keys) != (self.macro_source_id is not None):
            raise ValueError("Macro source requires a nonempty series list")
        object.__setattr__(self, "macro_series_keys", tuple(sorted(self.macro_series_keys)))

    def as_json(self) -> dict[str, Any]:
        return {
            "market_plan_revision": self.market_plan_revision,
            "price_source_id": str(self.price_source_id) if self.price_source_id else None,
            "price_start": self.price_start.isoformat() if self.price_start else None,
            "price_end": self.price_end.isoformat() if self.price_end else None,
            "macro_source_id": str(self.macro_source_id) if self.macro_source_id else None,
            "macro_series_keys": list(self.macro_series_keys) if self.macro_source_id else None,
            "macro_start": self.macro_start.isoformat() if self.macro_start else None,
            "macro_end": self.macro_end.isoformat() if self.macro_end else None,
            "macro_source_as_of_date": self.macro_source_as_of_date.isoformat()
            if self.macro_source_as_of_date
            else None,
        }


@dataclass(frozen=True)
class RequestOptions:
    history_mode: HistoryMode = "latest_reported"
    filed_cutoff: date | None = None
    requested_periods: tuple[RequestedPeriod, ...] = ()
    retrieval_vintage: datetime | None = None
    max_attempts: int = 3
    market_plan: MarketDataRequestPlan | None = None

    def __post_init__(self) -> None:
        if self.market_plan is not None and not isinstance(self.market_plan, MarketDataRequestPlan):
            raise ValueError("Market plan requires the strict typed plan")
        if self.history_mode not in {"latest_reported", "as_filed_by_date", "original_as_filed"}:
            raise ValueError("Unknown history mode")
        if self.history_mode == "as_filed_by_date" and self.filed_cutoff is None:
            raise ValueError("as_filed_by_date requires a filed cutoff")
        if self.history_mode == "latest_reported" and self.filed_cutoff is not None:
            raise ValueError("latest_reported does not accept a filed cutoff")
        if self.retrieval_vintage is not None and self.retrieval_vintage.utcoffset() is None:
            raise ValueError("Retrieval vintage requires a timezone")
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        if len(set(self.requested_periods)) != len(self.requested_periods):
            raise ValueError("Duplicate requested periods")

    def as_json(self) -> dict[str, Any]:
        return {
            "history_mode": self.history_mode,
            "filed_cutoff": self.filed_cutoff.isoformat() if self.filed_cutoff else None,
            "requested_periods": [period.as_json() for period in self.requested_periods],
            "retrieval_vintage": (
                self.retrieval_vintage.isoformat() if self.retrieval_vintage else None
            ),
            "max_attempts": self.max_attempts,
            **({"market_plan": self.market_plan.as_json()} if self.market_plan else {}),
        }


@dataclass(frozen=True)
class WorkspaceHandle:
    workspace_id: UUID
    watchlist_id: UUID


@dataclass(frozen=True)
class RequestHandle:
    request_id: UUID
    request_sequence: int
    membership_id: UUID | None
    generation: int | None


@dataclass(frozen=True)
class Lease:
    request_id: UUID
    execution_id: UUID
    epoch: int
    fencing_token: int
    worker_id: str
    expires_at: datetime = field(compare=False)

    def as_json(self) -> dict[str, Any]:
        return {
            "request_id": str(self.request_id),
            "execution_id": str(self.execution_id),
            "epoch": self.epoch,
            "fencing_token": self.fencing_token,
            "worker_id": self.worker_id,
        }


def _invoke(db: Database, sql: str, args: tuple[Any, ...]) -> Any:
    try:
        with db.transaction():
            row = db.execute(sql, args).fetchone()
            if row is None:
                raise RuntimeError("Workflow function did not return a result")
            return row["result"]
    except ObjectNotInPrerequisiteState as exc:
        if str(exc).startswith("lease lost"):
            raise LeaseLost(str(exc).splitlines()[0]) from exc
        raise


def _request(data: dict[str, Any]) -> RequestHandle:
    return RequestHandle(
        UUID(data["request_id"]),
        data["request_sequence"],
        UUID(data["membership_id"]) if data["membership_id"] else None,
        data["generation"],
    )


def _lease(data: dict[str, Any]) -> Lease:
    return Lease(
        UUID(data["request_id"]),
        UUID(data["execution_id"]),
        data["epoch"],
        data["fencing_token"],
        data["worker_id"],
        datetime.fromisoformat(data["expires_at"]),
    )


def create_workspace_watchlist(
    db: Database, *, name: str, timezone: str = "UTC"
) -> WorkspaceHandle:
    data = _invoke(db, "SELECT workflow_create_workspace(%s,%s) AS result", (name, timezone))
    return WorkspaceHandle(UUID(data["workspace_id"]), UUID(data["watchlist_id"]))


def add_watchlist_stock(
    db: Database,
    *,
    watchlist_id: UUID,
    security_id: UUID,
    quote_identifier_id: UUID,
    idempotency_key: str,
    options: RequestOptions | None = None,
) -> RequestHandle:
    return _request(
        _invoke(
            db,
            "SELECT workflow_enqueue(%s,%s,%s,%s,%s,%s,%s,%s) AS result",
            (
                None,
                watchlist_id,
                security_id,
                quote_identifier_id,
                idempotency_key,
                Jsonb((options or RequestOptions()).as_json()),
                "watchlist_add",
                None,
            ),
        )
    )


def rerun_analysis(
    db: Database,
    *,
    workspace_id: UUID,
    security_id: UUID,
    quote_identifier_id: UUID,
    idempotency_key: str,
    parent_request_id: UUID | None = None,
    options: RequestOptions | None = None,
) -> RequestHandle:
    return _request(
        _invoke(
            db,
            "SELECT workflow_enqueue(%s,%s,%s,%s,%s,%s,%s,%s) AS result",
            (
                workspace_id,
                None,
                security_id,
                quote_identifier_id,
                idempotency_key,
                Jsonb((options or RequestOptions()).as_json()),
                "manual_refresh",
                parent_request_id,
            ),
        )
    )


def remove_watchlist_stock(db: Database, *, membership_id: UUID | None) -> bool:
    if membership_id is None:
        raise ValueError("A membership ID is required")
    return bool(_invoke(db, "SELECT workflow_remove_membership(%s) AS result", (membership_id,)))


def claim_next(db: Database, *, worker_id: str, lease_seconds: int = 60) -> Lease | None:
    data = _invoke(db, "SELECT workflow_claim(%s,%s) AS result", (worker_id, lease_seconds))
    return _lease(data) if data else None


def enqueue_source_bootstrap(
    db: Database,
    *,
    workspace_id: UUID,
    security_id: UUID,
    idempotency_key: str,
    plan: BootstrapPlan,
    max_attempts: int = 3,
) -> RequestHandle:
    """Queue only the immutable, explicitly reviewed acquisition resources."""
    if (
        not isinstance(plan, BootstrapPlan)
        or type(max_attempts) is not int
        or not 1 <= max_attempts <= 3
    ):
        raise ValueError("Bootstrap requires a bounded plan and one to three attempts")
    return _request(
        _invoke(
            db,
            "SELECT workflow_enqueue_bootstrap(%s,%s,%s,%s) AS result",
            (
                workspace_id,
                security_id,
                idempotency_key,
                Jsonb({"plan": plan.as_json(), "max_attempts": max_attempts}),
            ),
        )
    )


def complete_bootstrap_stage(
    db: Database, lease: Lease, *, stage_id: UUID, result: dict[str, Any]
) -> None:
    """Persist the typed acquisition result under the existing stage fence."""
    _invoke(
        db,
        "SELECT workflow_complete_bootstrap_stage(%s,%s,%s) AS result",
        (Jsonb(lease.as_json()), stage_id, Jsonb(result)),
    )


def claim_source_bootstrap(
    db: Database, *, worker_id: str, lease_seconds: int = 60, request_id: UUID | None = None
) -> Lease | None:
    data = _invoke(
        db,
        "SELECT workflow_claim_bootstrap(%s,%s,%s) AS result",
        (worker_id, lease_seconds, request_id),
    )
    return _lease(data) if data else None


def renew_lease(db: Database, lease: Lease, *, lease_seconds: int = 60) -> Lease:
    return _lease(
        _invoke(
            db,
            "SELECT workflow_renew(%s,%s) AS result",
            (Jsonb(lease.as_json()), lease_seconds),
        )
    )


def start_stage(db: Database, lease: Lease, *, stage_key: str) -> UUID:
    return UUID(
        str(
            _invoke(
                db,
                "SELECT workflow_start_stage(%s,%s) AS result",
                (Jsonb(lease.as_json()), stage_key),
            )
        )
    )


def finish_stage(
    db: Database,
    lease: Lease,
    *,
    stage_id: UUID,
    outcome: StageOutcome,
    reason: str | None = None,
    reused_capture_ids: tuple[UUID, ...] = (),
) -> None:
    _invoke(
        db,
        "SELECT workflow_finish_stage(%s,%s,%s,%s,%s) AS result",
        (Jsonb(lease.as_json()), stage_id, outcome, reason, list(reused_capture_ids)),
    )


def finish_execution(
    db: Database,
    lease: Lease,
    *,
    outcome: ExecutionOutcome = "completed",
    reason: str | None = None,
) -> None:
    _invoke(
        db,
        "SELECT workflow_finish(%s,%s,%s) AS result",
        (Jsonb(lease.as_json()), outcome, reason),
    )


def retry_execution(
    db: Database,
    lease: Lease,
    *,
    error_code: str,
    delay_seconds: int = 30,
) -> None:
    _invoke(
        db,
        "SELECT workflow_retry(%s,%s,%s) AS result",
        (Jsonb(lease.as_json()), error_code, delay_seconds),
    )


def cancel_request(db: Database, *, request_id: UUID) -> bool:
    return bool(_invoke(db, "SELECT workflow_cancel(%s) AS result", (request_id,)))
