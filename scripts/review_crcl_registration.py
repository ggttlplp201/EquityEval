"""D5h registration-history review from immutable governed archives."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.export_crcl_prospectus import REVIEW_SHA as PRIOR_SHA
from scripts.normalize_crcl import ROOT
from scripts.review_crcl_prospectus import REPORT as PRIOR_REPORT

ACQUISITION = "docs/research/crcl-registration-acquisition-2026-10-13.json"
REPORT = "docs/research/crcl-registration-review-2026-10-13.json"
KEYS = tuple(
    "filing_document/0001876042/" + path
    for path in (
        "0001193125-25-070481/d737521ds1.htm",
        "0001193125-25-084832/d737521ds1a.htm",
        "0001193125-25-121234/d737521ds1a.htm",
        "0001193125-25-126208/d737521ds1a.htm",
        "0001193125-25-132755/d737521ds1a.htm",
        "0001193125-25-178989/d839239ds1.htm",
        "0001193125-25-181916/d839239d424b4.htm",
    )
)


def plan(root: Path = ROOT) -> list[dict[str, Any]]:
    raw = (root / PRIOR_REPORT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SHA:
        raise ValueError("Pinned D5g registration evidence changed")
    rows = sorted(json.loads(raw)["missingBodies"], key=lambda row: row["filedDate"])
    if tuple(row["resourceKey"] for row in rows) != KEYS:
        raise ValueError("Registration identities differ from D046")
    return rows


def groups(rows: list[dict[str, Any]]) -> tuple[tuple[str, ...], ...]:
    if tuple(row["resourceKey"] for row in rows) != KEYS:
        raise ValueError("D5h scope changed")
    return KEYS[:5], KEYS[5:]


def acquisition_complete(report: dict[str, Any] | None) -> bool:
    from scripts.normalize_crcl import RESOURCES

    if not report or report.get("originalRowsPreserved") is not True:
        return False
    acquired = report.get("groups", [])
    if len(acquired) != 2:
        return False
    for group, keys in zip(acquired, (KEYS[:5], KEYS[5:]), strict=True):
        expected = set(keys) | set(RESOURCES[:2])
        captures = group["captures"]
        if (
            group["result"]["state"] != "completed"
            or group["result"]["gaps"]
            or set(group["bootstrap_plan"]["resources"]) != expected
            or len(captures) != len(expected)
            or {c["source_object_key"] for c in captures} != expected
            or any(c["http_status"] != 200 for c in captures)
        ):
            return False
    return report.get("errorType") is None


PROFILES = (
    ("a410eeeab7f1e80407ff9bf2c8d3da695d0ff9bf68c732e07c7ea1046b8af0e8", 511, None),
    ("6d99abb0839359e6a47a03e745439557477a794b3ecbb2e7f5bcc6e7866df160", 511, None),
    ("7486de20e1e492c08de70450bffdabdf387d27e6389a2662f2b7cc754fa30267", 562, 506),
    ("112ab81bfccef80a7511cc44f27edcea82ea14ddc802574bf635bf25fd71a9cf", 574, 518),
    ("464d61505397a33116ce3c5db356d61e0a97edd64162c5cef2a852c38be86d7f", 574, 518),
    ("3b2ab9c97730a8f9740ed8a085016199b6919a8344093a4f48ee1ef782a014d1", 588, 510),
    ("91736cd252643f70368f07de5da44354761ac128a1b42cb94b95f5c8272a479e", 583, 505),
)
H1_HEADER = (
    "Three Months EndedJune 30, Six Months EndedJune 30, "
    "(in thousands, except per share information) 2025 2024 2025 2024"
)
H1_VALUES = [
    ["658,078", "430,030", "1,236,651", "795,124"],
    ["(325,582)", "50,246", "(232,642)", "102,565"],
]
COMMON_QUOTES = (
    "Our reporting currency is the U.S. dollar",
    "These reclassifications have no impact on the consolidated financial statements.",
    "In our opinion, the financial statements present fairly, in all material respects,",
    "Accordingly, we express no such opinion.",
    "Effective February 13, 2023, Grant Thornton LLP",
    "there were no “reportable events”",
    "may result in a restatement of our annual or interim financial statements.",
)


def annual_rows(text: str) -> list[dict[str, Any]]:
    from scripts.review_crcl_exhibits import statement_rows
    from scripts.review_crcl_prospectus import ANNUAL_HEADER, ANNUAL_VALUES

    return statement_rows(
        text.replace(" )", ")"),
        ANNUAL_HEADER,
        [
            ("Total revenue and reserve income from continuing operations", ANNUAL_VALUES[0]),
            ("Operating income (loss) from continuing operations", ANNUAL_VALUES[1]),
        ],
    )


def review_body(key: str, body: bytes, capture: dict[str, Any]) -> dict[str, Any]:
    import re

    from lxml import html

    from scripts.review_crcl_exhibits import clean, statement_rows
    from scripts.review_crcl_identity import normalized_text
    from scripts.review_crcl_prospectus import check_q1_table
    from scripts.review_crcl_safety import source_detail

    index = KEYS.index(key)
    digest, annual_index, interim_index = PROFILES[index]
    if hashlib.sha256(body).hexdigest() != digest or capture["body_sha256"] != digest:
        raise ValueError("Registration body changed; new substantive review required")
    doc = html.fromstring(body, parser=html.HTMLParser(encoding="utf-8"))
    text = clean(normalized_text(doc))
    tables = list(doc.iter("table"))
    selected = []
    for table_index, kind in (
        (annual_index, "FY2024/FY2023/FY2022"),
        (interim_index, "Q1" if index < 5 else "Q2/H1"),
    ):
        if table_index is None:
            continue
        table = tables[table_index]
        table_text = clean(normalized_text(table)).replace(" )", ")")
        if kind.startswith("FY"):
            rows = annual_rows(table_text)
        elif kind == "Q1":
            rows = check_q1_table(table_text)
        else:
            rows = statement_rows(
                table_text,
                H1_HEADER,
                [
                    ("Total revenue and reserve income", H1_VALUES[0]),
                    ("Operating income (loss) from continuing operations", H1_VALUES[1]),
                ],
            )
        selected.append(
            {
                "periods": kind,
                "rows": rows,
                "unit": "USD",
                "scale": 3,
                "entity": "Circle Internet Group, Inc. and subsidiaries; consolidated",
                "locator": doc.getroottree().getpath(table),
            }
        )
    quotes = list(COMMON_QUOTES)
    if index < 2:
        quotes.append(
            "Our unaudited condensed consolidated financial statements as of and for "
            "the three months ended March 31, 2025 are not yet available"
        )
    elif index < 5:
        quotes.append(
            "These reclassifications have no impact on the unaudited condensed "
            "consolidated financial statements."
        )
    else:
        quotes.append(
            "had no impact on previously reported total assets, total liabilities and net income."
        )
    if any(q not in text for q in quotes):
        raise ValueError("Reviewed accounting/basis passage changed")
    pattern = (
        r"restat|reclassif|non.reliance|material weakness|disagreements|correction of|corrected"
    )
    passages = [
        {"offset": m.start(), "text": text[max(0, m.start() - 250) : m.start() + 850]}
        for m in re.finditer(pattern, text, re.I)
    ]
    return {
        "resourceKey": key,
        "status": "reviewed",
        "source": source_detail(capture, key.split("/")[2]),
        "fullTextCharactersScanned": len(text),
        "selectedStatements": selected,
        "passages": passages,
        "quotes": [{"quote": q, "offset": text.index(q)} for q in quotes],
        "q1Status": "preliminary_blank_not_reported"
        if index < 2
        else "reported_pair_matches"
        if index < 5
        else "not_separately_present_no_derivation",
        "fy2025AnnualStatus": "not_present_in_this_2025_registration",
        "finding": "Reported selected annual operands match the retained IPO and later annual "
        "comparatives. Available reported interim operands match retained periodic "
        "editions. No selected-line correction or non-reliance declaration was "
        "identified in the reviewed full-body accounting and correction disclosures.",
        "limit": "Conditional restatement/control risks and clawback policy are not actual "
        "corrections. Certificate/MOU restatements, share conversions and fund tax "
        "reclassifications have distinct scopes. Generic immaterial reclassification "
        "wording alone does not prove unchanged revenue or operating income; exact "
        "statement comparisons supply the selected-line evidence. Auditor opinions "
        "cover financial statements, not internal-control assurance. The referenced "
        "2023 former-auditor letter is not treated as reviewed assurance.",
    }


PRIOR_ACQUISITIONS = (
    "docs/research/crcl-safety-acquisition-2026-10-12.json",
    "docs/research/crcl-exhibit-acquisition-2026-10-13.json",
    "docs/research/crcl-current-acquisition-2026-10-13.json",
    "docs/research/crcl-leadership-acquisition-2026-10-13.json",
    "docs/research/crcl-prospectus-acquisition-2026-10-13.json",
)


def retained_captures(root: Path = ROOT) -> list[dict[str, Any]]:
    from scripts.review_crcl_identity import read_audit
    from scripts.review_crcl_leadership import FACTS_ROSTER

    rows = list(read_audit(root)["captures"])
    rows += json.loads((root / FACTS_ROSTER).read_bytes())["captures"]
    for path in (*PRIOR_ACQUISITIONS, ACQUISITION):
        if (root / path).exists():
            rows += [
                c for g in json.loads((root / path).read_bytes())["groups"] for c in g["captures"]
            ]
    return list({r["capture_id"]: r for r in rows}.values())


def periodic_comparisons(captures: list[dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    from equity_ingest.archive import LocalArchive

    from scripts.review_crcl_exhibits import periodic_evidence
    from scripts.review_crcl_prospectus import ANNUAL_VALUES, Q1_VALUES

    comparisons = []
    for accession, periods, values in (
        (
            "0001876042-26-000062",
            [(0, "2024-01-01", "2024-12-31"), (1, "2023-01-01", "2023-12-31")],
            ANNUAL_VALUES,
        ),
        ("0001876042-26-000150", [(0, "2025-01-01", "2025-03-31")], Q1_VALUES),
        (
            "0001628280-25-039781",
            [
                (0, "2025-04-01", "2025-06-30"),
                (1, "2024-04-01", "2024-06-30"),
                (2, "2025-01-01", "2025-06-30"),
                (3, "2024-01-01", "2024-06-30"),
            ],
            H1_VALUES,
        ),
        (
            "0001876042-26-000248",
            [(0, "2025-04-01", "2025-06-30"), (2, "2025-01-01", "2025-06-30")],
            H1_VALUES,
        ),
    ):
        c = next(c for c in captures if f"/{accession}/" in c["source_object_key"])
        body = LocalArchive(root / "var/raw").read_blob(
            c["blob_key"], c["body_sha256"], c["byte_count"]
        )
        comparisons += periodic_evidence(c, body, periods, values)
    return comparisons


def time_scope(observed: str | None, retrieved: str | None) -> dict[str, Any]:
    from datetime import datetime

    covered = False
    if observed and retrieved:
        observation, cutoff = datetime.fromisoformat(observed), datetime.fromisoformat(retrieved)
        if observation.utcoffset() is None or cutoff.utcoffset() is None:
            raise ValueError("Explicit observation and retrieval timezones required")
        covered = observation >= cutoff
    return {
        "state": "observation_covers_retained_evidence" if covered else "blocked",
        "inventoryObservedAt": observed,
        "evidenceRetrievalCutoff": retrieved,
        "fullDayCoverage": False,
        "interpretation": "Retrospective filing-date comparison bounded by the exact inventory "
        "observation. Date equality does not establish intraday or full-day event coverage.",
        "requirement": "Before a new S3 batch, separately pin and retain the mandatory pair "
        "company_facts/0001876042 and submissions/0001876042, both captured after all "
        "retained bodies. Review any changed inventory and pin that exact observation "
        "as the preparation bound. "
        "The existing date-level Completeness field alone cannot clear a later retrieval gap.",
    }


def review_acquisition(acquisition: dict[str, Any] | None, root: Path = ROOT) -> dict[str, Any]:
    from datetime import datetime
    from uuid import UUID

    from equity_ingest.archive import LocalArchive
    from equity_ingest.sec_inventory import parse_submissions

    from scripts.normalize_crcl import CIK, CUTOFF, RESOURCES
    from scripts.review_crcl_current import annual_edition_check, review_inventory
    from scripts.review_crcl_leadership import q1_facts_review
    from scripts.review_crcl_prospectus import registration_roster
    from scripts.review_crcl_prospectus import review as prior_review
    from scripts.review_crcl_safety import source_detail

    planned = plan(root)
    prior = prior_review(root)
    if (
        hashlib.sha256((json.dumps(prior, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        != PRIOR_SHA
    ):
        raise ValueError("D5g retained replay changed")
    acquired = (acquisition or {}).get("groups", [])
    if len(acquired) > 2:
        raise ValueError("D5h group scope expanded")
    bodies, indexed, inventories, facts = {}, {}, [], []
    seen = set()
    archive = LocalArchive(root / "var/raw")
    old_acq = json.loads((root / PRIOR_ACQUISITIONS[-1]).read_bytes())
    old_inventory = next(
        c for c in old_acq["groups"][0]["captures"] if c["source_object_key"] == RESOURCES[1]
    )
    old_doc = json.loads(
        archive.read_blob(
            old_inventory["blob_key"], old_inventory["body_sha256"], old_inventory["byte_count"]
        )
    )
    recent = old_doc["filings"]["recent"]
    expected = []
    for row in prior["currentInventory"]["filings"]:
        i = recent["accessionNumber"].index(row["accession"])
        expected.append(
            {
                **row,
                "resourceKey": f"filing_document/{CIK}/{row['accession']}/"
                f"{recent['primaryDocument'][i]}",
            }
        )
    for number, group in enumerate(acquired):
        allowed = set(groups(planned)[number]) | set(RESOURCES[:2])
        local_keys = set()
        for c in group["captures"]:
            key = c["source_object_key"]
            stamp = datetime.fromisoformat(c["completed_at"])
            if (
                key not in allowed
                or key in local_keys
                or c["capture_id"] in seen
                or stamp.utcoffset() is None
                or stamp <= datetime.fromisoformat(prior["retrievalCutoff"])
            ):
                raise ValueError("Unexpected, duplicate or backdated registration capture")
            local_keys.add(key)
            seen.add(c["capture_id"])
            body = archive.read_blob(c["blob_key"], c["body_sha256"], c["byte_count"])
            if c["http_status"] != 200:
                continue
            indexed[c["capture_id"]] = c
            if key in KEYS:
                bodies[key] = review_body(key, body, c)
            elif key == RESOURCES[0]:
                doc = json.loads(body)
                q1 = q1_facts_review(doc)
                annual = []
                for concept, value in (
                    ("Revenues", "2746642000"),
                    ("OperatingIncomeLoss", "-96435000"),
                ):
                    records = [
                        r
                        for r in doc.get("facts", {})
                        .get("us-gaap", {})
                        .get(concept, {})
                        .get("units", {})
                        .get("USD", [])
                        if r.get("start") == "2025-01-01" and r.get("end") == "2025-12-31"
                    ]
                    annual.append({"concept": concept, **annual_edition_check(records, value)})
                facts.append(
                    {
                        "captureId": c["capture_id"],
                        "sha256": c["body_sha256"],
                        "source": {**source_detail(c), "label": "SEC Company Facts"},
                        **q1,
                        "annualEditionChecks": annual,
                    }
                )
            else:
                doc = json.loads(body)
                inventory = review_inventory(
                    parse_submissions(body, expected_cik=CIK, capture_id=UUID(c["capture_id"])),
                    expected,
                    stamp,
                )
                roster = registration_roster(doc)
                same = [(r["resourceKey"], r["form"], r["filedDate"]) for r in roster] == [
                    (r["resourceKey"], r["form"], r["filedDate"])
                    for r in prior["registrationRoster"]
                ]
                inventories.append(
                    {
                        **inventory,
                        "source": source_detail(c),
                        "registrationRosterMatches": same,
                        "registrationRoster": roster,
                    }
                )
    comparisons = periodic_comparisons(retained_captures(root), root) if bodies else []
    vintages = [*prior["q1FactsVintages"], *facts]
    facts_match = (
        len(facts) == 2
        and all(
            v["status"] == "later_comparative_only"
            and all(
                r["record"]["val"]
                == {"Revenues": 578573000, "OperatingIncomeLoss": 92940000}[r["concept"]]
                for r in v["rows"]
            )
            for v in vintages
        )
        and all(r["status"] == "matched" for v in facts for r in v["annualEditionChecks"])
    )
    inventory_match = len(inventories) == 2 and all(
        i["status"] == "matched_scoped_roster" and i["registrationRosterMatches"]
        for i in inventories
    )
    observed = inventories[-1]["source"]["capturedAt"] if inventories else None
    retrieved = (
        max(datetime.fromisoformat(c["completed_at"]) for c in indexed.values()).isoformat()
        if indexed
        else None
    )
    timing = time_scope(observed, retrieved)
    reasons = []
    if timing["state"] != "observation_covers_retained_evidence":
        reasons.append("inventory_observation_precedes_evidence_cutoff")
    if len(bodies) != 7:
        reasons.append("registration_body_unreviewed")
    if not inventory_match:
        reasons.append("current_inventory_incomplete")
    if not facts_match:
        reasons.append("facts_edition_unconfirmed")
    if not acquisition_complete(acquisition):
        reasons.append("acquisition_or_preservation_incomplete")
    details = {}
    for row in planned:
        key = row["resourceKey"]
        if key not in bodies:
            continue
        item = bodies[key]
        details[row["accession"]] = {
            "title": f"{row['form']} · {row['filedDate']} · {row['accession']}",
            "subtitle": "Retained body; reported statements and accounting disclosures",
            "sections": [
                {
                    "heading": "Evidence and limits",
                    "rows": [
                        {"label": "Finding", "value": item["finding"]},
                        {"label": "Limit", "value": item["limit"]},
                        {
                            "label": "Statements",
                            "value": json.dumps(item["selectedStatements"], sort_keys=True),
                        },
                        {
                            "label": "Basis/auditor/control quotes",
                            "value": json.dumps(item["quotes"], sort_keys=True),
                        },
                        {
                            "label": "All matched accounting/correction passages",
                            "value": json.dumps(item["passages"], sort_keys=True),
                        },
                    ],
                }
            ],
            "sources": [item["source"]],
        }
    details["comparisons"] = {
        "title": "Registration statements and retained periodic history",
        "subtitle": "Exact selected operands; earlier checkpoint evidence remains pinned",
        "sections": [
            {
                "heading": "Evidence and limits",
                "rows": [
                    {
                        "label": "Exact periodic contexts",
                        "value": json.dumps(comparisons, sort_keys=True),
                    },
                    {"label": "Facts vintages", "value": json.dumps(vintages, sort_keys=True)},
                    {
                        "label": "Scope",
                        "value": "FY2025 revenue and operating income, with selected "
                        "FY2024/FY2023 and 2025 interim edition reconciliation. This is not "
                        "certification "
                        "of every accounting line, every SEC form or every external "
                        "assurance report.",
                    },
                ],
            }
        ],
        "sources": [v["source"] for v in vintages]
        + [
            {
                **source_detail(c, c["source_object_key"].split("/")[2]),
                "captureId": c["capture_id"],
                "sha256": c["body_sha256"],
            }
            for c in retained_captures(root)
            if c["capture_id"] in {r["captureId"] for r in comparisons}
        ],
    }
    return {
        "kind": "real-crcl-registration-review",
        "proposalCommit": "01348a5",
        "reviewedOn": "2026-10-13",
        "priorReviewSha256": PRIOR_SHA,
        "documents": [
            {**r, **bodies.get(r["resourceKey"], {"status": "unavailable"})} for r in planned
        ],
        "periodicComparisons": comparisons,
        "q1FactsVintages": vintages,
        "factsMatch": facts_match,
        "inventories": inventories,
        "sourceHistoryScope": "Selected FY2025 consolidated income lines: retained annual, "
        "quarterly, amendment, current-event/exhibit and public registration/prospectus history.",
        "acquisitionAssessment": {
            "originalSummary": (acquisition or {}).get("status"),
            "verifiedGroupsComplete": acquisition_complete(acquisition),
            "note": "The immutable acquisition summary used a one-group count and says incomplete. "
            "Two typed completed groups, exact resources, successful captures and preservation "
            "are assessed independently; no source was retried or audit overwritten."
            if acquisition_complete(acquisition)
            and (acquisition or {}).get("status") == "incomplete"
            else "Incomplete or unavailable acquisition cannot prove source completeness.",
        },
        "timeScope": timing,
        "candidateBatch": {
            "status": "blocked" if reasons else "ready_for_s3_preparation",
            "batchId": None,
            "reasonCodes": reasons,
            "explanation": "All checked evidence gates pass for narrow S3 preparation; "
            "publication still requires pinned preparation and existing publisher checks."
            if not reasons
            else "Incomplete evidence cannot authorize a new PIT batch.",
        },
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "historicalRetrievalCutoff": CUTOFF.isoformat(),
        "inventoryObservedAt": inventories[-1]["source"]["capturedAt"] if inventories else None,
        "retrievalCutoff": max(
            datetime.fromisoformat(c["completed_at"]) for c in indexed.values()
        ).isoformat()
        if indexed
        else None,
        "cutoffNote": "Inventory observation and final retrieval are distinct. October review "
        "does not repair September application knowledge or assert later event coverage.",
        "conclusion": "The seven registration bodies and tested statement editions are reviewed. "
        "Narrow source/history/accounting evidence supports S3 preparation; "
        "no S6 metric is published."
        if not reasons
        else "The reported registration operands are reconciled, but source-history eligibility "
        "remains incomplete at the final evidence cutoff; no new batch or metric is eligible."
        if len(bodies) == 7 and facts_match and inventory_match
        else "Registration review remains incomplete; no batch or metric is eligible.",
        "nextStep": timing["requirement"],
        "details": details,
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
            raise ValueError("Registration review differs from archive replay")
    else:
        target.write_text(encoded)
    print(json.dumps({"review": REPORT, "verified": args.check}))


if __name__ == "__main__":
    main()
