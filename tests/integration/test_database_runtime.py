"""Prove the explicitly selected real runtime, including required hypertable behavior."""

from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from scripts.test_postgres import TIMESCALE_VERSION
from tests.conftest import drop_test_database, test_database_profile

pytestmark = pytest.mark.integration


def test_runtime_is_postgres16_with_required_profile(postgres_admin_dsn):
    with psycopg.connect(postgres_admin_dsn, autocommit=True) as connection:
        assert 160000 <= connection.info.server_version < 170000
        if test_database_profile() == "timescale-pg16":
            assert "timescaledb" in connection.execute("SHOW shared_preload_libraries").fetchone()[
                0
            ].split(",")
            assert connection.execute(
                "SELECT default_version FROM pg_available_extensions WHERE name='timescaledb'"
            ).fetchone() == (TIMESCALE_VERSION,)
            assert connection.execute("SHOW timescaledb.telemetry_level").fetchone() == ("off",)


def test_timescale_date_hypertables_enforce_incoming_and_outgoing_foreign_keys(postgres_admin_dsn):
    if test_database_profile() != "timescale-pg16":
        pytest.skip("Explicit native profile stops at 0004; full S4 requires Timescale profile")
    name = "equity_test_runtime_" + uuid4().hex
    with psycopg.connect(postgres_admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        try:
            dsn = postgres_admin_dsn.rsplit("/", 1)[0] + "/" + name
            with psycopg.connect(dsn, autocommit=True) as connection:
                connection.execute(
                    sql.SQL("CREATE EXTENSION timescaledb VERSION {}").format(
                        sql.Literal(TIMESCALE_VERSION)
                    )
                )
                assert connection.execute(
                    "SELECT extversion FROM pg_extension WHERE extname='timescaledb'"
                ).fetchone() == (TIMESCALE_VERSION,)
                connection.execute("CREATE TABLE runtime_parent(id integer PRIMARY KEY)")
                connection.execute("""
                    CREATE TABLE runtime_prices(
                        id integer NOT NULL, session_date date NOT NULL,
                        parent_id integer NOT NULL REFERENCES runtime_parent(id),
                        PRIMARY KEY(id,session_date)
                    )
                """)
                connection.execute("""
                    CREATE TABLE runtime_reference(
                        id integer NOT NULL, session_date date NOT NULL,
                        FOREIGN KEY(id,session_date) REFERENCES runtime_prices(id,session_date)
                    )
                """)
                # Match 0004 -> 0005: incoming FK exists before the empty-table conversion.
                connection.execute("""
                    SELECT create_hypertable(
                        'runtime_prices', by_range('session_date', INTERVAL '1 year'))
                """)
                assert connection.execute(
                    "SELECT hypertable_name FROM timescaledb_information.hypertables "
                    "WHERE hypertable_schema='public'"
                ).fetchall() == [("runtime_prices",)]
                connection.execute("INSERT INTO runtime_parent VALUES (1)")
                connection.execute("INSERT INTO runtime_prices VALUES (1,'2025-01-02',1)")
                connection.execute("INSERT INTO runtime_reference VALUES (1,'2025-01-02')")
                with pytest.raises(psycopg.errors.ForeignKeyViolation):
                    connection.execute("INSERT INTO runtime_prices VALUES (2,'2025-01-03',999)")
                with pytest.raises(psycopg.errors.ForeignKeyViolation):
                    connection.execute("INSERT INTO runtime_reference VALUES (1,'2025-01-03')")
                with pytest.raises(psycopg.errors.UniqueViolation):
                    connection.execute("INSERT INTO runtime_prices VALUES (1,'2025-01-02',1)")
                assert connection.execute(
                    "SELECT count(*) FROM timescaledb_information.jobs "
                    "WHERE proc_name IN ('policy_retention','policy_compression')"
                ).fetchone() == (0,)
        finally:
            drop_test_database(admin, name)
