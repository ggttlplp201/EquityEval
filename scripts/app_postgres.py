"""Own a separate, persistent loopback application PG16/Timescale cluster.

Explicitly copies the pinned executable installation; never reads, copies or
controls test data. Local-only (no TLS); Unix peer owner and TCP SCRAM runtime
credentials. Existing application configuration is read, never printed/changed.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from alembic import command as alembic_command
from alembic.config import Config
from dotenv import dotenv_values
from psycopg import sql
from psycopg.rows import dict_row
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
OWNER = "equityeval-application-postgres-v1"
PG_VERSION = "16.14"
TS_VERSION = "2.28.1"


@dataclass(frozen=True)
class ApplicationRuntime:
    root: Path
    port: int
    database: str
    role: str

    @property
    def directory(self) -> Path:
        return self.root / "var/application-postgres16"

    @property
    def data(self) -> Path:
        return self.directory / "data"

    @property
    def record(self) -> Path:
        return self.directory / "runtime.json"

    @property
    def binary(self) -> Path:
        return self.directory / "installation/bin"

    @property
    def unix_socket(self) -> Path:
        suffix = hashlib.sha256(str(self.root).encode()).hexdigest()[:12]
        return Path("/tmp") / f"equityeval-application-pg16-{suffix}"

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "owner": OWNER,
            "repository": str(self.root),
            "data_dir": str(self.data),
            "socket_dir": str(self.unix_socket),
            "port": self.port,
            "database": self.database,
            "role": self.role,
            "postgres_version": PG_VERSION,
            "timescale_version": TS_VERSION,
        }


def configuration(root: Path = ROOT) -> tuple[ApplicationRuntime, URL]:
    values = dotenv_values(root / ".env")
    raw = os.environ.get("DATABASE_URL") or values.get("DATABASE_URL")
    if not raw:
        raise ValueError("Application DATABASE_URL is required")
    url = make_url(raw)
    if (
        url.drivername not in {"postgresql", "postgresql+psycopg"}
        or url.host not in {"127.0.0.1", "localhost"}
        or url.port != 5433
        or url.query
        or not url.database
        or not url.username
        or not url.password
        or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", url.database)
        or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", url.username)
        or url.database.startswith(("equity_test", "template"))
        or url.database == "postgres"
        or url.username in {"postgres", getpass.getuser(), "equity_runtime"}
    ):
        raise ValueError(
            "Require explicit local port 5433, separate database/runtime login and password"
        )
    return ApplicationRuntime(root, url.port, url.database, url.username), url


def guard(runtime: ApplicationRuntime) -> None:
    paths = (
        runtime.root / "var",
        runtime.directory,
        runtime.record,
        runtime.data,
        runtime.unix_socket,
        runtime.directory / "installation",
        runtime.directory / "server.log",
        runtime.directory / "installation-provenance.json",
    )
    for path in paths:
        if path.is_symlink() or (path.exists() and path.stat().st_uid != os.getuid()):
            raise RuntimeError("Refusing unowned or symlinked application runtime path")
    if runtime.record.exists():
        if json.loads(runtime.record.read_text()) != runtime.identity:
            raise RuntimeError("Application runtime ownership record mismatch")
    elif runtime.directory.exists() and any(runtime.directory.iterdir()):
        raise RuntimeError("Existing application files have no matching ownership record")
    if runtime.data.exists() and (
        not (runtime.data / "PG_VERSION").is_file()
        or (runtime.data / "PG_VERSION").read_text().strip() != "16"
    ):
        raise RuntimeError("Existing application data is not a completed PG16 initialization")


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=60)


def owner_connection(
    runtime: ApplicationRuntime, database: str = "postgres"
) -> psycopg.Connection[dict[str, Any]]:
    return psycopg.connect(
        host=str(runtime.unix_socket),
        port=runtime.port,
        dbname=database,
        user=getpass.getuser(),
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=3,
    )


def verify(runtime: ApplicationRuntime) -> dict[str, Any]:
    with owner_connection(runtime) as db:
        row = db.execute(
            "SELECT current_setting('server_version_num')::int AS version, "
            "current_setting('data_directory') AS data, "
            "current_setting('listen_addresses') AS listen, "
            "current_setting('port')::int AS port, "
            "current_setting('shared_preload_libraries') AS preload"
        ).fetchone()
        if (
            not row
            or row["version"] != 160014
            or Path(row["data"]).resolve() != runtime.data.resolve()
            or row["listen"] != "127.0.0.1"
            or row["port"] != runtime.port
            or "timescaledb" not in row["preload"].split(",")
        ):
            raise RuntimeError("Application server does not match its owned runtime")
        extension = db.execute(
            "SELECT default_version FROM pg_available_extensions WHERE name='timescaledb'"
        ).fetchone()
        if not extension or extension["default_version"] != TS_VERSION:
            raise RuntimeError("Application Timescale version is not pinned 2.28.1")
        return dict(row)


def running(runtime: ApplicationRuntime) -> bool:
    if not runtime.data.exists():
        return False
    return (
        subprocess.run(
            [str(runtime.binary / "pg_ctl"), "-D", str(runtime.data), "status"],
            capture_output=True,
            text=True,
            timeout=10,
        ).returncode
        == 0
    )


def provision_binaries(runtime: ApplicationRuntime) -> None:
    if runtime.binary.is_dir():
        return
    record = runtime.root / "var/test-postgres16-timescale/installation.json"
    source = json.loads(record.read_text())
    if (
        source.get("owner") != "equityeval-private-timescale-build-v1"
        or source.get("repository") != str(runtime.root)
        or source.get("postgres_version") != PG_VERSION
        or source.get("timescale_version") != TS_VERSION
    ):
        raise RuntimeError("Pinned executable installation must be established first")
    installation = Path(source["bin_dir"]).parent
    if installation.is_symlink() or installation.stat().st_uid != os.getuid():
        raise RuntimeError("Refusing unowned executable installation")
    # Copy executable/library/share files only. Test data and ports are never touched.
    shutil.copytree(installation, runtime.binary.parent, symlinks=True)
    if (
        f"(PostgreSQL) {PG_VERSION}"
        not in run([str(runtime.binary / "postgres"), "--version"]).stdout
    ):
        raise RuntimeError("Copied PostgreSQL does not match the pinned version")
    provenance = {
        "source_installation": str(installation),
        "source_manifest": source,
        "application_purpose": "persistent local application; loopback only; no TLS",
        "copied_postgres_sha256": hashlib.sha256(
            (runtime.binary / "postgres").read_bytes()
        ).hexdigest(),
    }
    (runtime.directory / "installation-provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )


def start(runtime: ApplicationRuntime) -> None:
    guard(runtime)
    if running(runtime):
        verify(runtime)
        return
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", runtime.port))
    runtime.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime.directory.chmod(0o700)
    runtime.unix_socket.mkdir(exist_ok=True, mode=0o700)
    runtime.unix_socket.chmod(0o700)
    runtime.record.write_text(json.dumps(runtime.identity, indent=2) + "\n")
    runtime.record.chmod(0o600)
    provision_binaries(runtime)
    if not runtime.data.exists():
        run(
            [
                str(runtime.binary / "initdb"),
                "-D",
                str(runtime.data),
                "--auth-local=peer",
                "--auth-host=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
            ]
        )
    options = (
        f"-h 127.0.0.1 -p {runtime.port} -k {runtime.unix_socket} "
        "-c shared_buffers=64MB -c max_connections=40 "
        "-c shared_preload_libraries=timescaledb -c timescaledb.telemetry_level=off "
        "-c timescaledb.max_background_workers=4"
    )
    run(
        [
            str(runtime.binary / "pg_ctl"),
            "-D",
            str(runtime.data),
            "-l",
            str(runtime.directory / "server.log"),
            "-o",
            options,
            "-w",
            "start",
        ]
    )
    verify(runtime)


def migrate(runtime: ApplicationRuntime, url: URL) -> None:
    guard(runtime)
    verify(runtime)
    with owner_connection(runtime) as db:
        role = db.execute(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
            "FROM pg_roles WHERE rolname=%s",
            (runtime.role,),
        ).fetchone()
        if role is not None and any(role.values()):
            raise RuntimeError("Configured application login is privileged; refusing adoption")
        if role is None:
            db.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(runtime.role), sql.Literal(url.password))
            )
        if not db.execute(
            "SELECT 1 FROM pg_database WHERE datname=%s", (runtime.database,)
        ).fetchone():
            db.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                    sql.Identifier(runtime.database)
                )
            )
    # Migration ownership uses this cluster's owner-only peer socket, not runtime credentials.
    owner_url = URL.create(
        "postgresql+psycopg",
        username=getpass.getuser(),
        database=runtime.database,
        query={"host": str(runtime.unix_socket), "port": str(runtime.port)},
    ).render_as_string(hide_password=False)
    config = Config(str(runtime.root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", owner_url.replace("%", "%%"))
    alembic_command.upgrade(config, "head")
    with owner_connection(runtime, runtime.database) as db:
        db.execute(sql.SQL("GRANT equity_runtime TO {}").format(sql.Identifier(runtime.role)))
        migration = db.execute("SELECT version_num FROM alembic_version").fetchone()
        if migration is None:
            raise RuntimeError("Migration revision is missing")
    # Verify the actual application login without exposing its URL/password.
    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row, connect_timeout=3) as db:
        membership = db.execute(
            "SELECT pg_has_role(current_user,'equity_runtime','member') AS ok"
        ).fetchone()
        if membership is None or not membership["ok"]:
            raise RuntimeError("Application login lacks runtime membership")
        print(
            {
                "migration": migration["version_num"],
                "application_user": db.info.user,
                "runtime_membership": membership["ok"],
            }
        )


def inspect(runtime: ApplicationRuntime) -> None:
    guard(runtime)
    verify(runtime)
    with owner_connection(runtime, runtime.database) as db:
        tables = (
            "source_policy_revisions",
            "issuers",
            "securities",
            "mapping_revisions",
            "source_captures",
            "normalization_batches",
        )
        revision = db.execute("SELECT version_num FROM alembic_version").fetchone()
        print(f"Application migration: {revision['version_num'] if revision else 'missing'}")
        for table in tables:
            existing = db.execute("SELECT to_regclass(%s) AS name", (table,)).fetchone()
            if existing and existing["name"]:
                row = db.execute(
                    sql.SQL("SELECT count(*) AS count FROM {}").format(sql.Identifier(table))
                ).fetchone()
                assert row is not None
                print(f"{table}: {row['count']}")
        print("Application storage verified; no financial or policy rows modified by inspection.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "migrate", "inspect", "status", "stop"))
    args = parser.parse_args()
    runtime, url = configuration()
    guard(runtime)
    if args.action == "start":
        start(runtime)
    elif args.action == "migrate":
        migrate(runtime, url)
    elif args.action == "inspect":
        inspect(runtime)
    elif args.action == "status":
        verify(runtime)
        print(f"Application PG16/Timescale ready on 127.0.0.1:{runtime.port}")
    elif running(runtime):
        verify(runtime)
        run([str(runtime.binary / "pg_ctl"), "-D", str(runtime.data), "-m", "fast", "-w", "stop"])


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        RuntimeError,
        psycopg.Error,
        SQLAlchemyError,
        subprocess.SubprocessError,
    ) as error:
        # Connection errors / utility DDL can embed credentials; never print exception text.
        print(
            f"Application PostgreSQL failed ({type(error).__name__}); "
            "check the owned runtime and local configuration.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
