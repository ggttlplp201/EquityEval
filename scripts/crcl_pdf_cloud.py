"""D051 exact-repository execution intent/recovery; never acquires financial sources."""

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from scripts.crcl_pdf_runtime import (
    REPOSITORY,
    canonical,
    digest,
    validate_packet,
    validate_predecessor,
    verify_files,
)

WORKFLOW = ".github/workflows/crcl-pdf-runtime.yml"


def write_exclusive(path: Path, value: dict[str, Any]) -> None:
    data = canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Cloud intent symlink")
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("Cloud intent identity conflict")
        return
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".intent-")
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def recover_execution(intent: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    matching = [
        run
        for run in runs
        if run.get("head_sha") == intent["commit"]
        and run.get("head_branch") == intent["ref"].removeprefix("refs/heads/")
        and run.get("path") == intent["workflowPath"]
    ]
    if not matching:
        return {"status": "execution_outcome_unknown", "redispatch": False}
    if len(matching) != 1:
        return {"status": "execution_identity_conflict", "redispatch": False}
    run = matching[0]
    base = {"runId": run["id"], "runAttempt": run["run_attempt"], "redispatch": False}
    if run["run_attempt"] != 1:
        return base | {"status": "unapproved_rerun"}
    if run["status"] != "completed":
        return base | {"status": "execution_pending"}
    if run.get("conclusion") != "success":
        return base | {"status": "execution_failed", "conclusion": run.get("conclusion")}
    return base | {"status": "output_verification_required"}


class Github:
    """Only the owned repository API; authentication never enters logs or containers."""

    def __init__(self) -> None:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            text=True,
            capture_output=True,
            check=True,
        )
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        token = values.get("password")
        if not token:
            raise ValueError("GitHub credential unavailable")
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
            follow_redirects=False,
        )

    def close(self) -> None:
        self.client.close()

    def get(self, suffix: str) -> dict[str, Any]:
        if not suffix.startswith("/") or ".." in suffix or "://" in suffix:
            raise ValueError("Invalid GitHub repository path")
        response = self.client.get(f"https://api.github.com/repos/{REPOSITORY}{suffix}")
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    def runs(self, commit: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for page in range(1, 11):
            result = self.get(f"/actions/runs?head_sha={commit}&per_page=100&page={page}")
            batch = result["workflow_runs"]
            rows.extend(batch)
            if len(batch) < 100:
                return rows
        raise ValueError("Workflow discovery limit; outcome unknown")


def execution_intent(root: Path, packet_path: Path, commit: str) -> dict[str, Any]:
    packet = json.loads(packet_path.read_bytes())
    if packet_path.read_bytes() != canonical(packet):
        raise ValueError("Execution packet is not canonical")
    validate_packet(packet, ref=packet["ref"], repository=REPOSITORY, now=datetime.now(UTC))
    UUID(packet["executionId"])
    if packet["mode"] != "proof":
        raise ValueError("Real document execution remains separately held")
    verify_files(root, packet["files"])
    if subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=root).strip() != commit:
        raise ValueError("Execution commit is not checked-out HEAD")
    if subprocess.check_output(["git", "status", "--porcelain"], text=True, cwd=root).strip():
        raise ValueError("Execution requires a clean committed tree")
    if digest(root / "infra/pdf-runtime/toolchain.json") != packet["toolchainSha256"]:
        raise ValueError("Execution toolchain mismatch")
    result = {
        "revision": "d051-cloud-execution-v1",
        "executionId": packet["executionId"],
        "repository": REPOSITORY,
        "commit": commit,
        "ref": packet["ref"],
        "packetSha256": digest(packet_path),
        "workflowPath": WORKFLOW,
        "mode": packet["mode"],
        "runAttempt": 1,
    }
    if packet.get("predecessor") is not None:
        result["predecessor"] = packet["predecessor"]
    return result


def load_retained_intent(audit_root: Path, execution_id: str, commit: str) -> dict[str, Any]:
    if str(UUID(execution_id)) != execution_id:
        raise ValueError("Invalid execution identity")
    path = audit_root / f"{execution_id}.intent.json"
    if path.is_symlink():
        raise ValueError("Cloud intent symlink")
    data = path.read_bytes()
    intent: dict[str, Any] = json.loads(data)
    expected = {
        "revision": "d051-cloud-execution-v1",
        "executionId": execution_id,
        "repository": REPOSITORY,
        "commit": commit,
        "ref": "refs/heads/codex/d5m-runtime-proof",
        "packetSha256": intent.get("packetSha256"),
        "workflowPath": WORKFLOW,
        "mode": "proof",
        "runAttempt": 1,
    }
    if "predecessor" in intent:
        validate_predecessor(intent["predecessor"])
        expected["predecessor"] = intent["predecessor"]
    if (
        intent != expected
        or data != canonical(intent)
        or not re.fullmatch(r"[a-f0-9]{40}", commit)
        or not isinstance(intent.get("packetSha256"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", intent["packetSha256"])
    ):
        raise ValueError("Retained execution intent identity mismatch")
    return intent


def validate_ref_update(intent: dict[str, Any], remote_sha: str | None, ancestor: bool) -> None:
    predecessor = intent.get("predecessor")
    if predecessor is None:
        if remote_sha is not None:
            raise ValueError("Execution ref already exists; no implicit rerun")
    elif remote_sha != predecessor["commit"] or not ancestor or intent["commit"] == remote_sha:
        raise ValueError("Proof retry requires exact predecessor and strict fast-forward")


def verify_failed_predecessor(
    root: Path, audit_root: Path, intent: dict[str, Any], api: Github
) -> None:
    predecessor = intent.get("predecessor")
    if predecessor is None:
        return
    validate_predecessor(predecessor)
    old = load_retained_intent(audit_root, predecessor["executionId"], predecessor["commit"])
    old_path = audit_root / f"{predecessor['executionId']}.intent.json"
    receipt = audit_root / predecessor["executionId"] / "run.json"
    if (
        digest(old_path) != predecessor["intentSha256"]
        or old["packetSha256"] != predecessor["packetSha256"]
        or digest(receipt) != predecessor["runReceiptSha256"]
    ):
        raise ValueError("Proof predecessor retained evidence mismatch")
    run = api.get(f"/actions/runs/{predecessor['runId']}")
    if (
        run.get("id") != predecessor["runId"]
        or run.get("head_sha") != predecessor["commit"]
        or run.get("head_branch") != intent["ref"].removeprefix("refs/heads/")
        or run.get("path") != WORKFLOW
        or run.get("run_attempt") != 1
        or run.get("status") != "completed"
        or run.get("conclusion") != "failure"
    ):
        raise ValueError("Proof predecessor live identity changed")


def push_execution_ref(root: Path, intent: dict[str, Any]) -> str:
    # The caller has independently enforced strict ancestry. The explicit lease
    # adds atomic expected-OID comparison; it never authorizes a history rewrite.
    predecessor = intent.get("predecessor")
    expected = predecessor["commit"] if predecessor is not None else ""
    subprocess.run(
        [
            "git",
            "push",
            f"--force-with-lease={intent['ref']}:{expected}",
            "origin",
            f"{intent['commit']}:{intent['ref']}",
        ],
        cwd=root,
        check=True,
    )
    remote = (
        subprocess.check_output(
            ["git", "ls-remote", "origin", intent["ref"]],
            cwd=root,
            text=True,
        )
        .strip()
        .split()
    )
    if remote != [intent["commit"], intent["ref"]]:
        raise ValueError("Post-push execution ref identity mismatch; recover only")
    return remote[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("dispatch-proof", "recover"))
    parser.add_argument(
        "--packet", type=Path, default=Path("infra/pdf-runtime/execution-packet.json")
    )
    parser.add_argument("--commit", required=True)
    parser.add_argument("--execution-id")
    parser.add_argument("--audit-root", type=Path, default=Path("var/d5m-cloud"))
    args = parser.parse_args()
    root = Path.cwd()
    if args.action == "recover" and not args.execution_id:
        raise ValueError("Recovery requires the retained execution UUID")
    execution_id = args.execution_id
    if execution_id is None:
        execution_id = json.loads(args.packet.read_bytes())["executionId"]
    if str(UUID(execution_id)) != execution_id:
        raise ValueError("Invalid execution identity")
    path = args.audit_root / f"{execution_id}.intent.json"
    if path.exists() or args.action == "recover":
        intent = load_retained_intent(args.audit_root, execution_id, args.commit)
        api = Github()
        try:
            print(json.dumps(recover_execution(intent, api.runs(intent["commit"])), sort_keys=True))
        finally:
            api.close()
        return
    intent = execution_intent(root, args.packet, args.commit)
    if intent["executionId"] != execution_id:
        raise ValueError("Dispatch execution identity mismatch")
    api = Github()
    try:
        # Persist before dispatch; future invocations only reconstruct, never redispatch.
        write_exclusive(path, intent)
        existing = subprocess.check_output(
            ["git", "ls-remote", "origin", intent["ref"]], cwd=root, text=True
        )
        rows = [line.split() for line in existing.splitlines() if line.strip()]
        if len(rows) > 1 or (rows and (len(rows[0]) != 2 or rows[0][1] != intent["ref"])):
            raise ValueError("Ambiguous execution ref")
        remote_sha = rows[0][0] if rows else None
        ancestor = False
        if intent.get("predecessor") is not None:
            verify_failed_predecessor(root, args.audit_root, intent, api)
            ancestor = (
                subprocess.run(
                    [
                        "git",
                        "merge-base",
                        "--is-ancestor",
                        intent["predecessor"]["commit"],
                        args.commit,
                    ],
                    cwd=root,
                    check=False,
                ).returncode
                == 0
            )
        validate_ref_update(intent, remote_sha, ancestor)
        remote_head = push_execution_ref(root, intent)
        receipt = {
            "revision": "d051-cloud-dispatch-v1",
            "executionId": intent["executionId"],
            "intentSha256": digest(path),
            "ref": intent["ref"],
            "commit": args.commit,
            "observedAt": datetime.now(UTC).isoformat(),
            "verifiedRemoteHead": remote_head,
        }
        write_exclusive(args.audit_root / f"{intent['executionId']}.dispatch.json", receipt)
        print(json.dumps(recover_execution(intent, api.runs(args.commit)), sort_keys=True))
    finally:
        api.close()


if __name__ == "__main__":
    main()
