"""PDF entity readiness never follows solely from a successful HTTP status."""

import gzip
from dataclasses import replace

import pytest
from equity_ingest.contracts import ResourceKind, SecResource

from tests.test_ingest_transport import response, transport
from tests.test_ingest_transport import setup as fixture_setup

setup = fixture_setup


def pdf_request(setup):
    base = setup[4]
    return replace(
        base,
        resource=SecResource(
            base.resource.issuer_id,
            "1876042",
            ResourceKind.FILING_DOCUMENT,
            "filename1.pdf",
            "0000000000-24-002161",
        ),
    )


@pytest.mark.parametrize(
    "body,mime,reason",
    [
        (b"%PDF-1.7\n%%EOF\n", "text/html", "pdf_content_type"),
        (b"<html>error</html>", "application/pdf", "pdf_signature"),
        (b"%PDF-1.7\ntruncated", "application/pdf", "pdf_eof"),
    ],
)
def test_invalid_pdf_retained_but_not_ready_on_fetch_replay_reuse(setup, body, mime, reason):
    client = transport(setup, lambda _: response(body=body, headers={"Content-Type": mime}))
    request = pdf_request(setup)
    result = client.fetch(request)
    assert not result.usable and reason in result.gaps
    (record,) = result.records
    assert client.archive.read_blob(record.blob_key, record.body_sha256, record.byte_count) == body
    assert next(iter(setup[1].rows.values()))["state"] == "complete"
    for mode in ("replay", "reuse", "conditional"):
        repeated = client.fetch(
            replace(
                request,
                cache_mode=mode,
                replay_records=(record,) if mode == "replay" else (),
                cached_record=record if mode != "replay" else None,
            )
        )
        assert not repeated.usable and reason in repeated.gaps


def test_pdf_limit_is_eight_mib_even_when_document_limit_is_larger(setup):
    body = b"%PDF-1.7\n" + b"x" * (8 * 1024 * 1024) + b"\n%%EOF"
    client = transport(
        setup,
        lambda _: response(
            body=gzip.compress(body),
            headers={"Content-Type": "application/pdf", "Content-Encoding": "gzip"},
        ),
    )
    result = client.fetch(pdf_request(setup))
    assert not result.records and not result.usable
    assert "body_limit" in result.gaps


def test_complete_pdf_envelope_remains_subject_to_later_structural_review(setup):
    body = b"%PDF-1.7\nnot structurally reviewed\n%%EOF\n"
    client = transport(
        setup,
        lambda _: response(body=body, headers={"Content-Type": "application/pdf; charset=binary"}),
    )
    result = client.fetch(pdf_request(setup))
    assert result.usable
    assert result.records[0].byte_count == len(body)


def test_ordinary_pipeline_rejects_pdf_before_database_or_network(setup):
    from datetime import date

    from equity_ingest.pipeline import SourcePlan, run_source_stages

    resource = pdf_request(setup).resource
    plan = SourcePlan(
        resource.issuer_id, resource.cik, date(2024, 1, 1), date(2024, 12, 31), (resource,)
    )
    with pytest.raises(ValueError, match="V2 bootstrap"):
        run_source_stages(None, None, None, None, plan, None)


def test_acquisition_deadline_never_rounds_past_remaining_run_budget():
    from equity_ingest.pipeline import acquisition_lease_seconds

    assert acquisition_lease_seconds(lambda: 42.9) == 42
    assert acquisition_lease_seconds(lambda: 900) == 360
    for remaining in (0.9, 0, -1):
        with pytest.raises(ValueError, match="acquisition deadline"):
            acquisition_lease_seconds(lambda remaining=remaining: remaining)
