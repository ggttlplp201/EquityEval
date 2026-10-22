"""Run only the reviewed synthetic proof in a bounded disposable Docker container."""

import argparse
import json
import subprocess
from pathlib import Path

from scripts.crcl_pdf_runtime import canonical


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
        "1500",
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
        (args.output / "process.json").write_bytes(
            canonical(
                {
                    "exitCode": result.returncode,
                    "stdout": result.stdout[:65536].decode(errors="replace"),
                    "stderr": result.stderr[:65536].decode(errors="replace"),
                }
            )
        )
        subprocess.run(["docker", "cp", f"{identifier}:/out/.", str(args.output)], check=True)
        if result.returncode:
            raise ValueError("runtime_synthetic_proof_failed")
    finally:
        subprocess.run(["docker", "rm", "-f", identifier], check=True, capture_output=True)


if __name__ == "__main__":
    main()
