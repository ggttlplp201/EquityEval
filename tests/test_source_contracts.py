"""Resolved source identity and replay guards precede live provider work."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from equity_ingest.contracts import FetchRequest, ResourceKind, SecResource, canonical_cik


@pytest.mark.parametrize(
    "value", [True, False, 0, -1, 1.0, "+123", " 123", "１２３", "12345678901"]
)
def test_invalid_cik_is_never_silently_normalized(value):
    with pytest.raises(ValueError):
        canonical_cik(value)


def test_sec_resource_resolves_identity_and_uses_fixed_endpoint():
    assert canonical_cik("0001876042") == "0001876042"
    assert canonical_cik(1876042) == "0001876042"
    resource = SecResource(uuid4(), "0000320193", ResourceKind.COMPANY_FACTS)
    assert resource.url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
    assert resource.object_key == "company_facts/0000320193"


@pytest.mark.parametrize(
    "name", ["../x.json", "https://evil.example/x.json", "x%2f.json", "other.json"]
)
def test_history_filename_cannot_escape_issuer(name):
    with pytest.raises(ValueError):
        SecResource(uuid4(), "0000320193", ResourceKind.SUBMISSIONS_HISTORY, filename=name)


def test_live_fetch_requires_an_active_execution_context():
    resource = SecResource(uuid4(), "0000320193", ResourceKind.COMPANY_FACTS)
    with pytest.raises(ValueError, match="lease"):
        FetchRequest(uuid4(), resource, None, None)


def test_replay_cannot_be_disguised_as_a_new_historical_fetch():
    from equity_schema.workflow import Lease

    resource = SecResource(uuid4(), "0000320193", ResourceKind.COMPANY_FACTS)
    lease = Lease(uuid4(), uuid4(), 1, 1, "worker", datetime.now(UTC) + timedelta(minutes=1))
    with pytest.raises(ValueError, match="replay"):
        FetchRequest(
            uuid4(), resource, lease, uuid4(), retrieval_cutoff=datetime(2020, 1, 1, tzinfo=UTC)
        )
