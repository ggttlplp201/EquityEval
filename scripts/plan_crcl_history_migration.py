"""Read-only application preflight for the reviewed D050 additive migration."""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from equity_schema.fundamentals_canonical import content_hash

from scripts import app_postgres
from scripts.normalize_crcl import ROOT
from scripts.publish_crcl_fundamentals import _write_exclusive
from scripts.publish_crcl_normalization import rows_snapshot
from scripts.verify_crcl_broader_completion import verify as verify_prior

OUTPUT = ROOT / "docs/research/crcl-history-migration-plan-2026-10-16.json"
MIGRATIONS = ROOT / "infra/migrations/versions"


def plan() -> dict[str, Any]:
    prior = verify_prior()
    stream = io.StringIO()
    config = Config(str(ROOT / "alembic.ini"), output_buffer=stream)
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://localhost/offline_only")
    command.upgrade(config, "0013_real_fundamentals:0014_crcl_history_documents", sql=True)
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as db, db.transaction():
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        row = db.execute("SELECT version_num FROM alembic_version").fetchone()
        if row is None:
            raise ValueError("Application migration head is unavailable")
        head = row["version_num"]
        if head != "0013_real_fundamentals":
            raise ValueError("D5l requires the exact observed 0013 application baseline")
        before = rows_snapshot(db)
        if content_hash(before) != prior["currentRowsHash"]:
            raise ValueError("D5k application baseline changed during preflight")
        functions = db.execute(
            "SELECT p.oid::regprocedure::text AS signature,pg_get_functiondef(p.oid) AS definition,"
            "p.proacl::text AS acl FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname='public' AND p.prokind='f' ORDER BY signature"
        ).fetchall()
    return {
        "kind": "d5l-reviewed-migration-plan",
        "proposal": "dd2d4a9",
        "fromHead": head,
        "toHead": "0014_crcl_history_documents",
        "tableCount": len(before),
        "beforeRows": before,
        "beforeRowsHash": content_hash(before),
        "beforeFunctions": {
            row["signature"]: {
                "definitionHash": hashlib.sha256(row["definition"].encode()).hexdigest(),
                "acl": row["acl"],
            }
            for row in functions
        },
        "migrationFiles": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(MIGRATIONS.glob("[0-9]*.py"))
        },
        "offlineSqlSha256": hashlib.sha256(stream.getvalue().encode()).hexdigest(),
        "changedFunctions": [
            "workflow_valid_bootstrap_plan(jsonb)",
            "market_sec_resource(uuid,uuid,text,text)",
            "workflow_bootstrap_attempt_guard()",
        ],
        "newFunctions": [
            "workflow_valid_bootstrap_plan_v1(jsonb)",
            "market_sec_resource_v1(uuid,uuid,text,text)",
        ],
        "expectedNewTables": [],
        "priorCompletion": prior,
        "publication": False,
        "pdfRuntimeBlocker": "pdf_limits_unavailable: macOS rejects the reviewed 512 MiB RLIMIT_AS",
        "recovery": (
            "Transactional rollback before any V2 intent; retained V2 history forbids downgrade. "
            "Restore backup into a separate owned cluster or reviewed forward correction."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = plan()
    _write_exclusive(args.output, report)
    print(report["beforeRowsHash"], report["offlineSqlSha256"])


if __name__ == "__main__":
    main()
