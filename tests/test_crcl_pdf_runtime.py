"""D051 cloud packets must bind code, assets, mode, deadline and outputs."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from scripts.crcl_pdf_runtime import REQUIRED_FILES, validate_packet


def packet():
    return {
        "revision": "d051-pdf-runtime-v1",
        "executionId": str(uuid4()),
        "repository": "ggttlplp201/EquityEval",
        "mode": "proof",
        "ref": "refs/heads/codex/d5m-runtime-proof",
        "expiresAt": "2026-10-23T00:00:00Z",
        "toolchainSha256": "a" * 64,
        "files": {name: "b" * 64 for name in REQUIRED_FILES},
        "input": None,
    }


def test_proof_packet_cannot_accept_source_asset_or_wrong_ref():
    now = datetime(2026, 10, 22, tzinfo=UTC)
    good = packet()
    validate_packet(good, ref=good["ref"], repository=good["repository"], now=now)
    for altered in [
        good | {"input": {"assetId": 42}},
        good | {"ref": "refs/heads/main"},
        good | {"executionId": "bad"},
        good | {"files": {"../worker.py": "b" * 64}},
    ]:
        with pytest.raises(ValueError):
            validate_packet(altered, ref=good["ref"], repository=good["repository"], now=now)
    with pytest.raises(ValueError):
        validate_packet(
            good, ref=good["ref"], repository=good["repository"], now=now + timedelta(days=2)
        )


def test_review_packet_requires_exact_positive_asset_ids_and_manifest_identity():
    now = datetime(2026, 10, 22, tzinfo=UTC)
    good = packet() | {"mode": "review", "ref": "refs/heads/codex/d5m-runtime-review"}
    with pytest.raises(ValueError):
        validate_packet(good, ref=good["ref"], repository=good["repository"], now=now)


def test_cloud_recovery_never_redispatches_missing_or_duplicate_run():
    from scripts.crcl_pdf_cloud import recover_execution

    intent = {
        "commit": "a" * 40,
        "ref": "refs/heads/codex/d5m-runtime-proof",
        "workflowPath": ".github/workflows/crcl-pdf-runtime.yml",
    }
    assert recover_execution(intent, []) == {
        "status": "execution_outcome_unknown",
        "redispatch": False,
    }
    run = {
        "id": 7,
        "head_sha": "a" * 40,
        "head_branch": "codex/d5m-runtime-proof",
        "path": intent["workflowPath"],
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
    }
    result = recover_execution(intent, [run])
    assert result["status"] == "output_verification_required" and not result["redispatch"]
    assert (
        recover_execution(intent, [run, run | {"id": 8}])["status"] == "execution_identity_conflict"
    )
    assert recover_execution(intent, [run | {"run_attempt": 2}])["status"] == "unapproved_rerun"


def test_input_archive_rejects_traversal_duplicates_and_changed_bytes(tmp_path):
    import hashlib
    import io
    import tarfile

    from scripts.crcl_pdf_runtime import extract_inputs

    archive = tmp_path / "input.tar.gz"
    body = b"safe"
    expected = {"input.pdf": {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}}
    for i, names in enumerate((["../input.pdf"], ["input.pdf", "input.pdf"], ["input.pdf"])):
        with tarfile.open(archive, "w:gz") as bundle:
            for name in names:
                member = tarfile.TarInfo(name)
                member.size = len(body)
                bundle.addfile(member, io.BytesIO(b"evil" if i == 2 else body))
        with pytest.raises(ValueError):
            extract_inputs(archive, tmp_path / f"output-{i}", expected)


def test_signed_output_identity_and_exact_files_must_match(tmp_path):
    from scripts.crcl_pdf_runtime import canonical, seal_output, verify_output_tree

    good = packet()
    (tmp_path / "proof.json").write_bytes(b"{}")
    manifest = seal_output(tmp_path, good, commit="a" * 40, run_id="17", attempt="1")
    (tmp_path / "output-manifest.json").write_bytes(canonical(manifest))
    verify_output_tree(tmp_path, manifest, good, commit="a" * 40, run_id="17", attempt="1")
    for changed in (
        manifest | {"runId": "18"},
        manifest | {"commit": "b" * 40},
        manifest | {"executionId": str(uuid4())},
    ):
        with pytest.raises(ValueError):
            verify_output_tree(tmp_path, changed, good, commit="a" * 40, run_id="17", attempt="1")
    (tmp_path / "proof.json").write_bytes(b'{"altered":true}')
    with pytest.raises(ValueError):
        verify_output_tree(tmp_path, manifest, good, commit="a" * 40, run_id="17", attempt="1")


def test_retained_cloud_intent_recovers_without_current_packet_or_checkout(tmp_path):
    from scripts.crcl_pdf_cloud import load_retained_intent, write_exclusive

    execution_id = str(uuid4())
    intent = {
        "revision": "d051-cloud-execution-v1",
        "executionId": execution_id,
        "repository": "ggttlplp201/EquityEval",
        "commit": "a" * 40,
        "ref": "refs/heads/codex/d5m-runtime-proof",
        "packetSha256": "b" * 64,
        "workflowPath": ".github/workflows/crcl-pdf-runtime.yml",
        "mode": "proof",
        "runAttempt": 1,
    }
    write_exclusive(tmp_path / f"{execution_id}.intent.json", intent)
    assert load_retained_intent(tmp_path, execution_id, "a" * 40) == intent
    with pytest.raises(ValueError):
        load_retained_intent(tmp_path, execution_id, "c" * 40)
    with pytest.raises(ValueError):
        load_retained_intent(tmp_path, "../bad", "a" * 40)


def test_synthetic_image_fixture_is_drawn_by_page_contents():
    from scripts.run_crcl_pdf_proof import image_pdf

    body = image_pdf(b"compressed", width=32768, height=32768, rgb=False)
    assert b"/Contents 5 0 R" in body
    assert b"/Im1 Do" in body
    assert b"/Width 32768 /Height 32768" in body
    assert b"/Filter /FlateDecode" in body


def test_proof_ref_update_requires_exact_failed_predecessor_and_descendant():
    from scripts.crcl_pdf_cloud import validate_ref_update

    intent = {"commit": "b" * 40, "predecessor": {"commit": "a" * 40}}
    validate_ref_update(intent, "a" * 40, True)
    for remote, ancestor in (("c" * 40, True), ("a" * 40, False), (None, True)):
        with pytest.raises(ValueError):
            validate_ref_update(intent, remote, ancestor)
    with pytest.raises(ValueError):
        validate_ref_update(intent | {"commit": "a" * 40}, "a" * 40, True)
    validate_ref_update({"commit": "a" * 40}, None, False)
    with pytest.raises(ValueError):
        validate_ref_update({"commit": "a" * 40}, "a" * 40, True)


def test_predecessor_packet_rejects_wrong_outcome_or_reused_identity():
    from scripts.crcl_pdf_runtime import validate_predecessor

    previous = {
        "executionId": str(uuid4()),
        "commit": "a" * 40,
        "packetSha256": "b" * 64,
        "intentSha256": "c" * 64,
        "runReceiptSha256": "d" * 64,
        "runId": 17,
        "runAttempt": 1,
        "conclusion": "failure",
    }
    validate_predecessor(previous)
    for changed in (
        previous | {"conclusion": "success"},
        previous | {"runAttempt": 2},
        previous | {"runReceiptSha256": "wrong"},
    ):
        with pytest.raises(ValueError):
            validate_predecessor(changed)
    good = packet() | {"predecessor": previous}
    now = datetime(2026, 10, 22, tzinfo=UTC)
    validate_packet(good, ref=good["ref"], repository=good["repository"], now=now)
    good["executionId"] = previous["executionId"]
    with pytest.raises(ValueError):
        validate_packet(good, ref=good["ref"], repository=good["repository"], now=now)


def test_ca_bootstrap_matches_reviewed_package_derivation():
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    pin = json.loads((root / "infra/pdf-runtime/toolchain.json").read_bytes())["caBootstrap"]
    bundle = (root / "infra/pdf-runtime/ubuntu-ca-bootstrap.pem").read_bytes()
    assert len(bundle) == pin["pemBytes"] == 219342
    assert hashlib.sha256(bundle).hexdigest() == pin["pemSha256"]
    assert bundle.count(b"-----BEGIN CERTIFICATE-----") == pin["certificateCount"] == 146
    docker = (root / "infra/pdf-runtime/Dockerfile").read_text()
    assert docker.index("ubuntu-ca-bootstrap.pem") < docker.index("apt-get update")
    assert pin["pemSha256"] in docker
    assert "Verify-Peer" not in docker and "--allow-unauthenticated" not in docker


@pytest.mark.parametrize("moved", [None, "c" * 40])
def test_proof_ref_push_lease_rejects_post_preflight_deletion_or_move(monkeypatch, tmp_path, moved):
    import subprocess

    from scripts.crcl_pdf_cloud import push_execution_ref

    intent = {
        "commit": "b" * 40,
        "ref": "refs/heads/codex/d5m-runtime-proof",
        "predecessor": {"commit": "a" * 40},
    }

    def race(command, **kwargs):
        lease = f"--force-with-lease={intent['ref']}:{'a' * 40}"
        assert lease in command and "--force" not in command
        assert moved != "a" * 40
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", race)
    with pytest.raises(subprocess.CalledProcessError):
        push_execution_ref(tmp_path, intent)


def test_proof_ref_push_verifies_remote_after_atomic_update(monkeypatch, tmp_path):
    import subprocess

    from scripts.crcl_pdf_cloud import push_execution_ref

    intent = {
        "commit": "b" * 40,
        "ref": "refs/heads/codex/d5m-runtime-proof",
        "predecessor": {"commit": "a" * 40},
    }
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: f"{'c' * 40}\t{intent['ref']}\n"
    )
    with pytest.raises(ValueError, match="Post-push"):
        push_execution_ref(tmp_path, intent)


@pytest.mark.parametrize("delete", [False, True])
def test_real_git_lease_blocks_changed_predecessor_even_when_still_ancestor(tmp_path, delete):
    import subprocess

    from scripts.crcl_pdf_cloud import push_execution_ref, validate_ref_update

    checkout = tmp_path / "checkout"
    remote = tmp_path / "remote.git"
    checkout.mkdir()

    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=checkout, text=True, stderr=subprocess.DEVNULL
        ).strip()

    git("init", "-q")
    git("init", "--bare", "-q", str(remote))
    git("remote", "add", "origin", str(remote))
    commits = []
    for value in ("a", "c", "b"):
        (checkout / "value").write_text(value)
        git("add", "value")
        git(
            "-c",
            "user.name=Proof test",
            "-c",
            "user.email=proof@example.invalid",
            "commit",
            "-qm",
            value,
        )
        commits.append(git("rev-parse", "HEAD"))
    prior, moved, candidate = commits
    ref = "refs/heads/codex/d5m-runtime-proof"
    git("push", "origin", f"{prior}:{ref}")
    intent = {"commit": candidate, "ref": ref, "predecessor": {"commit": prior}}
    validate_ref_update(intent, prior, True)
    if delete:
        git("--git-dir", str(remote), "update-ref", "-d", ref)
    else:
        git("push", "origin", f"{moved}:{ref}")
    with pytest.raises(subprocess.CalledProcessError):
        push_execution_ref(checkout, intent)
    expected = "" if delete else f"{moved}\t{ref}"
    assert git("ls-remote", "origin", ref) == expected
