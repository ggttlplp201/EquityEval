"""Pure, conservative normalization of explicitly pinned market response bytes.

The caller verifies rights, requests and archive completeness before supplying
these inputs. We recheck hashes and interpretation scope; no network, database,
unit conversion, adjusted-price reconstruction or source substitution occurs.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from lxml import etree

from .financial_types import EvidenceCapture, evidence_id
from .market_types import (
    CoverageState,
    FredPage,
    MacroObservation,
    MacroSeriesDefinition,
    MarketNormalizationBundle,
    MarketNormalizationInput,
    MarketQualityFlag,
    PriceObservation,
    market_canonical_json,
)

ATOM = "http://www.w3.org/2005/Atom"
DATA = "http://schemas.microsoft.com/ado/2007/08/dataservices"
META = DATA + "/metadata"
TREASURY_ID = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "pages/xml-item?data=daily_treasury_yield_curve"
)
NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
PRICE_FIELDS = {
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "adj_open": "adjOpen",
    "adj_high": "adjHigh",
    "adj_low": "adjLow",
    "adj_close": "adjClose",
    "adj_volume": "adjVolume",
    "div_cash": "divCash",
    "split_factor": "splitFactor",
}


@dataclass(frozen=True)
class _JsonNumber:
    text: str


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _json(body: bytes) -> Any:
    return json.loads(
        body.decode("utf-8"),
        parse_int=_JsonNumber,
        parse_float=_JsonNumber,
        parse_constant=_JsonNumber,
        object_pairs_hook=_object,
    )


def _literal(value: Any) -> str:
    if isinstance(value, _JsonNumber):
        return value.text
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"), default=lambda item: item.text)


def _decimal(text: str | None) -> Decimal | None:
    if text is None or not NUMBER.fullmatch(text):
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _date(text: Any) -> date:
    if not isinstance(text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValueError("Expected exact source DATE")
    return date.fromisoformat(text)


def _label(text: Any, *, treasury: bool = False) -> date:
    pattern = (
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T00:00:00"
        if treasury
        else (r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T00:00:00(?:\.0+)?Z)?")
    )
    if not isinstance(text, str) or not re.fullmatch(pattern, text):
        raise ValueError("Unsupported provider daily date label")
    return _date(text[:10])


def market_input_hash(inputs: MarketNormalizationInput) -> str:
    return hashlib.sha256(market_canonical_json(inputs).encode()).hexdigest()


def market_output_hash(bundle: MarketNormalizationBundle) -> str:
    return hashlib.sha256(
        market_canonical_json(
            {
                "input_manifest_hash": bundle.input_manifest_hash,
                "prices": bundle.prices,
                "macros": bundle.macros,
                "flags": bundle.flags,
                "coverage_state": bundle.coverage_state,
            }
        ).encode()
    ).hexdigest()


def _aware(value: datetime) -> bool:
    return (
        isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None
    )


def _validate(inputs: MarketNormalizationInput) -> None:
    if type(inputs.requested_start) is not date or type(inputs.requested_end) is not date:
        raise ValueError("Finite date-only request bounds required")
    if inputs.requested_start > inputs.requested_end:
        raise ValueError("Reversed request bounds")
    if any(
        not value.strip()
        for value in (
            inputs.parser_revision,
            inputs.normalizer_revision,
            inputs.selection_policy_revision,
        )
    ):
        raise ValueError("Pinned interpretation revisions required")
    if inputs.source_as_of_date is not None and type(inputs.source_as_of_date) is not date:
        raise ValueError("Source vintage must be a DATE")
    if inputs.retrieval_cutoff is not None and not _aware(inputs.retrieval_cutoff):
        raise ValueError("Retrieval cutoff must be timezone-aware")
    ids: set[UUID] = set()
    for capture in inputs.captures:
        if capture.id in ids or capture.source_id != inputs.source_id:
            raise ValueError("Capture identity/source mismatch")
        ids.add(capture.id)
        if not re.fullmatch(r"[0-9a-f]{64}", capture.body_sha256) or capture.byte_count < 0:
            raise ValueError("Invalid capture content evidence")
        if not _aware(capture.fetched_at) or not _aware(capture.completed_at):
            raise ValueError("Capture times must be timezone-aware")
        if capture.fetched_at > capture.completed_at:
            raise ValueError("Capture completion precedes retrieval")
        if inputs.retrieval_cutoff is not None and capture.completed_at > inputs.retrieval_cutoff:
            raise ValueError("Capture is later than retrieval cutoff")


def _capture(
    inputs: MarketNormalizationInput, capture_id: UUID, body: bytes, key: str
) -> EvidenceCapture:
    captures = [c for c in inputs.captures if c.id == capture_id and c.role == "observations"]
    if len(captures) != 1:
        raise ValueError("Missing unique observation capture")
    capture = captures[0]
    if capture.source_object_key != key:
        raise ValueError("Unexpected source resource identity")
    if capture.byte_count != len(body) or capture.body_sha256 != hashlib.sha256(body).hexdigest():
        raise ValueError("Capture bytes differ from pinned evidence")
    return capture


def _single(inputs: MarketNormalizationInput, body: bytes, key: str) -> EvidenceCapture:
    captures = [c for c in inputs.captures if c.role == "observations"]
    if len(captures) != 1:
        raise ValueError("One coherent complete response is required")
    return _capture(inputs, captures[0].id, body, key)


def _definition(inputs: MarketNormalizationInput) -> MacroSeriesDefinition:
    definition = inputs.series_definition
    if definition is None or inputs.quote_binding is not None or inputs.quote_context is not None:
        raise ValueError("Macro scope requires one definition and no quote identity")
    if definition.source_id != inputs.source_id:
        raise ValueError("Definition source mismatch")
    if not any(
        c.id == definition.metadata_capture_id and c.role == "series_definition"
        for c in inputs.captures
    ):
        raise ValueError("Definition evidence is not pinned")
    if definition.unit_code not in {
        "percent_per_year",
        "percent",
        "percentage_points",
        "basis_points",
        "index",
        "count",
    }:
        raise ValueError("Unsupported macro unit")
    if (
        not isinstance(definition.unit_multiplier, Decimal)
        or not definition.unit_multiplier.is_finite()
        or definition.unit_multiplier <= 0
    ):
        raise ValueError("Unit multiplier must be an exact positive finite decimal")
    if definition.frequency not in {
        "daily",
        "business_day",
        "weekly",
        "monthly",
        "quarterly",
        "annual",
    }:
        raise ValueError("Unsupported macro frequency")
    if definition.seasonal_adjustment not in {
        "adjusted",
        "not_adjusted",
        "not_applicable",
        "unknown",
    }:
        raise ValueError("Unsupported seasonal basis")
    if definition.reference_date_convention not in {"measurement_date", "period_start"}:
        raise ValueError("Unsupported macro reference-date convention")
    if not all(
        (
            definition.source_series_key,
            definition.source_locator,
            definition.definition_revision,
            definition.units_text,
            definition.reference_date_convention,
            definition.upstream_source_name,
            definition.upstream_rights_reference,
            definition.geography,
        )
    ):
        raise ValueError("Reviewed macro interpretation evidence required")
    if not re.fullmatch(r"[0-9a-f]{64}", definition.content_sha256):
        raise ValueError("Invalid definition content hash")
    if definition.definition_as_of_basis not in {"source_supplied", "capture_only", "unknown"}:
        raise ValueError("Unsupported definition vintage basis")
    if (definition.definition_as_of_basis == "source_supplied") != (
        definition.definition_as_of_date is not None
    ):
        raise ValueError("Definition vintage basis and date disagree")
    return definition


def _reference_date(when: date, definition: MacroSeriesDefinition) -> None:
    if definition.reference_date_convention == "measurement_date":
        if definition.frequency not in {"daily", "business_day"}:
            raise ValueError("Unsupported native reference-date/frequency combination")
        return
    if definition.frequency not in {"monthly", "quarterly", "annual"}:
        raise ValueError("Period-start convention requires a reviewed calendar frequency")
    if (
        when.day != 1
        or (definition.frequency == "quarterly" and when.month not in {1, 4, 7, 10})
        or (definition.frequency == "annual" and when.month != 1)
    ):
        raise ValueError("Reference label is not the reviewed period start")


def _flag(
    inputs: MarketNormalizationInput,
    rule: str,
    message: str,
    *,
    capture: EvidenceCapture | None = None,
    when: date | None = None,
    field: str | None = None,
    locator: str | None = None,
    severity: Any = "blocking",
) -> MarketQualityFlag:
    values = [
        market_input_hash(inputs),
        rule,
        capture.id if capture else None,
        when,
        field,
        locator,
    ]
    return MarketQualityFlag(
        evidence_id("market_flag", values),
        when,
        field,
        rule,
        severity,
        message,
        capture_id=capture.id if capture else None,
        source_locator=locator,
    )


def _bundle(
    inputs: MarketNormalizationInput,
    *,
    prices: tuple[PriceObservation, ...] = (),
    macros: tuple[MacroObservation, ...] = (),
    flags: tuple[MarketQualityFlag, ...] = (),
) -> MarketNormalizationBundle:
    coverage: CoverageState = "unknown"
    if not prices and not macros:
        coverage = "unavailable"
        if not flags:
            flags = (
                _flag(inputs, "source_rows_absent", "No source observations in requested window"),
            )
    elif any(flag.severity == "blocking" for flag in flags):
        coverage = "partial"
    flags += (
        _flag(
            inputs,
            "calendar_coverage_unknown",
            "Complete source response does not prove calendar coverage",
            severity="info",
        ),
    )
    initial = MarketNormalizationBundle(
        inputs, prices, macros, flags, coverage, market_input_hash(inputs), ""
    )
    return MarketNormalizationBundle(
        inputs,
        prices,
        macros,
        flags,
        coverage,
        initial.input_manifest_hash,
        market_output_hash(initial),
    )


def _macro(
    inputs: MarketNormalizationInput,
    definition: MacroSeriesDefinition,
    capture: EvidenceCapture,
    locator: str,
    when: date,
    date_text: str,
    value: Decimal | None,
    state: Any,
    original: str | None,
    **vintage: Any,
) -> MacroObservation:
    return MacroObservation(
        evidence_id("macro_observation", [market_input_hash(inputs), capture.id, locator]),
        when,
        definition.id,
        capture.id,
        locator,
        date_text,
        value,
        state,
        original,
        None,
        inputs.normalizer_revision,
        **vintage,
    )


def normalize_treasury(body: bytes, inputs: MarketNormalizationInput) -> MarketNormalizationBundle:
    _validate(inputs)
    definition = _definition(inputs)
    capture = _single(inputs, body, "daily_treasury_yield_curve")
    if definition.source_series_key not in {"BC_2YEAR", "BC_10YEAR"}:
        raise ValueError("Unreviewed Treasury maturity")
    if (
        definition.unit_code not in {"percent", "percent_per_year"}
        or definition.unit_multiplier != Decimal("1")
        or definition.frequency != "business_day"
        or definition.reference_date_convention != "measurement_date"
    ):
        raise ValueError("Treasury native unit/frequency definition mismatch")
    if inputs.treasury_month is None or not re.fullmatch(r"[0-9]{6}", inputs.treasury_month):
        raise ValueError("Explicit Treasury YYYYMM resource required")
    month = inputs.treasury_month
    _date(month[:4] + "-" + month[4:] + "-01")
    if any(
        value.strftime("%Y%m") != month for value in (inputs.requested_start, inputs.requested_end)
    ):
        raise ValueError("Selection must lie within the explicit Treasury resource month")
    if len(body) > 8 * 1024 * 1024 or re.search(rb"<!\s*(DOCTYPE|ENTITY)\b", body, re.I):
        raise ValueError("Unsafe or oversized Treasury XML")
    try:
        root = etree.fromstring(
            body,
            etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True, recover=False),
        )
    except etree.XMLSyntaxError as exc:
        raise ValueError("Malformed Treasury XML") from exc
    info = root.getroottree().docinfo
    if (
        info.internalDTD is not None
        or info.externalDTD is not None
        or root.tag != f"{{{ATOM}}}feed"
    ):
        raise ValueError("Unsafe or wrong Treasury XML root")
    if any(
        not isinstance(child.tag, str) or not child.tag.startswith(f"{{{ATOM}}}") for child in root
    ):
        raise ValueError("Treasury feed namespace drift")
    if (
        len(root.findall(f"{{{ATOM}}}title")) != 1
        or len(root.findall(f"{{{ATOM}}}id")) != 1
        or root.findtext(f"{{{ATOM}}}title") != "DailyTreasuryYieldCurveRateData"
        or root.findtext(f"{{{ATOM}}}id") != TREASURY_ID
    ):
        raise ValueError("Wrong Treasury dataset")
    rows: list[MacroObservation] = []
    flags: list[MarketQualityFlag] = []
    seen: set[date] = set()
    for index, entry in enumerate(root.findall(f"{{{ATOM}}}entry")):
        category = entry.find(f"{{{ATOM}}}category")
        if (
            category is None
            or category.get("term") != "TreasuryDataWarehouseModel.DailyTreasuryYieldCurveRateDatum"
        ):
            raise ValueError("Wrong Treasury entry identity")
        contents = entry.findall(f"{{{ATOM}}}content")
        if len(contents) != 1 or contents[0].get("type") != "application/xml":
            raise ValueError("Unsupported Treasury content")
        properties = contents[0].findall(f"{{{META}}}properties")
        if len(properties) != 1:
            raise ValueError("Missing unique Treasury properties")
        props = properties[0]
        for node in props:
            if not isinstance(node.tag, str) or not node.tag.startswith(f"{{{DATA}}}") or len(node):
                raise ValueError("Treasury property namespace or structure drift")
        dates = props.findall(f"{{{DATA}}}NEW_DATE")
        if len(dates) != 1 or dates[0].get(f"{{{META}}}type") != "Edm.DateTime":
            raise ValueError("Missing unique typed Treasury date")
        source_date = dates[0].text
        when = _label(source_date, treasury=True)
        if when.strftime("%Y%m") != month or when in seen:
            raise ValueError("Duplicate or out-of-resource Treasury date")
        seen.add(when)
        fields = props.findall(f"{{{DATA}}}{definition.source_series_key}")
        if len(fields) > 1 or (fields and fields[0].get(f"{{{META}}}type") != "Edm.Double"):
            raise ValueError("Duplicate or mistyped selected Treasury field")
        if not inputs.requested_start <= when <= inputs.requested_end:
            continue
        locator = f"/feed/entry[{index + 1}]/content/properties/{definition.source_series_key}"
        if not fields:
            flags.append(
                _flag(
                    inputs,
                    "source_field_absent",
                    "Source omitted requested maturity; no observation fabricated",
                    capture=capture,
                    when=when,
                    field="value",
                    locator=locator,
                )
            )
            continue
        field = fields[0]
        text = field.text
        null = field.get(f"{{{META}}}null")
        state = "observed"
        value = _decimal(text)
        if null is not None:
            state = (
                "source_missing"
                if null == "true" and not text and inputs.allow_legacy_treasury_null
                else "unparseable"
            )
            value = None
        elif value is None:
            state = "unparseable"
        if state != "observed":
            flags.append(
                _flag(
                    inputs,
                    "source_missing" if state == "source_missing" else "unparseable_value",
                    "Source selected value unavailable; original text retained",
                    capture=capture,
                    when=when,
                    field="value",
                    locator=locator,
                )
            )
        assert isinstance(source_date, str)
        rows.append(
            _macro(inputs, definition, capture, locator, when, source_date, value, state, text)
        )
    if inputs.source_as_of_date is not None:
        return _bundle(
            inputs,
            flags=(
                _flag(
                    inputs,
                    "source_vintage_unavailable",
                    "Treasury current capture cannot reconstruct historical source vintages",
                    capture=capture,
                ),
            ),
        )
    return _bundle(
        inputs, macros=tuple(sorted(rows, key=lambda row: row.reference_date)), flags=tuple(flags)
    )


def normalize_tiingo(body: bytes, inputs: MarketNormalizationInput) -> MarketNormalizationBundle:
    _validate(inputs)
    binding, context = inputs.quote_binding, inputs.quote_context
    if binding is None or context is None or inputs.series_definition is not None:
        raise ValueError("Price scope requires a reviewed binding and quote context")
    capture = _single(inputs, body, "tiingo_eod/" + binding.provider_symbol)
    if binding.source_id != inputs.source_id or not any(
        c.id == binding.identity_capture_id and c.role == "quote_identity" for c in inputs.captures
    ):
        raise ValueError("Quote binding identity evidence mismatch")
    if inputs.source_as_of_date is not None:
        return _bundle(
            inputs,
            flags=(
                _flag(
                    inputs,
                    "source_vintage_unavailable",
                    "Tiingo adjustment vintage is capture-only",
                    capture=capture,
                ),
            ),
        )
    if (
        binding.security_id != context.security_id
        or binding.quote_identifier_id != context.quote_identifier_id
        or not context.venue
        or not context.quote_currency
        or not re.fullmatch(r"[A-Z]{3}", context.quote_currency)
        or context.instrument_kind != "common"
    ):
        return _bundle(
            inputs,
            flags=(
                _flag(
                    inputs,
                    "quote_identity_unverified",
                    "Dated venue/currency/common-instrument identity is unsupported",
                    capture=capture,
                ),
            ),
        )
    payload = _json(body)
    if not isinstance(payload, list):
        raise ValueError("Tiingo response must be an EOD array, not an API error")
    rows: list[PriceObservation] = []
    flags: list[MarketQualityFlag] = []
    seen: set[date] = set()
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError("Malformed Tiingo observation")
        source_date = row.get("date")
        when = _label(source_date)
        if when in seen or not inputs.requested_start <= when <= inputs.requested_end:
            raise ValueError("Duplicate or out-of-request price date")
        seen.add(when)
        locator = f"$[{index}]"
        if (
            when < binding.valid_from
            or when < context.valid_from
            or (binding.valid_to is not None and when >= binding.valid_to)
            or (context.valid_to is not None and when >= context.valid_to)
        ):
            flags.append(
                _flag(
                    inputs,
                    "quote_identity_outside_validity",
                    "Session outside reviewed binding or quote/closure interval",
                    capture=capture,
                    when=when,
                    locator=locator,
                )
            )
            continue
        if "ticker" in row and row["ticker"] != binding.provider_symbol:
            raise ValueError("Response symbol conflicts with requested identity")
        fields: dict[str, Any] = {}
        for field, source_field in PRICE_FIELDS.items():
            value: Decimal | None = None
            text: str | None = None
            state = "missing"
            if source_field in row:
                original = row[source_field]
                text = _literal(original)
                state = "source_null" if original is None else "unparseable"
                if isinstance(original, _JsonNumber):
                    value = _decimal(original.text)
                    if value is not None and (
                        value < 0 or (field == "split_factor" and value == 0)
                    ):
                        value = None
                    if value is not None:
                        state = "observed"
            fields[field], fields[field + "_state"], fields[field + "_text"] = value, state, text
            if state != "observed":
                flags.append(
                    _flag(
                        inputs,
                        "price_" + state,
                        "Source field unavailable; no substitution or reconstruction",
                        capture=capture,
                        when=when,
                        field=field,
                        locator=locator + "." + source_field,
                    )
                )
        for prefix in ("", "adj_"):
            opening, high, low, close = (
                fields[prefix + field] for field in ("open", "high", "low", "close")
            )
            if (high is not None and low is not None and high < low) or any(
                value is not None
                and ((high is not None and value > high) or (low is not None and value < low))
                for value in (opening, close)
            ):
                # No member of an inconsistent OHLC group can be identified as
                # correct from the response alone. Keep separate groups/volume usable.
                flags.extend(
                    _flag(
                        inputs,
                        "ohlc_inconsistent",
                        "Source OHLC is inconsistent; values are preserved without correction",
                        capture=capture,
                        when=when,
                        field=prefix + field,
                        locator=locator,
                    )
                    for field in ("open", "high", "low", "close")
                )
        dividend_currency = context.dividend_currency
        if (
            dividend_currency is None
            or not re.fullmatch(r"[A-Z]{3}", dividend_currency)
            or not context.dividend_currency_evidence
        ):
            dividend_currency = None
            if fields["div_cash_state"] == "observed":
                flags.append(
                    _flag(
                        inputs,
                        "dividend_currency_unverified",
                        "Dividend amount retained; currency not established",
                        capture=capture,
                        when=when,
                        field="div_cash",
                        locator=locator + ".divCash",
                    )
                )
        assert isinstance(source_date, str)
        rows.append(
            PriceObservation(
                evidence_id("price_observation", [market_input_hash(inputs), capture.id, locator]),
                when,
                capture.id,
                locator,
                binding.id,
                binding.quote_identifier_id,
                binding.security_id,
                context.quote_currency,
                dividend_currency,
                source_date,
                inputs.normalizer_revision,
                session_timezone=context.session_timezone,
                **fields,
            )
        )
    return _bundle(
        inputs, prices=tuple(sorted(rows, key=lambda row: row.session_date)), flags=tuple(flags)
    )


def _integer(value: Any) -> int:
    if not isinstance(value, _JsonNumber) or not re.fullmatch(r"0|[1-9][0-9]*", value.text):
        raise ValueError("Invalid integral FRED pagination metadata")
    return int(value.text)


def normalize_fred(
    pages: tuple[FredPage, ...], inputs: MarketNormalizationInput
) -> MarketNormalizationBundle:
    _validate(inputs)
    definition = _definition(inputs)
    if not pages or len({page.capture_id for page in pages}) != len(pages):
        raise ValueError("Missing or duplicate FRED capture pages")
    if {c.id for c in inputs.captures if c.role == "observations"} != {
        page.capture_id for page in pages
    }:
        raise ValueError("FRED page captures differ from pinned observation inputs")
    for page in pages:
        if (
            any(
                type(value) is not date
                for value in (
                    page.observation_start,
                    page.observation_end,
                    page.realtime_start,
                    page.realtime_end,
                )
            )
            or type(page.output_type) is not int
        ):
            raise ValueError("FRED request requires date labels and integral output type")
    ordered = sorted(pages, key=lambda page: page.offset)
    first = ordered[0]
    if first.realtime_start > first.realtime_end:
        raise ValueError("Reversed FRED source-vintage interval")
    as_of = inputs.source_as_of_date
    if as_of is not None and not first.realtime_start <= as_of <= first.realtime_end:
        raise ValueError("Explicit request does not cover source-as-of date")
    expected_offset = 0
    total: int | None = None
    rows: list[MacroObservation] = []
    flags: list[MarketQualityFlag] = []
    intervals: dict[date, list[tuple[date, date]]] = {}
    previous_date: date | None = None
    for page in ordered:
        capture = _capture(
            inputs, page.capture_id, page.body, "fred_observations/" + definition.source_series_key
        )
        if (
            page.series_id != definition.source_series_key
            or page.observation_start != inputs.requested_start
            or page.observation_end != inputs.requested_end
            or page.units != "lin"
            or page.output_type != 1
            or page.frequency is not None
            or page.aggregation_method is not None
            or page.order_by != "observation_date"
            or page.sort_order != "asc"
            or page.realtime_start != first.realtime_start
            or page.realtime_end != first.realtime_end
            or type(page.offset) is not int
            or type(page.limit) is not int
            or not 0 < page.limit <= 100000
            or page.offset != expected_offset
        ):
            raise ValueError(
                "FRED request pages are incomplete or change native series/filter/vintage"
            )
        data = _json(page.body)
        if not isinstance(data, dict) or not isinstance(data.get("observations"), list):
            raise ValueError("FRED response is not an observation page")
        if (
            data.get("units") != "lin"
            or _integer(data.get("output_type")) != 1
            or data.get("order_by") != "observation_date"
            or data.get("sort_order") != "asc"
            or data.get("file_type") != "json"
            or _date(data.get("observation_start")) != page.observation_start
            or _date(data.get("observation_end")) != page.observation_end
            or _date(data.get("realtime_start")) != page.realtime_start
            or _date(data.get("realtime_end")) != page.realtime_end
            or _integer(data.get("offset")) != page.offset
            or _integer(data.get("limit")) != page.limit
            or ("series_id" in data and data["series_id"] != page.series_id)
        ):
            raise ValueError("FRED envelope disagrees with exact request")
        count = _integer(data.get("count"))
        if total is not None and count != total:
            raise ValueError("FRED count changed between pages")
        total = count
        observations = data["observations"]
        if len(observations) != min(page.limit, count - page.offset) or page.offset > count:
            raise ValueError("Incomplete FRED page length")
        expected_offset += len(observations)
        for index, raw in enumerate(observations):
            if not isinstance(raw, dict):
                raise ValueError("Malformed FRED observation")
            source_date = raw.get("date")
            when = _date(source_date)
            _reference_date(when, definition)
            begin, end = _date(raw.get("realtime_start")), _date(raw.get("realtime_end"))
            if (
                not inputs.requested_start <= when <= inputs.requested_end
                or begin > end
                or begin < page.realtime_start
                or end > page.realtime_end
                or (previous_date is not None and when < previous_date)
            ):
                raise ValueError("FRED observation outside date/vintage/order bounds")
            previous_date = when
            if any(
                begin <= old_end and old_begin <= end
                for old_begin, old_end in intervals.get(when, [])
            ):
                raise ValueError("Duplicate or conflicting FRED revision intervals")
            intervals.setdefault(when, []).append((begin, end))
            if as_of is not None and not begin <= as_of <= end:
                continue
            locator = f"$.observations[{index}]"
            original = raw.get("value")
            text = _literal(original) if "value" in raw else None
            value = _decimal(original) if isinstance(original, str) else None
            state = (
                "observed"
                if value is not None
                else "source_missing"
                if original == "."
                else "unparseable"
            )
            if state != "observed":
                flags.append(
                    _flag(
                        inputs,
                        "source_missing" if state == "source_missing" else "unparseable_value",
                        "Native FRED value unavailable; original spelling retained",
                        capture=capture,
                        when=when,
                        field="value",
                        locator=locator,
                    )
                )
            assert isinstance(source_date, str)
            clipped = as_of is not None and page.realtime_start == page.realtime_end == as_of
            rows.append(
                _macro(
                    inputs,
                    definition,
                    capture,
                    locator,
                    when,
                    source_date,
                    value,
                    state,
                    text,
                    source_realtime_start=begin,
                    source_realtime_end=end,
                    source_vintage_basis=(
                        "current_only"
                        if as_of is None
                        else "requested_as_of"
                        if clipped
                        else "source_interval"
                    ),
                    requested_source_as_of=as_of,
                )
            )
    if expected_offset != total:
        raise ValueError("Missing FRED pages")
    return _bundle(inputs, macros=tuple(rows), flags=tuple(flags))


def unavailable_market_bundle(
    inputs: MarketNormalizationInput, reason: str
) -> MarketNormalizationBundle:
    """Publish a sourced gap without inventing observations or replacing older evidence."""
    _validate(inputs)
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", reason):
        raise ValueError("Unavailable market reason must be an explicit rule key")
    if not inputs.captures and not inputs.attempt_ids:
        raise ValueError("Unavailable market batch requires immutable source evidence")
    if any(c.role == "observations" for c in inputs.captures):
        raise ValueError("Failed response captures require the fetch_outcome role")
    return _bundle(
        inputs,
        flags=(_flag(inputs, reason, "Market request unavailable; no older value substituted"),),
    )
