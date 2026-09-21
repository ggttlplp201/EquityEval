"""Manage the separate persistent application Redis coordinator on loopback6380."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from dotenv import dotenv_values
from redis import Redis
from redis.exceptions import RedisError

ROOT = Path(__file__).resolve().parents[1]
OWNER = "equityeval-application-redis-v1"


@dataclass(frozen=True)
class ApplicationRedis:
    root: Path
    port: int = 6380

    @property
    def directory(self) -> Path:
        return self.root / "var/application-redis"

    @property
    def config(self) -> Path:
        return self.directory / "redis.conf"

    @property
    def record(self) -> Path:
        return self.directory / "runtime.json"

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "owner": OWNER,
            "repository": str(self.root),
            "runtime_dir": str(self.directory),
            "port": self.port,
        }

    def client(self) -> Redis:
        return Redis(
            host="127.0.0.1",
            port=self.port,
            db=0,
            socket_timeout=3,
            socket_connect_timeout=3,
            decode_responses=True,
        )


def configuration(root: Path = ROOT) -> ApplicationRedis:
    raw = os.environ.get("REDIS_URL") or dotenv_values(root / ".env").get("REDIS_URL")
    url = urlsplit(raw or "")
    if (
        url.scheme != "redis"
        or url.hostname not in {"127.0.0.1", "localhost"}
        or url.port != 6380
        or url.path not in {"", "/0"}
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError("Require a local application Redis URL on port 6380, database 0")
    return ApplicationRedis(root)


def guard(runtime: ApplicationRedis) -> None:
    paths = [
        runtime.root / "var",
        runtime.directory,
        runtime.config,
        runtime.record,
        runtime.directory / "server.log",
        runtime.directory / "redis.pid",
        runtime.directory / "appendonlydir",
        runtime.directory / "dump.rdb",
    ]
    if runtime.directory.is_dir():
        paths.extend(runtime.directory.rglob("*"))
    for path in paths:
        if path.is_symlink() or (path.exists() and path.stat().st_uid != os.getuid()):
            raise RuntimeError("Refusing unowned or symlinked application Redis path")
    if runtime.record.exists():
        if json.loads(runtime.record.read_text()) != runtime.identity:
            raise RuntimeError("Application Redis ownership record mismatch")
    elif runtime.directory.exists() and any(runtime.directory.iterdir()):
        raise RuntimeError("Existing Redis files have no matching ownership record")


def verify(runtime: ApplicationRedis, client: Redis) -> dict[str, Any]:
    guard(runtime)
    if not runtime.record.exists():
        raise RuntimeError("Application Redis has no ownership record")
    details = cast(dict[str, Any], client.info("server"))
    expected = {
        "bind": "127.0.0.1",
        "protected-mode": "yes",
        "appendonly": "yes",
        "appendfsync": "always",
        "dir": str(runtime.directory),
        "maxmemory-policy": "noeviction",
    }
    if (
        details.get("config_file") != str(runtime.config)
        or details.get("tcp_port") != runtime.port
        or any(
            cast(dict[str, Any], client.config_get(key)).get(key) != value
            for key, value in expected.items()
        )
    ):
        raise RuntimeError("Redis configuration does not match the owned application runtime")
    persistence = cast(dict[str, Any], client.info("persistence"))
    if persistence.get("aof_enabled") != 1 or persistence.get("aof_last_write_status") != "ok":
        raise RuntimeError("Application Redis persistence is not healthy")
    return {
        "port": runtime.port,
        "version": details["redis_version"],
        "aof": True,
        "appendfsync": "always",
        "application_only": True,
    }


def start(runtime: ApplicationRedis, client: Redis) -> None:
    guard(runtime)
    try:
        client.ping()
    except RedisError:
        pass
    else:
        verify(runtime, client)
        return
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", runtime.port))
    executable = shutil.which("redis-server")
    if not executable:
        raise RuntimeError("redis-server must be installed and on PATH")
    runtime.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime.directory.chmod(0o700)
    runtime.record.write_text(json.dumps(runtime.identity, indent=2) + "\n")
    runtime.record.chmod(0o600)
    lines = [
        "bind 127.0.0.1",
        f"port {runtime.port}",
        "protected-mode yes",
        "daemonize yes",
        f"pidfile {json.dumps(str(runtime.directory / 'redis.pid'))}",
        f"logfile {json.dumps(str(runtime.directory / 'server.log'))}",
        f"dir {json.dumps(str(runtime.directory))}",
        'save ""',
        "appendonly yes",
        "appendfsync always",
        "maxmemory 64mb",
        "maxmemory-policy noeviction",
        "databases 1",
    ]
    runtime.config.write_text("\n".join(lines) + "\n")
    runtime.config.chmod(0o600)
    subprocess.run([executable, str(runtime.config)], check=True, capture_output=True, timeout=15)
    # Daemonization returns before Redis finishes loading durable state.
    deadline = time.monotonic() + 10
    while True:
        try:
            verify(runtime, client)
            return
        except RedisError:
            if time.monotonic() >= deadline:
                raise RuntimeError("Application Redis startup deadline exceeded") from None
            time.sleep(0.05)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"))
    args = parser.parse_args()
    runtime = configuration()
    with runtime.client() as client:
        if args.action == "start":
            start(runtime, client)
        status = verify(runtime, client)
        if args.action == "stop":
            # AOF preserves shared cooldowns across intentional restarts; never flush data.
            client.shutdown(save=True)
            print("Application Redis stopped; persisted coordinator state retained.")
        else:
            print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, RedisError, subprocess.SubprocessError) as error:
        print(
            f"Application Redis failed ({type(error).__name__}); "
            "check the owned runtime and local configuration.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
