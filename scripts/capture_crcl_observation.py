"""D047 governed observation-exhibit acquisition, with immutable preservation evidence."""

from __future__ import annotations

import argparse
import json
from typing import Any

import httpx
import psycopg
from dotenv import dotenv_values
from equity_ingest.archive import LocalArchive
from equity_ingest.financial_types import canonical_json
from psycopg.rows import dict_row
from redis.exceptions import RedisError

from scripts import app_postgres, app_redis, bootstrap_crcl
from scripts.capture_crcl_registration import verify as verify_previous
from scripts.capture_crcl_safety import capture_group
from scripts.normalize_crcl import ROOT
from scripts.publish_crcl_normalization import rows_snapshot
from scripts.review_crcl_identity import verify_database_evidence
from scripts.review_crcl_observation import ACQUISITION, END, acquisition_complete

PREFIX = "d5i-observation-2026-10-15-group"
ADDITIONS = frozenset(
    {
        "analysis_requests",
        "analysis_request_keys",
        "analysis_request_state",
        "analysis_executions",
        "analysis_stage_attempts",
        "execution_events",
        "source_fetch_attempts",
        "source_captures",
        "capture_policy_links",
    }
)


def preserved(before: dict[str, list[str]], after: dict[str, list[str]]) -> bool:
    return before.keys() == after.keys() and all(
        set(rows).issubset(after[table]) if table in ADDITIONS else rows == after[table]
        for table, rows in before.items()
    )


def capture() -> None:
    target = ROOT / ACQUISITION
    if target.exists():
        raise ValueError("Saved D5i attempt exists; inspect it, never retry implicitly")
    report: dict[str, Any] = {
        "kind": "d5i-governed-observation-acquisition",
        "proposal": "c55c2cf",
        "status": "blocked",
        "errorType": None,
        "groups": [],
        "beforeRows": None,
        "afterRows": None,
        "originalRowsPreserved": None,
        "note": "Unavailable prerequisites or partial work never establish source completeness.",
    }
    try:
        planned = ((),)
        verify_previous()  # Verify the complete pre-D5i application state before any write.
        runtime, url = app_postgres.configuration()
        app_postgres.guard(runtime)
        app_postgres.verify(runtime)
        cache = app_redis.configuration()
        with cache.client() as client:
            app_redis.verify(cache, client)
        contact = bootstrap_crcl.contact_from_settings(dotenv_values(ROOT / ".env"))
        with app_postgres.owner_connection(runtime, runtime.database) as owner:
            with owner.transaction():
                owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                report["beforeRows"] = rows_snapshot(owner)
            try:
                with psycopg.connect(
                    url.set(drivername="postgresql").render_as_string(hide_password=False),
                    autocommit=True,
                    row_factory=dict_row,
                ) as db:
                    identities = bootstrap_crcl.registered(db)
                    for number, resources in enumerate(planned, 1):
                        result = capture_group(
                            db,
                            identities,
                            resources,
                            number,
                            contact,
                            f"redis://127.0.0.1:{cache.port}/0",
                            request_prefix=PREFIX,
                            worker_id="d5i-observation-capture",
                            inventory_end=END,
                        )
                        request = db.execute(
                            "SELECT request_parameters_hash FROM analysis_requests WHERE id=%s",
                            (result["request_id"],),
                        ).fetchone()
                        if request is None:
                            raise ValueError("Retained request disappeared")
                        result["request_parameters_hash"] = request["request_parameters_hash"]
                        report["groups"].append(result)
                        if result["result"]["state"] != "completed" or result["result"]["gaps"]:
                            break
            finally:
                with owner.transaction():
                    owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    report["afterRows"] = rows_snapshot(owner)
                    report["originalRowsPreserved"] = preserved(
                        report["beforeRows"], report["afterRows"]
                    )
        complete = len(report["groups"]) == len(planned) and all(
            group["result"]["state"] == "completed" and not group["result"]["gaps"]
            for group in report["groups"]
        )
        report["status"] = (
            "captured_pending_review"
            if complete and report["originalRowsPreserved"]
            else "incomplete"
        )
    except (OSError, ValueError, RuntimeError, psycopg.Error, RedisError, httpx.HTTPError) as error:
        report["errorType"] = type(error).__name__
    target.write_text(canonical_json(report) + "\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "groups": len(report["groups"]),
                "preserved": report["originalRowsPreserved"],
                "errorType": report["errorType"],
            }
        )
    )


def verify() -> None:
    report = json.loads((ROOT / ACQUISITION).read_text())
    if not acquisition_complete(report):
        raise ValueError("Acquisition remains incomplete; no full-verification claim")
    archive = LocalArchive(ROOT / "var/raw")
    runtime, _ = app_postgres.configuration()
    app_postgres.guard(runtime)
    app_postgres.verify(runtime)
    with app_postgres.owner_connection(runtime, runtime.database) as owner, owner.transaction():
        owner.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        for group in report["groups"]:
            verify_database_evidence(owner, group, archive)
        current = rows_snapshot(owner)
        if not preserved(report["beforeRows"], report["afterRows"]) or not preserved(
            report["afterRows"], current
        ):
            raise ValueError("Application preservation proof failed")
    captures = [capture for group in report["groups"] for capture in group["captures"]]
    print(
        json.dumps(
            {
                "groups": len(report["groups"]),
                "captures": len(captures),
                "originalRowsPreserved": True,
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "verify"))
    args = parser.parse_args()
    capture() if args.action == "capture" else verify()


if __name__ == "__main__":
    main()
