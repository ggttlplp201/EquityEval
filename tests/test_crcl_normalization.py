"""Offline D5a preparation tests; synthetic capture identities never reach the app."""

import copy
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from equity_ingest.archive import ArchiveError, LocalArchive

from scripts import normalize_crcl as subject
from tests.sec_normalization_seed import cohort_input


@pytest.fixture
def retained(tmp_path):
    body, inputs = cohort_input("CRCL")
    import gzip

    manifest = json.loads(
        (subject.ROOT / "docs/research/s1/evidence/filing-manifest.json").read_text()
    )
    original = next(row for row in manifest["requests"] if row.get("id") == "CRCL-filing")
    filing = gzip.decompress(
        (subject.ROOT / "docs/research/s1/evidence" / original["raw_file"]).read_bytes()
    )
    records = list(subject.FILINGS.values())
    inventory = json.dumps(
        {
            "cik": "0001876042",
            "filings": {
                "files": [],
                "recent": {
                    "accessionNumber": list(subject.FILINGS),
                    "filingDate": [row[0] for row in records],
                    "form": [row[1] for row in records],
                    "reportDate": [row[2] for row in records],
                    "primaryDocument": [row[3] for row in records],
                    "acceptanceDateTime": [row[4] for row in records],
                },
            },
        }
    ).encode()
    bodies = [body, inventory, filing, b"Fictional amendment context", b"Fictional quarter context"]
    archive = LocalArchive(tmp_path / "raw")
    captures = []
    source = uuid4()
    for key, payload in zip(subject.RESOURCES, bodies, strict=True):
        identifier = uuid4()
        stored = archive.write(
            [payload],
            source_key="fictional-test",
            source_object_key=key,
            params_hash="0" * 64,
            capture_id=identifier,
            retrieved_at=datetime(2026, 9, 21, tzinfo=UTC),
            max_bytes=5000000,
        )
        captures.append(
            {
                "capture_id": str(identifier),
                "source_id": str(source),
                "source_object_key": key,
                "request_url": subject.resource_url(key),
                "body_sha256": stored.body_sha256,
                "byte_count": stored.byte_count,
                "blob_key": stored.blob_key,
                "http_status": 200,
                "fetched_at": "2026-09-21T00:00:00+00:00",
                "completed_at": "2026-09-21T00:00:00+00:00",
            }
        )
    return {
        "bootstrap_plan": {
            "issuer_id": str(inputs.issuer_id),
            "source_id": str(source),
            "cik": "0001876042",
        },
        "captures": captures,
    }, archive


def test_exact_two_concepts_keep_flags_precision_and_distinct_filings(retained):
    audit, archive = retained
    bundle, proof = subject.prepare(audit, archive)
    observations = {row.id: row for row in bundle.observations}
    assert {
        row.concept_std.value: str(observations[row.selected_observation_id].numeric_value)
        for row in bundle.resolutions
    } == {"revenue": "2746642000", "operating_income": "-96435000"}
    assert len(bundle.inputs.filings) == 3
    assert len(bundle.inputs.requests) == 1
    assert bundle.inputs.filing_event_ids == ()
    assert not bundle.original_history_complete
    assert {flag.rule_key for flag in bundle.quality_flags} >= {
        "inventory_history_incomplete",
        "event_history_incomplete",
    }
    assert proof["revenue"]["fact"]["decimals"] == "-3"
    assert proof["operating_income"]["fact"]["sign"] == "-"
    assert subject.prepare(audit, archive) == (bundle, proof)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", str(uuid4())),
        ("request_url", "https://example.invalid/"),
        ("completed_at", "2026-09-22T00:00:00+00:00"),
        ("fetched_at", "2026-09-22T00:00:00+00:00"),
        ("http_status", 404),
        ("body_sha256", "f" * 64),
        ("byte_count", 1),
    ],
)
def test_invalid_capture_prevents_preparation(retained, field, value):
    audit, archive = retained
    audit["captures"][0][field] = value
    with pytest.raises((ValueError, OSError, ArchiveError)):
        subject.prepare(audit, archive)


def test_duplicate_capture_is_not_silently_overwritten(retained):
    audit, archive = retained
    audit["captures"].append(copy.deepcopy(audit["captures"][0]))
    with pytest.raises(ValueError):
        subject.prepare(audit, archive)


def test_wrong_cik_is_rejected(retained):
    audit, archive = retained
    audit["bootstrap_plan"]["cik"] = "0000320193"
    with pytest.raises(ValueError):
        subject.prepare(audit, archive)


def test_production_entry_requires_the_pinned_audit(tmp_path):
    from scripts.review_crcl_identity import AUDIT_PATH

    path = tmp_path / AUDIT_PATH
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    with pytest.raises(ValueError, match="new evidence review"):
        subject.load_preparation(tmp_path)


def replace_body(audit, archive, index, payload):
    row = audit["captures"][index]
    from uuid import UUID

    stored = archive.write(
        [payload],
        source_key="fictional-test-modified-" + str(uuid4()),
        source_object_key=row["source_object_key"],
        params_hash="a" * 64,
        capture_id=UUID(row["capture_id"]),
        retrieved_at=datetime(2026, 9, 21, tzinfo=UTC),
        max_bytes=5000000,
    )
    row.update(
        blob_key=stored.blob_key, body_sha256=stored.body_sha256, byte_count=stored.byte_count
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("accessionNumber", "0001876042-26-999999"),
        ("form", "10-Q"),
        ("reportDate", "2026-06-30"),
        ("filingDate", "2026-03-08"),
        ("acceptanceDateTime", "2026-03-09T12:36:51"),
    ],
)
def test_changed_inventory_requires_separate_review(retained, field, value):
    audit, archive = retained
    row = audit["captures"][1]
    inventory = json.loads(
        archive.read_blob(row["blob_key"], row["body_sha256"], row["byte_count"])
    )
    inventory["filings"]["recent"][field][0] = value
    replace_body(audit, archive, 1, json.dumps(inventory).encode())
    with pytest.raises(ValueError):
        subject.prepare(audit, archive)


@pytest.mark.parametrize(
    "old,new",
    [
        (b'id="c-1"', b'id="changed-context"'),
        (b"iso4217:USD", b"iso4217:EUR"),
        (b'decimals="-3"', b'decimals="-6"'),
        (b'scale="3"', b'scale="6"'),
        (b'sign="-"', b'sign="+"'),
        (b"2025-01-01", b"2025-01-02"),
    ],
)
def test_wrong_context_unit_precision_sign_or_period_is_not_accepted(retained, old, new):
    audit, archive = retained
    row = audit["captures"][2]
    body = archive.read_blob(row["blob_key"], row["body_sha256"], row["byte_count"])
    assert old in body
    replace_body(audit, archive, 2, body.replace(old, new))
    with pytest.raises(ValueError):
        subject.prepare(audit, archive)


def test_genuine_zero_is_distinct_from_missing(retained):
    audit, archive = retained
    row = audit["captures"][0]
    facts = json.loads(archive.read_blob(row["blob_key"], row["body_sha256"], row["byte_count"]))
    for item in facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"]:
        if (
            item.get("accn") == subject.ACCESSION
            and item.get("start") == "2025-01-01"
            and item.get("end") == "2025-12-31"
        ):
            item["val"] = 0
    replace_body(audit, archive, 0, json.dumps(facts).encode())
    row = audit["captures"][2]
    original = archive.read_blob(row["blob_key"], row["body_sha256"], row["byte_count"])
    replace_body(audit, archive, 2, original.replace(b"2,746,642", b"0"))
    bundle, _ = subject.prepare(audit, archive)
    revenue = next(item for item in bundle.resolutions if item.concept_std.value == "revenue")
    observation = next(
        item for item in bundle.observations if item.id == revenue.selected_observation_id
    )
    assert observation.numeric_value == 0 and revenue.status == "observed"
    del facts["facts"]["us-gaap"]["Revenues"]
    replace_body(audit, archive, 0, json.dumps(facts).encode())
    with pytest.raises(ValueError, match="do not agree"):
        subject.prepare(audit, archive)
