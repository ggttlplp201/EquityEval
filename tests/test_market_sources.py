"""Resource-to-body binding tests; provider replies are fictional."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from equity_ingest.contracts import RawRecord
from equity_ingest.market_sources import MarketSource
from equity_ingest.provider_contracts import ProviderDescriptor, ProviderKind, TreasuryResource

from tests.test_market_normalize import market_input, treasury_xml


class Transport:
    def __init__(self, inputs, body):
        self.descriptor = ProviderDescriptor(
            inputs.source_id,
            "fixture",
            "Fixture",
            inputs.policy_revision_id,
            "test-only",
            "fictional",
            "unknown",
            ProviderKind.TREASURY,
            timedelta(hours=1),
        )
        self.body = body

    def read_verified(self, record):
        return self.body


def setup_source():
    body = treasury_xml()
    inputs = market_input(body)
    resource = TreasuryResource("202609")
    capture = replace(inputs.captures[0], request_url=resource.url)
    inputs = replace(inputs, captures=(capture, inputs.captures[1]))
    record = RawRecord(
        capture.id,
        capture.source_id,
        capture.source_object_key,
        capture.request_url,
        resource.params_hash,
        capture.fetched_at,
        capture.fetched_at,
        capture.completed_at,
        200,
        capture.body_sha256,
        capture.byte_count,
        "fixture.gz",
        None,
        inputs.policy_revision_id,
        "test-only",
    )
    return MarketSource(Transport(inputs, body)), inputs, resource, record


def test_resource_params_bound_before_normalizing():
    source, inputs, resource, record = setup_source()
    bundle = source.normalize(inputs, resources=(resource,), records=(record,))
    assert str(bundle.macros[0].value) == "4.2500"
    for wrong in (
        replace(record, request_params_hash="0" * 64),
        replace(record, source_id=uuid4()),
        replace(record, policy_revision_id=uuid4()),
    ):
        with pytest.raises(ValueError):
            source.normalize(inputs, resources=(resource,), records=(wrong,))


def test_same_body_cannot_be_relabelled_as_another_month():
    source, inputs, _, record = setup_source()
    wrong = TreasuryResource("202608")
    record = replace(record, request_params_hash=wrong.params_hash)
    with pytest.raises(ValueError):
        source.normalize(inputs, resources=(wrong,), records=(record,))


def test_only_pinned_observation_capture_can_supply_body():
    source, inputs, resource, record = setup_source()
    with pytest.raises(ValueError):
        source.normalize(
            inputs, resources=(resource,), records=(replace(record, capture_id=uuid4()),)
        )
