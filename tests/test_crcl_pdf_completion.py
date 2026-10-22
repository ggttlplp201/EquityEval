"""D051 exact-resource caps and truthful interrupted-transfer evidence."""

import hashlib
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from equity_ingest.contracts import ResourceKind, SecResource
from equity_ingest.pdf_review import ARS_KEY, inspect_pdf

from tests.test_ingest_transport import response, transport
from tests.test_ingest_transport import setup as fixture_setup

setup = fixture_setup


def ars_request(setup):
    base = setup[4]
    return replace(
        base,
        resource=SecResource(
            base.resource.issuer_id,
            "1876042",
            ResourceKind.FILING_DOCUMENT,
            "a2025annualreport0331.pdf",
            "0001876042-26-000116",
        ),
    )


def test_exact_ars_above_eight_mib_retains_and_audits_counts(setup):
    body = b"%PDF-1.7\n" + b" " * (9 * 1024 * 1024) + b"\n%%EOF"
    client = transport(
        setup,
        lambda _: response(
            body=body, headers={"Content-Type": "application/pdf", "Content-Length": str(len(body))}
        ),
    )
    result = client.fetch(ars_request(setup))
    assert result.usable and len(result.records) == 1
    row = next(iter(setup[1].rows.values()))
    detail = json.loads(row["failure_detail"])
    assert detail["wireBytesObserved"] == len(body)
    assert detail["decodedBytesEmitted"] == len(body)
    assert detail["declaredContentLength"] == len(body)
    assert detail["wireEof"] and detail["archiveComplete"]
    assert detail["limitBytes"] == 32 * 1024 * 1024
    assert client.fetch(
        replace(ars_request(setup), cache_mode="replay", replay_records=result.records)
    ).usable


def test_ars_parser_requires_hash_bound_capture_for_larger_input(tmp_path):
    from equity_ingest.pdf_transfer import PdfCaptureBinding

    body = b"%PDF-1.7\n" + b" " * (9 * 1024 * 1024) + b"\n%%EOF"
    path = tmp_path / "renamed.pdf"
    path.write_bytes(body)
    binding = PdfCaptureBinding(str(uuid4()), ARS_KEY, hashlib.sha256(body).hexdigest(), len(body))
    assert (
        inspect_pdf(path, ARS_KEY, python=tmp_path / "missing")["reason"]
        == "pdf_capture_binding_required"
    )
    assert (
        inspect_pdf(path, ARS_KEY, python=tmp_path / "missing", capture=binding)["reason"]
        == "pdf_parser_unavailable"
    )
    bad = replace(binding, body_sha256="0" * 64)
    assert (
        inspect_pdf(path, ARS_KEY, python=tmp_path / "missing", capture=bad)["reason"]
        == "pdf_capture_binding_invalid"
    )
    other = "filing_document/0001876042/0000000000-24-002161/filename1.pdf"
    assert (
        inspect_pdf(path, other, python=tmp_path / "missing", capture=binding)["reason"]
        == "pdf_capture_binding_invalid"
    )


def test_interrupted_transfer_header_never_fabricates_counts(tmp_path):
    from equity_ingest.pdf_transfer import PdfTransferEvidence, recover_transfer

    identifier = uuid4()
    evidence = PdfTransferEvidence.create(
        tmp_path, identifier, ARS_KEY, "2026-10-22T00:00:00Z", "100", "identity", 32 * 1024 * 1024
    )
    evidence.observe_wire(b"abc")
    result = recover_transfer(tmp_path, identifier)
    assert result["status"] == "interrupted_unknown"
    assert result["wireBytesObserved"] is None
    assert result["declaredContentLength"] == 100
    with pytest.raises(ValueError):
        PdfTransferEvidence.create(
            tmp_path,
            identifier,
            ARS_KEY,
            "2026-10-22T00:00:00Z",
            "101",
            "identity",
            32 * 1024 * 1024,
        )


def test_ars_above_thirty_two_mib_fails_with_observed_not_total_counts(setup):
    import gzip

    body = b"%PDF-1.7\n" + b" " * (33 * 1024 * 1024) + b"\n%%EOF"
    wire = gzip.compress(body)
    client = transport(
        setup,
        lambda _: response(
            body=wire,
            headers={
                "Content-Type": "application/pdf",
                "Content-Encoding": "gzip",
                "Content-Length": str(len(wire)),
            },
        ),
    )
    result = client.fetch(ars_request(setup))
    assert not result.records and result.gaps == ("body_limit",)
    detail = json.loads(next(iter(setup[1].rows.values()))["failure_detail"])
    assert detail["wireBytesObserved"] <= len(wire)
    assert detail["decodedBytesEmitted"] <= 32 * 1024 * 1024
    assert not detail["archiveComplete"]
    assert detail["bodySha256"] is None


def test_transfer_terminal_recovery_reuses_identical_bytes_rejects_changed_header(tmp_path):
    from equity_ingest.pdf_transfer import PdfTransferEvidence, recover_transfer

    identifier = uuid4()
    evidence = PdfTransferEvidence.create(
        tmp_path, identifier, ARS_KEY, "2026-10-22T00:00:00Z", None, "identity", 32 * 1024 * 1024
    )
    evidence.observe_wire(b"abc")
    evidence.observe_decoded(b"abc")
    first = evidence.seal("body_limit", None, None)
    assert evidence.seal("body_limit", None, None) == first
    result = recover_transfer(tmp_path, identifier)
    assert result["status"] == "terminal_pending_database_verification"
    assert result["wireBytesObserved"] == 3
    header = tmp_path / f"{identifier}.header.json"
    header.write_text(header.read_text().replace('"limitBytes":33554432', '"limitBytes":1'))
    with pytest.raises(ValueError, match="mismatch"):
        recover_transfer(tmp_path, identifier)


def test_long_invalid_encoding_still_finishes_with_bounded_audit(setup):
    encoding = "x" * 3000
    client = transport(
        setup,
        lambda _: response(
            body=b"%PDF-1.7\n%%EOF",
            headers={"Content-Type": "application/pdf", "Content-Encoding": encoding},
        ),
    )
    result = client.fetch(ars_request(setup))
    assert not result.usable
    row = next(iter(setup[1].rows.values()))
    detail = json.loads(row["failure_detail"])
    assert detail["outcome"] == "transport_error"
    assert detail["contentEncoding"] is None
    assert detail["contentEncodingState"] == "unrecognized"
    assert detail["contentEncodingSha256"] == hashlib.sha256(encoding.encode()).hexdigest()
    assert len(row["failure_detail"].encode()) <= 2048
