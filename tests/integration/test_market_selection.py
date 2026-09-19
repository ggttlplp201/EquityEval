"""Historical selection uses complete captured evidence, never the next usable value."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from equity_schema.market_selection import select_macro, select_macro_at_or_before, select_price

from tests.market_selection_seed import (
    DAY,
    prepare_market,
    publish_prepared,
    quality_flag,
    seed_market,
)

pytestmark = pytest.mark.integration


def at(day):
    return datetime(2025, 1, day, tzinfo=UTC)


def test_price_selects_response_before_coverage_and_allows_explicit_old_batch(db_admin, db):
    ids, old = seed_market(db_admin, db)
    _, new = seed_market(db_admin, db, ids=ids, captured_at=at(4), omit=True, coverage="partial")
    result = select_price(db, ids["source"], ids["quote"], DAY)
    assert result.batch_id == new["batch"]["id"]
    assert result.value is None and not result.usable
    assert "missing_observation" in result.flags
    old_result = select_price(db, ids["source"], ids["quote"], DAY, batch_id=old["batch"]["id"])
    assert old_result.value == Decimal("100.25") and old_result.usable
    assert "explicit_batch" in old_result.flags
    historical = select_price(db, ids["source"], ids["quote"], DAY, retrieval_cutoff=at(3))
    assert historical.batch_id == old["batch"]["id"]
    assert historical.captured_at == at(3) and historical.capture_age == timedelta(0)


def test_capture_cutoff_includes_definition_and_identity_inputs(db_admin, db):
    ids, _ = seed_market(db_admin, db, captured_at=at(3), metadata_at=at(5))
    result = select_price(db, ids["source"], ids["quote"], DAY, retrieval_cutoff=at(4))
    assert result.value is None and result.batch_id is None
    ids, _ = seed_market(db_admin, db, ids=ids, kind="macro", metadata_at=at(5))
    result = select_macro(db, ids["source"], "TEST", DAY, retrieval_cutoff=at(4))
    assert result.value is None and result.batch_id is None


def test_raw_adjusted_and_field_quality_stay_separate(db_admin, db):
    ids, bundle = seed_market(
        db_admin,
        db,
        observation_changes={"dividend_currency": None},
        flags=(
            quality_flag("unknown_dividend_currency", reference_date=DAY, field_key="div_cash"),
        ),
    )
    raw = select_price(db, ids["source"], ids["quote"], DAY)
    adjusted = select_price(db, ids["source"], ids["quote"], DAY, field="adj_close")
    dividend = select_price(db, ids["source"], ids["quote"], DAY, field="div_cash")
    assert raw.value == Decimal("100.25") and raw.usable
    assert adjusted.value == Decimal("50") and adjusted.usable
    assert dividend.value == Decimal("0") and not dividend.usable
    assert dividend.quality_flags[0].rule_key == "unknown_dividend_currency"
    assert raw.currency == "USD" and raw.observation_id == bundle["prices"][0]["id"]
    assert raw.provenance[0].body_sha256


def test_new_missing_macro_preserves_marker_and_never_falls_back(db_admin, db):
    ids, _ = seed_market(db_admin, db, kind="macro", value="4.25")
    _, new = seed_market(
        db_admin,
        db,
        ids=ids,
        kind="macro",
        captured_at=at(4),
        value=None,
        observation_changes={"value_state": "source_missing", "original_value_text": "."},
        flags=(quality_flag("source_missing", at(4), reference_date=DAY, field_key="value"),),
    )
    result = select_macro(db, ids["source"], "TEST", DAY)
    assert result.batch_id == new["batch"]["id"] and result.value is None
    assert result.value_state == "source_missing" and result.original_value_text == "."
    assert result.unit_code == "percent_per_year" and result.unit_multiplier == Decimal("1")
    assert not result.usable


def test_source_vintage_is_exact_inclusive_and_distinct_from_local_capture(db_admin, db):
    vintage = date(2025, 1, 3)
    ids, bundle = seed_market(
        db_admin,
        db,
        kind="macro",
        value="-0.25",
        source_as_of_date=vintage,
        captured_at=at(8),
        observation_changes={
            "source_vintage_basis": "source_interval",
            "source_realtime_start": vintage,
            "source_realtime_end": date(9999, 12, 31),
        },
    )
    result = select_macro(db, ids["source"], "TEST", DAY, source_as_of_date=vintage)
    assert result.value == Decimal("-.25") and not result.usable
    assert result.source_realtime_end == date(9999, 12, 31)
    assert result.definition_as_of_basis == "capture_only"
    assert "definition_history_unavailable" in result.flags
    assert result.batch_id == bundle["batch"]["id"]
    assert select_macro(db, ids["source"], "TEST", DAY).value is None
    assert (
        select_macro(
            db, ids["source"], "TEST", DAY, source_as_of_date=vintage, retrieval_cutoff=at(7)
        ).value
        is None
    )


def test_future_source_definition_blocks_value_without_falling_back(db_admin, db):
    vintage = date(2025, 1, 3)
    ids, _ = seed_market(
        db_admin,
        db,
        kind="macro",
        source_as_of_date=vintage,
        definition_changes={
            "definition_as_of_basis": "source_supplied",
            "definition_as_of_date": date(2025, 1, 5),
        },
    )
    result = select_macro(db, ids["source"], "TEST", DAY, source_as_of_date=vintage)
    assert not result.usable and result.value is None
    assert "future_series_definition" in result.flags


@pytest.mark.parametrize(
    "precision,day,instant,cutoff,usable",
    [
        ("unknown", None, None, at(5), False),
        ("date", date(2025, 1, 3), None, at(3) + timedelta(hours=23), False),
        ("date", date(2025, 1, 3), None, at(4), True),
        ("instant", None, at(3) + timedelta(hours=10), at(3) + timedelta(hours=9), False),
        ("instant", None, at(3) + timedelta(hours=10), at(3) + timedelta(hours=10), True),
    ],
)
def test_intraday_source_knowledge_needs_publication_precision(
    db_admin, db, precision, day, instant, cutoff, usable
):
    ids, _ = seed_market(
        db_admin,
        db,
        observation_changes={
            "publication_precision": precision,
            "source_published_date": day,
            "source_published_at": instant,
        },
    )
    result = select_price(db, ids["source"], ids["quote"], DAY, source_known_at=cutoff)
    assert result.usable is usable
    assert (result.value == Decimal("100.25")) is usable


def test_conflicting_observations_are_not_selected_by_row_order(db_admin, db):
    prepared = prepare_market(db_admin, db)
    prepared[3]["prices"].append(
        prepared[3]["prices"][0]
        | {"id": uuid4(), "source_locator": "/1", "close": "99", "close_text": "99"}
    )
    ids, _ = publish_prepared(db, prepared)
    result = select_price(db, ids["source"], ids["quote"], DAY)
    assert result.value is None and not result.usable
    assert len(result.observation_ids) == 2 and "ambiguous_observation" in result.flags


def test_zero_is_observed_but_no_date_fill_or_arbitrary_batch_reuse(db_admin, db):
    ids, bundle = seed_market(db_admin, db, kind="macro", value="0")
    assert select_macro(db, ids["source"], "TEST", DAY).value == Decimal("0")
    assert select_macro(db, ids["source"], "TEST", date(2025, 1, 3)).value is None
    assert (
        select_macro(db, ids["source"], "OTHER", DAY, batch_id=bundle["batch"]["id"]).value is None
    )


def test_invalid_arguments_and_nonidle_connection_fail_closed(db):
    with pytest.raises(ValueError, match="field"):
        select_price(db, uuid4(), uuid4(), DAY, field="close; DROP TABLE price_daily")
    with pytest.raises(ValueError, match="timezone"):
        select_price(db, uuid4(), uuid4(), DAY, retrieval_cutoff=datetime(2025, 1, 1))
    with db.transaction(), pytest.raises(ValueError, match="idle"):
        select_price(db, uuid4(), uuid4(), DAY)


def test_backward_rate_requires_bounded_age_and_preserves_observation_date(db_admin, db):
    ids, batch = seed_market(db_admin, db, kind="macro", day=date(2025, 1, 3), value="4.25")
    result = select_macro_at_or_before(db, ids["source"], "TEST", date(2025, 1, 6), max_age_days=3)
    assert result.value == Decimal("4.25") and result.usable
    assert result.reference_date == date(2025, 1, 3)
    assert result.selection_date == date(2025, 1, 6)
    assert result.reference_age_days == 3 and result.max_age_days == 3
    assert result.batch_id == batch["batch"]["id"]
    assert "backward_selected" in result.flags
    too_old = select_macro_at_or_before(db, ids["source"], "TEST", date(2025, 1, 6), max_age_days=2)
    assert not too_old.usable and too_old.value is None
    assert "no_eligible_batch" in too_old.flags


def test_backward_rate_does_not_skip_new_missing_or_empty_response(db_admin, db):
    ids, old = seed_market(db_admin, db, kind="macro", day=date(2025, 1, 2), value="4.25")
    _, latest = seed_market(
        db_admin,
        db,
        ids=ids,
        kind="macro",
        day=date(2025, 1, 3),
        captured_at=at(4),
        value=None,
        observation_changes={"value_state": "source_missing", "original_value_text": "."},
        flags=(
            quality_flag(
                "source_missing", at(4), reference_date=date(2025, 1, 3), field_key="value"
            ),
        ),
    )
    result = select_macro_at_or_before(db, ids["source"], "TEST", date(2025, 1, 6), max_age_days=7)
    assert result.value is None and result.value_state == "source_missing"
    assert result.batch_id == latest["batch"]["id"]
    _, empty = seed_market(
        db_admin,
        db,
        ids=ids,
        kind="macro",
        day=date(2025, 1, 3),
        captured_at=at(5),
        omit=True,
        coverage="unavailable",
    )
    result = select_macro_at_or_before(db, ids["source"], "TEST", date(2025, 1, 6), max_age_days=7)
    assert result.batch_id == empty["batch"]["id"] and result.value is None
    assert "missing_observation" in result.flags


@pytest.mark.parametrize("age", [-1, 1.5, True])
def test_backward_rate_rejects_invalid_age(db, age):
    with pytest.raises(ValueError, match="age"):
        select_macro_at_or_before(db, uuid4(), "TEST", DAY, max_age_days=age)


def test_equal_response_time_from_different_captures_is_ambiguous(db_admin, db):
    ids, first = seed_market(db_admin, db)
    _, second = seed_market(db_admin, db, ids=ids, value="101")
    result = select_price(db, ids["source"], ids["quote"], DAY)
    assert result.value is None and not result.usable
    assert set(result.candidate_batch_ids) == {first["batch"]["id"], second["batch"]["id"]}
    assert result.flags == ("ambiguous_batch",)


def test_latest_unknown_coverage_or_malformed_value_cannot_fall_back(db_admin, db):
    ids, old = seed_market(db_admin, db)
    _, new = seed_market(
        db_admin,
        db,
        ids=ids,
        captured_at=at(4),
        coverage="unknown",
        flags=(quality_flag("calendar_unverified", at(4)),),
    )
    result = select_price(db, ids["source"], ids["quote"], DAY)
    assert result.batch_id == new["batch"]["id"] and not result.usable
    assert "incomplete_coverage" in result.flags
    _, broken = seed_market(
        db_admin,
        db,
        ids=ids,
        captured_at=at(5),
        observation_changes={"close": None, "close_state": "unparseable", "close_text": "oops"},
        flags=(quality_flag("invalid_close", at(5), reference_date=DAY, field_key="close"),),
    )
    result = select_price(db, ids["source"], ids["quote"], DAY)
    assert result.batch_id == broken["batch"]["id"] and result.value is None
    assert result.original_value_text == "oops" and "invalid_close" in result.flags


def test_ohlc_group_flags_block_each_affected_field_but_preserve_sound_volume(db_admin, db):
    ids, _ = seed_market(
        db_admin,
        db,
        observation_changes={"high": "50", "high_text": "50"},
        flags=tuple(
            quality_flag("inconsistent_ohlc", reference_date=DAY, field_key=field)
            for field in ("open", "high", "low", "close")
        ),
    )
    for field in ("open", "high", "low", "close"):
        result = select_price(db, ids["source"], ids["quote"], DAY, field)
        assert not result.usable and "inconsistent_ohlc" in result.flags
    volume = select_price(db, ids["source"], ids["quote"], DAY, "volume")
    assert volume.usable and volume.value == Decimal("50")
    assert not volume.quality_flags


def test_retrieval_cutoff_uses_complete_body_time_not_request_or_fetch_time(db_admin, db):
    ids, batch = seed_market(db_admin, db, captured_at=at(5), fetched_at=at(3), metadata_at=at(3))
    before_complete = select_price(db, ids["source"], ids["quote"], DAY, retrieval_cutoff=at(4))
    assert before_complete.value is None and before_complete.batch_id is None
    exact_complete = select_price(db, ids["source"], ids["quote"], DAY, retrieval_cutoff=at(5))
    assert exact_complete.batch_id == batch["batch"]["id"] and exact_complete.usable
    assert exact_complete.captured_at == at(5)


def test_late_historical_backfill_does_not_displace_newer_reference_date(db_admin, db):
    ids, current = seed_market(
        db_admin, db, kind="macro", day=date(2025, 1, 3), value="4.25", captured_at=at(4)
    )
    seed_market(
        db_admin, db, ids=ids, kind="macro", day=date(2025, 1, 2), value="4.50", captured_at=at(5)
    )
    result = select_macro_at_or_before(db, ids["source"], "TEST", date(2025, 1, 6), max_age_days=7)
    assert result.batch_id == current["batch"]["id"]
    assert result.reference_date == date(2025, 1, 3) and result.value == Decimal("4.25")


@pytest.mark.parametrize("basis", ["capture_only", "unknown", "source_supplied"])
def test_source_vintage_requires_historically_supported_series_interpretation(db_admin, db, basis):
    vintage = date(2025, 1, 3)
    changes = {"definition_as_of_basis": basis}
    if basis == "source_supplied":
        changes["definition_as_of_date"] = date(2025, 1, 2)
    ids, _ = seed_market(
        db_admin,
        db,
        kind="macro",
        source_as_of_date=vintage,
        definition_changes=changes,
        value="4.25",
    )
    result = select_macro(db, ids["source"], "TEST", DAY, source_as_of_date=vintage)
    assert result.value == Decimal("4.25") and result.unit_code == "percent_per_year"
    assert result.usable is (basis == "source_supplied")
    assert ("definition_history_unavailable" in result.flags) is (basis != "source_supplied")
