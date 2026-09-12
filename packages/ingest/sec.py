"""SEC Source boundary: fetched evidence becomes a pinned, verified local registry."""

from uuid import UUID

from equity_ingest.archive import ArchiveError, LocalArchive
from equity_ingest.contracts import (
    FetchRequest,
    FetchResult,
    RawRecord,
    ResourceKind,
    SecResource,
    SourceDescriptor,
)
from equity_ingest.financial_types import NormalizationBundle, NormalizationInput
from equity_ingest.sec_normalize import normalize_verified_bytes
from equity_ingest.transport import SecTransport


class SecSource:
    """Network work lives in fetch; normalization reads only explicitly registered archives.

    Historical records supplied by the caller must already be trusted metadata
    references (e.g. read from the evidence database). Constructor registration
    cannot make an unreviewed claim authoritative. Every read still verifies bytes.
    """

    def __init__(
        self,
        descriptor: SourceDescriptor,
        transport: SecTransport,
        archive: LocalArchive,
        *,
        trusted_records: tuple[RawRecord, ...] = (),
    ) -> None:
        if transport.descriptor != descriptor:
            raise ValueError("SEC source and transport must use the same source policy")
        if transport.archive.root != archive.root:
            raise ValueError("SEC source and transport must use the same archive store")
        self.descriptor = descriptor
        self.transport = transport
        self.archive = archive
        self._records: dict[UUID, RawRecord] = {}
        self._register(trusted_records)

    @property
    def records(self) -> tuple[RawRecord, ...]:
        return tuple(self._records.values())

    def _register(self, records: tuple[RawRecord, ...]) -> None:
        staged: dict[UUID, RawRecord] = {}
        for record in records:
            previous = staged.get(record.capture_id, self._records.get(record.capture_id))
            if previous is not None and previous != record:
                raise ArchiveError("A registered capture identity cannot change metadata")
            staged[record.capture_id] = record
        self._records.update(staged)

    def fetch(self, request: FetchRequest) -> FetchResult:
        result = self.transport.fetch(request)
        self._register(result.records)
        return result

    def read_verified(self, capture_id: UUID) -> bytes:
        try:
            record = self._records[capture_id]
        except KeyError as error:
            raise ArchiveError("Capture is not in the pinned source registry") from error
        if not record.successful:
            raise ArchiveError("An unsuccessful HTTP response cannot supply financial evidence")
        return self.archive.read_blob(record.blob_key, record.body_sha256, record.byte_count)

    def normalize(self, inputs: NormalizationInput) -> NormalizationBundle:
        primary = self._records.get(inputs.companyfacts_capture_id)
        expected = SecResource(inputs.issuer_id, inputs.cik, ResourceKind.COMPANY_FACTS)
        if (
            primary is None
            or primary.source_id != self.descriptor.source_id
            or primary.request_url != expected.url
        ):
            raise ArchiveError("Company Facts evidence does not match this SEC issuer/source")
        selected_body: bytes | None = None
        for evidence in inputs.captures:
            record = self._records.get(evidence.id)
            if record is None or (
                evidence.source_id != record.source_id
                or evidence.source_object_key != record.source_object_key
                or evidence.request_url != record.request_url
                or evidence.body_sha256 != record.body_sha256
                or evidence.byte_count != record.byte_count
                or evidence.fetched_at != record.fetched_at
                or evidence.completed_at != record.completed_at
            ):
                raise ArchiveError(
                    "Normalization evidence metadata differs from its pinned capture"
                )
            body = self.read_verified(evidence.id)
            if evidence.id == inputs.companyfacts_capture_id:
                selected_body = body
        if selected_body is None:
            raise ArchiveError("Company Facts capture is missing from the normalization manifest")
        return normalize_verified_bytes(selected_body, inputs)
