"""Real-v2 pure assembly using existing S5 calculations, without synthetic coercion."""

import re
from decimal import Decimal, localcontext
from typing import Literal, cast
from uuid import UUID

from equity_core.assessment import (
    MetricAssessment,
    coverage,
    evaluate,
    observations,
    review_items,
)
from equity_core.fundamentals import _calculate as _shared_calculate
from equity_core.fundamentals import _evidence as _shared_evidence
from equity_core.fundamentals import _number, _observation, _public_operand
from equity_core.history import HistoryPoint, compare_to_history, historical_band
from equity_core.inputs import FinancialInput
from equity_core.metrics import Calculation
from equity_core.periods import (
    PeriodAmount,
    _month_span,
)
from equity_core.reconciliation import balance_sheet_identity
from equity_core.trends import growth_trend
from equity_schema.fundamentals import InputManifest as V1Manifest
from equity_schema.fundamentals import (
    MetricSpec,
    PublicAccounting,
    PublicCoverage,
    PublicEvidence,
    PublicHistory,
    PublicMetric,
    PublicObservation,
    PublicTrend,
)
from equity_schema.fundamentals_canonical import content_hash
from equity_schema.real_fundamentals import (
    RealFundamentalsPayload as FundamentalsPayload,
)
from equity_schema.real_fundamentals import (
    RealInputManifest as InputManifest,
)


def _calculate(spec: MetricSpec, manifest: InputManifest) -> Calculation:
    # Structural helper reuse only: no synthetic manifest/label is constructed.
    return _shared_calculate(spec, cast(V1Manifest, manifest))


def _evidence(source: FinancialInput, index: int, manifest: InputManifest) -> PublicEvidence:
    return _shared_evidence(source, index, cast(V1Manifest, manifest))


def _histories(
    manifest: InputManifest,
    metrics: tuple[PublicMetric, ...],
    history_payloads: dict[UUID, FundamentalsPayload],
) -> tuple[PublicHistory, ...]:
    if set(history_payloads) != {ref.snapshot_id for ref in manifest.history_samples}:
        raise ValueError("Historical payload manifest must match exact snapshot references")
    results = []
    selection = manifest.selector
    for metric in metrics:
        series = content_hash(
            (
                metric.metric_id,
                metric.formula_revision,
                metric.unit,
                selection.issuer_id,
                selection.security_id,
                selection.period_basis,
                selection.reporting_basis,
                selection.currency,
                selection.history_mode,
                selection.profile_revision,
                selection.freshness_revision,
                selection.engine_revision,
            )
        )
        points = []
        refs = {}
        for ref in manifest.history_samples:
            payload = history_payloads[ref.snapshot_id]
            if content_hash(payload) != ref.payload_hash:
                raise ValueError("Historical snapshot payload hash mismatch")
            old = next((m for m in payload.metrics if m.metric_id == metric.metric_id), None)
            old_selector = payload.selector
            flags: set[str] = set()
            fields = (
                "issuer_id",
                "security_id",
                "selection_kind",
                "period_basis",
                "reporting_basis",
                "currency",
                "history_mode",
                "profile_revision",
                "freshness_revision",
                "engine_revision",
            )
            if payload.comparison_policy_hash != content_hash(
                (manifest.context.profile, manifest.context.freshness)
            ) or any(getattr(selection, name) != getattr(old_selector, name) for name in fields):
                flags.add("incompatible_series")
            if (
                old_selector.as_of != ref.quarter_end
                or old_selector.evaluated_at.date() != ref.quarter_end
            ):
                flags.add("historical_evaluation_date_mismatch")
            if old is None or old.status != "valid":
                flags.add("historical_metric_unavailable")
            elif old.unit != metric.unit or old.formula_revision != metric.formula_revision:
                flags.add("incompatible_series")
            point = HistoryPoint(
                ref.quarter_end,
                Decimal(old.value) if old and old.value else None,
                series,
                ref.payload_hash,
                tuple(sorted(flags)),
            )
            points.append(point)
            refs[id(point)] = (
                ref.snapshot_id
            )  # Preserve duplicate evidence's distinct envelope IDs.
        band = historical_band(
            tuple(points), as_of=selection.as_of, series_key=series, policy=manifest.history_policy
        )
        comparison = compare_to_history(
            Decimal(metric.value) if metric.value else None,
            band,
            series_key=series,
            input_hash=metric.input_hash,
            flags=() if metric.status == "valid" else ("current_metric_unavailable",),
        )
        results.append(
            PublicHistory(
                metric_id=metric.metric_id,
                years=manifest.selector.history_years,
                minimum_samples=band.minimum_samples,
                window_start=band.window_start,
                window_end=band.window_end,
                eligible_snapshot_ids=tuple(refs[id(point)] for point in band.eligible),
                excluded=tuple((refs[id(item.point)], item.reasons) for item in band.excluded),
                missing_quarter_ends=band.missing_quarter_ends,
                p25=_number(band.p25),
                p50=_number(band.p50),
                p75=_number(band.p75),
                relation=comparison.relation,
                reasons=comparison.flags,
            )
        )
    return tuple(results)


def calculate_payload(
    manifest: InputManifest, *, history_payloads: dict[UUID, FundamentalsPayload]
) -> FundamentalsPayload:
    assessed: list[MetricAssessment] = []
    metrics = []
    for spec in manifest.metrics:
        if spec.metric_id.startswith("reported.") and any(
            (
                manifest.sources[index].scope.scope_kind != "consolidated"
                or manifest.sources[index].scope.instrument_id is not None
            )
            for operand in spec.operands
            for index in operand.source_indices
        ):
            raise ValueError("Reported issuer amounts require consolidated scope")
        calculation = _calculate(spec, manifest)
        profile = manifest.context.profile
        rule = next((rule for rule in profile.rules if rule.metric_id == spec.metric_id), None)
        if (
            rule is not None
            and rule.applicable is None
            and not spec.operands
            and profile.instrument_basis == "consolidated_issuer"
            and profile.effective_on <= manifest.context.as_of
            and profile.known_on <= manifest.context.as_of
        ):
            # A roster slot with no reviewed applicability or supplied operands is
            # not an attempted formula. Coverage independently retains it unresolved.
            metrics.append(
                PublicMetric(
                    metric_id=spec.metric_id,
                    value=None,
                    unit=spec.unit,
                    status="unsupported",
                    applicability=None,
                    reasons=(
                        "profile_applicability_unreviewed",
                        f"required_source_inputs_unavailable:{spec.metric_id}",
                        f"applicability_requirement:{rule.rationale}",
                    ),
                    formula_revision=calculation.formula_revision,
                    input_hash=content_hash(calculation),
                    input_indices=(),
                    operands=(),
                )
            )
            continue
        item = evaluate(calculation, manifest.context)
        if calculation.operands:
            target = cast(FinancialInput | PeriodAmount, calculation.operands[0])
            basis = manifest.selector.period_basis
            if isinstance(target, FinancialInput):
                proof = spec.operands[0].calendar_evidence
                if target.period.start_date is None:
                    compatible = basis == "instant"
                elif basis == "annual":
                    match = proof.match(target, cumulative=True) if proof else None
                    compatible = (
                        (match is not None and match[1] == 4)
                        if proof
                        else _month_span(target) == 12
                    )
                elif basis == "quarter":
                    compatible = (
                        proof.match(target, cumulative=False) is not None
                        if proof
                        else _month_span(target) == 3
                    )
                else:
                    compatible = False
            else:
                compatible = target.formula_id in {
                    "annual": {"direct_annual"},
                    "quarter": {"ytd_difference"},
                    "ttm": {"sum_four_quarters", "annual_ytd_bridge"},
                }.get(basis, set())
            if not compatible:
                raise ValueError("Metric does not match requested period basis")
            if target.period.end_date != manifest.selector.period_end or (
                target.period.start_date is not None
                and target.period.start_date != manifest.selector.period_start
            ):
                raise ValueError("Metric does not match the requested financial window")
        assessed.append(item)
        indices = tuple(
            sorted({index for operand in spec.operands for index in operand.source_indices})
        )
        metrics.append(
            PublicMetric(
                metric_id=spec.metric_id,
                value=_number(item.value),
                unit=spec.unit,
                status=item.status,
                applicability=item.applicability,
                reasons=item.reasons,
                formula_revision=calculation.formula_revision,
                input_hash=content_hash(calculation),
                input_indices=indices,
                operands=tuple(
                    _public_operand(cast(FinancialInput | PeriodAmount, operand), operand_spec)
                    for operand, operand_spec in zip(
                        calculation.operands, spec.operands, strict=True
                    )
                ),
            )
        )
    summary = coverage(tuple(assessed), context=manifest.context)
    trends = tuple(
        evaluate(_calculate(spec, manifest), manifest.context) for spec in manifest.trend_inputs
    )
    trend_ends = tuple(
        cast(FinancialInput | PeriodAmount, item.calculation.operands[0]).period.end_date
        for item in trends
        if item.calculation.operands
    )
    if trends and (
        len(trend_ends) != len(trends) or trend_ends[-1] != manifest.selector.period_end
    ):
        raise ValueError("Trend must end at the requested financial period")
    trend = growth_trend(trends, policy=manifest.trend_policy)
    accounting = None
    if manifest.accounting_source_indices:
        if any(
            manifest.sources[i].period.end_date != manifest.selector.period_end
            for i in manifest.accounting_source_indices
        ):
            raise ValueError("Accounting check must use requested financial period")
        check = balance_sheet_identity(
            *(manifest.sources[index] for index in manifest.accounting_source_indices)
        )
        accounting = PublicAccounting(
            period_end=manifest.selector.period_end,
            residual=_number(check.calculation.value),
            tolerance=_number(check.tolerance),
            matches=check.matches,
            input_indices=manifest.accounting_source_indices,
            reasons=check.calculation.flags,
            rule_revision=check.rule_revision,
        )
    return FundamentalsPayload(
        version="s6-fundamentals-v2",
        evidence_mode=manifest.evidence_mode,
        selector=manifest.selector,
        precision_evidence=manifest.precision_evidence,
        policy_evidence=manifest.policy_evidence,
        dependency_hash=content_hash(manifest),
        comparison_policy_hash=content_hash((manifest.context.profile, manifest.context.freshness)),
        metrics=tuple(metrics),
        evidence=tuple(_evidence(source, i, manifest) for i, source in enumerate(manifest.sources)),
        coverage=PublicCoverage(
            applicable_count=summary.applicable_count,
            covered_count=summary.covered_count,
            unresolved_count=summary.unresolved_count,
            fraction=_number(summary.coverage),
            counts=dict(summary.counts),
            revision=summary.revision,
        ),
        observations=tuple(_observation(item) for item in observations(tuple(assessed))),
        review_items=tuple(_observation(item) for item in review_items(tuple(assessed)))
        + (
            (
                PublicObservation(
                    rule_id="real-accounting-unavailable",
                    rule_revision="d5j-v1",
                    topic="accounting",
                    category="missing",
                    text=(
                        "Balance-sheet identity unavailable: assets, liabilities and "
                        "equity operands are not included."
                    ),
                    metric_ids=(),
                ),
            )
            if not manifest.accounting_source_indices
            else ()
        ),
        history=_histories(manifest, tuple(metrics), history_payloads),
        trend=PublicTrend(
            period_ends=trend_ends,
            input_indices=tuple(
                sorted(
                    {
                        i
                        for spec in manifest.trend_inputs
                        for o in spec.operands
                        for i in o.source_indices
                    }
                )
            ),
            rates=tuple(_number(item.value) for item in trends),
            input_statuses=tuple(item.status for item in trends),
            input_reasons=tuple(item.reasons for item in trends),
            relation=cast(
                Literal["rising", "falling", "broadly_stable", "mixed"] | None, trend.relation
            ),
            changes=tuple(str(value) for value in trend.changes),
            reasons=trend.flags,
            rule_revision=trend.rule_revision,
        ),
        accounting=accounting,
    )


def precision_error(decimals: str) -> Decimal:
    """Half the reported rounding unit; XBRL INF denotes exact source accuracy."""
    if decimals == "INF":
        return Decimal(0)
    if not re.fullmatch(r"[+-]?[0-9]{1,4}", decimals) or abs(int(decimals)) > 1000:
        raise ValueError("Unsupported source decimals")
    with localcontext() as ctx:
        ctx.prec = 36
        return Decimal("0.5") * (Decimal(10) ** -int(decimals))
