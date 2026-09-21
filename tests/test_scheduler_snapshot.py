"""Saved scheduler provenance, operational honesty and allowlisted UI data."""

import json
from copy import deepcopy

import pytest

from scripts import export_scheduler_snapshot as exporter


def test_pinned_real_slot_and_paused_snapshot():
    assert (exporter.ROOT / exporter.OUTPUT).read_text() == exporter.export()
    data = exporter.project(exporter.read_audit())
    assert data["active"] is False and data["health"] == "paused"
    assert data["service"] == "not_configured" and data["epoch"] == 2
    slot = data["slots"][0]
    assert slot["index"] == 0 and slot["outcome"] == "no_change" and slot["eligible"]
    assert slot["nominalAt"] == slot["dueAt"] == "2026-09-21T22:07:00.000000Z"
    assert slot["checkedAt"] == "2026-09-21T22:07:33.362718Z"
    assert slot["filings"] == 6 and slot["newFilings"] == slot["amendments"] == 0
    assert data["actualAttempts"] == 1 and data["reservedUnits"] == data["budgetUnits"] == 3
    counts = {r["id"]: r["value"] for r in data["counts"]}
    assert counts["sec_filing_monitor"] == 2 and counts["source_fetch_attempts"] == 14
    assert counts["source_captures"] == 12 and counts["source_attempt_payloads"] == 2
    assert (
        counts["security_identifiers"]
        == counts["watchlist_memberships"]
        == counts["normalization_batches"]
        == 0
    )


def test_unknown_nested_private_fields_are_dropped():
    value = deepcopy(exporter.read_audit())
    nodes = [
        value,
        value["snapshot"],
        value["snapshot"]["config"],
        *value["snapshot"]["slots"],
        *value["snapshot"]["attempts"],
        *value["snapshot"]["revisions"],
        value["monitor_audits"][0]["result"]["coverage"],
        value["monitor_audits"][0]["application_counts"],
    ]
    for node in nodes:
        node["private_detail"] = "postgresql://private:secret@localhost/example"
        node["blob_key"] = "/private/raw/body.gz"
    body = json.dumps(exporter.project(value))
    assert all(v not in body for v in ("private_detail", "blob_key", "/private/", "postgresql:"))


@pytest.mark.parametrize(
    "field", ["service", "dispatch", "verified", "version", "monitor_dispatch"]
)
def test_no_live_or_financial_promotions(field):
    value = deepcopy(exporter.read_audit())
    if field == "service":
        value["snapshot"]["service"] = "running"
    elif field == "dispatch":
        value["snapshot"]["downstream_dispatched"] = True
    elif field == "verified":
        value["protected_history_verified"] = False
    elif field == "version":
        value["snapshot"]["version"] = "unknown"
    else:
        value["monitor_audits"][0]["result"]["downstream"]["dispatched"] = True
    with pytest.raises(ValueError, match="verified saved manual"):
        exporter.project(value)


def test_audit_bytes_require_explicit_review(tmp_path):
    target = tmp_path / exporter.AUDIT
    target.parent.mkdir(parents=True)
    target.write_bytes((exporter.ROOT / exporter.AUDIT).read_bytes() + b"\n")
    with pytest.raises(ValueError, match="reviewed evidence"):
        exporter.read_audit(tmp_path)


def test_readonly_verification_failures_do_not_print_credentials(monkeypatch, capsys):
    monkeypatch.setattr(exporter, "export", lambda: "not written")
    monkeypatch.setattr("sys.argv", ["export_scheduler_snapshot", "--verify-application"])

    def fail(_):
        raise RuntimeError("postgresql://private:secret@localhost/example")

    monkeypatch.setattr(exporter, "verify_application", fail)
    with pytest.raises(SystemExit, match=r"^Scheduler verification failed \(RuntimeError\)\.$"):
        exporter.main()
    assert capsys.readouterr().out == ""
