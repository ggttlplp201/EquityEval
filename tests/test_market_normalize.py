"""S4 numeric expectations, specified before the implementation; vendor cases are fictional."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from equity_ingest.financial_types import EvidenceCapture
from equity_ingest.market_normalize import normalize_fred, normalize_tiingo, normalize_treasury
from equity_ingest.market_types import (
    FredPage,
    MacroSeriesDefinition,
    MarketNormalizationInput,
    QuoteBinding,
    QuoteContext,
)

SOURCE, POLICY, CAPTURE, METADATA, DEFINITION, BINDING, QUOTE, SECURITY = (
    UUID(int=n) for n in range(1, 9)
)
AT = datetime(2026, 9, 12, 11, tzinfo=UTC)


def market_input(body, *, kind="treasury", series="BC_10YEAR"):
    key = {
        "treasury": "daily_treasury_yield_curve",
        "price": "tiingo_eod/TEST",
        "fred": f"fred_observations/{series}",
    }[kind]
    capture = EvidenceCapture(
        CAPTURE,
        SOURCE,
        key,
        "https://example.invalid/public",
        hashlib.sha256(body).hexdigest(),
        len(body),
        AT,
        AT,
        "observations",
    )
    metadata = EvidenceCapture(
        METADATA,
        SOURCE,
        "reviewed_definition",
        "https://example.invalid/definition",
        hashlib.sha256(b"reviewed").hexdigest(),
        8,
        AT,
        AT,
        "series_definition" if kind != "price" else "quote_identity",
    )
    definition = MacroSeriesDefinition(
        DEFINITION,
        SOURCE,
        series,
        METADATA,
        "/definition",
        "a" * 64,
        "definition-v1",
        "Reviewed nominal Treasury" if kind == "treasury" else "Fictional native rate",
        "Percent",
        "percent",
        Decimal("1"),
        "business_day" if kind == "treasury" else "daily",
        "unknown",
        "US",
        "measurement_date",
        "Treasury" if kind == "treasury" else "Fictional provider",
        "reviewed-rights",
    )
    binding = QuoteBinding(
        BINDING,
        SOURCE,
        QUOTE,
        SECURITY,
        "TEST",
        date(2024, 1, 1),
        None,
        METADATA,
        "/identity",
        "identity-v1",
        AT,
        "reviewer",
        "b" * 64,
    )
    context = QuoteContext(
        QUOTE,
        SECURITY,
        "TEST_VENUE",
        "USD",
        "common",
        date(2024, 1, 1),
        dividend_currency="USD",
        dividend_currency_evidence="reviewed dividend currency",
    )
    return MarketNormalizationInput(
        SOURCE,
        POLICY,
        date(2024, 1, 2) if kind == "price" else date(2026, 9, 1),
        date(2024, 1, 2) if kind == "price" else date(2026, 9, 30),
        (capture, metadata),
        "parser-v1",
        "normalizer-v1",
        "selection-v1",
        series_definition=definition if kind != "price" else None,
        quote_binding=binding if kind == "price" else None,
        quote_context=context if kind == "price" else None,
        treasury_month="202609" if kind == "treasury" else None,
    )


def treasury_xml(
    value="4.2500",
    *,
    absent=False,
    date_text="2026-09-10T00:00:00",
    extra="",
    value_attrs='m:type="Edm.Double"',
):
    dataset_id = (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
        "pages/xml-item?data=daily_treasury_yield_curve"
    )
    field = "" if absent else f"<d:BC_10YEAR {value_attrs}>{value}</d:BC_10YEAR>"
    return f"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"
 xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
 xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
<title>DailyTreasuryYieldCurveRateData</title>
<id>{dataset_id}</id>
<entry><category term="TreasuryDataWarehouseModel.DailyTreasuryYieldCurveRateDatum"/>
<content type="application/xml">
<m:properties>
<d:NEW_DATE m:type="Edm.DateTime">{date_text}</d:NEW_DATE>{field}{extra}
</m:properties></content></entry></feed>""".encode()


def price_body(**changes):
    row = dict(
        date="2024-01-02T00:00:00.000Z",
        open=98,
        high=102,
        low=97,
        close=100,
        volume=1000,
        adjOpen=49,
        adjHigh=51,
        adjLow=48.5,
        adjClose=50,
        adjVolume=2000,
        divCash=0,
        splitFactor=1,
    )
    row.update(changes)
    return json.dumps([row], separators=(",", ":")).encode()


def fred_case(values=("4.25",), *, offset=0, limit=10, count=None, capture_id=CAPTURE):
    payload = {
        "realtime_start": "2026-09-12",
        "realtime_end": "2026-09-12",
        "observation_start": "2026-09-01",
        "observation_end": "2026-09-30",
        "units": "lin",
        "output_type": 1,
        "file_type": "json",
        "order_by": "observation_date",
        "sort_order": "asc",
        "count": len(values) if count is None else count,
        "offset": offset,
        "limit": limit,
        "observations": [
            {
                "realtime_start": "2026-09-12",
                "realtime_end": "2026-09-12",
                "date": f"2026-09-{offset + i + 1:02d}",
                "value": v,
            }
            for i, v in enumerate(values)
        ],
    }
    body = json.dumps(payload).encode()
    inputs = replace(
        market_input(body, kind="fred", series="TEST_RATE"), source_as_of_date=date(2026, 9, 12)
    )
    page = FredPage(
        capture_id,
        body,
        "TEST_RATE",
        inputs.requested_start,
        inputs.requested_end,
        date(2026, 9, 12),
        date(2026, 9, 12),
        offset,
        limit,
    )
    return inputs, page


def test_treasury_exact_native_decimal_and_unknown_release_time():
    body = treasury_xml("9007199254740993.000100")
    with localcontext() as ctx:
        ctx.prec = 4
        bundle = normalize_treasury(body, market_input(body))
    row = bundle.macros[0]
    assert row.value == Decimal("9007199254740993.000100")
    assert row.original_value_text == "9007199254740993.000100"
    assert row.reference_date == date(2026, 9, 10)
    assert row.source_date_text == "2026-09-10T00:00:00"
    assert row.publication_precision == "unknown"
    assert row.source_published_at is row.source_realtime_start is None
    assert row.source_vintage_basis == "current_only"
    assert bundle.coverage_state == "unknown"


@pytest.mark.parametrize("value", ["", "true", "NaN", "Infinity", "1,000", "1_000", "--1"])
def test_treasury_malformed_value_is_null_with_blocking_flag(value):
    body = treasury_xml(value)
    bundle = normalize_treasury(body, market_input(body))
    assert bundle.macros[0].value is None
    assert bundle.macros[0].value_state == "unparseable"
    assert any(f.severity == "blocking" for f in bundle.flags)


def test_absent_treasury_maturity_has_flag_without_fake_observation():
    body = treasury_xml(absent=True)
    result = normalize_treasury(body, market_input(body))
    assert result.macros == ()
    assert any(
        f.rule_key == "source_field_absent" and f.reference_date == date(2026, 9, 10)
        for f in result.flags
    )


def test_treasury_legacy_null_needs_explicit_reviewed_rule():
    body = treasury_xml("", value_attrs='m:type="Edm.Double" m:null="true"')
    inputs = market_input(body)
    assert normalize_treasury(body, inputs).macros[0].value_state == "unparseable"
    result = normalize_treasury(body, replace(inputs, allow_legacy_treasury_null=True))
    assert result.macros[0].value_state == "source_missing"


def test_treasury_partial_month_filters_only_after_whole_resource_validation():
    body = treasury_xml(date_text="2026-09-01T00:00:00")
    result = normalize_treasury(
        body, replace(market_input(body), requested_start=date(2026, 9, 10))
    )
    assert result.macros == ()
    assert result.coverage_state == "unavailable"


@pytest.mark.parametrize(
    "change", ["dataset", "namespace", "date", "doctype", "duplicate", "type", "date_time"]
)
def test_treasury_rejects_unsafe_or_ambiguous_document(change):
    body = treasury_xml()
    if change == "dataset":
        body = body.replace(
            b"DailyTreasuryYieldCurveRateData", b"DailyTreasuryRealYieldCurveRateData"
        )
    if change == "namespace":
        body = body.replace(
            b'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"',
            b'xmlns:d="https://wrong.invalid"',
        )
    if change == "date":
        body = body.replace(b"2026-09-10", b"2026-08-31")
    if change == "date_time":
        body = body.replace(b"T00:00:00", b"T03:00:00")
    if change == "doctype":
        body = body.replace(
            b"<feed", b'<!DOCTYPE feed [<!ENTITY fake SYSTEM "file:///etc/passwd">]><feed'
        )
    if change == "duplicate":
        body = body.replace(
            b"</m:properties>", b'<d:BC_10YEAR m:type="Edm.Double">9</d:BC_10YEAR></m:properties>'
        )
    if change == "type":
        body = body.replace(b"Edm.Double", b"Edm.Int32")
    with pytest.raises(ValueError):
        normalize_treasury(body, market_input(body))


def test_treasury_rejects_wrong_units_capture_hash_and_historical_source_vintage():
    body = treasury_xml()
    inputs = market_input(body)
    with pytest.raises(ValueError):
        normalize_treasury(body + b" ", inputs)
    with pytest.raises(ValueError):
        normalize_treasury(
            body,
            replace(inputs, series_definition=replace(inputs.series_definition, unit_code="index")),
        )
    result = normalize_treasury(body, replace(inputs, source_as_of_date=date(2020, 1, 1)))
    assert result.macros == () and any(
        f.rule_key == "source_vintage_unavailable" for f in result.flags
    )


def test_tiingo_keeps_raw_adjusted_session_and_zero_separate():
    body = price_body()
    bundle = normalize_tiingo(body, market_input(body, kind="price"))
    row = bundle.prices[0]
    assert (row.close, row.adj_close, row.volume, row.adj_volume) == (
        Decimal("100"),
        Decimal("50"),
        Decimal("1000"),
        Decimal("2000"),
    )
    assert row.div_cash == 0 and row.div_cash_state == "observed"
    assert row.session_date == date(2024, 1, 2)
    assert row.source_published_at is row.adjustment_vintage_date is None
    assert row.adjustment_vintage_basis == "capture_only"


def test_price_numeric_token_precision_and_lexical_spelling():
    body = b'[{"date":"2024-01-02T00:00:00.000Z","close":9007199254740993.0001e-2}]'
    row = normalize_tiingo(body, market_input(body, kind="price")).prices[0]
    assert row.close == Decimal("90071992547409.930001")
    assert row.close_text == "9007199254740993.0001e-2"
    assert row.adj_close is None and row.adj_close_state == "missing"
    assert row.split_factor is None and row.split_factor_state == "missing"


@pytest.mark.parametrize(
    "field,value,state",
    [
        ("close", None, "source_null"),
        ("close", True, "unparseable"),
        ("close", -1, "unparseable"),
        ("volume", -1, "unparseable"),
        ("splitFactor", 0, "unparseable"),
        ("close", "12.34", "unparseable"),
    ],
)
def test_price_bad_fields_cannot_become_plausible_numbers(field, value, state):
    body = price_body(**{field: value})
    row = normalize_tiingo(body, market_input(body, kind="price")).prices[0]
    normalized = {"splitFactor": "split_factor"}.get(field, field)
    assert getattr(row, normalized) is None
    assert getattr(row, normalized + "_state") == state


def test_price_ohlc_disagreement_is_preserved_and_flagged():
    body = price_body(high=99)
    result = normalize_tiingo(body, market_input(body, kind="price"))
    assert result.prices[0].high == 99 and result.prices[0].close == 100
    assert any(f.rule_key == "ohlc_inconsistent" and f.severity == "blocking" for f in result.flags)


@pytest.mark.parametrize(
    "change", ["currency", "venue", "identity", "closed", "binding_closed", "ads"]
)
def test_quote_identity_failure_blocks_numeric_rows(change):
    body = price_body()
    inputs = market_input(body, kind="price")
    changes = {
        "currency": {"quote_currency": None},
        "venue": {"venue": None},
        "identity": {"security_id": UUID(int=999)},
        "closed": {"valid_to": date(2024, 1, 2)},
        "ads": {"instrument_kind": "ads"},
    }
    inputs = (
        replace(inputs, quote_binding=replace(inputs.quote_binding, valid_to=date(2024, 1, 2)))
        if change == "binding_closed"
        else replace(inputs, quote_context=replace(inputs.quote_context, **changes[change]))
    )
    result = normalize_tiingo(body, inputs)
    assert result.prices == ()
    assert any(f.severity == "blocking" for f in result.flags)


def test_unknown_dividend_currency_blocks_dividend_only():
    body = price_body(divCash=1)
    inputs = market_input(body, kind="price")
    result = normalize_tiingo(
        body,
        replace(
            inputs,
            quote_context=replace(
                inputs.quote_context, dividend_currency=None, dividend_currency_evidence=None
            ),
        ),
    )
    assert result.prices[0].close == 100 and result.prices[0].div_cash == 1
    assert result.prices[0].dividend_currency is None
    assert any(
        f.field_key == "div_cash" and f.rule_key == "dividend_currency_unverified"
        for f in result.flags
    )


def test_duplicate_sessions_and_json_keys_are_rejected():
    body = price_body()
    for bad in (
        body[:-1] + b"," + body[1:],
        body.replace(b'"close":100', b'"close":100,"close":101'),
    ):
        with pytest.raises(ValueError):
            normalize_tiingo(bad, market_input(bad, kind="price"))


@pytest.mark.parametrize(
    "value,expected,state",
    [
        ("4.25", "4.25", "observed"),
        ("0.00", "0.00", "observed"),
        ("-0.25", "-0.25", "observed"),
        (".", None, "source_missing"),
        (None, None, "unparseable"),
        (True, None, "unparseable"),
        ("NaN", None, "unparseable"),
        ("1_000", None, "unparseable"),
    ],
)
def test_fred_native_values_and_missingness(value, expected, state):
    inputs, page = fred_case((value,))
    row = normalize_fred((page,), inputs).macros[0]
    assert row.value == (Decimal(expected) if expected is not None else None)
    assert row.value_state == state
    assert row.source_vintage_basis == "requested_as_of"
    assert row.source_realtime_start == row.source_realtime_end == date(2026, 9, 12)
    assert row.publication_precision == "unknown"


def test_fred_pages_require_complete_unchanged_envelope_and_native_request():
    inputs, one = fred_case(("4.25",), limit=1, count=2)
    _, two = fred_case((".",), offset=1, limit=1, count=2, capture_id=UUID(int=10))
    capture = replace(
        inputs.captures[0],
        id=two.capture_id,
        body_sha256=hashlib.sha256(two.body).hexdigest(),
        byte_count=len(two.body),
    )
    inputs = replace(inputs, captures=inputs.captures + (capture,))
    result = normalize_fred((two, one), inputs)
    assert len(result.macros) == 2 and result.macros[-1].value_state == "source_missing"
    for bad in (
        (one,),
        (one, replace(two, offset=2)),
        (replace(one, units="pch"), two),
        (one, replace(two, series_id="OTHER")),
    ):
        with pytest.raises(ValueError):
            normalize_fred(bad, inputs)


def test_capture_cutoff_cannot_use_later_retrieval_or_metadata():
    body = treasury_xml()
    inputs = replace(market_input(body), retrieval_cutoff=datetime(2026, 9, 1, tzinfo=UTC))
    with pytest.raises(ValueError):
        normalize_treasury(body, inputs)


def test_same_pins_have_stable_hashes_and_definition_changes_have_different_identity():
    body = treasury_xml()
    inputs = market_input(body)
    first = normalize_treasury(body, inputs)
    assert first == normalize_treasury(body, inputs)
    other = normalize_treasury(body, replace(inputs, normalizer_revision="normalizer-v2"))
    assert first.input_manifest_hash != other.input_manifest_hash
    assert first.output_manifest_hash != other.output_manifest_hash


def test_fred_current_snapshot_keeps_bounds_without_claiming_full_revision_lifetime():
    inputs, page = fred_case()
    row = normalize_fred((page,), replace(inputs, source_as_of_date=None)).macros[0]
    assert row.source_vintage_basis == "current_only"
    assert row.requested_source_as_of is None
    assert row.source_realtime_start == row.source_realtime_end == date(2026, 9, 12)


def test_fred_source_asof_preserves_inclusive_last_finite_date():
    inputs, page = fred_case()
    raw = json.loads(page.body)
    raw["realtime_start"] = "1776-07-04"
    raw["realtime_end"] = "9999-12-31"
    raw["observations"] = [
        {
            "date": "2026-09-01",
            "realtime_start": "2026-09-02",
            "realtime_end": "2026-09-11",
            "value": "4.25",
        },
        {
            "date": "2026-09-01",
            "realtime_start": "2026-09-12",
            "realtime_end": "9999-12-31",
            "value": ".",
        },
    ]
    raw["count"] = 2
    body = json.dumps(raw).encode()
    inputs = replace(
        inputs,
        captures=(
            replace(
                inputs.captures[0],
                body_sha256=hashlib.sha256(body).hexdigest(),
                byte_count=len(body),
            ),
            inputs.captures[1],
        ),
    )
    page = replace(page, body=body, realtime_start=date(1776, 7, 4), realtime_end=date.max)
    prior = normalize_fred((page,), replace(inputs, source_as_of_date=date(2026, 9, 11))).macros[0]
    latest = normalize_fred((page,), inputs).macros[0]
    assert prior.value == Decimal("4.25")
    assert latest.value is None and latest.value_state == "source_missing"
    assert latest.source_realtime_end == date.max
    assert latest.source_vintage_basis == "source_interval"


@pytest.mark.parametrize(
    "changes",
    [
        {"output_type": True},
        {"limit": True},
        {"offset": True},
        {"realtime_start": datetime(2026, 9, 12, tzinfo=UTC)},
    ],
)
def test_fred_request_types_cannot_coerce_booleans_or_timestamps(changes):
    inputs, page = fred_case()
    with pytest.raises(ValueError):
        normalize_fred((replace(page, **changes),), inputs)


def test_changed_fred_count_and_overlapping_revision_rows_block_publication():
    inputs, page = fred_case(("4.25", "4.5"))
    raw = json.loads(page.body)
    raw["observations"][1]["date"] = raw["observations"][0]["date"]
    body = json.dumps(raw).encode()
    inputs = replace(
        inputs,
        captures=(
            replace(
                inputs.captures[0],
                body_sha256=hashlib.sha256(body).hexdigest(),
                byte_count=len(body),
            ),
            inputs.captures[1],
        ),
    )
    with pytest.raises(ValueError):
        normalize_fred((replace(page, body=body),), inputs)


@pytest.mark.parametrize(
    "basis,as_of",
    [("invented", None), ("capture_only", date(2026, 9, 12)), ("source_supplied", None)],
)
def test_definition_vintage_is_not_guessed(basis, as_of):
    body = treasury_xml()
    inputs = market_input(body)
    definition = replace(
        inputs.series_definition, definition_as_of_basis=basis, definition_as_of_date=as_of
    )
    with pytest.raises(ValueError):
        normalize_treasury(body, replace(inputs, series_definition=definition))


@pytest.mark.parametrize("change", ["duplicate_identity", "entry_namespace"])
def test_treasury_identity_must_be_unambiguous(change):
    body = treasury_xml()
    if change == "duplicate_identity":
        body = body.replace(b"</title>", b"</title><title>OtherDataset</title>")
    else:
        body = body.replace(b"<entry>", b'<entry xmlns="https://wrong.invalid">')
    with pytest.raises(ValueError):
        normalize_treasury(body, market_input(body))


def test_price_history_cannot_mix_independent_adjustment_captures():
    body = price_body()
    inputs = market_input(body, kind="price")
    extra = replace(inputs.captures[0], id=UUID(int=99))
    with pytest.raises(ValueError):
        normalize_tiingo(body, replace(inputs, captures=inputs.captures + (extra,)))


def test_definition_reference_convention_must_be_supported():
    body = treasury_xml()
    inputs = market_input(body)
    definition = replace(inputs.series_definition, reference_date_convention="unreviewed")
    with pytest.raises(ValueError):
        normalize_treasury(body, replace(inputs, series_definition=definition))


def test_native_monthly_fred_reference_period_is_validated_without_guessing_release():
    inputs, page = fred_case()
    definition = replace(
        inputs.series_definition, frequency="monthly", reference_date_convention="period_start"
    )
    inputs = replace(inputs, series_definition=definition)
    row = normalize_fred((page,), inputs).macros[0]
    assert row.reference_date == date(2026, 9, 1)
    assert row.reference_end_date is row.source_published_date is None
    body = page.body.replace(b'"date": "2026-09-01"', b'"date": "2026-09-02"')
    capture = replace(
        inputs.captures[0], body_sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body)
    )
    with pytest.raises(ValueError):
        normalize_fred(
            (replace(page, body=body),), replace(inputs, captures=(capture, inputs.captures[1]))
        )


@pytest.mark.parametrize("kind", ["price", "fred"])
def test_api_error_document_is_not_an_empty_success(kind):
    body = b'{"error":"no data access"}'
    if kind == "price":
        with pytest.raises(ValueError):
            normalize_tiingo(body, market_input(body, kind="price"))
    else:
        inputs, page = fred_case()
        capture = replace(
            inputs.captures[0], body_sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body)
        )
        with pytest.raises(ValueError):
            normalize_fred(
                (replace(page, body=body),), replace(inputs, captures=(capture, inputs.captures[1]))
            )


def test_zero_and_negative_native_macro_values_are_not_missing_sentinels():
    for text in ("0.00", "-0.25"):
        body = treasury_xml(text)
        row = normalize_treasury(body, market_input(body)).macros[0]
        assert row.value == Decimal(text) and row.value_state == "observed"


def test_changed_fred_response_metadata_is_not_ignored():
    inputs, page = fred_case()
    for field, value in (
        ("units", "pch"),
        ("offset", 1),
        ("count", 2),
        ("output_type", True),
        ("realtime_end", "9999-12-31"),
    ):
        raw = json.loads(page.body)
        raw[field] = value
        body = json.dumps(raw).encode()
        capture = replace(
            inputs.captures[0], body_sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body)
        )
        with pytest.raises(ValueError):
            normalize_fred(
                (replace(page, body=body),), replace(inputs, captures=(capture, inputs.captures[1]))
            )


@pytest.mark.parametrize(
    "change,prefix", [({"high": 99}, ""), ({"low": 103}, ""), ({"adjHigh": 49}, "adj_")]
)
def test_ohlc_inconsistency_blocks_every_field_in_only_the_affected_group(change, prefix):
    body = price_body(**change)
    result = normalize_tiingo(body, market_input(body, kind="price"))
    flags = [f for f in result.flags if f.rule_key == "ohlc_inconsistent"]
    assert {f.field_key for f in flags} == {
        prefix + key for key in ("open", "high", "low", "close")
    }
    assert all(f.severity == "blocking" for f in flags)
    assert result.prices[0].volume == Decimal("1000")
    assert result.prices[0].adj_volume == Decimal("2000")


def test_equivalent_datetime_offsets_preserve_market_hashes_and_observation_ids():
    body = price_body()
    inputs = market_input(body, kind="price")
    original = normalize_tiingo(body, inputs)
    local = ZoneInfo("America/Los_Angeles")
    replay_inputs = replace(
        inputs,
        captures=tuple(
            replace(
                c,
                fetched_at=c.fetched_at.astimezone(local),
                completed_at=c.completed_at.astimezone(local),
            )
            for c in inputs.captures
        ),
        quote_binding=replace(
            inputs.quote_binding, reviewed_at=inputs.quote_binding.reviewed_at.astimezone(local)
        ),
    )
    replay = normalize_tiingo(body, replay_inputs)
    assert replay.input_manifest_hash == original.input_manifest_hash
    assert replay.output_manifest_hash == original.output_manifest_hash
    assert replay.prices == original.prices
    assert replay.flags == original.flags


def test_unavailable_market_bundle_has_no_fabricated_observations():
    from equity_ingest.market_normalize import unavailable_market_bundle

    body = treasury_xml()
    inputs = market_input(body)
    inputs = replace(inputs, captures=(inputs.captures[1],), attempt_ids=(UUID(int=91),))
    bundle = unavailable_market_bundle(inputs, "source_request_failed")
    assert not bundle.prices and not bundle.macros
    assert bundle.coverage_state == "unavailable"
    assert any(
        f.rule_key == "source_request_failed" and f.severity == "blocking" for f in bundle.flags
    )
    assert bundle.inputs.attempt_ids == (UUID(int=91),)
