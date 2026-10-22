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
