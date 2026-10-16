"""D048 explicit CRCL real-v2 input assembly; no acquisition or publication."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from equity_core.assessment import SUPPORTED_METRICS, EvaluationContext, FreshnessPolicy
from equity_core.history import HistoryPolicy
from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_core.real_fundamentals import precision_error
from equity_core.trends import TrendPolicy
from equity_ingest.financial_types import NormalizationBundle
from equity_schema.concepts import Concept
from equity_schema.fundamentals import CaptureInput, MetricSpec, OperandSpec
from equity_schema.fundamentals_canonical import content_hash
from equity_schema.pit import HistoryMode, PitQuery, read_statement
from equity_schema.real_fundamentals import (
    RealInputManifest,
    RealSelectionKey,
    RetainedPolicyEvidence,
    RetainedPrecisionEvidence,
)
from equity_schema.real_fundamentals_store import engine_revision
from equity_schema.workflow import Database

from scripts.normalize_crcl import RESOURCES
from scripts.publish_crcl_observation import INPUT_HASH, OUTPUT_HASH
from scripts.review_crcl_safety import business_profile

REQUIREMENTS = {
    "revenue_growth_yoy": "Require FY2024 total revenue comparable with FY2025 total revenue, "
    "including reserve-income in both years; review annual period/edition consistency and "
    "reserve-yield/USDC-volume business applicability before interpreting growth.",
    "gross_margin": "Require FY2025 consolidated gross profit and total revenue; review whether "
    "reported cost classification includes distribution and transaction costs and whether gross "
    "margin meaningfully describes reserve-income economics.",
    "gross_margin_derived": "Require FY2025 consolidated cost of revenue and total revenue; "
    "review distribution and transaction cost classification, sign and matching scope before "
    "deriving gross profit for this reserve-income issuer.",
    "net_margin_consolidated": "Require FY2025 consolidated net income and total revenue; review "
    "consolidated versus parent attribution, tax and non-operating items and reserve-income "
    "applicability; do not substitute operating income.",
    "free_cash_flow_ppe": "Require FY2025 consolidated operating cash flow and cash PPE purchases "
    "with matching period, edition and cash-outflow sign; review token-holder reserve/customer "
    "flows and restricted cash before treating the result as issuer-discretionary cash.",
    "free_cash_flow_margin_ppe": "Require FY2025 consolidated operating cash flow, cash PPE "
    "purchases and total revenue with matching period/edition/sign; review token-holder reserve "
    "flows, restricted cash and reserve-income denominator applicability.",
    "current_ratio": "Require FY2025 year-end current assets and current liabilities; review "
    "classification of segregated USDC reserves, token-holder obligations and restricted versus "
    "issuer-available assets before approving liquidity applicability.",
    "net_working_capital": "Require FY2025 year-end current assets and current liabilities; "
    "review segregated reserve/token-holder balance classification and issuer-available working "
    "capital scope before interpreting their difference.",
    "return_on_assets": "Require FY2025 consolidated net income and comparable opening "
    "2024-12-31 and closing 2025-12-31 total assets; review period/edition consistency and "
    "whether token-holder reserve assets make the consolidated asset denominator meaningful.",
}


def build_manifest(
    db: Database,
    *,
    bundle: NormalizationBundle,
    proof: dict[str, Any],
    batch_id: UUID,
    security_id: UUID,
    evaluated_at: datetime,
) -> RealInputManifest:
    if (
        bundle.input_manifest_hash != INPUT_HASH
        or bundle.output_manifest_hash != OUTPUT_HASH
        or bundle.quality_flags
    ):
        raise ValueError("Only the reviewed eligible D5i source batch is in scope")
    if evaluated_at.utcoffset() is None or evaluated_at < bundle.inputs.captured_before:
        raise ValueError("Evaluation must follow the exact retained observation")
    records = db.execute(
        """SELECT DISTINCT c.period_id,c.scope_id,c.currency_unit_id,r.unit_id
    FROM statement_coverage c JOIN fact_resolutions r ON r.coverage_id=c.id WHERE c.batch_id=%s""",
        (batch_id,),
    ).fetchall()
    if len(records) != 1:
        raise ValueError("CRCL expects one reviewed annual statement")
    row = records[0]
    inputs = bundle.inputs
    query = PitQuery(
        issuer_id=inputs.issuer_id,
        period_id=row["period_id"],
        scope_id=row["scope_id"],
        unit_id=row["unit_id"],
        reporting_currency_unit_id=row["currency_unit_id"],
        statement_family="income",
        concepts=(Concept.OPERATING_INCOME,),
        batch_ids=(batch_id,),
        capture_ids=tuple(c.id for c in inputs.captures),
        filing_event_ids=(),
        mapping_revision_id=inputs.mapping_revision_id,
        normalizer_revision=inputs.normalizer_revision,
        authority_policy_revision=inputs.authority_policy_revision,
        captured_before=inputs.captured_before,
        mode=HistoryMode.AS_FILED_BY_DATE,
        filed_cutoff=date(2026, 10, 15),
        audited_required=True,
    )
    period = next(p for p in bundle.periods if p.id == row["period_id"])
    unit = next(u for u in bundle.units if u.id == row["unit_id"])
    scope = next(s for s in bundle.scopes if s.id == row["scope_id"])
    captures = {c.id: c for c in inputs.captures}
    sources = []
    precision = []
    for index, concept in enumerate((Concept.OPERATING_INCOME, Concept.REVENUE)):
        selected = read_statement(db, replace(query, concepts=(concept,)))
        if (
            not selected.usable_for_valuation
            or selected.flags
            or selected.quality_flag_ids
            or len(selected.facts) != 1
        ):
            raise ValueError("Current selected source is not independently eligible")
        item = proof[concept.value]
        fact = item["fact"]
        capture = captures[UUID(item["capture_id"])]
        ref = f"capture:{capture.id}:{capture.body_sha256}:{fact['locator']}"
        sources.append(
            FinancialInput(
                selected,
                concept,
                period,
                unit,
                scope,
                PrecisionEvidence(
                    precision_error(fact["decimals"]),
                    selected.facts[0].observation_ids,
                    (ref,),
                    "reported_inline_decimals_half_unit-v1",
                ),
            )
        )
        accession = selected.facts[0].accession
        if accession is None:
            raise ValueError("Selected operating fact has no filing accession")
        precision.append(
            RetainedPrecisionEvidence(
                input_index=index,
                capture_id=capture.id,
                body_sha256=capture.body_sha256,
                source_url=capture.request_url,
                fetched_at=capture.fetched_at,
                accession=accession,
                qualified_tag=fact["qualified_tag"],
                context_id=fact["context_id"],
                unit_id=fact["unit_id"],
                locator=fact["locator"],
                decimals=fact["decimals"],
                scale=fact["scale"],
                sign=fact["sign"],
            )
        )
    policy_captures = [
        captures[UUID(proof["revenue"]["capture_id"])],
        next(c for c in inputs.captures if c.source_object_key == RESOURCES[3]),
    ]
    policy_evidence = tuple(
        RetainedPolicyEvidence(
            capture_id=c.id,
            body_sha256=c.body_sha256,
            locator="document",
            purpose="business_applicability",
        )
        for c in policy_captures
    )
    refs = tuple(f"capture:{p.capture_id}:{p.body_sha256}:document" for p in policy_evidence)
    as_of = evaluated_at.astimezone(UTC).date()
    original_profile = business_profile(inputs.issuer_id)
    profile = replace(
        original_profile,
        rules=tuple(
            replace(rule, rationale=REQUIREMENTS[rule.metric_id])
            if rule.applicable is None
            else rule
            for rule in original_profile.rules
        ),
        revision="d5j-crcl-reported-operating-margin-v1",
        instrument_basis="consolidated_issuer",
        effective_on=as_of,
        known_on=as_of,
        evidence_refs=refs,
    )
    context = EvaluationContext(
        as_of,
        profile,
        FreshnessPolicy(
            "d5j-annual-historical-365d-v1",
            365,
            ("docs/design/d5j/proposal.md#first-production-policy-and-numerical-scope", *refs),
        ),
    )
    history = HistoryPolicy(3, 12, "d5j-no-inferred-history-v1")
    trend = TrendPolicy(
        Decimal(0), "d5j-trend-unavailable-v1", ("No quarterly trend inputs approved",)
    )
    selector = RealSelectionKey(
        issuer_id=inputs.issuer_id,
        security_id=security_id,
        selection_kind="issuer_fundamentals",
        period_basis="annual",
        period_start=period.start_date,
        period_end=period.end_date,
        reporting_basis="us_gaap",
        currency="USD",
        history_mode="as_filed_by_date",
        filed_cutoff=query.filed_cutoff,
        captured_before=inputs.captured_before,
        as_of=as_of,
        evaluated_at=evaluated_at,
        profile_revision=profile.revision,
        freshness_revision=context.freshness.revision,
        history_revision=history.revision,
        trend_revision=trend.revision,
        policy_content_hash=content_hash((context, history, trend)),
        history_years=3,
        engine_revision=engine_revision(),
    )
    metrics = tuple(
        MetricSpec(
            metric_id=metric,
            unit="USD"
            if metric in {"free_cash_flow_ppe", "net_working_capital"}
            else "multiple"
            if metric == "current_ratio"
            else "fraction",
            operands=tuple(
                OperandSpec(
                    method="selected",
                    source_indices=(i,),
                    calendar_evidence=None,
                    revision_compatibility=None,
                )
                for i in range(2)
            )
            if metric == "operating_margin"
            else (),
            calendar_evidence=None,
            revision_compatibility=None,
        )
        for metric in SUPPORTED_METRICS
    )
    return RealInputManifest(
        version="s6-input-v2",
        evidence_mode="real",
        selector=selector,
        policy_evidence=policy_evidence,
        precision_evidence=tuple(precision),
        context=context,
        history_policy=history,
        trend_policy=trend,
        captures=tuple(
            CaptureInput(capture_id=c.id, fetched_at=c.fetched_at, body_sha256=c.body_sha256)
            for c in inputs.captures
        ),
        sources=tuple(sources),
        metrics=metrics,
        trend_inputs=(),
        history_samples=(),
        accounting_source_indices=(),
    )


def application_candidate(evaluated_at: datetime) -> dict[str, Any]:
    """Read only the existing D5i batch; never provision source or quote records."""
    from equity_core.real_fundamentals import calculate_payload
    from equity_ingest.archive import LocalArchive
    from equity_schema.real_fundamentals_store import _verify_sources, policy_document

    from scripts import app_postgres
    from scripts.normalize_crcl import ROOT
    from scripts.publish_crcl_observation import checked_preparation

    bundle, proof = checked_preparation()
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as db:
        db.execute("SET default_transaction_read_only=on")
        batch = db.execute(
            "SELECT id FROM normalization_batches WHERE input_manifest_hash=%s",
            (INPUT_HASH,),
        ).fetchone()
        securities = db.execute(
            "SELECT id FROM securities WHERE issuer_id=%s", (bundle.inputs.issuer_id,)
        ).fetchall()
        if not batch or len(securities) != 1:
            raise ValueError("Missing D5i batch or ambiguous registered security")
        manifest = build_manifest(
            db,
            bundle=bundle,
            proof=proof,
            batch_id=batch["id"],
            security_id=securities[0]["id"],
            evaluated_at=evaluated_at,
        )
        _verify_sources(db, manifest, LocalArchive(ROOT / "var/raw"))
        payload = calculate_payload(manifest, history_payloads={})
        return {
            "kind": "d5j-real-fundamentals-preparation",
            "normalizationBatchId": str(batch["id"]),
            "manifest": manifest,
            "payload": payload,
            "manifestHash": content_hash(manifest),
            "payloadHash": content_hash(payload),
            "policyHash": content_hash(policy_document(manifest)),
            "sourceObservation": manifest.selector.captured_before,
            "evaluatedAt": evaluated_at,
            "sourceScope": "Retrospective FY2025 annual filing-date selection through the exact "
            "D5i observation; evaluation does not extend source knowledge.",
            "publicationStatus": "not_published",
        }
