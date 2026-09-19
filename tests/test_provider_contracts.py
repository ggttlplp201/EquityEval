"""Public resource identity and capture cutoffs, before any provider implementation."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from equity_ingest.contracts import RawRecord
from equity_ingest.provider_contracts import (
    FredResource,
    PriceResource,
    ProviderFetchRequest,
    TreasuryResource,
)
from equity_schema.workflow import Lease


def test_treasury_uses_exact_month_and_distinct_public_request_hash():
    resource = TreasuryResource("202609")
    assert resource.object_key == "daily_treasury_yield_curve"
    assert resource.url.startswith("https://home.treasury.gov/")
    assert dict(resource.params)["field_tdr_date_value_month"] == "202609"
    assert resource.params_hash != TreasuryResource("202608").params_hash


@pytest.mark.parametrize("month", ["20269", "202600", "202613", "../202609", "000009", True])
def test_treasury_month_is_bounded_identity_not_arbitrary_url(month):
    with pytest.raises(ValueError):
        TreasuryResource(month)


def test_price_identity_pins_quote_and_explicit_bounds():
    resource = PriceResource(uuid4(), uuid4(), "BRK.B", date(2024, 1, 1), date(2024, 1, 31))
    assert resource.object_key == "tiingo_eod/BRK.B"
    assert resource.url == "https://api.tiingo.com/tiingo/daily/BRK.B/prices"
    assert dict(resource.params) == {
        "startDate": "2024-01-01",
        "endDate": "2024-01-31",
        "format": "json",
    }
    with pytest.raises(ValueError):
        replace(resource, provider_symbol="../A")
    with pytest.raises(ValueError):
        replace(resource, start=date(2024, 2, 1))


def test_fred_requires_explicit_native_vintage_and_pagination():
    resource = FredResource("DGS10", date(2024, 1, 1), date(2024, 1, 31), date(2024, 2, 1))
    params = dict(resource.params)
    assert params["realtime_start"] == params["realtime_end"] == "2024-02-01"
    assert params["units"] == "lin" and params["output_type"] == "1"
    assert "frequency" not in params and "api_key" not in params
    assert replace(resource, offset=100000).params_hash != resource.params_hash
    with pytest.raises(ValueError):
        replace(resource, series_id="DGS10&api_key=secret")


def test_historical_local_capture_cutoff_requires_explicit_replay():
    now = datetime(2026, 9, 12, tzinfo=UTC)
    resource = TreasuryResource("202609")
    lease = Lease(uuid4(), uuid4(), 1, 1, "test", now + timedelta(minutes=10))
    request = ProviderFetchRequest(uuid4(), resource, lease, uuid4())
    with pytest.raises(ValueError):
        replace(request, retrieval_cutoff=now)
    record = RawRecord(
        uuid4(),
        uuid4(),
        resource.object_key,
        resource.url,
        resource.params_hash,
        now,
        now,
        now,
        200,
        "a" * 64,
        0,
        "test.gz",
        "text/xml",
        uuid4(),
        "fictional",
    )
    replay = replace(
        request,
        cache_mode="replay",
        lease=None,
        stage_id=None,
        replay_records=(record,),
        retrieval_cutoff=now,
    )
    assert replay.replay_records == (record,)
    with pytest.raises(ValueError):
        replace(replay, retrieval_cutoff=now - timedelta(seconds=1))
    with pytest.raises(ValueError):
        replace(replay, resource=TreasuryResource("202608"))
