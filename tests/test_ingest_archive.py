"""Archive boundaries: bytes are evidence, decoded exactly once and never partial."""

import gzip
import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from equity_ingest.archive import (
    ArchiveError,
    BodyLimitExceeded,
    ContentDecodingError,
    LocalArchive,
    TransferIncomplete,
)


def write(archive, chunks, **kwargs):
    return archive.write(
        chunks,
        source_key="sec",
        source_object_key="companyfacts/0000320193",
        params_hash=hashlib.sha256(b"{}").hexdigest(),
        capture_id=uuid4(),
        retrieved_at=datetime(2026, 9, 12, tzinfo=UTC),
        max_bytes=kwargs.pop("max_bytes", 1024),
        **kwargs,
    )


def test_archive_hashes_literal_decoded_bytes_and_replays_once(tmp_path):
    archive = LocalArchive(tmp_path)
    body = b'{"val":1.2300e+4}\r\n'
    wire = gzip.compress(body)
    result = write(archive, [wire[:7], wire[7:]], content_encoding="gzip")
    assert result.body_sha256 == hashlib.sha256(body).hexdigest()
    assert result.byte_count == len(body)
    assert archive.read(result) == body
    assert gzip.decompress((tmp_path / result.blob_key).read_bytes()) == body


def test_archive_preserves_existing_gzip_entity_without_double_decode(tmp_path):
    archive = LocalArchive(tmp_path)
    entity = gzip.compress(b"already a gzip file")
    result = write(archive, [entity], content_encoding="identity")
    assert archive.read(result) == entity


@pytest.mark.parametrize("encoding", ["br", "gzip, deflate"])
def test_unsupported_encodings_never_publish(tmp_path, encoding):
    with pytest.raises(ContentDecodingError):
        write(LocalArchive(tmp_path), [b"x"], content_encoding=encoding)
    assert not list(tmp_path.rglob("*.gz"))


@pytest.mark.parametrize("body", [b"not gzip", gzip.compress(b"hello")[:-3]])
def test_malformed_or_truncated_gzip_never_publish(tmp_path, body):
    with pytest.raises(ContentDecodingError):
        write(LocalArchive(tmp_path), [body], content_encoding="gzip")
    assert not list(tmp_path.rglob("*.gz"))


def test_decoded_limit_stops_compression_bomb_without_publish(tmp_path):
    with pytest.raises(BodyLimitExceeded):
        write(
            LocalArchive(tmp_path),
            [gzip.compress(b"a" * 100000)],
            content_encoding="gzip",
            max_bytes=100,
        )
    assert not list(tmp_path.rglob("*.gz"))


def test_interrupted_transfer_and_length_mismatch_do_not_publish(tmp_path):
    def chunks():
        yield b"partial"
        raise OSError("connection reset")

    with pytest.raises(OSError):
        write(LocalArchive(tmp_path), chunks())
    with pytest.raises(TransferIncomplete):
        write(LocalArchive(tmp_path), [b"abc"], expected_wire_bytes=4)
    assert not list(tmp_path.rglob("*.gz"))


def test_corrupt_archive_and_escape_fail_closed(tmp_path):
    archive = LocalArchive(tmp_path)
    result = write(archive, [b"evidence"])
    (tmp_path / result.blob_key).write_bytes(gzip.compress(b"changed"))
    with pytest.raises(ArchiveError):
        archive.read(result)
    with pytest.raises(ArchiveError):
        archive.read_blob("../outside.gz", result.body_sha256, result.byte_count)


def test_zero_body_and_deadline_callback(tmp_path):
    archive = LocalArchive(tmp_path)
    result = write(archive, [b""])
    assert archive.read(result) == b""

    def deadline():
        raise TimeoutError("deadline")

    with pytest.raises(TimeoutError):
        write(archive, [b"x"], check_deadline=deadline)
    assert len(list(tmp_path.rglob("*.gz"))) == 1
