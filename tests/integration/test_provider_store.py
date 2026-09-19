"""Fictional provider requests through real immutable W1 and durable quota guards."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from equity_ingest.provider_contracts import (
    PROVIDER_WIRE_LIMIT,
    FredResource,
    PriceResource,
    ProviderDescriptor,
    ProviderFetchRequest,
    ProviderKind,
    ProviderQuota,
    TreasuryResource,
)
from equity_ingest.provider_store import DatabaseProviderStore, ProviderBudgetExceeded
from equity_schema.market_data import disable_policy
from equity_schema.workflow import (
    LeaseLost,
    MarketDataRequestPlan,
    RequestOptions,
    add_watchlist_stock,
    cancel_request,
    claim_next,
    create_workspace_watchlist,
    finish_stage,
    start_stage,
)
from psycopg.pq import TransactionStatus

from tests.evidence_seed import insert, seed_evidence

pytestmark = pytest.mark.integration


@pytest.fixture
def provider_setup(db_admin, db):
    ids = seed_evidence(db_admin)
    original_policy = db_admin.execute(
        "SELECT p.* FROM source_policy_revisions p JOIN capture_policy_links l "
        "ON l.policy_revision_id=p.id WHERE l.capture_id=%s",
        (ids["capture"],),
    ).fetchone()
    sources = {}

    def setup(kind=ProviderKind.TREASURY, *, quota=None, as_of=None, symbol="TEST", base_url=None):
        source_url = (
            base_url
            or {
                ProviderKind.TREASURY: "https://home.treasury.gov",
                ProviderKind.FRED: "https://api.stlouisfed.org",
                ProviderKind.TIINGO: "https://api.tiingo.com",
            }[kind]
        )
        if (kind, source_url) not in sources:
            source_id, policy = uuid4(), uuid4()
            insert(
                db_admin,
                "sources",
                id=source_id,
                source_key=source_id.hex,
                name="Fictional provider identity",
                base_url=source_url,
                terms_review_reference="test-only",
                content_scope="fictional",
            )
            insert(
                db_admin,
                "source_policy_revisions",
                **(dict(original_policy) | {"id": policy, "source_id": source_id}),
            )
            sources[(kind, source_url)] = source_id, policy
        source_id, policy = sources[(kind, source_url)]
        source = db.execute("SELECT * FROM sources WHERE id=%s", (source_id,)).fetchone()
        descriptor = ProviderDescriptor(
            source_id,
            source["source_key"],
            source["name"],
            policy,
            "test-only",
            "Fictional test evidence only",
            "unknown",
            kind,
            timedelta(minutes=15),
            quota=quota if quota is not None else ProviderQuota(100, 1000, 10000, 100, 10**13),
        )
        plan = MarketDataRequestPlan(
            "s4-market-data-v1",
            price_source_id=source_id if kind == ProviderKind.TIINGO else None,
            price_start=date(2025, 1, 1) if kind == ProviderKind.TIINGO else None,
            price_end=date(2025, 1, 2) if kind == ProviderKind.TIINGO else None,
            macro_source_id=source_id if kind != ProviderKind.TIINGO else None,
            macro_series_keys=("BC_10YEAR",)
            if kind == ProviderKind.TREASURY
            else (("DGS10",) if kind == ProviderKind.FRED else ()),
            macro_start=date(2025, 1, 1) if kind != ProviderKind.TIINGO else None,
            macro_end=date(2025, 1, 2) if kind != ProviderKind.TIINGO else None,
            macro_source_as_of_date=as_of,
        )
        workspace = create_workspace_watchlist(db, name="Provider store fixture")
        queued = add_watchlist_stock(
            db,
            watchlist_id=workspace.watchlist_id,
            security_id=ids["security"],
            quote_identifier_id=ids["quote"],
            idempotency_key=uuid4().hex,
            options=RequestOptions(market_plan=plan),
        )
        lease = claim_next(db, worker_id=uuid4().hex, lease_seconds=300)
        assert lease is not None and lease.request_id == queued.request_id
        stage = start_stage(db, lease, stage_key="provider_fetch")
        if kind == ProviderKind.TREASURY:
            resource = TreasuryResource("202501")
        elif kind == ProviderKind.FRED:
            requested_at = db.execute(
                "SELECT requested_at FROM analysis_requests WHERE id=%s",
                (queued.request_id,),
            ).fetchone()["requested_at"]
            resource = FredResource(
                "DGS10",
                date(2025, 1, 1),
                date(2025, 1, 2),
                as_of or requested_at.astimezone(UTC).date(),
            )
        else:
            insert(
                db_admin,
                "provider_quote_bindings",
                id=uuid4(),
                source_id=source_id,
                quote_identifier_id=ids["quote"],
                security_id=ids["security"],
                provider_symbol=symbol,
                valid_from=date(2020, 1, 1),
                identity_capture_id=ids["capture"],
                source_locator="fictional/identity",
                identity_review_revision="test-only",
                reviewed_at=datetime.now(UTC),
                reviewed_by="test",
                content_sha256=uuid4().hex * 2,
            )
            resource = PriceResource(
                ids["quote"], ids["security"], symbol, date(2025, 1, 1), date(2025, 1, 2)
            )
        return DatabaseProviderStore(db, descriptor), ProviderFetchRequest(
            uuid4(), resource, lease, stage
        )

    return setup


def prepare(store, request, sequence=1):
    return store.prepare(request, sequence, request.resource.url, None)


def test_prepare_dispatch_cancel_are_committed_and_scoped(db, provider_setup):
    store, request = provider_setup()
    store.guard(request)
    attempt = prepare(store, request)
    assert db.info.transaction_status == TransactionStatus.IDLE
    assert prepare(store, request) == attempt
    store.dispatched(request, attempt, datetime.now(UTC))
    store.finish(request, attempt, "cancelled", datetime.now(UTC), failure="fixture_cancel")
    assert (
        db.execute("SELECT state FROM source_fetch_attempts WHERE id=%s", (attempt,)).fetchone()[
            "state"
        ]
        == "cancelled"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_key", "forged"),
        ("name", "Forged provider"),
        ("licence", "Made up public domain"),
        ("terms_review_reference", "not-reviewed"),
        ("redistribution_status", "allowed"),
    ],
)
def test_descriptor_claims_cannot_diverge_from_policy(provider_setup, field, value):
    store, request = provider_setup()
    store.descriptor = replace(store.descriptor, **{field: value})
    with pytest.raises(PermissionError, match="descriptor"):
        prepare(store, request)


@pytest.mark.parametrize("kind", list(ProviderKind))
def test_request_resource_must_match_immutable_plan(provider_setup, kind):
    store, request = provider_setup(kind)
    resource = request.resource
    if kind == ProviderKind.TREASURY:
        resource = TreasuryResource("202502")
    else:
        resource = replace(resource, end=date(2025, 1, 3))
    with pytest.raises(PermissionError, match="plan"):
        prepare(store, replace(request, resource=resource))


def test_price_requires_reviewed_full_window_binding(provider_setup):
    store, request = provider_setup(ProviderKind.TIINGO)
    with pytest.raises(PermissionError, match="binding"):
        prepare(
            store, replace(request, resource=replace(request.resource, provider_symbol="OTHER"))
        )
    with pytest.raises(PermissionError, match="plan"):
        prepare(store, replace(request, resource=replace(request.resource, security_id=uuid4())))


@pytest.mark.parametrize("as_of", [None, date(2025, 2, 1)])
def test_fred_pins_wire_realtime_day_to_intent(provider_setup, as_of):
    store, request = provider_setup(ProviderKind.FRED, as_of=as_of)
    store.guard(request)
    with pytest.raises(PermissionError, match="vintage"):
        prepare(
            store,
            replace(
                request,
                resource=replace(
                    request.resource, source_as_of=request.resource.source_as_of - timedelta(days=1)
                ),
            ),
        )


def test_rejects_structural_resource_spoof_and_arbitrary_url(provider_setup):
    store, request = provider_setup()

    class Spoof:
        provider = ProviderKind.TREASURY
        object_key = "daily_treasury_yield_curve"
        url = "https://example.invalid/stolen"
        params_hash = "a" * 64
        params = ()

    with pytest.raises(PermissionError, match="resource"):
        prepare(store, replace(request, resource=Spoof()))
    with pytest.raises(PermissionError, match="URL"):
        store.prepare(request, 1, "https://example.invalid/stolen", None)


def test_disabled_policy_prevents_dispatch_but_can_close_reserved_attempt(
    db_admin, db, provider_setup
):
    store, request = provider_setup()
    attempt = prepare(store, request)
    disable_policy(
        db_admin, store.descriptor.policy_revision_id, actor="test", reason="operational stop"
    )
    with pytest.raises(PermissionError):
        store.dispatched(request, attempt, datetime.now(UTC))
    store.finish(request, attempt, "cancelled", datetime.now(UTC), failure="policy_disabled")
    assert (
        db.execute("SELECT state FROM source_fetch_attempts WHERE id=%s", (attempt,)).fetchone()[
            "state"
        ]
        == "cancelled"
    )


def test_cancelled_request_cannot_prepare_or_dispatch(db, provider_setup):
    store, request = provider_setup()
    attempt = prepare(store, request)
    cancel_request(db, request_id=request.lease.request_id)
    for action in (
        lambda: prepare(store, replace(request, logical_fetch_id=uuid4())),
        lambda: store.dispatched(request, attempt, datetime.now(UTC)),
    ):
        with pytest.raises(LeaseLost):
            action()


def test_budget_survives_new_store_and_stage_and_counts_cancelled_preparations(db, provider_setup):
    store, request = provider_setup()
    for index in range(3):
        attempt = prepare(store, request)
        store.finish(request, attempt, "cancelled", datetime.now(UTC), failure="reserved")
        finish_stage(db, request.lease, stage_id=request.stage_id, outcome="completed")
        stage = start_stage(db, request.lease, stage_key=f"retry_{index}")
        request = replace(request, logical_fetch_id=uuid4(), stage_id=stage)
        store = DatabaseProviderStore(db, store.descriptor)
    with pytest.raises(ProviderBudgetExceeded, match="three"):
        prepare(store, request)
    assert db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"] == 3


@pytest.mark.parametrize(
    "quota",
    [
        ProviderQuota(1, 100, 100, 100, 10**13),
        ProviderQuota(100, 1, 100, 100, 10**13),
        ProviderQuota(100, 100, 1, 100, 10**13),
        ProviderQuota(100, 100, 100, 100, PROVIDER_WIRE_LIMIT),
    ],
)
def test_account_reservations_are_durable_across_requests(db, provider_setup, quota):
    first, request = provider_setup(ProviderKind.TIINGO, quota=quota)
    attempt = prepare(first, request)
    first.finish(request, attempt, "cancelled", datetime.now(UTC), failure="reserved")
    second, later = provider_setup(ProviderKind.TIINGO, quota=quota)
    with pytest.raises(ProviderBudgetExceeded, match="account"):
        prepare(second, later)
    assert db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"] == 1


def test_symbol_budget_counts_prepared_distinct_symbols(provider_setup):
    quota = ProviderQuota(100, 100, 100, 1, 10**13)
    first, request = provider_setup(ProviderKind.TIINGO, quota=quota)
    prepare(first, request)
    second, later = provider_setup(ProviderKind.TIINGO, quota=quota, symbol="OTHER")
    with pytest.raises(ProviderBudgetExceeded, match="symbols"):
        prepare(second, later)


def test_tiingo_requires_reviewed_quota(provider_setup):
    store, request = provider_setup(ProviderKind.TIINGO)
    store.descriptor = replace(store.descriptor, quota=None)
    with pytest.raises(PermissionError, match="quota"):
        prepare(store, request)


def test_store_refuses_outer_transaction(db, provider_setup):
    store, request = provider_setup()
    with db.transaction(), pytest.raises(RuntimeError, match="idle"):
        prepare(store, request)


def test_cannot_finalize_other_resource_attempt(db, provider_setup):
    store, request = provider_setup()
    attempt = prepare(store, request)
    other, other_request = provider_setup()
    with pytest.raises(PermissionError, match="attempt"):
        other.finish(
            other_request, attempt, "cancelled", datetime.now(UTC), failure="cross_request"
        )
    assert (
        db.execute("SELECT state FROM source_fetch_attempts WHERE id=%s", (attempt,)).fetchone()[
            "state"
        ]
        == "prepared"
    )


@pytest.mark.parametrize(
    "url,object_key,expected",
    [
        (
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000001.json",
            "company_facts/0000000001",
            True,
        ),
        (
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000001.json",
            "company_facts/0000000002",
            False,
        ),
        ("https://data.sec.gov/submissions/CIK0000000001.json", "submissions/0000000001", True),
        ("https://data.sec.gov/submissions/CIK0000000001.json", "submissions/0000000002", False),
        (
            "https://data.sec.gov/submissions/CIK0000000001-submissions-001.json",
            "submissions_history/0000000001/CIK0000000001-submissions-001.json",
            True,
        ),
        (
            "https://data.sec.gov/submissions/CIK0000000001-submissions-001.json",
            "submissions_history/0000000002/CIK0000000001-submissions-001.json",
            False,
        ),
        (
            "https://data.sec.gov/submissions/CIK0000000001-submissions-001.json",
            "submissions_history/0000000001/CIK0000000001-submissions-002.json",
            False,
        ),
        (
            "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/test.htm",
            "filing_document/0000000001/0000000001-25-000001/test.htm",
            True,
        ),
        (
            "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/test.htm",
            "filing_document/0000000002/0000000001-25-000001/test.htm",
            False,
        ),
        (
            "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/test.htm",
            "filing_document/0000000001/0000000001-25-000002/test.htm",
            False,
        ),
        (
            "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/test.htm",
            "filing_document/0000000001/0000000001-25-000001/other.htm",
            False,
        ),
    ],
)
def test_sec_exemption_binds_url_to_exact_object(db_admin, url, object_key, expected):
    from tests.evidence_seed import _insert_record

    source, policy = uuid4(), uuid4()
    insert(
        db_admin,
        "sources",
        id=source,
        source_key=uuid4().hex,
        name="SEC test identity",
        base_url="https://data.sec.gov",
        terms_review_reference="fictional",
        content_scope="fictional",
    )
    _insert_record(
        db_admin,
        "source_policy_revisions",
        id=policy,
        source_id=source,
        review_key="fictional",
        licence_label="Fictional test evidence only",
        content_scope="Fixture",
        redistribution_status="unknown",
        permitted_use="Tests only",
        attribution_requirements="Fixture",
        terms_urls=["https://example.invalid"],
        reviewed_at=datetime.now(UTC),
        reviewed_by="test",
        review_artifact_reference="fixture",
        review_artifact_sha256="a" * 64,
    )
    assert (
        db_admin.execute(
            "SELECT market_sec_resource(%s,%s,%s,%s) AS exempt", (source, policy, url, object_key)
        ).fetchone()["exempt"]
        is expected
    )


def test_provider_cannot_claim_another_registered_origin(provider_setup):
    store, request = provider_setup(base_url="https://example.invalid")
    with pytest.raises(PermissionError, match="registered source"):
        prepare(store, request)


def test_preparations_are_serialized_across_database_connections(db_admin, provider_setup):
    from concurrent.futures import ThreadPoolExecutor

    import psycopg
    from psycopg.rows import dict_row

    quota = ProviderQuota(1, 100, 100, 100, 10**13)
    first, request = provider_setup(ProviderKind.TIINGO, quota=quota)
    second, later = provider_setup(ProviderKind.TIINGO, quota=quota)

    def reserve(item):
        descriptor, intent = item
        with psycopg.connect(
            db_admin.info.dsn, autocommit=True, row_factory=dict_row
        ) as connection:
            connection.execute("SET ROLE equity_runtime")
            store = DatabaseProviderStore(connection, descriptor)
            try:
                prepare(store, intent)
                return "reserved"
            except ProviderBudgetExceeded:
                return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(reserve, [(first.descriptor, request), (second.descriptor, later)])
        )
    assert sorted(outcomes) == ["blocked", "reserved"]


def test_restart_into_new_execution_does_not_reset_logical_attempt_budget(db, provider_setup):
    from equity_schema.workflow import retry_execution

    store, request = provider_setup()
    for sequence in range(1, 4):
        attempt = prepare(store, request, sequence)
        store.finish(request, attempt, "cancelled", datetime.now(UTC), failure="reserved")
    retry_execution(db, request.lease, error_code="restart", delay_seconds=0)
    lease = claim_next(db, worker_id="restarted")
    assert lease and lease.request_id == request.lease.request_id
    assert lease.execution_id != request.lease.execution_id
    request = replace(
        request,
        logical_fetch_id=uuid4(),
        lease=lease,
        stage_id=start_stage(db, lease, stage_key="provider_fetch"),
    )
    with pytest.raises(ProviderBudgetExceeded, match="three"):
        prepare(DatabaseProviderStore(db, store.descriptor), request)


def test_authorized_capture_can_finish_and_replay_after_disable(db_admin, provider_setup, tmp_path):
    from equity_ingest.archive import ArchiveError, LocalArchive
    from equity_ingest.contracts import RawRecord
    from equity_schema import ingestion

    store, request = provider_setup()
    attempt = prepare(store, request)
    dispatched = datetime.now(UTC)
    store.dispatched(request, attempt, dispatched)
    disable_policy(
        db_admin, store.descriptor.policy_revision_id, actor="test", reason="stop new dispatch"
    )
    store.headers(
        request,
        attempt,
        datetime.now(UTC),
        200,
        ingestion.ResponseHeaders(content_type="text/xml"),
    )
    now, capture_id = datetime.now(UTC), uuid4()
    archived = LocalArchive(tmp_path).write(
        [b"<fictional/>"],
        source_key=store.descriptor.source_key,
        source_object_key=request.resource.object_key,
        params_hash=request.resource.params_hash,
        capture_id=capture_id,
        retrieved_at=now,
        max_bytes=1024,
    )
    record = RawRecord(
        capture_id,
        store.descriptor.source_id,
        request.resource.object_key,
        request.resource.url,
        request.resource.params_hash,
        dispatched,
        now,
        now,
        200,
        archived.body_sha256,
        archived.byte_count,
        archived.blob_key,
        "text/xml",
        store.descriptor.policy_revision_id,
        store.descriptor.terms_review_reference,
    )
    store.finish(request, attempt, "complete", now, capture=record)
    store.validate_record(record)
    with pytest.raises(ArchiveError):
        store.validate_record(replace(record, body_sha256="b" * 64))
    with pytest.raises(PermissionError):
        store.guard(request)


@pytest.mark.parametrize("operation", ["dispatched", "headers", "finish"])
def test_store_rejects_ambiguous_naive_evidence_time(provider_setup, operation):
    from equity_schema import ingestion

    store, request = provider_setup()
    attempt = prepare(store, request)
    naive = datetime.now(UTC).replace(tzinfo=None)
    if operation != "dispatched":
        store.dispatched(request, attempt, datetime.now(UTC))
    with pytest.raises(ValueError, match="timezone"):
        if operation == "headers":
            store.headers(request, attempt, naive, 200, ingestion.ResponseHeaders())
        elif operation == "finish":
            store.finish(request, attempt, "cancelled", naive, failure="test")
        else:
            store.dispatched(request, attempt, naive)


@pytest.mark.parametrize("entrypoint", ["prepare", "capture"])
@pytest.mark.parametrize(
    "kind,base_url,url,object_key,allowed",
    [
        (
            ProviderKind.TREASURY,
            None,
            TreasuryResource("202501").url,
            "daily_treasury_yield_curve",
            True,
        ),
        (ProviderKind.TREASURY, None, TreasuryResource("202501").url, "unrelated_metadata", False),
        (
            ProviderKind.TREASURY,
            "https://example.invalid",
            TreasuryResource("202501").url,
            "daily_treasury_yield_curve",
            False,
        ),
        (
            ProviderKind.TREASURY,
            None,
            "https://api.tiingo.com/tiingo/daily/TEST/prices",
            "daily_treasury_yield_curve",
            False,
        ),
        (
            ProviderKind.TREASURY,
            None,
            "https://home.treasury.gov/metadata",
            "fictional_metadata",
            True,
        ),
        (
            ProviderKind.TREASURY,
            None,
            "https://home.treasury.gov.evil.invalid/metadata",
            "fictional_metadata",
            False,
        ),
        (
            ProviderKind.TIINGO,
            None,
            "https://api.tiingo.com/tiingo/daily/TEST/prices",
            "tiingo_eod/TEST",
            True,
        ),
        (
            ProviderKind.TIINGO,
            None,
            "https://api.tiingo.com/tiingo/daily/OTHER/prices",
            "tiingo_eod/TEST",
            False,
        ),
        (
            ProviderKind.TIINGO,
            None,
            "https://api.tiingo.com/tiingo/daily/TEST/prices",
            "fictional_metadata",
            False,
        ),
        (
            ProviderKind.TIINGO,
            None,
            "https://api.tiingo.com/tiingo/daily/TEST",
            "fictional_metadata",
            True,
        ),
        (
            ProviderKind.TIINGO,
            None,
            "https://example.invalid/metadata",
            "fictional_metadata",
            False,
        ),
        (
            ProviderKind.TIINGO,
            None,
            "https://api.tiingo.com:443/tiingo/daily/TEST/prices",
            "tiingo_eod/TEST",
            False,
        ),
        (
            ProviderKind.FRED,
            None,
            "https://api.stlouisfed.org/fred/series/observations",
            "fred_observations/DGS10",
            True,
        ),
        (
            ProviderKind.FRED,
            None,
            "https://api.stlouisfed.org/fred/series/observations?api_key=fictional",
            "fred_observations/DGS10",
            False,
        ),
        (
            ProviderKind.FRED,
            None,
            "https://api.stlouisfed.org/fred/series",
            "fictional_metadata",
            True,
        ),
        (
            ProviderKind.FRED,
            None,
            "https://home.treasury.gov/metadata",
            "fictional_metadata",
            False,
        ),
        (
            ProviderKind.FRED,
            "https://example.invalid",
            "https://example.invalid/fixture",
            "fred_observations/DGS10",
            False,
        ),
        (
            ProviderKind.FRED,
            "https://example.invalid",
            "https://API.STLOUISFED.ORG/fred/series/observations",
            "fictional_metadata",
            False,
        ),
    ],
)
def test_shared_sql_guards_reject_misattributed_provider_resources(
    db_admin, db, provider_setup, entrypoint, kind, base_url, url, object_key, allowed
):
    import psycopg
    from equity_schema import ingestion

    store, request = provider_setup(kind, base_url=base_url)

    def persist():
        if entrypoint == "prepare":
            ingestion.prepare_attempt(
                db,
                request.lease,
                request.stage_id,
                ingestion.AttemptRequest(
                    uuid4(),
                    1,
                    store.descriptor.source_id,
                    store.descriptor.policy_revision_id,
                    object_key,
                    url,
                    request.resource.params_hash,
                ),
            )
        else:
            now = datetime.now(UTC)
            insert(
                db_admin,
                "source_captures",
                id=uuid4(),
                source_id=store.descriptor.source_id,
                source_object_key=object_key,
                request_url=url,
                request_params_hash=request.resource.params_hash,
                requested_at=now,
                fetched_at=now,
                completed_at=now,
                http_status=200,
                body_sha256="a" * 64,
                blob_key="fictional/source",
                byte_count=1,
                content_type="text/plain",
                terms_review_reference="test-only",
            )

    if allowed:
        persist()
    else:
        with pytest.raises(psycopg.errors.CheckViolation, match="market resource"):
            persist()


@pytest.mark.parametrize(
    "kind,url",
    [
        (ProviderKind.TREASURY, TreasuryResource("202501").url + "/"),
        (ProviderKind.FRED, "https://api.stlouisfed.org/fred/series/observations/"),
        (ProviderKind.TIINGO, "https://api.tiingo.com/tiingo/daily/TEST/%70rices"),
    ],
)
def test_observation_url_alias_cannot_be_claimed_as_metadata(db, provider_setup, kind, url):
    import psycopg
    from equity_schema import ingestion

    store, request = provider_setup(kind)
    with pytest.raises(psycopg.errors.CheckViolation, match="market resource"):
        ingestion.prepare_attempt(
            db,
            request.lease,
            request.stage_id,
            ingestion.AttemptRequest(
                uuid4(),
                1,
                store.descriptor.source_id,
                store.descriptor.policy_revision_id,
                "fictional_metadata",
                url,
                request.resource.params_hash,
            ),
        )


def _mock_provider_transport(store, archive, handler, *, api_key=None):
    import httpx
    from equity_ingest.provider_transport import ProviderTransport

    from tests.test_ingest_transport import Clock, Limiter

    return ProviderTransport(
        store.descriptor,
        archive,
        Limiter(Clock()),
        store,
        httpx.Client(transport=httpx.MockTransport(handler)),
        api_key=api_key,
        sleep=lambda _: None,
    )


def test_authenticated_redirect_persists_failure_without_secret_target(
    db, provider_setup, tmp_path, caplog
):
    import logging

    import httpx
    from equity_ingest.archive import LocalArchive

    store, request = provider_setup(ProviderKind.FRED)
    archive = LocalArchive(tmp_path)
    key, calls = "FICTIONAL_SECRET_0123456789", []

    def handler(incoming):
        calls.append(incoming)
        assert incoming.url.params["api_key"] == key
        return httpx.Response(
            302,
            stream=httpx.ByteStream(b"moved"),
            headers={"Location": "https://other.invalid/?api_key=" + key},
        )

    caplog.set_level(logging.DEBUG)
    transport = _mock_provider_transport(store, archive, handler, api_key=key)
    result = transport.fetch(request)
    assert len(calls) == 1 and result.gaps == ("redirect_refused",)
    record = result.records[0]
    assert transport.read_verified(record) == b"moved"
    row = db.execute(
        "SELECT state,failure_code,http_status,response_headers,completed_capture_id,"
        "request_url,request_params_hash FROM source_fetch_attempts WHERE id=%s",
        (result.attempts[0].attempt_id,),
    ).fetchone()
    assert row["state"] == row["failure_code"] == "redirect_refused"
    assert row["http_status"] == 302 and row["completed_capture_id"] == record.capture_id
    assert "location" not in row["response_headers"]
    assert key not in repr(row) + repr(result) + caplog.text
    assert "api_key" not in row["request_url"]


@pytest.mark.parametrize("mode", ["header", "body", "gzip_body"])
def test_reflected_credentials_never_reach_database_archive_or_logs(
    db, provider_setup, tmp_path, caplog, mode
):
    import gzip
    import logging

    import httpx
    from equity_ingest.archive import LocalArchive

    store, request = provider_setup(ProviderKind.FRED)
    archive = LocalArchive(tmp_path)
    key = "FICTIONAL_SECRET_0123456789"
    body = b"safe" if mode == "header" else b'{"error":"' + key.encode() + b'"}'
    headers = {"ETag": key} if mode == "header" else {}
    if mode == "gzip_body":
        body = gzip.compress(body)
        headers["Content-Encoding"] = "gzip"

    class Chunks(httpx.SyncByteStream):
        def __iter__(self):
            for offset in range(0, len(body), 3):
                yield body[offset : offset + 3]

    caplog.set_level(logging.DEBUG)
    transport = _mock_provider_transport(
        store,
        archive,
        lambda _: httpx.Response(403, stream=Chunks(), headers=headers),
        api_key=key,
    )
    result = transport.fetch(request)
    assert result.gaps == ("unsafe_reflected_secret",) and not result.records
    rows = db.execute(
        "SELECT * FROM source_fetch_attempts WHERE logical_fetch_id=%s",
        (request.logical_fetch_id,),
    ).fetchall()
    assert len(rows) == 1 and rows[0]["state"] == "archive_error"
    assert rows[0]["failure_code"] == "unsafe_reflected_secret"
    assert rows[0]["completed_capture_id"] is None
    assert key not in repr(rows) + repr(result) + caplog.text
    assert not list(archive.root.rglob("*.gz"))
    assert not list(archive.root.rglob(".partial-*"))


def test_market_conditional_reuse_and_disabled_historical_replay(
    db_admin, db, provider_setup, tmp_path
):
    import httpx
    from equity_ingest.archive import LocalArchive

    store, request = provider_setup()
    archive = LocalArchive(tmp_path)
    calls = []

    def handler(incoming):
        calls.append(incoming)
        return httpx.Response(
            304 if len(calls) > 1 else 200,
            stream=httpx.ByteStream(b"" if len(calls) > 1 else b"<fictional/>"),
            headers={"ETag": '"fixture-v1"'},
        )

    transport = _mock_provider_transport(store, archive, handler)
    original = transport.fetch(request)
    assert original.usable
    record = original.records[0]
    conditional = replace(
        request, logical_fetch_id=uuid4(), cache_mode="conditional", cached_record=record
    )
    reused = transport.fetch(conditional)
    assert reused.usable and reused.records == (record,)
    assert calls[1].headers["If-None-Match"] == '"fixture-v1"'
    assert db.execute(
        "SELECT state,reused_capture_id FROM source_fetch_attempts WHERE id=%s",
        (reused.attempts[0].attempt_id,),
    ).fetchone() == {"state": "not_modified", "reused_capture_id": record.capture_id}
    disable_policy(
        db_admin, store.descriptor.policy_revision_id, actor="test", reason="stop live source"
    )
    replay = replace(
        request,
        lease=None,
        stage_id=None,
        cache_mode="replay",
        replay_records=(record,),
        retrieval_cutoff=record.completed_at,
    )
    assert transport.fetch(replay).records == (record,)
    assert len(calls) == 2
