"""Read immutable market evidence, selecting the response before inspecting its value.

Retrieval cutoffs constrain original complete captures, not parsing/publication time.
Source vintage DATEs remain inclusive DATEs. Optional source_known_at asks the stricter
publication question: date-only evidence on that UTC date is ambiguous and unavailable.
No query fills gaps, converts units, adjusts prices, or searches for an older usable value.
"""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import Connection, sql
from psycopg.pq import TransactionStatus

Row = dict[str, Any]
PRICE_FIELDS = frozenset(
    (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adj_open",
        "adj_high",
        "adj_low",
        "adj_close",
        "adj_volume",
        "div_cash",
        "split_factor",
    )
)


@dataclass(frozen=True)
class MarketQualityFlag:
    id: UUID
    rule_key: str
    severity: str
    message: str
    reference_date: date | None
    field_key: str | None
    capture_id: UUID | None
    attempt_id: UUID | None
    source_locator: str | None


@dataclass(frozen=True)
class CaptureProvenance:
    capture_id: UUID
    role: str
    source_id: UUID
    source_object_key: str
    request_url: str
    body_sha256: str
    blob_key: str
    fetched_at: datetime
    completed_at: datetime


@dataclass(frozen=True)
class MarketSelection:
    data_kind: str
    source_id: UUID
    reference_date: date
    field: str
    value: Decimal | None = None
    value_state: str = "unavailable"
    usable: bool = False
    original_value_text: str | None = None
    batch_id: UUID | None = None
    candidate_batch_ids: tuple[UUID, ...] = ()
    observation_id: UUID | None = None
    observation_ids: tuple[UUID, ...] = ()
    provenance: tuple[CaptureProvenance, ...] = ()
    attempt_ids: tuple[UUID, ...] = ()
    flags: tuple[str, ...] = ()
    quality_flags: tuple[MarketQualityFlag, ...] = ()
    coverage_state: str | None = None
    captured_at: datetime | None = None
    evidence_known_at: datetime | None = None
    response_at: datetime | None = None
    capture_age: timedelta | None = None
    reference_age_days: int | None = None
    selection_date: date | None = None
    max_age_days: int | None = None
    retrieval_cutoff: datetime | None = None
    source_as_of_date: date | None = None
    source_known_at: datetime | None = None
    input_manifest_hash: str | None = None
    output_manifest_hash: str | None = None
    manifest_blob_key: str | None = None
    parser_revision: str | None = None
    normalizer_revision: str | None = None
    selection_policy_revision: str | None = None
    source_locator: str | None = None
    source_date_text: str | None = None
    transform_revision: str | None = None
    publication_precision: str | None = None
    source_published_date: date | None = None
    source_published_at: datetime | None = None
    currency: str | None = None
    quote_identifier_id: UUID | None = None
    security_id: UUID | None = None
    quote_binding_id: UUID | None = None
    adjustment_basis: str | None = None
    adjustment_vintage_basis: str | None = None
    adjustment_vintage_date: date | None = None
    session_basis: str | None = None
    session_timezone: str | None = None
    series_key: str | None = None
    series_definition_id: UUID | None = None
    unit_code: str | None = None
    units_text: str | None = None
    unit_multiplier: Decimal | None = None
    frequency: str | None = None
    seasonal_adjustment: str | None = None
    definition_as_of_basis: str | None = None
    definition_as_of_date: date | None = None
    source_vintage_basis: str | None = None
    source_realtime_start: date | None = None
    source_realtime_end: date | None = None
    reference_end_date: date | None = None
    source_observation_status: str | None = None


def select_price(
    db: Connection[Row],
    source_id: UUID,
    quote_identifier_id: UUID,
    session_date: date,
    field: str = "close",
    *,
    retrieval_cutoff: datetime | None = None,
    batch_id: UUID | None = None,
    source_known_at: datetime | None = None,
) -> MarketSelection:
    """Select one exact price field/date; raw close is never substituted by adjusted close."""
    if field not in PRICE_FIELDS:
        raise ValueError("Unknown price field")
    query = MarketSelection(
        "price",
        source_id,
        session_date,
        field,
        quote_identifier_id=quote_identifier_id,
        retrieval_cutoff=retrieval_cutoff,
        source_known_at=source_known_at,
    )
    return _read(db, query, batch_id)


def select_macro(
    db: Connection[Row],
    source_id: UUID,
    series_key: str,
    reference_date: date,
    *,
    source_as_of_date: date | None = None,
    retrieval_cutoff: datetime | None = None,
    batch_id: UUID | None = None,
    source_known_at: datetime | None = None,
) -> MarketSelection:
    """Select an exact native-unit observation; an as-of DATE must match the requested response."""
    if (
        not isinstance(series_key, str)
        or not series_key.strip()
        or series_key != series_key.strip()
    ):
        raise ValueError("An exact nonempty series key is required")
    query = MarketSelection(
        "macro",
        source_id,
        reference_date,
        "value",
        series_key=series_key,
        retrieval_cutoff=retrieval_cutoff,
        source_as_of_date=source_as_of_date,
        source_known_at=source_known_at,
    )
    return _read(db, query, batch_id)


def select_macro_at_or_before(
    db: Connection[Row],
    source_id: UUID,
    series_key: str,
    selection_date: date,
    *,
    max_age_days: int,
    source_as_of_date: date | None = None,
    retrieval_cutoff: datetime | None = None,
    batch_id: UUID | None = None,
    source_known_at: datetime | None = None,
) -> MarketSelection:
    """Read the latest actual bounded date from its newest applicable response.

    A newer empty or missing response blocks the result; this never searches older
    dates for a usable value or invents an observation on the selection date.
    An unrelated older-period backfill cannot displace a newer reference date.
    The returned reference age is measured against the caller's selection date.
    """
    if type(max_age_days) is not int or max_age_days < 0:
        raise ValueError("Maximum reference age must be a nonnegative integer")
    if type(selection_date) is not date or max_age_days >= selection_date.toordinal():
        raise ValueError("Selection date and maximum age must define a valid date window")
    if (
        not isinstance(series_key, str)
        or not series_key.strip()
        or series_key != series_key.strip()
    ):
        raise ValueError("An exact nonempty series key is required")
    return _read(
        db,
        MarketSelection(
            "macro",
            source_id,
            selection_date,
            "value",
            series_key=series_key,
            selection_date=selection_date,
            max_age_days=max_age_days,
            source_as_of_date=source_as_of_date,
            retrieval_cutoff=retrieval_cutoff,
            source_known_at=source_known_at,
        ),
        batch_id,
    )


def _read(db: Connection[Row], query: MarketSelection, batch_id: UUID | None) -> MarketSelection:
    if not isinstance(query.source_id, UUID) or (
        batch_id is not None and not isinstance(batch_id, UUID)
    ):
        raise ValueError("Source and batch identities require UUIDs")
    if query.data_kind == "price" and not isinstance(query.quote_identifier_id, UUID):
        raise ValueError("Quote identity requires a UUID")
    if type(query.reference_date) is not date or (
        query.source_as_of_date is not None and type(query.source_as_of_date) is not date
    ):
        raise ValueError("Reference and source vintage require exact dates")
    for value in (query.retrieval_cutoff, query.source_known_at):
        if value is not None and (not isinstance(value, datetime) or value.utcoffset() is None):
            raise ValueError("Cutoffs require timezone-aware timestamps")
    if db.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("Selection requires an idle connection for its evidence snapshot")
    with db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        if query.max_age_days is not None:
            return _backward(db, query, batch_id)
        return _select(db, query, batch_id)


def _batches(
    db: Connection[Row],
    q: MarketSelection,
    batch_id: UUID | None,
    window_start: date | None = None,
) -> list[Row]:
    # Every metadata input must be eligible. Ranking is driven by responses/outcomes,
    # so re-parsing older bytes today cannot outrank a genuinely newer response.
    return db.execute(
        """
        SELECT b.*, evidence.response_at, evidence.known_at, evidence.response_ids
        FROM market_data_batches b
        CROSS JOIN LATERAL (
          SELECT max(CASE WHEN i.role IN ('observations','fetch_outcome')
                          THEN coalesce(c.completed_at,a.finished_at,a.prepared_at) END)
                   AS response_at,
                 max(coalesce(c.completed_at,a.finished_at,a.prepared_at)) AS known_at,
                 array_agg(coalesce(i.capture_id,i.attempt_id)::text
                   ORDER BY coalesce(i.capture_id,i.attempt_id)::text)
                   FILTER(WHERE i.role IN ('observations','fetch_outcome')) AS response_ids,
                 bool_and(coalesce(c.completed_at,a.finished_at,a.prepared_at) IS NOT NULL
                   AND (%(cutoff)s::timestamptz IS NULL
                     OR coalesce(c.completed_at,a.finished_at,a.prepared_at)<=%(cutoff)s))
                   AS eligible
          FROM market_data_batch_inputs i LEFT JOIN source_captures c ON c.id=i.capture_id
          LEFT JOIN source_fetch_attempts a ON a.id=i.attempt_id WHERE i.batch_id=b.id
        ) evidence
        WHERE b.state='published' AND b.source_id=%(source)s AND b.data_kind=%(kind)s
          AND b.quote_identifier_id IS NOT DISTINCT FROM %(quote)s::uuid
          AND b.source_series_key IS NOT DISTINCT FROM %(series)s::text
          AND b.requested_start<=%(day)s AND b.requested_end>=%(window_start)s
          AND b.source_as_of_date IS NOT DISTINCT FROM %(asof)s::date
          AND (%(batch)s::uuid IS NULL OR b.id=%(batch)s)
          AND evidence.eligible AND evidence.response_at IS NOT NULL
        ORDER BY evidence.response_at DESC,b.published_at DESC
    """,
        dict(
            cutoff=q.retrieval_cutoff,
            source=q.source_id,
            kind=q.data_kind,
            quote=q.quote_identifier_id,
            series=q.series_key,
            day=q.reference_date,
            window_start=window_start or q.reference_date,
            asof=q.source_as_of_date,
            batch=batch_id,
        ),
    ).fetchall()


def _backward(db: Connection[Row], q: MarketSelection, batch_id: UUID | None) -> MarketSelection:
    assert q.max_age_days is not None and q.selection_date is not None
    first_date = q.selection_date - timedelta(days=q.max_age_days)
    batches = _batches(db, q, batch_id, first_date)
    if not batches:
        return replace(q, flags=("no_eligible_batch",))
    # Dates, including missing-value observations, establish the reference order.
    # Only then rank applicable responses, still before inspecting value/coverage.
    latest = db.execute(
        "SELECT max(reference_date) AS day FROM macro_observations "
        "WHERE batch_id=ANY(%s) AND reference_date BETWEEN %s AND %s",
        ([batch["id"] for batch in batches], first_date, q.selection_date),
    ).fetchone()
    assert latest is not None
    selected_date = latest["day"]
    if selected_date:
        # Older-period backfills do not supersede a newer dated observation, but a
        # newer empty response for that date or a later window blocks carry-forward.
        batches = [batch for batch in batches if batch["requested_end"] >= selected_date]
    query = replace(q, reference_date=selected_date) if selected_date else q
    result = _select(db, query, batch_id, batches=batches)
    if result.observation_id is None:
        return result
    flags = set(result.flags)
    if result.reference_date != q.selection_date:
        flags.add("backward_selected")
    return replace(
        result,
        reference_age_days=(q.selection_date - result.reference_date).days,
        flags=tuple(sorted(flags)),
    )


def _select(
    db: Connection[Row],
    q: MarketSelection,
    batch_id: UUID | None,
    *,
    batches: list[Row] | None = None,
) -> MarketSelection:
    if batches is None:
        batches = _batches(db, q, batch_id)
    if not batches:
        return replace(q, flags=("no_eligible_batch",))
    batch = batches[0]
    tied = [b for b in batches if b["response_at"] == batch["response_at"]]
    if len({tuple(b["response_ids"]) for b in tied}) > 1:
        return replace(
            q, candidate_batch_ids=tuple(b["id"] for b in tied), flags=("ambiguous_batch",)
        )
    flags = {"explicit_batch"} if batch_id else set()
    quality = tuple(
        MarketQualityFlag(**row)
        for row in db.execute(
            """
        SELECT id,rule_key,severity,message,reference_date,field_key,
               capture_id,attempt_id,source_locator
        FROM market_data_quality_flags WHERE batch_id=%s
          AND (reference_date IS NULL OR reference_date=%s) AND (field_key IS NULL OR field_key=%s)
        ORDER BY rule_key,id
    """,
            (batch["id"], q.reference_date, q.field),
        ).fetchall()
    )
    provenance = tuple(
        CaptureProvenance(**row)
        for row in db.execute(
            """
        SELECT c.id AS capture_id,i.role,c.source_id,c.source_object_key,c.request_url,
               c.body_sha256,c.blob_key,c.fetched_at,c.completed_at
        FROM market_data_batch_inputs i JOIN source_captures c ON c.id=i.capture_id
        WHERE i.batch_id=%s ORDER BY i.role,c.id
    """,
            (batch["id"],),
        ).fetchall()
    )
    attempts = tuple(
        row["attempt_id"]
        for row in db.execute(
            "SELECT attempt_id FROM market_data_batch_inputs WHERE batch_id=%s "
            "AND attempt_id IS NOT NULL ORDER BY attempt_id",
            (batch["id"],),
        ).fetchall()
    )
    q = replace(
        q,
        batch_id=batch["id"],
        candidate_batch_ids=(batch["id"],),
        coverage_state=batch["coverage_state"],
        response_at=batch["response_at"],
        evidence_known_at=batch["known_at"],
        provenance=provenance,
        attempt_ids=attempts,
        quality_flags=quality,
        **{
            key: batch[key]
            for key in (
                "input_manifest_hash",
                "output_manifest_hash",
                "manifest_blob_key",
                "parser_revision",
                "normalizer_revision",
                "selection_policy_revision",
            )
        },
    )
    table, day_column = (
        ("price_daily", "session_date")
        if q.data_kind == "price"
        else ("macro_observations", "reference_date")
    )
    rows = db.execute(
        sql.SQL("SELECT * FROM {} WHERE batch_id=%s AND {}=%s ORDER BY id").format(
            sql.Identifier(table), sql.Identifier(day_column)
        ),
        (batch["id"], q.reference_date),
    ).fetchall()
    q = replace(q, observation_ids=tuple(row["id"] for row in rows))
    if len(rows) != 1:
        flags.add("missing_observation" if not rows else "ambiguous_observation")
        return replace(q, flags=tuple(sorted(flags)))
    row = rows[0]
    captured_at = next(
        c.completed_at for c in provenance if c.capture_id == row["source_capture_id"]
    )
    age_at = q.retrieval_cutoff or datetime.now(UTC)
    q = replace(
        q,
        observation_id=row["id"],
        captured_at=captured_at,
        capture_age=age_at - captured_at,
        reference_age_days=(age_at.astimezone(UTC).date() - q.reference_date).days,
        **{
            key: row[key]
            for key in (
                "source_locator",
                "source_date_text",
                "transform_revision",
                "publication_precision",
                "source_published_date",
                "source_published_at",
            )
        },
    )
    if q.source_known_at is not None:
        problem = _publication_problem(row, q.source_known_at, q.source_as_of_date)
        if problem:
            return replace(q, flags=tuple(sorted(flags | {problem})))
    if q.data_kind == "macro":
        q, problem = _macro_metadata(db, q, row)
        if problem:
            return replace(q, flags=tuple(sorted(flags | {problem})))
        if q.source_as_of_date and q.definition_as_of_basis != "source_supplied":
            flags.add("definition_history_unavailable")
        q = replace(
            q,
            value=row["value"],
            value_state=row["value_state"],
            original_value_text=row["original_value_text"],
        )
    else:
        q = replace(
            q,
            value=row[q.field],
            value_state=row[q.field + "_state"],
            original_value_text=row[q.field + "_text"],
            currency=row["dividend_currency"]
            if q.field == "div_cash"
            else (
                None
                if q.field in ("volume", "adj_volume", "split_factor")
                else row["quote_currency"]
            ),
            **{
                key: row[key]
                for key in (
                    "security_id",
                    "quote_binding_id",
                    "adjustment_basis",
                    "adjustment_vintage_basis",
                    "adjustment_vintage_date",
                    "session_basis",
                    "session_timezone",
                )
            },
        )
    flags.update(f.rule_key for f in quality)
    blocking = "definition_history_unavailable" in flags or any(
        f.severity in ("error", "blocking") for f in quality
    )
    if q.value_state != "observed":
        flags.add(q.value_state)
    if q.coverage_state != "complete":
        flags.add("incomplete_coverage")
        blocking = True
    return replace(
        q, flags=tuple(sorted(flags)), usable=q.value_state == "observed" and not blocking
    )


def _publication_problem(row: Row, cutoff: datetime, source_as_of: date | None) -> str | None:
    boundary = cutoff.astimezone(UTC).date()
    if source_as_of is not None and source_as_of >= boundary:
        return "ambiguous_source_vintage_at_instant"
    start = row.get("source_realtime_start")
    if start is not None and start >= boundary:
        return "ambiguous_source_vintage_at_instant"
    if row["publication_precision"] == "instant":
        return None if row["source_published_at"] <= cutoff else "source_publication_after_cutoff"
    if row["publication_precision"] == "date":
        return (
            None if row["source_published_date"] < boundary else "ambiguous_source_publication_date"
        )
    return "unknown_source_publication_time"


def _macro_metadata(
    db: Connection[Row], q: MarketSelection, row: Row
) -> tuple[MarketSelection, str | None]:
    definition = db.execute(
        "SELECT * FROM macro_series_definitions WHERE id=%s", (row["series_definition_id"],)
    ).fetchone()
    assert definition is not None  # Enforced foreign key within this snapshot.
    as_of = q.source_as_of_date
    if definition["definition_as_of_date"] is not None and (
        (as_of is not None and definition["definition_as_of_date"] > as_of)
        or (
            q.source_known_at is not None
            and definition["definition_as_of_date"] >= q.source_known_at.astimezone(UTC).date()
        )
    ):
        return q, "future_series_definition"
    if as_of is not None and (
        row["requested_source_as_of"] != as_of
        or row["source_vintage_basis"] not in ("source_interval", "requested_as_of")
        or (
            row["source_realtime_start"] is not None
            and not row["source_realtime_start"] <= as_of <= row["source_realtime_end"]
        )
    ):
        return q, "source_vintage_mismatch"
    q = replace(
        q,
        series_definition_id=definition["id"],
        **{
            key: definition[key]
            for key in (
                "unit_code",
                "units_text",
                "unit_multiplier",
                "frequency",
                "seasonal_adjustment",
                "definition_as_of_basis",
                "definition_as_of_date",
            )
        },
        **{
            key: row[key]
            for key in (
                "source_vintage_basis",
                "source_realtime_start",
                "source_realtime_end",
                "reference_end_date",
                "source_observation_status",
            )
        },
    )
    return q, None
