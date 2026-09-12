"""S3 acceptance preparation against existing S1 evidence, not normalizer coverage.

These tests verify archived bytes, original numeric tokens, complete row identity
and carefully scoped gaps. They deliberately import no ingestion or normalization
code. Complete normalized statements and source/worker behavior remain S3 work.
"""

import gzip
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKET = json.loads(Path(__file__).with_name("s3_review_cases.json").read_text())
pytestmark = pytest.mark.golden


class NumericToken(str):
    """Retain a JSON number's exact token separately from decoded string values."""


def resolve_pointer(document, pointer):
    value = document
    assert pointer.startswith("/")
    for component in pointer[1:].split("/"):
        key = component.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


@lru_cache(maxsize=8)
def captured_documents(ticker):
    capture = PACKET["captures"][ticker]
    body = gzip.decompress((ROOT / capture["archive"]).read_bytes())
    assert hashlib.sha256(body).hexdigest() == capture["raw_sha256"]
    assert len(body) == capture["raw_bytes"]
    # Decimal avoids a float intermediary; the second view preserves lexical form.
    return (
        json.loads(body, parse_float=Decimal),
        json.loads(body, parse_int=NumericToken, parse_float=NumericToken),
    )


def verify_review_reference(case):
    reference = case["review_evidence"]
    text = (ROOT / reference["path"]).read_text()
    assert reference["section"] in text


@pytest.mark.parametrize("ticker", tuple(PACKET["captures"]))
def test_capture_identity_matches_reviewed_s1_manifest(ticker):
    capture = PACKET["captures"][ticker]
    manifest = json.loads((ROOT / capture["manifest"]).read_text())
    entry = next(row for row in manifest["requests"] if row["ticker"] == ticker)
    assert capture["raw_sha256"] == entry["raw_sha256"]
    assert capture["raw_bytes"] == entry["raw_bytes"]
    assert capture["fetched_at"] == entry["fetched_at"]
    assert capture["source_url"] == entry["url"]
    assert capture["archive"] == "docs/research/s1/evidence/" + entry["raw_file"]
    assert datetime.fromisoformat(capture["fetched_at"]).utcoffset() is not None
    document, _ = captured_documents(ticker)
    assert document["cik"] == capture["expected_raw_cik"]
    assert type(document["cik"]) is type(capture["expected_raw_cik"])
    assert str(document["cik"]).zfill(10) == capture["cik"]


@pytest.mark.parametrize("case", PACKET["observations"], ids=lambda case: case["id"])
def test_reviewed_observation_preserves_exact_row_and_numeric_token(case):
    document, lexical_document = captured_documents(case["ticker"])
    row = resolve_pointer(document, case["json_pointer"])
    lexical_row = resolve_pointer(lexical_document, case["json_pointer"])
    tag = document["facts"][case["namespace"]][case["tag"]]
    unit = case["unit"].replace("~", "~0").replace("/", "~1")
    assert case["json_pointer"].startswith(
        f"/facts/{case['namespace']}/{case['tag']}/units/{unit}/"
    )
    assert {key: value for key, value in row.items() if key != "val"} == case[
        "expected_row_metadata"
    ]
    assert isinstance(lexical_row["val"], NumericToken)
    assert lexical_row["val"] == case["expected_numeric_lexical"]
    assert Decimal(lexical_row["val"]) == Decimal(case["expected_decimal"])
    assert Decimal(row["val"]) == Decimal(case["expected_decimal"])
    assert tag.get("label") == case["expected_source_label"]
    assert tag.get("description") == case["expected_source_description"]
    verify_review_reference(case)


@pytest.mark.parametrize("case", PACKET["gaps"], ids=lambda case: case["id"])
def test_reviewed_gap_stays_limited_to_its_exact_archived_scope(case):
    document, _ = captured_documents(case["ticker"])
    if case["kind"] == "missing_paths":
        found = []
        for pointer in case["json_pointers"]:
            try:
                found.append(resolve_pointer(document, pointer))
            except KeyError:
                pass
        assert len(found) == case["expected_count"]
    elif case["kind"] == "namespace_accession_gap":
        namespace = resolve_pointer(document, case["json_pointer"])
        rows = [row for tag in namespace.values() for unit in tag["units"].values() for row in unit]
        assert sum(row["accn"] == case["accession"] for row in rows) == case["expected_count"]
        assert len(namespace) == case["expected_tag_count"]
        assert max(row["end"] for row in rows) == case["expected_latest_period_end"]
    elif case["kind"] == "tag_period_gap":
        rows = resolve_pointer(document, case["json_pointer"])
        matches = [
            row
            for row in rows
            if row["accn"] == case["accession"]
            and row["end"] == case["end"]
            and row.get("start") == case["start"]
        ]
        assert len(matches) == case["expected_count"]
    else:
        pytest.fail(f"Unknown evidence-only gap kind: {case['kind']}")
    verify_review_reference(case)


def test_packet_covers_the_reviewed_eight_company_cohort_without_claiming_normalization():
    cohort = {"AAPL", "MSFT", "JPM", "CRCL", "RBLX", "TSM", "KHC", "COST"}
    assert set(PACKET["captures"]) == cohort
    assert {case["ticker"] for case in PACKET["observations"]} == cohort
    assert "not complete normalized golden fixtures" in PACKET["status"]
    ids = [case["id"] for case in PACKET["observations"] + PACKET["gaps"]]
    assert len(ids) == len(set(ids))
