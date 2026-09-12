"""The SEC Source normalizes verified local evidence only, with immutable capture identity."""

import gzip
import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from equity_ingest.archive import ArchiveError, LocalArchive
from equity_ingest.contracts import FetchResult, RawRecord, ResourceKind, SourceDescriptor
from equity_ingest.sec import SecSource

from tests.sec_normalization_seed import EVIDENCE, cohort_input


class Transport:
    def __init__(self, descriptor, archive):
        self.descriptor, self.archive = descriptor, archive
        self.result = FetchResult()
        self.calls = 0

    def fetch(self, request):
        self.calls += 1
        return self.result


@pytest.fixture
def reviewed_source(tmp_path):
    body, inputs = cohort_input("CRCL")
    archive = LocalArchive(tmp_path)
    records = []
    files = json.loads((EVIDENCE / "filing-manifest.json").read_text())["requests"]
    policy_id = uuid4()
    for capture in inputs.captures:
        if capture.id == inputs.companyfacts_capture_id:
            content = body
        else:
            file = next(item for item in files if item.get("raw_sha256") == capture.body_sha256)
            content = gzip.decompress((EVIDENCE / file["raw_file"]).read_bytes())
        stored = archive.write(
            [content],
            source_key="sec",
            source_object_key=capture.source_object_key,
            params_hash=hashlib.sha256(b"{}").hexdigest(),
            capture_id=capture.id,
            retrieved_at=capture.fetched_at,
            max_bytes=64 * 1024 * 1024,
        )
        records.append(
            RawRecord(
                capture.id,
                capture.source_id,
                capture.source_object_key,
                capture.request_url,
                hashlib.sha256(b"{}").hexdigest(),
                capture.fetched_at,
                capture.fetched_at,
                capture.completed_at,
                200,
                stored.body_sha256,
                stored.byte_count,
                stored.blob_key,
                "application/json" if capture.id == inputs.companyfacts_capture_id else "text/html",
                policy_id,
                "S1-reviewed",
            )
        )
    primary = next(
        record for record in records if record.capture_id == inputs.companyfacts_capture_id
    )
    descriptor = SourceDescriptor(
        primary.source_id,
        "sec",
        "SEC",
        policy_id,
        "S1-reviewed",
        "public",
        "allowed",
        tuple(ResourceKind),
        timedelta(minutes=15),
    )
    fetcher = Transport(descriptor, archive)
    source = SecSource(descriptor, fetcher, archive, trusted_records=tuple(records))
    return source, inputs, fetcher


def test_normalize_verified_all_captures_without_network_or_database(reviewed_source):
    source, inputs, fetcher = reviewed_source
    bundle = source.normalize(inputs)
    assert len(bundle.resolutions) == 40
    assert fetcher.calls == 0
    assert source.read_verified(inputs.companyfacts_capture_id).startswith(b'{"cik"')
    assert isinstance(source.records, tuple)


def test_corrupt_secondary_evidence_stops_before_numeric_normalizer(reviewed_source, monkeypatch):
    source, inputs, fetcher = reviewed_source
    secondary = next(
        record for record in source.records if record.capture_id != inputs.companyfacts_capture_id
    )
    (source.archive.root / secondary.blob_key).write_bytes(gzip.compress(b"changed filing"))
    monkeypatch.setattr(
        "equity_ingest.sec.normalize_verified_bytes",
        lambda *_: pytest.fail("must verify every capture"),
    )
    with pytest.raises(ArchiveError):
        source.normalize(inputs)
    assert fetcher.calls == 0


@pytest.mark.parametrize(
    "change", ["request_url", "body_sha256", "byte_count", "source_id", "completed_at"]
)
def test_input_manifest_cannot_change_registered_evidence(reviewed_source, change):
    source, inputs, _ = reviewed_source
    capture = inputs.captures[1]
    changed = {
        "request_url": "https://example.invalid/other",
        "body_sha256": "a" * 64,
        "byte_count": capture.byte_count + 1,
        "source_id": uuid4(),
        "completed_at": capture.completed_at + timedelta(seconds=1),
    }
    manipulated = replace(capture, **{change: changed[change]})
    with pytest.raises(ArchiveError, match="metadata"):
        source.normalize(replace(inputs, captures=(inputs.captures[0], manipulated)))


def test_missing_or_error_capture_cannot_supply_financial_evidence(reviewed_source):
    source, inputs, transport = reviewed_source
    primary = next(
        record for record in source.records if record.capture_id == inputs.companyfacts_capture_id
    )
    incomplete = SecSource(source.descriptor, transport, source.archive, trusted_records=(primary,))
    with pytest.raises(ArchiveError):
        incomplete.normalize(inputs)
    failed = SecSource(
        source.descriptor,
        transport,
        source.archive,
        trusted_records=(replace(primary, http_status=500),),
    )
    with pytest.raises(ArchiveError, match="unsuccessful"):
        failed.read_verified(primary.capture_id)
    with pytest.raises(ArchiveError, match="registry"):
        source.read_verified(uuid4())


def test_capture_registry_cannot_rebind_an_existing_id(reviewed_source):
    source, _, transport = reviewed_source
    original = source.records[0]
    transport.result = FetchResult(records=(original,))
    source.fetch(None)
    assert len(source.records) == 2
    transport.result = FetchResult(records=(replace(original, body_sha256="0" * 64),))
    with pytest.raises(ArchiveError, match="cannot change"):
        source.fetch(None)
    assert source.records[0] == original


def test_different_transport_policy_or_archive_cannot_be_substituted(reviewed_source, tmp_path):
    source, _, transport = reviewed_source
    with pytest.raises(ValueError, match="policy"):
        SecSource(replace(source.descriptor, policy_revision_id=uuid4()), transport, source.archive)
    with pytest.raises(ValueError, match="archive"):
        SecSource(source.descriptor, transport, LocalArchive(tmp_path / "other"))
