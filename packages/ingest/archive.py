"""Verified, immutable local archives of HTTP entity bytes, before financial parsing."""

import gzip
import hashlib
import os
import re
import tempfile
import zlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID


class ArchiveError(RuntimeError):
    """A complete, reproducible archive could not be established."""


class BodyLimitExceeded(ArchiveError):
    """An explicit wire or decoded-body limit was exceeded."""


class ContentDecodingError(ArchiveError):
    """HTTP compression is unsupported, invalid, or incomplete."""


class TransferIncomplete(ArchiveError):
    """A declared complete response body was not fully received."""


@dataclass(frozen=True)
class ArchivedBody:
    blob_key: str
    body_sha256: str
    byte_count: int


class LocalArchive:
    """Archive keys are relative paths; neither source URLs nor caller paths are opened."""

    def __init__(self, root: Path) -> None:
        self.root = root.absolute()
        if self.root.is_symlink():
            raise ArchiveError("Archive root must not be a symlink")
        self.root.mkdir(parents=True, exist_ok=True)
        self.root = self.root.resolve()

    def _path(self, blob_key: str) -> Path:
        relative = Path(blob_key)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ArchiveError("Invalid archive key")
        current = self.root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ArchiveError("Archive paths must not contain symlinks")
        if not current.resolve().is_relative_to(self.root):
            raise ArchiveError("Archive key leaves the configured root")
        return current

    def write(
        self,
        chunks: Iterable[bytes],
        *,
        source_key: str,
        source_object_key: str,
        params_hash: str,
        capture_id: UUID,
        retrieved_at: datetime,
        max_bytes: int,
        content_encoding: str | None = None,
        expected_wire_bytes: int | None = None,
        check_deadline: Callable[[], None] | None = None,
    ) -> ArchivedBody:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", source_key):
            raise ValueError("Invalid archive source key")
        if not re.fullmatch(r"[a-f0-9]{64}", params_hash) or not source_object_key:
            raise ValueError("Explicit source object and parameter hash required")
        if retrieved_at.utcoffset() is None or max_bytes < 0:
            raise ValueError("Archive requires an aware retrieval time and finite body limit")
        if expected_wire_bytes is not None and expected_wire_bytes < 0:
            raise ValueError("Invalid Content-Length")
        encoding = (content_encoding or "identity").strip().lower()
        if encoding not in {"identity", "gzip", "deflate"}:
            raise ContentDecodingError("Unsupported HTTP Content-Encoding")
        decoder = (
            None if encoding == "identity" else zlib.decompressobj(31 if encoding == "gzip" else 15)
        )
        object_hash = hashlib.sha256(source_object_key.encode()).hexdigest()
        stamp = retrieved_at.strftime("%Y%m%dT%H%M%S%f%z")
        key = f"{source_key}/{object_hash}/{params_hash}/{stamp}-{capture_id}.gz"
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        checksum = hashlib.sha256()
        count = wire_count = 0
        fd, temporary_name = tempfile.mkstemp(prefix=".partial-", dir=target.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as output:
                with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as archive:
                    for chunk in chunks:
                        if check_deadline:
                            check_deadline()
                        wire_count += len(chunk)
                        if wire_count > max_bytes * 2 + 65536:
                            raise BodyLimitExceeded("Wire-body limit exceeded")
                        pending = chunk
                        while pending:
                            if decoder is None:
                                decoded, pending = pending, b""
                            else:
                                try:
                                    decoded = decoder.decompress(pending, max_bytes - count + 1)
                                except zlib.error as exc:
                                    raise ContentDecodingError("Malformed HTTP encoding") from exc
                                pending = decoder.unconsumed_tail
                                if decoder.unused_data:
                                    raise ContentDecodingError("Trailing HTTP compressed data")
                            count += len(decoded)
                            if count > max_bytes:
                                raise BodyLimitExceeded("Decoded-body limit exceeded")
                            checksum.update(decoded)
                            archive.write(decoded)
                    if check_deadline:
                        check_deadline()
                    if decoder is not None and not decoder.eof:
                        raise ContentDecodingError("Incomplete HTTP compressed body")
                    if expected_wire_bytes is not None and wire_count != expected_wire_bytes:
                        raise TransferIncomplete("Content-Length does not match received bytes")
                output.flush()
                os.fsync(output.fileno())
            result = ArchivedBody(key, checksum.hexdigest(), count)
            # Verify the complete gzip before a key can be published to database callers.
            self._read_path(temporary, result.body_sha256, count)
            os.link(temporary, target)  # Exclusive publication; never overwrite an existing key.
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return result
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _read_path(path: Path, body_sha256: str, byte_count: int) -> bytes:
        if byte_count < 0 or not re.fullmatch(r"[a-f0-9]{64}", body_sha256):
            raise ArchiveError("Invalid archive verification metadata")
        checksum = hashlib.sha256()
        parts = []
        count = 0
        try:
            with gzip.open(path, "rb") as source:
                while chunk := source.read(min(65536, byte_count - count + 1)):
                    count += len(chunk)
                    if count > byte_count:
                        raise ArchiveError("Archive byte count mismatch")
                    checksum.update(chunk)
                    parts.append(chunk)
        except (OSError, EOFError, zlib.error) as exc:
            raise ArchiveError("Archive is missing or corrupt") from exc
        if count != byte_count or checksum.hexdigest() != body_sha256:
            raise ArchiveError("Archive hash or byte count mismatch")
        return b"".join(parts)

    def read_blob(self, blob_key: str, body_sha256: str, byte_count: int) -> bytes:
        return self._read_path(self._path(blob_key), body_sha256, byte_count)

    def read(self, body: ArchivedBody) -> bytes:
        return self.read_blob(body.blob_key, body.body_sha256, body.byte_count)

    def verify(self, body: ArchivedBody) -> None:
        self.read(body)
