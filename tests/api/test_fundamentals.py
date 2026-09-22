"""HTTP contract: exact saved bytes, typed gaps, no defaults or cross-workspace reads."""

from contextlib import contextmanager
from uuid import uuid4

import psycopg
import pytest
from equity_api.fundamentals import create_app
from equity_schema.fundamentals_canonical import content_hash
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from tests.conftest import test_database_profile
from tests.integration.test_fundamentals_publication import publish, setup

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(test_database_profile() != "timescale-pg16", reason="S6 requires 0011"),
]
# Pytest imports the existing governed fixture; no second fixture graph.
assert setup


@pytest.fixture
def client(test_database_dsn, setup):
    @contextmanager
    def connections():
        with psycopg.connect(
            test_database_dsn, autocommit=True, row_factory=dict_row
        ) as connection:
            connection.execute("SET ROLE equity_runtime")
            yield connection

    app = create_app(workspace_id=setup[0].workspace_id, connection_factory=connections)
    return TestClient(app)


def test_known_snapshot_exact_latest_and_not_found(client, db, setup):
    snapshot_id = publish(db, setup)
    saved = client.get(f"/analysis-snapshots/{snapshot_id}")
    assert saved.status_code == 200
    assert saved.json()["result"]["metrics"][0]["value"] == "0.2"
    query = dict(
        security_id=str(setup[1].selector.security_id),
        compatibility_key=content_hash(setup[1].selector),
        scope_id=str(setup[3].membership_id),
    )
    url = f"/companies/{setup[1].selector.issuer_id}/fundamentals"
    latest = client.get(url, params=query)
    assert latest.status_code == 200
    assert latest.json()["snapshot"] == saved.json()
    assert client.get(url).status_code == 422
    assert client.get(url, params={**query, "compatibility_key": "f" * 64}).json() == {
        "code": "no_compatible_snapshot",
        "message": "N/A",
    }
    assert client.get(url, params={**query, "scope_id": str(uuid4())}).status_code == 404
    assert client.get(url, params={**query, "unexpected": "true"}).status_code == 422
    assert (
        client.get(f"/analysis-snapshots/{snapshot_id}", params={"as_of": "2026-09-22"}).status_code
        == 422
    )
    assert isinstance(
        client.get(f"/analysis-snapshots/{snapshot_id}", params={"extra": "value"}).json()[
            "detail"
        ],
        list,
    )
    assert client.get(f"/analysis-snapshots/{uuid4()}").json() == {
        "code": "snapshot_not_found",
        "message": "N/A",
    }
    assert client.post(url, json={}).status_code == 405
    assert "manifest_text" not in saved.text
    assert "reviewed_by" not in saved.text
    assert "test-only/fixture.json.gz" not in saved.text
    assert client.get(f"/analysis-snapshots/{snapshot_id}").content == saved.content


def test_workspace_cannot_be_overridden_by_caller(test_database_dsn, setup, db):
    snapshot_id = publish(db, setup)

    @contextmanager
    def connections():
        with psycopg.connect(
            test_database_dsn, autocommit=True, row_factory=dict_row
        ) as connection:
            connection.execute("SET ROLE equity_runtime")
            yield connection

    client = TestClient(create_app(workspace_id=uuid4(), connection_factory=connections))
    assert client.get(f"/analysis-snapshots/{snapshot_id}").status_code == 404
    assert (
        client.get(
            f"/analysis-snapshots/{snapshot_id}",
            params={"workspace_id": str(setup[0].workspace_id)},
        ).status_code
        == 422
    )


def test_openapi_status_decimal_and_required_selection_contract(client):
    contract = client.get("/openapi.json").json()
    metric = contract["components"]["schemas"]["PublicMetric"]["properties"]
    assert set(metric["status"]["enum"]) == {
        "valid",
        "not_meaningful",
        "missing",
        "invalid",
        "stale",
        "unsupported",
        "inapplicable",
    }
    assert metric["value"]["anyOf"][0]["type"] == "string"
    params = contract["paths"]["/companies/{issuer_id}/fundamentals"]["get"]["parameters"]
    assert all(p["required"] for p in params)
    assert set(contract["paths"]) == {
        "/companies/{issuer_id}/fundamentals",
        "/analysis-snapshots/{snapshot_id}",
    }
