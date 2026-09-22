"""Synthetic S6 input contracts; database tracer adds governed real FK identities."""

from datetime import UTC, date, datetime
from decimal import Decimal

from equity_core.history import HistoryPolicy
from equity_core.trends import TrendPolicy
from equity_schema.concepts import Concept
from equity_schema.fundamentals import (
    CaptureInput,
    InputManifest,
    MetricSpec,
    OperandSpec,
    SelectionKey,
)
from equity_schema.fundamentals_canonical import content_hash

from tests.core.metric_fixtures import identity, operand
from tests.core.test_assessment import context


def manifest():
    ctx = context("operating_margin")
    history = HistoryPolicy(3, 12, "synthetic-history-v1")
    trend = TrendPolicy(Decimal(".01"), "synthetic-trend-v1", ("synthetic:policy",))
    selector = SelectionKey(
        issuer_id=identity("issuer"),
        security_id=identity("security"),
        quote_identifier_id=identity("quote"),
        period_basis="annual",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        reporting_basis="us_gaap",
        currency="USD",
        history_mode="as_filed_by_date",
        filed_cutoff=date(2026, 2, 28),
        captured_before=datetime(2026, 3, 1, tzinfo=UTC),
        as_of=ctx.as_of,
        evaluated_at=datetime(2026, 2, 28, tzinfo=UTC),
        profile_revision=ctx.profile.revision,
        freshness_revision=ctx.freshness.revision,
        history_revision=history.revision,
        trend_revision=trend.revision,
        policy_content_hash=content_hash((ctx, history, trend)),
        history_years=3,
        engine_revision="synthetic-engine-v1",
    )
    return InputManifest(
        version="s6-input-v1",
        evidence_mode="synthetic",
        fixture_label="Synthetic integration fixture — not company data",
        selector=selector,
        context=ctx,
        history_policy=history,
        trend_policy=trend,
        captures=(
            CaptureInput(
                capture_id=identity("capture"),
                fetched_at=selector.captured_before,
                body_sha256="a" * 64,
            ),
        ),
        sources=(operand(Concept.OPERATING_INCOME, "20"), operand(Concept.REVENUE, "100")),
        metrics=(
            MetricSpec(
                metric_id="operating_margin",
                unit="fraction",
                operands=tuple(
                    OperandSpec(
                        method="selected",
                        source_indices=(index,),
                        calendar_evidence=None,
                        revision_compatibility=None,
                    )
                    for index in range(2)
                ),
                calendar_evidence=None,
                revision_compatibility=None,
            ),
        ),
        trend_inputs=(),
        history_samples=(),
        accounting_source_indices=(),
    )


def database_manifest(owner, runtime):
    """Two fictional values, exact retained S3 selections, no live captures."""
    import json
    from dataclasses import replace
    from uuid import uuid4

    from equity_core.inputs import FinancialInput, PrecisionEvidence
    from equity_schema.fundamentals_store import engine_revision
    from equity_schema.pit import read_statement
    from equity_schema.workflow import create_workspace_watchlist
    from psycopg.types.json import Jsonb

    from tests.evidence_seed import insert, publish, seed_evidence

    draft = manifest()
    template = draft.sources[1]
    ids = seed_evidence(
        owner,
        concept="revenue",
        value=Decimal("100"),
        accession="0000000001-26-000001",
        filed_date="2026-02-01",
        start_date="2025-01-01",
        end_date="2025-12-31",
        captured_at="2026-03-01T00:00:00Z",
        descriptor=json.loads(template.scope.descriptor_json),
        scope_content_sha256=template.scope.content_sha256,
        transform_metadata={"operation": "identity_decimal", "scale_applied": False},
    )
    observation = owner.execute(
        "SELECT * FROM source_observations WHERE id=%s", (ids["observation"],)
    ).fetchone()
    observation.update(
        id=uuid4(),
        source_locator="test:/operating_income",
        numeric_value=Decimal("20"),
        original_numeric_text="20",
        tag="OperatingIncomeLoss",
    )
    for key in ("raw_dimensions", "transform_metadata", "raw_metadata"):
        observation[key] = Jsonb(observation[key])
    insert(owner, "source_observations", **observation)
    resolution = owner.execute(
        "SELECT * FROM fact_resolutions WHERE id=%s", (ids["resolution"],)
    ).fetchone()
    resolution.update(
        id=uuid4(), concept_std="operating_income", selected_observation_id=observation["id"]
    )
    insert(owner, "fact_resolutions", **resolution)
    publish(owner, ids["batch"])
    sources = []
    for concept in (Concept.OPERATING_INCOME, Concept.REVENUE):
        query = replace(
            template.selection.query,
            issuer_id=ids["issuer"],
            period_id=ids["period"],
            scope_id=ids["scope"],
            unit_id=ids["unit"],
            concepts=(concept,),
            batch_ids=(ids["batch"],),
            capture_ids=(ids["capture"],),
            mapping_revision_id=ids["mapping"],
            normalizer_revision="test-v1",
            authority_policy_revision="test-v1",
            reporting_currency_unit_id=ids["unit"],
            security_id=ids["security"],
        )
        selected = read_statement(runtime, query)
        sources.append(
            FinancialInput(
                selected,
                concept,
                replace(template.period, id=ids["period"]),
                replace(template.unit, id=ids["unit"]),
                replace(template.scope, id=ids["scope"], issuer_id=ids["issuer"]),
                PrecisionEvidence(
                    Decimal(".5"),
                    selected.facts[0].observation_ids,
                    ("synthetic:source-rounding-evidence",),
                    "synthetic_fixture",
                ),
            )
        )
    ctx = replace(draft.context, profile=replace(draft.context.profile, issuer_id=ids["issuer"]))
    selector = draft.selector.model_copy(
        update=dict(
            issuer_id=ids["issuer"],
            security_id=ids["security"],
            quote_identifier_id=ids["quote"],
            policy_content_hash=content_hash((ctx, draft.history_policy, draft.trend_policy)),
            engine_revision=engine_revision(),
        )
    )
    inputs = draft.model_copy(
        update=dict(
            sources=tuple(sources),
            context=ctx,
            selector=selector,
            captures=(
                CaptureInput(
                    capture_id=ids["capture"],
                    fetched_at=selector.captured_before,
                    body_sha256="a" * 64,
                ),
            ),
        )
    )
    workspace = create_workspace_watchlist(runtime, name="Synthetic S6 test workspace")
    return workspace, inputs


def request_options(inputs):
    from equity_schema.workflow import RequestedPeriod, RequestOptions

    s = inputs.selector
    return RequestOptions(
        history_mode=s.history_mode,
        filed_cutoff=s.filed_cutoff,
        requested_periods=(RequestedPeriod("duration", s.period_end, s.period_start),),
        retrieval_vintage=s.captured_before,
    )
