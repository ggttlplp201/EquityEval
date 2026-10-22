"""D051 exact-PDF admission and crash-honest local transfer evidence."""

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from equity_schema.crcl_history import CRCL_HISTORY_PDFS

ARS_KEY = "filing_document/0001876042/0001876042-26-000116/a2025annualreport0331.pdf"


def pdf_body_limit(resource_key: str) -> int:
    if resource_key not in CRCL_HISTORY_PDFS:
        raise ValueError("Unreviewed PDF resource")
    return (32 if resource_key == ARS_KEY else 8) * 1024 * 1024


@dataclass(frozen=True)
class PdfCaptureBinding:
    capture_id: str
    resource_key: str
    body_sha256: str
    byte_count: int

    def matches(self, key: str, body: bytes) -> bool:
        try:
            UUID(self.capture_id)
        except (ValueError, TypeError):
            return False
        return (
            self.resource_key == key
            and self.byte_count == len(body)
            and self.body_sha256 == hashlib.sha256(body).hexdigest()
        )


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _root(root: Path) -> Path:
    if root.is_symlink():
        raise ValueError("Transfer evidence directory is a symlink")
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _exclusive(path: Path, value: Any) -> None:
    data = _canonical(value)
    if path.is_symlink():
        raise ValueError("Transfer evidence is a symlink")
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("Transfer evidence identity conflict")
        return
    fd, name = tempfile.mkstemp(prefix=".transfer-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.link(name, path)
        parent = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        Path(name).unlink(missing_ok=True)


@dataclass
class PdfTransferEvidence:
    root: Path
    attempt_id: UUID
    header: dict[str, Any]
    wire_bytes: int = 0
    decoded_bytes: int = 0
    wire_eof: bool = False
    crossed_wire_limit: bool = False
    archive_complete: bool = False

    @classmethod
    def create(
        cls,
        root: Path,
        attempt_id: UUID,
        resource_key: str,
        received_at: str,
        content_length: str | None,
        content_encoding: str | None,
        limit: int,
    ) -> "PdfTransferEvidence":
        if not 0 <= limit <= pdf_body_limit(resource_key):
            raise ValueError("Invalid transfer limit")
        if datetime.fromisoformat(received_at).utcoffset() is None:
            raise ValueError("Transfer timestamp must be aware")
        valid = content_length is None or bool(re.fullmatch(r"[0-9]{1,19}", content_length))
        encoding = content_encoding.strip().lower() if content_encoding is not None else None
        recognized = encoding in (None, "identity", "gzip", "deflate", "br")
        header = {
            "revision": "d051-pdf-transfer-v1",
            "attemptId": str(attempt_id),
            "resourceKey": resource_key,
            "headersReceivedAt": received_at,
            "declaredContentLength": int(content_length) if content_length and valid else None,
            "contentLengthState": "absent"
            if content_length is None
            else ("valid" if valid else "invalid"),
            "contentEncoding": encoding if recognized else None,
            "contentEncodingState": "absent"
            if content_encoding is None
            else ("recognized" if recognized else "unrecognized"),
            "contentEncodingSha256": hashlib.sha256(content_encoding.encode()).hexdigest()
            if content_encoding is not None
            else None,
            "limitBytes": limit,
        }
        directory = _root(root)
        _exclusive(directory / f"{attempt_id}.header.json", header)
        return cls(directory, attempt_id, header)

    def observe_wire(self, chunk: bytes) -> None:
        self.wire_bytes += len(chunk)
        self.crossed_wire_limit = self.wire_bytes > self.header["limitBytes"]

    def observe_decoded(self, chunk: bytes) -> None:
        self.decoded_bytes += len(chunk)

    def seal(self, outcome: str, capture_id: str | None, body_sha256: str | None) -> str:
        detail = self.header | {
            "wireBytesObserved": self.wire_bytes,
            "decodedBytesEmitted": self.decoded_bytes,
            "wireEof": self.wire_eof,
            "lastChunkCrossedWireLimit": self.crossed_wire_limit,
            "archiveComplete": self.archive_complete,
            "outcome": outcome,
            "captureId": capture_id,
            "bodySha256": body_sha256,
        }
        encoded = _canonical(detail)
        if len(encoded) > 2048:
            raise ValueError("Transfer evidence exceeds existing audit field")
        _exclusive(
            self.root / f"{self.attempt_id}.terminal.json",
            {
                "headerSha256": hashlib.sha256(_canonical(self.header)).hexdigest(),
                "detail": detail,
            },
        )
        return encoded.decode()


def recover_transfer(root: Path, attempt_id: UUID) -> dict[str, Any]:
    """Read only; caller must compare terminal detail to persisted DB outcome."""
    header_path = root / f"{attempt_id}.header.json"
    terminal_path = root / f"{attempt_id}.terminal.json"
    if root.is_symlink() or header_path.is_symlink() or terminal_path.is_symlink():
        raise ValueError("Transfer evidence symlink")
    header: dict[str, Any] = json.loads(header_path.read_bytes())
    if (
        header.get("attemptId") != str(attempt_id)
        or header.get("revision") != "d051-pdf-transfer-v1"
    ):
        raise ValueError("Transfer evidence identity mismatch")
    if not terminal_path.exists():
        return header | {
            "status": "interrupted_unknown",
            "wireBytesObserved": None,
            "decodedBytesEmitted": None,
            "archiveComplete": False,
        }
    terminal = json.loads(terminal_path.read_bytes())
    detail: dict[str, Any] = terminal["detail"]
    if terminal["headerSha256"] != hashlib.sha256(_canonical(header)).hexdigest() or any(
        detail.get(key) != value for key, value in header.items()
    ):
        raise ValueError("Transfer terminal evidence mismatch")
    return detail | {"status": "terminal_pending_database_verification"}
