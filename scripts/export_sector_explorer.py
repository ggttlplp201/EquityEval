"""Render an offline, fictional core-result bundle into labels and chart geometry.

No financial result, cohort, coverage gate, percentile or histogram is calculated
here. Those must already be supplied by equity_core. Decimal is used only to
format values and position complete, untrimmed chart ranges.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from datetime import date
from decimal import Context, Decimal, localcontext
from pathlib import Path
from typing import Any

Row = dict[str, Any]
STATUS = {
    "eligible": "Eligible",
    "limited": "Limited coverage",
    "nm": "N/M",
    "missing": "Missing inputs",
    "stale": "Stale inputs",
    "unsupported": "Unsupported profile",
}


def decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Financial numbers must be unrounded decimal strings")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Non-finite chart value")
    return result


def label(value: Any, unit: str, status: str = "missing") -> str:
    amount = decimal(value)
    if amount is None:
        return "N/M" if status == "nm" else "—"
    if unit == "fraction":
        return f"{amount * 100:,.2f}%"
    return f"{amount:,.2f}×"


def coverage(value: Any) -> str:
    amount = decimal(value)
    return "Unavailable" if amount is None else f"{amount * 100:.0f}%"


def domain(values: list[Decimal], *, zero: bool = True) -> tuple[Decimal, Decimal]:
    items = [*values, Decimal(0)] if zero else values
    low, high = (min(items), max(items)) if items else (Decimal(0), Decimal(1))
    if low == high:
        return (low - 1, high + 1) if low else (Decimal(0), Decimal(1))
    padding = (high - low) / 20
    return (low - padding if low < 0 else low, high + padding)


def position(value: Decimal, limits: tuple[Decimal, Decimal], start: int, end: int) -> float:
    return round(
        float(Decimal(start) + (value - limits[0]) / (limits[1] - limits[0]) * (end - start)), 4
    )


def axis(limits: tuple[Decimal, Decimal], unit: str, start: int, end: int) -> Row:
    ticks = []
    for index in range(5):
        amount = limits[0] + (limits[1] - limits[0]) * Decimal(index) / 4
        ticks.append(
            {"position": position(amount, limits, start, end), "label": label(str(amount), unit)}
        )
    return {"ticks": ticks, "zero": position(Decimal(0), limits, start, end)}


def bar(value: Any, limits: tuple[Decimal, Decimal]) -> Row | None:
    amount = decimal(value)
    if amount is None:
        return None
    origin, endpoint = position(Decimal(0), limits, 0, 100), position(amount, limits, 0, 100)
    return {"left": min(origin, endpoint), "width": abs(endpoint - origin), "endpoint": endpoint}


def reasons(codes: list[str], metric: str = "") -> list[str]:
    denominator = {
        "pe": "Company earnings",
        "ps": "Company revenue",
        "pfcf": "Company free cash flow",
        "revenue_growth": "Prior revenue",
        "growth_breadth": "Prior revenue",
    }.get(metric, "Company denominator")
    messages = {
        "company_denominator_nonpositive": denominator + " is zero or negative",
        "denominator_nonpositive": "Aggregate denominator is zero or negative",
        "small_sample": "Small sample",
        "limited_coverage": "Limited coverage",
        "full_capitalization_unknown": "Full roster capitalization is unknown",
        "unsupported_profile": "Metric unsupported for this company profile",
        "company_metric_unavailable": "Company ratio unavailable",
        "source_precision_unknown": "Source precision is unknown",
        "evidence_value_invalid": "Source amount is missing or invalid",
        "evidence_unusable": "Source amount is not usable",
        "stale_financials": "Financial statements are stale",
        "partial_sector_universe": "Partial sector universe",
        "zero_denominator": "Zero denominator",
        "denominator_indistinguishable_from_zero": (
            "Denominator is too close to zero at source precision"
        ),
    }
    return [messages.get(code, code.replace("_", " ").capitalize()) for code in codes]


def row(raw: Row, unit: str, limits: tuple[Decimal, Decimal]) -> Row:
    state = str(raw["status"])
    if state not in STATUS:
        raise ValueError(f"Unknown evaluated status: {state}")
    return {
        "sectorId": raw["sectorId"],
        "value": raw["value"],
        "valueLabel": label(raw["value"], unit, state),
        "status": state,
        "statusLabel": STATUS[state],
        "reasons": reasons(raw["reasons"], raw["metricId"]),
        "reasonCodes": raw["reasons"],
        "coverageLabel": coverage(raw["issuerCoverage"]),
        "capCoverageLabel": coverage(raw["capCoverage"]),
        "countsLabel": f"N {raw['N']} · K {raw['K']} · V {raw['V']}",
        "eligibilityLabel": f"Contributing / complete: {raw['V']}/{raw['K']}",
        "detailId": raw["detailId"],
        "observations": raw.get("observations", []),
        "concentration": concentration(raw.get("concentration")),
        "bar": bar(raw["value"], limits),
    }


def concentration(raw: Row | None) -> Row | None:
    if raw is None:
        return None
    return {
        "currentShareLabel": coverage(raw["currentTopFiveShare"]),
        "currentDate": raw["currentDate"],
        "growthLabel": label(raw["growthExTopFive"], "fraction"),
        "priorDate": raw["priorDate"],
        "excludedIds": raw["priorTopFiveIds"],
        "reasons": reasons(raw["reasons"]),
    }


def distribution(raw: Row, unit: str) -> Row:
    supplied = raw["distribution"]
    bins = supplied["bins"]
    endpoints = [decimal(item[key]) for item in bins for key in ("lower", "upper")]
    limits = domain([item for item in endpoints if item is not None], zero=False)
    largest = max((int(item["count"]) for item in bins), default=1) or 1
    y_limits = (Decimal(0), Decimal(largest))
    output_bins = []
    for item in bins:
        left, right = decimal(item["lower"]), decimal(item["upper"])
        if left is None or right is None:
            raise ValueError("Supplied histogram bins require both boundaries")
        x = position(left, limits, 60, 730)
        singleton = left == right
        top = position(Decimal(item["count"]), y_limits, 245, 25)
        output_bins.append(
            {
                "id": item["id"],
                "label": (
                    f"{label(str(left), unit)} (single value)"
                    if singleton
                    else f"{label(str(left), unit)} to {label(str(right), unit)}"
                ),
                "countLabel": str(item["count"]),
                "companyIds": item["companyIds"],
                "x": x - 12 if singleton else x,
                "y": top,
                "width": 24 if singleton else position(right, limits, 60, 730) - x,
                "height": 245 - top,
            }
        )
    markers = []
    for name, key in (("P25", "p25"), ("Median", "p50"), ("P75", "p75")):
        amount = decimal(supplied[key])
        if amount is not None:
            markers.append(
                {
                    "label": name,
                    "x": position(amount, limits, 60, 730),
                    "valueLabel": label(str(amount), unit),
                }
            )
    companies = []
    for company in raw["companies"]:
        amount = decimal(company["value"])
        companies.append(
            {
                **company,
                "valueLabel": label(company["value"], unit, company["status"]),
                "reasonCodes": company["reasons"],
                "reasons": reasons(company["reasons"], raw["metricId"]),
                "position": position(amount, limits, 60, 730)
                if amount is not None and company["status"] == "eligible" and bins
                else None,
            }
        )
    return {
        "detailId": raw["detailId"],
        "bins": output_bins,
        "markers": markers,
        "xAxis": axis(limits, unit, 60, 730),
        "yAxis": {
            "ticks": [{"position": 245, "label": "0"}, {"position": 25, "label": str(largest)}],
            "zero": 245,
        },
        "companies": companies,
        "excluded": supplied["excluded"],
        "emptyReason": None
        if bins
        else "No eligible company values for this metric. Excluded companies remain in the table.",
    }


def history(raw: Row, as_of: str, metric: str, method: str, unit: str, years: int) -> Row:
    end = date.fromisoformat(as_of)
    start = date(end.year - years, end.month, end.day)
    points = [
        item
        for item in raw["history"]
        if item["metricId"] == metric
        and item["method"] == method
        and start < date.fromisoformat(item["asOf"]) <= end
    ]
    eligible = [decimal(item["value"]) for item in points if item["status"] == "eligible"]
    y_limits = domain([item for item in eligible if item is not None])
    x_limits = (Decimal(start.toordinal()), Decimal(end.toordinal()))
    series = []
    for sector in raw["sectors"]:
        items = sorted(
            (item for item in points if item["sectorId"] == sector["id"]),
            key=lambda item: item["asOf"],
        )
        coordinates: list[Row] = []
        paths: list[str] = []
        segment: list[str] = []
        previous: date | None = None
        for item in items:
            observation_date = date.fromisoformat(item["asOf"])
            x = position(Decimal(observation_date.toordinal()), x_limits, 60, 730)
            value = decimal(item["value"])
            y = (
                position(value, y_limits, 245, 25)
                if value is not None and item["status"] == "eligible"
                else None
            )
            coordinates.append(
                {
                    "asOf": item["asOf"],
                    "x": x,
                    "y": y,
                    "valueLabel": label(item["value"], unit, item["status"]),
                    "status": STATUS[item["status"]],
                    "detailId": item["detailId"],
                }
            )
            gap = previous is not None and (observation_date - previous).days > 100
            if y is None or gap:
                if segment:
                    paths.append(" ".join(segment))
                segment = []
            if y is not None:
                segment.append(f"{'M' if not segment else 'L'} {x} {y}")
            previous = observation_date
        if segment:
            paths.append(" ".join(segment))
        series.append({"sectorId": sector["id"], "paths": paths, "points": coordinates})
    return {
        "xAxis": {
            "ticks": [
                {"position": 60, "label": start.isoformat()},
                {"position": 730, "label": as_of},
            ],
            "zero": 60,
        },
        "yAxis": axis(y_limits, unit, 245, 25),
        "series": series,
        "note": "Quarter-end snapshots · gaps stay gaps. "
        + raw["context"]["membershipMode"]
        + ". Eligibility and source evidence are recorded separately for every date.",
    }


def scatter(raw: Row, as_of: str, method: str) -> Row:
    current = [
        item for item in raw["evaluations"] if item["asOf"] == as_of and item["method"] == method
    ]
    pe = {item["sectorId"]: item for item in current if item["metricId"] == "pe"}
    growth = {item["sectorId"]: item for item in current if item["metricId"] == "revenue_growth"}
    matched, unavailable = [], []
    for sector in raw["sectors"]:
        x, y = pe.get(sector["id"]), growth.get(sector["id"])
        if (
            x is not None
            and y is not None
            and x["status"] == y["status"] == "eligible"
            and x["value"] is not None
            and y["value"] is not None
        ):
            matched.append((x, y))
        else:
            reasons = [
                STATUS[item["status"]]
                for item in (x, y)
                if item is not None and item["status"] != "eligible"
            ]
            unavailable.append(
                {
                    "sectorId": sector["id"],
                    "reason": "; ".join(dict.fromkeys(reasons))
                    or "Both meaningful P/E and comparable revenue growth are required",
                }
            )
    x_limits = domain([Decimal(item[0]["value"]) for item in matched])
    y_limits = domain([Decimal(item[1]["value"]) for item in matched])
    max_cap = max(
        (Decimal(item[0]["marketCap"]) for item in matched if item[0].get("marketCap") is not None),
        default=Decimal(1),
    )
    points = []
    for x, y in matched:
        cap = decimal(x.get("marketCap"))
        points.append(
            {
                "sectorId": x["sectorId"],
                "x": position(Decimal(x["value"]), x_limits, 60, 730),
                "y": position(Decimal(y["value"]), y_limits, 245, 25),
                "radius": round(float((cap / max_cap).sqrt() * 17), 3)
                if cap is not None and cap > 0 and max_cap > 0
                else 6,
                "xLabel": label(x["value"], "multiple"),
                "yLabel": label(y["value"], "fraction"),
                "detailId": x["detailId"],
                "growthDetailId": y["detailId"],
            }
        )
    method_name = next(item["label"] for item in raw["methods"] if item["id"] == method)
    return {
        "xAxis": axis(x_limits, "multiple", 60, 730),
        "yAxis": axis(y_limits, "fraction", 245, 25),
        "xLabel": f"Trailing P/E · {method_name}",
        "yLabel": f"TTM revenue YoY · {method_name}",
        "points": points,
        "unavailable": unavailable,
    }


def definition(metric: Row, method: Row) -> str:
    if metric["id"] == "growth_breadth":
        return (
            "Equal-company measure in every view: growing issuers / "
            "issuers with valid revenue YoY. "
            "Zero growth is unchanged; missing is not declining."
        )
    if metric["id"] in {"profit_breadth", "cash_breadth"}:
        return "Equal-company measure in every view. " + str(metric["definition"])
    if method["id"] == "mean":
        return "Simple mean of eligible company values, with no outlier trimming. " + str(
            metric["definition"]
        )
    if method["id"] == "median":
        qualifier = " Among profitable companies only." if metric["id"] == "pe" else ""
        return "Median of eligible company values." + qualifier + " " + str(metric["definition"])
    return str(metric["definition"])


def validate_sources(raw: Row) -> None:
    """Reject orphan plotted numbers before creating the browser artifact."""
    records = [*raw["evaluations"], *raw["history"], *raw["market"]]
    records.extend(company for row in raw["evaluations"] for company in row["companies"])
    for record in records:
        detail = raw["details"].get(record["detailId"])
        if not detail or not detail.get("sources") or not detail.get("sections"):
            raise ValueError("Every observation needs its frozen source detail")
        if record["status"] not in STATUS:
            raise ValueError("Unknown evaluated observation status")


def export(raw: Row) -> Row:
    with localcontext(Context(prec=4096, Emin=-9999, Emax=9999)):
        return _export(raw)


def _export(raw: Row) -> Row:
    if raw.get("fictional") is not True:
        raise ValueError("Only explicitly fictional development data may enter this artifact")
    validate_sources(raw)
    labels = {item["id"]: item["label"] for item in raw["sectors"]}
    views = {}
    for as_of in raw["context"]["asOfDates"]:
        for metric in raw["metrics"]:
            unit = metric["unit"]
            for method in raw["methods"]:
                selection = (as_of, metric["id"], method["id"])
                records = [
                    item
                    for item in raw["evaluations"]
                    if (item["asOf"], item["metricId"], item["method"]) == selection
                ]
                market = next(
                    (
                        item
                        for item in raw["market"]
                        if (item["asOf"], item["metricId"], item["method"]) == selection
                    ),
                    None,
                )
                amounts = [
                    decimal(item["value"]) for item in [*records, *([market] if market else [])]
                ]
                limits = domain([value for value in amounts if value is not None])
                rendered = [row(item, unit, limits) for item in records]
                alphabetical = sorted(rendered, key=lambda item: labels[item["sectorId"]])
                ranked = sorted(
                    (
                        item
                        for item in records
                        if item["status"] == "eligible" and item["value"] is not None
                    ),
                    key=lambda item: Decimal(item["value"]),
                    reverse=True,
                )
                unavailable = [
                    item
                    for item in alphabetical
                    if item["status"] != "eligible" or item["value"] is None
                ]
                manifest = {
                    "selection": selection,
                    "context": raw["context"],
                    "records": records,
                    "market": market,
                    "history": raw["history"],
                    "details": raw["details"],
                }
                view_id = hashlib.sha256(
                    json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                views["|".join(selection)] = {
                    "id": view_id,
                    "asOf": as_of,
                    "metricId": metric["id"],
                    "method": method["id"],
                    "definition": definition(metric, method),
                    "rows": rendered,
                    "orders": {
                        "alphabetical": [item["sectorId"] for item in alphabetical],
                        "numeric": [item["sectorId"] for item in [*ranked, *unavailable]],
                    },
                    "axis": axis(limits, unit, 0, 100),
                    "market": row(market, unit, limits) if market else None,
                    "distributions": {
                        item["sectorId"]: distribution(item, unit) for item in records
                    },
                    "history": {
                        str(years): history(raw, as_of, metric["id"], method["id"], unit, years)
                        for years in (1, 3, 5)
                    },
                    "scatter": scatter(raw, as_of, method["id"]),
                }
    return {
        "fictional": True,
        "context": raw["context"],
        "sectors": raw["sectors"],
        "metrics": raw["metrics"],
        "methods": raw["methods"],
        "views": views,
        "details": raw["details"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raw = json.loads(args.input.read_text())
    result = export(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(
        gzip.compress(content, mtime=0) if args.output.suffix == ".gz" else content
    )
    print(f"Exported {len(result['views'])} fictional presentation views to {args.output}")


if __name__ == "__main__":
    main()
