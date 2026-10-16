"""Fictional inputs for real-v2 contract tests; never application publication."""

from uuid import uuid4

from tests.fundamentals_seed import manifest


def real_manifest():
    from dataclasses import replace
    from datetime import UTC, date, datetime

    from equity_schema.fundamentals_canonical import content_hash
    from equity_schema.real_fundamentals import RealInputManifest

    fixture = manifest()
    context = replace(fixture.context, as_of=date(2026, 3, 1))
    selector = fixture.selector.model_copy(
        update={
            "as_of": context.as_of,
            "evaluated_at": datetime(2026, 3, 1, 23, tzinfo=UTC),
            "policy_content_hash": content_hash(
                (context, fixture.history_policy, fixture.trend_policy)
            ),
        }
    )
    old = fixture.model_copy(update={"context": context, "selector": selector}).model_dump(
        mode="json"
    )
    old.update(version="s6-input-v2", evidence_mode="real")
    old.pop("fixture_label")
    old["selector"].pop("quote_identifier_id")
    old["selector"]["selection_kind"] = "issuer_fundamentals"
    capture = old["captures"][0]
    old["policy_evidence"] = [
        {
            "capture_id": capture["capture_id"],
            "body_sha256": capture["body_sha256"],
            "locator": "test:profile",
            "purpose": "business_applicability",
        }
    ]
    old["precision_evidence"] = []
    return RealInputManifest.model_validate(old)


def quote_id():
    return str(uuid4())
