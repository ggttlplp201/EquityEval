"""D5c bounded archived safety review; no eligibility override or financial math."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from equity_core.assessment import SUPPORTED_METRICS, MetricApplicability, ProfilePolicy
from equity_ingest.archive import LocalArchive
from equity_ingest.sec_inventory import SubmissionDocument, assemble_inventory, parse_submissions

from scripts.export_crcl_analysis_readiness import generated as readiness_generated
from scripts.normalize_crcl import CIK, CUTOFF, RESOURCES, ROOT, prepare, resource_url
from scripts.publish_crcl_normalization import INPUT_HASH, OUTPUT_HASH
from scripts.review_crcl_identity import normalized_text, read_audit, xml_root

REPORT = "docs/research/crcl-safety-review-2026-10-12.json"
ACQUISITION = "docs/research/crcl-safety-acquisition-2026-10-12.json"
START = date(2025, 1, 1)
FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A", "NT 10-K", "NT 10-Q"})
QUOTES = {
    "reserve_income": (
        "our revenue is primarily driven by reserve income earned on the assets "
        "backing such stablecoins"
    ),
    "distribution": (
        "The Collaboration Agreement is accounted for as an executory contract and "
        "reflected in distribution and transaction costs in our Consolidated "
        "Statements of Operations."
    ),
    "holder_reserves": (
        "requirements to hold reserve assets for the benefit of stablecoin holders "
        "and prohibitions on lending, pledging, rehypothecating, or otherwise "
        "encumbering those reserves"
    ),
    "ipo_expense": "stock-based compensation related to vesting conditions met by our IPO",
    "amendment": (
        "Except as described above, this Amendment does not amend, update, or "
        "restate any other information or disclosure included in the Original Form "
        "10-K"
    ),
}


# Human content-review dispositions, replay-bound to the retained body and marker.
PRIMARY_REVIEWS = {
    "0001876042-26-000159": (
        "Submission of Matters",
        "Stockholder votes and auditor appointment ratification; primary text reviewed.",
    ),
    "0001876042-26-000192": (
        "Departure of Director",
        "Director resignation and replacement lead director; primary text reviewed.",
    ),
    "0001876042-26-000205": (
        "Token Purchase Agreement",
        "Additional token presale closing and repayment terms; primary text reviewed.",
    ),
    "0001876042-26-000246": (
        "Results of Operations",
        "Quarterly earnings furnished by reference; financial press-release exhibit still missing.",
    ),
    "0001876042-26-000267": (
        "Share Purchase Agreement",
        (
            "Proposed Tazapay acquisition and securities terms; agreement and "
            "announcement exhibits still missing."
        ),
    ),
    "0001876042-26-000032": (
        "Results of Operations",
        "Annual earnings furnished by reference; financial press-release exhibit still missing.",
    ),
    "0001876042-26-000078": (
        "Kirk Koenigsbauer",
        "Director appointment; announcement exhibit still missing.",
    ),
    "0001876042-26-000148": (
        "Token Purchase Agreement",
        (
            "Quarterly earnings and token presale terms; financial press-release "
            "exhibit still missing."
        ),
    ),
    "0001628280-25-039749": (
        "Results of Operations",
        "Quarterly earnings furnished by reference; financial press-release exhibit still missing.",
    ),
    "0001876042-25-000004": (
        "Adam Selipsky",
        "Director appointment; announcement exhibit still missing.",
    ),
    "0001876042-25-000014": ("David Orfao", "Director resignation; primary text reviewed."),
    "0001876042-25-000045": (
        "Results of Operations",
        "Quarterly earnings furnished by reference; financial press-release exhibit still missing.",
    ),
    "0000950103-25-007107": (
        "Material Modification to Rights",
        "IPO completion and governing documents; linked governing-document exhibits still missing.",
    ),
}


def within_historical_cutoff(completed_at: str) -> bool:
    stamp = datetime.fromisoformat(completed_at)
    if stamp.utcoffset() is None:
        raise ValueError("Capture completion requires an actual timezone")
    return stamp <= CUTOFF


def scope_inventory(
    document: SubmissionDocument, captured: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    inventory = assemble_inventory(document, (), boundary_start=START, boundary_end=CUTOFF.date())
    if inventory.flags or inventory.missing_documents or inventory.completeness != "complete":
        raise ValueError("Advertised Submissions history is incomplete or ambiguous")
    rows = []
    for item in sorted(inventory.filings, key=lambda row: (row.filed_date, row.accession)):
        if item.form not in FORMS:
            continue
        if not item.primary_document or item.acceptance_at is None:
            raise ValueError("Scoped filing needs primary document and aware acceptance time")
        raw = json.loads(item.raw_metadata)
        capture = captured.get(item.accession)
        historical = bool(capture and within_historical_cutoff(capture["completed_at"]))
        key = f"filing_document/{CIK}/{item.accession}/{item.primary_document}"
        rows.append(
            {
                "accession": item.accession,
                "form": item.form,
                "filedDate": str(item.filed_date),
                "acceptedAt": item.acceptance_at.isoformat(),
                "reportPeriodEnd": str(item.report_period_end) if item.report_period_end else None,
                "items": raw.get("items", ""),
                "resourceKey": key,
                "url": resource_url(key),
                "metadataCaptureId": str(item.source_capture_id),
                "metadataLocator": item.source_locator,
                "bodyStatus": "retained_at_cutoff"
                if historical
                else "retrospective_only"
                if capture
                else "missing",
                "availableAtHistoricalCutoff": historical,
                "captureId": capture["capture_id"] if capture else None,
                "completedAt": capture["completed_at"] if capture else None,
                "eventReview": "not_reviewed",
            }
        )
    return rows


def capture_groups(rows: list[dict[str, Any]]) -> tuple[tuple[str, ...], ...]:
    keys = [row["resourceKey"] for row in reversed(rows) if row["bodyStatus"] == "missing"]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate acquisition resource")
    return tuple(tuple(keys[index : index + 5]) for index in range(0, len(keys), 5))


def acquisition_blockers(
    rows: list[dict[str, Any]], acquisition: dict[str, Any] | None
) -> list[str]:
    codes = []
    if any(row["bodyStatus"] == "missing" for row in rows):
        codes.append("missing_primary_bodies")
    if (
        acquisition is None
        or len(acquisition["groups"]) != 4
        or acquisition.get("status") != "captured_pending_review"
    ):
        codes.append("acquisition_incomplete")
    if acquisition is None or acquisition.get("originalRowsPreserved") is not True:
        codes.append("application_preservation_unverified")
    return codes


def business_profile(issuer_id: UUID) -> ProfilePolicy:
    return ProfilePolicy(
        issuer_id=issuer_id,
        business_model="Stablecoin issuer with reserve-income and distribution economics",
        lifecycle="Listed issuer; reported FY2025 includes IPO-related compensation expense",
        instrument_basis=(
            "Consolidated issuer operations; not token-holder reserves or per-share value"
        ),
        revision="d5c-crcl-reported-operating-margin-v1",
        effective_on=date(2026, 10, 12),
        known_on=date(2026, 10, 12),
        evidence_refs=(RESOURCES[2], RESOURCES[3], "docs/design/d5c/proposal.md"),
        rules=tuple(
            MetricApplicability(
                metric,
                True if metric == "operating_margin" else None,
                (
                    "Descriptive reported operating result divided by total revenue including "
                    "reserve income; no generic technology thresholds or recurring-profit "
                    "inference."
                )
                if metric == "operating_margin"
                else (
                    "Deferred: requires its own accounting operands, scope and "
                    "business-applicability review."
                ),
            )
            for metric in SUPPORTED_METRICS
        ),
    )


def source_detail(capture: dict[str, Any], accession: str | None = None) -> dict[str, Any]:
    return {
        "label": "SEC / Circle retained filing"
        if accession
        else "SEC retained Submissions inventory",
        "url": capture["request_url"],
        "accession": accession,
        "capturedAt": capture["completed_at"],
        "transform": f"Verified entity bytes SHA256 {capture['body_sha256']}; exact source replay",
        "licence": "SEC public filings and government-created data reuse",
    }


def review(root: Path = ROOT) -> dict[str, Any]:
    audit = read_audit(root)
    archive = LocalArchive(root / "var/raw")
    bundle, _ = prepare(audit, archive)
    if bundle.input_manifest_hash != INPUT_HASH or bundle.output_manifest_hash != OUTPUT_HASH:
        raise ValueError("D5a preparation changed")
    captures = {row["source_object_key"]: row for row in audit["captures"]}
    bodies = {
        key: archive.read_blob(row["blob_key"], row["body_sha256"], row["byte_count"])
        for key, row in captures.items()
    }
    inventory_capture = captures[RESOURCES[1]]
    inventory = parse_submissions(
        bodies[RESOURCES[1]], expected_cik=CIK, capture_id=UUID(inventory_capture["capture_id"])
    )
    original_captures = {
        key.split("/")[2]: row
        for key, row in captures.items()
        if key.startswith("filing_document/")
    }
    historical_rows = scope_inventory(inventory, original_captures)
    if (
        len(historical_rows) != 19
        or sum(row["availableAtHistoricalCutoff"] for row in historical_rows) != 3
    ):
        raise ValueError("Pinned D5c filing roster changed")
    acquisition = None
    acquisition_hash = None
    if (root / ACQUISITION).exists():
        raw = (root / ACQUISITION).read_bytes()
        acquisition_hash = hashlib.sha256(raw).hexdigest()
        acquisition = json.loads(raw)
        for group in acquisition["groups"]:
            for capture in group.get("captures", []):
                archive.read_blob(
                    capture["blob_key"], capture["body_sha256"], capture["byte_count"]
                )
                if capture["http_status"] == 200 and capture["source_object_key"].startswith(
                    "filing_document/"
                ):
                    key = capture["source_object_key"]
                    if key not in {row["resourceKey"] for row in historical_rows}:
                        raise ValueError("Acquisition escaped pinned filing roster")
                    if within_historical_cutoff(capture["completed_at"]):
                        raise ValueError("New acquisition must not be backdated")
                    original_captures[key.split("/")[2]] = capture
    rows = scope_inventory(inventory, original_captures)
    missing_exhibits = []
    fresh_inventory = None
    if acquisition is not None:
        if len(acquisition["groups"]) > 4:
            raise ValueError("D5c acquisition escaped its bounded groups")
        fresh_captures = [
            capture
            for group in acquisition["groups"]
            for capture in group["captures"]
            if capture["source_object_key"] == RESOURCES[1]
        ]
        if fresh_captures:
            if len({capture["body_sha256"] for capture in fresh_captures}) != 1:
                raise ValueError("Fresh inventory changed during acquisition; review each vintage")
            fresh = max(
                fresh_captures, key=lambda capture: datetime.fromisoformat(capture["completed_at"])
            )
            fresh_document = parse_submissions(
                archive.read_blob(fresh["blob_key"], fresh["body_sha256"], fresh["byte_count"]),
                expected_cik=CIK,
                capture_id=UUID(fresh["capture_id"]),
            )
            fresh_scoped = scope_inventory(fresh_document, original_captures)
            if [
                (r["accession"], r["filedDate"], r["form"], r["resourceKey"]) for r in fresh_scoped
            ] != [(r["accession"], r["filedDate"], r["form"], r["resourceKey"]) for r in rows]:
                raise ValueError("Fresh inventory disagrees with the historical filing roster")
            fresh_inventory = {
                "source": source_detail(fresh),
                "sha256": fresh["body_sha256"],
                "sameHistoricalRoster": True,
                "outsidePinnedWindow": [
                    {
                        "accession": item.accession,
                        "form": item.form,
                        "filedDate": str(item.filed_date),
                        "url": resource_url(
                            f"filing_document/{CIK}/{item.accession}/{item.primary_document}"
                        ),
                    }
                    for item in fresh_document.filings
                    if item.form in FORMS and item.filed_date > CUTOFF.date()
                ],
            }
    reclassifications: list[dict[str, Any]] = []
    for row in rows:
        capture = original_captures.get(row["accession"])
        row["reviewSummary"] = (
            "Periodic statement and correction review remains incomplete; original "
            "annual pair and amendment have their own bounded checks below."
        )
        row["bodySha256"] = capture["body_sha256"] if capture else None
        if capture is None:
            continue
        doc = xml_root(
            archive.read_blob(capture["blob_key"], capture["body_sha256"], capture["byte_count"])
        )
        text = normalized_text(doc)
        if row["form"] in {"10-K", "10-Q"}:
            start = text.index("Certain prior period amounts have been reclassified")
            end = text.index("total assets, total liabilities and net income.", start)
            quote = text[start : end + len("total assets, total liabilities and net income.")]
            if len(quote) > 600:
                raise ValueError("Reclassification disclosure changed")
            reclassifications.append(
                {
                    "quote": quote,
                    "locator": f"normalized XML itertext character offset {start}",
                    "source": source_detail(capture, row["accession"]),
                }
            )
            row["reviewSummary"] = (
                "Basis, controls and reclassification disclosures reviewed. The stated "
                "unchanged totals are assets, liabilities and net income; the impact on "
                "selected revenue/operating-income operands remains unresolved. No "
                "restatement or changed operand is inferred from this disclosure alone."
            )
        if row["accession"] not in PRIMARY_REVIEWS:
            continue
        marker, summary = PRIMARY_REVIEWS[row["accession"]]
        if marker not in text:
            raise ValueError("Reviewed event content changed")
        row["eventReview"] = "primary_only_reviewed"
        row["reviewSummary"] = summary + (
            " No non-reliance or correction was identified in this primary text; this "
            "does not clear exhibit or full-history review."
        )
        for node in doc.iter():
            if not isinstance(node.tag, str) or not node.tag.endswith("}a") or not node.get("href"):
                continue
            label = normalized_text(node)
            if not any(
                term in label.lower()
                for term in (
                    "press release",
                    "share purchase",
                    "certificate of incorporation",
                    "bylaws",
                )
            ):
                continue
            href = node.get("href")
            if not href or "/" in href or ".." in href:
                raise ValueError("Exhibit link needs explicit resource review")
            missing_exhibits.append(
                {
                    "accession": row["accession"],
                    "label": label,
                    "resourceKey": f"filing_document/{CIK}/{row['accession']}/{href}",
                    "url": resource_url(f"filing_document/{CIK}/{row['accession']}/{href}"),
                    "discoveredInCaptureId": capture["capture_id"],
                    "status": "not_retained_or_reviewed",
                }
            )
    texts = {key: normalized_text(xml_root(bodies[key])) for key in RESOURCES[2:4]}
    quote_evidence = []
    for identifier, quote in QUOTES.items():
        key = RESOURCES[3] if identifier == "amendment" else RESOURCES[2]
        text = texts[key]
        if text.count(quote) != 1:
            raise ValueError(f"Reviewed primary-source statement changed: {identifier}")
        quote_evidence.append(
            {
                "id": identifier,
                "quote": quote,
                "captureId": captures[key]["capture_id"],
                "locator": f"normalized XML itertext character offset {text.index(quote)}",
                "source": source_detail(captures[key], key.split("/")[2]),
            }
        )
    blockers = acquisition_blockers(rows, acquisition)
    details: dict[str, Any] = {}
    checks = []
    definitions = (
        (
            "pair",
            "Annual operand consistency",
            "passed",
            (
                "D5a replay reproduces the exact input/output hashes. Both selected facts "
                "match the original consolidated annual context, USD, signed value, scale "
                "and decimals. Company Facts precision remains unknown; original-filing "
                "precision is separate evidence."
            ),
        ),
        (
            "amendment",
            "Annual amendment meaning",
            "passed",
            (
                "The explanatory note adds separate Circle Reserve Fund statements and "
                "expressly does not restate other annual disclosures. This checks that "
                "amendment only; it does not prove no other correction exists."
            ),
        ),
        (
            "inventory",
            "Advertised filing inventory",
            "passed",
            (
                "The retained Submissions document has no advertised older files. All "
                "scoped periodic, amendment, event and late-filing forms in the requested "
                "window are enumerated. Inventory metadata is not a substantive event "
                "review."
            ),
        ),
        (
            "history",
            "Historical application knowledge",
            "blocked",
            (
                "Only three scoped filing bodies were retained by the September retrieval "
                "cutoff. Later downloads cannot clear that historical gap, and the October "
                "profile was not known at that cutoff."
            ),
        ),
        (
            "events",
            "Retrospective financial/event review",
            "incomplete",
            (
                (
                    "All scoped primary bodies are now retained, and event primary text was "
                    if not blockers
                    else (
                        "Primary-body acquisition is incomplete or unverified; "
                        "available event text was "
                    )
                )
                + "reviewed. Referenced exhibits and reconciliation of periodic reclassifications "
                "remain outstanding. No complete absence-of-restatement conclusion "
                "is made."
            ),
        ),
        (
            "reclassifications",
            "Prior-period reclassification scope",
            "blocked",
            (
                (
                    (
                        f"{len(reclassifications)} retained periodic filings disclose "
                        "immaterial prior-period reclassifications "
                    )
                    if blockers
                    else "Five periodic filings disclose immaterial prior-period reclassifications "
                )
                + "and unchanged total assets, total liabilities and net income. This does "
                "not explicitly establish unchanged revenue or operating income. Reconcile "
                "the affected lines and editions before clearing the selected operands; "
                "no actual change or restatement is inferred."
            ),
        ),
        (
            "profile",
            "CRCL operating-margin interpretation",
            "reviewed",
            (
                "The reported margin is a descriptive issuer-level measure after "
                "distribution and operating costs. Reserve-income dependence, rates, "
                "circulation and IPO-related expense limit comparison with generic "
                "technology margins. It is not recurring cash profitability."
            ),
        ),
        (
            "publication",
            "Real S6 publication",
            "blocked",
            (
                "S6a is approved for synthetic publication only. Real typed "
                "source/policy/precision lineage, request/publication intent and contract "
                "review remain required. Quote identity affects price metrics, not this "
                "source-only margin."
            ),
        ),
    )
    for identifier, label, status, explanation in definitions:
        evidence_rows = [{"label": "Conclusion", "value": explanation}]
        sources = [source_detail(inventory_capture)]
        if identifier in {"pair", "amendment", "profile"}:
            selected_quotes = [
                q for q in quote_evidence if (q["id"] == "amendment") == (identifier == "amendment")
            ]
            evidence_rows += [
                {"label": q["id"], "value": q["quote"] + " · " + q["locator"]}
                for q in selected_quotes
            ]
            sources = [
                source_detail(
                    captures[RESOURCES[3 if identifier == "amendment" else 2]],
                    RESOURCES[3 if identifier == "amendment" else 2].split("/")[2],
                )
            ]
        if identifier == "events":
            sources = [
                source_detail(original_captures[accession], accession)
                for accession in PRIMARY_REVIEWS
                if accession in original_captures
            ]
        if identifier == "reclassifications":
            sources = [item["source"] for item in reclassifications]
            evidence_rows += [
                {
                    "label": item["source"]["accession"],
                    "value": item["quote"] + " · " + item["locator"],
                }
                for item in reclassifications
            ]
        if identifier == "publication":
            sources = [
                {
                    "label": "S6a repository implementation contract",
                    "url": None,
                    "accession": None,
                    "capturedAt": "2026-09-22 (contract approval, not SEC retrieval)",
                    "transform": (
                        "docs/design/s6/implementation.md; D037 synthetic-only authorization"
                    ),
                    "licence": "Local project documentation",
                }
            ]
        if identifier == "pair":
            evidence_rows += [
                {"label": "D5a input hash", "value": INPUT_HASH},
                {"label": "D5a output hash", "value": OUTPUT_HASH},
            ]
        details[identifier] = {
            "title": label,
            "subtitle": "D5c saved safety review · reviewed 2026-10-12",
            "sections": [{"heading": "Evidence and limits", "rows": evidence_rows}],
            "sources": sources,
        }
        checks.append(
            {
                "id": identifier,
                "label": label,
                "status": status,
                "explanation": explanation,
                "detailId": identifier,
            }
        )
    # Verify the old display projection remains reproducible, without changing it.
    readiness_generated(root)
    profile = json.loads(
        json.dumps(
            asdict(business_profile(UUID(audit["bootstrap_plan"]["issuer_id"]))), default=str
        )
    )
    return {
        "kind": "real-crcl-safety-review",
        "reviewedOn": "2026-10-12",
        "period": "2025-01-01 through 2025-12-31",
        "inventoryWindow": "2025-01-01 through 2026-09-21",
        "historicalRetrievalCutoff": CUTOFF.isoformat(),
        "historicalDecision": {
            "status": "blocked",
            "reasonCodes": ["historical_capture_gap", "profile_not_known_at_cutoff"],
            "explanation": (
                "The September D5a evidence remains ineligible. Later retrievals and an "
                "October profile cannot establish historical application knowledge."
            ),
        },
        "retrospectiveDecision": {
            "status": "blocked" if blockers else "incomplete",
            "reasonCodes": blockers
            + [
                "exhibit_review_incomplete",
                "reclassification_scope_unresolved",
                "real_publication_not_approved",
            ],
            "explanation": (
                "The annual pair and amendment wording pass the bounded replay checks. "
                "Complete financial/event safety has not been proved, and no current "
                "October eligibility judgment is published."
            ),
        },
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "filings": rows,
        "missingExhibits": missing_exhibits,
        "freshInventory": fresh_inventory,
        "checks": checks,
        **(
            {
                "missingPrimaryBodies": [
                    row["resourceKey"] for row in rows if row["bodyStatus"] == "missing"
                ]
            }
            if blockers
            else {}
        ),
        "details": details,
        "profile": profile,
        "profileNotes": [
            (
                "Reserve income depends on the stablecoin reserve base and yield; "
                "distribution economics affect the retained margin."
            ),
            (
                "Reported IPO-related compensation stays in operating expenses; no "
                "adjusted or sustainable margin is inferred."
            ),
            (
                "Holder reserves are not corporate excess cash. Broader balance-sheet and "
                "cash-flow metrics need separate scope review."
            ),
            "No generic technology score, peer percentile, valuation or price ratio is activated.",
        ],
        "inventorySource": source_detail(inventory_capture),
        "inventorySha256": inventory_capture["body_sha256"],
        "quoteEvidence": quote_evidence,
        "acquisitionSha256": acquisition_hash,
        "acquisition": None
        if acquisition is None
        else {
            "status": acquisition["status"],
            "attemptedGroups": len(acquisition["groups"]),
            "originalRowsPreserved": acquisition["originalRowsPreserved"],
            "note": acquisition["note"],
        },
        "nextStep": (
            "Retain and review the listed exhibits, finish "
            "reconciliation of reclassification scope and editions, and review the two "
            "newly discovered "
            "later events before pinning a current cutoff and new batch. Review real "
            "S6 publication before publishing the supported margin."
            if fresh_inventory is not None
            else (
                "Capture and review fresh Submissions inventory before identifying later "
                "events or pinning a current cutoff. Retain missing primary bodies and "
                "their exhibits, reconcile reclassification scope and editions, verify "
                "application preservation, and review real S6 publication prerequisites."
            )
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = json.dumps(review(), indent=2, sort_keys=True) + "\n"
    target = ROOT / REPORT
    if args.check:
        if target.read_text() != output:
            raise ValueError("D5c saved review differs from archived replay")
    else:
        target.write_text(output)


if __name__ == "__main__":
    main()
