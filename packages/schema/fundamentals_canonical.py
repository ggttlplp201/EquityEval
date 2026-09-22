"""S6 canonicalization v1: exact semantic content, never floating-point finance."""

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _plain(value.model_dump(mode="python"))
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(value))
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite financial values are forbidden")
        return str(value)
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("Timestamps require a timezone")
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, date | UUID):
        return str(value)
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, tuple | list):
        return [_plain(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _plain(item) for key, item in value.items()}
    raise TypeError("Canonical manifests accept no floats, sets or implicit conversions")


def canonical_json(value: Any) -> str:
    return json.dumps(
        _plain(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_canonical(text: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=pairs)
        if canonical_json(value) != text:
            raise ValueError("Manifest is not canonical v1 JSON")
    except (TypeError, UnicodeError) as exc:
        raise ValueError("Invalid canonical JSON") from exc
    return value
