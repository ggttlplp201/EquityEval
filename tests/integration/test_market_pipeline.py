"""W1 market stages with fictional HTTP, a real archive and isolated Timescale storage."""

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import RawRecord
from equity_ingest.market_pipeline import MarketReview, run_market_stages
from equity_ingest.market_sources import MarketSource
from equity_ingest.provider_contracts import ProviderDescriptor, ProviderKind, TreasuryResource
from equity_ingest.provider_store import DatabaseProviderStore
from equity_ingest.provider_transport import ProviderTransport
from equity_schema.market_selection import select_macro
from equity_schema.workflow import (
    MarketDataRequestPlan,
    RequestOptions,
    add_watchlist_stock,
    claim_next,
    create_workspace_watchlist,
    rerun_analysis,
)

from tests.evidence_seed import insert, seed_evidence
from tests.test_ingest_transport import Clock, Limiter, response
from tests.test_market_normalize import market_input, treasury_xml

pytestmark = pytest.mark.integration


def setup_market(
    db_admin,
    db,
    tmp_path,
    *,
    cutoff=None,
    include_price=False,
    months=False,
    series=("BC_10YEAR",),
):
    ids = seed_evidence(db_admin)
    ids["source"] = uuid4()
    insert(
        db_admin,
        "sources",
        id=ids["source"],
        source_key=str(ids["source"]),
        name="Fictional Treasury fixture",
        base_url="https://home.treasury.gov",
        terms_review_reference="test-only",
        content_scope="fictional only",
    )
    insert(
        db_admin,
        "source_policy_revisions",
        id=uuid4(),
        source_id=ids["source"],
        review_key="test-only",
        licence_label="Fictional test evidence only",
        content_scope="Fixture",
        redistribution_status="unknown",
        permitted_use="Tests only",
        attribution_requirements="Not a production policy",
        terms_urls=["https://example.invalid/test-policy"],
        reviewed_at=datetime(2026, 9, 12, tzinfo=UTC),
        reviewed_by="test-fixture",
        review_artifact_reference="tests/integration/test_market_pipeline.py",
        review_artifact_sha256="a" * 64,
    )
    archive = LocalArchive(tmp_path / "archive")
    row = db.execute(
        "SELECT s.source_key,s.name,p.* FROM sources s "
        "JOIN source_policy_revisions p ON p.source_id=s.id WHERE s.id=%s",
        (ids["source"],),
    ).fetchone()
    descriptor = ProviderDescriptor(
        ids["source"],
        row["source_key"],
        row["name"],
        row["id"],
        row["review_key"],
        row["licence_label"],
        row["redistribution_status"],
        ProviderKind.TREASURY,
        timedelta(hours=1),
    )
    template = market_input(treasury_xml()).series_definition
    metadata_id = uuid4()
    when = datetime(2026, 9, 12, tzinfo=UTC)
    body = b"Fictional reviewed Treasury definition; native percent, no release timestamp"
    archived = archive.write(
        [body],
        source_key=descriptor.source_key,
        source_object_key="reviewed_definition",
        params_hash="a" * 64,
        capture_id=metadata_id,
        retrieved_at=when,
        max_bytes=len(body),
    )
    metadata = RawRecord(
        metadata_id,
        ids["source"],
        "reviewed_definition",
        "https://home.treasury.gov/fictional-test-definition",
        "a" * 64,
        when,
        when,
        when,
        200,
        archived.body_sha256,
        archived.byte_count,
        archived.blob_key,
        "text/plain",
        descriptor.policy_revision_id,
        descriptor.terms_review_reference,
    )
    insert(
        db_admin,
        "source_captures",
        id=metadata_id,
        source_id=metadata.source_id,
        source_object_key=metadata.source_object_key,
        request_url=metadata.request_url,
        request_params_hash=metadata.request_params_hash,
        requested_at=when,
        fetched_at=when,
        completed_at=when,
        http_status=200,
        body_sha256=archived.body_sha256,
        blob_key=archived.blob_key,
        byte_count=archived.byte_count,
        content_type="text/plain",
        terms_review_reference=metadata.terms_review_reference,
    )
    definition = replace(
        template,
        id=uuid4(),
        source_id=ids["source"],
        metadata_capture_id=metadata_id,
    )
    review = MarketReview(
        definitions=tuple(replace(definition, id=uuid4(), source_series_key=key) for key in series),
        evidence=(metadata,),
    )
    plan = MarketDataRequestPlan(
        "s4-market-data-v1",
        price_source_id=ids["source"] if include_price else None,
        price_start=date(2026, 9, 1) if include_price else None,
        price_end=date(2026, 9, 30) if include_price else None,
        macro_source_id=ids["source"],
        macro_series_keys=series,
        macro_start=date(2026, 8, 31) if months else date(2026, 9, 1),
        macro_end=date(2026, 9, 1) if months else date(2026, 9, 30),
    )
    options = RequestOptions(market_plan=plan, retrieval_vintage=cutoff)
    workspace = create_workspace_watchlist(db, name="Fictional market pipeline")
    request = add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key=uuid4().hex,
        options=options,
    )
    lease = claim_next(db, worker_id=uuid4().hex, lease_seconds=300)
    assert lease
    return ids, archive, descriptor, review, workspace, request, lease, options


def source_for(db, archive, descriptor, handler):
    clock = Clock()
    clock.now = lambda: datetime.now(UTC)
    return MarketSource(
        ProviderTransport(
            descriptor,
            archive,
            Limiter(clock),
            DatabaseProviderStore(db, descriptor),
            httpx.Client(transport=httpx.MockTransport(handler)),
            now=clock.now,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )
    )


def observation_records(db, source):
    rows = db.execute(
        "SELECT c.*,p.policy_revision_id FROM source_captures c "
        "JOIN capture_policy_links p ON p.capture_id=c.id "
        "WHERE c.source_id=%s AND c.source_object_key=%s ORDER BY c.completed_at,c.id",
        (source, TreasuryResource("202609").object_key),
    ).fetchall()
    return tuple(
        RawRecord(
            row["id"],
            row["source_id"],
            row["source_object_key"],
            row["request_url"],
            row["request_params_hash"],
            row["requested_at"],
            row["fetched_at"],
            row["completed_at"],
            row["http_status"],
            row["body_sha256"],
            row["byte_count"],
            row["blob_key"],
            row["content_type"],
            row["policy_revision_id"],
            row["terms_review_reference"],
        )
        for row in rows
    )


def test_treasury_end_to_end_and_explicit_rerun_reuses_batch(db_admin, db, tmp_path):
    ids, archive, descriptor, review, workspace, request, lease, options = setup_market(
        db_admin, db, tmp_path
    )
    calls = []

    def handler(http_request):
        calls.append(http_request)
        assert http_request.url.params["field_tdr_date_value_month"] == "202609"
        return response(body=treasury_xml("4.2500"))

    source = source_for(db, archive, descriptor, handler)
    result = run_market_stages(db, lease, archive, {ids["source"]: source}, review)
    assert len(result.publications) == 1 and len(calls) == 1
    selected = select_macro(db, ids["source"], "BC_10YEAR", date(2026, 9, 10))
    assert selected.batch_id == result.publications[0].batch_id
    assert selected.value == Decimal("4.2500") and selected.unit_code == "percent"
    assert selected.publication_precision == "unknown" and not selected.usable
    assert "incomplete_coverage" in selected.flags
    assert selected.provenance and selected.manifest_blob_key
    records = observation_records(db, ids["source"])
    assert len(records) == 1 and source.read_verified(records[0]) == treasury_xml("4.2500")
    assert db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"] == 1
    rerun = rerun_analysis(
        db,
        workspace_id=workspace.workspace_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key=uuid4().hex,
        parent_request_id=request.request_id,
        options=options,
    )
    second_lease = claim_next(db, worker_id=uuid4().hex, lease_seconds=300)
    assert second_lease.request_id == rerun.request_id
    again = run_market_stages(
        db, second_lease, archive, {ids["source"]: source}, review, replay_records=records
    )
    assert len(calls) == 1 and len(again.publications) == 1
    previous_manifest = json.loads(archive.read(result.publications[0].manifest))
    replay_manifest = json.loads(archive.read(again.publications[0].manifest))
    assert (
        previous_manifest["normalization"]["inputs"] == replay_manifest["normalization"]["inputs"]
    )
    assert again.publications[0].reused
    assert again.publications[0].batch_id == result.publications[0].batch_id
    assert db.execute("SELECT count(*) AS n FROM market_data_batches").fetchone()["n"] == 1
    assert db.execute("SELECT count(*) AS n FROM analysis_requests").fetchone()["n"] == 2


def test_historical_cutoff_requires_replay_and_never_dispatches(db_admin, db, tmp_path):
    ids, archive, descriptor, review, _, _, lease, _ = setup_market(
        db_admin, db, tmp_path, cutoff=datetime(2026, 9, 13, tzinfo=UTC)
    )
    source = source_for(
        db, archive, descriptor, lambda _: pytest.fail("Historical request made HTTP")
    )
    with pytest.raises(ValueError, match="explicit replay"):
        run_market_stages(db, lease, archive, {ids["source"]: source}, review)
    result = run_market_stages(
        db, lease, archive, {ids["source"]: source}, review, replay_records=()
    )
    assert not result.publications and "capture_unavailable" in result.gaps
    assert db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"] == 0


def test_unavailable_price_provider_does_not_prevent_macro_publication(db_admin, db, tmp_path):
    ids, archive, descriptor, review, _, _, lease, _ = setup_market(
        db_admin, db, tmp_path, include_price=True
    )
    source = source_for(db, archive, descriptor, lambda _: response(body=treasury_xml()))
    result = run_market_stages(db, lease, archive, {ids["source"]: source}, review)
    assert "price_provider_unavailable" in result.gaps and len(result.publications) == 1
    states = db.execute("SELECT stage_key,state FROM analysis_stage_attempts").fetchall()
    assert {r["state"] for r in states if r["stage_key"] == "price_normalization"} == {"blocked"}
    assert result.state == "completed_with_gaps"


def test_month_windows_are_persisted_separately_and_metadata_is_required(db_admin, db, tmp_path):
    ids, archive, descriptor, review, _, _, lease, _ = setup_market(
        db_admin, db, tmp_path, months=True
    )
    months = []

    def handler(request):
        month = request.url.params["field_tdr_date_value_month"]
        months.append(month)
        day = "2026-08-31T00:00:00" if month == "202608" else "2026-09-01T00:00:00"
        return response(body=treasury_xml(date_text=day))

    source = source_for(db, archive, descriptor, handler)
    result = run_market_stages(db, lease, archive, {ids["source"]: source}, review)
    assert months == ["202608", "202609"] and len(result.publications) == 2
    windows = db.execute(
        "SELECT requested_start,requested_end FROM market_data_batches ORDER BY requested_start"
    ).fetchall()
    assert [(r["requested_start"], r["requested_end"]) for r in windows] == [
        (date(2026, 8, 31), date(2026, 8, 31)),
        (date(2026, 9, 1), date(2026, 9, 1)),
    ]


def test_missing_definition_evidence_blocks_before_http(db_admin, db, tmp_path):
    ids, archive, descriptor, review, _, _, lease, _ = setup_market(db_admin, db, tmp_path)
    source = source_for(db, archive, descriptor, lambda _: pytest.fail("Unreviewed source fetched"))
    result = run_market_stages(
        db, lease, archive, {ids["source"]: source}, replace(review, evidence=())
    )
    assert not result.publications and "reviewed_market_evidence_required" in result.gaps


def test_replay_capture_after_cutoff_is_a_source_gap_without_live_fallback(db_admin, db, tmp_path):
    ids, archive, descriptor, review, workspace, request, lease, options = setup_market(
        db_admin, db, tmp_path
    )
    calls = []

    def handler(request):
        calls.append(request)
        return response(body=treasury_xml())

    source = source_for(db, archive, descriptor, handler)
    first = run_market_stages(db, lease, archive, {ids["source"]: source}, review)
    assert len(first.publications) == 1
    records = observation_records(db, ids["source"])
    rerun_analysis(
        db,
        workspace_id=workspace.workspace_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key=uuid4().hex,
        parent_request_id=request.request_id,
        options=replace(options, retrieval_vintage=records[0].completed_at - timedelta(seconds=1)),
    )
    historical = claim_next(db, worker_id=uuid4().hex, lease_seconds=300)
    result = run_market_stages(
        db, historical, archive, {ids["source"]: source}, review, replay_records=records
    )
    assert not result.publications and result.gaps and len(calls) == 1
    assert result.state == "completed_with_gaps"
    assert (
        db.execute(
            "SELECT count(*) AS n FROM analysis_stage_attempts "
            "WHERE execution_id=%s AND state='running'",
            (historical.execution_id,),
        ).fetchone()["n"]
        == 0
    )


def test_failed_sec_identity_does_not_prevent_macro_in_combined_execution(db_admin, db, tmp_path):
    from unittest.mock import Mock

    from equity_ingest.analysis_pipeline import run_analysis_stages
    from equity_ingest.pipeline import SourcePlan

    ids, archive, descriptor, review, _, _, lease, _ = setup_market(db_admin, db, tmp_path)
    source = source_for(db, archive, descriptor, lambda _: response(body=treasury_xml()))
    unresolved_sec = Mock()
    unresolved_sec.fetch.side_effect = AssertionError("Unresolved SEC issuer must not dispatch")
    sec_plan = SourcePlan(ids["issuer"], "1234", date(2024, 1, 1), date(2026, 9, 30))
    result = run_analysis_stages(
        db,
        lease,
        unresolved_sec,
        archive,
        sec_plan,
        lambda _: None,
        {ids["source"]: source},
        review,
    )
    assert result.sec.state == "failed" and len(result.market.publications) == 1
    assert result.state == "completed_with_gaps" and "sec_source_ValueError" in result.gaps
    assert "valuation_milestones_pending" in result.gaps
    assert (
        db.execute(
            "SELECT state FROM analysis_stage_attempts WHERE stage_key='valuation'"
        ).fetchone()["state"]
        == "unsupported"
    )
    unresolved_sec.fetch.assert_not_called()


@pytest.mark.parametrize(
    "status,body,attempt_count",
    [(503, b"temporarily unavailable", 3), (200, b"<not-a-treasury-feed/>", 1)],
)
def test_newer_failed_fetch_supersedes_old_value_without_erasing_old_batch(
    db_admin, db, tmp_path, status, body, attempt_count
):
    ids, archive, descriptor, review, workspace, request, lease, options = setup_market(
        db_admin, db, tmp_path
    )
    source = source_for(db, archive, descriptor, lambda _: response(body=treasury_xml()))
    first = run_market_stages(db, lease, archive, {ids["source"]: source}, review)
    assert len(first.publications) == 1
    rerun_analysis(
        db,
        workspace_id=workspace.workspace_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key=uuid4().hex,
        parent_request_id=request.request_id,
        options=options,
    )
    rerun = claim_next(db, worker_id=uuid4().hex, lease_seconds=300)
    failing_source = source_for(db, archive, descriptor, lambda _: response(status, body))
    latest = run_market_stages(db, rerun, archive, {ids["source"]: failing_source}, review)
    assert len(latest.publications) == 1
    selected = select_macro(db, ids["source"], "BC_10YEAR", date(2026, 9, 10))
    assert selected.batch_id == latest.publications[0].batch_id
    assert selected.batch_id != first.publications[0].batch_id
    assert selected.value is None and not selected.usable
    assert selected.coverage_state == "unavailable" and selected.quality_flags
    assert len(selected.attempt_ids) == attempt_count
    old = select_macro(
        db,
        ids["source"],
        "BC_10YEAR",
        date(2026, 9, 10),
        batch_id=first.publications[0].batch_id,
    )
    assert old.value == Decimal("4.2500") and "explicit_batch" in old.flags


def test_retry_error_and_success_attempts_remain_in_published_provenance(db_admin, db, tmp_path):
    ids, archive, descriptor, review, _, _, lease, _ = setup_market(db_admin, db, tmp_path)
    calls = []

    def handler(request):
        calls.append(request)
        return (
            response(500, b"fictional server error")
            if len(calls) == 1
            else response(body=treasury_xml())
        )

    source = source_for(db, archive, descriptor, handler)
    result = run_market_stages(db, lease, archive, {ids["source"]: source}, review)
    assert len(calls) == 2 and len(result.publications) == 1
    selected = select_macro(db, ids["source"], "BC_10YEAR", date(2026, 9, 10))
    assert selected.value == Decimal("4.2500")
    assert len(selected.attempt_ids) == 2
    attempts = db.execute(
        "SELECT id,http_status FROM source_fetch_attempts ORDER BY prepared_at"
    ).fetchall()
    assert set(selected.attempt_ids) == {r["id"] for r in attempts}
    assert [r["http_status"] for r in attempts] == [500, 200]
    captures = observation_records(db, ids["source"])
    assert len(captures) == 2
    assert source.read_verified(captures[0]) == b"fictional server error"


def test_two_treasury_maturities_share_one_capture_and_keep_separate_native_values(
    db_admin, db, tmp_path
):
    ids, archive, descriptor, review, _, _, lease, _ = setup_market(
        db_admin, db, tmp_path, series=("BC_2YEAR", "BC_10YEAR")
    )
    calls = []

    def handler(request):
        calls.append(request)
        return response(
            body=treasury_xml("4.25", extra='<d:BC_2YEAR m:type="Edm.Double">3.75</d:BC_2YEAR>')
        )

    source = source_for(db, archive, descriptor, handler)
    result = run_market_stages(db, lease, archive, {ids["source"]: source}, review)
    assert len(calls) == 1 and len(result.publications) == 2
    assert select_macro(db, ids["source"], "BC_2YEAR", date(2026, 9, 10)).value == Decimal("3.75")
    assert select_macro(db, ids["source"], "BC_10YEAR", date(2026, 9, 10)).value == Decimal("4.25")
    assert len(observation_records(db, ids["source"])) == 1


def test_legacy_request_exposes_market_plan_gap_without_inventing_provider_intent(
    db_admin, db, tmp_path
):
    ids = seed_evidence(db_admin)
    workspace = create_workspace_watchlist(db, name="Legacy SEC-only request")
    add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key=uuid4().hex,
    )
    lease = claim_next(db, worker_id=uuid4().hex, lease_seconds=300)
    result = run_market_stages(db, lease, LocalArchive(tmp_path / "archive"), {}, MarketReview())
    assert not result.publications and "immutable_market_plan_missing" in result.gaps
    stage = db.execute(
        "SELECT state,error_code FROM analysis_stage_attempts WHERE stage_key='market_sources'"
    ).fetchone()
    assert stage["state"] == "unsupported"
    assert stage["error_code"] == "immutable_market_plan_missing"
    assert db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"] == 0
