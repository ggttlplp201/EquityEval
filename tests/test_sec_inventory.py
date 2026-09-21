"""Submission inventory boundaries are specified before the parser."""

import json
from datetime import date
from uuid import uuid4

import pytest
from equity_ingest.sec_inventory import assemble_inventory, parse_submissions


def recent_document(files=()):
    return json.dumps(
        {
            "cik": 320193,
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-25-000079"],
                    "filingDate": ["2025-10-31"],
                    "reportDate": ["2025-09-27"],
                    "form": ["10-K"],
                    "primaryDocument": ["aapl-20250927.htm"],
                    "acceptanceDateTime": ["2025-10-31T06:01:00.000Z"],
                },
                "files": list(files),
            },
        }
    ).encode()


def test_recent_only_inventory_does_not_claim_older_files_were_read():
    parsed = parse_submissions(
        recent_document(
            [
                {
                    "name": "CIK0000320193-submissions-001.json",
                    "filingCount": 1,
                    "filingFrom": "2015-01-01",
                    "filingTo": "2019-12-31",
                }
            ]
        ),
        expected_cik="0000320193",
        capture_id=uuid4(),
    )
    assert parsed.filings[0].acceptance_time_basis == "verified_timezone"
    inventory = assemble_inventory(
        parsed, (), boundary_start=date(2015, 1, 1), boundary_end=date(2025, 12, 31)
    )
    assert inventory.completeness == "incomplete"
    assert "CIK0000320193-submissions-001.json" in inventory.missing_documents


@pytest.mark.parametrize(
    "filename",
    ["../other.json", "https://example.com/a.json", "CIK0000019617-submissions-001.json"],
)
def test_older_document_identity_cannot_escape_the_requested_issuer(filename):
    with pytest.raises(ValueError):
        parse_submissions(
            recent_document(
                [
                    {
                        "name": filename,
                        "filingCount": 1,
                        "filingFrom": "2015-01-01",
                        "filingTo": "2019-12-31",
                    }
                ]
            ),
            expected_cik="0000320193",
            capture_id=uuid4(),
        )


def test_parallel_arrays_cannot_silently_zip_away_a_filing():
    payload = json.loads(recent_document())
    payload["filings"]["recent"]["filingDate"] = []
    with pytest.raises(ValueError, match="length"):
        parse_submissions(
            json.dumps(payload).encode(), expected_cik="0000320193", capture_id=uuid4()
        )


def test_complete_advertised_inventory_does_not_imply_event_completeness():
    metadata = {
        "name": "CIK0000320193-submissions-001.json",
        "filingCount": 1,
        "filingFrom": "2015-01-01",
        "filingTo": "2019-12-31",
    }
    recent = parse_submissions(
        recent_document([metadata]), expected_cik="0000320193", capture_id=uuid4()
    )
    historical = json.dumps(
        {
            "accessionNumber": ["0000320193-18-000007"],
            "filingDate": ["2018-01-01"],
            "form": ["8-K"],
            "acceptanceDateTime": ["2018-01-01T12:00:00"],
        }
    ).encode()
    older = parse_submissions(
        historical, expected_cik="0000320193", capture_id=uuid4(), document_name=metadata["name"]
    )
    assert older.filings[0].acceptance_at is None
    assert "2018-01-01T12:00:00" in older.filings[0].raw_metadata
    inventory = assemble_inventory(
        recent, (older,), boundary_start=date(2015, 1, 1), boundary_end=date(2025, 12, 31)
    )
    assert inventory.completeness == "complete"
    assert len(inventory.filings) == 2
    assert "event/original-history review is independent" in inventory.completeness_basis


def test_filing_count_mismatch_keeps_inventory_incomplete():
    metadata = {
        "name": "CIK0000320193-submissions-001.json",
        "filingCount": 2,
        "filingFrom": "2015-01-01",
        "filingTo": "2019-12-31",
    }
    recent = parse_submissions(
        recent_document([metadata]), expected_cik="0000320193", capture_id=uuid4()
    )
    older = parse_submissions(
        b'{"accessionNumber":[],"filingDate":[],"form":[]}',
        expected_cik="0000320193",
        capture_id=uuid4(),
        document_name=metadata["name"],
    )
    inventory = assemble_inventory(
        recent, (older,), boundary_start=date(2015, 1, 1), boundary_end=date(2025, 12, 31)
    )
    assert inventory.completeness == "incomplete"
    assert "older_inventory_metadata_mismatch" in inventory.flags


def test_unadvertised_older_document_is_not_trusted():
    recent = parse_submissions(recent_document(), expected_cik="0000320193", capture_id=uuid4())
    older = parse_submissions(
        b'{"accessionNumber":[],"filingDate":[],"form":[]}',
        expected_cik="0000320193",
        capture_id=uuid4(),
        document_name="CIK0000320193-submissions-001.json",
    )
    with pytest.raises(ValueError, match="not advertised"):
        assemble_inventory(
            recent, (older,), boundary_start=date(2015, 1, 1), boundary_end=date(2025, 12, 31)
        )


def test_duplicate_rows_in_one_document_do_not_satisfy_advertised_count():
    metadata = {
        "name": "CIK0000320193-submissions-001.json",
        "filingCount": 2,
        "filingFrom": "2015-01-01",
        "filingTo": "2019-12-31",
    }
    recent = parse_submissions(
        recent_document([metadata]), expected_cik="0000320193", capture_id=uuid4()
    )
    body = json.dumps(
        {
            "accessionNumber": ["0000320193-18-000007"] * 2,
            "filingDate": ["2018-01-01"] * 2,
            "form": ["8-K"] * 2,
        }
    ).encode()
    older = parse_submissions(
        body, expected_cik="0000320193", capture_id=uuid4(), document_name=metadata["name"]
    )
    result = assemble_inventory(
        recent, (older,), boundary_start=date(2015, 1, 1), boundary_end=date(2025, 12, 31)
    )
    assert result.completeness == "incomplete"
    assert "duplicate_accessions_in_document" in result.flags
    assert len(result.filings) == 3  # Keep both raw rows as evidence; never silently discard one.


@pytest.mark.parametrize(
    "filename", ["xsl144X01/primary_doc.xml", "xslF345X06/wk-form4_1789074349.xml"]
)
def test_primary_document_preserves_sec_renderer_directory(filename):
    payload = json.loads(recent_document())
    payload["filings"]["recent"]["primaryDocument"] = [filename]
    result = parse_submissions(
        json.dumps(payload).encode(), expected_cik="0000320193", capture_id=uuid4()
    )
    assert result.filings[0].primary_document == filename
    assert json.loads(result.filings[0].raw_metadata)["primaryDocument"] == filename


@pytest.mark.parametrize(
    "filename",
    [
        "../doc.xml",
        "xsl/../doc.xml",
        "/xsl/doc.xml",
        "//other/doc.xml",
        "https://example.com/doc.xml",
        "xsl//doc.xml",
        "xsl/./doc.xml",
        "xsl/%2e%2e/doc.xml",
        "xsl%2fdoc.xml",
        "xsl/doc.xml?redirect=1",
        "xsl/doc.xml#fragment",
        "xsl\\doc.xml",
        "xsl/doc.xml\n",
        "xsl/",
    ],
)
def test_primary_document_rejects_unsafe_relative_paths(filename):
    payload = json.loads(recent_document())
    payload["filings"]["recent"]["primaryDocument"] = [filename]
    with pytest.raises(ValueError, match="safe relative path"):
        parse_submissions(
            json.dumps(payload).encode(), expected_cik="0000320193", capture_id=uuid4()
        )
