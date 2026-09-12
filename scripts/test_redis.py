"""Manage only this repository's isolated, disposable Redis test server."""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "var" / "test-redis"
RECORD = RUNTIME / "runtime.json"
CONFIG = RUNTIME / "redis.conf"
PORT = 16380
OWNER = "equityeval-isolated-test-redis-v1"


def command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check, timeout=15)


def binaries() -> tuple[str, str]:
    paths = []
    configured = os.environ.get("EQUITY_TEST_REDIS_BIN")
    if configured:
        paths.append(Path(configured))
    paths.extend([Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path("/usr/bin")])
    available = shutil.which("redis-server")
    if available:
        paths.insert(0, Path(available).parent)
    for path in paths:
        server, cli = path / "redis-server", path / "redis-cli"
        if server.is_file() and cli.is_file():
            return str(server), str(cli)
    raise RuntimeError("Redis binaries required; set EQUITY_TEST_REDIS_BIN to their bin directory")


def guard_paths() -> None:
    for path in (ROOT / "var", RUNTIME, RECORD, CONFIG):
        if path.is_symlink() or (path.exists() and path.stat().st_uid != os.getuid()):
            raise RuntimeError("Refusing unowned or symlinked Redis runtime")
    if RECORD.exists():
        record = json.loads(RECORD.read_text())
        expected = {"owner": OWNER, "runtime_dir": str(RUNTIME), "port": PORT}
        if any(record.get(key) != value for key, value in expected.items()):
            raise RuntimeError("Redis ownership record does not match this repository")
    elif RUNTIME.exists() and any(RUNTIME.iterdir()):
        raise RuntimeError("Redis runtime exists without an ownership record")


def info(cli: str) -> dict[str, str] | None:
    result = command(
        [cli, "-h", "127.0.0.1", "-p", str(PORT), "--raw", "INFO", "server"], check=False
    )
    if result.returncode:
        return None
    return dict(
        line.split(":", 1)
        for line in result.stdout.splitlines()
        if line and not line.startswith("#") and ":" in line
    )


def verify(details: dict[str, str]) -> None:
    if details.get("config_file") != str(CONFIG) or details.get("tcp_port") != str(PORT):
        raise RuntimeError("Port 16380 belongs to another Redis server; refusing control")
    print(f"Isolated Redis {details.get('redis_version', 'unknown')} ready on localhost:{PORT}")


def start(server: str, cli: str) -> None:
    details = info(cli)
    if details is not None:
        if not RECORD.exists():
            raise RuntimeError("Running Redis has no matching ownership record")
        verify(details)
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", PORT))
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    RUNTIME.chmod(0o700)
    for path in (RUNTIME / "server.log", RUNTIME / "redis.pid"):
        if path.is_symlink():
            raise RuntimeError("Refusing symlink in Redis runtime")
    RECORD.write_text(
        json.dumps({"owner": OWNER, "runtime_dir": str(RUNTIME), "port": PORT}, indent=2) + "\n"
    )
    RECORD.chmod(0o600)
    CONFIG.write_text(
        "\n".join(
            [
                "bind 127.0.0.1",
                f"port {PORT}",
                "protected-mode yes",
                "daemonize yes",
                f"pidfile {json.dumps(str(RUNTIME / 'redis.pid'))}",
                f"logfile {json.dumps(str(RUNTIME / 'server.log'))}",
                f"dir {json.dumps(str(RUNTIME))}",
                'save ""',
                "appendonly no",
                "maxmemory 32mb",
                "maxmemory-policy noeviction",
                "databases 16",
                "",
            ]
        )
    )
    CONFIG.chmod(0o600)
    command([server, str(CONFIG)])
    details = info(cli)
    if details is None:
        raise RuntimeError("Isolated Redis did not start")
    verify(details)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"))
    args = parser.parse_args()
    try:
        guard_paths()
        server, cli = binaries()
        if args.action == "start":
            start(server, cli)
        else:
            details = info(cli)
            if details is None:
                print("Isolated Redis is stopped.")
                return 1 if args.action == "status" else 0
            if not RECORD.exists():
                raise RuntimeError("Running Redis has no matching ownership record")
            verify(details)
            if args.action == "stop":
                command([cli, "-h", "127.0.0.1", "-p", str(PORT), "SHUTDOWN", "NOSAVE"])
                print("Isolated Redis stopped.")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Test Redis: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
