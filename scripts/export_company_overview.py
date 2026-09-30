"""Checked, metadata-only linkage between separate fictional research workspaces."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "apps/web/src/features"
OUTPUT = FEATURES / "company/overview.json"
FILES = {
    "overview": "company/fixture.json.gz",
    "financials": "financials/fixture.json",
    "fundamentals": "fundamentals/fixture.json",
    "valuation": "valuation/fixture.json",
}
FIELDS = (
    "issuer_id",
    "security_id",
    "currency",
    "as_of",
    "evaluated_at",
    "known_at",
    "retrieved_at",
    "scope",
    "lineage",
)
DESTINATIONS = {
    "financials": ("Financials", "/development/company/financials"),
    "fundamentals": ("Fundamentals", "/development/company/ratios"),
    "valuation": ("Reverse DCF", "/development/valuation"),
}


def encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def complete(value: Any) -> bool:
    """Affirmative metadata has nonmissing string leaves; never normalize evidence.

    N/A is the presentation boundary's missing marker (case/whitespace variants
    included). Other literal strings retain exact equality in classify().
    Tuples occur in the exporter's scope projection before JSON serialization.
    """
    if isinstance(value, str):
        marker = value.strip()
        return bool(marker) and marker.casefold() != "n/a"
    if isinstance(value, dict):
        return bool(value) and all(complete(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return bool(value) and all(complete(item) for item in value)
    return False


def classify(left: dict[str, Any], right: dict[str, Any] | None) -> tuple[str, list[str]]:
    if right is None:
        return "unavailable", ["destination_missing"]
    reasons = []
    for field in FIELDS:
        if not complete(left.get(field)) or not complete(right.get(field)):
            reasons.append(f"{field}: proof unavailable")
        elif left[field] != right[field]:
            reasons.append(f"{field}: mismatch")
    return ("separate" if reasons else "compatible"), reasons


def only(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != 1:
        raise ValueError("Expected exactly one destination default")
    return rows[0]


def descriptor(payload: dict[str, Any], **metadata: Any) -> dict[str, Any]:
    return {
        **dict.fromkeys(FIELDS),
        "local_payload_sha256": digest(encoded(payload)),
        "local_payload_hash_method": "SHA256 of sorted indent=2 UTF-8 JSON plus newline",
        **metadata,
    }


def destination(key: str, bundle: dict[str, Any]) -> dict[str, Any]:
    if key == "financials":
        row = only(
            [
                r
                for r in bundle["snapshots"]
                if r["edition"] == "annual_original" and r["basis"] == "annual"
            ]
        )
        return descriptor(
            row,
            issuer_id=row["issuer_id"],
            currency=row["currency"],
            known_at=row["known_on"],
            retrieved_at=row["retrieved_at"],
            scope=row["scope"],
            lineage={"snapshot_id": row["snapshot_id"], "input_hash": row["input_hash"]},
            name=row["company"],
            snapshot_id=row["snapshot_id"],
            filed_on=row["filed_on"],
            declared={
                k: row[k]
                for k in ("source_id", "input_hash", "payload_hash", "history_mode", "supersedes")
            },
            selector={"basis": "annual", "edition": "annual_original"},
        )
    if key == "fundamentals":
        choice = only([r for r in bundle["examples"] if r["id"] == "reference"])
        row = only(
            [
                r
                for r in bundle["snapshots"]
                if r["example"] == "reference"
                and r["years"] == 3
                and r["payload"]["selector"]["as_of"] == choice["dates"][-1]
            ]
        )
        payload = row["payload"]
        s = payload["selector"]
        evidence = payload["evidence"]
        return descriptor(
            payload,
            **{k: s[k] for k in ("issuer_id", "security_id", "currency", "as_of", "evaluated_at")},
            retrieved_at=sorted({date for e in evidence for date in e["retrieved_at"]}),
            scope=sorted({(e["scope_kind"], e["scope_hash"]) for e in evidence}),
            lineage={
                "snapshot_id": row["snapshot_id"],
                "input_snapshot_id": row["input_snapshot_id"],
            },
            name=bundle["label"],
            snapshot_id=row["snapshot_id"],
            source_selector=s,
            source_metadata=[
                {
                    k: e[k]
                    for k in (
                        "source_hashes",
                        "filed_on",
                        "retrieved_at",
                        "scope_kind",
                        "scope_hash",
                        "source_url",
                    )
                }
                for e in evidence
            ],
            declared={"payload_hash": row["payload_hash"]},
            selector={"example": "reference", "date": s["as_of"], "years": "3"},
        )
    row = only([r for r in bundle["examples"] if r["id"] == "reference"])
    payload = row["payload"]
    s = payload["source_selector"]
    return descriptor(
        payload,
        **{k: s[k] for k in ("issuer_id", "security_id", "currency", "as_of", "evaluated_at")},
        lineage={
            "snapshot_id": payload["source_snapshot_id"],
            "input_hash": payload["source_input_hash"],
        },
        name="Reverse DCF fictional example",
        snapshot_id=payload["source_snapshot_id"],
        source_selector=s,
        valuation_at=payload["valuation_at"],
        bridge_captured_before=payload["bridge_captured_before"],
        price_source_known_at=payload["price"]["source_known_at"],
        declared={k: payload[k] for k in ("source_payload_hash", "source_input_hash")},
        selector={"example": "reference"},
    )


def build(features: Path = FEATURES) -> dict[str, Any]:
    files: dict[str, str | None] = {}
    bundles = {}
    for key, relative in FILES.items():
        path = features / relative
        if not path.exists() and key != "overview":
            files[relative] = None
            continue
        raw = path.read_bytes()
        files[relative] = digest(raw)
        bundle = json.loads(gzip.decompress(raw) if relative.endswith(".gz") else raw)
        if bundle.get("fictional") is not True:
            raise ValueError("Only explicitly fictional workspaces are supported")
        bundles[key] = bundle
    company = bundles["overview"]
    destinations = {key: destination(key, bundles[key]) for key in DESTINATIONS if key in bundles}
    for key, item in destinations.items():
        item["fixture"] = FILES[key]
        item["fixture_sha256"] = files[FILES[key]]
    entries = {}
    for view in company["views"].values():
        if view["id"] in entries:
            raise ValueError("Ambiguous Company view ID")
        issuer = only([r for r in company["companies"] if r["id"] == view["companyId"]])
        identity = descriptor(
            view,
            issuer_id=issuer["id"],
            name=issuer["name"],
            ticker=issuer["ticker"],
            currency=company["context"]["currency"],
            as_of=view["asOf"],
            scope=[
                {"label": a["label"], "basis": a["basis"], "period": a["period"]}
                for a in view["amounts"]
            ],
            lineage={
                "snapshot_id": view["snapshotId"],
                "source_snapshot_id": company["context"]["sourceSnapshotId"],
            },
            snapshot_id=view["snapshotId"],
            view_id=view["id"],
            fixture=FILES["overview"],
            fixture_sha256=files[FILES["overview"]],
            declared_capture_dates=[
                s["capturedAt"] for s in company["details"][view["detailId"]]["sources"]
            ],
        )
        cards = [
            {
                "id": "overview",
                "title": "Overview",
                "status": "ready",
                "statusLabel": "Ready · selected snapshot",
                "name": issuer["name"],
                "asOf": view["asOf"],
                "reasons": [],
                "href": "/development/company?"
                + urlencode({"company": issuer["id"], "asOf": view["asOf"]}),
                "navigationLabel": "Selected company and date",
            }
        ]
        for key, (title, href) in DESTINATIONS.items():
            target = destinations.get(key)
            status, reasons = classify(identity, target)
            compatible = status == "compatible"
            cards.append(
                {
                    "id": key,
                    "title": title,
                    "status": status,
                    "statusLabel": {
                        "compatible": "Compatible",
                        "separate": "Separate fictional example",
                        "unavailable": "N/A",
                    }[status],
                    "name": target["name"] if target else None,
                    "asOf": target.get("as_of") if target else None,
                    "reasons": reasons,
                    "href": (
                        href + "?" + urlencode(target["selector"])
                        if compatible and target
                        else href
                        if target
                        else None
                    ),
                    "navigationLabel": (
                        "Exact compatible selection"
                        if compatible
                        else "Opens its own default"
                        if target
                        else "N/A"
                    ),
                }
            )
        entries[view["id"]] = {
            "identity": identity,
            "cards": cards,
            "counts": {
                "ready": 1,
                "compatible": sum(c["status"] == "compatible" for c in cards),
                "separate": sum(c["status"] == "separate" for c in cards),
                "unavailable": sum(c["status"] == "unavailable" for c in cards),
            },
        }
    return {
        "version": "s8d-metadata-v1",
        "fictional": True,
        "files": files,
        "method": "Exact affirmative metadata equality; missing proof is never compatibility. "
        "Overview readiness applies only to its own saved snapshot. "
        "Capture cutoffs are not retrieval timestamps. Declared hashes are not local file digests.",
        "destinations": destinations,
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = encoded(build())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != result:
            raise SystemExit(
                "Overview manifest differs; run python -m scripts.export_company_overview"
            )
    else:
        OUTPUT.write_bytes(result)


if __name__ == "__main__":
    main()
