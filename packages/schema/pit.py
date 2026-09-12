"""Read frozen financial evidence without mixing editions or inventing missing values.

This module performs storage selection, not financial arithmetic. Each read owns a
short repeatable-read transaction and returns immutable evidence-bearing objects.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from equity_schema.concepts import Concept
from psycopg import Connection
from psycopg.pq import TransactionStatus

Row = dict[str, Any]


class HistoryMode(StrEnum):
    AS_FILED_BY_DATE = "as_filed_by_date"
    ORIGINAL_AS_FILED = "original_as_filed"
    LATEST_REPORTED = "latest_reported"


@dataclass(frozen=True)
class PitQuery:
    issuer_id: UUID
    period_id: UUID
    scope_id: UUID
    unit_id: UUID
    statement_family: str
    concepts: tuple[Concept, ...]
    batch_ids: tuple[UUID, ...]
    capture_ids: tuple[UUID, ...]
    filing_event_ids: tuple[UUID, ...]
    mapping_revision_id: UUID
    normalizer_revision: str
    authority_policy_revision: str
    captured_before: datetime
    mode: HistoryMode
    filed_cutoff: date | None = None
    instrument_id: UUID | None = None
    security_id: UUID | None = None
    reporting_currency_unit_id: UUID | None = None
    additional_quality_flag_ids: tuple[UUID, ...] = ()
    audited_required: bool = False
    allow_reviewed_equivalent: bool = False
    original_history_complete: bool = False

    def __post_init__(self) -> None:
        if self.captured_before.utcoffset() is None:
            raise ValueError("Retrieval vintage requires a timezone-aware timestamp")
        if self.mode == HistoryMode.AS_FILED_BY_DATE and self.filed_cutoff is None:
            raise ValueError("as_filed_by_date requires an inclusive filed cutoff")
        if not isinstance(self.mode, HistoryMode):
            raise ValueError("A reviewed history mode is required")
        for name in ("concepts", "batch_ids", "capture_ids"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or not values or len(set(values)) != len(values):
                raise ValueError(f"{name} must be a nonempty tuple without duplicates")
        for name in ("filing_event_ids", "additional_quality_flag_ids"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(set(values)) != len(values):
                raise ValueError(f"{name} must be an explicit tuple without duplicates")
        if not all(isinstance(concept, Concept) for concept in self.concepts):
            raise ValueError("concepts must use the reviewed Concept enum")
        if not self.normalizer_revision or not self.authority_policy_revision:
            raise ValueError("Normalizer and authority policy revisions must be explicit")


@dataclass(frozen=True)
class SelectedFact:
    concept: Concept
    value: Decimal | None
    status: str
    resolution_ids: tuple[UUID, ...] = ()
    observation_ids: tuple[UUID, ...] = ()
    accession: str | None = None
    filed_date: date | None = None
    source_url: str | None = None
    source_locator: str | None = None
    capture_ids: tuple[UUID, ...] = ()
    source_hashes: tuple[str, ...] = ()
    source_tag: str | None = None
    original_numeric_text: str | None = None
    transform_json: str | None = None
    reason: str | None = None
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class StatementSelection:
    query: PitQuery
    coverage_ids: tuple[UUID, ...]
    filing_version_ids: tuple[UUID, ...]
    facts: tuple[SelectedFact, ...]
    flags: tuple[str, ...]
    quality_flag_ids: tuple[UUID, ...]
    event_ids: tuple[UUID, ...]
    usable_for_valuation: bool
    reporting_basis: str | None
    input_hash: str


def _ids(values: Any) -> tuple[UUID, ...]:
    return tuple(sorted(set(values), key=str))


def _result(
    query: PitQuery,
    *,
    flags: set[str],
    rows: list[Row] | None = None,
    facts: list[SelectedFact] | None = None,
    quality_ids: tuple[UUID, ...] = (),
    event_ids: tuple[UUID, ...] = (),
) -> StatementSelection:
    selected = rows or []
    values = (
        tuple(facts)
        if facts is not None
        else tuple(
            SelectedFact(
                concept=concept, value=None, status="unavailable", flags=tuple(sorted(flags))
            )
            for concept in query.concepts
        )
    )
    nonblocking = {"earliest_available", "revised_view"}
    usable = not (flags - nonblocking) and all(fact.status == "observed" for fact in values)
    coverage_ids = _ids(row["id"] for row in selected)
    filing_ids = _ids(row["filing_version_id"] for row in selected)
    content = dict(
        query=asdict(query),
        coverage_ids=_ids(row["id"] for row in selected),
        filing_version_ids=_ids(row["filing_version_id"] for row in selected),
        facts=[asdict(fact) for fact in values],
        flags=tuple(sorted(flags)),
        quality_flag_ids=quality_ids,
        event_ids=event_ids,
        usable_for_valuation=usable,
        reporting_basis=selected[0]["reporting_basis"] if selected else None,
    )
    input_hash = hashlib.sha256(
        json.dumps(content, sort_keys=True, default=str).encode()
    ).hexdigest()
    return StatementSelection(
        query=query,
        coverage_ids=coverage_ids,
        filing_version_ids=filing_ids,
        facts=values,
        flags=tuple(sorted(flags)),
        quality_flag_ids=quality_ids,
        event_ids=event_ids,
        usable_for_valuation=usable,
        reporting_basis=selected[0]["reporting_basis"] if selected else None,
        input_hash=input_hash,
    )


def _select_source_captures(inputs: list[Row]) -> tuple[set[UUID], set[str]]:
    """Select source-object/role vintages inside an explicitly pinned evidence bundle."""
    groups: dict[tuple[UUID, str, str], list[Row]] = {}
    for row in inputs:
        groups.setdefault((row["source_id"], row["source_object_key"], row["role"]), []).append(row)
    chosen: set[UUID] = set()
    superseded: set[UUID] = set()
    for rows in groups.values():
        newest = max(row["fetched_at"] for row in rows)
        latest = [row for row in rows if row["fetched_at"] == newest]
        if len({row["body_sha256"] for row in latest}) > 1:
            return set(), {"ambiguous_capture_vintage"}
        chosen.update(row["source_capture_id"] for row in latest)
        superseded.update(row["source_capture_id"] for row in rows if row["fetched_at"] < newest)
    if chosen & superseded:
        # The same resource cannot be fresh financial evidence and superseded evidence
        # in another role. Require a coherent manifest instead of reviving stale bytes.
        return set(), {"incompatible_source_roles"}
    return chosen, set()


def _bundle(connection: Connection[Row], query: PitQuery) -> tuple[set[UUID], set[str]]:
    batches = connection.execute(
        "SELECT * FROM normalization_batches WHERE id=ANY(%s)", (list(query.batch_ids),)
    ).fetchall()
    if len(batches) != len(query.batch_ids) or any(row["state"] != "published" for row in batches):
        return set(), {"unpublished_or_missing_batch"}
    for row in batches:
        if (
            row["issuer_id"] != query.issuer_id
            or row["mapping_revision_id"] != query.mapping_revision_id
            or row["normalizer_revision"] != query.normalizer_revision
            or row["source_authority_policy_revision"] != query.authority_policy_revision
        ):
            return set(), {"incompatible_batch_revision"}
    fingerprints: dict[str, set[str]] = {}
    for row in batches:
        fingerprints.setdefault(row["input_manifest_hash"], set()).add(row["output_manifest_hash"])
    if any(len(outputs) > 1 for outputs in fingerprints.values()):
        return set(), {"nondeterministic_normalization"}
    inputs = connection.execute(
        "SELECT n.*, c.* FROM normalization_inputs n JOIN source_captures c "
        "ON c.id=n.source_capture_id WHERE n.batch_id=ANY(%s)",
        (list(query.batch_ids),),
    ).fetchall()
    if {row["source_capture_id"] for row in inputs} != set(query.capture_ids):
        return set(), {"incompatible_capture_manifest"}
    if any(
        row["fetched_at"] is None
        or row["fetched_at"] > query.captured_before
        or row["completed_at"] is None
        or row["completed_at"] > query.captured_before
        for row in inputs
    ):
        return set(), {"capture_unavailable"}
    events = connection.execute(
        "SELECT e.id,e.issuer_id,f.metadata_capture_id FROM filing_events e "
        "JOIN filing_versions f ON f.id=e.source_filing_version_id WHERE e.id=ANY(%s)",
        (list(query.filing_event_ids),),
    ).fetchall()
    if len(events) != len(query.filing_event_ids) or any(
        row["issuer_id"] != query.issuer_id or row["metadata_capture_id"] not in query.capture_ids
        for row in events
    ):
        return set(), {"incompatible_event_manifest"}
    quality = connection.execute(
        "SELECT * FROM data_quality_flags WHERE id=ANY(%s)",
        (list(query.additional_quality_flag_ids),),
    ).fetchall()
    if len(quality) != len(query.additional_quality_flag_ids) or any(
        row["issuer_id"] != query.issuer_id
        or row["period_id"] not in (None, query.period_id)
        or row["security_id"] not in (None, query.security_id)
        or row["batch_id"] not in (None, *query.batch_ids)
        for row in quality
    ):
        return set(), {"incompatible_quality_manifest"}
    selected, flags = _select_source_captures(inputs)
    if not flags and any(row["metadata_capture_id"] not in selected for row in events):
        return set(), {"incompatible_event_vintage"}
    return selected, flags


def _eligible_coverage(
    connection: Connection[Row], query: PitQuery, captures: set[UUID]
) -> list[Row]:
    rows = connection.execute(
        "SELECT c.*, f.filing_id, f.filed_date, f.acceptance_at, f.acceptance_time_basis, "
        "f.metadata_capture_id, x.accession FROM statement_coverage c "
        "JOIN filing_versions f ON f.id=c.filing_version_id JOIN filings x ON x.id=f.filing_id "
        "WHERE c.batch_id=ANY(%s) AND c.period_id=%s AND c.statement_family=%s "
        "AND c.scope_id=%s AND (c.currency_unit_id=%s OR c.currency_unit_id IS NULL)",
        (
            list(query.batch_ids),
            query.period_id,
            query.statement_family,
            query.scope_id,
            query.reporting_currency_unit_id or query.unit_id,
        ),
    ).fetchall()
    allowed = {"periodic_complete"}
    if query.allow_reviewed_equivalent:
        allowed.add("reviewed_equivalent")
    return [
        row
        for row in rows
        if row["metadata_capture_id"] in captures
        and row["authority_class"] in allowed
        and (not query.audited_required or row["assurance"] == "audited")
        and (query.filed_cutoff is None or row["filed_date"] <= query.filed_cutoff)
    ]


def _edition(rows: list[Row], query: PitQuery) -> tuple[list[Row], set[str]]:
    choose = min if query.mode == HistoryMode.ORIGINAL_AS_FILED else max
    selected_date = choose(row["filed_date"] for row in rows)
    finalists = [row for row in rows if row["filed_date"] == selected_date]
    editions = {row["filing_version_id"] for row in finalists}
    if len(editions) > 1:
        if not all(
            row["acceptance_at"] is not None and row["acceptance_time_basis"] == "verified_timezone"
            for row in finalists
        ):
            return finalists, {"ambiguous_filing_order"}
        selected_time = choose(row["acceptance_at"] for row in finalists)
        finalists = [row for row in finalists if row["acceptance_at"] == selected_time]
        if len({row["filing_version_id"] for row in finalists}) > 1:
            return finalists, {"ambiguous_filing_order"}
    if len({row["reporting_basis"] for row in finalists}) > 1:
        return finalists, {"incompatible_reporting_basis"}
    if any(
        row["currency_unit_id"] is None or row["coverage_state"] != "covered" for row in finalists
    ):
        return finalists, {"unresolved_coverage"}
    return finalists, set()


def _facts(
    connection: Connection[Row], query: PitQuery, editions: list[Row], captures: set[UUID]
) -> tuple[list[SelectedFact], set[str], tuple[UUID, ...]]:
    rows = connection.execute(
        "SELECT r.*, o.numeric_value, o.source_capture_id, o.namespace, o.tag, o.source_locator, "
        "o.original_numeric_text, o.transform_metadata, o.value_state, o.raw_metadata, "
        "c.request_url, c.body_sha256 FROM fact_resolutions r "
        "LEFT JOIN source_observations o ON o.id=r.selected_observation_id "
        "LEFT JOIN source_captures c ON c.id=o.source_capture_id "
        "WHERE r.coverage_id=ANY(%s) AND r.semantic_scope_id=%s AND r.unit_id=%s "
        "AND r.instrument_id IS NOT DISTINCT FROM %s",
        ([row["id"] for row in editions], query.scope_id, query.unit_id, query.instrument_id),
    ).fetchall()
    facts: list[SelectedFact] = []
    flags: set[str] = set()
    for concept in query.concepts:
        matches = [row for row in rows if row["concept_std"] == concept.value]
        if not matches:
            flags.add("unresolved_concept")
            facts.append(
                SelectedFact(concept, None, "missing", reason="Selected edition has no resolution")
            )
            continue
        signatures = {
            (row["status"], row["numeric_value"], row["selected_observation_id"]) for row in matches
        }
        if len(signatures) != 1:
            flags.add("ambiguous_resolution")
            facts.append(
                SelectedFact(
                    concept, None, "ambiguous", resolution_ids=_ids(row["id"] for row in matches)
                )
            )
            continue
        row = matches[0]
        status = row["status"]
        value = row["numeric_value"] if status == "observed" else None
        if row["selected_observation_id"] is not None and row["source_capture_id"] not in captures:
            status, value = "stale_source", None
        if status != "observed":
            flags.add("unresolved_concept")
        facts.append(
            SelectedFact(
                concept=concept,
                value=value,
                status=status,
                resolution_ids=_ids(match["id"] for match in matches),
                observation_ids=_ids(
                    match["selected_observation_id"]
                    for match in matches
                    if match["selected_observation_id"]
                ),
                accession=editions[0]["accession"],
                filed_date=editions[0]["filed_date"],
                source_url=row["request_url"],
                source_locator=row["source_locator"],
                capture_ids=_ids(
                    match["source_capture_id"] for match in matches if match["source_capture_id"]
                ),
                source_hashes=tuple(
                    sorted({match["body_sha256"] for match in matches if match["body_sha256"]})
                ),
                source_tag=f"{row['namespace']}:{row['tag']}" if row["tag"] else None,
                original_numeric_text=row["original_numeric_text"],
                transform_json=json.dumps(row["transform_metadata"], sort_keys=True)
                if row["transform_metadata"] is not None
                else None,
                reason=row["reason"],
            )
        )
    quality = connection.execute(
        "SELECT q.* FROM data_quality_flags q LEFT JOIN fact_resolutions r ON r.id=q.resolution_id "
        "WHERE q.id=ANY(%s) OR (q.batch_id=ANY(%s) AND "
        "((q.resolution_id IS NULL AND (q.period_id IS NULL OR q.period_id=%s)) "
        "OR r.id=ANY(%s)))",
        (
            list(query.additional_quality_flag_ids),
            list(query.batch_ids),
            query.period_id,
            [rid for fact in facts for rid in fact.resolution_ids],
        ),
    ).fetchall()
    if any(row["severity"] in {"error", "blocking"} for row in quality):
        flags.add("blocking_quality_flag")
    return facts, flags, _ids(row["id"] for row in quality)


def _events(
    connection: Connection[Row], query: PitQuery, editions: list[Row], captures: set[UUID]
) -> list[Row]:
    # Explicit affected filing IDs prevent a replacement from rehabilitating its original.
    return connection.execute(
        "SELECT DISTINCT e.id, e.event_kind FROM filing_events e "
        "JOIN filing_event_scopes s ON s.event_id=e.id "
        "JOIN filing_versions f ON f.id=e.source_filing_version_id "
        "WHERE e.issuer_id=%s AND e.id=ANY(%s) AND s.filing_id=ANY(%s) "
        "AND (s.period_id IS NULL OR s.period_id=%s) "
        "AND (s.concept_std IS NULL OR s.concept_std=ANY(%s)) "
        "AND (%s::date IS NULL OR e.announced_date<=%s) "
        "AND f.metadata_capture_id=ANY(%s) "
        "AND e.event_kind IN ('non_reliance','withdrawal')",
        (
            query.issuer_id,
            list(query.filing_event_ids),
            [row["filing_id"] for row in editions],
            query.period_id,
            [concept.value for concept in query.concepts],
            query.filed_cutoff,
            query.filed_cutoff,
            list(captures),
        ),
    ).fetchall()


def _read_statement(connection: Connection[Row], query: PitQuery) -> StatementSelection:
    captures, flags = _bundle(connection, query)
    if flags:
        return _result(query, flags=flags)
    rows = _eligible_coverage(connection, query, captures)
    if not rows:
        return _result(query, flags={"coverage_unavailable"})
    editions, flags = _edition(rows, query)
    if flags:
        return _result(query, flags=flags, rows=editions)
    facts, flags, quality_ids = _facts(connection, query, editions, captures)
    events = _events(connection, query, editions, captures)
    flags.update(event["event_kind"] for event in events)
    if query.mode == HistoryMode.ORIGINAL_AS_FILED and not query.original_history_complete:
        flags.add("earliest_available")
    if query.mode == HistoryMode.LATEST_REPORTED:
        flags.add("revised_view")
    return _result(
        query,
        flags=flags,
        rows=editions,
        facts=facts,
        quality_ids=quality_ids,
        event_ids=_ids(event["id"] for event in events),
    )


def read_statement(connection: Connection[Row], query: PitQuery) -> StatementSelection:
    """Read one statement from an idle connection in a consistent, read-only snapshot."""
    if connection.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("PIT reads require an idle connection for a consistent snapshot")
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return _read_statement(connection, query)


@dataclass(frozen=True)
class FinancialSelection:
    statements: tuple[StatementSelection, ...]
    flags: tuple[str, ...]
    usable_for_valuation: bool


def read_statements(
    connection: Connection[Row], queries: tuple[PitQuery, ...]
) -> FinancialSelection:
    """Read several statements atomically, flagging incompatible editions and bases.

    The engine receives explicit incompatibility, never a silently mixed series.
    All queries must pin the same history, captures and normalization policy.
    """
    if not queries:
        raise ValueError("At least one statement query is required")
    if connection.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("PIT reads require an idle connection for a consistent snapshot")
    policies = {
        (
            q.issuer_id,
            q.mode,
            q.filed_cutoff,
            q.captured_before,
            q.mapping_revision_id,
            q.normalizer_revision,
            q.authority_policy_revision,
            frozenset(q.batch_ids),
            frozenset(q.capture_ids),
            frozenset(q.filing_event_ids),
            q.audited_required,
            q.allow_reviewed_equivalent,
        )
        for q in queries
    }
    if len(policies) != 1:
        raise ValueError("Statement queries require one pinned history/source policy")
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        results = tuple(_read_statement(connection, query) for query in queries)
    flags: set[str] = set()
    for period in {q.period_id for q in queries}:
        members = [result for result in results if result.query.period_id == period]
        if len({member.reporting_basis for member in members if member.reporting_basis}) > 1:
            flags.add("incompatible_reporting_basis")
        if len({member.query.statement_family for member in members}) > 1:
            versions = {
                frozenset(member.filing_version_ids)
                for member in members
                if member.filing_version_ids
            }
            if len(versions) > 1:
                flags.add("mixed_statement_editions")
            if len({member.query.scope_id for member in members}) > 1:
                flags.add("incompatible_semantic_scopes")
            if (
                len(
                    {
                        member.query.reporting_currency_unit_id or member.query.unit_id
                        for member in members
                    }
                )
                > 1
            ):
                flags.add("incompatible_statement_currencies")
    return FinancialSelection(
        results,
        tuple(sorted(flags)),
        not flags and all(result.usable_for_valuation for result in results),
    )
