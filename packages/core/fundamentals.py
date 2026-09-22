"""S6a pure assembly of existing S5 calculations into the approved public payload."""

import json
import re
from decimal import Decimal
from typing import Literal, cast
from urllib.parse import urlsplit
from uuid import UUID

from equity_core.assessment import (
    _CALCULATORS,
    MetricAssessment,
    Observation,
    coverage,
    evaluate,
    observations,
    review_items,
)
from equity_core.history import HistoryPoint, compare_to_history, historical_band
from equity_core.inputs import FinancialInput
from equity_core.metrics import Calculation, reported_amount, revenue_growth
from equity_core.periods import (
    PeriodAmount,
    _month_span,
    annual_amount,
    quarter_from_ytd,
    ttm_from_annual_ytd,
    ttm_from_quarters,
)
from equity_core.reconciliation import balance_sheet_identity
from equity_core.trends import growth_trend
from equity_schema.fundamentals import (
    FundamentalsPayload,
    InputManifest,
    MetricSpec,
    OperandSpec,
    PublicAccounting,
    PublicCoverage,
    PublicEvidence,
    PublicHistory,
    PublicMetric,
    PublicObservation,
    PublicOperand,
    PublicTrend,
)
from equity_schema.fundamentals_canonical import content_hash


def _number(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _operand(spec: OperandSpec, manifest: InputManifest) -> FinancialInput | PeriodAmount:
    sources = tuple(manifest.sources[index] for index in spec.source_indices)
    if spec.method == "selected" and len(sources) == 1:
        if spec.revision_compatibility is not None:
            raise ValueError("A selected source cannot use assembly revision evidence")
        if spec.calendar_evidence is not None and spec.calendar_evidence.problems(sources):
            raise ValueError("Selected fiscal evidence does not match its source")
        return sources[0]
    if spec.method == "annual" and len(sources) == 1 and spec.revision_compatibility is None:
        return annual_amount(sources[0], calendar_evidence=spec.calendar_evidence)
    if spec.method == "quarters" and sources:
        return ttm_from_quarters(
            sources,
            calendar_evidence=spec.calendar_evidence,
            revision_compatibility=spec.revision_compatibility,
        )
    if spec.method == "ytd" and len(sources) == 2 and spec.revision_compatibility is None:
        return quarter_from_ytd(*sources, calendar_evidence=spec.calendar_evidence)
    if spec.method == "annual_ytd" and len(sources) == 3:
        return ttm_from_annual_ytd(
            *sources,
            calendar_evidence=spec.calendar_evidence,
            revision_compatibility=spec.revision_compatibility,
        )
    raise ValueError("Unsupported operand assembly or arity")


def _calculate(spec: MetricSpec, manifest: InputManifest) -> Calculation:
    operands = tuple(_operand(item, manifest) for item in spec.operands)
    if spec.metric_id.startswith("reported.") and len(operands) == 1:
        result = reported_amount(operands[0])
    elif spec.metric_id in _CALCULATORS:
        count, calculator = _CALCULATORS[spec.metric_id]
        if len(operands) != count:
            return Calculation(
                spec.metric_id, None, spec.unit, operands, ("source_input_unavailable",)
            )
        if spec.metric_id in {"return_on_assets", "current_ratio", "net_working_capital"} and any(
            not isinstance(item, FinancialInput) for item in operands
        ):
            raise ValueError("Balance metric requires selected instant/annual operands")
        if spec.metric_id == "revenue_growth_yoy":
            result = revenue_growth(
                *operands,
                calendar_evidence=spec.calendar_evidence,
                revision_compatibility=spec.revision_compatibility,
            )
        else:
            if spec.calendar_evidence is not None or spec.revision_compatibility is not None:
                raise ValueError("Unused metric-level review evidence")
            result = calculator(*operands)
    else:
        return Calculation(
            spec.metric_id, None, spec.unit, operands, ("unsupported_metric_definition",)
        )
    if result.metric_id != spec.metric_id or result.unit != spec.unit:
        raise ValueError("Metric request does not match the supported formula/unit")
    return result


def _safe_url(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        url = urlsplit(value)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            return None
    except ValueError:
        return None
    return value


def _evidence(source: FinancialInput, index: int, manifest: InputManifest) -> PublicEvidence:
    fact = source.fact
    try:
        transform = json.loads(fact.transform_json or "null") if fact else None
    except (ValueError, TypeError):
        transform = None
    identity_transform = transform == {"operation": "identity_decimal", "scale_applied": False}
    captures = {c.capture_id: c for c in manifest.captures}
    lexical = fact.original_numeric_text if fact else None
    if lexical is not None and not re.fullmatch(
        r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", lexical
    ):
        lexical = None
    return PublicEvidence(
        input_index=index,
        concept=source.concept.value,
        source_url=_safe_url(fact.source_url) if fact else None,
        accession=fact.accession if fact else None,
        filed_on=fact.filed_date if fact else None,
        capture_ids=fact.capture_ids if fact else (),
        retrieved_at=tuple(captures[c].fetched_at for c in fact.capture_ids) if fact else (),
        source_tag=fact.source_tag if fact else None,
        original_numeric_text=lexical,
        normalization_operation="identity_decimal" if identity_transform else None,
        transform_hash=content_hash(transform) if transform is not None else None,
        mapping_revision_id=source.selection.query.mapping_revision_id,
        normalizer_revision=source.selection.query.normalizer_revision,
        selection_hash=source.selection.input_hash,
        scope_kind=source.scope.scope_kind,
        scope_hash=source.scope.content_sha256,
        source_hashes=fact.source_hashes if fact else (),
        resolution_ids=fact.resolution_ids if fact else (),
        observation_ids=fact.observation_ids if fact else (),
        period_start=source.period.start_date,
        period_end=source.period.end_date,
        unit=source.unit.unit_key,
        value=_number(source.value),
        absolute_error=_number(source.precision.absolute_error) if source.precision else None,
        flags=source.flags,
    )


def _observation(item: Observation) -> PublicObservation:
    return PublicObservation(
        rule_id=item.rule_id,
        rule_revision=item.rule_revision,
        topic=item.topic,
        category=item.category,
        text=item.text,
        metric_ids=tuple(metric.calculation.metric_id for metric in item.metrics),
    )


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
                "quote_identifier_id",
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


def _public_operand(item: FinancialInput | PeriodAmount, spec: OperandSpec) -> PublicOperand:
    return PublicOperand(
        input_indices=spec.source_indices,
        coefficients=item.coefficients if isinstance(item, PeriodAmount) else (1,),
        period_start=item.period.start_date,
        period_end=item.period.end_date,
        value=_number(item.value),
        absolute_error=_number(item.precision.absolute_error) if item.precision else None,
        formula_id=item.formula_id if isinstance(item, PeriodAmount) else "selected_source",
        formula_revision=item.formula_revision
        if isinstance(item, PeriodAmount)
        else "s5-source-metrics-v1",
        reasons=item.flags,
        review_hash=content_hash(spec),
    )


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
        version="s6-fundamentals-v1",
        evidence_mode=manifest.evidence_mode,
        fixture_label=manifest.fixture_label,
        selector=manifest.selector,
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
        review_items=tuple(_observation(item) for item in review_items(tuple(assessed))),
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
