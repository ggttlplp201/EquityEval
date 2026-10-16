"""D049 real-v2 candidate assembly using unchanged S5 engines and publication contracts."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from equity_core.assessment import SUPPORTED_METRICS, EvaluationContext, FreshnessPolicy
from equity_core.history import HistoryPolicy
from equity_core.inputs import FinancialInput, PrecisionEvidence
from equity_core.real_fundamentals import calculate_payload, precision_error
from equity_core.trends import TrendPolicy
from equity_ingest.archive import LocalArchive
from equity_ingest.financial_types import NormalizationBundle
from equity_schema.fundamentals import CaptureInput, MetricSpec, OperandSpec
from equity_schema.fundamentals_canonical import content_hash
from equity_schema.pit import read_statement
from equity_schema.real_fundamentals import (
    RealInputManifest,
    RealSelectionKey,
    RetainedPolicyEvidence,
    RetainedPrecisionEvidence,
)
from equity_schema.real_fundamentals_store import _verify_sources, engine_revision, policy_document
from equity_schema.workflow import Database

from scripts.normalize_crcl import ROOT
from scripts.publish_crcl_broader import (
    INPUT_HASH,
    OUTPUT_HASH,
    checked_preparation,
    source_queries,
)
from scripts.review_crcl_broader import BLOCKED, FINDINGS
from scripts.review_crcl_safety import business_profile

OPERANDS = {
    "operating_margin": ("operating_income", "revenue"),
    "net_margin_consolidated": ("net_income_consolidated", "revenue"),
    "free_cash_flow_ppe": ("cash_from_operating_activities", "capital_expenditures_ppe"),
    "free_cash_flow_margin_ppe": (
        "cash_from_operating_activities",
        "capital_expenditures_ppe",
        "revenue",
    ),
    "current_ratio": ("current_assets", "current_liabilities"),
    "net_working_capital": ("current_assets", "current_liabilities"),
}
RATIONALES = {
    "operating_margin": (
        "Reported signed operating result / total revenue including reserve income. "
        "Descriptive annual ratio, not adjusted or recurring profit."
    ),
    "net_margin_consolidated": FINDINGS["attribution"] + " Denominator includes reserve income.",
    "free_cash_flow_ppe": FINDINGS["cash_flow"],
    "free_cash_flow_margin_ppe": FINDINGS["cash_flow"]
    + " Denominator is total revenue including reserve income.",
    "current_ratio": FINDINGS["liquidity"],
    "net_working_capital": FINDINGS["liquidity"],
}


def build_manifest(
    db: Database,
    *,
    bundle: NormalizationBundle,
    proof: dict[str, Any],
    batch_id: UUID,
    security_id: UUID,
    evaluated_at: datetime,
    period_basis: Literal["annual", "instant"],
) -> RealInputManifest:
    if (bundle.input_manifest_hash, bundle.output_manifest_hash) != (
        INPUT_HASH,
        OUTPUT_HASH,
    ) or bundle.quality_flags:
        raise ValueError("Only exact reviewed D5k source batch is in scope")
    if evaluated_at.utcoffset() is None or evaluated_at < bundle.inputs.captured_before:
        raise ValueError("Evaluation must follow source observation")
    if period_basis not in {"annual", "instant"}:
        raise ValueError("Only annual and closing-instant selectors are reviewed")
    active = {
        m: operands
        for m, operands in OPERANDS.items()
        if (m in {"current_ratio", "net_working_capital"}) == (period_basis == "instant")
    }
    used = {c for operands in active.values() for c in operands} | {
        "total_assets",
        "total_liabilities",
        "equity_including_noncontrolling_interests",
    }
    captures = {c.id: c for c in bundle.inputs.captures}
    periods = {p.id: p for p in bundle.periods}
    units = {u.id: u for u in bundle.units}
    scopes = {s.id: s for s in bundle.scopes}
    sources: list[FinancialInput] = []
    precision = []
    for query in source_queries(bundle, batch_id):
        if query.concepts[0].value not in used:
            continue
        index = len(sources)
        selection = read_statement(db, query)
        if (
            not selection.usable_for_valuation
            or selection.flags
            or selection.quality_flag_ids
            or len(selection.facts) != 1
        ):
            raise ValueError("Each selected broader source must be eligible independently")
        concept = query.concepts[0]
        item = proof[concept.value]
        fact = item["fact"]
        capture = captures[UUID(item["capture_id"])]
        sources.append(
            FinancialInput(
                selection,
                concept,
                periods[query.period_id],
                units[query.unit_id],
                scopes[query.scope_id],
                PrecisionEvidence(
                    precision_error(fact["decimals"]),
                    selection.facts[0].observation_ids,
                    (f"capture:{capture.id}:{capture.body_sha256}:{fact['locator']}",),
                    "reported_inline_decimals_half_unit-v1",
                ),
            )
        )
        precision.append(
            RetainedPrecisionEvidence(
                input_index=index,
                capture_id=capture.id,
                body_sha256=capture.body_sha256,
                source_url=capture.request_url,
                fetched_at=capture.fetched_at,
                accession=item["accession"],
                qualified_tag=fact["qualified_tag"],
                context_id=fact["context_id"],
                unit_id=fact["unit_id"],
                locator=fact["locator"],
                decimals=fact["decimals"],
                scale=fact["scale"],
                sign=fact["sign"],
            )
        )
    indices = {s.concept.value: i for i, s in enumerate(sources)}
    original = captures[UUID(proof["revenue"]["capture_id"])]
    policy_evidence = (
        RetainedPolicyEvidence(
            capture_id=original.id,
            body_sha256=original.body_sha256,
            locator="document",
            purpose="business_applicability",
        ),
    )
    refs = tuple(f"capture:{p.capture_id}:{p.body_sha256}:document" for p in policy_evidence)
    as_of = evaluated_at.astimezone(UTC).date()
    profile = business_profile(bundle.inputs.issuer_id)
    profile = replace(
        profile,
        revision=f"d5k-crcl-reported-{period_basis}-v1",
        instrument_basis="consolidated_issuer",
        effective_on=as_of,
        known_on=as_of,
        evidence_refs=refs,
        rules=tuple(
            replace(
                r,
                applicable=True if r.metric_id in active else None,
                rationale=(
                    RATIONALES[r.metric_id]
                    if r.metric_id in active
                    else "Other period scope: this metric is reviewed only in the companion "
                    + (
                        "closing-instant result using December 31 "
                        "current assets/current liabilities. "
                        if period_basis == "annual"
                        else "annual result using full-year income/cash-flow operands. "
                    )
                    + "Those operands are not included as metric inputs in this selector; "
                    "no cross-period formula evaluation is authorized."
                    if r.metric_id in OPERANDS
                    else BLOCKED[r.metric_id]
                ),
            )
            for r in profile.rules
        ),
    )
    context = EvaluationContext(
        as_of,
        profile,
        FreshnessPolicy(
            "d5k-annual-historical-365d-v1", 365, ("docs/design/d5k/proposal.md", *refs)
        ),
    )
    history = HistoryPolicy(3, 12, "d5k-history-unproved-v1")
    trend = TrendPolicy(
        Decimal(0), "d5k-quarterly-trend-unavailable-v1", ("No quarterly trend inputs approved",)
    )
    selected_period = next(
        p
        for p in bundle.periods
        if (p.start_date is not None) == (period_basis == "annual")
        and p.end_date == date(2025, 12, 31)
    )
    selector = RealSelectionKey(
        issuer_id=bundle.inputs.issuer_id,
        security_id=security_id,
        selection_kind="issuer_fundamentals",
        period_basis=period_basis,
        period_start=selected_period.start_date,
        period_end=selected_period.end_date,
        reporting_basis="us_gaap",
        currency="USD",
        history_mode="as_filed_by_date",
        filed_cutoff=query.filed_cutoff,
        captured_before=bundle.inputs.captured_before,
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
                    source_indices=(indices[concept],),
                    calendar_evidence=None,
                    revision_compatibility=None,
                )
                for concept in active.get(metric, ())
            ),
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
            for c in bundle.inputs.captures
        ),
        sources=tuple(sources),
        metrics=metrics,
        trend_inputs=(),
        history_samples=(),
        accounting_source_indices=tuple(
            indices[c]
            for c in (
                "total_assets",
                "total_liabilities",
                "equity_including_noncontrolling_interests",
            )
        ),
    )


def application_candidate(
    evaluated_at: datetime, period_basis: Literal["annual", "instant"]
) -> dict[str, Any]:
    from scripts import app_postgres

    if evaluated_at.utcoffset() is None or evaluated_at > datetime.now(UTC):
        raise ValueError("Live evaluation cannot be in the future")
    bundle, proof = checked_preparation()
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as db:
        db.execute("SET default_transaction_read_only=on")
        batch = db.execute(
            "SELECT id FROM normalization_batches WHERE input_manifest_hash=%s", (INPUT_HASH,)
        ).fetchone()
        securities = db.execute(
            "SELECT id FROM securities WHERE issuer_id=%s", (bundle.inputs.issuer_id,)
        ).fetchall()
        if not batch or len(securities) != 1:
            raise ValueError("Published D5k source batch or unique security missing")
        manifest = build_manifest(
            db,
            bundle=bundle,
            proof=proof,
            batch_id=batch["id"],
            security_id=securities[0]["id"],
            evaluated_at=evaluated_at,
            period_basis=period_basis,
        )
        _verify_sources(db, manifest, LocalArchive(ROOT / "var/raw"))
        payload = calculate_payload(manifest, history_payloads={})
        return {
            "kind": "d5k-real-fundamentals-preparation",
            "sourceObservation": manifest.selector.captured_before.isoformat(),
            "evaluatedAt": evaluated_at.isoformat(),
            "manifest": manifest,
            "payload": payload,
            "manifestHash": content_hash(manifest),
            "payloadHash": content_hash(payload),
            "policyHash": content_hash(policy_document(manifest)),
        }


def main() -> None:
    import argparse

    from equity_schema.fundamentals_canonical import canonical_json

    from scripts.publish_crcl_fundamentals import _write_exclusive

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluated-at", required=True)
    args = parser.parse_args()
    evaluated_at = datetime.fromisoformat(args.evaluated_at)
    bases: tuple[Literal["annual", "instant"], ...] = ("annual", "instant")
    reports = [(basis, application_candidate(evaluated_at, basis)) for basis in bases]
    for basis, report in reports:
        path = ROOT / f"docs/research/crcl-broader-{basis}-candidate-2026-10-15.json"
        if path.exists():
            if path.read_text() != canonical_json(report) + "\n":
                raise ValueError("Existing immutable candidate differs")
        else:
            _write_exclusive(path, report)
        print(
            canonical_json(
                {
                    "path": str(path),
                    **{key: report[key] for key in ("manifestHash", "payloadHash", "policyHash")},
                }
            )
        )


if __name__ == "__main__":
    main()
