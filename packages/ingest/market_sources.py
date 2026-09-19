"""Typed adapters bind complete archives to exact public resource parameters."""

from .contracts import FetchResult, RawRecord
from .market_normalize import normalize_fred, normalize_tiingo, normalize_treasury
from .market_types import FredPage, MarketNormalizationBundle, MarketNormalizationInput
from .provider_contracts import (
    FredResource,
    PriceResource,
    ProviderFetchRequest,
    ProviderKind,
    ProviderResource,
    TreasuryResource,
)
from .provider_transport import ProviderTransport


class MarketSource:
    def __init__(self, transport: ProviderTransport) -> None:
        self.transport = transport
        self.descriptor = transport.descriptor
        self._fetched: dict[object, tuple[ProviderResource, RawRecord]] = {}

    def fetch(self, request: ProviderFetchRequest[ProviderResource]) -> FetchResult:
        result = self.transport.fetch(request)
        for record in result.successful_records:
            self._fetched[record.capture_id] = (request.resource, record)
        return result

    def read_verified(self, record: RawRecord) -> bytes:
        return self.transport.read_verified(record)

    def normalize(
        self,
        inputs: MarketNormalizationInput,
        *,
        resources: tuple[ProviderResource, ...] = (),
        records: tuple[RawRecord, ...] = (),
    ) -> MarketNormalizationBundle:
        observations = tuple(c for c in inputs.captures if c.role == "observations")
        if not resources and not records:
            pinned = [self._fetched[c.id] for c in observations if c.id in self._fetched]
            resources, records = tuple(p[0] for p in pinned), tuple(p[1] for p in pinned)
        if not records or len(records) != len(resources):
            raise ValueError("Exact observation resources and captures required")
        if {c.id for c in observations} != {r.capture_id for r in records}:
            raise ValueError("Observation captures differ from pinned inputs")
        if len({r.capture_id for r in records}) != len(records):
            raise ValueError("Duplicate observation captures")
        if (
            inputs.source_id != self.descriptor.source_id
            or inputs.policy_revision_id != self.descriptor.policy_revision_id
        ):
            raise ValueError("Normalization differs from source policy")
        bodies = []
        for resource, record in zip(resources, records, strict=True):
            if (
                resource.provider != self.descriptor.provider
                or record.source_id != inputs.source_id
                or record.policy_revision_id != inputs.policy_revision_id
                or record.source_object_key != resource.object_key
                or record.request_url != resource.url
                or record.request_params_hash != resource.params_hash
                or not record.successful
            ):
                raise ValueError("Capture differs from exact provider resource/policy")
            bodies.append(self.read_verified(record))
        if self.descriptor.provider == ProviderKind.TREASURY:
            resource = resources[0]
            if (
                len(resources) != 1
                or not isinstance(resource, TreasuryResource)
                or resource.month != inputs.treasury_month
            ):
                raise ValueError("Treasury normalization must pin the fetched month")
            return normalize_treasury(bodies[0], inputs)
        if self.descriptor.provider == ProviderKind.TIINGO:
            resource = resources[0]
            binding = inputs.quote_binding
            if (
                len(resources) != 1
                or not isinstance(resource, PriceResource)
                or binding is None
                or resource.quote_identifier_id != binding.quote_identifier_id
                or resource.security_id != binding.security_id
                or resource.provider_symbol != binding.provider_symbol
                or (resource.start, resource.end) != (inputs.requested_start, inputs.requested_end)
            ):
                raise ValueError("Price normalization must pin the fetched quote and window")
            return normalize_tiingo(bodies[0], inputs)
        pages = []
        for resource, record, body in zip(resources, records, bodies, strict=True):
            definition = inputs.series_definition
            if (
                not isinstance(resource, FredResource)
                or definition is None
                or resource.series_id != definition.source_series_key
                or (resource.start, resource.end) != (inputs.requested_start, inputs.requested_end)
                or (
                    inputs.source_as_of_date is not None
                    and resource.source_as_of != inputs.source_as_of_date
                )
            ):
                raise ValueError("FRED normalization must pin the fetched series/window/vintage")
            pages.append(
                FredPage(
                    record.capture_id,
                    body,
                    resource.series_id,
                    resource.start,
                    resource.end,
                    resource.source_as_of,
                    resource.source_as_of,
                    resource.offset,
                    resource.limit,
                )
            )
        return normalize_fred(tuple(pages), inputs)
