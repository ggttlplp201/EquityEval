"""Read-only D050 blocked-history UI projection; no financial calculation."""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from equity_schema.fundamentals_canonical import canonical_json

from scripts.capture_crcl_history import ACQUISITION
from scripts.normalize_crcl import ROOT
from scripts.review_crcl_history import REPORT, review_acquisition

OUTPUT = ROOT / "apps/web/src/features/analysis-readiness/history.json"
MANIFEST = OUTPUT.with_name("history-manifest.ts")


def project(report: dict[str, Any]) -> dict[str, Any]:
    details = {}
    bodies = []
    for row in report["bodies"]:
        key = row["accession"]
        content = row["contentReview"]
        sections = [
            {
                "heading": "Retained evidence and limits",
                "rows": [
                    {"label": "Resource", "value": row["resourceKey"]},
                    {"label": "Finding", "value": row["finding"]},
                    {"label": "Accounting cleared", "value": "No"},
                    {
                        "label": "Capture",
                        "value": canonical_json(row["capture"])
                        if row["capture"]
                        else "No complete retained body",
                    },
                ],
            }
        ]
        if content:
            if content.get("markers"):
                sections.append(
                    {
                        "heading": "Text screening with exact locators",
                        "rows": [
                            {"label": marker["code"], "value": canonical_json(marker)}
                            for marker in content["markers"]
                            if marker["occurrences"]
                        ],
                    }
                )
                sections.append(
                    {
                        "heading": "Linked references (not fetched by this view)",
                        "rows": [
                            {"label": str(index + 1), "value": canonical_json(reference)}
                            for index, reference in enumerate(content["references"])
                        ],
                    }
                )
            else:
                sections.append(
                    {
                        "heading": "Bounded PDF inspection",
                        "rows": [{"label": "Result", "value": canonical_json(content)}],
                    }
                )
        details[key] = {
            "title": f"{row['form']} · {row['filedDate']}",
            "subtitle": row["accession"],
            "sections": sections,
            "sources": [row["source"]] if row["source"] else [],
        }
        bodies.append(
            {
                name: row[name]
                for name in [
                    "accession",
                    "form",
                    "filedDate",
                    "resourceKey",
                    "retained",
                    "status",
                    "finding",
                    "actualContentType",
                ]
            }
        )
    return {
        **{
            key: report[key]
            for key in [
                "kind",
                "status",
                "retainedBodyCount",
                "mimeCounts",
                "acquisitionCompletedAt",
                "filingDateScopeEnd",
                "postBodyObservation",
                "cutoffNote",
                "blockers",
                "metrics",
                "nextStep",
            ]
        },
        "bodies": bodies,
        "details": details,
        "reviewLimit": (
            "This checkpoint indexes all retained HTML text and references and records "
            "specific accounting findings. It does not claim completed accounting "
            "reconciliation of every edition. Seven PDF bodies remain unreadable under "
            "the required limits; one PDF is not retained."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = review_acquisition(json.loads(ACQUISITION.read_text()))
    if REPORT.read_text() != canonical_json(report) + "\n":
        raise ValueError("D5l review is not reproducible")
    value = canonical_json(project(report)) + "\n"
    manifest = (
        '// Generated from the verified blocked D5l review.\nexport const historySha256 = "'
        + hashlib.sha256(value.encode()).hexdigest()
        + '";\n'
    )
    if args.check:
        if OUTPUT.read_text() != value or MANIFEST.read_text() != manifest:
            raise ValueError("D5l UI projection differs")
    else:
        OUTPUT.write_text(value)
        MANIFEST.write_text(manifest)


if __name__ == "__main__":
    main()
