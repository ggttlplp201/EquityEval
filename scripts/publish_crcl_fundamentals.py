"""D048 exact reviewed real S6 candidate, fenced W1 publication and readback."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
from equity_core.real_fundamentals import calculate_payload
from equity_ingest.archive import LocalArchive
from equity_ingest.real_fundamentals_pipeline import run_fundamentals_stage
from equity_schema.fundamentals_canonical import canonical_json, content_hash
from equity_schema.real_fundamentals import RealFundamentalsPayload, RealInputManifest
from equity_schema.real_fundamentals_store import (
    approve_real_manifest,
    claim_real_fundamentals,
    compatibility_key,
    engine_revision,
    enqueue_fundamentals,
    get_latest,
    get_snapshot,
)
from equity_schema.workflow import _invoke
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from scripts import app_postgres
from scripts.normalize_crcl import ROOT
from scripts.prepare_crcl_fundamentals import application_candidate
from scripts.publish_crcl_normalization import rows_snapshot

PREPARATION = "docs/research/crcl-fundamentals-preparation-2026-10-15-r3.json"
PREPARATION_SHA = "6d10a6ed9f9770ccb246dfc211de00bd2fe19c51acd197db2d5d526eb54545d8"
MANIFEST_HASH = "1fa24dc52392e29aad1db306500db81b76f8ab9e3e6f8282496a02daaebc24e9"
PAYLOAD_HASH = "4042d892477467e07c906091cb30e70aeb264ed9c1adb3df75e351828ffa23db"
PUBLICATION = "docs/research/crcl-fundamentals-publication-2026-10-15.json"
INTENT = "docs/research/crcl-fundamentals-publication-intent-2026-10-15.json"
REQUEST_KEY = "d5j-crcl-fy2025-real-fundamentals-v1"
WORKSPACE = UUID("33f9d092-93e6-46ee-b851-fcbd7b4993fd")
ALLOWED_ADDITIONS = frozenset(
    {
        "analysis_requests",
        "analysis_request_keys",
        "analysis_request_state",
        "analysis_executions",
        "analysis_stage_attempts",
        "execution_events",
        "latest_real_fundamentals",
    }
)


def checked_candidate(root: Path = ROOT) -> tuple[RealInputManifest, RealFundamentalsPayload]:
    raw = (root / PREPARATION).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PREPARATION_SHA:
        raise ValueError("Pinned real preparation changed")
    report = json.loads(raw)
    manifest = RealInputManifest.model_validate(report["manifest"])
    payload = RealFundamentalsPayload.model_validate(report["payload"])
    if (
        content_hash(manifest) != MANIFEST_HASH
        or content_hash(payload) != PAYLOAD_HASH
        or content_hash(calculate_payload(manifest, history_payloads={})) != PAYLOAD_HASH
    ):
        raise ValueError("Real candidate differs from reviewed input/output")
    return manifest, payload


def verify_preserved(before: dict[str, list[str]], after: dict[str, list[str]]) -> None:
    if before.keys() != after.keys():
        raise ValueError("Publication must not alter schema")
    for table, hashes in before.items():
        allowed = table in ALLOWED_ADDITIONS or table.startswith("real_fundamentals_")
        if not set(hashes).issubset(after[table]) or (not allowed and hashes != after[table]):
            raise ValueError(f"Publication changed retained rows: {table}")


def _write_exclusive(path: Path, report: dict[str, Any]) -> None:
    """Durable, atomic, never-overwriting local evidence publication."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + str(uuid4()))
    try:
        with temporary.open("x") as output:
            output.write(canonical_json(report) + "\n")
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def write_audit(path: Path, report: dict[str, Any]) -> None:
    _write_exclusive(path, report)


def original_baseline(before: dict[str, list[str]], *, create: bool) -> dict[str, list[str]]:
    path = ROOT / INTENT
    identity = {
        "manifestHash": MANIFEST_HASH,
        "payloadHash": PAYLOAD_HASH,
        "workspaceId": str(WORKSPACE),
        "requestKey": REQUEST_KEY,
    }
    if not path.exists():
        if not create:
            raise ValueError("Missing original publication preservation intent")
        _write_exclusive(path, {**identity, "beforeRows": before})
    saved = json.loads(path.read_bytes())
    if any(saved.get(key) != value for key, value in identity.items()):
        raise ValueError("Publication intent differs from pinned candidate")
    baseline: dict[str, list[str]] = saved["beforeRows"]
    verify_preserved(baseline, before)
    return baseline


def application(action: str) -> dict[str, Any]:
    manifest, payload = checked_candidate()
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    target = ROOT / PUBLICATION
    if action == "publish" and target.exists():
        raise ValueError("Publication audit exists; use read-only verify")
    with app_postgres.owner_connection(runtime, runtime.database) as owner:
        owner.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", ("d5j-real-publication",))
        version = owner.execute("SELECT version_num FROM alembic_version").fetchone()
        head = version["version_num"] if version else None
        if head != "0013_real_fundamentals":
            raise ValueError("Reviewed sequential application migration is required first")
        before = rows_snapshot(owner)
        if action in {"preflight", "publish"}:
            if manifest.selector.engine_revision != engine_revision():
                raise ValueError("Pinned engine changed; new independent review required")
            current = application_candidate(manifest.selector.evaluated_at)
            if current["manifestHash"] != MANIFEST_HASH or current["payloadHash"] != PAYLOAD_HASH:
                raise ValueError("Current retained readback differs from pinned candidate")
        if action == "preflight":
            return {
                "kind": "d5j-real-preflight",
                "ready": True,
                "manifestHash": MANIFEST_HASH,
                "payloadHash": PAYLOAD_HASH,
                "beforeRows": before,
                "operatingMargin": None,
            }
        baseline = original_baseline(before, create=action == "publish")
        recovered = False
        if action == "publish":
            review = approve_real_manifest(
                owner,
                workspace_id=WORKSPACE,
                manifest=manifest,
                archive=LocalArchive(ROOT / "var/raw"),
                reviewed_by="D048 independent standards/spec/numeric review",
                reason=(
                    "Pinned D5i FY2025 signed operating margin; nine unresolved metrics; "
                    "exact observation cutoff"
                ),
            )
            with psycopg.connect(
                url.set(drivername="postgresql").render_as_string(hide_password=False),
                autocommit=True,
                row_factory=dict_row,
            ) as db:
                request = enqueue_fundamentals(
                    db,
                    workspace_id=WORKSPACE,
                    review_id=review,
                    idempotency_key=REQUEST_KEY,
                )
                committed = db.execute(
                    "SELECT id,lease_identity,stage_id,input_snapshot_id "
                    "FROM real_fundamentals_snapshots WHERE request_id=%s",
                    (request.request_id,),
                ).fetchone()
                if committed:
                    # A successful request is intentionally unclaimable. Replay its
                    # exact saved identity rather than creating a replacement request.
                    snapshot_id = committed["id"]
                    replay = _invoke(
                        db,
                        "SELECT real_fundamentals_publish(%s,%s,%s,%s) AS result",
                        (
                            Jsonb(committed["lease_identity"]),
                            committed["stage_id"],
                            committed["input_snapshot_id"],
                            canonical_json(payload),
                        ),
                    )
                    recovered = True
                else:
                    lease = claim_real_fundamentals(
                        db, worker_id="d5j-reviewed-real-worker", request_id=request.request_id
                    )
                    if lease is None:
                        raise ValueError(
                            "No eligible dedicated real lease; inspect existing request"
                        )
                    snapshot_id = run_fundamentals_stage(db, lease)
                    replay = run_fundamentals_stage(db, lease)
                if str(snapshot_id) != str(replay):
                    raise ValueError("Real publication exact replay differs")
                again = enqueue_fundamentals(
                    db,
                    workspace_id=WORKSPACE,
                    review_id=review,
                    idempotency_key=REQUEST_KEY,
                )
                if again.request_id != request.request_id:
                    raise ValueError("Real request replay differs")
        else:
            prior = json.loads(target.read_bytes())
            snapshot_id = UUID(prior["snapshot"]["snapshot_id"])
        saved = get_snapshot(owner, workspace_id=WORKSPACE, snapshot_id=snapshot_id)
        latest = get_latest(
            owner,
            workspace_id=WORKSPACE,
            issuer_id=manifest.selector.issuer_id,
            security_id=manifest.selector.security_id,
            compatibility_key=compatibility_key(manifest),
        )
        if (
            saved is None
            or saved.payload_hash != PAYLOAD_HASH
            or saved.result != payload
            or latest is None
            or latest[0] != saved
            or latest[2] != "completed_with_gaps"
        ):
            raise ValueError("Saved real API readback differs from independently reviewed result")
        after = rows_snapshot(owner)
        verify_preserved(baseline, after)
        if action == "verify" and before != after:
            raise ValueError("Read-only verification changed rows")
        report = {
            "kind": "d5j-real-fundamentals-publication",
            "manifestHash": MANIFEST_HASH,
            "payloadHash": PAYLOAD_HASH,
            "snapshot": saved,
            "sourceObservation": manifest.selector.captured_before,
            "evaluatedAt": manifest.selector.evaluated_at,
            "beforeRows": baseline,
            "afterRows": after,
            "priorRowsPreserved": True,
            "exactReplay": True if action == "publish" else prior["exactReplay"],
            "recoveredCommittedSnapshot": recovered
            if action == "publish"
            else prior["recoveredCommittedSnapshot"],
            "intentHash": hashlib.sha256((ROOT / INTENT).read_bytes()).hexdigest(),
            "normalizationBatchIds": tuple(
                str(b) for b in manifest.sources[0].selection.query.batch_ids
            ),
        }
        if action == "publish":
            write_audit(target, report)
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "publish", "verify"))
    args = parser.parse_args()
    report = application(args.action)
    print(canonical_json({k: report[k] for k in ("kind", "manifestHash", "payloadHash")}))


if __name__ == "__main__":
    main()
