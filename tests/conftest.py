"""Real PostgreSQL tests use only databases created by this test session.

Never reads the application's .env or DATABASE_URL. The isolated PG16 helper owns
its cluster; every test clones a migrated template into a fresh random database.
"""

import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]


def migration_config(dsn):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        dsn.replace("postgresql://", "postgresql+psycopg://", 1).replace("%", "%%"),
    )
    return config


@pytest.fixture(scope="session")
def postgres_admin_dsn():
    subprocess.run([sys.executable, str(ROOT / "scripts/test_postgres.py"), "start"], check=True)
    runtime = json.loads((ROOT / "var/test-postgres16/runtime.json").read_text())
    dsn = f"postgresql://localhost:{runtime['port']}/postgres"
    with psycopg.connect(dsn, autocommit=True) as connection:
        assert 160000 <= connection.info.server_version < 170000, "S2 requires PostgreSQL 16"
    return dsn


def drop_test_database(connection, name):
    assert name.startswith("equity_test_")
    connection.execute(
        sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
    )


@pytest.fixture(scope="session")
def migrated_template(postgres_admin_dsn):
    name = "equity_test_template_" + uuid4().hex
    with psycopg.connect(postgres_admin_dsn, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
        )
        try:
            dsn = postgres_admin_dsn.rsplit("/", 1)[0] + "/" + name
            command.upgrade(migration_config(dsn), "head")
            yield name
        finally:
            drop_test_database(connection, name)


@pytest.fixture
def test_database_dsn(postgres_admin_dsn, migrated_template):
    name = "equity_test_" + uuid4().hex
    with psycopg.connect(postgres_admin_dsn, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                sql.Identifier(name), sql.Identifier(migrated_template)
            )
        )
        try:
            yield postgres_admin_dsn.rsplit("/", 1)[0] + "/" + name
        finally:
            drop_test_database(connection, name)


@pytest.fixture
def db_admin(test_database_dsn):
    with psycopg.connect(test_database_dsn, autocommit=True, row_factory=dict_row) as connection:
        yield connection


@pytest.fixture
def db(test_database_dsn):
    with psycopg.connect(test_database_dsn, autocommit=True, row_factory=dict_row) as connection:
        connection.execute("SET ROLE equity_runtime")
        yield connection


@pytest.fixture(scope="session")
def redis_url():
    subprocess.run([sys.executable, str(ROOT / "scripts/test_redis.py"), "start"], check=True)
    return "redis://127.0.0.1:16380/0"
