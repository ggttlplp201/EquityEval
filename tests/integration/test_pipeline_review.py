"""Independent pipeline boundary review using real DB state and archived source bytes."""

import json
from dataclasses import fields, replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from equity_ingest import pipeline
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import FetchResult, RawRecord, ResourceKind, SecResource
from equity_ingest.pipeline import SourcePlan, run_source_stages
from equity_ingest.publisher import NORMALIZATION_STAGE
from equity_ingest.sec_normalize import normalize_verified_bytes
from equity_schema.workflow import (
    LeaseLost,
    RequestedPeriod,
    RequestOptions,
    add_watchlist_stock,
    cancel_request,
    claim_next,
    create_workspace_watchlist,
)

from tests.evidence_seed import insert
from tests.normalization_db_seed import seed_normalization_inputs
from tests.sec_normalization_seed import cohort_input

pytestmark = pytest.mark.integration


class ArchivedReviewSource:
    """A deterministic Source test double; all returned captures already exist in PostgreSQL."""

    def __init__(self, body, record):
        self.body = body
        self.record = record
        self.calls = []
        self.normalizations = []
        self.companyfacts_result = FetchResult(records=(record,))

    def fetch(self, request):
        self.calls.append(request)
        if request.resource.kind == ResourceKind.COMPANY_FACTS:
            return self.companyfacts_result
        return FetchResult(gaps=("submissions_unavailable",))

    def read_verified(self, capture_id):
        assert capture_id == self.record.capture_id
        return self.body

    def normalize(self, inputs):
        self.normalizations.append(inputs)
        return normalize_verified_bytes(self.body, inputs)


@pytest.fixture
def review_run(db_admin, db, tmp_path):
    def prepare(options=None):
        body, inputs = cohort_input("AAPL")
        resource = SecResource(inputs.issuer_id, inputs.cik, ResourceKind.COMPANY_FACTS)
        primary = replace(inputs.captures[0], source_object_key=resource.object_key)
        inputs = replace(inputs, captures=(primary, *inputs.captures[1:]))
        seed_normalization_inputs(db_admin, inputs)
        security = next(
            request.scope.instrument_id
            for request in inputs.requests
            if request.scope.instrument_id is not None
        )
        quote = uuid4()
        insert(
            db_admin,
            "security_identifiers",
            id=quote,
            security_id=security,
            symbol="REVIEW",
            exchange_code="TEST",
            quote_currency="USD",
            valid_from="2020-01-01",
            source_capture_id=primary.id,
        )
        workspace = create_workspace_watchlist(db, name="Independent S3 pipeline review")
        request = add_watchlist_stock(
            db,
            watchlist_id=workspace.watchlist_id,
            security_id=security,
            quote_identifier_id=quote,
            idempotency_key="review",
            options=options,
        )
        lease = claim_next(db, worker_id="pipeline-review")
        assert lease is not None
        row = db_admin.execute(
            "SELECT c.*,p.policy_revision_id FROM source_captures c "
            "JOIN capture_policy_links p ON p.capture_id=c.id WHERE c.id=%s",
            (primary.id,),
        ).fetchone()
        record = RawRecord(
            capture_id=row["id"],
            **{
                field.name: row[field.name]
                for field in fields(RawRecord)
                if field.name in row and field.name != "capture_id"
            },
        )
        source = ArchivedReviewSource(body, record)
        plan = SourcePlan(inputs.issuer_id, inputs.cik, date(1990, 1, 1), date(2026, 9, 12))
        archive = LocalArchive(tmp_path / "archive")
        return inputs, request, lease, source, plan, archive

    return prepare


def test_failed_companyfacts_never_normalizes_or_publishes(db, review_run):
    inputs, _, lease, source, plan, archive = review_run()
    source.companyfacts_result = FetchResult(gaps=("body_incomplete",))
    result = run_source_stages(db, lease, source, archive, plan, lambda context: inputs)
    assert result.state == "waiting_for_input"
    assert result.publication is None
    assert not source.normalizations
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0


def test_wrong_reviewed_period_cannot_mark_request_complete(db, review_run):
    options = RequestOptions(requested_periods=(RequestedPeriod("instant", date(2020, 12, 31)),))
    inputs, _, lease, source, plan, archive = review_run(options)
    with pytest.raises(ValueError, match="period"):
        run_source_stages(db, lease, source, archive, plan, lambda context: inputs)
    assert not source.normalizations
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0
    assert (
        db.execute(
            "SELECT state FROM analysis_executions WHERE id=%s", (lease.execution_id,)
        ).fetchone()["state"]
        == "failed"
    )


def test_historical_vintage_cannot_fall_back_to_live_fetch(db, review_run):
    inputs, _, lease, source, plan, archive = review_run(
        RequestOptions(retrieval_vintage=datetime(2025, 1, 1, tzinfo=UTC))
    )
    with pytest.raises(ValueError, match="archived replay"):
        run_source_stages(db, lease, source, archive, plan, lambda context: inputs)
    assert not source.calls
    assert not source.normalizations


def test_cancellation_during_reviewed_mapping_blocks_publication(db, review_run):
    inputs, request, lease, source, plan, archive = review_run()

    def cancel_then_return(context):
        cancel_request(db, request_id=request.request_id)
        return inputs

    with pytest.raises(LeaseLost):
        run_source_stages(db, lease, source, archive, plan, cancel_then_return)
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0
    assert (
        db.execute(
            "SELECT state FROM analysis_executions WHERE id=%s", (lease.execution_id,)
        ).fetchone()["state"]
        == "cancelled"
    )


def test_deferred_source_records_retry_without_normalizing(db, review_run):
    inputs, _, lease, source, plan, archive = review_run()
    source.companyfacts_result = FetchResult(
        gaps=("sec_cooldown",), next_eligible_at=datetime.now(UTC) + timedelta(minutes=2)
    )
    result = run_source_stages(db, lease, source, archive, plan, lambda context: inputs)
    assert result.state == "retry_scheduled"
    assert not source.normalizations
    row = db.execute(
        "SELECT state FROM analysis_executions WHERE id=%s", (lease.execution_id,)
    ).fetchone()
    assert row["state"] == "failed"
    following = db.execute(
        "SELECT e.state,e.available_at>s.updated_at AS deferred "
        "FROM analysis_request_state s JOIN analysis_executions e ON e.id=s.current_execution_id "
        "WHERE s.request_id=%s",
        (lease.request_id,),
    ).fetchone()
    assert following == {"state": "queued", "deferred": True}
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0


def test_request_history_policy_reaches_reviewed_input_builder(db, review_run):
    cutoff = date(2025, 10, 31)
    inputs, _, lease, source, plan, archive = review_run(
        RequestOptions(history_mode="as_filed_by_date", filed_cutoff=cutoff)
    )
    seen = []

    def build(context):
        seen.append(context)
        assert context.history_mode == "as_filed_by_date"
        assert context.filed_cutoff == cutoff
        return None

    result = run_source_stages(db, lease, source, archive, plan, build)
    assert seen
    assert result.state == "waiting_for_input"


def test_published_batch_has_durable_manifest_even_if_worker_dies_after_publish(
    db, review_run, monkeypatch
):
    inputs, _, lease, source, plan, archive = review_run()
    original_publish = pipeline.publish_bundle

    def publish_then_crash(*args, **kwargs):
        original_publish(*args, **kwargs)
        raise SystemExit("Simulated process death immediately after publication commits")

    monkeypatch.setattr(pipeline, "publish_bundle", publish_then_crash)
    with pytest.raises(SystemExit):
        run_source_stages(db, lease, source, archive, plan, lambda context: inputs)
    batch = db.execute("SELECT id FROM normalization_batches WHERE state='published'").fetchone()
    assert batch is not None
    stage = db.execute(
        "SELECT state,error_code FROM analysis_stage_attempts "
        "WHERE execution_id=%s AND stage_key=%s",
        (lease.execution_id, NORMALIZATION_STAGE),
    ).fetchone()
    assert stage["state"] == "completed", "Published evidence must retain its manifest atomically"
    audit = json.loads(stage["error_code"])
    assert audit["batch_id"] == str(batch["id"])
    manifest = audit["manifest"]
    payload = json.loads(
        archive.read_blob(manifest["blob_key"], manifest["body_sha256"], manifest["byte_count"])
    )
    assert payload["bundle"]["inputs"]["companyfacts_capture_id"] == str(
        inputs.companyfacts_capture_id
    )


def test_wrong_issuer_plan_is_rejected_before_any_source_fetch(db, review_run):
    inputs, _, lease, source, plan, archive = review_run()
    with pytest.raises(ValueError, match="issuer"):
        run_source_stages(
            db, lease, source, archive, replace(plan, issuer_id=uuid4()), lambda context: inputs
        )
    assert not source.calls
    assert not source.normalizations
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 0


def test_exhausted_retry_does_not_claim_a_future_run_exists(db, review_run):
    inputs, _, lease, source, plan, archive = review_run(RequestOptions(max_attempts=1))
    source.companyfacts_result = FetchResult(
        gaps=("sec_cooldown",), next_eligible_at=datetime.now(UTC) + timedelta(minutes=2)
    )
    result = run_source_stages(db, lease, source, archive, plan, lambda context: inputs)
    terminal = db.execute(
        "SELECT terminal_outcome FROM analysis_request_state WHERE request_id=%s",
        (lease.request_id,),
    ).fetchone()["terminal_outcome"]
    assert terminal == "failed"
    assert result.state == "failed"
    assert result.publication is None
