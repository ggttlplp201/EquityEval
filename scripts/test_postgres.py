"""Manage only this repository's isolated PostgreSQL 16 test cluster."""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "var" / "test-postgres16"
DATA = RUNTIME / "data"
RECORD = RUNTIME / "runtime.json"
PORT = 55432
# The iCloud repository path exceeds macOS's Unix socket path limit.
SOCKET = Path("/tmp") / f"equityeval-pg16-{hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]}"
OWNER = "equityeval-isolated-test-postgres-v1"


def command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def binary_directory() -> Path:
    candidates = [os.environ.get("EQUITY_TEST_PG_BIN")]
    if RECORD.is_file():
        record = json.loads(RECORD.read_text())
        candidates.append(record.get("bin_dir"))
    candidates += [
        "/opt/homebrew/opt/postgresql@16/bin",
        "/usr/local/opt/postgresql@16/bin",
        "/usr/lib/postgresql/16/bin",
    ]
    postgres = shutil.which("postgres")
    if postgres:
        candidates.append(str(Path(postgres).parent))
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        directory = Path(candidate)
        executable = directory / "postgres"
        if not executable.is_file():
            continue
        result = command([str(executable), "--version"], check=False)
        if result.returncode == 0 and "(PostgreSQL) 16." in result.stdout:
            if all((directory / name).is_file() for name in ("initdb", "pg_ctl", "psql")):
                return directory
    raise RuntimeError(
        "PostgreSQL 16 binaries are required. Set EQUITY_TEST_PG_BIN to their bin directory."
    )


def guard_paths() -> None:
    for path in (ROOT / "var", RUNTIME, DATA, RECORD, SOCKET):
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlink in test runtime: {path}")
        if path.exists() and path.stat().st_uid != os.getuid():
            raise RuntimeError(f"Test runtime path belongs to another user: {path}")
    if RECORD.exists():
        record = json.loads(RECORD.read_text())
        expected = {"owner": OWNER, "data_dir": str(DATA), "socket_dir": str(SOCKET), "port": PORT}
        if any(record.get(key) != value for key, value in expected.items()):
            raise RuntimeError(
                "Runtime ownership record does not match this repository; refusing control."
            )
    elif DATA.exists():
        raise RuntimeError(
            "Data directory exists without this helper's ownership record; refusing control."
        )
    if DATA.exists() and (DATA / "PG_VERSION").read_text().strip() != "16":
        raise RuntimeError("Refusing to control a data directory that is not PostgreSQL 16.")


def running(binary: Path) -> bool:
    return (
        DATA.exists()
        and command([str(binary / "pg_ctl"), "-D", str(DATA), "status"], check=False).returncode
        == 0
    )


def verify(binary: Path) -> None:
    result = command(
        [
            str(binary / "psql"),
            "-X",
            "-h",
            "127.0.0.1",
            "-p",
            str(PORT),
            "-d",
            "postgres",
            "-At",
            "-c",
            "SELECT current_setting('server_version_num'), current_setting('data_directory')",
        ]
    )
    version, data = result.stdout.strip().split("|", maxsplit=1)
    if not 160000 <= int(version) < 170000 or Path(data).resolve() != DATA.resolve():
        raise RuntimeError("Port 55432 is not serving this repository's PostgreSQL 16 cluster.")
    print(f"PostgreSQL {version} ready: postgresql://localhost:{PORT}/postgres")
    print(f"Runtime: {RECORD}")


def start(binary: Path) -> None:
    if running(binary):
        verify(binary)
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", PORT))
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    SOCKET.mkdir(exist_ok=True, mode=0o700)
    SOCKET.chmod(0o700)
    if not DATA.exists():
        result = command(
            [
                str(binary / "initdb"),
                "--pgdata",
                str(DATA),
                "--auth-local=trust",
                "--auth-host=trust",
                "--encoding=UTF8",
                "--locale=C",
            ]
        )
        print(result.stdout, end="")
    RECORD.write_text(
        json.dumps(
            {
                "owner": OWNER,
                "bin_dir": str(binary),
                "data_dir": str(DATA),
                "socket_dir": str(SOCKET),
                "port": PORT,
            },
            indent=2,
        )
        + "\n"
    )
    RECORD.chmod(0o600)
    result = command(
        [
            str(binary / "pg_ctl"),
            "-D",
            str(DATA),
            "-l",
            str(RUNTIME / "server.log"),
            "-o",
            f"-h 127.0.0.1 -p {PORT} -k {SOCKET} -c shared_buffers=32MB -c max_connections=40",
            "-w",
            "start",
        ]
    )
    print(result.stdout, end="")
    verify(binary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"))
    args = parser.parse_args()
    try:
        guard_paths()
        binary = binary_directory()
        if args.action == "start":
            start(binary)
        elif args.action == "status":
            if not running(binary):
                print("Isolated PostgreSQL 16 test cluster is stopped.")
                return 1
            verify(binary)
        elif running(binary):
            # Validate the server's data identity before stopping even this owned cluster.
            verify(binary)
            result = command([str(binary / "pg_ctl"), "-D", str(DATA), "-m", "fast", "-w", "stop"])
            print(result.stdout, end="")
        else:
            print("Isolated PostgreSQL 16 test cluster is already stopped.")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Test PostgreSQL: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stdout or "", end="", file=sys.stderr)
            print(error.stderr or "", end="", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
