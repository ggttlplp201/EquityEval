"""Watchlist -> real source adapter -> archived normalization -> durable rerun.

HTTP returns pinned S1 Company Facts and an explicitly synthetic inventory; no
upstream requests and no claim that the inventory establishes original history.
"""

import json
import shutil
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from equity_ingest.archive import LocalArchive
from equity_ingest.contracts import RawRecord, ResourceKind, SourceDescriptor
from equity_ingest.financial_types import EvidenceCapture, evidence_id
from equity_ingest.limiter import RedisRateLimiter
from equity_ingest.pipeline import SourcePlan, run_source_stages
from equity_ingest.sec import SecSource
from equity_ingest.transport import DatabaseAttemptStore, SecTransport
from equity_schema.workflow import (
    add_watchlist_stock,
    claim_next,
    create_workspace_watchlist,
    rerun_analysis,
)
from redis import Redis

from tests.evidence_seed import seed_evidence
from tests.normalization_db_seed import seed_normalization_inputs
from tests.sec_normalization_seed import cohort_input

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def source_pipeline(db_admin, db, redis_url, tmp_path):
    body, base = cohort_input("AAPL")
    seed_normalization_inputs(db_admin, base)
    quote = seed_evidence(db_admin, issuer_id=base.issuer_id)
    workspace = create_workspace_watchlist(db, name="SEC pipeline fixture")
    request = add_watchlist_stock(
        db,
        watchlist_id=workspace.watchlist_id,
        security_id=quote["security"],
        quote_identifier_id=quote["quote"],
        idempotency_key="add",
    )
    archive = LocalArchive(tmp_path)
    trusted = []
    for c in base.captures:
        row = db_admin.execute(
            "SELECT c.*,l.policy_revision_id FROM source_captures c "
            "JOIN capture_policy_links l ON l.capture_id=c.id WHERE c.id=%s",
            (c.id,),
        ).fetchone()
        target = tmp_path / row["blob_key"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / row["blob_key"], target)
        trusted.append(
            RawRecord(
                capture_id=row["id"],
                **{
                    k: row[k]
                    for k in RawRecord.__dataclass_fields__
                    if k != "capture_id" and k in row
                },
            )
        )
    descriptor = SourceDescriptor(
        base.captures[0].source_id,
        "sec-pipeline-test",
        "SEC pipeline fixture",
        trusted[0].policy_revision_id,
        trusted[0].terms_review_reference,
        "Fictional test evidence only",
        "unknown",
        tuple(ResourceKind),
        timedelta(minutes=15),
        limiter_key="test:" + uuid4().hex,
    )
    limiter = RedisRateLimiter(
        Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1),
        key=descriptor.limiter_key,
    )
    inventory = json.dumps(
        {
            "cik": base.cik,
            "filings": {
                "recent": {
                    "accessionNumber": [base.filings[0].accession],
                    "filingDate": [base.filings[0].filed_date.isoformat()],
                    "form": ["10-K"],
                },
                "files": [],
            },
        }
    ).encode()
    calls = []

    def handler(request):
        calls.append(str(request.url))
        data = body if "/companyfacts/" in str(request.url) else inventory
        return httpx.Response(
            200, stream=httpx.ByteStream(data), headers={"Content-Type": "application/json"}
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = SecSource(
        descriptor,
        SecTransport(
            descriptor,
            archive,
            limiter,
            DatabaseAttemptStore(db, descriptor),
            client,
            "test@example.invalid",
        ),
        archive,
        trusted_records=tuple(trusted),
    )
    plan = SourcePlan(base.issuer_id, base.cik, date(2020, 1, 1), datetime.now(UTC).date())

    def build(context):
        primary = context.companyfacts
        filing = replace(
            base.filings[0],
            id=evidence_id("pipeline-filing-version", primary.capture_id),
            metadata_capture_id=primary.capture_id,
        )
        captures = (
            base.captures[1],
            *(
                EvidenceCapture(
                    r.capture_id,
                    r.source_id,
                    r.source_object_key,
                    r.request_url,
                    r.body_sha256,
                    r.byte_count,
                    r.fetched_at,
                    r.completed_at,
                    "financial_facts" if r.capture_id == primary.capture_id else "filing_inventory",
                )
                for r in context.records
                if r.successful
            ),
        )
        return replace(
            base,
            companyfacts_capture_id=primary.capture_id,
            captures=captures,
            filings=(filing,),
            captured_before=datetime.now(UTC),
            requests=tuple(replace(r, filing_version_id=filing.id) for r in base.requests),
        )

    yield source, archive, plan, build, calls, workspace, quote, request
    client.close()
    limiter.client.delete(*limiter.keys)


def test_add_and_explicit_rerun_archive_new_inputs_and_preserve_previous_result(
    db, source_pipeline
):
    source, archive, plan, build, calls, workspace, quote, first = source_pipeline
    lease = claim_next(db, worker_id="source-pipeline")
    outcome = run_source_stages(db, lease, source, archive, plan, build)
    assert outcome.state == "completed_with_gaps"
    assert outcome.publication and outcome.manifest
    assert not outcome.publication.original_history_complete
    manifest = json.loads(archive.read(outcome.manifest))
    assert len(manifest["bundle"]["resolutions"]) == 40
    assert manifest["bundle"]["inputs"]["attempt_ids"]
    assert manifest["inventory"]["completeness_basis"].startswith("Advertised")
    stage = db.execute(
        "SELECT error_code FROM analysis_stage_attempts WHERE execution_id=%s "
        "AND stage_key='sec_normalization'",
        (lease.execution_id,),
    ).fetchone()
    assert (
        json.loads(stage["error_code"])["manifest"]["body_sha256"] == outcome.manifest.body_sha256
    )
    rerun = rerun_analysis(
        db,
        workspace_id=workspace.workspace_id,
        security_id=quote["security"],
        quote_identifier_id=quote["quote"],
        idempotency_key="refresh",
        parent_request_id=first.request_id,
    )
    lease2 = claim_next(db, worker_id="source-pipeline")
    second = run_source_stages(db, lease2, source, archive, plan, build)
    assert second.publication and second.manifest
    assert rerun.request_id != first.request_id
    assert second.publication.batch_id != outcome.publication.batch_id
    assert len(calls) == 4
    assert archive.read(outcome.manifest) == archive.read_blob(
        outcome.manifest.blob_key, outcome.manifest.body_sha256, outcome.manifest.byte_count
    )
    assert (
        db.execute(
            "SELECT count(*) AS n FROM normalization_batches WHERE state='published' "
            "AND issuer_id=%s",
            (plan.issuer_id,),
        ).fetchone()["n"]
        == 2
    )
    assert (
        db.execute(
            "SELECT count(*) AS n FROM source_fetch_attempts WHERE state='complete'"
        ).fetchone()["n"]
        == 4
    )


def test_unreviewed_mapping_archives_sources_and_stops_with_explicit_input_gap(db, source_pipeline):
    source, archive, plan, _, calls, _, _, _ = source_pipeline
    lease = claim_next(db, worker_id="source-pipeline")
    outcome = run_source_stages(db, lease, source, archive, plan, lambda _: None)
    assert outcome.state == "waiting_for_input"
    assert outcome.gaps[-1] == "reviewed_mapping_required"
    assert len(calls) == 2
    assert (
        db.execute(
            "SELECT count(*) AS n FROM source_fetch_attempts WHERE state='complete'"
        ).fetchone()["n"]
        == 2
    )
    assert (
        db.execute(
            "SELECT count(*) AS n FROM normalization_batches WHERE state='published'"
        ).fetchone()["n"]
        == 0
    )
