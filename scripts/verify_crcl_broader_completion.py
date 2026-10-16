"""Read-only D049 audit-chain verification after both separately governed publications."""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any
from uuid import UUID

from equity_schema.fundamentals_canonical import canonical_json, content_hash
from equity_schema.real_fundamentals_store import get_snapshot

from scripts import app_postgres
from scripts.export_crcl_broader import PUBLICATION_HASHES, SOURCE_PUBLICATION_SHA
from scripts.normalize_crcl import ROOT, load_preparation
from scripts.publish_crcl_broader import PUBLICATION, checked_preparation, readback
from scripts.publish_crcl_broader_fundamentals import PINS, WORKSPACE
from scripts.publish_crcl_fundamentals import PAYLOAD_HASH as D5J_PAYLOAD
from scripts.publish_crcl_normalization import readback as historical_readback
from scripts.publish_crcl_normalization import rows_snapshot, verify_preserved
from scripts.publish_crcl_observation import checked_preparation as prior_preparation
from scripts.publish_crcl_observation import readback as prior_readback

OUTPUT = "docs/research/crcl-broader-completion-2026-10-15.json"


def verify() -> dict[str, Any]:
    audits = []
    hashes = []
    for path, digest in [(PUBLICATION, SOURCE_PUBLICATION_SHA)] + [
        (PINS[b].publication, PUBLICATION_HASHES[b]) for b in ("annual", "instant")
    ]:
        raw = (ROOT / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Immutable publication audit changed")
        audits.append(json.loads(raw))
        hashes.append({"path": path, "sha256": digest})
    source, annual, instant = audits
    verify_preserved(source["beforeRows"], source["afterRows"])
    if annual["beforeRows"] != source["afterRows"] or instant["beforeRows"] != annual["afterRows"]:
        raise ValueError("Separately governed publication preservation chain differs")
    from scripts.publish_crcl_fundamentals import verify_preserved as verify_real

    verify_real(annual["beforeRows"], annual["afterRows"])
    verify_real(instant["beforeRows"], instant["afterRows"])
    bundle, _ = checked_preparation()
    old, _ = load_preparation()
    prior, _ = prior_preparation()
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as db:
        db.execute("SET default_transaction_read_only=on")
        before = rows_snapshot(db)
        if before != instant["afterRows"]:
            raise ValueError("Application differs from completed bounded publication chain")
        new_readback = readback(db, bundle, UUID(source["batch"]["id"]))
        batches = {
            r["input_manifest_hash"]: r["id"]
            for r in db.execute(
                "SELECT id,input_manifest_hash FROM normalization_batches"
            ).fetchall()
        }
        if canonical_json(
            historical_readback(db, old, batches[old.input_manifest_hash])
        ) != canonical_json(source["historicalSelection"]):
            raise ValueError("Historical D5a selection changed")
        if canonical_json(
            prior_readback(db, prior, batches[prior.input_manifest_hash])
        ) != canonical_json(source["priorSelection"]):
            raise ValueError("D5i selection changed")
        old_snapshot = get_snapshot(
            db, workspace_id=WORKSPACE, snapshot_id=UUID("1a259fc4-7395-4111-939b-30c58919e230")
        )
        if old_snapshot is None or old_snapshot.payload_hash != D5J_PAYLOAD:
            raise ValueError("Original D5j snapshot changed")
        snapshots = []
        for report in (annual, instant):
            saved = get_snapshot(
                db, workspace_id=WORKSPACE, snapshot_id=UUID(report["snapshot"]["snapshot_id"])
            )
            if saved is None or saved.payload_hash != report["payloadHash"]:
                raise ValueError("Published pair readback differs")
            snapshots.append(str(saved.snapshot_id))
        counts = {}
        for table in (
            "source_captures",
            "source_fetch_attempts",
            "analysis_requests",
            "normalization_batches",
            "fact_resolutions",
            "real_fundamentals_snapshots",
        ):
            row = db.execute(f"SELECT count(*) AS n FROM {table}").fetchone()
            if row is None:
                raise ValueError("Completion count unavailable")
            counts[table] = row["n"]
        if rows_snapshot(db) != before:
            raise ValueError("Read-only completion verification changed rows")
    return {
        "kind": "d5k-completion-verification",
        "auditChain": hashes,
        "currentRowsHash": content_hash(before),
        "sourceReadbackHash": content_hash(new_readback),
        "priorRowsPreserved": True,
        "historicalD5aFlagsPreserved": True,
        "d5iSelectionPreserved": True,
        "d5jPayloadHash": D5J_PAYLOAD,
        "snapshotIds": snapshots,
        "counts": counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = verify()
    value = canonical_json(report) + "\n"
    path = ROOT / OUTPUT
    if args.check:
        if path.read_text() != value:
            raise ValueError("Completion verification differs")
    else:
        from scripts.publish_crcl_fundamentals import _write_exclusive

        _write_exclusive(path, report)
    print(canonical_json(report))


if __name__ == "__main__":
    main()
