"""D050 retained-body screening and explicit unresolved accounting/history gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from equity_ingest.archive import LocalArchive
from equity_schema.fundamentals_canonical import canonical_json
from lxml import html

from scripts.capture_crcl_history import ACQUISITION, checked_scope
from scripts.normalize_crcl import ROOT
from scripts.review_crcl_exhibits import clean
from scripts.review_crcl_identity import normalized_text
from scripts.review_crcl_safety import source_detail

ACQUISITION_SHA = "34a52157078f4f9f0b89c5a3f3b538d22568c8fdf20bbf77d6cc632c66daf015"
REPORT = ROOT / "docs/research/crcl-history-review-2026-10-17-r2.json"
PDF_REPORT = ROOT / "docs/research/crcl-history-pdf-runtime-2026-10-17.json"
PDF_SHA = "78fde310a08714ee978893f90e3c721654d7b4d32eb81536d3acab6a54c0c99f"
PRIOR_FACTS_SHA = "f7139545b482a7b31520225bc155cb41241b82f004eb8fbca55f4ab66d1426af"
MARKERS = {
    "fund_accounting_objection": "object to the Company’s conclusion",
    "cash_flow_presentation": (
        "presented in the consolidated statements of cash flows in the same manner"
    ),
    "preliminary_results": (
        "Our consolidated financial statements as of and for the three months ended "
        "March 31, 2025 are not yet available"
    ),
    "withdrawal": "no longer plans to consummate the business combination",
    "financial_reclassification": "Certain prior period amounts have been reclassified",
    "concord_restated": "Concord’s audited financial statements (as restated)",
    "fund_equity_method": "equity method",
    "sab122": "The Company early adopted SAB 122 retrospectively",
    "fund_fair_value": "In January 2025, the Company retrospectively changed",
    "redacted_content": "[***]",
    "incorporation": "incorporated by reference",
    "control_weakness": "material weakness",
    "discontinued_operations": "discontinued operations",
}
FINDINGS = {
    "0000950123-25-001965": (
        "Draft discloses retrospective SAB122 safeguarding-asset/liability removal "
        "for earlier balance sheets, with no stated operating/net-income or equity effect. "
        "It also adopts the ASC825 fair-value option for the Reserve Fund, otherwise "
        "an equity-method investment; the stated effect is additional disclosure. "
        "Earlier balance-sheet editions cannot be blended into ROA history."
    ),
    "0000950123-25-000606": (
        "SEC comment objects to Reserve Fund accounting and requests equity-method "
        "treatment for each presented period. The issuer’s substantive response is "
        "redacted. Later edition reconciliation and the retained-but-unreadable SEC "
        "letter are still required."
    ),
    "0000950103-25-004232": (
        "Response addresses corporate-held USDC operating-expense cash-flow "
        "presentation and adds earlier audited Reserve Fund statements. Circle and "
        "Fund entity/period scopes must remain separate."
    ),
    "0001193125-25-084837": (
        "Response discusses distribution-cost trends and clarifies corporate-held "
        "USDC cash-flow and balance-sheet presentation, including a promised "
        "post-IPO policy update. This is affected-line evidence, not a clearance of "
        "all earlier editions."
    ),
    "0001193125-25-098254": (
        "Preliminary Q1 ranges are explicitly subject to closing and not audited or "
        "reviewed by Deloitte. They cannot replace final reported operands or "
        "establish a historical trend."
    ),
    "0000950103-25-003718": (
        "Proposed risk-factor, capital-stock and bylaw text is redacted. The public "
        "body cannot establish the omitted content’s accounting relevance."
    ),
    "0001104659-22-124570": (
        "Withdrawal states that the proposed business combination will not proceed "
        "and the registration never became effective. Proposed "
        "combined-company/pro-forma figures must not become Circle reported history."
    ),
    "0000950103-25-007009": (
        "Additional-share registration incorporates the prior S-1 and exhibits; "
        "this body does not supply a new selected statement edition."
    ),
    "0001193125-26-335377": (
        "Shelf registration incorporates retained annual/quarterly/event filings "
        "and security-description/legal documents. Incorporation is not a new "
        "accounting statement or proof that every linked exhibit is irrelevant."
    ),
}


def indexed_body(body: bytes) -> dict[str, Any]:
    doc = html.fromstring(body, parser=html.HTMLParser(encoding="utf-8", no_network=True))
    text = clean(normalized_text(doc))
    markers = []
    for code, phrase in MARKERS.items():
        matches = list(re.finditer(re.escape(phrase), text, re.I))
        markers.append(
            {
                "code": code,
                "occurrences": len(matches),
                "evidence": [
                    {
                        "locator": f"normalized-text:{m.start()}:{m.end()}",
                        "excerpt": text[max(0, m.start() - 100) : m.end() + 450],
                    }
                    for m in matches[:3]
                ],
            }
        )
    return {
        "fullTextIndexed": True,
        "textSha256": hashlib.sha256(text.encode()).hexdigest(),
        "textLength": len(text),
        "markers": markers,
        "references": [
            {"href": a.get("href"), "label": clean(normalized_text(a))}
            for a in doc.iter("a")
            if a.get("href") is not None and not a.get("href", "").startswith("#")
        ],
        "screeningLimit": (
            "Full retained text and links indexed; keyword absence does not prove "
            "absence of corrections. Selected accounting editions are not cleared by "
            "this screening."
        ),
    }


def review_acquisition(acquisition: dict[str, Any] | None, root: Path = ROOT) -> dict[str, Any]:
    scope = checked_scope()
    if (
        acquisition is not None
        and hashlib.sha256((canonical_json(acquisition) + "\n").encode()).hexdigest()
        != ACQUISITION_SHA
    ):
        raise ValueError("Acquisition differs from pinned D5l evidence")
    captures = [c for g in (acquisition or {}).get("groups", []) for c in g["captures"]]
    archive = LocalArchive(root / "var/raw")
    verified = {
        c["capture_id"]: archive.read_blob(c["blob_key"], c["body_sha256"], c["byte_count"])
        for c in captures
    }
    by_key = {c["source_object_key"]: c for c in captures}
    pdf_path = root / PDF_REPORT.relative_to(ROOT)
    if pdf_path.exists() and hashlib.sha256(pdf_path.read_bytes()).hexdigest() != PDF_SHA:
        raise ValueError("PDF runtime audit differs from pinned evidence")
    pdf_rows = json.loads(pdf_path.read_text()) if pdf_path.exists() else []
    pdf_by_key = {r["resourceKey"]: r for r in pdf_rows}
    bodies = []
    mime_counts: dict[str, int] = {}
    for item in scope["resources"]:
        key = item["resourceKey"]
        capture = by_key.get(key)
        row = {
            **item,
            "retained": capture is not None,
            "accountingCleared": False,
            "capture": capture,
            "contentReview": None,
            "source": None,
            "status": "missing_body",
            "finding": "No retained complete body; content relevance is unconfirmed.",
        }
        if capture:
            mime = capture["content_type"].split(";", 1)[0].lower()
            expected = "application/pdf" if key.endswith(".pdf") else "text/html"
            if mime != expected:
                raise ValueError("Retained MIME differs from reviewed representation")
            mime_counts[mime] = mime_counts.get(mime, 0) + 1
            row["actualContentType"] = mime
            row["source"] = source_detail(capture, item["accession"])
            if mime == "application/pdf":
                review = pdf_by_key.get(key)
                if review and review["inputSha256"] != capture["body_sha256"]:
                    raise ValueError("PDF runtime evidence differs from retained body")
                row.update(
                    status="pdf_review_blocked",
                    contentReview=review,
                    finding=(
                        "Retained PDF; bounded parser cannot enforce required memory cap on this "
                        "host. Contents and references remain unreviewed, not irrelevant."
                    ),
                )
            else:
                row.update(
                    status="accounting_reconciliation_unresolved",
                    contentReview=indexed_body(verified[capture["capture_id"]]),
                    finding=FINDINGS.get(
                        item["accession"],
                        (
                            "Retained HTML text and reference screening is available. "
                            "Entity, period, "
                            "final-versus-pro-forma and affected-line reconciliation remains "
                            "unapproved; no numeric history is selected from this body."
                        ),
                    ),
                )
        bodies.append(row)
    facts = [c for c in captures if c["source_object_key"].startswith("company_facts/")]
    submissions = [c for c in captures if c["source_object_key"].startswith("submissions/")]
    inventory = json.loads(verified[submissions[-1]["capture_id"]]) if submissions else None
    return {
        "kind": "d5l-blocked-history-review",
        "status": "blocked",
        "acquisitionSha256": ACQUISITION_SHA if acquisition else None,
        "acquisitionStartedAt": (acquisition or {}).get("startedAt"),
        "acquisitionCompletedAt": (acquisition or {}).get("completedAt"),
        "filingDateScopeEnd": "2026-10-16",
        "postBodyObservation": None,
        "cutoffNote": (
            "October 17 retrievals do not establish September knowledge or full-day "
            "October 16 coverage. No final post-body mandatory pair was dispatched; no "
            "new eligibility cutoff is established."
        ),
        "retainedBodyCount": sum(r["retained"] for r in bodies),
        "mimeCounts": mime_counts,
        "eligibleForNormalization": False,
        "financialPublication": False,
        "blockers": [
            "ars_body_limit",
            "pdf_limits_unavailable",
            "post_body_pair_not_captured",
            "affected_line_edition_reconciliation_unresolved",
            "gross_margin_applicability_and_operands_unreviewed",
            "historical_periods_and_trend_contract_inputs_unreviewed",
        ]
        if acquisition
        else ["acquisition_unavailable", "accounting_review_unavailable"],
        "metrics": [
            {"id": name, "value": None, "status": "unsupported", "reason": reason}
            for name, reason in (
                (
                    "gross_margin",
                    (
                        "No reviewed complete-scope gross-profit/cost-of-revenue operand; "
                        "distribution costs or RLDC cannot substitute."
                    ),
                ),
                (
                    "revenue_growth",
                    (
                        "Annual reported operands remain candidates until "
                        "registration/correspondence editions and missing PDF/final-pair gates are "
                        "resolved."
                    ),
                ),
                (
                    "return_on_assets",
                    (
                        "Opening/closing assets and consolidated profit require Reserve Fund, "
                        "holder-asset, temporary-equity and edition reconciliation; do not "
                        "substitute parent net income."
                    ),
                ),
                (
                    "history_trend",
                    (
                        "No newly eligible period snapshots or three comparable quarterly "
                        "year-over-year samples; annual growth does not establish trend."
                    ),
                ),
            )
        ],
        "bodies": bodies,
        "mandatoryPairReview": {
            "factsCaptures": facts,
            "submissionsCaptures": submissions,
            "factsMatchPrior": bool(facts)
            and all(c["body_sha256"] == PRIOR_FACTS_SHA for c in facts),
            "submissionsMatchesPrior": bool(submissions)
            and all(c["body_sha256"] == scope["inventoryBodySha256"] for c in submissions),
            "recentRecordCount": len(inventory["filings"]["recent"]["accessionNumber"])
            if inventory
            else None,
            "advertisedHistory": inventory["filings"]["files"] if inventory else None,
            "limitation": (
                "These ten pairs preceded the final body attempt; unchanged hashes cannot "
                "stand in for the withheld final pair."
            ),
        },
        "preservation": {
            "originalRowsPreserved": (acquisition or {}).get("originalRowsPreserved", False),
            "priorSnapshotsUnchanged": True if acquisition else None,
        },
        "nextStep": (
            "Review an exact ARS-only bounded acquisition amendment and an enforcing "
            "PDF runtime; complete all eight PDF content/reference reviews and "
            "affected-line reconciliation, then capture a fresh mandatory pair after "
            "all retained bodies. No retry, larger cap, normalization or metric "
            "publication is authorized by this artifact."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = ACQUISITION.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ACQUISITION_SHA:
        raise ValueError("Acquisition file changed")
    report = review_acquisition(json.loads(raw))
    value = canonical_json(report) + "\n"
    if args.check:
        if REPORT.read_text() != value:
            raise ValueError("D5l history review differs")
    else:
        from scripts.publish_crcl_fundamentals import _write_exclusive

        _write_exclusive(REPORT, report)
    print(report["status"], report["retainedBodyCount"])


if __name__ == "__main__":
    main()
