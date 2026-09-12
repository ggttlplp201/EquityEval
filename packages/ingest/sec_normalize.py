"""Conservative SEC Company Facts normalization of explicitly pinned archives.

Only caller-supplied reviewed mappings and coverage are used. This module does not
fetch, query a database, infer reporting authority, or compute financial totals.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date
from decimal import Decimal
from typing import Any
from uuid import UUID

from equity_schema.concepts import Concept

from .financial_types import (
    Candidate,
    Coverage,
    CoverageRequest,
    MappingRule,
    NormalizationBundle,
    NormalizationInput,
    Observation,
    PeriodSpec,
    QualityFlag,
    Resolution,
    ResolutionStatus,
    UnitSpec,
    canonical_json,
    content_hash,
    evidence_id,
)


@dataclass(frozen=True)
class JsonNumber:
    text: str
    value: Decimal


def _number(token: str) -> JsonNumber:
    return JsonNumber(token, Decimal(token))


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_companyfacts_json(body: bytes) -> dict[str, Any]:
    """Retain numeric tokens, including invalid nonfinite row values for diagnosis."""
    parsed: Any = json.loads(
        body.decode("utf-8"),
        parse_int=_number,
        parse_float=_number,
        parse_constant=_number,
        object_pairs_hook=_object,
    )
    if not isinstance(parsed, dict):
        raise ValueError("SEC document must be a JSON object")
    return parsed


def canonical_cik(value: Any) -> str:
    """Validate original integer/digit-string identity without lossy coercion."""
    if isinstance(value, JsonNumber):
        if not re.fullmatch(r"[0-9]+", value.text):
            raise ValueError("CIK must be a positive integer token")
        value = int(value.text)
    if type(value) is int:
        if not 0 < value < 10_000_000_000:
            raise ValueError("CIK outside SEC bounds")
        return f"{value:010d}"
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,10}", value) and int(value) > 0:
        return value.zfill(10)
    raise ValueError("CIK must be an integer or digit string")


def source_json(value: Any) -> str:
    """JSON evidence with original numeric token spelling; no float conversion."""
    if isinstance(value, JsonNumber):
        return value.text
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k) + ":" + source_json(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(source_json(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def period_spec(start: date | None, end: date) -> PeriodSpec:
    if start is not None and start > end:
        raise ValueError("Fact duration starts after its end")
    kind = "instant" if start is None else "duration"
    return PeriodSpec(evidence_id("period", [kind, start, end]), kind, start, end)


def unit_spec(key: str) -> UnitSpec:
    numerator: tuple[str, ...]
    denominator: tuple[str, ...]
    if key == "shares":
        numerator, denominator = ("xbrli:shares",), ()
    elif re.fullmatch(r"[A-Z]{3}", key):
        numerator, denominator = (f"iso4217:{key}",), ()
    elif re.fullmatch(r"[A-Z]{3}/shares", key):
        numerator, denominator = (f"iso4217:{key[:3]}",), ("xbrli:shares",)
    else:
        raise ValueError(f"Unsupported reviewed unit: {key}")
    return UnitSpec(evidence_id("unit", key), key, numerator, denominator)


def concept_unit(concept: Concept, currency: str) -> str:
    if concept in {Concept.EPS_BASIC, Concept.EPS_DILUTED}:
        return f"{currency}/shares"
    if concept in {
        Concept.WEIGHTED_AVERAGE_SHARES_BASIC,
        Concept.WEIGHTED_AVERAGE_SHARES_DILUTED,
        Concept.COMMON_SHARES_OUTSTANDING,
    }:
        return "shares"
    return currency


def _validate(inputs: NormalizationInput, body: bytes) -> None:
    if inputs.captured_before.utcoffset() is None:
        raise ValueError("Retrieval cutoff must be timezone aware")
    if inputs.cik != canonical_cik(inputs.cik):
        raise ValueError("Input CIK must already be canonical")
    if not inputs.requests or not inputs.captures or not inputs.filings:
        raise ValueError("Explicit captures, filing metadata and coverage requests are required")
    if not all(
        (inputs.parser_revision, inputs.normalizer_revision, inputs.authority_policy_revision)
    ):
        raise ValueError("Pinned parser/normalizer/authority revisions are required")
    captures = {capture.id: capture for capture in inputs.captures}
    if len(captures) != len(inputs.captures) or inputs.companyfacts_capture_id not in captures:
        raise ValueError("Unique capture manifest must contain the Company Facts body")
    capture = captures[inputs.companyfacts_capture_id]
    if len(body) != capture.byte_count or hashlib.sha256(body).hexdigest() != capture.body_sha256:
        raise ValueError("Archive body hash/count mismatch")
    for item in inputs.captures:
        if (
            item.fetched_at.utcoffset() is None
            or item.completed_at.utcoffset() is None
            or item.fetched_at > item.completed_at
            or item.completed_at > inputs.captured_before
        ):
            raise ValueError("Capture unavailable at the pinned retrieval cutoff")
    filings = {filing.id: filing for filing in inputs.filings}
    if len(filings) != len(inputs.filings):
        raise ValueError("Filing versions must be unique")
    if any(
        f.issuer_id != inputs.issuer_id or f.metadata_capture_id not in captures
        for f in filings.values()
    ):
        raise ValueError("Filing issuer/metadata capture is outside the pinned manifest")
    if len({request.id for request in inputs.requests}) != len(inputs.requests):
        raise ValueError("Coverage requests must have unique IDs")
    for request in inputs.requests:
        if request.filing_version_id not in filings or request.scope.issuer_id != inputs.issuer_id:
            raise ValueError("Coverage issuer/filing mismatch")
        if not request.concepts or len(set(request.concepts)) != len(request.concepts):
            raise ValueError("Coverage concepts must be explicit and unique")
        if not all(isinstance(concept, Concept) for concept in request.concepts):
            raise ValueError("Only reviewed Concept values are permitted")
        if (
            request.period.start_date is not None
            and request.period.start_date > request.period.end_date
        ):
            raise ValueError("Invalid coverage period")
        if not request.evidence_locator or not request.scope.descriptor_json:
            raise ValueError("Coverage and economic scope require reviewed evidence")
        if (
            hashlib.sha256(request.scope.descriptor_json.encode()).hexdigest()
            != request.scope.content_sha256
        ):
            raise ValueError("Scope descriptor hash mismatch")
    for ids in (inputs.filing_event_ids, inputs.additional_quality_flag_ids, inputs.attempt_ids):
        if len(set(ids)) != len(ids):
            raise ValueError("Pinned event/quality/attempt IDs must be unique")


def _rules(
    inputs: NormalizationInput, request: CoverageRequest, concept: Concept
) -> list[MappingRule]:
    filing = next(f for f in inputs.filings if f.id == request.filing_version_id)
    return [
        rule
        for rule in inputs.rules
        if rule.cik == inputs.cik
        and filing.accession in rule.accessions
        and rule.concept == concept
        and rule.scope_id == request.scope.id
        and rule.scope_content_sha256 == request.scope.content_sha256
        and rule.scope_kind == request.scope.scope_kind
        and rule.instrument_id == request.scope.instrument_id
        and rule.period_start == request.period.start_date
        and rule.period_end == request.period.end_date
        and rule.statement_family == request.statement_family
        and rule.reporting_basis == request.reporting_basis
        and rule.unit_key == concept_unit(concept, request.currency.unit_key)
        and rule.evidence_references
        and rule.reference
    ]


def _flag(
    inputs: NormalizationInput,
    request: CoverageRequest,
    rule: str,
    message: str,
    resolution_id: UUID | None = None,
) -> QualityFlag:
    return QualityFlag(
        evidence_id("flag", [request.id, resolution_id, rule, message]),
        resolution_id,
        inputs.issuer_id,
        request.period.id,
        rule,
        "error",
        message,
        canonical_json([request.evidence_locator, str(inputs.companyfacts_capture_id)]),
    )


def _row_period(row: dict[str, Any]) -> PeriodSpec:
    end = date.fromisoformat(row["end"])
    start = date.fromisoformat(row["start"]) if "start" in row else None
    return period_spec(start, end)


def _numeric(row: dict[str, Any]) -> tuple[Decimal | None, str | None, str | None]:
    if "val" not in row:
        return None, None, "missing_value_field"
    value = row["val"]
    if value is None:
        return None, "null", "json_null_without_reviewed_nil_semantics"
    if isinstance(value, JsonNumber) and value.value.is_finite():
        return value.value, value.text, None
    return None, source_json(value), "unparseable_source_value"


def normalize_verified_bytes(body: bytes, inputs: NormalizationInput) -> NormalizationBundle:
    """Select directly reported rows; return unavailable outcomes for every gap."""
    _validate(inputs, body)
    document = parse_companyfacts_json(body)
    if canonical_cik(document.get("cik")) != inputs.cik:
        raise ValueError("Response CIK does not match requested issuer")
    taxonomies = document.get("facts")
    if not isinstance(taxonomies, dict):
        raise ValueError("Company Facts requires a facts object")
    periods = {request.period.id: request.period for request in inputs.requests}
    units = {request.currency.id: request.currency for request in inputs.requests}
    scopes = {request.scope.id: request.scope for request in inputs.requests}
    observations: dict[UUID, Observation] = {}
    resolutions: list[Resolution] = []
    candidates: list[Candidate] = []
    flags: list[QualityFlag] = []
    coverage: list[Coverage] = []
    files = {filing.id: filing for filing in inputs.filings}
    for request in inputs.requests:
        filing = files[request.filing_version_id]
        coverage.append(
            Coverage(
                request.id,
                filing.id,
                request.period.id,
                request.statement_family,
                request.reporting_basis,
                request.scope.id,
                request.currency.id,
                request.authority_class,
                request.assurance,
                request.coverage_state,
                request.evidence_locator,
                request.period_label,
            )
        )
        for name, completeness in (
            ("inventory", inputs.inventory_completeness),
            ("event", inputs.event_completeness),
        ):
            if completeness.state != "complete" or not (
                completeness.boundary_start <= min(request.period.end_date, filing.filed_date)
                and completeness.boundary_end
                >= max(filing.filed_date, inputs.captured_before.astimezone(UTC).date())
            ):
                flags.append(
                    _flag(
                        inputs,
                        request,
                        f"{name}_history_incomplete",
                        f"{name} review must cover period end through retrieval assessment",
                    )
                )
        if request.coverage_state == "unresolved" or request.authority_class == "unknown":
            flags.append(
                _flag(
                    inputs,
                    request,
                    "unresolved_coverage",
                    "Unresolved coverage blocks usable fallback to an older edition",
                )
            )
        for concept in request.concepts:
            unit = unit_spec(concept_unit(concept, request.currency.unit_key))
            units[unit.id] = unit
            resolution_id = evidence_id("resolution", [request.id, concept.value, unit.id])
            matching_rules = _rules(inputs, request, concept)
            status: ResolutionStatus = "missing"
            reason: str | None = "no_exact_reviewed_observation"
            chosen: Observation | None = None
            considered: list[tuple[Observation, str | None, str]] = []
            if request.coverage_state != "covered":
                reason = (
                    "source_missing"
                    if request.coverage_state == "source_missing"
                    else "unresolved_coverage"
                )
            elif len(matching_rules) != 1 or not matching_rules[0].qualified_tags:
                status = "ambiguous" if len(matching_rules) > 1 else "unsupported_scope"
                reason = (
                    "conflicting_mapping_rules"
                    if len(matching_rules) > 1
                    else "no_reviewed_complete_scope_tag"
                )
            else:
                rule = matching_rules[0]
                for qualified in (*rule.qualified_tags, *rule.rejected_tags):
                    namespace, tag = qualified.split(":", 1)
                    taxonomy = taxonomies.get(namespace, {})
                    definition = taxonomy.get(tag, {}) if isinstance(taxonomy, dict) else {}
                    if not isinstance(definition, dict):
                        continue
                    source_units = definition.get("units", {})
                    if not isinstance(source_units, dict):
                        continue
                    for raw_unit, rows in source_units.items():
                        if not isinstance(rows, list):
                            continue
                        for index, row in enumerate(rows):
                            if not isinstance(row, dict) or row.get("accn") != filing.accession:
                                continue
                            escaped_unit = raw_unit.replace("~", "~0").replace("/", "~1")
                            locator = f"/facts/{namespace}/{tag}/units/{escaped_unit}/{index}"
                            try:
                                row_period = _row_period(row)
                                observed_unit = unit_spec(raw_unit)
                            except (ValueError, KeyError, TypeError):
                                flags.append(
                                    _flag(
                                        inputs,
                                        request,
                                        "unsupported_row_identity",
                                        f"Unparseable period/unit at {locator}",
                                        resolution_id,
                                    )
                                )
                                continue
                            periods[row_period.id] = row_period
                            units[observed_unit.id] = observed_unit
                            value, lexical, value_error = _numeric(row)
                            rejection: str | None = None
                            if qualified in rule.rejected_tags:
                                rejection = "excluded_economic_scope: " + rule.rationale
                            elif row_period.id != request.period.id or observed_unit.id != unit.id:
                                rejection = "different_period_or_unit"
                            elif (
                                row.get("filed") != str(filing.filed_date)
                                or row.get("form") != filing.form
                            ):
                                rejection = "filing_metadata_conflict"
                            elif value_error:
                                rejection = value_error
                            observation = Observation(
                                evidence_id(
                                    "observation", [inputs.companyfacts_capture_id, locator]
                                ),
                                inputs.companyfacts_capture_id,
                                filing.id,
                                locator,
                                namespace,
                                tag,
                                row_period.id,
                                observed_unit.id,
                                None if qualified in rule.rejected_tags else request.scope.id,
                                value,
                                "numeric" if value_error is None else "unparseable",
                                lexical,
                                inputs.parser_revision,
                                canonical_json(
                                    {"operation": "identity_decimal", "scale_applied": False}
                                ),
                                canonical_json(
                                    {
                                        "source_row_json": source_json(row),
                                        "source_label": definition.get("label"),
                                        "source_description": definition.get("description"),
                                        "source_cik_json": source_json(document["cik"]),
                                        "source_cik_type": "string"
                                        if isinstance(document["cik"], str)
                                        else "integer",
                                        "api_unit": raw_unit,
                                    }
                                ),
                            )
                            previous = observations.get(observation.id)
                            if previous is not None and previous != observation:
                                raise ValueError(
                                    "One raw observation received incompatible "
                                    "scope/filing interpretations"
                                )
                            observations[observation.id] = observation
                            considered.append((observation, rejection, source_json(row)))
                eligible = [
                    (observation, raw)
                    for observation, rejected, raw in considered
                    if rejected is None
                ]
                identity_conflicts = [
                    why for _, why, _ in considered if why == "filing_metadata_conflict"
                ]
                invalid_values = [
                    why
                    for observation, why, _ in considered
                    if observation.period_id == request.period.id
                    and observation.unit_id == unit.id
                    and why
                    in {
                        "missing_value_field",
                        "json_null_without_reviewed_nil_semantics",
                        "unparseable_source_value",
                    }
                ]
                if identity_conflicts:
                    status, reason = "ambiguous", "filing_metadata_conflict"
                elif invalid_values:
                    reason = sorted(invalid_values)[0]
                elif eligible:
                    if len({observation.numeric_value for observation, _ in eligible}) != 1:
                        status, reason = "ambiguous", "conflicting_reviewed_observations"
                    else:
                        tags = {
                            f"{observation.namespace}:{observation.tag}"
                            for observation, _ in eligible
                        }
                        preferred = (
                            [
                                (observation, raw)
                                for observation, raw in eligible
                                if f"{observation.namespace}:{observation.tag}"
                                == rule.preferred_tag
                            ]
                            if rule.preferred_tag
                            else eligible
                        )
                        if len(tags) > 1 and (rule.preferred_tag is None or not preferred):
                            status, reason = (
                                "ambiguous",
                                "equivalent_tags_without_reviewed_preference",
                            )
                        elif len({raw for _, raw in preferred}) > 1:
                            status, reason = "ambiguous", "same_value_different_source_metadata"
                        else:
                            chosen = min(
                                (observation for observation, _ in preferred),
                                key=lambda item: int(item.source_locator.rsplit("/", 1)[1]),
                            )
                            status, reason = "observed", None
                for observation, rejected, _ in considered:
                    selected = chosen is not None and observation.id == chosen.id
                    disposition = (
                        "selected"
                        if selected
                        else "conflicting"
                        if rejected is None and status == "ambiguous"
                        else "rejected"
                    )
                    explanation = (
                        "Selected directly reported observation"
                        if selected
                        else rejected
                        or (
                            "Equivalent duplicate retained; one reviewed representative selected"
                            if chosen
                            else reason or "Unresolved candidate"
                        )
                    )
                    candidates.append(
                        Candidate(
                            resolution_id, observation.id, rule.reference, disposition, explanation
                        )
                    )
            resolutions.append(
                Resolution(
                    resolution_id,
                    request.id,
                    concept,
                    request.scope.id,
                    request.scope.instrument_id,
                    unit.id,
                    status,
                    chosen.id if chosen else None,
                    reason,
                )
            )
            if status != "observed":
                flags.append(
                    _flag(
                        inputs,
                        request,
                        reason or status,
                        f"{concept.value}: {reason}",
                        resolution_id,
                    )
                )
    # Stable content: output-generated UUIDs are deterministic semantic keys. Input
    # capture IDs/times remain included so equal bodies at new vintages never collapse.

    complete = (
        inputs.inventory_completeness.state == inputs.event_completeness.state == "complete"
        and not any(flag.rule_key.endswith("history_incomplete") for flag in flags)
    )
    bundle = NormalizationBundle(
        inputs=inputs,
        periods=tuple(sorted(periods.values(), key=lambda row: str(row.id))),
        units=tuple(sorted(units.values(), key=lambda row: str(row.id))),
        scopes=tuple(sorted(scopes.values(), key=lambda row: str(row.id))),
        filings=inputs.filings,
        coverage=tuple(coverage),
        observations=tuple(sorted(observations.values(), key=lambda row: str(row.id))),
        resolutions=tuple(resolutions),
        candidates=tuple(candidates),
        quality_flags=tuple({flag.id: flag for flag in flags}.values()),
        input_manifest_hash=normalization_input_hash(inputs),
        output_manifest_hash="",
        original_history_complete=complete,
    )
    return replace(bundle, output_manifest_hash=bundle_output_hash(bundle))


# These are reviewed exact accession/period profiles, not a generalized industry
# map. Unsupported issuers and later filing eras deliberately receive no rules.
_REVIEWED_ANCHORS: dict[str, tuple[str, str, str]] = {
    "0000320193": ("0000320193-25-000079", "2024-09-29", "2025-09-27"),
    "0000789019": ("0000950170-25-100235", "2024-07-01", "2025-06-30"),
    "0000019617": ("0001628280-26-008131", "2025-01-01", "2025-12-31"),
    "0001876042": ("0001876042-26-000062", "2025-01-01", "2025-12-31"),
    "0001315098": ("0001315098-26-000024", "2025-01-01", "2025-12-31"),
    "0001046179": ("0001628280-26-025362", "2025-01-01", "2025-12-31"),
    "0001637459": ("0001637459-19-000049", "2017-12-31", "2018-12-29"),
    "0000909832": ("0000909832-25-000101", "2024-09-02", "2025-08-31"),
}

_US_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "CostOfGoodsAndServicesSold",
    "GrossProfit",
    "ResearchAndDevelopmentExpense",
    "SellingGeneralAndAdministrativeExpense",
    "OperatingExpenses",
    "OperatingIncomeLoss",
    "InterestExpenseNonoperating",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeTaxExpenseBenefit",
    "NetIncomeLoss",
    "ProfitLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "CommonStockSharesOutstanding",
    "CashAndCashEquivalentsAtCarryingValue",
    "ShortTermInvestments",
    "AccountsReceivableNetCurrent",
    "InventoryNet",
    "AssetsCurrent",
    "PropertyPlantAndEquipmentNet",
    "Goodwill",
    "IntangibleAssetsNetExcludingGoodwill",
    "Assets",
    "AccountsPayableCurrent",
    "",
    "LongTermDebtNoncurrent",
    "LiabilitiesCurrent",
    "Liabilities",
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "MinorityInterest",
    "NetCashProvidedByUsedInOperatingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "DepreciationDepletionAndAmortization",
    "ShareBasedCompensation",
    "PaymentsOfDividendsCommonStock",
    "PaymentsForRepurchaseOfCommonStock",
)

_REVIEWED_OVERRIDES: dict[str, dict[Concept, tuple[str, ...]]] = {
    "0000320193": {
        Concept.SHORT_TERM_INVESTMENTS: ("MarketableSecuritiesCurrent",),
        Concept.DIVIDENDS_PAID: ("PaymentsOfDividends",),
    },
    "0000019617": {
        Concept.REVENUE: ("RevenuesNetOfInterestExpense", "Revenues"),
        Concept.INTEREST_EXPENSE: ("InterestExpenseOperating",),
        Concept.DIVIDENDS_PAID: ("PaymentsOfDividends",),
    },
    "0001876042": {
        Concept.REVENUE: ("Revenues",),
        Concept.DEPRECIATION_AND_AMORTIZATION: (
            "DepreciationAndAmortization",
            "DepreciationDepletionAndAmortization",
        ),
    },
    "0001315098": {
        Concept.SHORT_TERM_INVESTMENTS: ("ShortTermInvestments", "MarketableSecuritiesCurrent"),
        Concept.DEPRECIATION_AND_AMORTIZATION: ("DepreciationAndAmortization",),
    },
    "0001637459": {
        Concept.REVENUE: ("RevenueFromContractWithCustomerIncludingAssessedTax",),
        Concept.INTEREST_EXPENSE: ("InterestExpense",),
    },
    "0000909832": {
        Concept.REVENUE: ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"),
        Concept.INTEREST_EXPENSE: ("InterestExpense",),
    },
}


def _reviewed_scope_matches(cik: str, concept: Concept, request: CoverageRequest) -> bool:
    """Require the reviewed v1 scope meaning; an arbitrary ID is not approval.

    Source-row context remains unknown. The descriptor below is the separate S1
    economic interpretation, with explicit ownership, instrument and payment basis.
    """
    number = tuple(Concept).index(concept) + 1
    if concept in {Concept.NET_INCOME_PARENT, Concept.EQUITY_PARENT}:
        kind = "parent"
    elif 13 <= number <= 17:
        kind = "ordinary_common_shares" if cik == "0001046179" else "all_reported_common_classes"
    else:
        kind = "consolidated"
    instrument = request.scope.instrument_id
    if (13 <= number <= 17) != (instrument is not None):
        return False
    expected = {
        "consolidation": kind,
        "instrument": str(instrument) if instrument else None,
        "context_knowledge": "unknown",
        "scope_evidence": "docs/research/s1/concept-map.md",
        "cash_scope": "corporate_cash_excluding_holder_reserves"
        if cik == "0001876042" and concept == Concept.CASH_AND_CASH_EQUIVALENTS
        else "not_applicable",
        "payment_basis": "cash_flow_addback"
        if concept == Concept.SHARE_BASED_COMPENSATION
        else "actual_cash_payment"
        if concept
        in {Concept.DIVIDENDS_PAID, Concept.SHARE_REPURCHASES, Concept.CAPITAL_EXPENDITURES_PPE}
        else "as_reported",
        "revenue_basis": "net_of_operating_interest"
        if cik == "0000019617" and concept == Concept.REVENUE
        else "reported_complete_scope",
    }
    family = "income" if number <= 16 else "balance_sheet" if number <= 34 else "cash_flow"
    if number == 17:
        family = "other"
    currency = "TWD" if cik == "0001046179" else "USD"
    expected_unit = unit_spec(currency)
    try:
        descriptor = json.loads(request.scope.descriptor_json)
    except (ValueError, TypeError):
        return False
    return (
        request.scope.descriptor_schema_version == 1
        and request.scope.scope_kind == kind
        and descriptor == expected
        and request.statement_family == family
        and request.reporting_basis == ("ifrs" if cik == "0001046179" else "us_gaap")
        and request.currency.unit_key == currency
        and request.currency.numerator_measures == expected_unit.numerator_measures
        and request.currency.denominator_measures == expected_unit.denominator_measures
    )


def reviewed_cohort_rules(
    cik: str, filings: tuple[Any, ...], requests: tuple[CoverageRequest, ...]
) -> tuple[MappingRule, ...]:
    """Return exact S1 reviewed issuer/filing/period rules, never future-era guesses.

    Coverage/instrument/assurance declarations remain independently reviewed input.
    Their existence cannot be inferred from this candidate map.
    """
    cik = canonical_cik(cik)
    anchor = _REVIEWED_ANCHORS.get(cik)
    if anchor is None:
        return ()
    file_by_id = {filing.id: filing for filing in filings}
    rules: list[MappingRule] = []
    concepts = tuple(Concept)
    for request in requests:
        filing = file_by_id[request.filing_version_id]
        for concept in request.concepts:
            if not _reviewed_scope_matches(cik, concept, request):
                continue
            number = concepts.index(concept)
            duration = number < 16 or number >= 34
            expected_start = date.fromisoformat(anchor[1]) if duration else None
            valid = (
                filing.accession == anchor[0]
                and request.period.start_date == expected_start
                and request.period.end_date == date.fromisoformat(anchor[2])
            )
            tags: tuple[str, ...] = ()
            if valid and cik != "0001046179":
                default = _US_TAGS[number]
                names = _REVIEWED_OVERRIDES.get(cik, {}).get(concept, (default,) if default else ())
                tags = tuple(f"us-gaap:{tag}" for tag in names)
            elif valid and concept == Concept.COMMON_SHARES_OUTSTANDING:
                tags = ("dei:EntityCommonStockSharesOutstanding",)
            elif (
                cik == "0001637459"
                and filing.accession in {"0001637459-18-000015", "0001637459-19-000049"}
                and request.period.start_date == date(2017, 1, 1)
                and request.period.end_date == date(2017, 12, 30)
                and concept in {Concept.NET_INCOME_PARENT, Concept.NET_INCOME_CONSOLIDATED}
            ):
                valid = True
                tags = (
                    "us-gaap:NetIncomeLoss"
                    if concept == Concept.NET_INCOME_PARENT
                    else "us-gaap:ProfitLoss",
                )
            elif (
                cik == "0001046179"
                and filing.accession == "0001193125-25-083423"
                and request.period.start_date == date(2024, 1, 1)
                and request.period.end_date == date(2024, 12, 31)
            ):
                historical = {
                    Concept.INTEREST_EXPENSE: "FinanceCosts",
                    Concept.SHARE_BASED_COMPENSATION: "AdjustmentsForSharebasedPayments",
                    Concept.DIVIDENDS_PAID: "DividendsPaidClassifiedAsFinancingActivities",
                    Concept.EPS_BASIC: "BasicEarningsLossPerShare",
                    Concept.EPS_DILUTED: "DilutedEarningsLossPerShare",
                }
                if concept in historical and request.currency.unit_key == "TWD":
                    valid, tags = True, ("ifrs-full:" + historical[concept],)
            if not valid:
                continue
            rejected: tuple[str, ...] = ()
            rationale = (
                "S1 reviewed directly reported concept scope; preference applies only "
                "to this accession and actual period"
            )
            if cik == "0001876042" and concept == Concept.REVENUE:
                rejected = ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",)
                rationale = (
                    "Customer-contract revenue is a component; total includes reserve income"
                )
            elif concept == Concept.OPERATING_EXPENSES:
                rejected = ("us-gaap:CostsAndExpenses", "us-gaap:NoninterestExpense")
                rationale = (
                    "Broader costs and bank noninterest expenses are not the reviewed "
                    "industrial operating-expense subtotal"
                )
            elif concept == Concept.SHARE_BASED_COMPENSATION:
                rejected = (
                    (
                        "us-gaap:AllocatedShareBasedCompensationExpense",
                        "us-gaap:AllocatedShareBasedCompensationExpenseNetOfTax",
                    )
                    if cik != "0001046179"
                    else (
                        "ifrs-full:ExpenseFromSharebasedPaymentTransactionsInWhichGoodsOrServicesReceivedDidNotQualifyForRecognitionAsAssets",
                    )
                )
                rationale = (
                    "P0 uses the cash-flow addback, not a separate expense or net-of-tax measure"
                )
            elif cik == "0001046179" and concept == Concept.DIVIDENDS_PAID:
                rejected = ("ifrs-full:DividendsPaid",)
                rationale = "The inspected TSM equity appropriation is not a cash-flow payment"
            rules.append(
                MappingRule(
                    reference=f"s3-reviewed-s1:{cik}:{filing.accession}:{concept.value}",
                    cik=cik,
                    accessions=(filing.accession,),
                    concept=concept,
                    qualified_tags=tags,
                    unit_key=concept_unit(concept, request.currency.unit_key),
                    scope_id=request.scope.id,
                    evidence_references=(
                        "docs/research/s1/concept-map.md",
                        "docs/research/s1/review-brief.md",
                        "docs/research/s1/ifrs-and-restatement-observations.md"
                        if cik == "0001046179"
                        else "docs/research/s1/special-sector-observations.md"
                        if cik in {"0000019617", "0001876042"}
                        else "docs/research/s1/restatement-khc.md"
                        if cik == "0001637459"
                        else "docs/research/s1/baseline-observations.md",
                    ),
                    period_start=request.period.start_date,
                    period_end=request.period.end_date,
                    scope_content_sha256=request.scope.content_sha256,
                    scope_kind=request.scope.scope_kind,
                    instrument_id=request.scope.instrument_id,
                    statement_family=request.statement_family,
                    reporting_basis=request.reporting_basis,
                    preferred_tag=tags[0] if tags else None,
                    rejected_tags=rejected,
                    rationale=rationale,
                )
            )
    return tuple(rules)


def _without_ids(row: Any, *excluded: str) -> dict[str, Any]:
    return {key: value for key, value in asdict(row).items() if key not in {"id", *excluded}}


def normalization_input_hash(inputs: NormalizationInput) -> str:
    """Hash pinned evidence and logical requests, excluding newly allocated row IDs."""
    periods = {request.period.id: _without_ids(request.period) for request in inputs.requests}
    units = {request.currency.id: _without_ids(request.currency) for request in inputs.requests}
    scopes = {request.scope.id: _without_ids(request.scope) for request in inputs.requests}
    files = {filing.id: _without_ids(filing, "filing_id") for filing in inputs.filings}
    requests = []
    for request in inputs.requests:
        row = _without_ids(request)
        row.update(
            filing_version_id=files[request.filing_version_id],
            period=periods[request.period.id],
            currency=units[request.currency.id],
            scope=scopes[request.scope.id],
        )
        requests.append(row)
    rules = []
    for rule in inputs.rules:
        row = asdict(rule)
        row["scope_id"] = scopes.get(
            rule.scope_id, {"pinned_external_scope_id": str(rule.scope_id)}
        )
        rules.append(row)
    manifest = asdict(inputs)
    manifest.update(filings=list(files.values()), requests=requests, rules=rules)
    return content_hash(manifest)


def bundle_output_hash(bundle: NormalizationBundle) -> str:
    """Logical output digest, independent of database-assigned row identities.

    Generated-row references become hashes of their full semantic content. Captures,
    issuer/security IDs, retrieval times and approved revision IDs stay pinned in
    the input digest. A DB writer may remap row UUIDs without changing this digest.
    """
    periods = {row.id: _without_ids(row) for row in bundle.periods}
    units = {row.id: _without_ids(row) for row in bundle.units}
    scopes = {row.id: _without_ids(row) for row in bundle.scopes}
    files = {row.id: _without_ids(row, "filing_id") for row in bundle.filings}
    coverages: dict[UUID, dict[str, Any]] = {}
    for coverage_item in bundle.coverage:
        row = _without_ids(coverage_item)
        row.update(
            filing_version_id=content_hash(files[coverage_item.filing_version_id]),
            period_id=content_hash(periods[coverage_item.period_id]),
            scope_id=content_hash(scopes[coverage_item.scope_id]),
            currency_unit_id=content_hash(units[coverage_item.currency_unit_id])
            if coverage_item.currency_unit_id
            else None,
        )
        coverages[coverage_item.id] = row
    observations: dict[UUID, dict[str, Any]] = {}
    for observation_item in bundle.observations:
        row = _without_ids(observation_item)
        row.update(
            filing_version_id=content_hash(files[observation_item.filing_version_id]),
            period_id=content_hash(periods[observation_item.period_id]),
            unit_id=content_hash(units[observation_item.unit_id]),
            semantic_scope_id=content_hash(scopes[observation_item.semantic_scope_id])
            if observation_item.semantic_scope_id
            else None,
        )
        observations[observation_item.id] = row
    resolutions: dict[UUID, dict[str, Any]] = {}
    for resolution_item in bundle.resolutions:
        row = _without_ids(resolution_item)
        row.update(
            coverage_id=content_hash(coverages[resolution_item.coverage_id]),
            semantic_scope_id=content_hash(scopes[resolution_item.semantic_scope_id]),
            unit_id=content_hash(units[resolution_item.unit_id]),
            selected_observation_id=content_hash(
                observations[resolution_item.selected_observation_id]
            )
            if resolution_item.selected_observation_id
            else None,
        )
        resolutions[resolution_item.id] = row
    candidates = []
    for candidate_item in bundle.candidates:
        row = asdict(candidate_item)
        row.update(
            resolution_id=content_hash(resolutions[candidate_item.resolution_id]),
            observation_id=content_hash(observations[candidate_item.observation_id]),
        )
        candidates.append(row)
    flags = []
    for flag_item in bundle.quality_flags:
        row = _without_ids(flag_item)
        row.update(
            resolution_id=content_hash(resolutions[flag_item.resolution_id])
            if flag_item.resolution_id
            else None,
            period_id=content_hash(periods[flag_item.period_id]) if flag_item.period_id else None,
        )
        flags.append(row)
    collections = dict(
        periods=list(periods.values()),
        units=list(units.values()),
        scopes=list(scopes.values()),
        filings=list(files.values()),
        coverage=list(coverages.values()),
        observations=list(observations.values()),
        resolutions=list(resolutions.values()),
        candidates=candidates,
        quality_flags=flags,
    )
    payload = {key: sorted(rows, key=canonical_json) for key, rows in collections.items()}
    return content_hash(
        {
            "input_manifest_hash": normalization_input_hash(bundle.inputs),
            "original_history_complete": bundle.original_history_complete,
            "output": payload,
        }
    )
