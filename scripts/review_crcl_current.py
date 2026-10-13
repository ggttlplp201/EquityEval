"D5e bounded current-window review; never retrofits historical knowledge."

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.export_crcl_exhibits import REVIEW_SHA as PRIOR_SHA
from scripts.normalize_crcl import CIK, ROOT, resource_url
from scripts.review_crcl_exhibits import REPORT as PRIOR_REPORT

ACQUISITION = "docs/research/crcl-current-acquisition-2026-10-13.json"
REPORT = "docs/research/crcl-current-review-2026-10-13.json"
EXPECTED = (
    ("0001876042-26-000276", "2026-09-22", "crcl-20260917.htm"),
    ("0001876042-26-000279", "2026-09-25", "crcl-20260925.htm"),
)


def plan(root: Path = ROOT) -> list[dict[str, Any]]:
    raw = (root / PRIOR_REPORT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SHA:
        raise ValueError("Pinned D5d later-filing evidence changed")
    prior = json.loads(raw)
    rows = sorted(prior["freshInventory"]["outsidePinnedWindow"], key=lambda r: r["accession"])
    if len(rows) != len(EXPECTED):
        raise ValueError("D5e requires exactly the two pinned later primaries")
    result = []
    for row, (accession, filed, filename) in zip(rows, EXPECTED, strict=True):
        key = f"filing_document/{CIK}/{accession}/{filename}"
        if (row["accession"], row["filedDate"], row["form"], row["url"]) != (
            accession,
            filed,
            "8-K",
            resource_url(key),
        ):
            raise ValueError("Later filing identity differs from proposal")
        result.append({**row, "resourceKey": key})
    return result


def groups(rows: list[dict[str, Any]]) -> tuple[tuple[str, ...], ...]:
    keys = tuple(row["resourceKey"] for row in rows)
    if len(keys) != 2 or len(set(keys)) != 2:
        raise ValueError("D5e requires two distinct primary documents")
    return (keys,)


def annual_edition_check(records: list[dict[str, Any]], expected_value: str) -> dict[str, Any]:
    expected = {
        "start": "2025-01-01",
        "end": "2025-12-31",
        "accn": "0001876042-26-000062",
        "form": "10-K",
        "filed": "2026-03-09",
    }
    matched = len(records) == 1 and all(records[0].get(k) == v for k, v in expected.items())
    matched = matched and str(records[0].get("val")) == expected_value
    return {
        "status": "matched" if matched else "blocked",
        "records": records,
        "reason": "Exact original annual edition and source value match."
        if matched
        else ("Missing, changed or additional annual edition requires source-body review."),
    }


def candidate_decision(
    *,
    missing_bodies: list[str],
    accounting_complete: bool,
    inventory_complete: bool,
    acquisition_complete: bool,
) -> dict[str, Any]:
    reasons = []
    if missing_bodies:
        reasons.append("linked_body_unreviewed")
    if not accounting_complete:
        reasons.append("affected_line_scope_unresolved")
    if not inventory_complete:
        reasons.append("current_inventory_incomplete")
    if not acquisition_complete:
        reasons.append("acquisition_or_preservation_incomplete")
    return {
        "status": "blocked" if reasons else "requires_governed_preparation",
        "batchId": None,
        "reasonCodes": reasons,
        "explanation": (
            "No new PIT batch was published. Evidence gaps must close before "
            "reviewed preparation; real S6 remains outside this milestone."
        ),
    }


def reconcile_editions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields = ("concept", "start", "end", "unit", "scale", "literalThousands")
    bases = {tuple(row.get(field) for field in fields) for row in rows}
    matched = (
        len({row["captureId"] for row in rows}) >= 2
        and len(bases) == 1
        and all(row.get("unit") == "USD" and row.get("scale") == 3 for row in rows)
    )
    return {
        "status": "matched" if matched else "unconfirmed",
        "evidence": rows,
        "reason": (
            "Distinct retained editions match exact selected line, period, unit, "
            "scale and signed literal."
        )
        if matched
        else ("Distinct comparable editions are missing or differ; no unchanged-line claim."),
    }


def review_inventory(
    document: Any, expected_rows: list[dict[str, Any]], observed: Any
) -> dict[str, Any]:
    from equity_ingest.sec_inventory import assemble_inventory

    from scripts.review_crcl_safety import FORMS, START

    inventory = assemble_inventory(document, (), boundary_start=START, boundary_end=observed.date())
    expected = {r["accession"] for r in expected_rows}
    expected_identities = {
        (r["accession"], r["form"], r["filedDate"], r["resourceKey"]) for r in expected_rows
    }
    scoped = [f for f in inventory.filings if f.form in FORMS]
    actual = {f.accession for f in scoped}
    actual_identities = {
        (
            f.accession,
            f.form,
            str(f.filed_date),
            f"filing_document/{CIK}/{f.accession}/{f.primary_document}",
        )
        for f in scoped
    }
    complete = (
        not inventory.flags
        and not inventory.missing_documents
        and inventory.completeness == "complete"
        and actual_identities == expected_identities
        and all(f.acceptance_at is not None and f.acceptance_at <= observed for f in scoped)
    )
    return {
        "status": "matched_scoped_roster" if complete else "blocked",
        "forms": sorted(FORMS),
        "boundaryStart": str(START),
        "boundaryEnd": str(observed.date()),
        "count": len(scoped),
        "unexpectedAccessions": sorted(actual - expected),
        "missingAccessions": sorted(expected - actual),
        "changedIdentities": sorted({r[0] for r in actual_identities ^ expected_identities}),
        "missingHistoryFiles": list(inventory.missing_documents),
        "filings": [
            {
                "accession": f.accession,
                "form": f.form,
                "filedDate": str(f.filed_date),
                "items": json.loads(f.raw_metadata).get("items", ""),
                "acceptedAt": f.acceptance_at.isoformat() if f.acceptance_at else None,
                "metadataLocator": f.source_locator,
            }
            for f in scoped
        ],
        "note": (
            "This is the specified financial/event-form inventory observed at its capture "
            "time, not proof of every SEC form or later public event. Date boundaries do "
            "not assert knowledge of the remainder of the day."
        ),
    }


EVENT_REVIEWS = {
    "0001876042-26-000276": {
        "sha256": "6e752f46a2efde82d2783330cb6dcdea15868efe064cd38fd041045be86e95f3",
        "title": "Binance arrangements and private placement",
        "quotes": [
            (
                "The agreement supersedes and replaces the agreements the Company "
                "previously entered into with Binance in November 2024 and in August "
                "2025."
            ),
            (
                "we agreed to pay Binance a monthly incentive fee representing a "
                "percentage of the amount of USDC held through the Modular Smart "
                "Contract Wallet infrastructure service"
            ),
        ],
        "finding": (
            "Entire primary body reviewed. It reports September 2026 commercial "
            "arrangements and a concurrent private placement, with only embedded "
            "Exhibit 104. The new terms matter to future distribution economics "
            "and share basis, but the body supplies no FY2025 "
            "revenue/operating-income correction or affected-line reconciliation."
            " No financial-statement non-reliance declaration was identified in "
            "this body."
        ),
        "limit": (
            "No inference about recognition of the new arrangements or future "
            "margins; no market quote or per-share ratio is created."
        ),
        "linked": [],
    },
    "0001876042-26-000279": {
        "sha256": "09196ebd34e78c16b07585fc53eb488aae8fe5becc742a12909bbfed5b5433d6",
        "title": "Director and CFO departures",
        "quotes": [
            (
                "Mr. Fox-Geen’s departure from the Company did not result from any "
                "disagreement with the operations, policies, or practices of the "
                "Company."
            ),
            (
                "The press release is furnished as Exhibit 99.1 to this Report and "
                "incorporated herein by reference."
            ),
        ],
        "finding": (
            "Entire primary body reviewed. It describes a director resignation, "
            "CFO transition and compensation/restrictive-covenant terms. The "
            "no-disagreement statement is not an audit opinion or proof that "
            "selected income lines are unchanged. No financial-statement "
            "non-reliance declaration was identified in the primary body; "
            "referenced Exhibit 99.1 remains unreviewed."
        ),
        "limit": (
            "The CFO-departure release cannot be classified from its parent "
            "metadata. Its body is required before closing this event review."
        ),
        "linked": ["final_leadershiptransiti.htm"],
    },
}


def review_acquisition(acquisition: dict[str, Any] | None, root: Path = ROOT) -> dict[str, Any]:
    from datetime import datetime
    from uuid import UUID

    from equity_ingest.archive import LocalArchive
    from equity_ingest.sec_inventory import parse_submissions

    from scripts.normalize_crcl import CUTOFF, RESOURCES
    from scripts.review_crcl_exhibits import clean
    from scripts.review_crcl_identity import normalized_text, xml_root
    from scripts.review_crcl_safety import source_detail

    planned = plan(root)
    prior = json.loads((root / PRIOR_REPORT).read_bytes())
    old_raw = (root / "docs/research/crcl-safety-review-2026-10-12.json").read_bytes()
    if hashlib.sha256(old_raw).hexdigest() != prior["priorReviewSha256"]:
        raise ValueError("Prior D5c reconciliation evidence changed")
    old = json.loads(old_raw)
    archive = LocalArchive(root / "var/raw")
    acquired_groups = (acquisition or {}).get("groups", [])
    if len(acquired_groups) > 1:
        raise ValueError("D5e acquisition escaped its single governed group")
    captures = [c for g in acquired_groups for c in g["captures"]]
    allowed = {row["resourceKey"] for row in planned} | set(RESOURCES[:2])
    indexed, bodies = {}, {}
    seen: set[str] = set()
    for capture in captures:
        key = capture["source_object_key"]
        stamp = datetime.fromisoformat(capture["completed_at"])
        if key not in allowed or key in seen or stamp.utcoffset() is None or stamp <= CUTOFF:
            raise ValueError("Unexpected, duplicate or backdated current capture")
        seen.add(key)
        body = archive.read_blob(capture["blob_key"], capture["body_sha256"], capture["byte_count"])
        if capture["http_status"] == 200:
            indexed[key], bodies[key] = capture, body
    details: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for item in planned:
        accession = item["accession"]
        disposition = EVENT_REVIEWS[accession]
        capture = indexed.get(item["resourceKey"])
        row = {
            **item,
            "id": accession,
            "title": disposition["title"],
            "status": "missing",
            "finding": "Primary body unavailable; event content review unconfirmed.",
            "limit": disposition["limit"],
            "capturedAt": None,
            "sha256": None,
        }
        if capture is not None:
            body = bodies[item["resourceKey"]]
            if hashlib.sha256(body).hexdigest() != disposition["sha256"]:
                raise ValueError("Reviewed primary edition changed")
            text = clean(normalized_text(xml_root(body)))
            if any(q not in text for q in disposition["quotes"]):
                raise ValueError("Reviewed primary quote changed")
            # These are exact exhibit links observed during full primary-body review.
            for filename in disposition["linked"]:
                if filename.encode() not in bodies[item["resourceKey"]]:
                    raise ValueError("Reviewed linked exhibit changed")
                key = f"filing_document/{CIK}/{accession}/{filename}"
                missing.append(
                    {
                        "resourceKey": key,
                        "accession": accession,
                        "exhibit": "99.1",
                        "url": resource_url(key),
                        "reason": (
                            "Referenced CFO-departure release body not retained or reviewed in "
                            "this bounded group."
                        ),
                    }
                )
            row.update(
                status="primary_reviewed",
                finding=disposition["finding"],
                capturedAt=capture["completed_at"],
                sha256=capture["body_sha256"],
            )
            details[accession] = {
                "title": disposition["title"],
                "subtitle": "D5e · entire retained primary body reviewed",
                "sections": [
                    {
                        "heading": "Evidence and limits",
                        "rows": [
                            {"label": "Finding", "value": row["finding"]},
                            {"label": "Limit", "value": row["limit"]},
                            *[
                                {
                                    "label": (
                                        f"Retained quote · normalized text offset {text.index(q)}"
                                    ),
                                    "value": q,
                                }
                                for q in disposition["quotes"]
                            ],
                        ],
                    }
                ],
                "sources": [source_detail(capture, accession)],
            }
        events.append(row)
    retrieval_cutoff = max(
        (datetime.fromisoformat(c["completed_at"]) for c in captures), default=None
    )
    inventory_capture = indexed.get(RESOURCES[1])
    inventory_complete = False
    current_inventory = None
    if inventory_capture is not None:
        observed = datetime.fromisoformat(inventory_capture["completed_at"])
        document = parse_submissions(
            bodies[RESOURCES[1]], expected_cik=CIK, capture_id=UUID(inventory_capture["capture_id"])
        )
        current_inventory = {
            **review_inventory(document, old["filings"] + planned, observed),
            "source": source_detail(inventory_capture),
            "sha256": inventory_capture["body_sha256"],
        }
        inventory_complete = current_inventory["status"] == "matched_scoped_roster"
        for event in events:
            matches = [
                f for f in current_inventory["filings"] if f["accession"] == event["accession"]
            ]
            if len(matches) == 1:
                event.update({k: matches[0][k] for k in ("items", "acceptedAt", "metadataLocator")})
    annual_checks = []
    facts_capture = indexed.get(RESOURCES[0])
    if facts_capture is not None:
        facts = json.loads(bodies[RESOURCES[0]])
        if str(facts.get("cik", "")).zfill(10) != CIK:
            raise ValueError("Current Company Facts issuer changed")
        for concept, expected_value in (
            ("Revenues", "2746642000"),
            ("OperatingIncomeLoss", "-96435000"),
        ):
            units = facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {})
            records = [
                r
                for r in units.get("USD", [])
                if r.get("start") == "2025-01-01" and r.get("end") == "2025-12-31"
            ]
            checked = annual_edition_check(records, expected_value)
            annual_checks.append({"concept": concept, **checked})
        details["annual-editions"] = {
            "title": "Fresh Company Facts annual editions",
            "subtitle": "Exact source USD values; no ratio calculated",
            "sections": [
                {
                    "heading": "Evidence and limits",
                    "rows": [
                        {"label": check["concept"], "value": json.dumps(check, sort_keys=True)}
                        for check in annual_checks
                    ],
                }
            ],
            "sources": [
                {
                    **source_detail(facts_capture, "0001876042-26-000062"),
                    "label": "SEC Company Facts · exact annual filing row",
                }
            ],
        }
    # Prior matched operands are retained as dated corroboration, not recast as a current clearance.
    matrix = [
        {
            "id": "annual",
            "label": "FY2025 annual release versus original 10-K",
            "status": "matched_prior_review",
            "finding": (
                "D5d verified both reported annual operands, exact annual column, USD"
                " filing unit and scale/sign. Fresh Company Facts editions are "
                "checked separately."
            ),
            "detailId": "annual",
        },
        {
            "id": "q2-h1",
            "label": "Q2 and H1 FY2025 repeated comparatives",
            "status": "matched_prior_review",
            "finding": (
                "D5d verified the same selected Q2/H1 operands in 2025 and 2026 "
                "releases and their retained periodic filings. This corroborates "
                "those periods without constructing an annual number."
            ),
            "detailId": "q2-h1",
        },
        {
            "id": "q1",
            "label": "Q1 FY2025 earlier edition",
            "status": "unconfirmed",
            "finding": (
                "The retained Q1 evidence is the 2026 comparative. No earlier Q1 "
                "primary edition is retained in this reviewed set to establish "
                "unchanged affected-line presentation; matching the 2026 release to "
                "that same 2026 filing does not provide it."
            ),
            "detailId": "q1",
        },
        {
            "id": "annual-scope",
            "label": "Annual affected-line reclassification scope",
            "status": "unconfirmed",
            "finding": (
                "The original annual pair is corroborated; the amendment expressly "
                "leaves other disclosures unchanged. Generic prior-period "
                "reclassification text does not identify revenue/operating-income "
                "effects. Partial comparative matches alone do not certify every "
                "affected-line/edition question. No actual change is inferred."
            ),
            "detailId": "annual-scope",
        },
    ]
    for identifier, prior_id in (
        ("annual", "exhibit-5"),
        ("q2-h1", "exhibit-8"),
        ("q1", "exhibit-7"),
    ):
        saved = prior["details"][prior_id]
        details[identifier] = {
            **saved,
            "subtitle": "D5d saved corroboration · separate from D5e current coverage",
        }
    comparison_rows = [
        r for exhibit in prior["exhibits"] for r in exhibit.get("periodicComparisons", [])
    ]
    affected_lines = []
    for start_date, end_date in (
        ("2025-01-01", "2025-03-31"),
        ("2025-04-01", "2025-06-30"),
        ("2025-01-01", "2025-06-30"),
    ):
        for concept in ("Revenues", "OperatingIncomeLoss"):
            observations = [
                r
                for r in comparison_rows
                if (r["concept"], r["start"], r["end"]) == (concept, start_date, end_date)
            ]
            affected_lines.append(
                {
                    "concept": concept,
                    "start": start_date,
                    "end": end_date,
                    **reconcile_editions(observations),
                }
            )
    details["q2-h1"] = {
        **details["q2-h1"],
        "sections": details["q2-h1"]["sections"]
        + [
            {
                "heading": "Cross-edition reconciliation",
                "rows": [
                    {
                        "label": f"{row['concept']} · {row['start']} to {row['end']}",
                        "value": json.dumps(row, sort_keys=True),
                    }
                    for row in affected_lines
                ],
            }
        ],
        "sources": details["q2-h1"]["sources"]
        + prior["details"]["exhibit-3"]["sources"]
        + prior["details"]["exhibit-7"]["sources"],
    }
    details["annual-scope"] = {
        **old["details"]["reclassifications"],
        "sections": old["details"]["reclassifications"]["sections"]
        + old["details"]["amendment"]["sections"],
        "sources": old["details"]["reclassifications"]["sources"]
        + old["details"]["amendment"]["sources"],
    }
    acquisition_complete = (
        (acquisition or {}).get("status") == "captured_pending_review"
        and (acquisition or {}).get("originalRowsPreserved") is True
        and len(indexed) == 4
    )
    accounting_complete = (
        all(row["status"] == "matched_prior_review" for row in matrix)
        and len(annual_checks) == 2
        and all(row["status"] == "matched" for row in annual_checks)
    )
    candidate = candidate_decision(
        missing_bodies=[row["resourceKey"] for row in missing],
        accounting_complete=accounting_complete,
        inventory_complete=inventory_complete,
        acquisition_complete=acquisition_complete,
    )
    return {
        "kind": "real-crcl-current-review",
        "reviewedOn": "2026-10-13",
        "proposalCommit": "373c358",
        "priorReviewSha256": PRIOR_SHA,
        "historicalRetrievalCutoff": CUTOFF.isoformat(),
        "inventoryObservedAt": inventory_capture["completed_at"] if inventory_capture else None,
        "retrievalCutoff": retrieval_cutoff.isoformat() if retrieval_cutoff else None,
        "currentInventory": current_inventory,
        "events": events,
        "missingBodies": missing,
        "annualEditionChecks": annual_checks,
        "affectedLineChecks": affected_lines,
        "reconciliation": matrix,
        "details": details,
        "candidateBatch": candidate,
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "conclusion": (
            "The reviewed later primary bodies add specific current-window evidence. "
            "Missing linked content and unresolved affected-line scope prevent a new "
            "eligible PIT batch. Historical September knowledge and real S6 gates "
            "remain unchanged."
        )
        if any(row["status"] == "primary_reviewed" for row in events)
        else (
            "Current primary-body evidence is unavailable. No current event-review "
            "completion or new eligible PIT batch is established."
        ),
        "cutoffNote": (
            "Inventory was observed at its own timestamp. The later retrieval cutoff "
            "records when all acquired evidence was held; it does not extend public-event "
            "coverage beyond the inventory observation or repair September knowledge."
        ),
        "nextStep": (
            "Pin review of the exact outstanding CFO-departure exhibit and resolve the "
            "remaining affected-line/edition evidence before preparing a new governed "
            "PIT batch. Real S6 publication remains a separate proposal boundary."
        )
        if missing
        else (
            "Complete the missing primary/inventory acquisition and affected-line review "
            "before preparing a new governed PIT batch. Real S6 remains separately gated."
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
    encoded = json.dumps(review(), indent=2, sort_keys=True) + "\n"
    target = ROOT / REPORT
    if args.check:
        if not target.exists() or target.read_text() != encoded:
            raise ValueError("Current review differs from archived replay")
    else:
        target.write_text(encoded)
    print(json.dumps({"review": REPORT, "verified": args.check}))


if __name__ == "__main__":
    main()
