"""Verify hand-checked KHC rows against the immutable S1 source archive."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_khc_expected_observations_have_exact_archived_provenance():
    fixture = json.loads((Path(__file__).with_name("khc_restatement.json")).read_text())
    body = gzip.decompress((ROOT / fixture["archive"]).read_bytes())
    assert hashlib.sha256(body).hexdigest() == fixture["raw_sha256"]
    assert len(body) == fixture["raw_bytes"]
    source = json.loads(body)
    assert source["cik"] == 1637459
    expected = [10999000000, 10941000000, 10990000000, 10932000000]
    for item, amount in zip(fixture["observations"], expected, strict=True):
        index = int(item["locator"].rsplit("/", 1)[1])
        assert source["facts"]["us-gaap"][item["tag"]]["units"]["USD"][index] == item["row"]
        assert item["row"]["val"] == amount
        assert item["row"]["start"] == "2017-01-01"
        assert item["row"]["end"] == "2017-12-30"
