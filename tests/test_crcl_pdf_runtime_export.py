"""Bounded live-container output export and durable synthetic checkpoints."""

import io
import json
import sys
import tarfile

import pytest


def test_command_stream_blocks_oversize_and_timeout(tmp_path):
    from scripts.run_crcl_pdf_container import bounded_stream

    for code, limit, timeout in (
        ("print('x'*1000)", 32, 2),
        ("import time;time.sleep(2)", 32, 0.05),
    ):
        destination = tmp_path / "partial"
        with pytest.raises((ValueError, TimeoutError)):
            bounded_stream([sys.executable, "-c", code], destination, limit=limit, timeout=timeout)
        assert not destination.exists()


def test_export_archive_rejects_traversal_links_and_host_receipt_collision(tmp_path):
    from scripts.run_crcl_pdf_container import extract_output

    for i, name in enumerate(("../escape", "container.json", "link")):
        archive = tmp_path / f"{i}.tar"
        with tarfile.open(archive, "w") as bundle:
            member = tarfile.TarInfo(name)
            if name == "link":
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                bundle.addfile(member)
            else:
                member.size = 1
                bundle.addfile(member, io.BytesIO(b"x"))
        destination = tmp_path / str(i)
        destination.mkdir()
        with pytest.raises(ValueError):
            extract_output(archive, destination)


def test_export_preserves_failed_worker_intermediate_results(tmp_path):
    from scripts.run_crcl_pdf_container import extract_output

    archive = tmp_path / "live.tar"
    with tarfile.open(archive, "w") as bundle:
        for name, body in (
            ("./controls.json", b'{"status":"controls_proven"}'),
            ("./synthetic-progress.json", b'{"compressedStream":{"reason":"exact"}}'),
        ):
            member = tarfile.TarInfo(name)
            member.size = len(body)
            bundle.addfile(member, io.BytesIO(body))
    destination = tmp_path / "out"
    destination.mkdir()
    extract_output(archive, destination)
    assert (
        json.loads((destination / "synthetic-progress.json").read_bytes())["compressedStream"][
            "reason"
        ]
        == "exact"
    )


def test_proof_result_is_checkpointed_before_assertion(tmp_path):
    from scripts.run_crcl_pdf_proof import CheckpointResults

    checkpoint = tmp_path / "progress.json"
    results = CheckpointResults(checkpoint)
    results["compressedStream"] = {"status": "blocked", "reason": "actual_reason"}
    assert json.loads(checkpoint.read_bytes())["compressedStream"]["reason"] == "actual_reason"


def test_failed_probe_keeps_failure_runs_independent_and_skips_dependents(tmp_path):
    from scripts.run_crcl_pdf_proof import CheckpointResults

    results = CheckpointResults(tmp_path / "progress.json")
    results.probe("first", lambda: {"reason": "unexpected"}, lambda row: False)
    results.probe("independent", lambda: {"ok": True}, lambda row: row["ok"])
    results.probe(
        "dependent", lambda: pytest.fail("must not execute"), lambda row: True, requires=("first",)
    )
    saved = json.loads((tmp_path / "progress.json").read_bytes())
    assert saved["checks"] == {"first": "failed", "independent": "passed", "dependent": "skipped"}
    assert saved["dependent"]["reason"] == "prerequisite_failed"
    assert saved["first"]["reason"] == "unexpected"


def test_supervisor_timeout_kills_container_without_exporting_mutable_tmpfs(monkeypatch, tmp_path):
    import subprocess

    from scripts import run_crcl_pdf_container as module

    output = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["runner", "--image", "pinned", "--output", str(output)])
    config = {
        "HostConfig": {
            "NetworkMode": "none",
            "Memory": 2147483648,
            "MemorySwap": 2147483648,
            "NanoCpus": 1000000000,
            "PidsLimit": 64,
            "ReadonlyRootfs": True,
        },
        "Config": {"User": "65534:65534"},
        "Image": "pinned",
    }
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda command, **kwargs: (
            "container" if command[1] == "create" else json.dumps([config]).encode()
        ),
    )
    removed = []

    def run(command, **kwargs):
        if command[1] == "exec":
            raise subprocess.TimeoutExpired(command, 1500)
        if command[1] == "rm":
            removed.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(
        module, "export_live_output", lambda *args: pytest.fail("mutable export forbidden")
    )
    with pytest.raises(ValueError, match="wall_timeout"):
        module.main()
    assert removed
    assert (
        json.loads((output / "export.json").read_bytes())["reason"]
        == "worker_timeout_no_quiescence"
    )
