"""Hash-bound D049 expanded-line event dispositions and exact edition comparisons."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any

from equity_ingest.filing import extract_inline_filing
from lxml import html

from scripts.normalize_crcl import CIK, ROOT
from scripts.review_crcl_exhibits import clean
from scripts.review_crcl_identity import normalized_text

LEDGER = "docs/research/crcl-broader-body-dispositions-2026-10-15.json"
LEDGER_SHA = "bed6fdbb9eb44ec0dd238e7a69f9800b4d4ab632d18d6cfcaa3151fc4543a560"
COMPONENTS = {
    "CashAndCashEquivalentsAtCarryingValue": "1526046000",
    "CashAndCashEquivalentsSegregatedForCorporateHeldStablecoins": "822963000",
    "CashAndCashEquivalentsSegregatedForTheBenefitOfStablecoinHolders": "75067932000",
    "AccountsReceivableNetCurrent": "62866000",
    "PrepaidExpenseAndOtherAssetsCurrent": "321660000",
    "AssetsCurrent": "77801467000",
    "DepositLiabilityCurrent": "74912567000",
    "AccountsPayableAndAccruedLiabilitiesCurrent": "360609000",
    "ConvertibleNotesPayableCurrent": "36821000",
    "OtherLiabilitiesCurrent": "18398000",
    "LiabilitiesCurrent": "75328395000",
}


def review_bodies(rows: list[dict[str, Any]], bodies: dict[str, bytes]) -> dict[str, Any]:
    raw = (ROOT / LEDGER).read_bytes()
    if hashlib.sha256(raw).hexdigest() != LEDGER_SHA:
        raise ValueError("Expanded accounting dispositions require renewed review")
    ledger = json.loads(raw)["bodyDispositions"]
    filings = {
        r["capture_id"]: r for r in rows if r["source_object_key"].startswith("filing_document/")
    }
    if set(filings) != {r["captureId"] for r in ledger} or len(ledger) != 41:
        raise ValueError("Expanded reviewed body roster differs")
    for item in ledger:
        row = filings[item["captureId"]]
        if (
            row["source_object_key"] != item["resourceKey"]
            or row["body_sha256"] != item["bodySha256"]
            or hashlib.sha256(bodies.get(item["captureId"], b"")).hexdigest() != item["bodySha256"]
            or row["request_url"] != item["url"]
            or row["completed_at"] != item["retrievedAt"]
        ):
            raise ValueError("Expanded reviewed body or lineage changed")
    by_accession = {
        r["accession"]: r
        for r in ledger
        if r["kind"]
        in {
            "audited_annual",
            "periodic_interim",
            "registration",
        }
    }
    extractions: dict[str, Any] = {}

    def inline(acc: str, tag: str, start: str | None, end: str, value: str) -> dict[str, Any]:
        item = by_accession[acc]
        row = filings[item["captureId"]]
        if acc not in extractions:
            extractions[acc] = extract_inline_filing(
                bodies[item["captureId"]],
                expected_sha256=item["bodySha256"],
                expected_byte_count=row["byte_count"],
                expected_cik=CIK,
            )
        extraction = extractions[acc]
        contexts = {c.id: c for c in extraction.contexts}
        units = {u.id: u for u in extraction.units}
        matches = []
        for fact in extraction.facts:
            context = contexts.get(fact.context_id)
            unit = units.get(fact.unit_id)
            if (
                fact.qualified_tag.split("}")[-1] == tag
                and context
                and context.valid
                and context.cik == CIK
                and not context.dimensions
                and context.start_date == (date.fromisoformat(start) if start else None)
                and context.end_date == date.fromisoformat(end)
                and unit
                and fact.unit_id == "usd"
            ):
                if fact.value != Decimal(value) or fact.scale != 3 or fact.decimals != "-3":
                    raise ValueError("Expanded matching-period affected line differs")
                matches.append(
                    {"fact": asdict(fact), "context": asdict(context), "unit": asdict(unit)}
                )
        if not matches:
            raise ValueError("Expanded matching-period affected line absent")
        return {
            "captureId": item["captureId"],
            "bodySha256": item["bodySha256"],
            "accession": acc,
            "url": item["url"],
            "retrievedAt": item["retrievedAt"],
            "periodStart": start,
            "periodEnd": end,
            "valueUSD": value,
            "evidence": matches,
        }

    def table(
        item: dict[str, Any],
        index: int,
        label: str,
        expected: list[int],
        column: int,
        start: str,
        end: str,
    ) -> dict[str, Any]:
        evidence = next(
            t
            for t in item["statementEvidence"]
            if t["locator"] == f"html.table[{index}] (zero-based)"
        )
        candidates = []
        for row in evidence["rows"]:
            if not row.startswith(label):
                continue
            tail = row[len(label) :].replace("$", "").strip()
            if not re.fullmatch(r"[\d,()\s-]+", tail):
                continue
            tokens = re.findall(r"\(\s*[\d,]+\s*\)|[\d,]+", tail)
            values = [
                int(t.replace(",", "").replace("(", "-").replace(")", "").replace(" ", ""))
                for t in tokens
            ]
            if values == expected:
                candidates.append(row)
        if len(candidates) != 1 or "thousands" not in evidence["header"]:
            raise ValueError("Reviewed table period/scale/row values changed")
        return {
            "captureId": item["captureId"],
            "bodySha256": item["bodySha256"],
            "url": item["url"],
            "retrievedAt": item["retrievedAt"],
            "accession": item["accession"],
            "locator": evidence["locator"],
            "header": evidence["header"],
            "row": candidates[0],
            "column": column,
            "periodStart": start,
            "periodEnd": end,
            "valueUSD": str(expected[column] * 1000),
            "scale": 3,
            "interpretation": "Reported cash PPE outflow magnitude"
            if "Purchase" in label
            else "Reported consolidated statement row",
        }

    comparisons = []

    def compare(
        concept: str, left: dict[str, Any], right: dict[str, Any], *, cash: bool = False
    ) -> None:
        if (left["periodStart"], left["periodEnd"]) != (right["periodStart"], right["periodEnd"]):
            raise ValueError("Comparison period mismatch")
        a, b = Decimal(left["valueUSD"]), Decimal(right["valueUSD"])
        if (abs(a) if cash else a) != (abs(b) if cash else b):
            raise ValueError("Expanded affected-line edition mismatch")
        comparisons.append(
            {
                "concept": concept,
                "consistent": True,
                "left": left,
                "right": right,
                "cashOutflowMagnitude": cash,
                "historicalEligibilityGranted": False,
            }
        )

    annual = "0001876042-26-000062"
    q1, q2 = "0001876042-26-000150", "0001876042-26-000248"
    # Every nonzero current component, not just aggregate balance identity.
    for tag, value in COMPONENTS.items():
        left = inline(annual, tag, None, "2025-12-31", value)
        for acc in (q1, q2):
            compare(
                {
                    "AssetsCurrent": "current_assets",
                    "LiabilitiesCurrent": "current_liabilities",
                }.get(tag, tag),
                left,
                inline(acc, tag, None, "2025-12-31", value),
            )
    # Exact half-year later edition, never a substitute for full-year cash flows.
    for concept, tag, value in (
        (
            "cash_from_operating_activities",
            "NetCashProvidedByUsedInOperatingActivities",
            "303716000",
        ),
        ("capital_expenditures_ppe", "PaymentsToAcquirePropertyPlantAndEquipment", "7419000"),
    ):
        compare(
            concept,
            inline("0001628280-25-039781", tag, "2025-01-01", "2025-06-30", value),
            inline(q2, tag, "2025-01-01", "2025-06-30", value),
        )
    # Registration actual statements, excluding preliminary/pro-forma columns.
    q1_tables = {
        "0001193125-25-135795": 516,
        "0001193125-25-121234": 509,
        "0001193125-25-126208": 521,
        "0001193125-25-132755": 521,
    }
    q2_tables = {"0001193125-25-178989": 514, "0001193125-25-181916": 509}
    annual_tables = {
        "0001193125-25-135795": (572, 573),
        "0001193125-25-070481": (514, 515),
        "0001193125-25-084832": (514, 515),
        "0001193125-25-121234": (565, 566),
        "0001193125-25-126208": (577, 578),
        "0001193125-25-132755": (577, 578),
        "0001193125-25-178989": (592, 592),
        "0001193125-25-181916": (587, 587),
    }
    for acc, idx in {**q1_tables, **q2_tables}.items():
        first = acc in q1_tables
        end = "2025-03-31" if first else "2025-06-30"
        specs = (
            (
                "net_income_consolidated",
                "Net income" if first else "Net income (loss)",
                [64791, 48639] if first else [-417309, 81562],
                "ProfitLoss",
            ),
            (
                "cash_from_operating_activities",
                "Net cash provided by operating activities",
                [56593, 77167] if first else [303716, 124955],
                "NetCashProvidedByUsedInOperatingActivities",
            ),
            (
                "capital_expenditures_ppe",
                "Purchase of long-lived assets",
                [-5864, -247] if first else [-7419, -3351],
                "PaymentsToAcquirePropertyPlantAndEquipment",
            ),
        )
        for concept, label, expected, tag in specs:
            left = table(by_accession[acc], idx, label, expected, 0, "2025-01-01", end)
            value = str(
                abs(expected[0]) * 1000
                if concept == "capital_expenditures_ppe"
                else expected[0] * 1000
            )
            compare(
                concept,
                left,
                inline(q1 if first else q2, tag, "2025-01-01", end, value),
                cash=concept == "capital_expenditures_ppe",
            )
    for acc, (cf, ppe) in annual_tables.items():
        for concept, label, expected, tag, idx in (
            (
                "net_income_consolidated",
                "Net income (loss)",
                [155667, 267562, -768847],
                "ProfitLoss",
                cf,
            ),
            (
                "cash_from_operating_activities",
                "Net cash provided by (used in) operating activities",
                [344576, 139568, -72693],
                "NetCashProvidedByUsedInOperatingActivities",
                cf,
            ),
            (
                "capital_expenditures_ppe",
                "Purchase of long-lived assets",
                [-18128, -654, -3050],
                "PaymentsToAcquirePropertyPlantAndEquipment",
                ppe,
            ),
        ):
            for column, year in enumerate((2024, 2023)):
                start, end = f"{year}-01-01", f"{year}-12-31"
                left = table(by_accession[acc], idx, label, expected, column, start, end)
                value = str(
                    abs(expected[column]) * 1000
                    if concept == "capital_expenditures_ppe"
                    else expected[column] * 1000
                )
                compare(
                    concept,
                    left,
                    inline(annual, tag, start, end, value),
                    cash=concept == "capital_expenditures_ppe",
                )

    def release(
        name: str, header: str, quote: str, value: str, start: str | None, end: str, column: int
    ) -> dict[str, Any]:
        item = next(r for r in ledger if r["resourceKey"].endswith("/" + name))
        text = clean(normalized_text(html.fromstring(bodies[item["captureId"]])))
        if text.count(header) != 1 or text.count(quote) != 1:
            raise ValueError("Release period/row evidence changed")
        if text.index(quote) < text.index(header):
            raise ValueError("Release row precedes statement header")
        return {
            "captureId": item["captureId"],
            "bodySha256": item["bodySha256"],
            "url": item["url"],
            "retrievedAt": item["retrievedAt"],
            "accession": item["accession"],
            "locator": f"normalized_text[{text.index(quote)}]",
            "header": header,
            "row": quote,
            "column": column,
            "scale": 3,
            "periodStart": start,
            "periodEnd": end,
            "valueUSD": value,
        }

    releases = (
        (
            "final_circlereportsfourt.htm",
            "December 31, 2025 December 31, 2024 ASSETS Current assets:",
            "Total current assets 77,801,467 45,164,949",
            "Total current liabilities 75,328,395 44,030,967",
            0,
        ),
        (
            "final_05x11q1epr30.htm",
            "March 31, 2026 December 31, 2025 (unaudited) ASSETS Current assets:",
            "Total current assets 79,602,575 77,801,467",
            "Total current liabilities 77,055,382 75,328,395",
            1,
        ),
        (
            "augustepr-circle_q22026f.htm",
            "June 30, 2026 December 31, 2025 (unaudited) ASSETS Current assets:",
            "Total current assets 76,169,618 77,801,467",
            "Total current liabilities 73,602,153 75,328,395",
            1,
        ),
    )
    for name, header, assets, liabilities, column in releases:
        for concept, tag, quote, value in (
            ("current_assets", "AssetsCurrent", assets, "77801467000"),
            ("current_liabilities", "LiabilitiesCurrent", liabilities, "75328395000"),
        ):
            compare(
                concept,
                release(name, header, quote, value, None, "2025-12-31", column),
                inline(annual, tag, None, "2025-12-31", value),
            )
    income_releases = (
        (
            "final_circlereportsfourt.htm",
            "Net income (loss) 133,406 3,109 (69,518) 155,667",
            "-69518000",
            "2025-01-01",
            "2025-12-31",
            2,
            annual,
            "ProfitLoss",
        ),
        (
            "q22025epr.htm",
            "Net income (loss) from continuing operations $ (482,100) $ 32,923 "
            "$ (417,309) $ 81,562",
            "-417309000",
            "2025-01-01",
            "2025-06-30",
            2,
            q2,
            "ProfitLoss",
        ),
        (
            "nolivelinksversion_q3202.htm",
            "Net income (loss) from continuing operations $ 214,385 $ 70,996 $ (202,924) $ 152,558",
            "-202924000",
            "2025-01-01",
            "2025-09-30",
            2,
            "0001876042-25-000047",
            "NetIncomeLoss",
        ),
        (
            "final_05x11q1epr30.htm",
            "Net income from continuing operations 55,246 64,791",
            "64791000",
            "2025-01-01",
            "2025-03-31",
            1,
            q1,
            "ProfitLoss",
        ),
        (
            "augustepr-circle_q22026f.htm",
            "Net income (loss) from continuing operations 48,214 (482,100) 103,460 (417,309)",
            "-417309000",
            "2025-01-01",
            "2025-06-30",
            3,
            q2,
            "ProfitLoss",
        ),
    )
    for name, quote, value, start, end, column, acc, tag in income_releases:
        compare(
            "net_income_consolidated",
            release(
                name, "CONSOLIDATED STATEMENTS OF OPERATIONS", quote, value, start, end, column
            ),
            inline(acc, tag, start, end, value),
        )
    return {
        "ledgerSha256": LEDGER_SHA,
        "bodyDispositions": ledger,
        "editionComparisons": comparisons,
        "annualCashFlowLimitation": (
            "FY2025 annual CFO/PPE are directly supported by audited 10-K "
            "and retained Facts vintages. "
            "No subsequent retained release or quarterly statement reproduces "
            "their full-year amounts. "
            "Interim matching-period comparisons do not prove a full-year amount by addition. "
            "The amendment explicitly leaves the original consolidated statements unchanged."
        ),
        "zeroComponentLimitation": (
            "The original stablecoins-receivable current component is zero; "
            "later balance presentations "
            "omit that row. No missing later value is normalized to zero. "
            "All nonzero selected-period "
            "current components and totals are compared separately."
        ),
    }
