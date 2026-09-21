"""Project frozen fictional company results into an offline Company display bundle.

This is an internal presentation format, not the S6 API. Existing equity_core
results and source records are copied without recalculation. Arithmetic here is
limited to display formatting, calendar windows and chart geometry. Sector
histories are deliberately ignored: they are not company observations.
"""

from __future__ import annotations

import argparse
import calendar
import gzip
import hashlib
import json
from datetime import date
from decimal import Context, Decimal, localcontext
from pathlib import Path
from typing import Any

from scripts.export_sector_explorer import STATUS, axis, decimal, domain, label, position, reasons

Row = dict[str, Any]
METRIC_IDS = {
    "pe": "pe",
    "ps": "ps",
    "pfcf": "pfcf",
    "revenue_growth": "revenue_yoy",
    "operating_margin": "operating_margin",
    "fcf_margin": "fcf_margin",
}


def fields(section: Row) -> dict[str, str]:
    return {item["label"]: item["value"] for item in section["rows"]}


def validate_detail(record: Row, detail: Row | None, metric_id: str, as_of: str) -> None:
    observation_date = date.fromisoformat(as_of)
    if (
        observation_date.month not in (3, 6, 9, 12)
        or observation_date.day
        != (calendar.monthrange(observation_date.year, observation_date.month)[1])
    ):
        raise ValueError("Company history observations require exact calendar quarter ends")
    if record["detailId"] != f"company|{as_of}|{record['id']}":
        raise ValueError("Company observation date does not match its frozen source detail ID")
    if not detail or not detail.get("sources") or not detail.get("sections"):
        raise ValueError("Every company observation needs its frozen source detail")
    sections = {section["heading"]: section for section in detail["sections"]}
    snapshot = fields(sections.get("Fictional company snapshot", {"rows": []}))
    if (
        snapshot.get("Snapshot ID") != record["snapshotId"]
        or snapshot.get("Issuer") != record["id"]
    ):
        raise ValueError("Company snapshot identity does not match frozen source detail")
    if record["status"] not in STATUS:
        raise ValueError("Unknown evaluated company status")
    value = decimal(record["value"])
    if value is not None:
        calculations = fields(sections.get("Shared company calculations", {"rows": []}))
        frozen = calculations.get(metric_id, "Unavailable").split(";", 1)[0]
        if frozen == "Unavailable" or decimal(frozen) != value:
            raise ValueError("Company value does not match frozen core calculation")


def source_amounts(detail: Row, detail_id: str) -> list[Row]:
    output = []
    for section in detail["sections"]:
        supplied = fields(section)
        if "Value (USD)" not in supplied:
            continue
        raw_value = supplied["Value (USD)"]
        value = None if raw_value == "Unavailable" else raw_value
        amount = decimal(value)
        input_hash = supplied.get("Input manifest SHA256")
        if not input_hash:
            raise ValueError("Every company amount requires its exact input manifest")
        output.append(
            {
                "label": section["heading"],
                "value": value,
                "valueLabel": "—" if amount is None else f"${amount:,.2f}",
                "basis": supplied.get("Basis", "Unavailable"),
                "period": supplied.get("Period", "Unavailable"),
                "inputHash": input_hash,
                "flags": supplied.get("Flags", "None"),
                "uncertainty": supplied.get("Absolute source uncertainty", "Unavailable"),
                "detailId": detail_id,
            }
        )
    return output


def calendar_window(as_of: str, years: int) -> tuple[date, date, list[str]]:
    end = date.fromisoformat(as_of)
    start = end.replace(
        year=end.year - years,
        day=min(end.day, calendar.monthrange(end.year - years, end.month)[1]),
    )
    expected = []
    for year in range(start.year, end.year + 1):
        for month in (3, 6, 9, 12):
            quarter = date(year, month, calendar.monthrange(year, month)[1])
            if start < quarter <= end:
                expected.append(quarter.isoformat())
    return start, end, expected


def history_chart(observations: list[Row], metric: Row, start: date, end: date) -> Row:
    eligible = [
        decimal(view["metricMap"][metric["id"]]["value"])
        for view in observations
        if view["metricMap"][metric["id"]]["status"] == "eligible"
    ]
    limits = domain([value for value in eligible if value is not None])
    x_limits = (Decimal(start.toordinal()), Decimal(end.toordinal()))
    points: list[Row] = []
    paths: list[str] = []
    segment: list[str] = []
    previous: date | None = None
    for observation in observations:
        item = observation["metricMap"][metric["id"]]
        point_date = date.fromisoformat(observation["asOf"])
        value = decimal(item["value"])
        x = position(Decimal(point_date.toordinal()), x_limits, 60, 730)
        y = (
            position(value, limits, 245, 25)
            if value is not None and item["status"] == "eligible"
            else None
        )
        points.append(
            {
                "date": observation["asOf"],
                "value": item["value"],
                "valueLabel": item["valueLabel"],
                "status": item["status"],
                "statusLabel": item["statusLabel"],
                "reasons": item["reasons"],
                "detailId": observation["detailId"],
                "snapshotId": observation["snapshotId"],
                "x": x,
                "y": y,
            }
        )
        if y is None or (previous is not None and (point_date - previous).days > 100):
            if segment:
                paths.append(" ".join(segment))
            segment = []
        if y is not None:
            segment.append(f"{'M' if not segment else 'L'} {x} {y}")
        previous = point_date
    if segment:
        paths.append(" ".join(segment))
    return {
        "points": points,
        "paths": paths,
        "unavailableDates": [point["date"] for point in points if point["y"] is None],
        "emptyReason": None
        if any(point["y"] is not None for point in points)
        else ("No eligible company observations are supplied for this metric in this window."),
        "xAxis": {
            "ticks": [
                {"position": 60, "label": start.isoformat()},
                {"position": 730, "label": end.isoformat()},
            ],
            "zero": 60,
        },
        "yAxis": axis(limits, metric["unit"], 245, 25),
    }


def export(raw: Row) -> Row:
    with localcontext(Context(prec=4096, Emin=-9999, Emax=9999)):
        return _export(raw)


def _export(raw: Row) -> Row:
    if raw.get("fictional") is not True:
        raise ValueError("Only explicitly fictional data may enter this Company artifact")
    metrics = [
        {**item, "id": METRIC_IDS[item["id"]]}
        for item in raw["metrics"]
        if item["id"] in METRIC_IDS
    ]
    sectors = {item["id"]: item for item in raw["sectors"]}
    records: dict[tuple[str, str, str], Row] = {}
    identities: dict[tuple[str, str], Row] = {}
    companies: dict[str, Row] = {}
    details = {}
    for evaluation in raw["evaluations"]:
        if evaluation["metricId"] not in METRIC_IDS:
            continue
        metric_id = METRIC_IDS[evaluation["metricId"]]
        as_of = evaluation["asOf"]
        for record in evaluation["companies"]:
            key = (as_of, record["id"], metric_id)
            if key in records and records[key] != record:
                raise ValueError("Conflicting company observations in repeated sector projections")
            detail = raw["details"].get(record["detailId"])
            validate_detail(record, detail, metric_id, as_of)
            records[key] = record
            identity = {
                key: record[key] for key in ("id", "ticker", "name", "snapshotId", "detailId")
            }
            snapshot_key = (as_of, record["id"])
            if snapshot_key in identities and identities[snapshot_key] != identity:
                raise ValueError("Conflicting company snapshot identities across metrics")
            identities[snapshot_key] = identity
            details[record["detailId"]] = detail
            sector = sectors[evaluation["sectorId"]]
            parent = sectors[sector["parentId"]] if "parentId" in sector else sector
            company = {
                **{key: record[key] for key in ("id", "ticker", "name")},
                "sectorId": parent["id"],
                "sectorLabel": parent["label"],
            }
            if record["id"] in companies and companies[record["id"]] != company:
                raise ValueError("Conflicting company identity or fictional sector membership")
            companies[record["id"]] = company
    observations = []
    for (as_of, company_id), identity in sorted(identities.items()):
        metric_map = {}
        for metric in metrics:
            record = records.get((as_of, company_id, metric["id"]))
            state = record["status"] if record else "missing"
            codes = record["reasons"] if record else ["company_metric_not_supplied"]
            value = record["value"] if record else None
            metric_map[metric["id"]] = {
                **metric,
                "value": value,
                "valueLabel": label(value, metric["unit"], state),
                "status": state,
                "statusLabel": STATUS[state],
                "reasons": reasons(codes, metric["id"]),
                "reasonCodes": codes,
                "detailId": identity["detailId"],
            }
        observations.append(
            {
                "asOf": as_of,
                "companyId": company_id,
                "snapshotId": identity["snapshotId"],
                "detailId": identity["detailId"],
                "metrics": list(metric_map.values()),
                "metricMap": metric_map,
                "amounts": source_amounts(details[identity["detailId"]], identity["detailId"]),
            }
        )
    views = {}
    for observation in observations:
        histories = {}
        for years in (3, 5, 10):
            start, end, expected = calendar_window(observation["asOf"], years)
            selected = [
                item
                for item in observations
                if item["companyId"] == observation["companyId"]
                and start.isoformat() < item["asOf"] <= end.isoformat()
            ]
            supplied_dates = [item["asOf"] for item in selected]
            missing = [point for point in expected if point not in supplied_dates]
            histories[str(years)] = {
                "windowStart": start.isoformat(),
                "windowEnd": end.isoformat(),
                "coverageLabel": (
                    f"{len(supplied_dates)} of {len(expected)} quarter-end snapshots available"
                ),
                "availableDates": supplied_dates,
                "missingDates": missing,
                "note": (
                    "Requested window; only supplied company snapshots are plotted. "
                    "Missing quarters remain gaps. Sector histories are not company histories. "
                    "Percentile and rank "
                    "comparisons are unavailable in this limited demonstration."
                ),
                "charts": {
                    metric["id"]: history_chart(selected, metric, start, end) for metric in metrics
                },
            }
        view = {key: value for key, value in observation.items() if key != "metricMap"}
        view["history"] = histories
        view["id"] = hashlib.sha256(
            json.dumps(view, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        views[observation["asOf"] + "|" + observation["companyId"]] = view
    return {
        "fictional": True,
        "context": {
            **raw["context"],
            "title": "Company Fundamentals",
            "defaultCompanyId": next(iter(companies), None),
            "historyNote": (
                "The frozen Sector Explorer bundle supplies company details for two dates only; "
                "3/5/10-year selections expose incomplete history, not invented historical values."
            ),
        },
        "companies": list(companies.values()),
        "metrics": metrics,
        "views": views,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = export(json.loads(args.input.read_text()))
    content = (json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(gzip.compress(content, mtime=0))
    print(f"Exported {len(result['views'])} fictional company presentation views to {args.output}")


if __name__ == "__main__":
    main()
