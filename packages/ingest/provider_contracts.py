"""Approved S4 resource identities; credentials never enter public request metadata."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Literal, Protocol, TypeVar
from uuid import UUID

from equity_schema.workflow import Lease

from .contracts import CacheMode, FetchResult, RawRecord

PROVIDER_BODY_LIMIT = 32 * 1024 * 1024
PROVIDER_WIRE_LIMIT = 2 * PROVIDER_BODY_LIMIT + 65536


class ProviderKind(StrEnum):
    TREASURY = "treasury_yield"
    TIINGO = "tiingo_eod"
    FRED = "fred_observations"


def _dates(start: date, end: date) -> None:
    if type(start) is not date or type(end) is not date or start > end:
        raise ValueError("Ordered explicit date bounds required")


def _hash(params: tuple[tuple[str, str], ...]) -> str:
    return hashlib.sha256(
        json.dumps(dict(params), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class ProviderResource(Protocol):
    @property
    def provider(self) -> ProviderKind: ...
    @property
    def object_key(self) -> str: ...
    @property
    def url(self) -> str: ...
    @property
    def params(self) -> tuple[tuple[str, str], ...]: ...
    @property
    def params_hash(self) -> str: ...


@dataclass(frozen=True)
class TreasuryResource:
    month: str

    def __post_init__(self) -> None:
        if not isinstance(self.month, str) or not re.fullmatch(r"[0-9]{6}", self.month):
            raise ValueError("Treasury month must be YYYYMM")
        try:
            date(int(self.month[:4]), int(self.month[4:]), 1)
        except ValueError as exc:
            raise ValueError("Invalid Treasury month") from exc

    @property
    def provider(self) -> ProviderKind:
        return ProviderKind.TREASURY

    @property
    def object_key(self) -> str:
        return "daily_treasury_yield_curve"

    @property
    def url(self) -> str:
        return (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
        )

    @property
    def params(self) -> tuple[tuple[str, str], ...]:
        return (("data", self.object_key), ("field_tdr_date_value_month", self.month))

    @property
    def params_hash(self) -> str:
        return _hash(self.params)


@dataclass(frozen=True)
class PriceResource:
    quote_identifier_id: UUID
    security_id: UUID
    provider_symbol: str
    start: date
    end: date

    def __post_init__(self) -> None:
        _dates(self.start, self.end)
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,19}", self.provider_symbol):
            raise ValueError("Unsupported reviewed provider symbol")
        if ".." in self.provider_symbol:
            raise ValueError("Invalid provider symbol")
        if not isinstance(self.quote_identifier_id, UUID) or not isinstance(self.security_id, UUID):
            raise ValueError("Explicit reviewed quote and security IDs required")

    @property
    def provider(self) -> ProviderKind:
        return ProviderKind.TIINGO

    @property
    def object_key(self) -> str:
        return "tiingo_eod/" + self.provider_symbol

    @property
    def url(self) -> str:
        return "https://api.tiingo.com/tiingo/daily/" + self.provider_symbol + "/prices"

    @property
    def params(self) -> tuple[tuple[str, str], ...]:
        return (
            ("startDate", self.start.isoformat()),
            ("endDate", self.end.isoformat()),
            ("format", "json"),
        )

    @property
    def params_hash(self) -> str:
        return _hash(self.params)


@dataclass(frozen=True)
class FredResource:
    series_id: str
    start: date
    end: date
    source_as_of: date
    offset: int = 0
    limit: int = 100000

    def __post_init__(self) -> None:
        _dates(self.start, self.end)
        if type(self.source_as_of) is not date or self.source_as_of < date(1776, 7, 4):
            raise ValueError("Explicit supported source vintage date required")
        if not re.fullmatch(r"[A-Za-z0-9_]{1,80}", self.series_id):
            raise ValueError("Invalid FRED series key")
        if type(self.offset) is not int or self.offset < 0:
            raise ValueError("Invalid FRED page offset")
        if type(self.limit) is not int or not 1 <= self.limit <= 100000:
            raise ValueError("Invalid FRED page limit")

    @property
    def provider(self) -> ProviderKind:
        return ProviderKind.FRED

    @property
    def object_key(self) -> str:
        return "fred_observations/" + self.series_id

    @property
    def url(self) -> str:
        return "https://api.stlouisfed.org/fred/series/observations"

    @property
    def params(self) -> tuple[tuple[str, str], ...]:
        return (
            ("series_id", self.series_id),
            ("file_type", "json"),
            ("observation_start", self.start.isoformat()),
            ("observation_end", self.end.isoformat()),
            ("realtime_start", self.source_as_of.isoformat()),
            ("realtime_end", self.source_as_of.isoformat()),
            ("units", "lin"),
            ("output_type", "1"),
            ("sort_order", "asc"),
            ("order_by", "observation_date"),
            ("offset", str(self.offset)),
            ("limit", str(self.limit)),
        )

    @property
    def params_hash(self) -> str:
        return _hash(self.params)


@dataclass(frozen=True)
class ProviderQuota:
    """Reviewed conservative rolling windows; reservations survive Redis restart."""

    hourly_requests: int
    daily_requests: int
    monthly_requests: int
    monthly_symbols: int
    monthly_wire_bytes: int

    def __post_init__(self) -> None:
        if any(
            type(x) is not int or x <= 0
            for x in (
                self.hourly_requests,
                self.daily_requests,
                self.monthly_requests,
                self.monthly_symbols,
                self.monthly_wire_bytes,
            )
        ):
            raise ValueError("Every account quota must be explicitly positive")


@dataclass(frozen=True)
class ProviderDescriptor:
    source_id: UUID
    source_key: str
    name: str
    policy_revision_id: UUID
    terms_review_reference: str
    licence: str
    redistribution_status: Literal["allowed", "prohibited", "unknown"]
    provider: ProviderKind
    freshness_sla: timedelta
    quota: ProviderQuota | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider, ProviderKind):
            raise ValueError("Unknown provider kind")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", self.source_key):
            raise ValueError("Invalid source key")
        if not all(x.strip() for x in (self.name, self.terms_review_reference, self.licence)):
            raise ValueError("Explicit reviewed source identity required")
        if self.redistribution_status not in {"allowed", "prohibited", "unknown"}:
            raise ValueError("Invalid redistribution status")
        if self.freshness_sla <= timedelta(0):
            raise ValueError("Positive freshness policy required")


R = TypeVar("R", bound=ProviderResource, contravariant=True)


@dataclass(frozen=True)
class ProviderFetchRequest[R: ProviderResource]:
    logical_fetch_id: UUID
    resource: R
    lease: Lease | None
    stage_id: UUID | None
    cache_mode: CacheMode = "refresh"
    cached_record: RawRecord | None = None
    replay_records: tuple[RawRecord, ...] = ()
    retrieval_cutoff: datetime | None = None

    def __post_init__(self) -> None:
        if self.cache_mode not in {"refresh", "reuse", "conditional", "replay"}:
            raise ValueError("Invalid provider cache mode")
        if self.cache_mode != "replay" and (self.lease is None or self.stage_id is None):
            raise ValueError("Live retrieval requires a lease and stage")
        if self.retrieval_cutoff is not None:
            if self.retrieval_cutoff.utcoffset() is None or self.cache_mode != "replay":
                raise ValueError("An aware historical capture cutoff requires replay")
        if self.replay_records and self.cache_mode != "replay":
            raise ValueError("Pinned captures require replay mode")
        if self.cached_record and self.cache_mode == "replay":
            raise ValueError("Replay cannot consult a mutable cache")
        for record in self.replay_records + ((self.cached_record,) if self.cached_record else ()):
            if (
                record.source_object_key != self.resource.object_key
                or record.request_url != self.resource.url
                or record.request_params_hash != self.resource.params_hash
            ):
                raise ValueError("Capture belongs to another resource/request")
            if self.retrieval_cutoff and record.completed_at > self.retrieval_cutoff:
                raise ValueError("Capture is later than local cutoff")


InputT = TypeVar("InputT", contravariant=True)
BundleT = TypeVar("BundleT", covariant=True)


class ProviderSource(Protocol[R, InputT, BundleT]):
    descriptor: ProviderDescriptor

    def fetch(self, request: ProviderFetchRequest[R]) -> FetchResult: ...
    def normalize(self, inputs: InputT) -> BundleT: ...
