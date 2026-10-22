"""D051 hash-bound offline PDF runtime; no financial-source acquisition."""

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

REPOSITORY = "ggttlplp201/EquityEval"
REFS = {mode: f"refs/heads/codex/d5m-runtime-{mode}" for mode in ("proof", "review")}
MAX_OUTPUT = 736 * 1024 * 1024
REQUIRED_FILES = frozenset(
    (
        ".github/workflows/crcl-pdf-runtime.yml",
        "infra/pdf-runtime/Dockerfile",
        "infra/pdf-runtime/toolchain.json",
        "infra/pdf-runtime/ubuntu.sources",
        "infra/pdf-runtime/apt-SHA256SUMS",
        "infra/pdf-runtime/Dockerfile.dockerignore",
        "scripts/build_crcl_pdf_runtime.py",
        "scripts/crcl_pdf_runtime.py",
        "scripts/crcl_pdf_cloud.py",
        "scripts/run_crcl_pdf_container.py",
        "scripts/run_crcl_pdf_proof.py",
        "packages/ingest/pdf_review.py",
        "packages/ingest/pdf_review_worker.py",
        "packages/ingest/pdf_exec_worker.py",
        "packages/ingest/pdf_transfer.py",
        "packages/schema/crcl_history.py",
    )
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(65536):
            checksum.update(chunk)
    return checksum.hexdigest()


def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[a-f0-9]{64}", value))


def safe_relative(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and not path.is_absolute()
        and all(p not in {".", ".."} for p in path.parts)
        and str(path) == value
        and "\\" not in value
    )


def validate_packet(packet: dict[str, Any], *, ref: str, repository: str, now: datetime) -> None:
    if (
        packet.get("revision") != "d051-pdf-runtime-v1"
        or repository != REPOSITORY
        or packet.get("repository") != repository
    ):
        raise ValueError("runtime_packet_repository")
    UUID(packet["executionId"])
    mode = packet.get("mode")
    if mode not in REFS or ref != REFS[mode] or packet.get("ref") != ref:
        raise ValueError("runtime_packet_ref")
    expiry = datetime.fromisoformat(packet["expiresAt"])
    if expiry.utcoffset() is None or now.utcoffset() is None or now >= expiry:
        raise ValueError("runtime_packet_expired")
    if not _sha(packet.get("toolchainSha256")):
        raise ValueError("runtime_packet_toolchain")
    files = packet.get("files")
    if (
        not isinstance(files, dict)
        or set(files) != REQUIRED_FILES
        or len(files) > 100
        or any(not safe_relative(k) or not _sha(v) for k, v in files.items())
    ):
        raise ValueError("runtime_packet_files")
    source = packet.get("input")
    if mode == "proof":
        if source is not None:
            raise ValueError("runtime_proof_has_source")
    elif (
        not isinstance(source, dict)
        or any(
            type(source.get(k)) is not int or source[k] <= 0
            for k in ("releaseId", "assetId", "bytes")
        )
        or source["bytes"] > 96 * 1024 * 1024
        or any(
            not _sha(source.get(k))
            for k in ("sha256", "manifestSha256", "transportIntentSha256", "receiptSha256")
        )
    ):
        raise ValueError("runtime_packet_input")


def verify_files(root: Path, files: dict[str, str]) -> None:
    for name, expected in files.items():
        if not safe_relative(name):
            raise ValueError("runtime_file_path")
        path = root / name
        if (
            any(parent.is_symlink() for parent in (path, *path.parents))
            or not path.is_file()
            or digest(path) != expected
        ):
            raise ValueError("runtime_file_hash")


def extract_inputs(archive: Path, destination: Path, expected: dict[str, dict[str, Any]]) -> None:
    """No extraction until every entry has passed the finite manifest boundary."""
    if destination.exists():
        raise ValueError("runtime_input_destination_exists")
    with tempfile.TemporaryFile() as bounded:
        total = 0
        with gzip.open(archive, "rb") as encoded:
            while chunk := encoded.read(65536):
                total += len(chunk)
                if total > 96 * 1024 * 1024:
                    raise ValueError("runtime_input_expansion_limit")
                bounded.write(chunk)
        bounded.seek(0)
        with tarfile.open(fileobj=bounded, mode="r:") as source:
            members = []
            for member in source:
                members.append(member)
                if len(members) > 10:
                    raise ValueError("runtime_input_roster")
            if len(members) != len(expected):
                raise ValueError("runtime_input_roster")
            seen: set[str] = set()
            for member in members:
                if (
                    not member.isfile()
                    or not safe_relative(member.name)
                    or member.name in seen
                    or member.name not in expected
                ):
                    raise ValueError("runtime_input_entry")
                seen.add(member.name)
                if member.size != expected[member.name]["bytes"] or member.size > 32 * 1024 * 1024:
                    raise ValueError("runtime_input_size")
            destination.mkdir()
            for member in members:
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError("runtime_input_missing")
                path = destination / member.name
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as output:
                    while chunk := stream.read(65536):
                        output.write(chunk)
                if digest(path) != expected[member.name]["sha256"]:
                    raise ValueError("runtime_input_hash")


def _probe(code: str, expected: int, timeout: int = 10) -> dict[str, Any]:
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=timeout,
        env={"PATH": os.defpath, "LC_ALL": "C", "TZ": "UTC"},
    )
    if result.returncode != expected:
        raise ValueError(f"runtime_probe_exit:{result.returncode}:{expected}")
    return {
        "exitCode": result.returncode,
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "stdoutSha256": hashlib.sha256(result.stdout).hexdigest(),
        "stderrSha256": hashlib.sha256(result.stderr).hexdigest(),
    }


def prove_controls(output: Path) -> dict[str, Any]:
    if sys.platform != "linux":
        raise ValueError("runtime_linux_required")
    control = {
        name: Path("/sys/fs/cgroup", name).read_text().strip()
        for name in ("memory.max", "memory.swap.max", "cpu.max", "pids.max")
    }
    if (
        control["memory.max"] != "2147483648"
        or control["memory.swap.max"] != "0"
        or control["pids.max"] != "64"
    ):
        raise ValueError("runtime_cgroup_mismatch")
    quota, period = control["cpu.max"].split()
    if quota == "max" or int(quota) != int(period):
        raise ValueError("runtime_cpu_mismatch")
    if os.getuid() == 0:
        raise ValueError("runtime_root_forbidden")
    status = Path("/proc/self/status").read_text()
    security = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
    if (
        int(security["CapEff"].strip(), 16) != 0
        or security["NoNewPrivs"].strip() != "1"
        or security["Seccomp"].strip() != "2"
        or sorted(p.name for p in Path("/sys/class/net").iterdir()) != ["lo"]
    ):
        raise ValueError("runtime_security_boundary_mismatch")
    probes = {
        "addressSpace": _probe(
            "import resource; resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912));\n"
            "try: bytearray(805306368)\n"
            "except MemoryError: raise SystemExit(0)\n"
            "raise SystemExit(1)",
            0,
        ),
        "cpu": _probe(
            "import resource; resource.setrlimit(resource.RLIMIT_CPU,(1,1));\nwhile True: pass", -9
        ),
        "fileSize": _probe(
            "import resource,tempfile,os; resource.setrlimit(resource.RLIMIT_FSIZE,(1024,1024));\n"
            "try:\n"
            " f=tempfile.TemporaryFile(); f.write(b'x'*4096); f.flush()\n"
            "except OSError: raise SystemExit(0)\n"
            "raise SystemExit(1)",
            0,
        ),
        "network": _probe(
            "import socket; s=socket.socket(); s.settimeout(2);\n"
            "try: s.connect(('1.1.1.1',443))\n"
            "except OSError: raise SystemExit(0)\n"
            "raise SystemExit(1)",
            0,
        ),
    }
    result = {
        "status": "controls_proven",
        "cgroups": control,
        "uid": os.getuid(),
        "platform": sys.platform,
        "kernel": os.uname().release,
        "python": sys.version,
        "probes": probes,
        "checkedAt": datetime.now(UTC).isoformat(),
    }
    output.write_bytes(canonical(result))
    return result


def seal_output(
    root: Path, packet: dict[str, Any], *, commit: str, run_id: str, attempt: str
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path == root / "output-manifest.json":
            continue
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ValueError("runtime_output_type")
        if path.is_file():
            count = path.stat().st_size
            total += count
            if count > 32 * 1024 * 1024 or total > MAX_OUTPUT or len(rows) >= 3000:
                raise ValueError("runtime_output_limit")
            rows.append(
                {"path": str(path.relative_to(root)), "bytes": count, "sha256": digest(path)}
            )
    return {
        "revision": "d051-pdf-output-v1",
        "executionId": packet["executionId"],
        "packetSha256": hashlib.sha256(canonical(packet)).hexdigest(),
        "commit": commit,
        "runId": run_id,
        "runAttempt": attempt,
        "files": rows,
        "totalBytes": total,
    }


def verify_output_tree(
    root: Path,
    manifest: dict[str, Any],
    packet: dict[str, Any],
    *,
    commit: str,
    run_id: str,
    attempt: str,
) -> None:
    """Verify content/run binding after external cryptographic attestation verification."""
    path = root / "output-manifest.json"
    if path.is_symlink() or path.read_bytes() != canonical(manifest):
        raise ValueError("runtime_output_manifest_changed")
    expected = seal_output(root, packet, commit=commit, run_id=run_id, attempt=attempt)
    if manifest != expected:
        raise ValueError("runtime_output_identity_or_content_changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("verify-packet", "prove-controls", "seal"))
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prove-controls":
        prove_controls(args.output)
        return
    packet = json.loads(args.packet.read_bytes())
    if args.packet.read_bytes() != canonical(packet):
        raise ValueError("runtime_packet_noncanonical")
    validate_packet(
        packet,
        ref=os.environ["GITHUB_REF"],
        repository=os.environ["GITHUB_REPOSITORY"],
        now=datetime.now(UTC),
    )
    verify_files(Path.cwd(), packet["files"])
    if digest(Path("infra/pdf-runtime/toolchain.json")) != packet["toolchainSha256"]:
        raise ValueError("runtime_toolchain_hash")
    result = (
        {"status": "packet_verified", "executionId": packet["executionId"]}
        if args.action == "verify-packet"
        else seal_output(
            args.output,
            packet,
            commit=os.environ["GITHUB_SHA"],
            run_id=os.environ["GITHUB_RUN_ID"],
            attempt=os.environ["GITHUB_RUN_ATTEMPT"],
        )
    )
    target = args.output if args.action == "verify-packet" else args.output / "output-manifest.json"
    target.write_bytes(canonical(result))


if __name__ == "__main__":
    main()
