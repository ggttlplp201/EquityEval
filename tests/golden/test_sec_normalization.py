"""Expected numerical behavior is specified before the Company Facts parser."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from equity_ingest.sec_normalize import (
    canonical_cik,
    normalize_verified_bytes,
    parse_companyfacts_json,
)

from tests.sec_normalization_seed import cohort_input


@pytest.mark.parametrize("value", [True, -1, 0, 10000000000, 1876042.0, "+1876042", "1e3"])
def test_reject_untrusted_cik_identity(value):
    with pytest.raises(ValueError):
        canonical_cik(value)


def test_cik_integer_and_digit_string_have_one_identity():
    assert canonical_cik(1876042) == canonical_cik("0001876042") == "0001876042"


def test_numeric_lexeme_is_exact_before_float_can_round_it():
    parsed = parse_companyfacts_json(b'{"cik":1876042,"val":9007199254740993.0001e-2}')
    assert parsed["val"].text == "9007199254740993.0001e-2"
    assert parsed["val"].value == Decimal("90071992547409.930001")


def test_duplicate_json_key_is_a_document_error():
    with pytest.raises(ValueError, match="Duplicate"):
        parse_companyfacts_json(b'{"cik":1876042,"val":1,"val":2}')


GOLDEN = json.loads(Path(__file__).with_name("sec_normalized_cohort.json").read_text())


@pytest.mark.parametrize("company", GOLDEN["companies"], ids=lambda item: item["ticker"])
def test_all_forty_reviewed_anchor_outcomes(company):
    body, inputs = cohort_input(company["ticker"])
    bundle = normalize_verified_bytes(body, inputs)
    resolutions = {item.concept_std.value: item for item in bundle.resolutions}
    observations = {item.id: item for item in bundle.observations}
    units = {item.id: item.unit_key for item in bundle.units}
    assert len(resolutions) == len(company["outcomes"]) == 40
    assert bundle.original_history_complete is False
    for expected in company["outcomes"]:
        actual = resolutions[expected["concept"]]
        assert actual.status == expected["status"], expected["concept"]
        assert actual.reason == expected["reason"], expected["concept"]
        assert units[actual.unit_id] == expected["unit"]
        if expected["value"] is None:
            assert actual.selected_observation_id is None
            assert any(flag.resolution_id == actual.id for flag in bundle.quality_flags)
        else:
            observation = observations[actual.selected_observation_id]
            assert observation.numeric_value == Decimal(expected["value"]), expected["concept"]
            assert f"{observation.namespace}:{observation.tag}" == expected["tag"]
            assert observation.context_knowledge == "unknown"
            assert observation.raw_dimensions is observation.context_id is None
            assert observation.semantic_scope_id == actual.semantic_scope_id
            selected = [
                candidate
                for candidate in bundle.candidates
                if candidate.resolution_id == actual.id and candidate.disposition == "selected"
            ]
            assert len(selected) == 1
