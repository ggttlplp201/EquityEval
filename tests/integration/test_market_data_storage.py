"""Approved S4 contract against PostgreSQL; all values and sources are fictional."""

from datetime import date
from uuid import uuid4

import psycopg
import pytest

from tests.evidence_seed import seed_evidence

pytestmark = pytest.mark.integration


def test_contract_tables_exist(db_admin):
    for table in (
        "source_policy_capabilities",
        "provider_quote_bindings",
        "market_data_batches",
        "market_data_batch_inputs",
        "market_data_quality_flags",
        "price_daily",
        "macro_series_definitions",
        "macro_observations",
    ):
        assert db_admin.execute("SELECT to_regclass(%s) AS name", (table,)).fetchone()["name"]


def test_market_request_plan_is_immutable_and_hashes_all_options(db_admin, db):
    from equity_schema.workflow import (
        MarketDataRequestPlan,
        RequestOptions,
        add_watchlist_stock,
        create_workspace_watchlist,
    )

    ids = seed_evidence(db_admin)
    workspace = create_workspace_watchlist(db, name="S4")
    plan = MarketDataRequestPlan(
        market_plan_revision="s4-market-data-v1",
        price_source_id=ids["source"],
        price_start=date(2025, 1, 1),
        price_end=date(2025, 1, 2),
    )
    kwargs = dict(
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key="s4-plan",
    )
    first = add_watchlist_stock(db, **kwargs, options=RequestOptions(market_plan=plan))
    assert add_watchlist_stock(db, **kwargs, options=RequestOptions(market_plan=plan)) == first
    row = db.execute(
        "SELECT price_source_id,price_start,macro_source_as_of_date "
        "FROM analysis_requests WHERE id=%s",
        (first.request_id,),
    ).fetchone()
    assert row == {
        "price_source_id": ids["source"],
        "price_start": date(2025, 1, 1),
        "macro_source_as_of_date": None,
    }
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        add_watchlist_stock(db, **kwargs, options=RequestOptions())
    with pytest.raises(psycopg.Error):
        db_admin.execute(
            "UPDATE analysis_requests SET price_end='2025-01-03' WHERE id=%s", (first.request_id,)
        )


@pytest.mark.parametrize(
    "value,state,text,valid",
    [
        ("100.25", "observed", "100.25", True),
        ("0", "observed", "0", True),
        (None, "source_null", "null", True),
        (None, "missing", None, True),
        ("0", "missing", None, False),
        ("NaN", "observed", "NaN", False),
        ("Infinity", "observed", "Infinity", False),
        (None, "observed", "2.5", False),
    ],
)
def test_price_numeric_state_requires_exact_source_meaning(db, value, state, text, valid):
    assert (
        db.execute(
            "SELECT market_numeric_valid(%s::numeric,%s,%s,false) AS valid", (value, state, text)
        ).fetchone()["valid"]
        is valid
    )


def test_runtime_cannot_self_approve_or_write_market_rows(db):
    for table in (
        "source_policy_capabilities",
        "price_daily",
        "macro_observations",
        "market_data_batches",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(
                psycopg.sql.SQL("INSERT INTO {} DEFAULT VALUES").format(
                    psycopg.sql.Identifier(table)
                )
            )


@pytest.mark.parametrize(
    "change",
    [
        {"market_plan_revision": "unreviewed"},
        {"price_source_id": "not-a-uuid"},
        {"price_start": None},
        {"price_end": date(2024, 12, 31)},
        {"macro_series_keys": ("DGS10",)},
        {"macro_source_as_of_date": date(2025, 1, 1)},
    ],
)
def test_market_plan_rejects_inconsistent_intent(change):
    from equity_schema.workflow import MarketDataRequestPlan

    values = dict(
        market_plan_revision="s4-market-data-v1",
        price_source_id=uuid4(),
        price_start=date(2025, 1, 1),
        price_end=date(2025, 1, 2),
    )
    with pytest.raises(ValueError):
        MarketDataRequestPlan(**(values | change))


def test_request_plan_preserves_legacy_options_and_separates_cutoffs():
    from equity_schema.workflow import MarketDataRequestPlan, RequestOptions

    assert "market_plan" not in RequestOptions().as_json()
    source = uuid4()
    plan = MarketDataRequestPlan(
        "s4-market-data-v1",
        macro_source_id=source,
        macro_series_keys=("TWO", "TEN"),
        macro_start=date(2020, 1, 1),
        macro_end=date(2020, 1, 3),
        macro_source_as_of_date=date(2020, 2, 1),
    )
    options = RequestOptions(
        history_mode="as_filed_by_date", filed_cutoff=date(2020, 3, 1), market_plan=plan
    )
    assert options.as_json()["filed_cutoff"] == "2020-03-01"
    assert options.as_json()["market_plan"]["macro_source_as_of_date"] == "2020-02-01"
    assert plan.macro_series_keys == ("TEN", "TWO")


def test_runtime_cannot_activate_a_policy(db):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("SELECT market_activate_policy(%s,'runtime','not authorized')", (uuid4(),))


def test_capability_replacement_preserves_historical_grant(db_admin, db):
    from tests.evidence_seed import _insert_record

    ids = seed_evidence(db_admin)
    old = db_admin.execute(
        "SELECT p.* FROM source_policy_revisions p JOIN capture_policy_links l "
        "ON l.policy_revision_id=p.id WHERE l.capture_id=%s",
        (ids["capture"],),
    ).fetchone()
    new_id = uuid4()
    _insert_record(
        db_admin,
        "source_policy_revisions",
        **(dict(old) | {"id": new_id, "review_key": "replacement"}),
    )
    old_cap = db_admin.execute(
        "SELECT * FROM source_policy_capabilities WHERE policy_revision_id=%s", (old["id"],)
    ).fetchone()
    fields = dict(old_cap) | {"policy_revision_id": new_id}
    for name in (
        "activated_at",
        "activated_by",
        "activation_reason",
        "disabled_at",
        "disabled_by",
        "disable_reason",
    ):
        fields[name] = None
    _insert_record(db_admin, "source_policy_capabilities", **fields)
    db_admin.execute("SELECT market_activate_policy(%s,'reviewer','new scope review')", (new_id,))
    assert (
        db.execute(
            "SELECT count(*) AS n FROM source_policy_capabilities WHERE source_id=%s "
            "AND activated_at IS NOT NULL AND disabled_at IS NULL",
            (ids["source"],),
        ).fetchone()["n"]
        == 1
    )
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
        db.execute(
            "SELECT market_validate_policy(%s,%s,'fixture',NULL,false,true)",
            (old["id"], ids["source"]),
        )
    assert db.execute(
        "SELECT market_validate_policy(%s,%s,'fixture',NULL,false,false) AS ok",
        (old["id"], ids["source"]),
    ).fetchone()["ok"]
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
        db_admin.execute(
            "SELECT market_activate_policy(%s,'reviewer','cannot reactivate')", (old["id"],)
        )


def test_policy_requires_exact_content_scope(db_admin, db):
    from tests.evidence_seed import _insert_record

    ids = seed_evidence(db_admin)
    old = db_admin.execute(
        "SELECT p.* FROM source_policy_revisions p JOIN capture_policy_links l "
        "ON l.policy_revision_id=p.id WHERE l.capture_id=%s",
        (ids["capture"],),
    ).fetchone()
    policy = uuid4()
    _insert_record(
        db_admin,
        "source_policy_revisions",
        **(dict(old) | {"id": policy, "review_key": "exact-scope"}),
    )
    _insert_record(
        db_admin,
        "source_policy_capabilities",
        policy_revision_id=policy,
        source_id=ids["source"],
        raw_scope_kind="source_objects",
        raw_scope_keys=["monthly_yields"],
        normalized_scope_kind="macro_series",
        normalized_scope_keys=["TEN"],
        raw_retention="indefinite_without_required_deletion",
        normalized_retention="indefinite_without_required_deletion",
        internal_analysis_allowed=True,
        review_basis="Fictional exact scope",
    )
    db_admin.execute("SELECT market_activate_policy(%s,'reviewer','fictional scope')", (policy,))
    for object_key, series, normalized in (
        ("another_object", None, False),
        ("monthly_yields", "TWO", True),
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute(
                "SELECT market_validate_policy(%s,%s,%s,%s,%s,true)",
                (policy, ids["source"], object_key, series, normalized),
            )
    assert db.execute(
        "SELECT market_validate_policy(%s,%s,'monthly_yields','TEN',true,true) AS ok",
        (policy, ids["source"]),
    ).fetchone()["ok"]


@pytest.fixture
def market_transport_attempt(db_admin, db):
    from equity_schema.ingestion import AttemptRequest
    from equity_schema.workflow import (
        add_watchlist_stock,
        claim_next,
        create_workspace_watchlist,
        start_stage,
    )

    ids = seed_evidence(db_admin)
    policy = db_admin.execute(
        "SELECT policy_revision_id FROM capture_policy_links WHERE capture_id=%s",
        (ids["capture"],),
    ).fetchone()["policy_revision_id"]
    workspace = create_workspace_watchlist(db, name="Market policy transport")
    add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=ids["security"],
        quote_identifier_id=ids["quote"],
        idempotency_key="policy transport",
    )
    lease = claim_next(db, worker_id="market policy worker")
    stage = start_stage(db, lease, stage_key="source_fetch")
    request = AttemptRequest(
        uuid4(), 1, ids["source"], policy, "fixture", "https://example.invalid/fixture", "a" * 64
    )
    return ids, policy, lease, stage, request


def test_old_generic_prepare_cannot_bypass_deactivation(db_admin, db, market_transport_attempt):
    from equity_schema.ingestion import prepare_attempt

    _, policy, lease, stage, request = market_transport_attempt
    db_admin.execute("SELECT market_disable_policy(%s,'reviewer','source disabled')", (policy,))
    with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState, match="inactive"):
        prepare_attempt(db, lease, stage, request)
    assert db.execute("SELECT count(*) AS n FROM source_fetch_attempts").fetchone()["n"] == 0


def test_authorized_dispatch_retains_capture_when_operationally_disabled(
    db_admin, db, market_transport_attempt
):
    from datetime import UTC, datetime

    from equity_schema.ingestion import (
        CaptureMetadata,
        ResponseHeaders,
        finalize_attempt,
        mark_dispatched,
        prepare_attempt,
        record_response_headers,
    )

    _, policy, lease, stage, request = market_transport_attempt
    attempt = prepare_attempt(db, lease, stage, request)
    mark_dispatched(db, lease, attempt, datetime.now(UTC))
    record_response_headers(
        db, lease, attempt, datetime.now(UTC), 200, ResponseHeaders(content_type="application/json")
    )
    db_admin.execute("SELECT market_disable_policy(%s,'reviewer','stop new dispatch')", (policy,))
    capture = CaptureMetadata(uuid4(), datetime.now(UTC), "d" * 64, "fictional/retained.gz", 2)
    assert (
        finalize_attempt(
            db, lease, attempt, "complete", datetime.now(UTC), completed_capture=capture
        )
        == capture.capture_id
    )
    assert (
        db.execute(
            "SELECT policy_revision_id FROM capture_policy_links WHERE capture_id=%s",
            (capture.capture_id,),
        ).fetchone()["policy_revision_id"]
        == policy
    )
