"""D5d archived exhibit review; never promotes a historical or current metric."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.export_crcl_safety import REVIEW_SHA
from scripts.normalize_crcl import ROOT
from scripts.review_crcl_safety import REPORT as PRIOR_REPORT

ACQUISITION = "docs/research/crcl-exhibit-acquisition-2026-10-13.json"
REPORT = "docs/research/crcl-exhibit-review-2026-10-13.json"


def plan(root: Path = ROOT) -> list[dict[str, Any]]:
    raw = (root / PRIOR_REPORT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != REVIEW_SHA:
        raise ValueError("D5c exhibit roster changed")
    prior = json.loads(raw)
    filings = {row["accession"]: row for row in prior["filings"]}
    result = []
    for exhibit in prior["missingExhibits"]:
        parent = filings[exhibit["accession"]]
        filename = exhibit["resourceKey"].rsplit("/", 1)[1]
        number = {
            "dp229888_ex0301.htm": "3.1",
            "dp229888_ex0302.htm": "3.2",
            "final-projecttaurusxshar.htm": "2.1",
        }.get(filename, "99.1")
        result.append(
            {
                **exhibit,
                "exhibit": number,
                "form": parent["form"],
                "filedDate": parent["filedDate"],
                "items": parent["items"],
                "parentSha256": parent["bodySha256"],
            }
        )
    if len(result) != 11:
        raise ValueError("D5d requires the eleven reviewed exhibit links")
    return result


def groups(rows: list[dict[str, Any]]) -> tuple[tuple[str, ...], ...]:
    keys = [row["resourceKey"] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate exhibit resource")
    return tuple(tuple(keys[index : index + 5]) for index in range(0, len(keys), 5))


def capture_index(
    captures: list[dict[str, Any]], planned: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    from scripts.normalize_crcl import RESOURCES
    from scripts.review_crcl_safety import within_historical_cutoff

    allowed = {row["resourceKey"] for row in planned}
    result = {}
    for capture in captures:
        key = capture["source_object_key"]
        if key in RESOURCES[:2]:
            continue
        if key not in allowed or key in result:
            raise ValueError("Exhibit capture is duplicated or outside the pinned roster")
        if within_historical_cutoff(capture["completed_at"]):
            raise ValueError("New exhibit retrieval cannot be backdated")
        if capture["http_status"] == 200:
            result[key] = capture
    return result


def clean(text: str) -> str:
    import re

    return re.sub(r"\s+", " ", text.replace("\u200b", " ")).strip()


def checked_text(body: bytes, digest: str, quotes: list[str]) -> str:
    from lxml import html

    from scripts.review_crcl_identity import normalized_text

    if hashlib.sha256(body).hexdigest() != digest:
        raise ValueError("Human-reviewed exhibit edition changed")
    text = clean(normalized_text(html.fromstring(body.decode("utf-8"))))
    for quote in quotes:
        if clean(quote) not in text:
            raise ValueError("Reviewed exhibit quote is absent")
    return text


def statement_rows(
    text: str, header: str, expected: list[tuple[str, list[str]]]
) -> list[dict[str, Any]]:
    import re

    text = clean(text)
    header = clean(header)
    if text.count(header) != 1:
        raise ValueError("Statement period, unit or column header changed")
    statement = text.split(header, 1)[1]
    result = []
    for label, values in expected:
        if statement.count(label) != 1:
            raise ValueError("Statement row is ambiguous")
        tail = statement.split(label, 1)[1].lstrip()
        match = re.match(r"(?:\(?[\d,]+\)?\s*)+", tail)
        if match is None or match.group().split() != values:
            raise ValueError("Statement signed values or column order changed")
        result.append({"label": label, "values": values, "header": header})
    return result


def periodic_evidence(
    capture: dict[str, Any],
    body: bytes,
    periods: list[tuple[int, str, str]],
    values: list[list[str]],
) -> list[dict[str, Any]]:
    from equity_ingest.filing import extract_inline_filing

    from scripts.normalize_crcl import CIK

    parsed = extract_inline_filing(
        body,
        expected_sha256=capture["body_sha256"],
        expected_byte_count=capture["byte_count"],
        expected_cik=CIK,
    )
    contexts = {row.id: row for row in parsed.contexts}
    units = {row.id: row for row in parsed.units}
    result = []
    for row_index, concept in enumerate(("Revenues", "OperatingIncomeLoss")):
        for column, start, end in periods:
            candidates = []
            for fact in parsed.facts:
                context = contexts.get(fact.context_id or "")
                unit = units.get(fact.unit_id or "")
                if (
                    fact.qualified_tag.endswith("}" + concept)
                    and fact.qualified_tag.startswith("{http://fasb.org/us-gaap/")
                    and context is not None
                    and context.valid
                    and context.cik == CIK
                    and context.period_kind == "duration"
                    and not context.dimensions
                    and str(context.start_date) == start
                    and str(context.end_date) == end
                    and unit is not None
                    and unit.valid
                    and not unit.denominator_measures
                    and unit.numerator_measures == ("{http://www.xbrl.org/2003/iso4217}USD",)
                    and fact.status == "observed"
                    and fact.scale == 3
                ):
                    signed = (
                        ("(" + fact.lexical_text + ")") if fact.sign == "-" else fact.lexical_text
                    )
                    if clean(signed) != values[row_index][column]:
                        raise ValueError("Paired periodic operand disagrees with exhibit")
                    candidates.append(fact)
            if not candidates:
                raise ValueError("No exact consolidated USD periodic operand for reviewed period")
            result.append(
                {
                    "concept": concept,
                    "start": start,
                    "end": end,
                    "exhibitColumn": column + 1,
                    "literalThousands": values[row_index][column],
                    "unit": "USD",
                    "scale": 3,
                    "locators": [fact.locator for fact in candidates],
                    "captureId": capture["capture_id"],
                    "sha256": capture["body_sha256"],
                }
            )
    return result


def review_acquisition(acquisition: dict[str, Any] | None, root: Path = ROOT) -> dict[str, Any]:
    from datetime import datetime
    from uuid import UUID

    from equity_ingest.archive import LocalArchive
    from equity_ingest.sec_inventory import parse_submissions

    from scripts.crcl_exhibit_dispositions import EARNINGS, REVIEWS
    from scripts.normalize_crcl import CIK, CUTOFF, RESOURCES, resource_url
    from scripts.review_crcl_identity import read_audit
    from scripts.review_crcl_safety import ACQUISITION as PRIOR_ACQUISITION
    from scripts.review_crcl_safety import FORMS, scope_inventory, source_detail

    planned = plan(root)
    archive = LocalArchive(root / "var/raw")
    captures = [c for g in (acquisition or {}).get("groups", []) for c in g["captures"]]
    if len((acquisition or {}).get("groups", [])) > 3:
        raise ValueError("Exhibit acquisition escaped bounded group count")
    indexed = capture_index(captures, planned)
    # Check every captured body, including mandatory inventory/facts, without network.
    for capture in captures:
        archive.read_blob(capture["blob_key"], capture["body_sha256"], capture["byte_count"])
    original = read_audit(root)["captures"]
    prior_raw = (root / PRIOR_ACQUISITION).read_bytes()
    prior_report = json.loads((root / PRIOR_REPORT).read_bytes())
    if hashlib.sha256(prior_raw).hexdigest() != prior_report["acquisitionSha256"]:
        raise ValueError("Prior periodic acquisition lineage changed")
    prior = json.loads(prior_raw)
    periodic = {
        c["source_object_key"].split("/")[2]: c
        for c in original + [c for g in prior["groups"] for c in g["captures"]]
        if c["source_object_key"].startswith("filing_document/")
    }
    rows, details = [], {}
    for number, item in enumerate(planned):
        filename = item["resourceKey"].rsplit("/", 1)[1]
        disposition = REVIEWS[filename]
        capture = indexed.get(item["resourceKey"])
        row = {
            **item,
            "id": f"exhibit-{number}",
            "status": "missing",
            "scope": disposition["scope"],
            "relevance": disposition["relevance"],
            "finding": "Body unavailable; content finding unconfirmed.",
            "limit": disposition["limit"],
            "captureId": None,
            "capturedAt": None,
            "sha256": None,
        }
        if capture is not None:
            body = archive.read_blob(
                capture["blob_key"], capture["body_sha256"], capture["byte_count"]
            )
            text = checked_text(body, disposition["sha256"], disposition["quotes"])
            row.update(
                status="reviewed_with_limits",
                finding=disposition["finding"],
                captureId=capture["capture_id"],
                capturedAt=capture["completed_at"],
                sha256=capture["body_sha256"],
            )
            sources = [source_detail(capture, item["accession"])]
            evidence = [
                {"label": "Review scope", "value": row["scope"]},
                {"label": "Finding", "value": row["finding"]},
                {"label": "Remaining limit", "value": row["limit"]},
                {
                    "label": "Parent exhibit link",
                    "value": f"{item['accession']} / {item['parentSha256']}",
                },
            ]
            for quote in disposition["quotes"]:
                evidence.append(
                    {
                        "label": "Exact retained quote · normalized text offset "
                        + str(text.index(clean(quote))),
                        "value": quote,
                    }
                )
            if filename in EARNINGS:
                _, suffix, revenue, income, accession, periods = EARNINGS[filename]
                op_label = (
                    "Operating income from continuing operations"
                    if filename == "final_05x11q1epr30.htm"
                    else "Operating income (loss) from continuing operations"
                )
                statement = statement_rows(
                    text,
                    "CONSOLIDATED STATEMENTS OF OPERATIONS " + suffix,
                    [("Total revenue and reserve income", revenue), (op_label, income)],
                )
                paired = periodic[accession]
                paired_body = archive.read_blob(
                    paired["blob_key"], paired["body_sha256"], paired["byte_count"]
                )
                comparisons = periodic_evidence(paired, paired_body, periods, [revenue, income])
                row["statementChecks"] = statement
                row["periodicComparisons"] = comparisons
                sources.append(source_detail(paired, accession))
                evidence += [
                    {
                        "label": "Statement unit / period / ordered columns",
                        "value": statement[0]["header"],
                    },
                    {
                        "label": "Reported rows (source thousands; no ratio calculated)",
                        "value": json.dumps(statement),
                    },
                    {
                        "label": (
                            "Paired filing proof: explicit USD unit, scale, period, consolidated "
                            "context and signed literal"
                        ),
                        "value": json.dumps(comparisons),
                    },
                    {
                        "label": "Currency scope",
                        "value": (
                            "Release labels dollars/thousands; explicit USD is established by "
                            "paired filing contexts. This is not evidence of quote currency."
                        ),
                    },
                ]
            details[row["id"]] = {
                "title": item["label"],
                "subtitle": "D5d retrospective exhibit review · actual October retrieval",
                "sections": [{"heading": "Evidence and limits", "rows": evidence}],
                "sources": sources,
            }
        rows.append(row)
    fresh_inventory = None
    fresh = [
        c for c in captures if c["source_object_key"] == RESOURCES[1] and c["http_status"] == 200
    ]
    if fresh:
        if len({c["body_sha256"] for c in fresh}) != 1:
            raise ValueError(
                "Inventory editions changed during bounded acquisition; review required"
            )
        capture = max(fresh, key=lambda c: datetime.fromisoformat(c["completed_at"]))
        document = parse_submissions(
            archive.read_blob(capture["blob_key"], capture["body_sha256"], capture["byte_count"]),
            expected_cik=CIK,
            capture_id=UUID(capture["capture_id"]),
        )
        current = scope_inventory(document, {})
        old = json.loads((root / PRIOR_REPORT).read_bytes())["filings"]
        if [(r["accession"], r["form"], r["filedDate"], r["resourceKey"]) for r in current] != [
            (r["accession"], r["form"], r["filedDate"], r["resourceKey"]) for r in old
        ]:
            raise ValueError("Historical inventory changed; separate edition review required")
        fresh_inventory = {
            "source": source_detail(capture),
            "sha256": capture["body_sha256"],
            "outsidePinnedWindow": [
                {
                    "accession": f.accession,
                    "form": f.form,
                    "filedDate": str(f.filed_date),
                    "url": resource_url(
                        f"filing_document/{CIK}/{f.accession}/{f.primary_document}"
                    ),
                }
                for f in document.filings
                if f.form in FORMS and f.filed_date > CUTOFF.date()
            ],
        }
    missing = [r["resourceKey"] for r in rows if r["status"] == "missing"]
    return {
        "kind": "real-crcl-exhibit-review",
        "reviewedOn": "2026-10-13",
        "proposalCommit": "564edfd",
        "priorReviewSha256": REVIEW_SHA,
        "historicalRetrievalCutoff": CUTOFF.isoformat(),
        "historicalStatus": "blocked",
        "currentStatus": "blocked",
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "reviewedCount": len(rows) - len(missing),
        "missingExhibits": missing,
        "exhibits": rows,
        "details": details,
        "acquisitionStatus": (acquisition or {}).get("status", "unavailable"),
        "originalRowsPreserved": (acquisition or {}).get("originalRowsPreserved"),
        "freshInventory": fresh_inventory,
        "conclusion": (
            "The retained exhibits support only their stated retrospective "
            "findings. October retrievals do not repair September application "
            "knowledge; no metric is published."
        ),
        "blockers": [
            (
                "September knowledge: exhibit and primary bodies retrieved later cannot"
                " clear the saved D5a cutoff."
            ),
            (
                "Current coverage: later primary filings remain unreviewed; fresh "
                "inventory alone is not current financial-history clearance."
            ),
            (
                "Accounting scope: completed operand comparisons corroborate only the "
                "explicitly tested periods; they do not resolve every annual affected-line "
                "reclassification. Agreement schedules and target statements remain "
                "unavailable as financial proof."
            )
            if any(row.get("periodicComparisons") for row in rows)
            else (
                "Accounting scope: reported-operand corroboration is unavailable; no "
                "periodic comparison completed. Annual affected-line reclassification "
                "and agreement/target accounting scope remain unconfirmed."
            ),
            (
                "Publication: real S6 authorization/contract gate remains; no "
                "eligibility override, normalized replacement batch or numeric metric "
                "is created."
            ),
        ]
        + (["Acquisition incomplete: exact missing exhibit keys are listed."] if missing else [])
        + (
            ["Application preservation remains unverified."]
            if (acquisition or {}).get("originalRowsPreserved") is not True
            else []
        ),
        "nextStep": (
            "Review the later primary filings identified by the fresh inventory "
            "under a separately pinned current cutoff, settle the remaining "
            "affected-line scope and real S6 publication gate."
        )
        if fresh_inventory
        else (
            "Capture and review inventory and missing bodies under a separately "
            "pinned cutoff before any current eligibility decision."
        ),
    }


def review(root: Path = ROOT) -> dict[str, Any]:
    target = root / ACQUISITION
    raw = target.read_bytes() if target.exists() else None
    result = review_acquisition(json.loads(raw) if raw else None, root)
    result["acquisitionSha256"] = hashlib.sha256(raw).hexdigest() if raw else None
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = json.dumps(review(), indent=2, sort_keys=True) + "\n"
    target = ROOT / REPORT
    if args.check:
        if not target.exists() or target.read_text() != result:
            raise ValueError("Saved exhibit review differs from archived replay")
    else:
        target.write_text(result)
    print(json.dumps({"review": REPORT, "verified": args.check}))


if __name__ == "__main__":
    main()
