"""Crash recovery reads the original intent and never retries committed work."""

import copy
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from equity_ingest.contracts import FetchRequest, ResourceKind, SecResource
from equity_ingest.pipeline import run_source_bootstrap
from equity_schema.workflow import claim_source_bootstrap, enqueue_source_bootstrap, start_stage

from scripts.capture_crcl_history import PREFIX, SCOPE_SHA, checked_scope, group_plan
from scripts.publish_crcl_normalization import rows_snapshot
from scripts.recover_crcl_history import reconstruct
from tests.integration.test_source_bootstrap import (
    bootstrap_plan,
    pytestmark,  # noqa: F401
)
from tests.integration.test_source_bootstrap import (
    identity as fixture_identity,
)
from tests.integration.test_source_bootstrap import (
    transport as fixture_transport,
)

identity = fixture_identity
transport = fixture_transport


def intent_for(db_admin, db, identity):
    base = bootstrap_plan(db, identity)
    ids = {
        "issuer": identity[1],
        "security": identity[2],
        "workspace": identity[0].workspace_id,
        "source": base.source_id,
        "policy": base.policy_revision_id,
    }
    return {
        "scopeSha256": SCOPE_SHA,
        "proposal": "dd2d4a9",
        "groups": [],
        "financialPublication": False,
        "beforeRows": rows_snapshot(db_admin),
        "identities": {k: str(v) for k, v in ids.items()},
        "plans": [group_plan(ids, g).as_json() for g in checked_scope()["groups"]],
    }, ids


def request_group(db, ids, number):
    plan = group_plan(ids, checked_scope()["groups"][number - 1])
    request = enqueue_source_bootstrap(
        db,
        workspace_id=ids["workspace"],
        security_id=ids["security"],
        idempotency_key=f"{PREFIX}-{number}",
        plan=plan,
        max_attempts=1,
    )
    lease = claim_source_bootstrap(db, worker_id="recovery-fixture", request_id=request.request_id)
    return plan, lease


def test_committed_group_recovered_without_new_request_or_http(db_admin, db, identity, transport):
    source, archive, calls = transport
    intent, ids = intent_for(db_admin, db, identity)
    plan, lease = request_group(db, ids, 11)
    assert run_source_bootstrap(db, lease, source, archive, plan).state == "completed"
    before = rows_snapshot(db_admin)
    dispatches = len(calls)
    report = reconstruct(db_admin, intent, archive)
    assert report["status"] == "incomplete"
    assert report["originalRowsPreserved"]
    assert len(report["groups"]) == 1 and len(report["groups"][0]["captures"]) == 2
    assert len(report["missingResources"]) == 67
    assert reconstruct(db_admin, intent, archive) == report
    assert rows_snapshot(db_admin) == before and len(calls) == dispatches
    changed = copy.deepcopy(intent)
    changed["plans"][-1]["inventory_end"] = "2026-10-17"
    with pytest.raises(ValueError, match="intent plans"):
        reconstruct(db_admin, changed, archive)


def test_dispatch_without_completion_remains_unknown_and_is_not_retried(
    db_admin, db, identity, transport
):
    source, archive, calls = transport
    intent, ids = intent_for(db_admin, db, identity)
    _, lease = request_group(db, ids, 11)
    stage = start_stage(db, lease, stage_key="sec_fetch_" + "f" * 24)
    resource = SecResource(ids["issuer"], "1876042", ResourceKind.COMPANY_FACTS)
    fetch = FetchRequest(uuid4(), resource, lease, stage)
    store = source.transport.attempts
    attempt = store.prepare(fetch, 1, resource.url, None)
    store.dispatched(fetch, attempt, datetime.now(UTC))
    before = rows_snapshot(db_admin)
    report = reconstruct(db_admin, intent, archive)
    assert report["status"] == "incomplete" and len(report["missingResources"]) == 69
    assert report["retainedAttemptEvidence"][0]["state"] == "in_progress"
    assert report["groups"][0]["result"]["gaps"] == ["acquisition_completion_unavailable"]
    assert report["originalRowsPreserved"] and not calls
    assert rows_snapshot(db_admin) == before
