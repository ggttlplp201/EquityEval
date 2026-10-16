"""Version separation and fail-closed real source selectors."""

import pytest
from pydantic import ValidationError

from tests.real_fundamentals_seed import quote_id, real_manifest


def test_real_contract_has_no_synthetic_label_or_quote():
    from equity_schema.fundamentals import InputManifest
    from equity_schema.fundamentals_canonical import canonical_json
    from equity_schema.real_fundamentals import read_manifest

    item = real_manifest()
    text = canonical_json(item)
    assert read_manifest(text) == item
    assert "quote_identifier_id" not in text and "fixture_label" not in text
    with pytest.raises(ValidationError):
        InputManifest.model_validate_json(text)


@pytest.mark.parametrize("change", ["synthetic", "quote", "label", "unknown", "future_capture"])
def test_real_contract_rejects_ambiguous_or_lookahead_inputs(change):
    from equity_schema.real_fundamentals import RealInputManifest

    data = real_manifest().model_dump(mode="json")
    if change == "synthetic":
        data["evidence_mode"] = "synthetic"
    elif change == "quote":
        data["selector"]["quote_identifier_id"] = quote_id()
    elif change == "label":
        data["fixture_label"] = "Synthetic integration fixture — not company data"
    elif change == "unknown":
        data["version"] = "s6-input-v99"
    else:
        data["captures"][0]["fetched_at"] = "2099-01-01T00:00:00Z"
    with pytest.raises(ValueError):
        RealInputManifest.model_validate(data)


def test_real_capture_cutoff_cannot_exceed_frozen_evaluation():
    from dataclasses import replace
    from datetime import UTC, date, datetime

    from equity_schema.fundamentals_canonical import content_hash
    from equity_schema.real_fundamentals import RealInputManifest

    item = real_manifest()
    context = replace(item.context, as_of=date(2026, 2, 28))
    selector = item.selector.model_copy(
        update={
            "as_of": context.as_of,
            "evaluated_at": datetime(2026, 2, 28, 23, tzinfo=UTC),
            "policy_content_hash": content_hash((context, item.history_policy, item.trend_policy)),
        }
    )
    data = item.model_dump(mode="json")
    data.update(context=context, selector=selector)
    with pytest.raises(ValueError):
        RealInputManifest.model_validate(data)
