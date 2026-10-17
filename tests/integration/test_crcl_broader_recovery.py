"""D049 paired publication retains commit-before-audit recovery and old snapshots."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from equity_core.real_fundamentals import calculate_payload
from equity_ingest.archive import LocalArchive
from equity_schema.fundamentals_canonical import content_hash
from sqlalchemy.engine import make_url

from tests.integration.test_real_fundamentals_publication import (  # noqa: F401
    real_setup,  # noqa: F811
    retained_bundle,
)

pytestmark = pytest.mark.integration


def test_broader_publisher_recovers_without_replacing_committed_snapshot(
    real_setup,  # noqa: F811
    db_admin,
    test_database_dsn,
    tmp_path,
    monkeypatch,  # noqa: F811
):
    from alembic import command

    from scripts import publish_crcl_broader_fundamentals as publisher
    from scripts.normalize_crcl import ROOT
    from tests.conftest import migration_config

    # Replay the original D5k publication boundary; its frozen publisher requires 0013.
    command.downgrade(migration_config(test_database_dsn), "0013_real_fundamentals")
    workspace, manifest, _ = real_setup
    payload = calculate_payload(manifest, history_payloads={})
    pin = publisher.PublicationPin(
        preparation="candidate.json",
        preparation_sha="0" * 64,
        manifest_hash=content_hash(manifest),
        payload_hash=content_hash(payload),
        publication="annual-publication.json",
        intent="annual-intent.json",
        request_key="d5k-test-annual",
    )
    monkeypatch.setattr(publisher, "ROOT", tmp_path)
    monkeypatch.setattr(publisher, "WORKSPACE", workspace.workspace_id)
    monkeypatch.setattr(publisher, "PINS", {"annual": pin})
    monkeypatch.setattr(publisher, "checked_candidate", lambda _: (manifest, payload))
    monkeypatch.setattr(
        publisher,
        "application_candidate",
        lambda *_: {
            "manifestHash": content_hash(manifest),
            "payloadHash": content_hash(payload),
        },
    )
    monkeypatch.setattr(publisher, "LocalArchive", lambda _: LocalArchive(ROOT / "var/raw"))
    monkeypatch.setattr(
        publisher.app_postgres,
        "configuration",
        lambda: (
            SimpleNamespace(database="test"),
            make_url(test_database_dsn),
        ),
    )
    monkeypatch.setattr(publisher.app_postgres, "guard", lambda _: None)
    monkeypatch.setattr(publisher.app_postgres, "verify", lambda _: None)

    @contextmanager
    def owner(*args):
        yield db_admin

    monkeypatch.setattr(publisher.app_postgres, "owner_connection", owner)
    original = publisher.write_audit

    def interrupted(*args):
        raise InterruptedError("after commit, before audit")

    monkeypatch.setattr(publisher, "write_audit", interrupted)
    with pytest.raises(InterruptedError):
        publisher.application("publish", "annual")
    assert (tmp_path / pin.intent).exists()
    assert not (tmp_path / pin.publication).exists()
    monkeypatch.setattr(publisher, "write_audit", original)
    result = publisher.application("publish", "annual")
    assert result["recoveredCommittedSnapshot"] and result["priorRowsPreserved"]
    assert (
        db_admin.execute("SELECT count(*) AS n FROM real_fundamentals_snapshots").fetchone()["n"]
        == 1
    )
    assert db_admin.execute("SELECT count(*) AS n FROM analysis_requests").fetchone()["n"] == 1
    assert publisher.application("verify", "annual")["payloadHash"] == pin.payload_hash
    with pytest.raises(ValueError, match="pinned"):
        publisher.application("publish", "instant")


def test_two_broader_snapshots_publish_through_existing_fences_and_preserve_d5j(
    real_setup,  # noqa: F811
    db_admin,
    db,  # noqa: F811
):
    from datetime import UTC, datetime

    from equity_ingest.publisher import publish_bundle
    from equity_ingest.real_fundamentals_pipeline import run_fundamentals_stage
    from equity_schema.real_fundamentals_store import (
        approve_real_manifest,
        claim_real_fundamentals,
        enqueue_fundamentals,
        get_snapshot,
    )

    from scripts.normalize_crcl import ROOT
    from scripts.prepare_crcl_broader import prepare
    from scripts.prepare_crcl_broader_fundamentals import build_manifest
    from scripts.publish_crcl_broader import register_mapping

    workspace, old_manifest, old_review = real_setup

    def publish(review, key):
        request = enqueue_fundamentals(
            db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key=key
        )
        lease = claim_real_fundamentals(
            db, worker_id="disposable-d5k", request_id=request.request_id
        )
        assert lease is not None
        result = run_fundamentals_stage(db, lease)
        assert run_fundamentals_stage(db, lease) == result
        return result

    old_id = publish(old_review, "preserved-d5j")
    before = get_snapshot(db, workspace_id=workspace.workspace_id, snapshot_id=old_id)
    bundle, proof = prepare()
    register_mapping(db_admin, bundle)
    batch = publish_bundle(db, bundle)
    ids = []
    for basis, valid in (("annual", 4), ("instant", 2)):
        manifest = build_manifest(
            db,
            bundle=bundle,
            proof=proof,
            batch_id=batch.batch_id,
            security_id=old_manifest.selector.security_id,
            evaluated_at=datetime(2026, 10, 16, 1, tzinfo=UTC),
            period_basis=basis,
        )
        review = approve_real_manifest(
            db_admin,
            workspace_id=workspace.workspace_id,
            manifest=manifest,
            archive=LocalArchive(ROOT / "var/raw"),
            reviewed_by="disposable-d5k",
            reason="Exact separately scoped selector test",
        )
        snapshot_id = publish(review, "new-d5k-" + basis)
        saved = get_snapshot(db, workspace_id=workspace.workspace_id, snapshot_id=snapshot_id)
        assert saved.result == calculate_payload(manifest, history_payloads={})
        assert saved.result.coverage.counts["valid"] == valid
        from dataclasses import asdict

        from scripts.export_crcl_broader import project_result
        from scripts.publish_crcl_broader_fundamentals import PublicationPin

        pin = PublicationPin(
            "unused",
            "0" * 64,
            content_hash(manifest),
            saved.payload_hash,
            "unused",
            "unused",
            "test",
        )
        publication = {
            "snapshot": saved.model_dump(mode="json"),
            "manifestHash": pin.manifest_hash,
            "priorRowsPreserved": True,
            "exactReplay": True,
        }
        view = project_result(
            {"manifest": manifest.model_dump(mode="json")},
            publication,
            {str(c.id): asdict(c) for c in bundle.inputs.captures},
            pin,
            basis,
        )
        assert len(view["metrics"]) == valid and len(view["gaps"]) == 10 - valid
        assert all(view["details"][m["id"]]["sources"] for m in view["metrics"])
        publication["snapshot"]["payload_hash"] = "0" * 64
        with pytest.raises(ValueError):
            project_result(
                {"manifest": manifest.model_dump(mode="json")},
                publication,
                {str(c.id): asdict(c) for c in bundle.inputs.captures},
                pin,
                basis,
            )
        ids.append(snapshot_id)
    assert len({old_id, *ids}) == 3
    assert get_snapshot(db, workspace_id=workspace.workspace_id, snapshot_id=old_id) == before
