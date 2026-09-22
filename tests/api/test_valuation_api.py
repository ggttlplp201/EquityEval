from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
from equity_api.valuation import create_app
from equity_ingest.valuation_pipeline import run_valuation_stage
from equity_schema.fundamentals_canonical import content_hash
from equity_schema.workflow import claim_next
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from tests.conftest import test_database_profile
from tests.integration.test_valuation_publication import setup, valuation_setup

assert valuation_setup and setup
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(test_database_profile() != "timescale-pg16", reason="S7 requires 0012"),
]


def client_for(dsn, workspace_id):
    @contextmanager
    def connections():
        with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as db:
            db.execute("SET ROLE equity_runtime")
            yield db

    return TestClient(create_app(workspace_id=workspace_id, connection_factory=connections))


def test_api_queued_request_saved_bytes_latest_and_workspace(
    test_database_dsn, db, valuation_setup, monkeypatch
):
    source, draft, review = valuation_setup
    client = client_for(test_database_dsn, source[0].workspace_id)
    body = dict(
        review_id=str(review),
        parent_request_id=str(source[3].request_id),
        idempotency_key="api-valuation",
        max_attempts=3,
    )
    response = client.post("/valuation-requests", json=body)
    assert response.status_code == 202, response.text
    assert response.json()["state"] == "queued"
    assert db.execute("SELECT count(*) n FROM valuation_model_runs").fetchone()["n"] == 0
    assert client.post("/valuation-requests", json=body).json() == response.json()
    lease = claim_next(db, worker_id="api-tracer", lease_seconds=3600)
    run_id = run_valuation_stage(db, lease)
    saved = client.get(f"/model-runs/{run_id}")
    assert saved.status_code == 200, saved.text
    assert saved.json()["result"]["bridge"]["market_ev_target"] == "193.43750"
    assert "private-fixture-author" not in saved.text
    assert "Private fictional rationale" not in saved.text
    import equity_core.valuation_payload as core

    def never(*args, **kwargs):
        raise AssertionError("Read recalculated")

    monkeypatch.setattr(core, "calculate_payload", never)
    assert client.get(f"/model-runs/{run_id}").content == saved.content
    assert client.get(f"/model-runs/{run_id}?extra=true").status_code == 422
    query = dict(
        security_id=str(draft.selector.security_id),
        quote_identifier_id=str(draft.selector.quote_identifier_id),
        scope_id=str(source[3].membership_id),
        compatibility_key=content_hash(draft),
    )
    url = f"/companies/{draft.selector.issuer_id}/valuation"
    assert client.get(url, params=query).json()["run"] == saved.json()
    assert client.get(url, params={**query, "compatibility_key": "0" * 64}).status_code == 404
    other = client_for(test_database_dsn, uuid4())
    assert other.get(f"/model-runs/{run_id}").status_code == 404
    assert other.get(f"/assumption-sets/{draft.assumption_set_id}").status_code == 404
    assert other.post("/valuation-requests", json=body).status_code == 404


def test_local_assumption_creation_revision_idempotency_and_no_backdating(
    test_database_dsn, valuation_setup
):
    source, draft, _ = valuation_setup
    client = client_for(test_database_dsn, source[0].workspace_id)
    content = draft.assumptions.model_copy(
        update={"authored_at": datetime.now(UTC), "retrospective": True}
    )
    body = dict(
        parent_id=str(draft.assumption_set_id),
        idempotency_key="new-judgment",
        content=content.model_dump(mode="json"),
    )
    result = client.post("/assumption-sets", json=body)
    assert result.status_code == 201, result.text
    assert result.json()["id"] != str(draft.assumption_set_id)
    assert client.post("/assumption-sets", json=body).json() == result.json()
    changed = {**body, "content": {**body["content"], "author_id": "changed"}}
    assert client.post("/assumption-sets", json=changed).status_code == 409
    old = {
        **body,
        "idempotency_key": "backdate",
        "content": draft.assumptions.model_dump(mode="json"),
    }
    assert client.post("/assumption-sets", json=old).status_code == 422
    assert client.get("/assumption-sets/" + result.json()["id"]).json() == result.json()


def test_generated_contract_has_only_explicit_routes_and_decimal_strings(
    test_database_dsn, valuation_setup
):
    client = client_for(test_database_dsn, valuation_setup[0][0].workspace_id)
    spec = client.get("/openapi.json").json()
    assert len(spec["paths"]) == 6
    assert (
        spec["components"]["schemas"]["BridgeResult"]["properties"]["market_ev_target"]["anyOf"][0][
            "type"
        ]
        == "string"
    )
    assert spec["components"]["schemas"]["SolveResult"]["properties"]["state"]["enum"] == [
        "converged",
        "no_solution_in_domain",
        "non_unique",
        "inconclusive",
        "unavailable",
    ]


def test_request_progress_and_failure_are_safe_public_projections(
    test_database_dsn, db, valuation_setup
):
    from equity_schema.workflow import finish_execution, finish_stage, start_stage

    from tests.integration.test_valuation_publication import enqueue

    request, lease = enqueue(db, valuation_setup)
    client = client_for(test_database_dsn, valuation_setup[0][0].workspace_id)
    url = f"/valuation-requests/{request.request_id}"
    stage = start_stage(db, lease, stage_key="valuation")
    running = client.get(url).json()
    assert (running["state"], running["stage_key"], running["stage_state"]) == (
        "running",
        "valuation",
        "running",
    )
    assert running["error_code"] is None
    private = "private worker detail private@example.invalid"
    finish_stage(db, lease, stage_id=stage, outcome="failed", reason=private)
    finish_execution(db, lease, outcome="failed", reason=private)
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["error_code"] == "worker_failure"
    assert response.json()["stage_state"] == "failed"
    assert "private" not in response.text
    assert client_for(test_database_dsn, uuid4()).get(url).status_code == 404
