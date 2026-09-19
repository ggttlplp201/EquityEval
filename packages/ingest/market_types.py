"""Frozen market ingestion DTOs; no I/O, provider activation or valuation arithmetic."""

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from .financial_types import EvidenceCapture

PriceState = Literal["observed", "source_null", "missing", "unparseable"]
MacroState = Literal["observed", "source_missing", "unparseable"]
CoverageState = Literal["complete", "partial", "unknown", "unavailable"]
MacroUnit = Literal[
    "percent_per_year", "percent", "percentage_points", "basis_points", "index", "count"
]
Frequency = Literal["daily", "business_day", "weekly", "monthly", "quarterly", "annual"]


@dataclass(frozen=True)
class QuoteBinding:
    id: UUID
    source_id: UUID
    quote_identifier_id: UUID
    security_id: UUID
    provider_symbol: str
    valid_from: date
    valid_to: date | None
    identity_capture_id: UUID
    source_locator: str
    identity_review_revision: str
    reviewed_at: datetime
    reviewed_by: str
    content_sha256: str
    provider_instrument_key: str | None = None


@dataclass(frozen=True)
class QuoteContext:
    """Separately reviewed quote/closure/unit evidence; never infer it from a ticker."""

    quote_identifier_id: UUID
    security_id: UUID
    venue: str | None
    quote_currency: str | None
    instrument_kind: str
    valid_from: date
    valid_to: date | None = None
    session_timezone: str | None = None
    dividend_currency: str | None = None
    dividend_currency_evidence: str | None = None


@dataclass(frozen=True)
class MacroSeriesDefinition:
    id: UUID
    source_id: UUID
    source_series_key: str
    metadata_capture_id: UUID
    source_locator: str
    content_sha256: str
    definition_revision: str
    title: str
    units_text: str
    unit_code: MacroUnit
    unit_multiplier: Decimal
    frequency: Frequency
    seasonal_adjustment: Literal["adjusted", "not_adjusted", "not_applicable", "unknown"]
    geography: str
    reference_date_convention: str
    upstream_source_name: str
    upstream_rights_reference: str
    source_release_key: str | None = None
    definition_as_of_date: date | None = None
    definition_as_of_basis: Literal["source_supplied", "capture_only", "unknown"] = "capture_only"


@dataclass(frozen=True)
class MarketNormalizationInput:
    source_id: UUID
    policy_revision_id: UUID
    requested_start: date
    requested_end: date
    captures: tuple[EvidenceCapture, ...]
    parser_revision: str
    normalizer_revision: str
    selection_policy_revision: str
    series_definition: MacroSeriesDefinition | None = None
    quote_binding: QuoteBinding | None = None
    quote_context: QuoteContext | None = None
    retrieval_cutoff: datetime | None = None
    source_as_of_date: date | None = None
    treasury_month: str | None = None
    allow_legacy_treasury_null: bool = False
    attempt_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True)
class FredPage:
    """Exact public request parameters and complete body; credentials never belong here."""

    capture_id: UUID
    body: bytes
    series_id: str
    observation_start: date
    observation_end: date
    realtime_start: date
    realtime_end: date
    offset: int
    limit: int
    units: str = "lin"
    output_type: int = 1
    order_by: str = "observation_date"
    sort_order: str = "asc"
    frequency: str | None = None
    aggregation_method: str | None = None


@dataclass(frozen=True)
class MarketQualityFlag:
    id: UUID
    reference_date: date | None
    field_key: str | None
    rule_key: str
    severity: Literal["info", "warning", "error", "blocking"]
    message: str
    capture_id: UUID | None = None
    attempt_id: UUID | None = None
    source_locator: str | None = None


@dataclass(frozen=True)
class MacroObservation:
    id: UUID
    reference_date: date
    series_definition_id: UUID
    source_capture_id: UUID
    source_locator: str
    source_date_text: str
    value: Decimal | None
    value_state: MacroState
    original_value_text: str | None
    source_observation_status: str | None
    transform_revision: str
    reference_end_date: date | None = None
    source_realtime_start: date | None = None
    source_realtime_end: date | None = None
    source_vintage_basis: Literal[
        "source_interval", "requested_as_of", "current_only", "unknown"
    ] = "current_only"
    requested_source_as_of: date | None = None
    source_published_date: date | None = None
    source_published_at: datetime | None = None
    publication_precision: Literal["unknown", "date", "instant"] = "unknown"


@dataclass(frozen=True)
class PriceObservation:
    id: UUID
    session_date: date
    source_capture_id: UUID
    source_locator: str
    quote_binding_id: UUID
    quote_identifier_id: UUID
    security_id: UUID
    quote_currency: str
    dividend_currency: str | None
    source_date_text: str
    transform_revision: str
    open: Decimal | None
    open_state: PriceState
    open_text: str | None
    high: Decimal | None
    high_state: PriceState
    high_text: str | None
    low: Decimal | None
    low_state: PriceState
    low_text: str | None
    close: Decimal | None
    close_state: PriceState
    close_text: str | None
    volume: Decimal | None
    volume_state: PriceState
    volume_text: str | None
    adj_open: Decimal | None
    adj_open_state: PriceState
    adj_open_text: str | None
    adj_high: Decimal | None
    adj_high_state: PriceState
    adj_high_text: str | None
    adj_low: Decimal | None
    adj_low_state: PriceState
    adj_low_text: str | None
    adj_close: Decimal | None
    adj_close_state: PriceState
    adj_close_text: str | None
    adj_volume: Decimal | None
    adj_volume_state: PriceState
    adj_volume_text: str | None
    div_cash: Decimal | None
    div_cash_state: PriceState
    div_cash_text: str | None
    split_factor: Decimal | None
    split_factor_state: PriceState
    split_factor_text: str | None
    session_basis: Literal["provider_daily_label"] = "provider_daily_label"
    session_timezone: str | None = None
    source_published_date: date | None = None
    source_published_at: datetime | None = None
    publication_precision: Literal["unknown", "date", "instant"] = "unknown"
    adjustment_basis: Literal["split_and_dividend", "split_only", "unadjusted", "unknown"] = (
        "split_and_dividend"
    )
    adjustment_vintage_basis: Literal["provider_supplied", "capture_only", "unknown"] = (
        "capture_only"
    )
    adjustment_vintage_date: date | None = None


@dataclass(frozen=True)
class MarketNormalizationBundle:
    inputs: MarketNormalizationInput
    prices: tuple[PriceObservation, ...]
    macros: tuple[MacroObservation, ...]
    flags: tuple[MarketQualityFlag, ...]
    coverage_state: CoverageState
    input_manifest_hash: str
    output_manifest_hash: str


def market_canonical_json(value: Any) -> str:
    """Canonical S4 evidence uses instants, independent of DB/session timezones.

    S3's historical hashes retain their separate serialization contract.
    """

    def encode(item: Any) -> Any:
        if is_dataclass(item) and not isinstance(item, type):
            return asdict(item)
        if isinstance(item, datetime):
            if item.utcoffset() is None:
                raise ValueError("Market evidence timestamp requires a timezone")
            return str(item.astimezone(UTC))
        if isinstance(item, (UUID, date, Decimal)):
            return str(item)
        raise TypeError(f"Unsupported market manifest type: {type(item).__name__}")

    return json.dumps(value, default=encode, sort_keys=True, separators=(",", ":"), allow_nan=False)
