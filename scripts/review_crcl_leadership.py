"""D5f leadership exhibit and retained accounting evidence, with no publication."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.export_crcl_current import REVIEW_SHA as PRIOR_SHA
from scripts.normalize_crcl import ROOT
from scripts.review_crcl_current import REPORT as PRIOR_REPORT

ACQUISITION = "docs/research/crcl-leadership-acquisition-2026-10-13.json"
REPORT = "docs/research/crcl-leadership-review-2026-10-13.json"
KEY = "filing_document/0001876042/0001876042-26-000279/final_leadershiptransiti.htm"


def plan(root: Path = ROOT) -> list[dict[str, Any]]:
    raw = (root / PRIOR_REPORT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SHA:
        raise ValueError("Pinned D5e parent evidence changed")
    rows: list[dict[str, Any]] = json.loads(raw)["missingBodies"]
    if len(rows) != 1 or rows[0]["resourceKey"] != KEY:
        raise ValueError("D5f requires exactly the pinned leadership exhibit")
    return rows


def groups(rows: list[dict[str, Any]]) -> tuple[tuple[str, ...], ...]:
    if [row["resourceKey"] for row in rows] != [KEY]:
        raise ValueError("D5f source scope changed")
    return ((KEY,),)


BODY_SHA = "cce31d92421d6c66aada4c821edb2dcde8473c377a1eed908e748c0467372604"
QUOTES = [
    "To assist with a smooth transition, he will continue as Chief Financial Officer through "
    "the end of December 2026, unless a successor is appointed sooner.",
    "Having achieved many milestones, it is now the right time for me to step down and take "
    "a break before my next chapter.",
]
PROSPECTUS = "filing_document/0001876042/0001193125-25-135795/d737521d424b4.htm"


def retained_accounting(root: Path = ROOT) -> dict[str, Any]:
    from equity_ingest.archive import LocalArchive

    from scripts.export_crcl_safety import REVIEW_SHA as safety_sha
    from scripts.review_crcl_exhibits import clean
    from scripts.review_crcl_identity import normalized_text, read_audit, xml_root
    from scripts.review_crcl_safety import ACQUISITION as safety_acquisition
    from scripts.review_crcl_safety import REPORT as safety_report
    from scripts.review_crcl_safety import source_detail

    raw = (root / safety_report).read_bytes()
    if hashlib.sha256(raw).hexdigest() != safety_sha:
        raise ValueError("Prior accounting review changed")
    saved = json.loads(raw)
    acquired = (root / safety_acquisition).read_bytes()
    if hashlib.sha256(acquired).hexdigest() != saved["acquisitionSha256"]:
        raise ValueError("Prior accounting acquisition changed")
    captures = read_audit(root)["captures"] + [
        c for g in json.loads(acquired)["groups"] for c in g["captures"]
    ]
    expected = {
        r["resourceKey"]: r for r in saved["filings"] if r["form"] in {"10-K", "10-K/A", "10-Q"}
    }
    archive = LocalArchive(root / "var/raw")
    scanned = []
    for capture in captures:
        key = capture["source_object_key"]
        if key not in expected:
            continue
        if capture["body_sha256"] != expected[key]["bodySha256"]:
            raise ValueError("Retained periodic edition changed")
        doc: Any = xml_root(
            archive.read_blob(capture["blob_key"], capture["body_sha256"], capture["byte_count"])
        )
        text = clean(normalized_text(doc))
        contexts = {e.get("id"): e for e in doc.xpath('//*[local-name()="context"]')}
        observations = []
        for element in doc.xpath("//*[@contextRef]"):
            if element.get("name") not in ("us-gaap:Revenues", "us-gaap:OperatingIncomeLoss"):
                continue
            context = contexts[element.get("contextRef")]
            dates = [
                e.text
                for e in context.xpath('.//*[local-name()="startDate" or local-name()="endDate"]')
            ]
            if len(dates) != 2 or not dates[0].startswith("2025-"):
                continue
            if context.xpath('.//*[local-name()="explicitMember" or local-name()="typedMember"]'):
                continue
            observations.append(
                {
                    "concept": element.get("name"),
                    "start": dates[0],
                    "end": dates[1],
                    "contextRef": element.get("contextRef"),
                    "unitRef": element.get("unitRef"),
                    "scale": element.get("scale"),
                    "sign": element.get("sign"),
                    "literal": clean(normalized_text(element)),
                    "locator": doc.getroottree().getpath(element),
                    "entity": [e.text for e in context.xpath('.//*[local-name()="identifier"]')],
                }
            )
        passages = []
        offset = 0
        while (offset := text.lower().find("reclassif", offset)) >= 0:
            passages.append(
                {"offset": offset, "excerpt": text[max(0, offset - 180) : offset + 500]}
            )
            offset += len("reclassif")
        scanned.append(
            {
                "resourceKey": key,
                "sha256": capture["body_sha256"],
                "source": source_detail(capture, expected[key]["accession"]),
                "selected2025Contexts": observations,
                "reclassificationPassages": passages,
            }
        )
    if {row["resourceKey"] for row in scanned} != set(expected) or len(scanned) != 6:
        raise ValueError("Retained periodic review set is incomplete or duplicated")
    q1 = [
        row["resourceKey"]
        for row in scanned
        if any(
            r["start"] == "2025-01-01" and r["end"] == "2025-03-31"
            for r in row["selected2025Contexts"]
        )
    ]
    if q1 != ["filing_document/0001876042/0001876042-26-000150/crcl-20260331.htm"]:
        raise ValueError("Q1 evidence scope changed; new accounting review required")
    return {
        "status": "unconfirmed",
        "periodicBodiesScanned": len(scanned),
        "q1SourceKeys": q1,
        "bodies": scanned,
        "finding": "All six retained periodic/amendment bodies were searched for dimensionless "
        "FY2025 selected inline contexts and every reclassification passage. The Q1 pair occurs "
        "only in the 2026 comparative. The annual original pair and Q2/H1 prior matches remain "
        "corroborated. Preferred-stock equity conversion, reserve-fund tax allocations and "
        "liability maturity transfers do not establish unchanged Circle revenue/operating income. "
        "Generic prior-period wording does not identify selected-line effects. No actual "
        "FY2025 correction is inferred; the original current-year annual pair is not itself "
        "a restated comparative merely because that note exists.",
        "limit": "This exhausts the retained periodic set and saved release comparisons, not "
        "unretained registration/prospectus bodies. Earlier Q1 edition and complete affected-line "
        "scope remain unconfirmed; no arithmetic-derived Q1 or new annual amount is substituted.",
    }


def q1_facts_review(document: dict[str, Any]) -> dict[str, Any]:
    if str(document.get("cik", "")).zfill(10) != "0001876042":
        raise ValueError("Q1 Facts issuer changed")
    rows = []
    for concept in ("Revenues", "OperatingIncomeLoss"):
        units = document.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {})
        for unit, records in units.items():
            for index, record in enumerate(records):
                if record.get("start") == "2025-01-01" and record.get("end") == "2025-03-31":
                    rows.append(
                        {
                            "concept": concept,
                            "unit": unit,
                            "record": record,
                            "locator": f"facts.us-gaap.{concept}.units.{unit}[{index}]",
                        }
                    )
    later_only = (
        len(rows) == 2
        and {r["concept"] for r in rows} == {"Revenues", "OperatingIncomeLoss"}
        and all(
            r["unit"] == "USD"
            and all(
                r["record"].get(k) == v
                for k, v in {
                    "accn": "0001876042-26-000150",
                    "form": "10-Q",
                    "filed": "2026-05-11",
                }.items()
            )
            for r in rows
        )
    )
    return {
        "status": "later_comparative_only" if later_only else "edition_review_required",
        "rows": rows,
        "limit": "Facts are observations with filing attribution, not a substitute "
        "for an earlier primary body or selected-line accounting review.",
    }


FACTS_ROSTER = "docs/research/crcl-leadership-facts-roster-2026-10-13.json"
FACTS_ROSTER_SHA = "3cc5a99a40d8d4a475e236f4277d48eef79e762150cc8c580935d0fffbf1f20d"


def facts_vintages(root: Path, new_captures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from equity_ingest.archive import LocalArchive

    from scripts.normalize_crcl import RESOURCES
    from scripts.review_crcl_safety import source_detail

    raw = (root / FACTS_ROSTER).read_bytes()
    if hashlib.sha256(raw).hexdigest() != FACTS_ROSTER_SHA:
        raise ValueError("Retained Facts roster changed")
    all_captures = json.loads(raw)["captures"]
    # Partial replays cannot inherit a D5f capture that their acquisition does not contain.
    current_ids = {c["capture_id"] for c in new_captures}
    current_capture_id = "938f0ff1-1b08-4c66-9a93-596a6905567c"
    captures = [
        c
        for c in all_captures
        if c["capture_id"] != current_capture_id or current_capture_id in current_ids
    ]
    archive = LocalArchive(root / "var/raw")
    result = []
    for capture in captures:
        if capture["source_object_key"] != RESOURCES[0] or capture["http_status"] != 200:
            raise ValueError("Retained Facts roster contains a non-Facts response")
        body = archive.read_blob(capture["blob_key"], capture["body_sha256"], capture["byte_count"])
        result.append(
            {
                "captureId": capture["capture_id"],
                "sha256": capture["body_sha256"],
                "source": {**source_detail(capture), "label": "SEC Company Facts"},
                "observedStageStates": capture["observedStageStates"],
                **q1_facts_review(json.loads(body)),
            }
        )
    return result


def review_acquisition(acquisition: dict[str, Any] | None, root: Path = ROOT) -> dict[str, Any]:
    from datetime import datetime
    from uuid import UUID

    from equity_ingest.archive import LocalArchive
    from equity_ingest.sec_inventory import parse_submissions

    from scripts.normalize_crcl import CIK, CUTOFF, RESOURCES, resource_url
    from scripts.review_crcl_current import (
        annual_edition_check,
        candidate_decision,
        review_inventory,
    )
    from scripts.review_crcl_exhibits import checked_text, clean
    from scripts.review_crcl_safety import source_detail

    plan(root)
    prior = json.loads((root / PRIOR_REPORT).read_bytes())
    prior_acq_raw = (root / "docs/research/crcl-current-acquisition-2026-10-13.json").read_bytes()
    if hashlib.sha256(prior_acq_raw).hexdigest() != prior["acquisitionSha256"]:
        raise ValueError("D5e source lineage changed")
    archive = LocalArchive(root / "var/raw")
    old_captures = json.loads(prior_acq_raw)["groups"][0]["captures"]
    old_inventory = next(c for c in old_captures if c["source_object_key"] == RESOURCES[1])
    old_doc = json.loads(
        archive.read_blob(
            old_inventory["blob_key"], old_inventory["body_sha256"], old_inventory["byte_count"]
        )
    )
    recent = old_doc["filings"]["recent"]
    candidates = []
    for index, form in enumerate(recent["form"]):
        if form not in {"S-1", "S-1/A", "424B4", "424B3"}:
            continue
        accession = recent["accessionNumber"][index]
        key = f"filing_document/{CIK}/{accession}/{recent['primaryDocument'][index]}"
        candidates.append(
            {
                "resourceKey": key,
                "form": form,
                "filedDate": recent["filingDate"][index],
                "locator": f"filings.recent row {index}",
                "url": resource_url(key),
            }
        )
    if not any(row["resourceKey"] == PROSPECTUS for row in candidates):
        raise ValueError("Pinned prospectus inventory identity changed")
    groups_ = (acquisition or {}).get("groups", [])
    if len(groups_) > 1:
        raise ValueError("D5f escaped its single group")
    indexed, bodies, seen = {}, {}, set()
    for capture in [c for g in groups_ for c in g["captures"]]:
        key = capture["source_object_key"]
        stamp = datetime.fromisoformat(capture["completed_at"])
        if (
            key in seen
            or key not in {KEY, *RESOURCES[:2]}
            or stamp.utcoffset() is None
            or stamp <= datetime.fromisoformat(prior["retrievalCutoff"])
        ):
            raise ValueError("Unexpected, duplicate or backdated leadership capture")
        seen.add(key)
        body = archive.read_blob(capture["blob_key"], capture["body_sha256"], capture["byte_count"])
        if capture["http_status"] == 200:
            indexed[key], bodies[key] = capture, body
    event = {
        "status": "unavailable",
        "finding": "Exhibit body unavailable; no event clearance.",
        "capturedAt": None,
    }
    details = {}
    if KEY in indexed:
        text = checked_text(bodies[KEY], BODY_SHA, QUOTES)
        event = {
            "status": "reviewed",
            "capturedAt": indexed[KEY]["completed_at"],
            "finding": (
                "Entire release reviewed: CFO transition through December or "
                "earlier successor, "
                "successor search, management/CFO comments, corporate description and contact. "
                "No financial-statement correction, restatement or non-reliance declaration was "
                "identified in this body. It supplies no selected-line reconciliation; positive "
                "management statements and IPO commentary are not accounting assurance."
            ),
        }
        details["leadership"] = {
            "title": "CFO transition · full retained exhibit",
            "subtitle": "D5f · September 25, 2026 release; actual October retrieval",
            "sections": [
                {
                    "heading": "Evidence and limits",
                    "rows": [
                        {"label": "Finding", "value": event["finding"]},
                        *[
                            {"label": f"Normalized text offset {text.index(clean(q))}", "value": q}
                            for q in QUOTES
                        ],
                    ],
                }
            ],
            "sources": [source_detail(indexed[KEY], "0001876042-26-000279")],
        }
    accounting = retained_accounting(root)
    details["accounting"] = {
        "title": "Retained accounting evidence exhausted",
        "subtitle": "Selected contexts and every reclassification passage; no derived values",
        "sections": [
            {
                "heading": "Evidence and limits",
                "rows": [
                    {"label": "Finding", "value": accounting["finding"]},
                    {"label": "Limit", "value": accounting["limit"]},
                    *[
                        {
                            "label": r["resourceKey"],
                            "value": json.dumps(
                                {k: v for k, v in r.items() if k != "source"}, sort_keys=True
                            ),
                        }
                        for r in accounting["bodies"]
                    ],
                ],
            }
        ],
        "sources": [r["source"] for r in accounting["bodies"]],
    }
    details["prospectus"] = {
        "title": "Exact unretained earlier-edition candidate",
        "subtitle": "Retained D5e inventory metadata only; body content unconfirmed",
        "sections": [
            {
                "heading": "Evidence and limits",
                "rows": [
                    {"label": "Next bounded source candidate", "value": PROSPECTUS},
                    {
                        "label": "Limit",
                        "value": (
                            "The IPO 424B4 is identified by inventory metadata. "
                            "Its Q1 contents and sufficiency cannot be confirmed "
                            "before body review. No claim of a missing Q1 10-Q "
                            "is made."
                        ),
                    },
                    {
                        "label": "Registration/prospectus identities",
                        "value": json.dumps(candidates, sort_keys=True),
                    },
                ],
            }
        ],
        "sources": [source_detail(old_inventory)],
    }
    inventory = None
    if RESOURCES[1] in indexed:
        capture = indexed[RESOURCES[1]]
        doc = parse_submissions(
            bodies[RESOURCES[1]], expected_cik=CIK, capture_id=UUID(capture["capture_id"])
        )
        expected = []
        for r in prior["currentInventory"]["filings"]:
            # Match exact saved identities using the saved SEC document, never guess filenames.
            idx = recent["accessionNumber"].index(r["accession"])
            expected.append(
                {
                    **r,
                    "resourceKey": (
                        f"filing_document/{CIK}/{r['accession']}/{recent['primaryDocument'][idx]}"
                    ),
                }
            )
        inventory = {
            **review_inventory(doc, expected, datetime.fromisoformat(capture["completed_at"])),
            "source": source_detail(capture),
        }
    annual = []
    if RESOURCES[0] in indexed:
        facts = json.loads(bodies[RESOURCES[0]])
        if str(facts.get("cik", "")).zfill(10) != CIK:
            raise ValueError("Current Facts issuer changed")
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
        details["annual"] = {
            "title": "Fresh annual edition checks",
            "subtitle": "Exact retained Company Facts rows; no ratio",
            "sections": [
                {
                    "heading": "Evidence and limits",
                    "rows": [
                        {"label": r["concept"], "value": json.dumps(r, sort_keys=True)}
                        for r in annual
                    ],
                }
            ],
            "sources": [source_detail(indexed[RESOURCES[0]], "0001876042-26-000062")],
        }
    vintages = facts_vintages(root, list(indexed.values()))
    details["q1-facts"] = {
        "title": "Q1 Company Facts vintages",
        "subtitle": "All retained governed Facts captures; exact filing editions and locators",
        "sections": [
            {
                "heading": "Evidence and limits",
                "rows": [
                    {
                        "label": r["captureId"],
                        "value": json.dumps(
                            {k: v for k, v in r.items() if k != "source"}, sort_keys=True
                        ),
                    }
                    for r in vintages
                ],
            }
        ],
        "sources": [r["source"] for r in vintages],
    }
    complete = (
        len(indexed) == 3
        and (acquisition or {}).get("status") == "captured_pending_review"
        and (acquisition or {}).get("originalRowsPreserved") is True
    )
    candidate = candidate_decision(
        missing_bodies=[] if KEY in indexed else [KEY],
        accounting_complete=accounting["status"] == "confirmed"
        and len(annual) == 2
        and all(r["status"] == "matched" for r in annual),
        inventory_complete=inventory is not None and inventory["status"] == "matched_scoped_roster",
        acquisition_complete=complete,
    )
    return {
        "kind": "real-crcl-leadership-review",
        "reviewedOn": "2026-10-13",
        "proposalCommit": "f72a5ed",
        "priorReviewSha256": PRIOR_SHA,
        "event": event,
        "accounting": accounting,
        "q1FactsVintages": vintages,
        "factsRosterSha256": FACTS_ROSTER_SHA,
        "details": details,
        "annualEditionChecks": annual,
        "currentInventory": inventory,
        "candidateBatch": candidate,
        "inventoryObservedAt": indexed[RESOURCES[1]]["completed_at"]
        if RESOURCES[1] in indexed
        else None,
        "retrievalCutoff": max(
            datetime.fromisoformat(c["completed_at"]) for c in indexed.values()
        ).isoformat()
        if indexed
        else None,
        "historicalRetrievalCutoff": CUTOFF.isoformat(),
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "nextSource": PROSPECTUS,
        "nextSourceUrl": resource_url(PROSPECTUS),
        "conclusion": (
            "The named leadership exhibit is reviewed; selected-line accounting "
            "scope still blocks a new PIT batch."
        )
        if KEY in indexed
        else "Leadership evidence remains unavailable; no new PIT batch is eligible.",
        "cutoffNote": (
            "Fresh inventory describes its observation time only. Later body "
            "retrieval does not extend event coverage or repair September "
            "application knowledge."
        ),
        "nextStep": (
            "Pin a bounded review of the identified IPO prospectus and reconcile "
            "any actual earlier-Q1 selected lines. Its contents and sufficiency "
            "remain unconfirmed. Complete affected-line review before governed "
            "batch preparation; real S6 is separately gated."
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
            raise ValueError("Leadership review differs from archive replay")
    else:
        target.write_text(encoded)
    print(json.dumps({"review": REPORT, "verified": args.check}))


if __name__ == "__main__":
    main()
