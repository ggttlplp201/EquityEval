"""Original-filing numeric acceptance from five pre-existing S1 manual checks."""

import gzip
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from equity_ingest.filing import extract_inline_filing, select_filing_fact

EVIDENCE = Path(__file__).resolve().parents[2] / "docs/research/s1/evidence"
CHECKS = json.loads((EVIDENCE / "filing-spot-checks.json").read_text())["checks"]
MANIFEST = json.loads((EVIDENCE / "filing-manifest.json").read_text())["requests"]
CIKS = {"AAPL": "0000320193", "MSFT": "0000789019", "RBLX": "0001315098", "COST": "0000909832"}


@pytest.mark.parametrize("case", CHECKS, ids=lambda c: c["ticker"] + ":" + c["tag"])
def test_previously_hand_checked_filing_value_context_scale_and_unit(case):
    capture = next(row for row in MANIFEST if row.get("raw_file") == case["filing_raw_file"])
    body = gzip.decompress((EVIDENCE / case["filing_raw_file"]).read_bytes())
    extraction = extract_inline_filing(
        body,
        expected_sha256=case["filing_raw_sha256"],
        expected_byte_count=capture["raw_bytes"],
        expected_cik=CIKS[case["ticker"]],
    )
    matching = [
        fact
        for fact in extraction.facts
        if fact.raw_name == case["tag"] and fact.context_id == case["context_id"]
    ]
    assert matching
    for fact in matching:
        assert fact.lexical_text == case["filing_literal"]
        assert fact.scale == case["scale"]
        assert fact.value == Decimal(str(case["hand_checked_expected_api_value"]))
        assert fact.status == "observed"
        assert fact.locator
    chosen = select_filing_fact(
        extraction,
        qualified_tag=matching[0].qualified_tag,
        context_id=case["context_id"],
        unit_id=matching[0].unit_id,
    )
    assert chosen.status == "observed"
    assert chosen.value == Decimal(str(case["hand_checked_expected_api_value"]))
    context = next(c for c in extraction.contexts if c.id == case["context_id"])
    assert context.start_date == date.fromisoformat(case["start"])
    assert context.end_date == date.fromisoformat(case["end"])
    assert context.dimensions == ()
    unit = next(u for u in extraction.units if u.id == matching[0].unit_id)
    assert unit.numerator_measures == ("{http://www.xbrl.org/2003/iso4217}USD",)
    assert unit.denominator_measures == ()
    assert extraction.capture_sha256 == case["filing_raw_sha256"]


def test_tsm_reviewed_ordinary_and_ads_eps_remain_separate():
    from equity_ingest.filing import FilingDimension

    # The S1 IFRS review records these four source amounts and the ADS context;
    # no ADS conversion or FX calculation is used to produce an expected value.
    capture = next(row for row in MANIFEST if row["id"] == "TSM-filing" and row.get("raw_file"))
    body = gzip.decompress((EVIDENCE / capture["raw_file"]).read_bytes())
    extraction = extract_inline_filing(
        body,
        expected_sha256=capture["raw_sha256"],
        expected_byte_count=capture["raw_bytes"],
        expected_cik="0001046179",
    )
    namespace = "https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full"
    tag = "{" + namespace + "}BasicEarningsLossPerShare"
    dimension = FilingDimension(
        "{" + namespace + "}ClassesOfShareCapitalAxis",
        "{http://www.tsmc.com/20251231}AmericanDepositarySharesMember",
        "segment",
    )
    for context, unit, expected in [
        ("c-1", "twdPerShare", "65.47"),
        ("c-1", "usdPerShare", "2.09"),
        ("c-9", "twdPerShare", "327.37"),
        ("c-9", "usdPerShare", "10.44"),
    ]:
        if context == "c-9":
            unreviewed = select_filing_fact(
                extraction, qualified_tag=tag, context_id=context, unit_id=unit
            )
            assert unreviewed.status == "unsupported"
            assert unreviewed.value is None
        chosen = select_filing_fact(
            extraction,
            qualified_tag=tag,
            context_id=context,
            unit_id=unit,
            expected_dimensions=(dimension,) if context == "c-9" else (),
        )
        assert chosen.status == "observed"
        assert chosen.value == Decimal(expected)
        assert chosen.fact.lexical_text == expected


def test_khc_html_restatement_note_requires_a_separate_reviewed_reader():
    capture = next(row for row in MANIFEST if row["id"] == "KHC-restatement-note")
    body = gzip.decompress((EVIDENCE / capture["raw_file"]).read_bytes())
    extraction = extract_inline_filing(
        body,
        expected_sha256=capture["raw_sha256"],
        expected_byte_count=capture["raw_bytes"],
        expected_cik="0001637459",
    )
    assert not extraction.complete
    assert not extraction.facts
    assert extraction.issues[0].code == "malformed_xml"
