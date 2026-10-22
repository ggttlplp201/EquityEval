"""Run only the reviewed synthetic proof in a bounded disposable Docker container."""

import argparse
import json
import os
import selectors
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

from scripts.crcl_pdf_runtime import MAX_OUTPUT, canonical, safe_relative


def bounded_stream(command: list[str], destination: Path, *, limit: int, timeout: float) -> None:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert process.stdout is not None
    deadline = time.monotonic() + timeout
    count = 0
    try:
        with selectors.DefaultSelector() as selector, destination.open("xb") as output:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("runtime_export_wall_limit")
                if not selector.select(remaining):
                    raise TimeoutError("runtime_export_wall_limit")
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                count += len(chunk)
                if count > limit:
                    raise ValueError("runtime_export_byte_limit")
                output.write(chunk)
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
            if process.returncode:
                raise ValueError("runtime_export_process_failed")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()


def extract_output(archive: Path, destination: Path) -> None:
    reserved = {"container.json", "process.json", "export.json", "output-manifest.json"}
    with tarfile.open(archive, mode="r:") as bundle:
        members: list[tarfile.TarInfo] = []
        total = 0
        names: set[str] = set()
        for member in bundle:
            if len(members) >= 3000:
                raise ValueError("runtime_export_member_limit")
            members.append(member)
            name = member.name.removeprefix("./").removesuffix("/")
            if member.isdir() and name in ("", "."):
                continue
            if (
                not safe_relative(name)
                or name in names
                or name.split("/", 1)[0] in reserved
                or not (member.isdir() or member.isfile())
                or not 0 <= member.size <= 32 * 1024 * 1024
            ):
                raise ValueError("runtime_export_member_invalid")
            names.add(name)
            total += member.size
            if total > MAX_OUTPUT:
                raise ValueError("runtime_export_aggregate_limit")
        for member in members:
            name = member.name.removeprefix("./").removesuffix("/")
            if member.isdir() and name in ("", "."):
                continue
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.extractfile(member)
                assert source is not None
                with source, target.open("xb") as output:
                    while chunk := source.read(65536):
                        output.write(chunk)


def export_live_output(identifier: str, destination: Path) -> None:
    # Docker cp reads the underlying container filesystem and can omit tmpfs.
    # Execute tar inside the live mount namespace, bounding the stream on the host.
    try:
        with tempfile.TemporaryDirectory(prefix="equity-runtime-export-") as directory:
            archive = Path(directory) / "output.tar"
            bounded_stream(
                ["docker", "exec", identifier, "tar", "-C", "/out", "-cf", "-", "."],
                archive,
                limit=MAX_OUTPUT + 8 * 1024 * 1024,
                timeout=120,
            )
            extract_output(archive, destination)
        receipt = {"status": "exported", "method": "bounded-live-container-tar"}
    except (OSError, ValueError, TimeoutError, subprocess.TimeoutExpired) as error:
        receipt = {
            "status": "blocked",
            "reason": type(error).__name__,
            "method": "bounded-live-container-tar",
        }
        (destination / "export.json").write_bytes(canonical(receipt))
        raise
    (destination / "export.json").write_bytes(canonical(receipt))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    command = [
        "docker",
        "create",
        "--network",
        "none",
        "--cpus",
        "1",
        "--memory",
        "2g",
        "--memory-swap",
        "2g",
        "--pids-limit",
        "64",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "65534:65534",
        "--tmpfs",
        "/out:rw,noexec,nosuid,nodev,size=768m,mode=1777",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
        args.image,
        "sleep",
        "3600",
    ]
    identifier = subprocess.check_output(command, text=True).strip()
    try:
        subprocess.run(["docker", "start", identifier], check=True, capture_output=True)
        inspection = json.loads(subprocess.check_output(["docker", "inspect", identifier]))[0]
        config = inspection["HostConfig"]
        if (
            config["NetworkMode"] != "none"
            or config["Memory"] != 2147483648
            or config["MemorySwap"] != 2147483648
            or config["NanoCpus"] != 1000000000
            or config["PidsLimit"] != 64
            or not config["ReadonlyRootfs"]
            or inspection["Config"]["User"] != "65534:65534"
        ):
            raise ValueError("runtime_container_configuration")
        receipt = {
            "imageId": inspection["Image"],
            "containerId": identifier,
            "configuration": config,
            "command": command,
        }
        (args.output / "container.json").write_bytes(canonical(receipt))
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    identifier,
                    "/opt/runtime/bin/python",
                    "-m",
                    "scripts.run_crcl_pdf_proof",
                ],
                timeout=1500,
                check=False,
                capture_output=True,
            )
            process = {
                "exitCode": result.returncode,
                "wallTimeout": False,
                "stdout": result.stdout[:65536].decode(errors="replace"),
                "stderr": result.stderr[:65536].decode(errors="replace"),
            }
        except subprocess.TimeoutExpired as error:
            process = {
                "exitCode": None,
                "wallTimeout": True,
                "stdout": (error.stdout or b"")[:65536].decode(errors="replace"),
                "stderr": (error.stderr or b"")[:65536].decode(errors="replace"),
            }
        (args.output / "process.json").write_bytes(canonical(process))
        if process["wallTimeout"]:
            (args.output / "export.json").write_bytes(
                canonical(
                    {
                        "status": "blocked",
                        "reason": "worker_timeout_no_quiescence",
                        "method": "no-export-container-removal-required",
                    }
                )
            )
            raise ValueError("runtime_worker_wall_timeout")
        export_live_output(identifier, args.output)
        if process["exitCode"] != 0:
            raise ValueError("runtime_synthetic_proof_failed")
    finally:
        subprocess.run(["docker", "rm", "-f", identifier], check=True, capture_output=True)


if __name__ == "__main__":
    main()
