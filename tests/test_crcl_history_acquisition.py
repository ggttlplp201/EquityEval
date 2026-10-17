"""The acquisition runner consumes only the committed finite roster and budget."""

import json

import pytest

from scripts.capture_crcl_history import SCOPE_SHA, checked_scope
from scripts.normalize_crcl import ROOT


def test_scope_is_exactly_eleven_bounded_groups_with_final_pair():
    scope = checked_scope()
    assert len(scope["groups"]) == 11
    assert sum(len(g["resources"]) for g in scope["groups"]) == 69
    assert scope["groups"][-1]["resources"] == [
        "company_facts/0001876042",
        "submissions/0001876042",
    ]


def test_changed_roster_is_rejected_before_any_dispatch(tmp_path):
    scope = json.loads((ROOT / "docs/design/d5l/inventory-scope.json").read_text())
    scope["groups"][0]["resources"].append(
        "filing_document/0001876042/0000000000-24-002161/other.pdf"
    )
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(scope))
    with pytest.raises(ValueError, match="scope hash"):
        checked_scope(path)
    assert len(SCOPE_SHA) == 64


def test_unavailable_migration_records_honest_blocked_attempt(tmp_path, monkeypatch):
    from scripts import capture_crcl_history as runner

    monkeypatch.setattr(runner, "ACQUISITION", tmp_path / "attempt.json")
    monkeypatch.setattr(runner, "INTENT", tmp_path / "intent.json")
    monkeypatch.setattr(runner, "MIGRATION", tmp_path / "missing.json")
    result = runner.capture()
    assert result["status"] == "blocked"
    assert result["errorType"] == "FileNotFoundError"
    assert len(result["missingResources"]) == 69
    assert result["beforeRows"] is None and result["originalRowsPreserved"] is None
    assert not (tmp_path / "intent.json").exists()
    with pytest.raises(ValueError, match="already exists"):
        runner.capture()


def test_capture_does_not_clear_reconstruction_archive_failure(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from uuid import uuid4

    from scripts import capture_crcl_history as runner
    from scripts import recover_crcl_history as recovery

    baseline = {}
    migration = tmp_path / "migration.json"
    migration.write_text(
        json.dumps(
            {
                "head": "0014_crcl_history_documents",
                "originalRowsPreserved": True,
                "afterRows": baseline,
            }
        )
    )
    monkeypatch.setattr(runner, "ACQUISITION", tmp_path / "attempt.json")
    monkeypatch.setattr(runner, "INTENT", tmp_path / "intent.json")
    monkeypatch.setattr(runner, "MIGRATION", migration)
    db = SimpleNamespace(transaction=lambda: nullcontext(), execute=lambda *a, **k: None)
    url = SimpleNamespace(set=lambda **k: SimpleNamespace(render_as_string=lambda **k: "fixture"))
    monkeypatch.setattr(
        runner.app_postgres, "configuration", lambda: (SimpleNamespace(database="fixture"), url)
    )
    monkeypatch.setattr(runner.app_postgres, "guard", lambda *a: None)
    monkeypatch.setattr(runner.app_postgres, "verify", lambda *a: None)
    monkeypatch.setattr(runner.app_postgres, "owner_connection", lambda *a: nullcontext(db))
    monkeypatch.setattr(
        runner.app_redis,
        "configuration",
        lambda: SimpleNamespace(port=1, client=lambda: nullcontext()),
    )
    monkeypatch.setattr(runner.app_redis, "verify", lambda *a: None)
    monkeypatch.setattr(
        runner.bootstrap, "contact_from_settings", lambda *a: "fixture@example.invalid"
    )
    monkeypatch.setattr(
        runner.bootstrap,
        "registered",
        lambda *a: {
            key: uuid4() for key in ("issuer", "security", "workspace", "source", "policy")
        },
    )
    monkeypatch.setattr(runner, "rows_snapshot", lambda *a: baseline)
    monkeypatch.setattr(runner.psycopg, "connect", lambda *a, **k: nullcontext(db))
    monkeypatch.setattr(
        runner,
        "capture_group",
        lambda *a: {"result": {"state": "completed", "gaps": []}, "captures": []},
    )

    def reconstructed(db, intent, archive):
        return intent | {
            "status": "incomplete",
            "groups": [{"result": {"state": "completed", "gaps": []}} for _ in range(11)],
            "missingResources": [],
            "archiveFailures": ["corrupt-retained-body"],
            "originalRowsPreserved": True,
            "afterRows": baseline,
        }

    monkeypatch.setattr(recovery, "reconstruct", reconstructed)
    result = runner.capture()
    assert result["status"] == "incomplete"
    assert result["archiveFailures"] == ["corrupt-retained-body"]
