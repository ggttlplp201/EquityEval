"""D047 exact fresh inventory observation; prior audits remain immutable."""

from __future__ import annotations

from datetime import date
from typing import Any

from scripts.normalize_crcl import RESOURCES

END = date(2026, 10, 15)
ACQUISITION = "docs/research/crcl-observation-acquisition-2026-10-15.json"
REPORT = "docs/research/crcl-observation-review-2026-10-15.json"


def acquisition_complete(report: dict[str, Any] | None) -> bool:
    if (
        not report
        or report.get("originalRowsPreserved") is not True
        or report.get("errorType") is not None
    ):
        return False
    groups = report.get("groups", [])
    if len(groups) != 1:
        return False
    group = groups[0]
    captures = group.get("captures", [])
    return (
        group["result"]["state"] == "completed"
        and not group["result"]["gaps"]
        and group["bootstrap_plan"]["resources"] == list(RESOURCES[:2])
        and group["bootstrap_plan"]["inventory_start"] == "2025-01-01"
        and group["bootstrap_plan"]["inventory_end"] == END.isoformat()
        and len(captures) == 2
        and {c["source_object_key"] for c in captures} == set(RESOURCES[:2])
        and len({c["capture_id"] for c in captures}) == 2
        and all(c["http_status"] == 200 for c in captures)
    )


def metadata_rows(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from scripts.review_crcl_prospectus import REGISTRATION_FORMS
    from scripts.review_crcl_safety import FORMS

    recent = document["filings"]["recent"]
    return {
        accession: {key: values[i] for key, values in recent.items()}
        for i, accession in enumerate(recent["accessionNumber"])
        if recent["form"][i] in FORMS | REGISTRATION_FORMS
        and recent["filingDate"][i] >= "2025-01-01"
    }


def compare_documents(
    facts: dict[str, Any],
    inventory: dict[str, Any],
    old_inventory: dict[str, Any],
    observed: Any,
    capture_id: Any,
) -> dict[str, Any]:
    import json

    from equity_ingest.sec_inventory import parse_submissions

    from scripts.normalize_crcl import CIK
    from scripts.review_crcl_current import annual_edition_check, review_inventory
    from scripts.review_crcl_leadership import q1_facts_review
    from scripts.review_crcl_safety import FORMS

    previous, current = metadata_rows(old_inventory), metadata_rows(inventory)
    expected = [
        {
            "accession": a,
            "form": r["form"],
            "filedDate": r["filingDate"],
            "resourceKey": f"filing_document/{CIK}/{a}/{r['primaryDocument']}",
        }
        for a, r in previous.items()
        if r["form"] in FORMS
    ]
    document = parse_submissions(
        json.dumps(inventory).encode(), expected_cik=CIK, capture_id=capture_id
    )
    assessed = review_inventory(document, expected, observed)
    changed = sorted(a for a in set(previous) | set(current) if previous.get(a) != current.get(a))
    relevant = [f for f in document.filings if f.accession in current]
    accepted = len(relevant) == len(current) and all(
        f.acceptance_at is not None and f.acceptance_at <= observed for f in relevant
    )
    annual = []
    for concept, expected_value in [
        ("Revenues", "2746642000"),
        ("OperatingIncomeLoss", "-96435000"),
    ]:
        records = [
            r
            for r in facts.get("facts", {})
            .get("us-gaap", {})
            .get(concept, {})
            .get("units", {})
            .get("USD", [])
            if r.get("start") == "2025-01-01" and r.get("end") == "2025-12-31"
        ]
        annual.append({"concept": concept, **annual_edition_check(records, expected_value)})
    q1 = q1_facts_review(facts)
    return {
        "inventory": assessed,
        "changedMetadataAccessions": changed,
        "allScopedAcceptanceTimesWithinObservation": accepted,
        "annualEditionChecks": annual,
        "q1": q1,
        "matched": assessed["status"] == "matched_scoped_roster"
        and not changed
        and accepted
        and all(r["status"] == "matched" for r in annual)
        and q1["status"] == "later_comparative_only"
        and all(
            r["record"]["val"]
            == {"Revenues": 578573000, "OperatingIncomeLoss": 92940000}[r["concept"]]
            for r in q1["rows"]
        ),
    }


ACCEPTANCE_VINTAGES = {
    "0001876042-26-000062": ("2026-03-09T12:36:51.000Z", "2026-03-09T16:36:51.000Z"),
    "0001876042-26-000228": ("2026-07-13T20:40:02.000Z", "2026-07-14T00:40:02.000Z"),
    "0001876042-26-000248": ("2026-08-05T13:02:57.000Z", "2026-08-05T17:02:57.000Z"),
}


def metadata_rebinding(
    root: Any, captures: list[dict[str, Any]], fresh: dict[str, Any], document: dict[str, Any]
) -> dict[str, Any]:
    import json

    from equity_ingest.archive import LocalArchive

    from scripts.normalize_crcl import load_preparation
    from scripts.review_crcl_safety import source_detail

    old, _ = load_preparation(root)
    archive = LocalArchive(root / "var/raw")
    current = metadata_rows(document)
    rows = []
    matched = True
    for filing in old.inputs.filings:
        capture = next(c for c in captures if c["capture_id"] == str(filing.metadata_capture_id))
        previous = metadata_rows(
            json.loads(
                archive.read_blob(
                    capture["blob_key"], capture["body_sha256"], capture["byte_count"]
                )
            )
        )
        before, after = previous[filing.accession], current.get(filing.accession, {})
        changes = {
            k: {"previous": before.get(k), "current": after.get(k)}
            for k in before.keys() | after.keys()
            if before.get(k) != after.get(k)
        }
        expected = ACCEPTANCE_VINTAGES[filing.accession]
        allowed = {"acceptanceDateTime": {"previous": expected[0], "current": expected[1]}}
        matched = matched and changes == allowed
        rows.append(
            {
                "accession": filing.accession,
                "oldCaptureId": capture["capture_id"],
                "newCaptureId": fresh["capture_id"],
                "oldBodySha256": capture["body_sha256"],
                "newBodySha256": fresh["body_sha256"],
                "oldFilingVersionId": str(filing.id),
                "changedFields": changes,
                "source": source_detail(capture),
                "metadataFieldReview": "Every raw metadata field compared; "
                "only pinned acceptanceDateTime delta allowed.",
            }
        )
    return {
        "status": "reviewed_source_vintage_difference" if matched else "blocked",
        "rows": rows,
        "limit": "Use the fresh source-reported timestamp in a new immutable version. "
        "The cause of the difference is not inferred; old versions and September "
        "knowledge remain unchanged.",
    }


def review_acquisition(acquisition: dict[str, Any] | None, root: Any = None) -> dict[str, Any]:
    import hashlib
    import json
    from datetime import datetime
    from uuid import UUID

    from equity_ingest.archive import LocalArchive

    from scripts.export_crcl_registration import REVIEW_SHA
    from scripts.normalize_crcl import ROOT
    from scripts.review_crcl_registration import REPORT as PRIOR_REPORT
    from scripts.review_crcl_registration import retained_captures
    from scripts.review_crcl_registration import review as replay_prior
    from scripts.review_crcl_safety import source_detail

    root = root or ROOT
    prior = replay_prior(root)
    raw = (json.dumps(prior, indent=2, sort_keys=True) + "\n").encode()
    if hashlib.sha256(raw).hexdigest() != REVIEW_SHA or (root / PRIOR_REPORT).read_bytes() != raw:
        raise ValueError("Pinned D5h review changed")
    if prior["candidateBatch"]["reasonCodes"] != ["inventory_observation_precedes_evidence_cutoff"]:
        raise ValueError("Prior content/accounting gates are not satisfied")
    rows = retained_captures(root)
    old = {
        key: max(
            (r for r in rows if r["source_object_key"] == key), key=lambda r: r["completed_at"]
        )
        for key in RESOURCES[:2]
    }
    archive = LocalArchive(root / "var/raw")
    old_inventory = json.loads(
        archive.read_blob(
            old[RESOURCES[1]]["blob_key"],
            old[RESOURCES[1]]["body_sha256"],
            old[RESOURCES[1]]["byte_count"],
        )
    )
    indexed, documents = {}, {}
    groups = (acquisition or {}).get("groups", [])
    if len(groups) > 1:
        raise ValueError("Observation scope expanded")
    for group in groups:
        for c in group["captures"]:
            key = c["source_object_key"]
            stamp = datetime.fromisoformat(c["completed_at"])
            if (
                key not in RESOURCES[:2]
                or key in indexed
                or stamp.utcoffset() is None
                or stamp <= datetime.fromisoformat(prior["retrievalCutoff"])
                or stamp.date() != END
            ):
                raise ValueError("Unexpected, duplicate, backdated or out-of-window observation")
            body = archive.read_blob(c["blob_key"], c["body_sha256"], c["byte_count"])
            if c["http_status"] == 200:
                indexed[key] = c
                documents[key] = json.loads(body)
    reasons = []
    if not acquisition_complete(acquisition):
        reasons.append("observation_acquisition_incomplete")
    comparison = None
    metadata = None
    observed = None
    if set(indexed) == set(RESOURCES[:2]):
        observed = datetime.fromisoformat(indexed[RESOURCES[1]]["completed_at"])
        if any(datetime.fromisoformat(c["completed_at"]) > observed for c in indexed.values()):
            reasons.append("facts_retrieved_after_inventory_observation")
        comparison = compare_documents(
            documents[RESOURCES[0]],
            documents[RESOURCES[1]],
            old_inventory,
            observed,
            UUID(indexed[RESOURCES[1]]["capture_id"]),
        )
        metadata = metadata_rebinding(root, rows, indexed[RESOURCES[1]], documents[RESOURCES[1]])
        if metadata["status"] != "reviewed_source_vintage_difference":
            reasons.append("historical_metadata_change_unreviewed")
        if not comparison["matched"]:
            reasons.append("source_editions_or_inventory_changed")
        if indexed[RESOURCES[0]]["body_sha256"] != old[RESOURCES[0]]["body_sha256"]:
            reasons.append("facts_payload_changed_requires_review")
    sources = [
        {
            **source_detail(c),
            "label": "SEC Company Facts" if k == RESOURCES[0] else "SEC Submissions inventory",
        }
        for k, c in indexed.items()
    ]
    if metadata:
        sources += [r["source"] for r in metadata["rows"]]
    timing = {
        "state": "blocked" if reasons else "observation_covers_retained_evidence",
        "inventoryObservedAt": observed.isoformat() if observed else None,
        "priorEvidenceRetrievalCutoff": prior["retrievalCutoff"],
        "fullDayCoverage": False,
        "interpretation": "Retrospective filing-date scope through the exact observation only; "
        "no intraday interval after that instant or whole-day completeness is asserted. "
        "September application knowledge is unchanged.",
    }
    return {
        "kind": "real-crcl-observation-review",
        "proposalCommit": "c55c2cf",
        "reviewedOn": "2026-10-15",
        "priorReviewSha256": REVIEW_SHA,
        "comparison": comparison,
        "metadataRebinding": metadata,
        "timeScope": timing,
        "inventoryObservedAt": timing["inventoryObservedAt"],
        "candidateBatch": {
            "status": "blocked" if reasons else "ready_for_s3_preparation",
            "reasonCodes": reasons,
            "batchId": None,
        },
        "operatingMargin": None,
        "publishedMetricCount": 0,
        "conclusion": "Fresh observation matches the reviewed selected-line history and closes the "
        "prior temporal gap. S3 preparation and independent publication review are required; "
        "no ratio is published."
        if not reasons
        else "Fresh observation remains incomplete or changed; "
        "no eligible batch or ratio is claimed.",
        "details": {
            "observation": {
                "title": "Exact current observation and edition checks",
                "subtitle": "D5i fresh mandatory pair; D5h retained-body review pinned by hash",
                "sections": [
                    {
                        "heading": "Evidence and limits",
                        "rows": [
                            {
                                "label": "Exact cutoff scope",
                                "value": json.dumps(timing, sort_keys=True),
                            },
                            {
                                "label": "Fresh comparisons",
                                "value": json.dumps(comparison, sort_keys=True),
                            },
                            {"label": "Pinned prior review", "value": REVIEW_SHA},
                            {
                                "label": "Historical metadata differences",
                                "value": json.dumps(metadata, sort_keys=True),
                            },
                        ],
                    }
                ],
                "sources": sources,
            }
        },
    }


def review(root: Any = None) -> dict[str, Any]:
    import hashlib
    import json

    from scripts.normalize_crcl import ROOT

    root = root or ROOT
    path = root / ACQUISITION
    raw = path.read_bytes() if path.exists() else None
    result = review_acquisition(json.loads(raw) if raw else None, root)
    result["acquisitionSha256"] = hashlib.sha256(raw).hexdigest() if raw else None
    return result


def retained_captures(root: Any) -> list[dict[str, Any]]:
    import json

    from scripts.review_crcl_registration import retained_captures as prior_captures

    result = prior_captures(root)
    report = json.loads((root / ACQUISITION).read_bytes())
    result.extend(c for group in report["groups"] for c in group["captures"])
    if len({r["capture_id"] for r in result}) != len(result):
        raise ValueError("Repeated capture identity in observation lineage")
    return result


def main() -> None:
    import argparse
    import json

    from scripts.normalize_crcl import ROOT

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = json.dumps(review(), indent=2, sort_keys=True) + "\n"
    target = ROOT / REPORT
    if args.check:
        if not target.exists() or target.read_text() != text:
            raise ValueError("Observation review differs from archive replay")
    else:
        target.write_text(text)
    print(json.dumps({"review": REPORT, "verified": args.check}))


if __name__ == "__main__":
    main()
