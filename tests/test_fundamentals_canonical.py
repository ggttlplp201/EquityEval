"""Canonicalization has exact bytes and no implicit numeric coercion."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from equity_schema.fundamentals_canonical import canonical_json, content_hash, parse_canonical


def test_canonical_bytes_are_sorted_utf8_and_preserve_decimal_scale_and_array_order():
    value = {"z": Decimal("100.00"), "a": ["é", Decimal("-0.50"), 2, None]}
    expected = '{"a":["é","-0.50",2,null],"z":"100.00"}'
    assert canonical_json(value) == expected
    assert canonical_json(dict(reversed(tuple(value.items())))) == expected
    assert content_hash(value) == content_hash(parse_canonical(expected))
    assert content_hash(value) != content_hash({**value, "z": Decimal("100")})
    assert content_hash(value) != content_hash({**value, "a": list(reversed(value["a"]))})


@pytest.mark.parametrize(
    "value",
    [
        1.0,
        float("nan"),
        Decimal("NaN"),
        Decimal("Infinity"),
        {1: "bad"},
        {"a": {1, 2}},
        datetime(2025, 1, 1),
    ],
)
def test_float_nonfinite_ambiguous_maps_and_naive_time_are_rejected(value):
    with pytest.raises((TypeError, ValueError)):
        canonical_json(value)


def test_timestamps_and_ids_have_one_unambiguous_representation():
    value = {"at": datetime(2026, 2, 28, tzinfo=UTC), "id": UUID(int=1)}
    assert (
        canonical_json(value)
        == '{"at":"2026-02-28T00:00:00.000000Z","id":"00000000-0000-0000-0000-000000000001"}'
    )


@pytest.mark.parametrize(
    "text", ['{"b":1, "a":2}', '{"a":1,"a":2}', '{"a":1.0}', '{"a":NaN}', '{"a":"\\u00e9"}']
)
def test_noncanonical_or_duplicate_json_is_not_silently_normalized(text):
    with pytest.raises(ValueError):
        parse_canonical(text)
