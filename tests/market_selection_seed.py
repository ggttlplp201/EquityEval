"""Fictional market evidence published through the real leased S4 boundary."""

import hashlib
import json
from datetime import UTC, date, datetime
from uuid import uuid4

from equity_schema.workflow import (
    MarketDataRequestPlan,
    RequestOptions,
    add_watchlist_stock,
    claim_next,
    create_workspace_watchlist,
    start_stage,
)
from psycopg.types.json import Jsonb

from tests.evidence_seed import insert, seed_evidence

FIELDS = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adj_open",
    "adj_high",
    "adj_low",
    "adj_close",
    "adj_volume",
    "div_cash",
    "split_factor",
)
DAY = date(2025, 1, 2)


def capture(db_admin, ids, when, fetched_at=None):
    capture_id = uuid4()
    insert(
        db_admin,
        "source_captures",
        id=capture_id,
        source_id=ids["source"],
        source_object_key="fictional-market",
        request_url="https://example.invalid/market",
        request_params_hash="a" * 64,
        requested_at=fetched_at or when,
        fetched_at=fetched_at or when,
        completed_at=when,
        http_status=200,
        body_sha256=capture_id.hex * 2,
        blob_key="test-only/fictional-market.json.gz",
        byte_count=1,
        content_type="application/json",
        terms_review_reference="test-only",
    )
    return capture_id


def prepare_market(
    db_admin,
    db,
    *,
    ids=None,
    kind="price",
    day=DAY,
    value="100.25",
    captured_at=datetime(2025, 1, 3, tzinfo=UTC),
    metadata_at=None,
    fetched_at=None,
    source_as_of_date=None,
    omit=False,
    observation_changes=None,
    definition_changes=None,
    coverage="complete",
    flags=(),
    requested_start=None,
    requested_end=None,
):
    """Return (identity IDs, lease, stage, mutable bundle) for boundary assertions."""
    ids = ids or seed_evidence(db_admin, captured_at="2025-01-01T00:00:00Z")
    observation_capture = capture(db_admin, ids, captured_at, fetched_at)
    metadata_capture = capture(db_admin, ids, metadata_at or captured_at)
    policy = db_admin.execute(
        "SELECT policy_revision_id FROM capture_policy_links WHERE capture_id=%s",
        (observation_capture,),
    ).fetchone()["policy_revision_id"]
    start, end = requested_start or day, requested_end or day
    if kind == "price":
        plan = MarketDataRequestPlan(
            "s4-market-data-v1", price_source_id=ids["source"], price_start=start, price_end=end
        )
    else:
        plan = MarketDataRequestPlan(
            "s4-market-data-v1",
            macro_source_id=ids["source"],
            macro_series_keys=("TEST",),
            macro_start=start,
            macro_end=end,
            macro_source_as_of_date=source_as_of_date,
        )
    workspace = create_workspace_watchlist(db, name="Fictional market fixture")
    add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key=str(uuid4()),
        options=RequestOptions(market_plan=plan),
    )
    lease = claim_next(db, worker_id="market-fixture-" + uuid4().hex, lease_seconds=300)
    assert lease
    stage = start_stage(
        db,
        lease,
        stage_key="price_normalization"
        if kind == "price"
        else "macro_normalization_0000000000000000",
    )
    batch_id, definition_id, binding_id, observation_id = (uuid4() for _ in range(4))
    digest = hashlib.sha256(str(batch_id).encode()).hexdigest()
    batch = dict(
        id=batch_id,
        data_kind=kind,
        source_id=ids["source"],
        policy_revision_id=policy,
        quote_identifier_id=ids["quote"] if kind == "price" else None,
        security_id=ids["security"] if kind == "price" else None,
        quote_binding_id=binding_id if kind == "price" else None,
        source_series_key="TEST" if kind == "macro" else None,
        series_definition_id=definition_id if kind == "macro" else None,
        requested_start=start,
        requested_end=end,
        source_vintage_mode="source_as_of_date"
        if source_as_of_date
        else "current_provider_history",
        source_as_of_date=source_as_of_date,
        retrieval_cutoff=None,
        parser_revision="parser-v1",
        normalizer_revision="normalizer-v1",
        selection_policy_revision="selection-v1",
        input_manifest_hash=digest,
        output_manifest_hash=digest,
        manifest_blob_key="test-only/manifest.json.gz",
        manifest_body_sha256=digest,
        manifest_byte_count=1,
        coverage_state=coverage,
    )
    bundle = dict(
        batch=batch,
        inputs=[
            dict(id=uuid4(), capture_id=observation_capture, role="observations"),
            dict(
                id=uuid4(),
                capture_id=metadata_capture,
                role="quote_identity" if kind == "price" else "series_definition",
            ),
        ],
        flags=list(flags),
        prices=[],
        macros=[],
        bindings=[],
        definitions=[],
    )
    observation = dict(
        id=observation_id,
        source_capture_id=observation_capture,
        source_locator="/0",
        source_date_text=day.isoformat(),
        publication_precision="unknown",
        source_published_date=None,
        source_published_at=None,
        transform_revision="normalizer-v1",
    )
    _records(
        bundle,
        observation,
        kind,
        ids,
        day,
        value,
        metadata_capture,
        metadata_at or captured_at,
        source_as_of_date,
        binding_id,
        definition_id,
        digest,
        definition_changes,
    )
    observation.update(observation_changes or {})
    if not omit:
        bundle["prices" if kind == "price" else "macros"] = [observation]
    else:
        bundle["flags"].append(quality_flag("response_omitted_date", captured_at))
    return ids, lease, stage, bundle


def _records(
    bundle,
    observation,
    kind,
    ids,
    day,
    value,
    metadata_capture,
    metadata_at,
    source_as_of_date,
    binding_id,
    definition_id,
    digest,
    definition_changes,
):
    if kind == "price":
        bundle["bindings"] = [
            dict(
                id=binding_id,
                source_id=ids["source"],
                quote_identifier_id=ids["quote"],
                security_id=ids["security"],
                provider_symbol="TEST",
                valid_from=date(2020, 1, 1),
                identity_capture_id=metadata_capture,
                source_locator="/symbol",
                identity_review_revision="fixture-v1",
                reviewed_at=metadata_at,
                reviewed_by="fictional-fixture",
                content_sha256=digest,
            )
        ]
        observation.update(
            session_date=day,
            quote_binding_id=binding_id,
            quote_identifier_id=ids["quote"],
            security_id=ids["security"],
            quote_currency="USD",
            dividend_currency="USD",
            session_basis="provider_daily_label",
            session_timezone="America/New_York",
            adjustment_basis="split_and_dividend",
            adjustment_vintage_basis="capture_only",
        )
        for field in FIELDS:
            number = (
                value
                if field in ("open", "high", "low", "close")
                else ("1" if field == "split_factor" else ("0" if field == "div_cash" else "50"))
            )
            observation.update(
                {field: number, field + "_state": "observed", field + "_text": number}
            )
    else:
        definition = dict(
            id=definition_id,
            source_id=ids["source"],
            source_series_key="TEST",
            metadata_capture_id=metadata_capture,
            source_locator="/series/0",
            content_sha256=digest,
            definition_revision="fixture-v1",
            title="Fictional annual rate",
            units_text="Percent",
            unit_code="percent_per_year",
            unit_multiplier="1",
            frequency="daily",
            seasonal_adjustment="not_applicable",
            geography="US",
            reference_date_convention="provider_observation_date",
            upstream_source_name="Fictional",
            upstream_rights_reference="fictional-only",
            definition_as_of_basis="capture_only",
        )
        definition.update(definition_changes or {})
        bundle["definitions"] = [definition]
        observation.update(
            reference_date=day,
            series_definition_id=definition_id,
            value=value,
            value_state="observed",
            original_value_text=value,
            source_vintage_basis="requested_as_of" if source_as_of_date else "current_only",
            requested_source_as_of=source_as_of_date,
        )


def quality_flag(rule, when=datetime(2025, 1, 3, tzinfo=UTC), **changes):
    result = dict(
        id=uuid4(),
        rule_key=rule,
        severity="blocking",
        message="Fictional test flag",
        raised_at=when,
    )
    result.update(changes)
    return result


def publish_prepared(db, prepared):
    ids, lease, stage, bundle = prepared
    payload = json.loads(json.dumps(bundle, default=str))
    db.execute("SELECT market_publish(%s,%s,%s)", (Jsonb(lease.as_json()), stage, Jsonb(payload)))
    return ids, bundle


def seed_market(db_admin, db, **kwargs):
    return publish_prepared(db, prepare_market(db_admin, db, **kwargs))
