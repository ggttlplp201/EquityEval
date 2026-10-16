"""D5k existing S3 publisher with exact new scope, disposable database only."""

import pytest
from equity_ingest.publisher import publish_bundle

from tests.integration.test_crcl_observation_publication import current_pair  # noqa: F401

pytestmark = pytest.mark.integration


def test_broader_source_publication_keeps_both_prior_batches(current_pair, db_admin, db):  # noqa: F811
    from scripts.prepare_crcl_broader import prepare
    from scripts.publish_crcl_broader import readback, register_mapping
    from scripts.publish_crcl_normalization import readback as historical_readback
    from scripts.publish_crcl_normalization import rows_snapshot, verify_preserved
    from scripts.publish_crcl_observation import readback as current_readback

    old, current = current_pair
    first = publish_bundle(db, old)
    second = publish_bundle(db, current)
    before = rows_snapshot(db_admin)
    broader, _ = prepare()
    register_mapping(db_admin, broader)
    result = publish_bundle(db, broader)
    replay = publish_bundle(db, broader)
    assert replay.reused and replay.batch_id == result.batch_id
    checks = readback(db, broader, result.batch_id)
    assert len(checks) == 10
    assert all(c["current"]["usable_for_valuation"] for c in checks.values())
    assert all(c["before_filing"]["facts"][0]["value"] is None for c in checks.values())
    assert current_readback(db, current, second.batch_id)["as_filed"]["usable_for_valuation"]
    assert not historical_readback(db, old, first.batch_id)["as_filed"]["usable_for_valuation"]
    verify_preserved(before, rows_snapshot(db_admin))


@pytest.mark.parametrize("basis, valid", [("annual", 4), ("instant", 2)])
def test_broader_real_candidate_keeps_period_scopes_separate(
    current_pair,  # noqa: F811
    db_admin,
    db,
    basis,
    valid,
):  # noqa: F811
    from datetime import UTC, datetime
    from decimal import Decimal
    from uuid import uuid4

    from equity_core.real_fundamentals import calculate_payload

    from scripts.prepare_crcl_broader import prepare
    from scripts.prepare_crcl_broader_fundamentals import build_manifest
    from scripts.publish_crcl_broader import register_mapping

    bundle, proof = prepare()
    register_mapping(db_admin, bundle)
    published = publish_bundle(db, bundle)
    manifest = build_manifest(
        db,
        bundle=bundle,
        proof=proof,
        batch_id=published.batch_id,
        security_id=uuid4(),
        evaluated_at=datetime(2026, 10, 16, 1, tzinfo=UTC),
        period_basis=basis,
    )
    result = calculate_payload(manifest, history_payloads={})
    metrics = {m.metric_id: m for m in result.metrics}
    assert result.coverage.counts["valid"] == valid
    assert result.coverage.counts["unsupported"] == 10 - valid
    assert result.coverage.counts["invalid"] == 0
    assert result.accounting.matches is True
    if basis == "annual":
        assert metrics["free_cash_flow_ppe"].value == "529697000"
        assert metrics["net_margin_consolidated"].value.startswith("-0.025310")
        other = ("current_ratio", "net_working_capital")
    else:
        assert metrics["net_working_capital"].value == "2473072000"
        assert Decimal(metrics["current_ratio"].value) > 1
        other = (
            "operating_margin",
            "net_margin_consolidated",
            "free_cash_flow_ppe",
            "free_cash_flow_margin_ppe",
        )
    for key in other:
        assert metrics[key].value is None and metrics[key].status == "unsupported"
        assert any("Other period scope" in reason for reason in metrics[key].reasons)
    for key in ("gross_margin", "gross_margin_derived", "revenue_growth_yoy", "return_on_assets"):
        assert metrics[key].value is None and metrics[key].status == "unsupported"
    assert all(not h.eligible_snapshot_ids for h in result.history)
    from pydantic import ValidationError

    changed = manifest.model_dump(mode="python")
    changed["selector"]["period_basis"] = "instant" if basis == "annual" else "annual"
    with pytest.raises(ValidationError):
        type(manifest).model_validate(changed)
