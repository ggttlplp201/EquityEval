"""Narrow S4 database entry points. No HTTP, archives, or financial arithmetic."""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from psycopg.errors import ObjectNotInPrerequisiteState
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from .workflow import Database, Lease, LeaseLost


def json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return json_value(asdict(value))
    if isinstance(value, (UUID, date, datetime, Decimal)):
        return str(value) if not isinstance(value, (date, datetime)) else value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def _invoke(db: Database, statement: str, params: tuple[Any, ...]) -> Any:
    if db.info.transaction_status != TransactionStatus.IDLE:
        raise RuntimeError("Market operations require an idle database connection")
    try:
        with db.transaction():
            row = db.execute(statement, params).fetchone()
            if row is None:
                raise RuntimeError("Market operation returned no result")
            return row["result"]
    except ObjectNotInPrerequisiteState as exc:
        if str(exc).startswith("lease lost"):
            raise LeaseLost("lease lost during market operation") from None
        raise


def validate_policy(
    db: Database,
    *,
    policy_revision_id: UUID,
    source_id: UUID,
    object_key: str,
    series_key: str | None = None,
    normalized: bool = False,
    require_active: bool = True,
) -> None:
    _invoke(
        db,
        "SELECT market_validate_policy(%s,%s,%s,%s,%s,%s) AS result",
        (policy_revision_id, source_id, object_key, series_key, normalized, require_active),
    )


def activate_policy(db: Database, policy_revision_id: UUID, *, actor: str, reason: str) -> bool:
    """Owner-only reviewed activation; the runtime database role cannot call it."""
    return bool(
        _invoke(
            db,
            "SELECT market_activate_policy(%s,%s,%s) AS result",
            (policy_revision_id, actor, reason),
        )
    )


def disable_policy(db: Database, policy_revision_id: UUID, *, actor: str, reason: str) -> bool:
    return bool(
        _invoke(
            db,
            "SELECT market_disable_policy(%s,%s,%s) AS result",
            (policy_revision_id, actor, reason),
        )
    )


def publish(
    db: Database, lease: Lease, stage_id: UUID, payload: dict[str, Any]
) -> tuple[UUID, bool]:
    result = _invoke(
        db,
        "SELECT market_publish(%s,%s,%s) AS result",
        (Jsonb(lease.as_json()), stage_id, Jsonb(json_value(payload))),
    )
    return UUID(result["batch_id"]), bool(result["reused"])
