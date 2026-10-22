"""D051 transfer evidence fits existing SQL audit and immutable outcome guards."""

import json
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import httpx
from equity_ingest.contracts import FetchRequest, ResourceKind, SecResource, SourceDescriptor
from equity_ingest.pdf_transfer import ARS_KEY, recover_transfer
from equity_ingest.transport import DatabaseAttemptStore, SecTransport
from equity_schema.crcl_history import CRCL_HISTORY_VERSION
from equity_schema.workflow import claim_source_bootstrap, start_stage

from tests.integration.test_source_bootstrap import (  # noqa: F401
    bootstrap_plan,
    enqueue,
    pytestmark,
)
from tests.integration.test_source_bootstrap import identity as fixture_identity
from tests.test_ingest_transport import Clock, Limiter, response

identity = fixture_identity


def test_complete_ars_persists_counter_audit_without_schema_change(db, identity, tmp_path):
    from equity_ingest.archive import LocalArchive

    base = bootstrap_plan(db, identity)
    plan = replace(base, version=CRCL_HISTORY_VERSION, resources=(*base.resources, ARS_KEY))
    enqueue(db, identity, plan=plan)
    lease = claim_source_bootstrap(db, worker_id="d051-audit")
    stage = start_stage(db, lease, stage_key="sec_fetch_" + "a" * 24)
    policy = db.execute(
        "SELECT * FROM source_policy_revisions WHERE id=%s", (plan.policy_revision_id,)
    ).fetchone()
    descriptor = SourceDescriptor(
        plan.source_id,
        str(plan.source_id),
        "Fictional test SEC",
        plan.policy_revision_id,
        policy["review_key"],
        policy["licence_label"],
        policy["redistribution_status"],
        tuple(ResourceKind),
        timedelta(minutes=15),
    )
    resource = SecResource(
        identity[1],
        "1876042",
        ResourceKind.FILING_DOCUMENT,
        "a2025annualreport0331.pdf",
        "0001876042-26-000116",
    )
    request = FetchRequest(uuid4(), resource, lease, stage)
    archive = LocalArchive(tmp_path)
    body = b"%PDF-1.7\n" + b" " * (9 * 1024 * 1024) + b"\n%%EOF"
    clock = Clock()
    client = SecTransport(
        descriptor,
        archive,
        Limiter(clock),
        DatabaseAttemptStore(db, descriptor),
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _: response(
                    body=body,
                    headers={"Content-Type": "application/pdf", "Content-Length": str(len(body))},
                )
            )
        ),
        "test@example.invalid",
    )
    result = client.fetch(request)
    assert result.usable
    attempt = result.attempts[0].attempt_id
    row = db.execute(
        "SELECT state,failure_detail,completed_capture_id FROM source_fetch_attempts WHERE id=%s",
        (attempt,),
    ).fetchone()
    detail = json.loads(row["failure_detail"])
    recovered = recover_transfer(tmp_path / "pdf-transfer", attempt)
    assert recovered.pop("status") == "terminal_pending_database_verification"
    assert recovered == detail
    assert detail["captureId"] == str(row["completed_capture_id"])
    assert detail["outcome"] == row["state"] == "complete"
    assert detail["wireBytesObserved"] == detail["decodedBytesEmitted"] == len(body)
