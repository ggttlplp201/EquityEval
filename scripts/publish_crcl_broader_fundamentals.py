"""D049 reviewed annual/instant candidates with fenced publication and readback."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

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
from scripts.prepare_crcl_broader_fundamentals import application_candidate
from scripts.publish_crcl_fundamentals import _write_exclusive, verify_preserved
from scripts.publish_crcl_normalization import rows_snapshot


@dataclass(frozen=True)
class PublicationPin:
    preparation: str
    preparation_sha: str
    manifest_hash: str
    payload_hash: str
    publication: str
    intent: str
    request_key: str


# Exact candidates staged for independent review; live publication requires clearance.
PINS: dict[str, PublicationPin] = {
    "annual": PublicationPin(
        preparation="docs/research/crcl-broader-annual-candidate-2026-10-15.json",
        preparation_sha="a0442da2caddab240c5ccfa7eb6c4f795c17cad948a64db89ce5d3f7dcef35a9",
        manifest_hash="19000a8621a73860125099ef6f1fbf3102f5c700f2aa10afa83b8e29bf7b8251",
        payload_hash="e147886c832645ab5c933168da3146147f06d0784067759f841dbf87918ba1a2",
        publication="docs/research/crcl-broader-annual-publication-2026-10-15.json",
        intent="docs/research/crcl-broader-annual-intent-2026-10-15.json",
        request_key="d5k-crcl-fy2025-annual-v1",
    ),
    "instant": PublicationPin(
        preparation="docs/research/crcl-broader-instant-candidate-2026-10-15.json",
        preparation_sha="846d5927e0ee25826cadc3ab589875b0901b73da0738b7efb8e392510806755f",
        manifest_hash="40e08d1412dee2faaea0afd86db560e6be428fd041122074944645a53b96bade",
        payload_hash="dc881fc1c1ed7ea12caf455c7963f7c6d355da02c6e4e58fd1c297d677d557eb",
        publication="docs/research/crcl-broader-instant-publication-2026-10-15.json",
        intent="docs/research/crcl-broader-instant-intent-2026-10-15.json",
        request_key="d5k-crcl-fy2025-instant-v1",
    ),
}
WORKSPACE = UUID("33f9d092-93e6-46ee-b851-fcbd7b4993fd")


def checked_candidate(
    pin: PublicationPin, root: Path = ROOT
) -> tuple[RealInputManifest, RealFundamentalsPayload]:
    raw = (root / pin.preparation).read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin.preparation_sha:
        raise ValueError("Pinned real preparation changed")
    report = json.loads(raw)
    manifest = RealInputManifest.model_validate(report["manifest"])
    payload = RealFundamentalsPayload.model_validate(report["payload"])
    if (
        content_hash(manifest) != pin.manifest_hash
        or content_hash(payload) != pin.payload_hash
        or content_hash(calculate_payload(manifest, history_payloads={})) != pin.payload_hash
    ):
        raise ValueError("Real candidate differs from reviewed input/output")
    return manifest, payload


def write_audit(path: Path, report: dict[str, Any]) -> None:
    _write_exclusive(path, report)


def original_baseline(
    before: dict[str, list[str]], pin: PublicationPin, *, create: bool
) -> dict[str, list[str]]:
    path = ROOT / pin.intent
    identity = {
        "manifestHash": pin.manifest_hash,
        "payloadHash": pin.payload_hash,
        "workspaceId": str(WORKSPACE),
        "requestKey": pin.request_key,
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


def application(action: str, basis: Literal["annual", "instant"]) -> dict[str, Any]:
    if action not in {"preflight", "publish", "verify"} or basis not in PINS:
        raise ValueError("Exact reviewed result is not pinned")
    pin = PINS[basis]
    manifest, payload = checked_candidate(pin)
    if manifest.selector.period_basis != basis:
        raise ValueError("Pinned selector differs from requested result")
    runtime, url = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    target = ROOT / pin.publication
    if action == "publish" and target.exists():
        raise ValueError("Publication audit exists; use read-only verify")
    with app_postgres.owner_connection(runtime, runtime.database) as owner:
        owner.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", ("d5k-real-publication",))
        version = owner.execute("SELECT version_num FROM alembic_version").fetchone()
        head = version["version_num"] if version else None
        if head != "0013_real_fundamentals":
            raise ValueError("Reviewed sequential application migration is required first")
        before = rows_snapshot(owner)
        if action in {"preflight", "publish"}:
            if manifest.selector.engine_revision != engine_revision():
                raise ValueError("Pinned engine changed; new independent review required")
            current = application_candidate(manifest.selector.evaluated_at, basis)
            if (
                current["manifestHash"] != pin.manifest_hash
                or current["payloadHash"] != pin.payload_hash
            ):
                raise ValueError("Current retained readback differs from pinned candidate")
        if action == "preflight":
            return {
                "kind": "d5k-real-preflight",
                "ready": True,
                "manifestHash": pin.manifest_hash,
                "payloadHash": pin.payload_hash,
                "beforeRows": before,
                "operatingMargin": None,
            }
        baseline = original_baseline(before, pin, create=action == "publish")
        recovered = False
        if action == "publish":
            review = approve_real_manifest(
                owner,
                workspace_id=WORKSPACE,
                manifest=manifest,
                archive=LocalArchive(ROOT / "var/raw"),
                reviewed_by="D049 independent standards/spec/numeric review",
                reason=(
                    "Pinned D5k FY2025 reported fundamentals with explicit period-scope gaps; "
                    "bounded D5i source observation and preserved prior result"
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
                    idempotency_key=pin.request_key,
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
                        db, worker_id="d5k-reviewed-real-worker", request_id=request.request_id
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
                    idempotency_key=pin.request_key,
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
            or saved.payload_hash != pin.payload_hash
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
            "kind": "d5k-real-fundamentals-publication",
            "manifestHash": pin.manifest_hash,
            "payloadHash": pin.payload_hash,
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
            "intentHash": hashlib.sha256((ROOT / pin.intent).read_bytes()).hexdigest(),
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
    parser.add_argument("basis", choices=("annual", "instant"))
    args = parser.parse_args()
    report = application(args.action, args.basis)
    print(canonical_json({k: report[k] for k in ("kind", "manifestHash", "payloadHash")}))


if __name__ == "__main__":
    main()
