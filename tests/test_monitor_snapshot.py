"""D4a saved UI is deterministic, separately dated and stripped of private storage metadata."""

import json
from copy import deepcopy

import pytest

from scripts import export_monitor_snapshot as exporter


def test_shipped_snapshot_matches_real_pinned_check():
    assert (exporter.ROOT / exporter.OUTPUT).read_text() == exporter.export()
    audit = exporter.read_audit()
    data = exporter.project(audit)
    assert data["outcome"] == "no_change" and data["filingCount"] == 6
    assert data["newCount"] == data["amendmentCount"] == 0
    assert data["checkedAt"] == "2026-09-21T20:36:50.335318Z"
    assert data["cutoff"] == "2026-09-21T20:32:51Z"
    assert data["checkedAt"] != data["filings"][0]["capturedAt"]
    counts = {r["id"]: r["value"] for r in data["counts"]}
    assert counts["source_captures"] == 12 and counts["source_fetch_attempts"] == 13
    assert counts["source_bootstrap"] == 3 and counts["sec_filing_monitor"] == 1
    assert counts["source_attempt_payloads"] == 1 and counts["normalization_batches"] == 0
    assert (
        data["attempts"][0]["status"] == 200 and data["attempts"][0]["state"] == "content_unchanged"
    )
    assert data["attempts"][0]["reusedCaptureId"] == data["baseline"]["captureIds"][0]


def test_monitor_projection_drops_unreviewed_private_fields():
    audit = deepcopy(exporter.read_audit())
    for node in (
        audit,
        audit["result"],
        *audit["captures"],
        *audit["attempts"],
        audit["result"]["coverage"],
        audit["result"]["history"]["current"],
    ):
        node["private_detail"] = "postgresql://private:secret@localhost/example"
        node["blob_key"] = "/private/raw/file.gz"
    body = json.dumps(exporter.project(audit))
    assert all(x not in body for x in ("private_detail", "blob_key", "/private/", "postgresql:"))


def test_monitor_audit_drift_requires_new_review(tmp_path):
    target = tmp_path / exporter.AUDIT
    target.parent.mkdir(parents=True)
    target.write_bytes((exporter.ROOT / exporter.AUDIT).read_bytes() + b"\n")
    with pytest.raises(ValueError, match="audit changed"):
        exporter.export(tmp_path)


@pytest.mark.parametrize("field", ["scheduler", "history_verified", "dispatch"])
def test_monitor_snapshot_cannot_promote_unsupported_activity(field):
    audit = deepcopy(exporter.read_audit())
    if field == "scheduler":
        audit["scheduler"] = "running"
    elif field == "history_verified":
        audit["protected_history_verified"] = False
    else:
        audit["result"]["downstream"]["dispatched"] = True
    with pytest.raises(ValueError, match="reviewed no-dispatch"):
        exporter.project(audit)


def test_monitor_links_must_be_reviewed_public_sec_sources():
    audit = deepcopy(exporter.read_audit())
    audit["captures"][0]["request_url"] = "file:///private/raw/source"
    with pytest.raises(ValueError, match="public SEC"):
        exporter.project(audit)


def test_verification_errors_do_not_leak_connection_details(monkeypatch, capsys):
    monkeypatch.setattr(exporter, "export", lambda: "not written")
    monkeypatch.setattr("sys.argv", ["export_monitor_snapshot", "--verify-application"])

    def fail():
        raise RuntimeError("postgresql://private:secret@localhost/example")

    monkeypatch.setattr(exporter, "verify_application", fail)
    with pytest.raises(SystemExit, match=r"^Monitor verification failed \(RuntimeError\)\.$"):
        exporter.main()
    assert capsys.readouterr().out == ""
