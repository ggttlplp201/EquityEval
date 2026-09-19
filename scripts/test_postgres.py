"""Manage isolated native PG16 or required PG16 + Timescale test runtimes."""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMESCALE_VERSION = "2.28.1"
PROFILES = ("native-pg16", "timescale-pg16")
DEFAULT_PROFILE = "timescale-pg16"


@dataclass(frozen=True)
class Runtime:
    profile: str
    runtime: Path
    data: Path
    record: Path
    port: int
    socket: Path
    owner: str


def runtime_for(profile: str) -> Runtime:
    if profile not in PROFILES:
        raise ValueError(f"Unknown test database profile: {profile}")
    native = profile == "native-pg16"
    directory = ROOT / "var" / ("test-postgres16" if native else "test-postgres16-timescale")
    suffix = hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
    return Runtime(
        profile,
        directory,
        directory / "data",
        directory / "runtime.json",
        55432 if native else 55433,
        Path("/tmp") / f"equityeval-{'pg16' if native else 'pg16ts'}-{suffix}",
        "equityeval-isolated-test-postgres-v1"
        if native
        else "equityeval-isolated-test-timescale-v1",
    )


def command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def binary_directory(runtime: Runtime) -> Path:
    native = runtime.profile == "native-pg16"
    candidates = [
        os.environ.get("EQUITY_TEST_PG_BIN" if native else "EQUITY_TEST_TIMESCALE_PG_BIN")
    ]
    if runtime.record.is_file():
        record = json.loads(runtime.record.read_text())
        candidates.append(record.get("bin_dir"))
    installation_record = runtime.runtime / "installation.json"
    if not native and installation_record.is_file():
        installation = json.loads(installation_record.read_text())
        if installation.get("timescale_version") != TIMESCALE_VERSION:
            raise RuntimeError("Private Timescale installation is not the pinned version.")
        candidates.append(installation.get("bin_dir"))
    if native:
        candidates += [
            "/opt/homebrew/opt/postgresql@16/bin",
            "/usr/local/opt/postgresql@16/bin",
            "/usr/lib/postgresql/16/bin",
        ]
    postgres = shutil.which("postgres") if native else None
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
        "PostgreSQL 16 binaries are required. Native profile: set EQUITY_TEST_PG_BIN. "
        "Timescale profile: run scripts/setup_test_timescale.py or set "
        "EQUITY_TEST_TIMESCALE_PG_BIN to an installation with the pinned extension."
    )


def guard_paths(runtime: Runtime) -> None:
    for path in (ROOT / "var", runtime.runtime, runtime.data, runtime.record, runtime.socket):
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlink in test runtime: {path}")
        if path.exists() and path.stat().st_uid != os.getuid():
            raise RuntimeError(f"Test runtime path belongs to another user: {path}")
    if runtime.record.exists():
        record = json.loads(runtime.record.read_text())
        expected = {
            "owner": runtime.owner,
            "data_dir": str(runtime.data),
            "socket_dir": str(runtime.socket),
            "port": runtime.port,
        }
        if any(record.get(key) != value for key, value in expected.items()):
            raise RuntimeError(
                "Runtime ownership record does not match this repository; refusing control."
            )
    elif runtime.data.exists():
        raise RuntimeError(
            "Data directory exists without this helper's ownership record; refusing control."
        )
    if runtime.data.exists() and (runtime.data / "PG_VERSION").read_text().strip() != "16":
        raise RuntimeError("Refusing to control a data directory that is not PostgreSQL 16.")


def running(binary: Path, runtime: Runtime) -> bool:
    return (
        runtime.data.exists()
        and command(
            [str(binary / "pg_ctl"), "-D", str(runtime.data), "status"], check=False
        ).returncode
        == 0
    )


def verify(binary: Path, runtime: Runtime) -> None:
    result = command(
        [
            str(binary / "psql"),
            "-X",
            "-h",
            "127.0.0.1",
            "-p",
            str(runtime.port),
            "-d",
            "postgres",
            "-At",
            "-c",
            "SELECT current_setting('server_version_num'), current_setting('data_directory')",
        ]
    )
    version, data = result.stdout.strip().split("|", maxsplit=1)
    if not 160000 <= int(version) < 170000 or Path(data).resolve() != runtime.data.resolve():
        raise RuntimeError(f"Port {runtime.port} is not serving this repository's PG16 cluster.")
    if runtime.profile == "timescale-pg16":
        extension = command(
            [
                str(binary / "psql"),
                "-X",
                "-h",
                "127.0.0.1",
                "-p",
                str(runtime.port),
                "-d",
                "postgres",
                "-At",
                "-c",
                "SELECT default_version FROM pg_available_extensions WHERE name='timescaledb'",
            ]
        ).stdout.strip()
        if extension != TIMESCALE_VERSION:
            raise RuntimeError(f"Required Timescale {TIMESCALE_VERSION}, found {extension!r}.")
        preload = command(
            [
                str(binary / "psql"),
                "-X",
                "-h",
                "127.0.0.1",
                "-p",
                str(runtime.port),
                "-d",
                "postgres",
                "-At",
                "-c",
                "SHOW shared_preload_libraries",
            ]
        ).stdout.strip()
        if "timescaledb" not in preload.split(","):
            raise RuntimeError("Required Timescale shared preload is missing.")
    print(
        f"Profile {runtime.profile}: PostgreSQL {version} ready: postgresql://localhost:{runtime.port}/postgres"
    )
    print(f"Runtime: {runtime.record}")


def start(binary: Path, runtime: Runtime) -> None:
    if running(binary, runtime):
        verify(binary, runtime)
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", runtime.port))
    runtime.runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime.socket.mkdir(exist_ok=True, mode=0o700)
    runtime.socket.chmod(0o700)
    if not runtime.data.exists():
        result = command(
            [
                str(binary / "initdb"),
                "--pgdata",
                str(runtime.data),
                "--auth-local=trust",
                "--auth-host=trust",
                "--encoding=UTF8",
                "--locale=C",
            ]
        )
        print(result.stdout, end="")
    runtime.record.write_text(
        json.dumps(
            {
                "owner": runtime.owner,
                "bin_dir": str(binary),
                "data_dir": str(runtime.data),
                "socket_dir": str(runtime.socket),
                "port": runtime.port,
            },
            indent=2,
        )
        + "\n"
    )
    runtime.record.chmod(0o600)
    options = (
        f"-h 127.0.0.1 -p {runtime.port} -k {runtime.socket} "
        "-c shared_buffers=32MB -c max_connections=40"
    )
    if runtime.profile == "timescale-pg16":
        options += (
            " -c shared_preload_libraries=timescaledb"
            " -c timescaledb.telemetry_level=off -c timescaledb.max_background_workers=4"
        )
    result = command(
        [
            str(binary / "pg_ctl"),
            "-D",
            str(runtime.data),
            "-l",
            str(runtime.runtime / "server.log"),
            "-o",
            options,
            "-w",
            "start",
        ]
    )
    print(result.stdout, end="")
    verify(binary, runtime)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"))
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default=os.environ.get("EQUITY_TEST_DB_PROFILE", DEFAULT_PROFILE),
    )
    args = parser.parse_args()
    try:
        runtime = runtime_for(args.profile)
        guard_paths(runtime)
        binary = binary_directory(runtime)
        if args.action == "start":
            start(binary, runtime)
        elif args.action == "status":
            if not running(binary, runtime):
                print("Isolated PostgreSQL 16 test cluster is stopped.")
                return 1
            verify(binary, runtime)
        elif running(binary, runtime):
            # Validate the server's data identity before stopping even this owned cluster.
            verify(binary, runtime)
            result = command(
                [str(binary / "pg_ctl"), "-D", str(runtime.data), "-m", "fast", "-w", "stop"]
            )
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
