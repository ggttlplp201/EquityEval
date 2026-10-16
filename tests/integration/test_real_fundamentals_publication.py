"""Disposable real-v2 storage and W1 boundary regressions."""

import psycopg
import pytest

pytestmark = pytest.mark.integration


def test_companion_tables_and_original_synthetic_constraints(db_admin):
    names = [
        "policy_reviews",
        "policy_evidence",
        "input_reviews",
        "review_inputs",
        "review_captures",
        "review_history",
        "request_intents",
        "input_snapshots",
        "calculation_payloads",
        "snapshots",
    ]
    for name in names:
        assert db_admin.execute(
            "SELECT to_regclass(%s) AS name", ("real_fundamentals_" + name,)
        ).fetchone()["name"]
    assert db_admin.execute("SELECT to_regclass('latest_real_fundamentals') AS name").fetchone()[
        "name"
    ]
    constraints = db_admin.execute(
        "SELECT pg_get_constraintdef(oid) AS text FROM pg_constraint "
        "WHERE conrelid='fundamentals_input_reviews'::regclass"
    ).fetchall()
    assert any("synthetic" in row["text"] for row in constraints)


def test_real_runtime_cannot_insert_unreviewed_policy(db):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("INSERT INTO real_fundamentals_policy_reviews DEFAULT VALUES")


@pytest.fixture(scope="session")
def retained_bundle():
    from scripts.normalize_crcl import ROOT
    from scripts.prepare_crcl_observation import prepare
    from scripts.review_crcl_observation import retained_captures

    bundle, proof = prepare()
    return bundle, proof, {r["capture_id"]: r for r in retained_captures(ROOT)}


@pytest.fixture
def real_setup(retained_bundle, db_admin, db):
    from datetime import UTC, datetime
    from uuid import uuid4

    from equity_ingest.archive import LocalArchive
    from equity_ingest.publisher import publish_bundle
    from equity_schema.real_fundamentals_store import approve_real_manifest
    from equity_schema.workflow import create_workspace_watchlist

    from scripts.normalize_crcl import ROOT
    from scripts.prepare_crcl_fundamentals import build_manifest
    from scripts.publish_crcl_normalization import register_mapping
    from tests.evidence_seed import _insert_record, insert

    bundle, proof, rows = retained_bundle
    inputs = bundle.inputs
    insert(
        db_admin,
        "issuers",
        id=inputs.issuer_id,
        cik=inputs.cik,
        legal_name="Disposable CRCL evidence test",
        first_seen_at=inputs.captured_before,
    )
    security = uuid4()
    insert(
        db_admin,
        "securities",
        id=security,
        issuer_id=inputs.issuer_id,
        instrument_kind="common_equity",
    )
    source = inputs.captures[0].source_id
    insert(
        db_admin,
        "sources",
        id=source,
        source_key=str(source),
        name="Disposable retained SEC fixture",
        base_url="https://www.sec.gov",
        terms_review_reference="test-only",
        content_scope="Retained source fixture",
    )
    # Retained S3 SEC policy, without inventing S4 market capability rows.
    policy_id = uuid4()
    _insert_record(
        db_admin,
        "source_policy_revisions",
        id=policy_id,
        source_id=source,
        review_key="sec-public-filings-2026-09-21",
        licence_label="SEC retained scope fixture",
        content_scope="SEC filings",
        redistribution_status="allowed",
        permitted_use="Retained source bodies for local analysis",
        attribution_requirements="SEC",
        terms_urls=["https://www.sec.gov/about/webmaster-frequently-asked-questions"],
        reviewed_at=min(c.fetched_at for c in inputs.captures),
        reviewed_by="disposable-test",
        review_artifact_reference="docs/research/sec-application-policy-2026-09-21.md",
        review_artifact_sha256="719f60fbe146bbcfaba8049b4f8b61d0785915cc910187ff2b48f0e9479d2c4f",
    )
    with db_admin.transaction():
        for capture in inputs.captures:
            row = rows[str(capture.id)]
            _insert_record(
                db_admin,
                "source_captures",
                id=capture.id,
                source_id=source,
                source_object_key=capture.source_object_key,
                request_url=capture.request_url,
                request_params_hash="0" * 64,
                requested_at=row["requested_at"],
                completed_at=row["completed_at"],
                fetched_at=row["fetched_at"],
                http_status=200,
                body_sha256=capture.body_sha256,
                blob_key=row["blob_key"],
                byte_count=capture.byte_count,
                content_type=row.get("content_type"),
                terms_review_reference="sec-public-filings-2026-09-21",
            )
            _insert_record(
                db_admin,
                "capture_policy_links",
                capture_id=capture.id,
                policy_revision_id=policy_id,
            )
    register_mapping(db_admin, bundle)
    batch = publish_bundle(db, bundle)
    workspace = create_workspace_watchlist(db, name="Disposable real source test")
    manifest = build_manifest(
        db,
        bundle=bundle,
        proof=proof,
        batch_id=batch.batch_id,
        security_id=security,
        evaluated_at=datetime(2026, 10, 15, 23, tzinfo=UTC),
    )
    review = approve_real_manifest(
        db_admin,
        workspace_id=workspace.workspace_id,
        manifest=manifest,
        archive=LocalArchive(ROOT / "var/raw"),
        reviewed_by="disposable-test",
        reason="Retained operands and signed formula; no application write",
    )
    return workspace, manifest, review


def test_real_fenced_publication_replay_and_no_quote(real_setup, db, db_admin):
    from equity_ingest.real_fundamentals_pipeline import run_fundamentals_stage
    from equity_schema.real_fundamentals_store import (
        claim_real_fundamentals,
        enqueue_fundamentals,
        get_snapshot,
    )
    from equity_schema.workflow import claim_next

    workspace, manifest, review = real_setup
    request = enqueue_fundamentals(
        db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key="real-once"
    )
    assert claim_next(db, worker_id="ordinary-worker") is None
    lease = claim_real_fundamentals(db, worker_id="real-test", request_id=request.request_id)
    assert lease
    snapshot = run_fundamentals_stage(db, lease)
    assert run_fundamentals_stage(db, lease) == snapshot
    saved = get_snapshot(db, workspace_id=workspace.workspace_id, snapshot_id=snapshot)
    assert saved and saved.outcome == "completed_with_gaps"
    margin = next(m for m in saved.result.metrics if m.metric_id == "operating_margin")
    assert margin.status == "valid" and margin.value.startswith("-0.035"), margin.reasons
    assert len(saved.result.metrics) == 10 and saved.result.coverage.unresolved_count == 9
    assert saved.result.coverage.fraction is None
    from collections import Counter

    statuses = Counter(metric.status for metric in saved.result.metrics)
    assert all(saved.result.coverage.counts[status] == count for status, count in statuses.items())
    assert statuses == {"valid": 1, "unsupported": 9}
    for metric in saved.result.metrics:
        if metric.metric_id != "operating_margin":
            assert metric.value is None and metric.applicability is None
            assert f"required_source_inputs_unavailable:{metric.metric_id}" in metric.reasons
            from scripts.prepare_crcl_fundamentals import REQUIREMENTS

            assert f"applicability_requirement:{REQUIREMENTS[metric.metric_id]}" in metric.reasons
            rule = next(
                r for r in manifest.context.profile.rules if r.metric_id == metric.metric_id
            )
            assert rule.rationale == REQUIREMENTS[metric.metric_id]
    assert db_admin.execute("SELECT count(*) AS n FROM security_identifiers").fetchone()["n"] == 0
    assert db_admin.execute("SELECT count(*) AS n FROM analysis_snapshots").fetchone()["n"] == 0


@pytest.mark.parametrize("mutation", ["value", "precision", "unproved_precision", "policy_locator"])
def test_real_review_rejects_changed_source_proofs(real_setup, db_admin, mutation):
    from dataclasses import replace
    from decimal import Decimal

    from equity_ingest.archive import LocalArchive
    from equity_schema.real_fundamentals_store import approve_real_manifest

    from scripts.normalize_crcl import ROOT

    workspace, manifest, _ = real_setup
    if mutation == "value":
        source = manifest.sources[0]
        fact = replace(source.fact, value=Decimal("96435000"))
        source = replace(source, selection=replace(source.selection, facts=(fact,)))
        changed = manifest.model_copy(update={"sources": (source, manifest.sources[1])})
    elif mutation == "precision":
        proof = manifest.precision_evidence[0].model_copy(update={"scale": 6})
        changed = manifest.model_copy(
            update={"precision_evidence": (proof, manifest.precision_evidence[1])}
        )
    elif mutation == "unproved_precision":
        changed = manifest.model_copy(update={"precision_evidence": ()})
    else:
        proof = manifest.policy_evidence[0].model_copy(update={"locator": "invented"})
        changed = manifest.model_copy(
            update={"policy_evidence": (proof, *manifest.policy_evidence[1:])}
        )
    with pytest.raises(ValueError):
        approve_real_manifest(
            db_admin,
            workspace_id=workspace.workspace_id,
            manifest=changed,
            archive=LocalArchive(ROOT / "var/raw"),
            reviewed_by="test",
            reason="must reject",
        )
    assert (
        db_admin.execute("SELECT count(*) AS n FROM real_fundamentals_input_reviews").fetchone()[
            "n"
        ]
        == 1
    )


def test_real_intent_is_idempotent_and_review_children_are_sealed(real_setup, db, db_admin):
    from equity_schema.real_fundamentals_store import enqueue_fundamentals

    workspace, manifest, review = real_setup
    first = enqueue_fundamentals(
        db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key="same"
    )
    again = enqueue_fundamentals(
        db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key="same"
    )
    assert first.request_id == again.request_id
    with pytest.raises(psycopg.Error):
        enqueue_fundamentals(
            db,
            workspace_id=workspace.workspace_id,
            review_id=review,
            idempotency_key="same",
            max_attempts=4,
        )
    with pytest.raises(psycopg.Error):
        db_admin.execute(
            "INSERT INTO real_fundamentals_review_captures VALUES(%s,%s,%s,%s)",
            (
                review,
                manifest.captures[0].capture_id,
                manifest.captures[0].body_sha256,
                manifest.captures[0].fetched_at,
            ),
        )
    with pytest.raises(psycopg.Error):
        db_admin.execute(
            "UPDATE real_fundamentals_input_reviews SET expected_payload_hash=%s WHERE id=%s",
            ("f" * 64, review),
        )


def test_real_cancel_and_wrong_stage_cannot_publish(real_setup, db):
    from equity_ingest.real_fundamentals_pipeline import run_fundamentals_stage
    from equity_schema.real_fundamentals_store import claim_real_fundamentals, enqueue_fundamentals
    from equity_schema.workflow import LeaseLost, cancel_request, start_stage

    workspace, _, review = real_setup
    request = enqueue_fundamentals(
        db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key="cancel"
    )
    lease = claim_real_fundamentals(db, worker_id="test", request_id=request.request_id)
    with pytest.raises(psycopg.Error):
        start_stage(db, lease, stage_key="fundamentals")
    cancel_request(db, request_id=request.request_id)
    with pytest.raises((LeaseLost, psycopg.errors.ObjectNotInPrerequisiteState)):
        run_fundamentals_stage(db, lease)
    assert db.execute("SELECT count(*) AS n FROM real_fundamentals_snapshots").fetchone()["n"] == 0


def test_real_late_completion_does_not_replace_newer_request(real_setup, db):
    from equity_ingest.real_fundamentals_pipeline import run_fundamentals_stage
    from equity_schema.real_fundamentals_store import (
        claim_real_fundamentals,
        compatibility_key,
        enqueue_fundamentals,
        get_latest,
    )

    workspace, manifest, review = real_setup
    first = enqueue_fundamentals(
        db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key="old"
    )
    newer = enqueue_fundamentals(
        db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key="new"
    )
    old_lease = claim_real_fundamentals(db, worker_id="old", request_id=first.request_id)
    new_lease = claim_real_fundamentals(db, worker_id="new", request_id=newer.request_id)
    saved = run_fundamentals_stage(db, new_lease)
    run_fundamentals_stage(db, old_lease)
    latest = get_latest(
        db,
        workspace_id=workspace.workspace_id,
        issuer_id=manifest.selector.issuer_id,
        security_id=manifest.selector.security_id,
        compatibility_key=compatibility_key(manifest),
    )
    assert latest[0].snapshot_id == saved and latest[1] == newer.request_id


def test_real_retry_reuses_frozen_inputs_and_rejects_old_epoch(real_setup, db):
    from equity_schema.real_fundamentals_store import (
        calculate_and_publish,
        claim_real_fundamentals,
        enqueue_fundamentals,
        freeze_inputs,
    )
    from equity_schema.workflow import LeaseLost, retry_execution, start_stage

    workspace, _, review = real_setup
    request = enqueue_fundamentals(
        db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key="retry"
    )
    old = claim_real_fundamentals(db, worker_id="old", request_id=request.request_id)
    stage = start_stage(db, old, stage_key="real_fundamentals")
    frozen = freeze_inputs(db, old, stage_id=stage, review_id=review)
    retry_execution(db, old, error_code="test_crash", delay_seconds=0)
    lease = claim_real_fundamentals(db, worker_id="retry", request_id=request.request_id)
    newer_stage = start_stage(db, lease, stage_key="real_fundamentals")
    assert freeze_inputs(db, lease, stage_id=newer_stage, review_id=review) == frozen
    with pytest.raises(LeaseLost):
        calculate_and_publish(db, old, stage_id=stage, input_snapshot_id=frozen)
    assert calculate_and_publish(db, lease, stage_id=newer_stage, input_snapshot_id=frozen)


def test_real_http_saved_exact_provenance_and_workspace_isolation(
    real_setup, db, test_database_dsn
):
    from contextlib import contextmanager
    from uuid import uuid4

    from equity_api.real_fundamentals import create_app
    from equity_ingest.real_fundamentals_pipeline import run_fundamentals_stage
    from equity_schema.real_fundamentals_store import (
        claim_real_fundamentals,
        compatibility_key,
        enqueue_fundamentals,
    )
    from fastapi.testclient import TestClient
    from psycopg.rows import dict_row

    workspace, manifest, review = real_setup
    request = enqueue_fundamentals(
        db, workspace_id=workspace.workspace_id, review_id=review, idempotency_key="http"
    )
    lease = claim_real_fundamentals(db, worker_id="http", request_id=request.request_id)
    snapshot = run_fundamentals_stage(db, lease)

    @contextmanager
    def connections():
        with psycopg.connect(test_database_dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SET ROLE equity_runtime")
            yield conn

    client = TestClient(
        create_app(workspace_id=workspace.workspace_id, connection_factory=connections)
    )
    url = f"/v2/real-fundamentals/snapshots/{snapshot}"
    saved = client.get(url)
    assert saved.status_code == 200
    body = saved.json()
    assert body["result"]["evidence_mode"] == "real"
    assert len(body["result"]["precision_evidence"]) == 2
    assert body["result"]["precision_evidence"][0]["accession"] == "0001876042-26-000062"
    latest_url = f"/v2/companies/{manifest.selector.issuer_id}/real-fundamentals"
    query = {
        "security_id": str(manifest.selector.security_id),
        "compatibility_key": compatibility_key(manifest),
    }
    assert client.get(latest_url, params=query).json()["snapshot"] == body
    assert client.get(url).content == saved.content
    assert client.get(latest_url, params={**query, "compatibility_key": "f" * 64}).json() == {
        "code": "no_compatible_snapshot",
        "message": "N/A",
    }
    other = TestClient(create_app(workspace_id=uuid4(), connection_factory=connections))
    assert other.get(url).json() == {"code": "snapshot_not_found", "message": "N/A"}
    assert other.get(latest_url, params=query).status_code == 404
    assert client.post(url, json={}).status_code == 405
    assert "manifest_text" not in saved.text and "reviewed_by" not in saved.text


def clone_review_direct(db, original, manifest):
    """Bypass owner Python verification, matching all JSON and typed ID sets."""
    from uuid import uuid4

    from equity_schema.fundamentals_canonical import canonical_json, content_hash
    from equity_schema.real_fundamentals_store import compatibility_key

    from tests.evidence_seed import _insert_record

    review = uuid4()
    row = dict(
        db.execute(
            "SELECT * FROM real_fundamentals_input_reviews WHERE id=%s", (original,)
        ).fetchone()
    )
    row.update(
        id=review,
        manifest_text=canonical_json(manifest),
        manifest_hash=content_hash(manifest),
        compatibility_text=canonical_json(manifest.selector),
        compatibility_hash=compatibility_key(manifest),
    )
    row.pop("creation_transaction_id")
    _insert_record(db, "real_fundamentals_input_reviews", **row)
    for capture in manifest.captures:
        db.execute(
            "INSERT INTO real_fundamentals_review_captures VALUES(%s,%s,%s,%s)",
            (review, capture.capture_id, capture.body_sha256, capture.fetched_at),
        )
    from psycopg import sql

    for index, source in enumerate(manifest.sources):
        sel, q = source.selection, source.selection.query
        db.execute(
            "INSERT INTO real_fundamentals_review_inputs VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (
                review,
                index,
                source.period.id,
                source.unit.id,
                source.scope.id,
                q.mapping_revision_id,
                sel.input_hash,
            ),
        )
        refs = {
            "batches": q.batch_ids,
            "captures": q.capture_ids,
            "editions": sel.filing_version_ids,
            "coverage": sel.coverage_ids,
            "events": (*q.filing_event_ids, *sel.event_ids),
            "quality": (*q.additional_quality_flag_ids, *sel.quality_flag_ids),
            "resolutions": tuple(v for f in sel.facts for v in f.resolution_ids),
            "observations": tuple(v for f in sel.facts for v in f.observation_ids),
        }
        for name, values in refs.items():
            for value in set(values):
                db.execute(
                    sql.SQL("INSERT INTO {} VALUES(%s,%s,%s)").format(
                        sql.Identifier("real_fundamentals_input_" + name)
                    ),
                    (review, index, value),
                )
    return review


@pytest.mark.parametrize(
    "kind", ["resolution", "observation", "coverage", "period", "edition", "issuer", "empty"]
)
def test_direct_sql_rejects_unrelated_lineage_even_with_matching_id_sets(
    real_setup, db_admin, kind
):
    from dataclasses import replace
    from uuid import uuid4

    from tests.evidence_seed import _insert_record

    _, manifest, review = real_setup
    source, other = manifest.sources
    selection = source.selection
    if kind == "empty":
        fact = replace(source.fact, resolution_ids=(), observation_ids=())
        selection = replace(selection, facts=(fact,))
    elif kind == "resolution":
        fact = replace(source.fact, resolution_ids=other.fact.resolution_ids)
        selection = replace(selection, facts=(fact,))
    elif kind == "observation":
        fact = replace(source.fact, observation_ids=other.fact.observation_ids)
        selection = replace(selection, facts=(fact,))
    elif kind in ("coverage", "period"):
        # Existing S3 coverage from a different, internally valid building batch.
        original = dict(
            db_admin.execute(
                "SELECT * FROM statement_coverage WHERE id=%s", (selection.coverage_ids[0],)
            ).fetchone()
        )
        batch = dict(
            db_admin.execute(
                "SELECT * FROM normalization_batches WHERE id=%s", (original["batch_id"],)
            ).fetchone()
        )
        batch.update(
            id=uuid4(),
            state="building",
            published_at=None,
            input_manifest_hash=None,
            output_manifest_hash=None,
        )
        _insert_record(db_admin, "normalization_batches", **batch)
        if kind == "period":
            original["period_id"] = db_admin.execute(
                "SELECT id FROM periods WHERE period_kind='duration' "
                "AND start_date='2024-01-01' AND end_date='2024-12-31'"
            ).fetchone()["id"]
        original.update(id=uuid4(), batch_id=batch["id"])
        _insert_record(db_admin, "statement_coverage", **original)
        selection = replace(selection, coverage_ids=(original["id"],))
    elif kind == "issuer":
        issuer, filing, edition = uuid4(), uuid4(), uuid4()
        _insert_record(
            db_admin,
            "issuers",
            id=issuer,
            cik="9999999999",
            legal_name="Unrelated fixture",
            first_seen_at=manifest.selector.evaluated_at,
        )
        _insert_record(
            db_admin, "filings", id=filing, issuer_id=issuer, accession="9999999999-26-000001"
        )
        row = dict(
            db_admin.execute(
                "SELECT * FROM filing_versions WHERE id=%s", (selection.filing_version_ids[0],)
            ).fetchone()
        )
        row.update(id=edition, filing_id=filing)
        _insert_record(db_admin, "filing_versions", **row)
        selection = replace(selection, filing_version_ids=(edition,))
    else:
        edition = db_admin.execute(
            "SELECT id FROM filing_versions WHERE id<>%s LIMIT 1",
            (selection.filing_version_ids[0],),
        ).fetchone()["id"]
        selection = replace(selection, filing_version_ids=(edition,))
    changed = manifest.model_copy(update={"sources": (replace(source, selection=selection), other)})
    with pytest.raises(psycopg.errors.CheckViolation):
        with db_admin.transaction():
            clone_review_direct(db_admin, review, changed)
    assert (
        db_admin.execute("SELECT count(*) AS n FROM real_fundamentals_input_reviews").fetchone()[
            "n"
        ]
        == 1
    )


def test_commit_before_audit_interruption_recovers_original_baseline_and_snapshot(
    real_setup, db_admin, test_database_dsn, tmp_path, monkeypatch
):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from equity_core.real_fundamentals import calculate_payload
    from equity_ingest.archive import LocalArchive
    from equity_schema.fundamentals_canonical import content_hash
    from sqlalchemy.engine import make_url

    from scripts import publish_crcl_fundamentals as publisher
    from scripts.normalize_crcl import ROOT

    workspace, manifest, _ = real_setup
    payload = calculate_payload(manifest, history_payloads={})

    @contextmanager
    def owner(*args):
        yield db_admin

    monkeypatch.setattr(publisher, "ROOT", tmp_path)
    monkeypatch.setattr(publisher, "WORKSPACE", workspace.workspace_id)
    monkeypatch.setattr(publisher, "MANIFEST_HASH", content_hash(manifest))
    monkeypatch.setattr(publisher, "PAYLOAD_HASH", content_hash(payload))
    monkeypatch.setattr(publisher, "checked_candidate", lambda: (manifest, payload))
    monkeypatch.setattr(
        publisher,
        "application_candidate",
        lambda _: {"manifestHash": content_hash(manifest), "payloadHash": content_hash(payload)},
    )
    monkeypatch.setattr(publisher, "LocalArchive", lambda _: LocalArchive(ROOT / "var/raw"))
    monkeypatch.setattr(
        publisher.app_postgres,
        "configuration",
        lambda: (SimpleNamespace(database="test"), make_url(test_database_dsn)),
    )
    monkeypatch.setattr(publisher.app_postgres, "guard", lambda _: None)
    monkeypatch.setattr(publisher.app_postgres, "verify", lambda _: None)
    monkeypatch.setattr(publisher.app_postgres, "owner_connection", owner)
    original = publisher.write_audit

    def interrupted(*args):
        raise InterruptedError("simulated crash after commit, before audit")

    monkeypatch.setattr(publisher, "write_audit", interrupted)
    with pytest.raises(InterruptedError):
        publisher.application("publish")
    import json

    intent = json.loads((tmp_path / publisher.INTENT).read_text())
    assert intent["beforeRows"]["real_fundamentals_snapshots"] == []
    assert (
        db_admin.execute("SELECT count(*) AS n FROM real_fundamentals_snapshots").fetchone()["n"]
        == 1
    )
    assert not (tmp_path / publisher.PUBLICATION).exists()
    monkeypatch.setattr(publisher, "write_audit", original)
    recovered = publisher.application("publish")
    assert recovered["beforeRows"] == intent["beforeRows"]
    assert recovered["exactReplay"] and recovered["priorRowsPreserved"]
    assert recovered["recoveredCommittedSnapshot"]
    assert db_admin.execute("SELECT count(*) AS n FROM analysis_requests").fetchone()["n"] == 1
    assert (
        db_admin.execute("SELECT count(*) AS n FROM real_fundamentals_snapshots").fetchone()["n"]
        == 1
    )
    assert publisher.application("verify")["payloadHash"] == content_hash(payload)
