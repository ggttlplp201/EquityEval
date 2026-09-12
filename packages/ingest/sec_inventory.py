"""Parse pinned SEC Submissions inventories without fetching missing history.

Completeness describes advertised Submissions documents within a requested filed-
 date window. It never proves public event coverage or original-as-filed history.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from .sec_normalize import JsonNumber, canonical_cik, parse_companyfacts_json, source_json


@dataclass(frozen=True)
class InventoryFiling:
    accession: str
    filed_date: date
    form: str
    report_period_end: date | None
    primary_document: str | None
    acceptance_at: datetime | None
    acceptance_time_basis: str | None
    source_capture_id: UUID
    source_locator: str
    raw_metadata: str


@dataclass(frozen=True)
class OlderDocument:
    name: str
    filing_count: int
    filing_from: date
    filing_to: date


@dataclass(frozen=True)
class SubmissionDocument:
    cik: str
    capture_id: UUID
    document_name: str | None
    filings: tuple[InventoryFiling, ...]
    older_documents: tuple[OlderDocument, ...]
    source_cik_json: str | None


@dataclass(frozen=True)
class FilingInventory:
    cik: str
    boundary_start: date
    boundary_end: date
    filings: tuple[InventoryFiling, ...]
    capture_ids: tuple[UUID, ...]
    completeness: str
    missing_documents: tuple[str, ...]
    flags: tuple[str, ...]
    completeness_basis: str = (
        "Advertised Submissions documents only; event/original-history review is independent"
    )


def validate_older_name(name: Any, cik: str) -> str:
    if not isinstance(name, str) or not re.fullmatch(
        rf"CIK{re.escape(cik)}-submissions-[0-9]{{3}}\.json", name
    ):
        raise ValueError("Older Submissions filename must be a validated same-issuer relative name")
    return name


def _integer(value: Any) -> int:
    if not isinstance(value, JsonNumber) or not re.fullmatch(r"[0-9]+", value.text):
        raise ValueError("Inventory count must be a nonnegative integer")
    return int(value.text)


def _filings(columns: Any, capture_id: UUID, prefix: str) -> tuple[InventoryFiling, ...]:
    if not isinstance(columns, dict):
        raise ValueError("Submissions filing columns must be an object")
    required = {"accessionNumber", "filingDate", "form"}
    if not required.issubset(columns):
        raise ValueError("Submissions filing identity columns are missing")
    count = len(columns["accessionNumber"]) if isinstance(columns["accessionNumber"], list) else -1
    if count < 0 or any(
        not isinstance(values, list) or len(values) != count for values in columns.values()
    ):
        raise ValueError("Parallel Submissions columns have inconsistent length")
    result = []
    for index in range(count):
        row = {key: values[index] for key, values in columns.items()}
        accession = row["accessionNumber"]
        if not isinstance(accession, str) or not re.fullmatch(
            r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession
        ):
            raise ValueError("Invalid filing accession")
        if not isinstance(row["form"], str) or not row["form"].strip():
            raise ValueError("Invalid filing form")
        filed_date = date.fromisoformat(row["filingDate"])
        report = date.fromisoformat(row["reportDate"]) if row.get("reportDate") else None
        primary = row.get("primaryDocument") or None
        if primary is not None and (
            not isinstance(primary, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", primary)
            or ".." in primary
        ):
            raise ValueError("Primary document must be a safe relative filename")
        acceptance, basis = None, None
        acceptance_text = row.get("acceptanceDateTime")
        if acceptance_text:
            if not isinstance(acceptance_text, str):
                raise ValueError("Invalid acceptance timestamp")
            parsed = datetime.fromisoformat(acceptance_text.replace("Z", "+00:00"))
            if parsed.utcoffset() is not None:
                acceptance, basis = parsed, "verified_timezone"
            # A naive source timestamp remains raw evidence. Do not invent UTC or
            # Eastern offsets, especially at DST transitions.
        result.append(
            InventoryFiling(
                accession,
                filed_date,
                row["form"],
                report,
                primary,
                acceptance,
                basis,
                capture_id,
                f"{prefix}/{index}",
                source_json(row),
            )
        )
    return tuple(result)


def parse_submissions(
    body: bytes,
    *,
    expected_cik: str,
    capture_id: UUID,
    document_name: str | None = None,
) -> SubmissionDocument:
    """Parse an already archive-verified recent or declared older document.

    Older array-only documents carry no CIK. Their requested filename must bind
    them to the expected issuer and to the parent manifest at assembly time.
    """
    cik = canonical_cik(expected_cik)
    document = parse_companyfacts_json(body)
    if document_name is not None:
        validate_older_name(document_name, cik)
        return SubmissionDocument(
            cik, capture_id, document_name, _filings(document, capture_id, ""), (), None
        )
    if canonical_cik(document.get("cik")) != cik:
        raise ValueError("Submissions CIK does not match requested issuer")
    filing_info = document.get("filings")
    if not isinstance(filing_info, dict) or not isinstance(filing_info.get("files"), list):
        raise ValueError("Submissions requires explicit recent and older-document inventory")
    references = []
    names = set()
    for item in filing_info["files"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid older-document inventory row")
        name = validate_older_name(item.get("name"), cik)
        if name in names:
            raise ValueError("Duplicate older-document identity")
        names.add(name)
        start, end = date.fromisoformat(item["filingFrom"]), date.fromisoformat(item["filingTo"])
        if start > end:
            raise ValueError("Older inventory has reversed date bounds")
        references.append(OlderDocument(name, _integer(item["filingCount"]), start, end))
    return SubmissionDocument(
        cik,
        capture_id,
        None,
        _filings(filing_info.get("recent"), capture_id, "/filings/recent"),
        tuple(references),
        source_json(document["cik"]),
    )


def assemble_inventory(
    recent: SubmissionDocument,
    older: tuple[SubmissionDocument, ...],
    *,
    boundary_start: date,
    boundary_end: date,
) -> FilingInventory:
    if recent.document_name is not None or boundary_start > boundary_end:
        raise ValueError("A recent root and ordered explicit boundary are required")
    advertised = {item.name: item for item in recent.older_documents}
    supplied: dict[str, SubmissionDocument] = {}
    for document in older:
        if document.cik != recent.cik or document.document_name not in advertised:
            raise ValueError("Older document was not advertised by this issuer's pinned root")
        if document.document_name in supplied:
            raise ValueError(
                "Conflicting duplicate older-document captures require explicit vintage choice"
            )
        supplied[document.document_name] = document
    needed = {
        name
        for name, reference in advertised.items()
        if reference.filing_from <= boundary_end and reference.filing_to >= boundary_start
    }
    missing = tuple(sorted(needed - supplied.keys()))
    flags: set[str] = set()
    if missing:
        flags.add("missing_advertised_history")
    for document in (recent, *older):
        if len({filing.accession for filing in document.filings}) != len(document.filings):
            flags.add("duplicate_accessions_in_document")
    records = list(recent.filings)
    for name, document in supplied.items():
        reference = advertised[name]
        if len(document.filings) != reference.filing_count or any(
            not reference.filing_from <= filing.filed_date <= reference.filing_to
            for filing in document.filings
        ):
            flags.add("older_inventory_metadata_mismatch")
        records.extend(document.filings)
    selected = [item for item in records if boundary_start <= item.filed_date <= boundary_end]
    identities: dict[str, set[str]] = {}
    for item in selected:
        identities.setdefault(item.accession, set()).add(item.raw_metadata)
    if any(len(versions) > 1 for versions in identities.values()):
        flags.add("conflicting_filing_metadata")
    return FilingInventory(
        recent.cik,
        boundary_start,
        boundary_end,
        tuple(
            sorted(
                selected,
                key=lambda item: (item.filed_date, item.accession, str(item.source_capture_id)),
            )
        ),
        tuple(sorted({recent.capture_id, *(item.capture_id for item in older)}, key=str)),
        "incomplete" if flags else "complete",
        missing,
        tuple(sorted(flags)),
    )
