"""Migration roundtrips, frozen vocabulary, and least-privilege runtime checks."""

import re
from pathlib import Path

import dotenv
import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from equity_schema.concepts import Concept
from psycopg import sql

from tests.conftest import migration_config, test_migration_target

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]

# These reviewed domain tables must exist, while auxiliary bookkeeping may grow.
REQUIRED_TABLES = {
    "issuers",
    "securities",
    "security_identifiers",
    "security_identifier_validity",
    "security_identifier_closures",
    "security_relationships",
    "sources",
    "source_captures",
    "source_policy_revisions",
    "source_fetch_attempts",
    "capture_policy_links",
    "filings",
    "filing_versions",
    "periods",
    "units",
    "semantic_scopes",
    "mapping_revisions",
    "normalization_batches",
    "normalization_inputs",
    "statement_coverage",
    "source_observations",
    "fact_resolutions",
    "resolution_candidates",
    "data_quality_flags",
    "quality_flag_acknowledgements",
    "filing_events",
    "filing_event_scopes",
    "fact_revision_links",
    "workspaces",
    "watchlists",
    "watchlist_memberships",
    "analysis_requests",
    "analysis_request_state",
    "analysis_executions",
    "analysis_stage_attempts",
    "execution_events",
}


def public_tables(connection):
    return {
        row["relname"]
        for row in connection.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind IN ('r','p') AND c.relname<>'alembic_version'"
        )
    }


def schema_signature(connection):
    """Compare definitions, avoiding OIDs that change during a genuine rebuild."""
    queries = {
        "columns": """
            SELECT c.relname, a.attnum, a.attname, format_type(a.atttypid,a.atttypmod) AS type,
                   a.attnotnull, a.attidentity, a.attgenerated,
                   pg_get_expr(d.adbin,d.adrelid) AS default_expression
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_attribute a ON a.attrelid=c.oid
            LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
            WHERE n.nspname='public' AND c.relkind IN ('r','p')
              AND a.attnum>0 AND NOT a.attisdropped
            ORDER BY c.relname,a.attnum
        """,
        "constraints": """
            SELECT c.relname, con.conname, con.contype, con.condeferrable, con.condeferred,
                   con.convalidated, pg_get_constraintdef(con.oid) AS definition
            FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' ORDER BY c.relname,con.conname
        """,
        "indexes": """
            SELECT c.relname, pg_get_indexdef(i.indexrelid) AS definition,
                   i.indisvalid, i.indisready
            FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' ORDER BY c.relname
        """,
        "triggers": """
            SELECT c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid) AS definition
            FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname
        """,
        "functions": """
            SELECT p.proname,pg_get_function_identity_arguments(p.oid) AS arguments,
                   pg_get_functiondef(p.oid) AS definition, p.proacl::text AS privileges
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='public' AND p.prokind IN ('f','p')
              AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass
                  AND d.objid=p.oid AND d.refclassid='pg_extension'::regclass AND d.deptype='e')
            ORDER BY p.proname,arguments
        """,
        "table_privileges": """
            SELECT c.relname,c.relacl::text AS privileges
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind IN ('r','p','S') ORDER BY c.relname
        """,
    }
    return {name: connection.execute(query).fetchall() for name, query in queries.items()}


def test_actual_postgres_upgrade_downgrade_roundtrip(db_admin, test_database_dsn):
    config = migration_config(test_database_dsn)
    expected_heads = {
        ScriptDirectory.from_config(config).get_revision(test_migration_target()).revision
    }
    assert expected_heads, "At least one frozen migration must exist"
    actual_heads = {
        row["version_num"] for row in db_admin.execute("SELECT version_num FROM alembic_version")
    }
    assert actual_heads == expected_heads
    assert REQUIRED_TABLES <= public_tables(db_admin)
    before = schema_signature(db_admin)

    # This fixture owns a fresh random database; no application/runtime transaction is open.
    command.downgrade(config, "base")
    assert public_tables(db_admin) == set()
    assert db_admin.execute("SELECT count(*) AS n FROM alembic_version").fetchone()["n"] == 0
    assert db_admin.execute("SELECT 1 FROM pg_roles WHERE rolname='equity_runtime'").fetchone()
    assert not schema_signature(db_admin)["functions"], (
        "Downgrade must not leave application functions"
    )

    command.upgrade(config, test_migration_target())
    assert schema_signature(db_admin) == before
    assert {
        row["version_num"] for row in db_admin.execute("SELECT version_num FROM alembic_version")
    } == expected_heads


def test_database_concept_checks_match_python_and_generated_typescript(db_admin):
    expected = {concept.value for concept in Concept}
    typescript = (ROOT / "packages/schema/types/concepts.ts").read_text()
    generated = re.findall(r'^\s+"([a-z_]+)",$', typescript, flags=re.MULTILINE)
    assert len(generated) == len(set(generated)) == len(expected)
    assert set(generated) == expected
    columns = db_admin.execute("""
        SELECT c.relname,a.attname,a.attnotnull,
               array_agg(pg_get_constraintdef(con.oid)) FILTER (WHERE con.oid IS NOT NULL) AS checks
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.oid
        LEFT JOIN pg_constraint con ON con.conrelid=c.oid AND con.contype='c'
            AND a.attnum=ANY(con.conkey)
        WHERE n.nspname='public' AND c.relkind IN ('r','p')
          AND a.attname='concept_std' AND NOT a.attisdropped
        GROUP BY c.relname,a.attname,a.attnotnull ORDER BY c.relname
    """).fetchall()
    assert columns, "The database must enforce the financial concept vocabulary"
    assert "fact_resolutions" in {row["relname"] for row in columns}
    for column in columns:
        allowed_sets = [
            set(re.findall(r"'([a-z_]+)'::text", check)) for check in column["checks"] or []
        ]
        assert expected in allowed_sets, f"Frozen concept CHECK drift: {column['relname']}"


def test_runtime_role_cannot_elevate_or_own_application_objects(db_admin, db):
    role = db_admin.execute("""
        SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin
        FROM pg_roles WHERE rolname='equity_runtime'
    """).fetchone()
    assert role and not any(role.values())
    assert not db.execute(
        "SELECT has_schema_privilege(current_user,'public','CREATE') AS allowed"
    ).fetchone()["allowed"]
    owned = db_admin.execute("""
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public'
          AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname='equity_runtime')
    """).fetchall()
    assert owned == []


@pytest.mark.parametrize("operation", ["alter", "drop", "truncate"])
def test_runtime_cannot_change_table_structure_or_truncate(db_admin, db, operation):
    statements = {
        "alter": "ALTER TABLE {} ADD COLUMN migration_privilege_probe text",
        "drop": "DROP TABLE {} CASCADE",
        "truncate": "TRUNCATE TABLE {} CASCADE",
    }
    for table in sorted(public_tables(db_admin)):
        statement = sql.SQL(statements[operation]).format(sql.Identifier("public", table))
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute(statement)


@pytest.mark.parametrize(
    "signature,invocation",
    [
        ("evidence_immutable()", "evidence_immutable()"),
        ("evidence_event_complete()", "evidence_event_complete()"),
        ("evidence_quote_projection_guard()", "evidence_quote_projection_guard()"),
        ("evidence_quote_projection_seed()", "evidence_quote_projection_seed()"),
        ("evidence_lock_building(uuid)", "evidence_lock_building(NULL::uuid)"),
        ("evidence_integrity()", "evidence_integrity()"),
        ("evidence_batch_transition()", "evidence_batch_transition()"),
        ("evidence_revision_integrity()", "evidence_revision_integrity()"),
    ],
)
def test_runtime_cannot_execute_owner_only_evidence_functions(db_admin, db, signature, invocation):
    assert not db_admin.execute(
        "SELECT has_function_privilege('equity_runtime',%s,'EXECUTE') AS allowed", (signature,)
    ).fetchone()["allowed"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute(sql.SQL("SELECT public.{};").format(sql.SQL(invocation)))


def test_workflow_only_exposes_reviewed_runtime_entry_points(db_admin, db):
    entry_points = {
        "workflow_create_workspace",
        "workflow_enqueue",
        "workflow_remove_membership",
        "workflow_claim",
        "workflow_renew",
        "workflow_start_stage",
        "workflow_finish_stage",
        "workflow_finish",
        "workflow_retry",
        "workflow_cancel",
    }
    if test_migration_target() == "head":
        entry_points |= {
            "workflow_enqueue_bootstrap",
            "workflow_claim_bootstrap",
            "workflow_complete_bootstrap_stage",
        }
    functions = db_admin.execute(r"""
        SELECT p.oid,p.proname,p.oid::regprocedure::text AS signature,p.prosecdef,p.proconfig,
               has_function_privilege('equity_runtime',p.oid,'EXECUTE') AS runtime_allowed,
               ARRAY(SELECT format_type(a.type_oid,NULL) FROM unnest(p.proargtypes) a(type_oid))
                   AS argument_types,
               EXISTS(SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl
                      WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE') AS public_allowed
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public' AND p.proname LIKE 'workflow\_%' ESCAPE '\'
        ORDER BY p.proname
    """).fetchall()
    assert entry_points <= {function["proname"] for function in functions}
    for function in functions:
        assert not function["public_allowed"], function["signature"]
        assert function["runtime_allowed"] == (function["proname"] in entry_points)
        if function["proname"] in entry_points:
            assert function["prosecdef"]
            assert "search_path=public,pg_temp" in {
                setting.replace(" ", "") for setting in function["proconfig"] or []
            }
        else:
            arguments = sql.SQL(",").join(
                sql.SQL("NULL::{}").format(sql.SQL(type_name))
                for type_name in function["argument_types"]
            )
            statement = sql.SQL("SELECT {}({})").format(
                sql.Identifier("public", function["proname"]), arguments
            )
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                db.execute(statement)


def test_explicit_migration_url_never_loads_application_dotenv(
    db_admin, test_database_dsn, monkeypatch
):
    config = migration_config(test_database_dsn)
    command.downgrade(config, "base")

    def unexpected_dotenv(*args, **kwargs):
        raise AssertionError("An explicit migration URL must not read application dotenv")

    monkeypatch.setattr(dotenv, "load_dotenv", unexpected_dotenv)
    monkeypatch.setenv("DATABASE_URL", "must-not-be-used://application-database")
    command.upgrade(config, test_migration_target())
    assert REQUIRED_TABLES <= public_tables(db_admin)
    assert {
        row["version_num"] for row in db_admin.execute("SELECT version_num FROM alembic_version")
    } == {ScriptDirectory.from_config(config).get_revision(test_migration_target()).revision}


def test_source_storage_exposes_only_fenced_runtime_entry_points(db_admin, db):
    entry_points = {
        "ingestion_validate_stage",
        "ingestion_prepare",
        "ingestion_dispatch",
        "ingestion_headers",
        "ingestion_finalize",
        "ingestion_recover",
    }
    functions = db_admin.execute(r"""
        SELECT p.proname,p.oid::regprocedure::text AS signature,p.prosecdef,p.proconfig,
               has_function_privilege('equity_runtime',p.oid,'EXECUTE') AS runtime_allowed,
               ARRAY(SELECT format_type(a.type_oid,NULL) FROM unnest(p.proargtypes) a(type_oid))
                   AS argument_types,
               EXISTS(SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl
                      WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE') AS public_allowed
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public' AND p.proname LIKE 'ingestion\_%' ESCAPE '\'
        ORDER BY p.proname
    """).fetchall()
    assert entry_points <= {function["proname"] for function in functions}
    for function in functions:
        assert not function["public_allowed"], function["signature"]
        assert function["runtime_allowed"] == (function["proname"] in entry_points)
        if function["proname"] in entry_points:
            assert function["prosecdef"]
            assert "search_path=public,pg_temp" in {
                setting.replace(" ", "") for setting in function["proconfig"] or []
            }
        else:
            arguments = sql.SQL(",").join(
                sql.SQL("NULL::{}").format(sql.SQL(type_name))
                for type_name in function["argument_types"]
            )
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                db.execute(
                    sql.SQL("SELECT {}({})").format(
                        sql.Identifier("public", function["proname"]), arguments
                    )
                )


def test_source_upgrade_preserves_legacy_capture_and_restores_s2_grants_on_downgrade(
    db_admin, db, test_database_dsn
):
    from tests.evidence_seed import seed_evidence

    config = migration_config(test_database_dsn)
    command.downgrade(config, "0002_watchlist")
    assert db.execute(
        "SELECT has_table_privilege(current_user,'source_captures','INSERT') AS allowed"
    ).fetchone()["allowed"]
    ids = seed_evidence(db_admin)
    original = db_admin.execute(
        "SELECT * FROM source_captures WHERE id=%s", (ids["capture"],)
    ).fetchone()
    command.upgrade(config, test_migration_target())
    assert (
        db_admin.execute("SELECT * FROM source_captures WHERE id=%s", (ids["capture"],)).fetchone()
        == original
    )
    assert db.execute(
        "SELECT review_status,policy_revision_id FROM source_capture_policy_status "
        "WHERE capture_id=%s",
        (ids["capture"],),
    ).fetchone() == {"review_status": "legacy_unreviewed", "policy_revision_id": None}
    assert not db.execute(
        "SELECT has_table_privilege(current_user,'source_captures','INSERT') AS allowed"
    ).fetchone()["allowed"]
    assert (
        db_admin.execute("SELECT count(*) AS n FROM source_policy_revisions").fetchone()["n"] == 0
    )
