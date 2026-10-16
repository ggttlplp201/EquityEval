"""New real endpoints are explicit and never alias synthetic clients."""

from contextlib import contextmanager
from uuid import uuid4

from fastapi.testclient import TestClient


def test_new_read_routes_have_no_quote_or_scope_defaults():
    from equity_api.real_fundamentals import create_app

    @contextmanager
    def unavailable():
        raise AssertionError("Invalid selectors must not query storage")
        yield

    client = TestClient(create_app(workspace_id=uuid4(), connection_factory=unavailable))
    url = f"/v2/companies/{uuid4()}/real-fundamentals"
    assert client.get(url).status_code == 422
    assert (
        client.get(
            url,
            params={
                "security_id": str(uuid4()),
                "compatibility_key": "a" * 64,
                "quote_identifier_id": str(uuid4()),
            },
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/v2/real-fundamentals/snapshots/{uuid4()}", params={"scope_id": str(uuid4())}
        ).status_code
        == 422
    )
    assert client.get(f"/analysis-snapshots/{uuid4()}").status_code == 404
    assert client.post(url, json={}).status_code == 405
