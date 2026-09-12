"""Frozen ingestion transfer objects mirroring the reviewed S2 evidence tables.

JSON fields are canonical JSON strings so frozen objects cannot hide mutable dicts.
UUIDs identify rows; only the writer publishes them. This module performs no I/O.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from equity_schema.concepts import Concept

CompletenessState = Literal["complete", "incomplete", "unknown"]
ResolutionStatus = Literal[
    "observed", "source_nil", "missing", "ambiguous", "unsupported_scope", "stale_source"
]


def canonical_json(value: Any) -> str:
    def encode(item: Any) -> Any:
        if is_dataclass(item) and not isinstance(item, type):
            return asdict(item)
        if isinstance(item, (UUID, date, datetime, Decimal)):
            return str(item)
        raise TypeError(f"Unsupported manifest type: {type(item).__name__}")

    return json.dumps(value, default=encode, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def evidence_id(kind: str, value: Any) -> UUID:
    return uuid5(NAMESPACE_URL, f"equityeval:{kind}:{canonical_json(value)}")


@dataclass(frozen=True)
class EvidenceCapture:
    id: UUID
    source_id: UUID
    source_object_key: str
    request_url: str
    body_sha256: str
    byte_count: int
    fetched_at: datetime
    completed_at: datetime
    role: str


@dataclass(frozen=True)
class Completeness:
    state: CompletenessState
    boundary_start: date
    boundary_end: date
    evidence_references: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.state not in {"complete", "incomplete", "unknown"}:
            raise ValueError("Explicit completeness state required")
        if self.boundary_start > self.boundary_end or not self.evidence_references:
            raise ValueError("Completeness requires an ordered boundary and evidence")


@dataclass(frozen=True)
class FilingMetadata:
    id: UUID
    filing_id: UUID
    issuer_id: UUID
    accession: str
    metadata_capture_id: UUID
    filed_date: date
    form: str
    source_url: str
    metadata_hash: str
    report_period_end: date | None = None
    acceptance_at: datetime | None = None
    acceptance_time_basis: str | None = None


@dataclass(frozen=True)
class PeriodSpec:
    id: UUID
    period_kind: str
    start_date: date | None
    end_date: date


@dataclass(frozen=True)
class UnitSpec:
    id: UUID
    unit_key: str
    numerator_measures: tuple[str, ...]
    denominator_measures: tuple[str, ...]


@dataclass(frozen=True)
class ScopeSpec:
    id: UUID
    issuer_id: UUID
    instrument_id: UUID | None
    scope_kind: str
    descriptor_schema_version: int
    descriptor_json: str
    content_sha256: str


@dataclass(frozen=True)
class MappingRule:
    reference: str
    cik: str
    accessions: tuple[str, ...]
    concept: Concept
    qualified_tags: tuple[str, ...]
    unit_key: str
    scope_id: UUID
    evidence_references: tuple[str, ...]
    period_start: date | None
    period_end: date
    scope_content_sha256: str
    scope_kind: str
    instrument_id: UUID | None
    statement_family: str
    reporting_basis: str
    preferred_tag: str | None = None
    rejected_tags: tuple[str, ...] = ()
    rationale: str = "Directly reported reviewed scope; no arithmetic fallback"


@dataclass(frozen=True)
class CoverageRequest:
    id: UUID
    filing_version_id: UUID
    period: PeriodSpec
    scope: ScopeSpec
    currency: UnitSpec
    statement_family: str
    reporting_basis: str
    authority_class: str
    assurance: str
    coverage_state: str
    evidence_locator: str
    concepts: tuple[Concept, ...]
    period_label: str | None = None


@dataclass(frozen=True)
class NormalizationInput:
    issuer_id: UUID
    cik: str
    companyfacts_capture_id: UUID
    captures: tuple[EvidenceCapture, ...]
    filings: tuple[FilingMetadata, ...]
    requests: tuple[CoverageRequest, ...]
    rules: tuple[MappingRule, ...]
    mapping_revision_id: UUID
    parser_revision: str
    normalizer_revision: str
    authority_policy_revision: str
    captured_before: datetime
    inventory_completeness: Completeness
    event_completeness: Completeness
    filing_event_ids: tuple[UUID, ...] = ()
    additional_quality_flag_ids: tuple[UUID, ...] = ()
    attempt_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True)
class Coverage:
    id: UUID
    filing_version_id: UUID
    period_id: UUID
    statement_family: str
    reporting_basis: str
    scope_id: UUID
    currency_unit_id: UUID | None
    authority_class: str
    assurance: str
    coverage_state: str
    evidence_locator: str
    period_label: str | None = None


@dataclass(frozen=True)
class Observation:
    id: UUID
    source_capture_id: UUID
    filing_version_id: UUID
    source_locator: str
    namespace: str
    tag: str
    period_id: UUID
    unit_id: UUID
    semantic_scope_id: UUID | None
    numeric_value: Decimal | None
    value_state: str
    original_numeric_text: str | None
    parser_revision: str
    transform_metadata: str
    raw_metadata: str
    context_id: str | None = None
    raw_dimensions: str | None = None
    context_knowledge: str = "unknown"


@dataclass(frozen=True)
class Resolution:
    id: UUID
    coverage_id: UUID
    concept_std: Concept
    semantic_scope_id: UUID
    instrument_id: UUID | None
    unit_id: UUID
    status: ResolutionStatus
    selected_observation_id: UUID | None
    reason: str | None


@dataclass(frozen=True)
class Candidate:
    resolution_id: UUID
    observation_id: UUID
    rule_reference: str
    disposition: str
    explanation: str


@dataclass(frozen=True)
class QualityFlag:
    id: UUID
    resolution_id: UUID | None
    issuer_id: UUID
    period_id: UUID | None
    rule_key: str
    severity: str
    message: str
    evidence_references: str
    security_id: UUID | None = None


@dataclass(frozen=True)
class NormalizationBundle:
    inputs: NormalizationInput
    periods: tuple[PeriodSpec, ...]
    units: tuple[UnitSpec, ...]
    scopes: tuple[ScopeSpec, ...]
    filings: tuple[FilingMetadata, ...]
    coverage: tuple[Coverage, ...]
    observations: tuple[Observation, ...]
    resolutions: tuple[Resolution, ...]
    candidates: tuple[Candidate, ...]
    quality_flags: tuple[QualityFlag, ...]
    input_manifest_hash: str
    output_manifest_hash: str
    original_history_complete: bool
