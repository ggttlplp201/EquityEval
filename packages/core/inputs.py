"""Pure projections of previously selected financial evidence.

Callers perform storage selection before constructing these inputs. The original
records stay attached; validation never rewrites a reported value or source flag.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date
from decimal import Decimal
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import UUID

from equity_schema.concepts import Concept

if TYPE_CHECKING:
    from equity_ingest.financial_types import PeriodSpec, ScopeSpec, UnitSpec
    from equity_schema.pit import SelectedFact, StatementSelection


@dataclass(frozen=True)
class PrecisionEvidence:
    """An explicit source-evidenced absolute uncertainty, never inferred digits."""

    absolute_error: Decimal
    observation_ids: tuple[UUID, ...]
    evidence_refs: tuple[str, ...]
    method: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.absolute_error, Decimal)
            or not self.absolute_error.is_finite()
            or self.absolute_error < 0
        ):
            raise ValueError("Source precision requires a finite nonnegative Decimal uncertainty")
        if not _valid_ids(self.observation_ids):
            raise ValueError("Source precision requires unique selected observation UUIDs")
        if (
            not isinstance(self.evidence_refs, tuple)
            or not self.evidence_refs
            or not all(isinstance(ref, str) and ref.strip() for ref in self.evidence_refs)
            or not isinstance(self.method, str)
            or not self.method.strip()
        ):
            raise ValueError("Source precision requires nonempty evidence references and method")


@dataclass(frozen=True)
class FinancialInput:
    """One concept and its exact source-selection context, without I/O."""

    selection: StatementSelection
    concept: Concept
    period: PeriodSpec
    unit: UnitSpec
    scope: ScopeSpec
    precision: PrecisionEvidence | None = None

    @property
    def fact(self) -> SelectedFact | None:
        matches = tuple(fact for fact in self.selection.facts if fact.concept == self.concept)
        return matches[0] if len(matches) == 1 else None

    @property
    def flags(self) -> tuple[str, ...]:
        flags = set(self.selection.flags) | self._context_flags()
        if not self.selection.usable_for_valuation:
            flags.add("input_selection_unusable")
        if not self._selection_evidence_valid():
            flags.add("input_selection_evidence_invalid")
        fact = self.fact
        if fact is None:
            flags.add("input_fact_not_unique")
        else:
            flags.update(fact.flags)
            if self.precision is not None and (
                set(self.precision.observation_ids) != set(fact.observation_ids)
            ):
                flags.add("input_precision_mismatch")
            if not self._provenance_valid(fact):
                flags.add("input_provenance_invalid")
            if not isinstance(fact.value, Decimal) or not fact.value.is_finite():
                flags.add("input_value_invalid")
            if fact.status != "observed":
                flags.add("input_fact_not_observed")
        return tuple(sorted(flags))

    @property
    def blocking_flags(self) -> tuple[str, ...]:
        return tuple(
            flag for flag in self.flags if flag not in {"revised_view", "earliest_available"}
        )

    @property
    def value(self) -> Decimal | None:
        fact = self.fact
        return fact.value if fact is not None and not self.blocking_flags else None

    @property
    def history_key(self) -> tuple[object, ...]:
        query = self.selection.query
        return (
            query.issuer_id,
            query.security_id,
            query.reporting_currency_unit_id or query.unit_id,
            query.mode,
            query.filed_cutoff,
            query.captured_before,
            tuple(sorted(query.batch_ids, key=str)),
            tuple(sorted(query.capture_ids, key=str)),
            tuple(sorted(query.filing_event_ids, key=str)),
            query.mapping_revision_id,
            query.normalizer_revision,
            query.authority_policy_revision,
            tuple(sorted(query.additional_quality_flag_ids, key=str)),
            query.audited_required,
            query.allow_reviewed_equivalent,
            query.original_history_complete,
        )

    def _context_flags(self) -> set[str]:
        query = self.selection.query
        flags: set[str] = set()
        required_ids = (
            query.issuer_id,
            query.period_id,
            query.unit_id,
            query.scope_id,
            query.mapping_revision_id,
            self.period.id,
            self.unit.id,
            self.scope.id,
            self.scope.issuer_id,
        )
        optional_ids = (
            query.instrument_id,
            query.security_id,
            query.reporting_currency_unit_id,
            self.scope.instrument_id,
        )
        if (
            not all(isinstance(value, UUID) for value in required_ids)
            or not all(value is None or isinstance(value, UUID) for value in optional_ids)
            or not _valid_ids(query.batch_ids)
            or not _valid_ids(query.capture_ids)
            or not _valid_ids(query.filing_event_ids, allow_empty=True)
            or not _valid_ids(query.additional_quality_flag_ids, allow_empty=True)
        ):
            flags.add("input_identity_invalid")
        if not isinstance(self.concept, Concept) or self.concept not in query.concepts:
            flags.add("input_concept_mismatch")
        if self.period.id != query.period_id:
            flags.add("input_period_mismatch")
        if self.unit.id != query.unit_id:
            flags.add("input_unit_mismatch")
        # PIT coverage uses an explicit statement currency, or the monetary
        # query unit when omitted. A whole-currency fact must use that exact unit.
        reporting_currency = query.reporting_currency_unit_id or query.unit_id
        if re.fullmatch(r"[A-Z]{3}", self.unit.unit_key) and reporting_currency != self.unit.id:
            flags.add("input_reporting_currency_mismatch")
        if (
            self.scope.id != query.scope_id
            or self.scope.issuer_id != query.issuer_id
            or self.scope.instrument_id != query.instrument_id
        ):
            flags.add("input_scope_mismatch")
        period = self.period
        if not (
            type(period.end_date) is date
            and (
                (period.period_kind == "instant" and period.start_date is None)
                or (
                    period.period_kind == "duration"
                    and type(period.start_date) is date
                    and period.start_date <= period.end_date
                )
            )
        ):
            flags.add("input_period_invalid")
        if not self._scope_valid():
            flags.add("input_scope_invalid")
        if not self._unit_valid():
            flags.add("input_unit_invalid")
        return flags

    def _scope_valid(self) -> bool:
        scope = self.scope
        try:
            descriptor = json.loads(scope.descriptor_json)
        except (ValueError, TypeError):
            return False
        return (
            scope.descriptor_schema_version == 1
            and isinstance(descriptor, dict)
            and hashlib.sha256(scope.descriptor_json.encode()).hexdigest() == scope.content_sha256
            and descriptor.get("consolidation") == scope.scope_kind
            and bool(scope.scope_kind)
            and "instrument" in descriptor
            and descriptor["instrument"]
            == (str(scope.instrument_id) if scope.instrument_id is not None else None)
            and isinstance(descriptor.get("scope_evidence"), str)
            and bool(descriptor["scope_evidence"].strip())
        )

    def _unit_valid(self) -> bool:
        unit = self.unit
        expected: tuple[tuple[str, ...], tuple[str, ...]]
        if unit.unit_key == "shares":
            expected = (("xbrli:shares",), ())
        elif re.fullmatch(r"[A-Z]{3}", unit.unit_key):
            expected = ((f"iso4217:{unit.unit_key}",), ())
        elif re.fullmatch(r"[A-Z]{3}/shares", unit.unit_key):
            expected = ((f"iso4217:{unit.unit_key[:3]}",), ("xbrli:shares",))
        else:
            return False
        return (unit.numerator_measures, unit.denominator_measures) == expected

    def _selection_evidence_valid(self) -> bool:
        selection = self.selection
        query = selection.query
        return (
            _valid_ids(selection.coverage_ids)
            and _valid_ids(selection.filing_version_ids)
            and len(selection.filing_version_ids) == 1
            and _valid_ids(selection.quality_flag_ids, allow_empty=True)
            and _valid_ids(selection.event_ids, allow_empty=True)
            and set(selection.event_ids).issubset(query.filing_event_ids)
            and _sha256(selection.input_hash)
            and selection.reporting_basis in {"us_gaap", "ifrs"}
        )

    def _provenance_valid(self, fact: SelectedFact) -> bool:
        query = self.selection.query
        try:
            url = urlsplit(fact.source_url or "")
            valid_url = (
                url.scheme in {"http", "https"}
                and bool(url.hostname)
                and url.username is None
                and url.password is None
            )
            transform = json.loads(fact.transform_json or "")
        except (ValueError, TypeError):
            return False
        return (
            _valid_ids(fact.resolution_ids)
            and _valid_ids(fact.observation_ids)
            and len(fact.observation_ids) == 1
            and _valid_ids(fact.capture_ids)
            and len(fact.capture_ids) == 1
            and set(fact.capture_ids).issubset(query.capture_ids)
            and bool(fact.accession and re.fullmatch(r"\d{10}-\d{2}-\d{6}", fact.accession))
            and type(fact.filed_date) is date
            and fact.filed_date <= query.captured_before.astimezone(UTC).date()
            and (query.filed_cutoff is None or fact.filed_date <= query.filed_cutoff)
            and valid_url
            and bool(fact.source_locator and fact.source_locator.strip())
            and isinstance(fact.source_hashes, tuple)
            and len(fact.source_hashes) == 1
            and all(_sha256(value) for value in fact.source_hashes)
            and bool(fact.source_tag and fact.source_tag.strip())
            and bool(fact.original_numeric_text and fact.original_numeric_text.strip())
            and isinstance(transform, dict)
        )


def _valid_ids(values: object, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(values, tuple)
        and (allow_empty or bool(values))
        and all(isinstance(value, UUID) for value in values)
        and len(set(values)) == len(values)
    )


def _sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
