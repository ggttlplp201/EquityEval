"""Approved S3 source boundary: resolved identities and pinned archive evidence."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, Protocol
from uuid import UUID

from equity_schema.workflow import Lease, RequestedPeriod

if TYPE_CHECKING:
    from .financial_types import NormalizationBundle, NormalizationInput


class ResourceKind(StrEnum):
    COMPANY_FACTS = "company_facts"
    SUBMISSIONS = "submissions"
    SUBMISSIONS_HISTORY = "submissions_history"
    FILING_DOCUMENT = "filing_document"


def canonical_cik(value: object) -> str:
    if type(value) is int:
        text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        raise ValueError("CIK must be an integer or ASCII digit string")
    if not re.fullmatch(r"[0-9]{1,10}", text) or int(text) == 0:
        raise ValueError("CIK must be a positive integer with at most ten digits")
    return text.zfill(10)


def _aware(value: datetime) -> None:
    if value.utcoffset() is None:
        raise ValueError("Source timestamps require an explicit timezone")


@dataclass(frozen=True)
class SecResource:
    issuer_id: UUID
    cik: str
    kind: ResourceKind
    filename: str | None = None
    accession: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "cik", canonical_cik(self.cik))
        if not isinstance(self.kind, ResourceKind):
            raise ValueError("Unknown SEC resource kind")
        if self.kind == ResourceKind.SUBMISSIONS_HISTORY:
            if not self.filename or not re.fullmatch(
                rf"CIK{self.cik}-submissions-[0-9]+\.json", self.filename
            ):
                raise ValueError("History filename must belong to the resolved CIK")
            if self.accession is not None:
                raise ValueError("Submissions history has no filing accession")
        elif self.kind == ResourceKind.FILING_DOCUMENT:
            if not self.accession or not re.fullmatch(
                r"[0-9]{10}-[0-9]{2}-[0-9]{6}", self.accession
            ):
                raise ValueError("Filing document needs a validated accession")
            if not self.filename or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:htm|html|xml|txt|xsd)", self.filename
            ):
                raise ValueError("Invalid filing document filename")
            if ".." in self.filename:
                raise ValueError("Invalid filing document filename")
        elif self.filename is not None or self.accession is not None:
            raise ValueError("This SEC resource has no filename or accession")

    @property
    def url(self) -> str:
        if self.kind == ResourceKind.COMPANY_FACTS:
            return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{self.cik}.json"
        if self.kind == ResourceKind.SUBMISSIONS:
            return f"https://data.sec.gov/submissions/CIK{self.cik}.json"
        if self.kind == ResourceKind.SUBMISSIONS_HISTORY:
            return f"https://data.sec.gov/submissions/{self.filename}"
        assert self.accession is not None
        return (
            f"https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/"
            f"{self.accession.replace('-', '')}/{self.filename}"
        )

    @property
    def object_key(self) -> str:
        suffix = "/".join(item for item in (self.accession, self.filename) if item)
        return f"{self.kind.value}/{self.cik}" + (f"/{suffix}" if suffix else "")

    @property
    def params_hash(self) -> str:
        return hashlib.sha256(b"{}").hexdigest()


@dataclass(frozen=True)
class SourceDescriptor:
    source_id: UUID
    source_key: str
    name: str
    policy_revision_id: UUID
    terms_review_reference: str
    licence: str
    redistribution_status: Literal["allowed", "prohibited", "unknown"]
    resource_kinds: tuple[ResourceKind, ...]
    freshness_sla: timedelta
    limiter_key: str = "sec:user"
    requests_per_second: int = 5

    def __post_init__(self) -> None:
        if not all(
            (
                self.source_key.strip(),
                self.name.strip(),
                self.terms_review_reference.strip(),
                self.licence.strip(),
                self.limiter_key.strip(),
            )
        ):
            raise ValueError("Source identity and reviewed policy must be explicit")
        if self.redistribution_status not in {"allowed", "prohibited", "unknown"}:
            raise ValueError("Invalid redistribution status")
        if type(self.requests_per_second) is not int or not 1 <= self.requests_per_second <= 10:
            raise ValueError("SEC request rate must be between one and ten")
        if self.freshness_sla <= timedelta(0) or not self.resource_kinds:
            raise ValueError("Source freshness policy and capabilities must be explicit")

    @property
    def redistribution_allowed(self) -> bool:
        return self.redistribution_status == "allowed"


@dataclass(frozen=True)
class RawRecord:
    capture_id: UUID
    source_id: UUID
    source_object_key: str
    request_url: str
    request_params_hash: str
    requested_at: datetime
    fetched_at: datetime
    completed_at: datetime
    http_status: int
    body_sha256: str
    byte_count: int
    blob_key: str
    content_type: str | None
    policy_revision_id: UUID
    terms_review_reference: str
    etag: str | None = None
    last_modified: str | None = None

    def __post_init__(self) -> None:
        for stamp in (self.requested_at, self.fetched_at, self.completed_at):
            _aware(stamp)
        if not self.requested_at <= self.fetched_at <= self.completed_at:
            raise ValueError("Invalid source retrieval ordering")
        if type(self.http_status) is not int or not 100 <= self.http_status <= 599:
            raise ValueError("Invalid HTTP status")
        if type(self.byte_count) is not int or self.byte_count < 0 or not self.blob_key:
            raise ValueError("A complete archive reference is required")
        if not all(
            re.fullmatch(r"[a-f0-9]{64}", value)
            for value in (self.body_sha256, self.request_params_hash)
        ):
            raise ValueError("Invalid archive or parameter hash")

    @property
    def successful(self) -> bool:
        return 200 <= self.http_status < 300


CacheMode = Literal["refresh", "reuse", "conditional", "replay"]
Completeness = Literal["complete", "incomplete", "unknown"]


@dataclass(frozen=True)
class FetchRequest:
    logical_fetch_id: UUID
    resource: SecResource
    lease: Lease | None
    stage_id: UUID | None
    cache_mode: CacheMode = "refresh"
    cached_record: RawRecord | None = None
    replay_records: tuple[RawRecord, ...] = ()
    requested_periods: tuple[RequestedPeriod, ...] = ()
    retrieval_cutoff: datetime | None = None

    def __post_init__(self) -> None:
        if self.cache_mode not in {"refresh", "reuse", "conditional", "replay"}:
            raise ValueError("Unknown source cache mode")
        if self.cache_mode != "replay" and (self.lease is None or self.stage_id is None):
            raise ValueError("Live fetch needs a workflow lease and stage")
        if self.retrieval_cutoff is not None:
            _aware(self.retrieval_cutoff)
            if self.cache_mode != "replay":
                raise ValueError("A pinned historical retrieval cutoff requires archive replay")
        if self.replay_records and self.cache_mode != "replay":
            raise ValueError("Pinned records require explicit replay mode")
        if self.cache_mode == "replay" and self.cached_record is not None:
            raise ValueError("Replay uses pinned records, not a mutable cache choice")
        for record in self.replay_records + ((self.cached_record,) if self.cached_record else ()):
            if (
                record.source_object_key != self.resource.object_key
                or record.request_params_hash != self.resource.params_hash
            ):
                raise ValueError("Cached/pinned capture belongs to another resource")
            if self.retrieval_cutoff is not None and record.completed_at > self.retrieval_cutoff:
                raise ValueError("Pinned capture is newer than retrieval cutoff")


@dataclass(frozen=True)
class AttemptOutcome:
    attempt_id: UUID
    outcome: str
    http_status: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class FetchResult:
    records: tuple[RawRecord, ...] = ()
    attempts: tuple[AttemptOutcome, ...] = ()
    reused_capture_ids: tuple[UUID, ...] = ()
    completeness: Completeness = "unknown"
    gaps: tuple[str, ...] = ()
    next_eligible_at: datetime | None = None

    @property
    def successful_records(self) -> tuple[RawRecord, ...]:
        return tuple(record for record in self.records if record.successful)

    @property
    def usable(self) -> bool:
        return bool(self.successful_records) and not self.gaps


class Source(Protocol):
    descriptor: SourceDescriptor

    def fetch(self, request: FetchRequest) -> FetchResult: ...

    def normalize(self, inputs: "NormalizationInput") -> "NormalizationBundle": ...
