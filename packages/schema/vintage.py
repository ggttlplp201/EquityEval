"""Prepare explicit capture vintages from archived attempts, without fetching data.

This is a source-object preparation step before normalization. Roles express why
an object is needed; they do not create extra network requests or reinterpret a
cache hit as a fresh retrieval. Re-preparing can discover additional stored rows;
callers must retain the returned immutable manifest for reproducible analysis.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.pq import TransactionStatus

Row = dict[str, Any]


@dataclass(frozen=True)
class SourceObject:
    source_id: UUID
    source_object_key: str
    role: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, UUID):
            raise ValueError("A source object requires a UUID source identity")
        if not self.source_object_key.strip() or not self.role.strip():
            raise ValueError("Source object key and role must be explicit")


@dataclass(frozen=True)
class CaptureManifest:
    requirements: tuple[SourceObject, ...]
    captured_before: datetime
    capture_ids: tuple[UUID, ...]
    failed_capture_ids: tuple[UUID, ...]
    flags: tuple[str, ...]
    usable: bool
    attempt_ids: tuple[UUID, ...] = ()
    failed_attempt_ids: tuple[UUID, ...] = ()


def _successful(row: Row, cutoff: datetime) -> bool:
    status = row["http_status"]
    return (
        status is not None
        and 200 <= status < 300
        and row["fetched_at"] is not None
        and row["fetched_at"] <= cutoff
        and row["body_sha256"] is not None
        and row["blob_key"] is not None
        and bool(row["blob_key"].strip())
        and row["byte_count"] is not None
    )


def prepare_capture_manifest(
    connection: Connection[Row],
    *,
    requirements: tuple[SourceObject, ...],
    captured_before: datetime,
) -> CaptureManifest:
    """Choose archived successes and expose newer failures at an explicit cutoff.

    Both retrieval and completion must be known by the cutoff. Newer failed
    attempts warn about freshness while preserving usable historical evidence;
    missing objects and conflicting simultaneous captures block the manifest.
    A 304 revalidation keeps the original body's retrieval time and is not a
    failed attempt. Incomplete attempts cannot supply captured evidence. S3
    attempt IDs are retained separately from legacy failed-capture IDs. Outcomes
    recorded after the cutoff remain unknown at that cutoff, even when the row
    has since finalized; no completion time or HTTP result is inferred.

    ``attempt_ids`` audits every known attempt, including unfinished ones. It is
    not interchangeable with NormalizationInput's completed-at-cutoff attempt
    list; retain this manifest's unknown-outcome evidence separately.
    """
    if captured_before.utcoffset() is None:
        raise ValueError("Retrieval vintage requires a timezone-aware timestamp")
    if (
        not isinstance(requirements, tuple)
        or not requirements
        or not all(isinstance(item, SourceObject) for item in requirements)
        or len(set(requirements)) != len(requirements)
    ):
        raise ValueError("requirements must be a nonempty tuple of unique SourceObject values")
    if connection.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("Capture preparation requires an idle connection")

    objects = sorted(
        {(item.source_id, item.source_object_key) for item in requirements},
        key=lambda item: (str(item[0]), item[1]),
    )
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        rows = connection.execute(
            "SELECT c.* FROM source_captures c JOIN "
            "unnest(%s::uuid[],%s::text[]) AS requested(source_id,object_key) "
            "ON c.source_id=requested.source_id AND c.source_object_key=requested.object_key "
            "WHERE c.completed_at IS NOT NULL AND c.completed_at<=%s",
            ([item[0] for item in objects], [item[1] for item in objects], captured_before),
        ).fetchall()
        attempts = connection.execute(
            "SELECT a.* FROM source_fetch_attempts a JOIN "
            "unnest(%s::uuid[],%s::text[]) AS requested(source_id,object_key) "
            "ON a.source_id=requested.source_id AND a.source_object_key=requested.object_key "
            "WHERE a.prepared_at<=%s",
            ([item[0] for item in objects], [item[1] for item in objects], captured_before),
        ).fetchall()

    attempt_groups: dict[tuple[UUID, str], list[Row]] = {}
    for attempt in attempts:
        attempt_groups.setdefault((attempt["source_id"], attempt["source_object_key"]), []).append(
            attempt
        )
    groups: dict[tuple[UUID, str], list[Row]] = {}
    for row in rows:
        groups.setdefault((row["source_id"], row["source_object_key"]), []).append(row)
    selected: set[UUID] = set()
    failed: set[UUID] = set()
    flags: set[str] = set()
    failed_attempts: set[UUID] = set()
    for identity in objects:
        captures = groups.get(identity, [])
        successes = [row for row in captures if _successful(row, captured_before)]
        newest = max((row["fetched_at"] for row in successes), default=None)
        if newest is None:
            flags.add("capture_unavailable")
        else:
            latest = [row for row in successes if row["fetched_at"] == newest]
            if len({row["body_sha256"] for row in latest}) > 1:
                flags.add("ambiguous_capture_vintage")
            else:
                selected.update(row["id"] for row in latest)
        known = [
            attempt
            for attempt in attempt_groups.get(identity, [])
            if attempt["finished_at"] is not None and attempt["finished_at"] <= captured_before
        ]
        unknown = [
            attempt
            for attempt in attempt_groups.get(identity, [])
            if attempt["finished_at"] is None
            or attempt["finished_at"] > captured_before
            or attempt["state"] == "interrupted_unknown"
        ]
        if unknown:
            flags.add("source_attempt_outcome_unknown")
        # A successful revalidation can clear an earlier freshness failure while
        # preserving every original capture ID and its retrieval timestamp.
        validated = [
            attempt["finished_at"]
            for attempt in known
            if attempt["state"] == "not_modified" and attempt["reused_capture_id"] in selected
        ]
        freshness_boundary = max([newest, *validated]) if newest is not None else None
        current_attempt_failures = [
            attempt
            for attempt in known
            if attempt["state"]
            in {
                "http_error",
                "transport_error",
                "body_limit",
                "redirect_refused",
                "archive_error",
                "cancelled",
            }
            and (freshness_boundary is None or attempt["finished_at"] >= freshness_boundary)
        ]
        if current_attempt_failures:
            failed_attempts.update(attempt["id"] for attempt in current_attempt_failures)
            flags.add("newer_capture_failed" if newest is not None else "capture_failed")
        later_failures = [
            row
            for row in captures
            if not _successful(row, captured_before)
            and row["http_status"] != 304
            and (freshness_boundary is None or row["completed_at"] >= freshness_boundary)
        ]
        if later_failures:
            failed.update(row["id"] for row in later_failures)
            flags.add("newer_capture_failed" if newest is not None else "capture_failed")
    return CaptureManifest(
        requirements=requirements,
        captured_before=captured_before,
        capture_ids=tuple(sorted(selected, key=str)),
        failed_capture_ids=tuple(sorted(failed, key=str)),
        flags=tuple(sorted(flags)),
        usable=not bool(flags & {"capture_unavailable", "ambiguous_capture_vintage"}),
        attempt_ids=tuple(sorted((attempt["id"] for attempt in attempts), key=str)),
        failed_attempt_ids=tuple(sorted(failed_attempts, key=str)),
    )
