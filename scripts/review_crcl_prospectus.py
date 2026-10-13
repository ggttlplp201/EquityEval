"""D5g archived IPO prospectus reconciliation, never historical lookahead repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.export_crcl_leadership import REVIEW_SHA as PRIOR_SHA
from scripts.normalize_crcl import ROOT
from scripts.review_crcl_leadership import REPORT as PRIOR_REPORT

ACQUISITION = "docs/research/crcl-prospectus-acquisition-2026-10-13.json"
REPORT = "docs/research/crcl-prospectus-review-2026-10-13.json"
KEY = "filing_document/0001876042/0001193125-25-135795/d737521d424b4.htm"


def plan(root: Path = ROOT) -> list[dict[str, Any]]:
    raw = (root / PRIOR_REPORT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SHA:
        raise ValueError("Pinned D5f prospectus evidence changed")
    prior = json.loads(raw)
    if prior["nextSource"] != KEY:
        raise ValueError("Prospectus identity differs from proposal")
    return [{"resourceKey": KEY, "url": prior["nextSourceUrl"]}]


def groups(rows: list[dict[str, Any]]) -> tuple[tuple[str, ...], ...]:
    if [row["resourceKey"] for row in rows] != [KEY]:
        raise ValueError("D5g source scope changed")
    return ((KEY,),)


BODY_SHA = "c6cad26039ea6e29ef98f5faca7df5419e6828523c89b3895dc568df568b279c"
Q1_HEADER = "Three MonthsEnded March 31, (in thousands, except per share information) 2025 2024"
ANNUAL_HEADER = (
    "(in thousands, except per share information) Year Ended December 31, 2024 2023 2022"
)
Q1_VALUES = [["578,573", "365,094"], ["92,940", "52,319"]]
ANNUAL_VALUES = [["1,676,253", "1,450,466", "772,052"], ["167,158", "269,528", "(38,116)"]]
REGISTRATION_FORMS = frozenset({"S-1", "S-1/A", "424B4", "424B3"})
QUOTES = [
    "Effective February 13, 2023, Grant Thornton LLP (the “Former Auditor”) was "
    "dismissed as our independent accountant.",
    "may result in a restatement of our annual or interim financial statements.",
    "Our reporting currency is the U.S. dollar and the functional currency of our "
    "international operations is its local currency.",
    "These reclassifications have no impact on the unaudited condensed consolidated "
    "financial statements.",
    "The historical basis of accounting was retained as if the entities had always "
    "been combined for financial reporting purposes.",
    "This prospectus does not contain all of the information set forth in the "
    "registration statement and the exhibits and schedules thereto.",
]


def check_q1_table(text: str) -> list[dict[str, Any]]:
    from scripts.review_crcl_exhibits import statement_rows

    return statement_rows(
        text.replace(" )", ")"),
        Q1_HEADER,
        list(
            zip(
                ("Total revenue and reserve income", "Operating income from continuing operations"),
                Q1_VALUES,
                strict=True,
            )
        ),
    )


def registration_roster(document: dict[str, Any]) -> list[dict[str, Any]]:
    from scripts.normalize_crcl import CIK, resource_url

    if str(document.get("cik", "")).zfill(10) != CIK:
        raise ValueError("Registration inventory issuer changed")
    recent = document["filings"]["recent"]
    rows = []
    for index, form in enumerate(recent["form"]):
        if form not in REGISTRATION_FORMS or recent["filingDate"][index] < "2025-01-01":
            continue
        accession = recent["accessionNumber"][index]
        key = f"filing_document/{CIK}/{accession}/{recent['primaryDocument'][index]}"
        rows.append(
            {
                "resourceKey": key,
                "accession": accession,
                "form": form,
                "filedDate": recent["filingDate"][index],
                "url": resource_url(key),
                "locator": f"filings.recent row {index}",
            }
        )
    if len({r["accession"] for r in rows}) != len(rows):
        raise ValueError("Ambiguous registration inventory")
    return rows


def compare_prospectus(body: bytes, capture: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    from equity_ingest.archive import LocalArchive
    from lxml import html

    from scripts.review_crcl_exhibits import checked_text, clean, periodic_evidence, statement_rows
    from scripts.review_crcl_identity import normalized_text, read_audit
    from scripts.review_crcl_safety import source_detail

    text = checked_text(body, BODY_SHA, QUOTES)
    doc: Any = html.fromstring(body.decode("utf-8"))
    tables = doc.xpath("//table")
    q1 = tables[513]
    annual = tables[569]
    q1_rows = check_q1_table(clean(normalized_text(q1)))
    annual_rows = statement_rows(
        clean(normalized_text(annual)).replace(" )", ")"),
        ANNUAL_HEADER,
        list(
            zip(
                (
                    "Total revenue and reserve income from continuing operations",
                    "Operating income (loss) from continuing operations",
                ),
                ANNUAL_VALUES,
                strict=True,
            )
        ),
    )
    # Independent existing inline extractor validates entity, empty dimensions, USD,
    # duration, sign/scale and every matching equivalent fact in each later filing.
    original = read_audit(root)["captures"]
    safety_raw = (root / "docs/research/crcl-safety-acquisition-2026-10-12.json").read_bytes()
    from scripts.export_crcl_safety import REVIEW_SHA as safety_sha

    safety_report = (root / "docs/research/crcl-safety-review-2026-10-12.json").read_bytes()
    if (
        hashlib.sha256(safety_report).hexdigest() != safety_sha
        or hashlib.sha256(safety_raw).hexdigest() != json.loads(safety_report)["acquisitionSha256"]
    ):
        raise ValueError("Retained later filing lineage changed")
    captures = original + [c for g in json.loads(safety_raw)["groups"] for c in g["captures"]]
    paired = []
    sources = [source_detail(capture, "0001193125-25-135795")]
    for accession, periods, values in (
        ("0001876042-26-000150", [(0, "2025-01-01", "2025-03-31")], Q1_VALUES),
        (
            "0001876042-26-000062",
            [(0, "2024-01-01", "2024-12-31"), (1, "2023-01-01", "2023-12-31")],
            ANNUAL_VALUES,
        ),
    ):
        candidate = next(c for c in captures if f"/{accession}/" in c["source_object_key"])
        later_body = LocalArchive(root / "var/raw").read_blob(
            candidate["blob_key"], candidate["body_sha256"], candidate["byte_count"]
        )
        paired += periodic_evidence(candidate, later_body, periods, values)
        sources.append(source_detail(candidate, accession))
    return {
        "status": "matched_tested_operands",
        "prospectusStatements": [
            {
                "page": "F-4",
                "scope": "Circle Internet Group, Inc. and subsidiaries; consolidated; unaudited",
                "period": "Q1 2025 and Q1 2024",
                "unit": "USD",
                "scale": 3,
                "locator": doc.getroottree().getpath(q1),
                "rows": q1_rows,
            },
            {
                "scope": "Circle Internet Group, Inc. and subsidiaries; consolidated; annual",
                "period": "FY2024/FY2023/FY2022",
                "unit": "USD",
                "scale": 3,
                "locator": doc.getroottree().getpath(annual),
                "rows": annual_rows,
            },
        ],
        "laterComparisons": paired,
        "sources": sources,
        "quotes": [{"quote": q, "offset": text.index(q)} for q in QUOTES],
        "finding": (
            "The final IPO prospectus supplies the earlier Q1 reported pair. Both "
            "operands "
            "match the retained 2026 Q1 comparative. Its FY2024/FY2023 annual selected lines also "
            "match the FY2025 annual filing comparatives. This resolves those specific "
            "earlier-edition "
            "and affected-line comparisons, alongside saved Q2/H1 matches. No ratio or synthetic "
            "quarter is calculated; pro forma EPS and adjusted EBITDA are excluded."
        ),
        "limit": (
            "Matching tested statements does not certify unreviewed registration "
            "editions or "
            "every accounting line. Prospective restatement/control-risk language is not an actual "
            "correction. The disclosed February 2023 auditor change is not a FY2025 correction; "
            "its referenced letter is not treated as reviewed assurance."
        ),
    }


def review_acquisition(acquisition: dict[str, Any] | None, root: Path = ROOT) -> dict[str, Any]:
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from equity_ingest.archive import LocalArchive
    from equity_ingest.sec_inventory import parse_submissions

    from scripts.normalize_crcl import CIK, CUTOFF, RESOURCES
    from scripts.review_crcl_current import annual_edition_check, review_inventory
    from scripts.review_crcl_leadership import ACQUISITION as prior_acquisition
    from scripts.review_crcl_leadership import q1_facts_review
    from scripts.review_crcl_leadership import review as replay_prior
    from scripts.review_crcl_safety import source_detail

    plan(root)
    prior = replay_prior(root)
    if (
        hashlib.sha256((json.dumps(prior, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        != PRIOR_SHA
    ):
        raise ValueError("D5f archived replay changed")
    old_acq = json.loads((root / prior_acquisition).read_bytes())
    old_inventory = next(
        c for c in old_acq["groups"][0]["captures"] if c["source_object_key"] == RESOURCES[1]
    )
    archive = LocalArchive(root / "var/raw")
    old_doc = json.loads(
        archive.read_blob(
            old_inventory["blob_key"], old_inventory["body_sha256"], old_inventory["byte_count"]
        )
    )
    expected_registration = registration_roster(old_doc)
    groups_ = (acquisition or {}).get("groups", [])
    if len(groups_) > 1:
        raise ValueError("D5g escaped its single group")
    indexed, bodies, seen = {}, {}, set()
    for c in [c for g in groups_ for c in g["captures"]]:
        key = c["source_object_key"]
        stamp = datetime.fromisoformat(c["completed_at"])
        if (
            key not in {KEY, *RESOURCES[:2]}
            or key in seen
            or stamp.utcoffset() is None
            or stamp <= datetime.fromisoformat(prior["retrievalCutoff"])
        ):
            raise ValueError("Unexpected, duplicate or backdated prospectus capture")
        seen.add(key)
        body = archive.read_blob(c["blob_key"], c["body_sha256"], c["byte_count"])
        if c["http_status"] == 200:
            indexed[key], bodies[key] = c, body
    comparison = compare_prospectus(bodies[KEY], indexed[KEY], root) if KEY in indexed else None
    registration = expected_registration
    inventory = None
    if RESOURCES[1] in indexed:
        c = indexed[RESOURCES[1]]
        doc = json.loads(bodies[RESOURCES[1]])
        registration = registration_roster(doc)
        recent = old_doc["filings"]["recent"]
        expected = []
        for row in prior["currentInventory"]["filings"]:
            i = recent["accessionNumber"].index(row["accession"])
            expected.append(
                {
                    **row,
                    "resourceKey": (
                        f"filing_document/{CIK}/{row['accession']}/{recent['primaryDocument'][i]}"
                    ),
                }
            )
        inventory = {
            **review_inventory(
                parse_submissions(
                    bodies[RESOURCES[1]], expected_cik=CIK, capture_id=UUID(c["capture_id"])
                ),
                expected,
                datetime.fromisoformat(c["completed_at"]),
            ),
            "source": source_detail(c),
        }

    def identities(rows: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
        return {(r["resourceKey"], r["form"], r["filedDate"]) for r in rows}

    registration_matches = inventory is not None and (
        identities(registration) == identities(expected_registration)
    )
    missing = [
        {
            **r,
            "reason": "Registration/prospectus body not retained and substantively reviewed; "
            "its edition/correction content is unconfirmed from inventory metadata.",
        }
        for r in registration
        if not (r["resourceKey"] == KEY and comparison)
    ]
    vintages = list(prior["q1FactsVintages"])
    annual = []
    if RESOURCES[0] in indexed:
        c = indexed[RESOURCES[0]]
        facts = json.loads(bodies[RESOURCES[0]])
        vintages.append(
            {
                "captureId": c["capture_id"],
                "sha256": c["body_sha256"],
                "source": {**source_detail(c), "label": "SEC Company Facts"},
                **q1_facts_review(facts),
            }
        )
        for concept, value in [("Revenues", "2746642000"), ("OperatingIncomeLoss", "-96435000")]:
            records = [
                r
                for r in facts.get("facts", {})
                .get("us-gaap", {})
                .get(concept, {})
                .get("units", {})
                .get("USD", [])
                if r.get("start") == "2025-01-01" and r.get("end") == "2025-12-31"
            ]
            annual.append({"concept": concept, **annual_edition_check(records, value)})
    facts_match = bool(comparison) and all(
        v["status"] == "later_comparative_only"
        and all(
            Decimal(str(r["record"]["val"]))
            == Decimal({"Revenues": "578573000", "OperatingIncomeLoss": "92940000"}[r["concept"]])
            for r in v["rows"]
        )
        for v in vintages
    )
    complete = (
        len(indexed) == 3
        and (acquisition or {}).get("status") == "captured_pending_review"
        and (acquisition or {}).get("originalRowsPreserved") is True
    )
    reasons = []
    if comparison is None:
        reasons.append("prospectus_body_unreviewed")
    if missing:
        reasons.append("registration_history_unreviewed")
    if (
        inventory is None
        or inventory["status"] != "matched_scoped_roster"
        or not registration_matches
    ):
        reasons.append("current_inventory_incomplete")
    if not facts_match or len(annual) != 2 or any(r["status"] != "matched" for r in annual):
        reasons.append("facts_edition_unconfirmed")
    if not complete:
        reasons.append("acquisition_or_preservation_incomplete")
    details = {}
    if comparison:
        details["statements"] = {
            "title": "IPO statements versus later retained editions",
            "subtitle": "Reported consolidated operands; exact USD scale and signed literals",
            "sections": [
                {
                    "heading": "Evidence and limits",
                    "rows": [
                        {"label": "Finding", "value": comparison["finding"]},
                        {"label": "Limit", "value": comparison["limit"]},
                        {
                            "label": "Source statements",
                            "value": json.dumps(comparison["prospectusStatements"], sort_keys=True),
                        },
                        {
                            "label": "Later exact contexts",
                            "value": json.dumps(comparison["laterComparisons"], sort_keys=True),
                        },
                        {
                            "label": "Basis and edition references",
                            "value": json.dumps(comparison["quotes"], sort_keys=True),
                        },
                    ],
                }
            ],
            "sources": comparison["sources"],
        }
    details["facts"] = {
        "title": "Every retained Q1 Facts vintage",
        "subtitle": "Source attribution and comparison; not a substitute for filing-body review",
        "sections": [
            {
                "heading": "Evidence and limits",
                "rows": [
                    {
                        "label": v["captureId"],
                        "value": json.dumps(
                            {k: x for k, x in v.items() if k != "source"}, sort_keys=True
                        ),
                    }
                    for v in vintages
                ],
            }
        ],
        "sources": [v["source"] for v in vintages],
    }
    details["registration"] = {
        "title": "Exact registration-history gap",
        "subtitle": "Inventory metadata, not inferred body content",
        "sections": [
            {
                "heading": "Evidence and limits",
                "rows": [
                    {
                        "label": "Coverage boundary",
                        "value": (
                            "Prior 21-primary coverage was limited to K/Q/8-K "
                            "financial/event forms. Registration/prospectus editions "
                            "are now explicit; no broad complete-history claim "
                            "follows from that narrower roster."
                        ),
                    },
                    {"label": "Required body review", "value": json.dumps(missing, sort_keys=True)},
                    {
                        "label": "Why required",
                        "value": (
                            "These are known financial registration/prospectus "
                            "editions within the review window. Their selected-line "
                            "presentation, amendment changes and correction "
                            "disclosures cannot be classified from form/date "
                            "metadata. Review them in a separately pinned batch "
                            "before declaring original/event history complete."
                        ),
                    },
                ],
            }
        ],
        "sources": [source_detail(indexed.get(RESOURCES[1], old_inventory))],
    }
    if annual:
        details["annual"] = {
            "title": "Fresh FY2025 annual Facts editions",
            "subtitle": "Exact source rows; no ratio",
            "sections": [
                {
                    "heading": "Evidence and limits",
                    "rows": [
                        {"label": r["concept"], "value": json.dumps(r, sort_keys=True)}
                        for r in annual
                    ],
                }
            ],
            "sources": [
                {
                    **source_detail(indexed[RESOURCES[0]], "0001876042-26-000062"),
                    "label": "SEC Company Facts",
                }
            ],
        }
    return {
        "kind": "real-crcl-prospectus-review",
        "reviewedOn": "2026-10-13",
        "proposalCommit": "4866b16",
        "priorReviewSha256": PRIOR_SHA,
        "comparison": comparison,
        "q1FactsVintages": vintages,
        "q1FactsMatch": facts_match,
        "annualEditionChecks": annual,
        "currentInventory": inventory,
        "registrationRoster": registration,
        "registrationRosterMatches": registration_matches,
        "missingBodies": missing,
        "details": details,
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "candidateBatch": {
            "status": "blocked" if reasons else "requires_governed_preparation",
            "batchId": None,
            "reasonCodes": reasons,
            "explanation": (
                "No new PIT batch is published. Specific statement matches do not "
                "establish complete registration/event history; real S6 remains "
                "separately gated."
            ),
        },
        "historicalRetrievalCutoff": CUTOFF.isoformat(),
        "inventoryObservedAt": indexed[RESOURCES[1]]["completed_at"]
        if RESOURCES[1] in indexed
        else None,
        "retrievalCutoff": max(
            datetime.fromisoformat(c["completed_at"]) for c in indexed.values()
        ).isoformat()
        if indexed
        else None,
        "conclusion": (
            "The IPO prospectus resolves the tested earlier-Q1 and annual comparative "
            "selected-line matches. Unreviewed registration history still prevents a "
            "new eligible PIT batch."
        )
        if comparison
        else "Prospectus evidence unavailable; no earlier-Q1 comparison is established.",
        "nextStep": (
            "Pin review of the seven remaining registration/prospectus bodies in two "
            "governed groups of five and two, each with mandatory inventories. "
            "Reassess source scope if inventory changes."
            if comparison and registration_matches and len(missing) == 7
            else "Complete the pinned prospectus and fresh inventory review, then pin the "
            "exact remaining registration/prospectus bodies without inferring their contents."
        ),
        "cutoffNote": (
            "Inventory is observed at its own timestamp. Later retrieval does not "
            "extend public-event knowledge or repair September application knowledge."
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
            raise ValueError("Prospectus review differs from archive replay")
    else:
        target.write_text(encoded)
    print(json.dumps({"review": REPORT, "verified": args.check}))


if __name__ == "__main__":
    main()
