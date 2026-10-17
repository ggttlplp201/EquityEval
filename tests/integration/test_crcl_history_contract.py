"""D050 SQL independently enforces the finite V2 acquisition boundary."""

from dataclasses import replace

from equity_schema.crcl_history import CRCL_HISTORY_DOCUMENTS, CRCL_HISTORY_VERSION
from psycopg.types.json import Jsonb

from tests.integration.test_source_bootstrap import (  # noqa: F401
    bootstrap_plan,
    pytestmark,
)
from tests.integration.test_source_bootstrap import (
    identity as fixture_identity,
)

identity = fixture_identity


def test_sql_accepts_exact_v2_and_rejects_unreviewed_resource(db_admin, db, identity):
    base = bootstrap_plan(db, identity)
    candidate = replace(base, version=CRCL_HISTORY_VERSION)
    assert db_admin.execute(
        "SELECT workflow_valid_bootstrap_plan(%s) AS ok", (Jsonb(candidate.as_json()),)
    ).fetchone()["ok"]
    for key in sorted(CRCL_HISTORY_DOCUMENTS):
        value = candidate.as_json()
        value["resources"].append(key)
        assert db_admin.execute(
            "SELECT workflow_valid_bootstrap_plan(%s) AS ok", (Jsonb(value),)
        ).fetchone()["ok"]
    value = candidate.as_json()
    value["resources"].append("filing_document/0001876042/0000000000-24-002161/filename2.pdf")
    assert not db_admin.execute(
        "SELECT workflow_valid_bootstrap_plan(%s) AS ok", (Jsonb(value),)
    ).fetchone()["ok"]


def test_v2_runtime_enqueue_and_sql_pdf_ownership(db_admin, db, identity):
    import hashlib
    from uuid import uuid4

    import psycopg
    import pytest
    from equity_ingest.contracts import ResourceKind, SecResource
    from equity_schema.crcl_history import CRCL_HISTORY_PDFS
    from equity_schema.workflow import claim_source_bootstrap, start_stage

    from tests.evidence_seed import insert
    from tests.integration.test_source_bootstrap import enqueue

    key = sorted(CRCL_HISTORY_PDFS)[0]
    _, cik, accession, filename = key.split("/")
    base = bootstrap_plan(db, identity)
    candidate = replace(base, version=CRCL_HISTORY_VERSION, resources=(*base.resources, key))
    enqueue(db, identity, plan=candidate)
    lease = claim_source_bootstrap(db, worker_id="pdf-contract")
    stage = start_stage(db, lease, stage_key="sec_fetch_" + "d" * 24)
    resource = SecResource(identity[1], cik, ResourceKind.FILING_DOCUMENT, filename, accession)
    row = dict(
        id=uuid4(),
        logical_fetch_id=uuid4(),
        sequence_no=1,
        source_id=candidate.source_id,
        policy_revision_id=candidate.policy_revision_id,
        source_object_key=key,
        request_url=resource.url,
        request_params_hash=hashlib.sha256(b"{}").hexdigest(),
        stage_attempt_id=stage,
        lease_epoch=lease.epoch,
        lease_fencing_token=lease.fencing_token,
        lease_owner=lease.worker_id,
    )
    insert(db_admin, "source_fetch_attempts", **row)
    for changes in [
        {"source_object_key": sorted(CRCL_HISTORY_PDFS)[1]},
        {"request_url": resource.url + "?other=1"},
        {"source_object_key": key.replace("filename1.pdf", "filename2.pdf")},
    ]:
        with pytest.raises(psycopg.errors.CheckViolation):
            insert(
                db_admin,
                "source_fetch_attempts",
                **(row | changes | {"id": uuid4(), "logical_fetch_id": uuid4()}),
            )


def test_v2_sql_common_shape_and_limits_cannot_be_bypassed(db_admin, db, identity):
    base = replace(bootstrap_plan(db, identity), version=CRCL_HISTORY_VERSION).as_json()
    changes = [
        {"resources": base["resources"] + sorted(CRCL_HISTORY_DOCUMENTS)[:6]},
        {"resources": base["resources"] + [base["resources"][0]]},
        {"resources": base["resources"] + [None]},
        {"resources": base["resources"][:1]},
        {"inventory_end": "2030-01-01"},
        {"inventory_start": "2025-02-31"},
        {"cik": "0000320193"},
        {"extra": None},
        {"source_id": "unknown"},
        {
            "resources": base["resources"]
            + ["submissions_history/0001876042/CIK0001876042-submissions-001.json"]
        },
    ]
    for change in changes:
        assert not db_admin.execute(
            "SELECT workflow_valid_bootstrap_plan(%s) AS ok", (Jsonb(base | change),)
        ).fetchone()["ok"]


def test_v2_downgrade_refuses_retained_request_and_empty_restores_v1(
    db_admin, db, identity, test_database_dsn
):
    import pytest
    from alembic import command

    from tests.conftest import migration_config
    from tests.integration.test_source_bootstrap import enqueue

    config = migration_config(test_database_dsn)
    command.downgrade(config, "0013_real_fundamentals")
    assert (
        db_admin.execute(
            "SELECT to_regprocedure('workflow_valid_bootstrap_plan_v1(jsonb)') AS f"
        ).fetchone()["f"]
        is None
    )
    command.upgrade(config, "head")
    enqueue(db, identity, plan=replace(bootstrap_plan(db, identity), version=CRCL_HISTORY_VERSION))
    with pytest.raises(Exception, match="refusing to discard retained V2"):
        command.downgrade(config, "0013_real_fundamentals")
    assert (
        db_admin.execute("SELECT version_num FROM alembic_version").fetchone()["version_num"]
        == "0014_crcl_history_documents"
    )


def test_ordinary_request_cannot_insert_pdf_attempt_directly(db_admin, db, identity):
    import hashlib
    from uuid import uuid4

    import psycopg
    import pytest
    from equity_ingest.contracts import ResourceKind, SecResource
    from equity_schema.workflow import claim_next, rerun_analysis, start_stage

    from tests.evidence_seed import insert, seed_evidence

    base = bootstrap_plan(db, identity)
    evidence = seed_evidence(db_admin)
    rerun_analysis(
        db,
        workspace_id=identity[0].workspace_id,
        security_id=evidence["security"],
        quote_identifier_id=evidence["quote"],
        idempotency_key="ordinary-pdf-bypass",
    )
    lease = claim_next(db, worker_id="ordinary-pdf")
    stage = start_stage(db, lease, stage_key="sec_fetch_" + "e" * 24)
    resource = SecResource(
        identity[1],
        "1876042",
        ResourceKind.FILING_DOCUMENT,
        "filename1.pdf",
        "0000000000-24-002161",
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="PDF requires exact V2"):
        insert(
            db_admin,
            "source_fetch_attempts",
            id=uuid4(),
            logical_fetch_id=uuid4(),
            sequence_no=1,
            source_id=base.source_id,
            policy_revision_id=base.policy_revision_id,
            source_object_key=resource.object_key,
            request_url=resource.url,
            request_params_hash=hashlib.sha256(b"{}").hexdigest(),
            stage_attempt_id=stage,
            lease_epoch=lease.epoch,
            lease_fencing_token=lease.fencing_token,
            lease_owner=lease.worker_id,
        )
