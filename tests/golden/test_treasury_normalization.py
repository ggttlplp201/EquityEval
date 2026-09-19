"""Hand-checked native yields from the complete, licensed September 2026 capture."""

import hashlib
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from equity_ingest.market_normalize import normalize_treasury

from tests.test_market_normalize import market_input

pytestmark = pytest.mark.golden
EVIDENCE = Path(__file__).resolve().parents[2] / "docs/research/s4/evidence"


@pytest.mark.parametrize(
    "series,expected",
    [
        ("BC_2YEAR", ["4.39", "4.39", "4.34", "4.37", "4.39", "4.43", "4.56", "4.63"]),
        ("BC_10YEAR", ["4.79", "4.79", "4.77", "4.78", "4.80", "4.83", "4.95", "4.96"]),
    ],
)
def test_all_eight_actual_treasury_rows_have_exact_native_values(series, expected):
    body = (EVIDENCE / "treasury-yield-202609-e655415955c5.xml").read_bytes()
    assert (
        hashlib.sha256(body).hexdigest()
        == "e655415955c550b13f8ed20868c6cf56578387e82f3babdd39779bd2225b9e17"
    )
    inputs = market_input(body, series=series)
    result = normalize_treasury(body, inputs)
    assert [row.value for row in result.macros] == [Decimal(value) for value in expected]
    assert [row.reference_date.day for row in result.macros] == [1, 2, 3, 4, 8, 9, 10, 11]
    assert all(row.source_vintage_basis == "current_only" for row in result.macros)
    assert result.coverage_state == "unknown"
    partial = normalize_treasury(
        body, replace(inputs, requested_start=date(2026, 9, 10), requested_end=date(2026, 9, 11))
    )
    assert len(partial.macros) == 2
