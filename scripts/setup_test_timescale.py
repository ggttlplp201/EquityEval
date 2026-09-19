"""Build pinned PG16 + Timescale privately; never install into system PostgreSQL.

This explicit setup command downloads official, SHA-256-pinned source archives.
It is not run implicitly by tests. Only loopback test servers use this build.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import urllib.request
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_KEY = hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
CACHE = Path.home() / ".cache" / "equityeval" / f"test-pg16-timescale-{REPO_KEY}"
INSTALL = CACHE / "installation"
OWNER = "equityeval-private-timescale-build-v1"
PG_VERSION = "16.14"
TIMESCALE_VERSION = "2.28.1"
CMAKE_VERSION = "3.31.10"
SOURCE_ARCHIVES = (
    (
        f"postgresql-{PG_VERSION}.tar.bz2",
        f"https://ftp.postgresql.org/pub/source/v{PG_VERSION}/postgresql-{PG_VERSION}.tar.bz2",
        "f6d077142737920858ce958ccdb75c6ee137a63b5b0853c70693d401ac7e3471",
    ),
    (
        f"timescaledb-{TIMESCALE_VERSION}.tar.gz",
        f"https://codeload.github.com/timescale/timescaledb/tar.gz/refs/tags/{TIMESCALE_VERSION}",
        "ae582d545b1364d7df0deeba862161c021d9df82e9bb281f7f57ddaa686a6a44",
    ),
)


def guard_paths() -> None:
    for path in (CACHE.parent.parent, CACHE.parent, CACHE, INSTALL):
        if path.is_symlink() or (path.exists() and path.stat().st_uid != os.getuid()):
            raise RuntimeError(f"Refusing unowned or symlinked build path: {path}")
    marker = CACHE / "owner.json"
    expected = {"owner": OWNER, "repository": str(ROOT), "cache": str(CACHE)}
    if marker.is_file():
        if marker.is_symlink() or json.loads(marker.read_text()) != expected:
            raise RuntimeError("Private build ownership record mismatch.")
    else:
        if CACHE.exists() and any(CACHE.iterdir()):
            raise RuntimeError("Refusing existing build directory without ownership record.")
        CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker.write_text(json.dumps(expected, indent=2) + "\n")
        marker.chmod(0o600)


def download_sources() -> None:
    for filename, url, expected in SOURCE_ARCHIVES:
        archive = CACHE / filename
        if archive.is_symlink():
            raise RuntimeError("Refusing symlinked source archive.")
        if not archive.exists():
            print(f"Download {filename}", flush=True)
            with urllib.request.urlopen(url, timeout=60) as response:
                body = response.read(64 * 1024 * 1024 + 1)
            if len(body) > 64 * 1024 * 1024:
                raise RuntimeError("Source archive exceeds the configured download limit.")
            if hashlib.sha256(body).hexdigest() != expected:
                raise RuntimeError(f"Source archive checksum mismatch: {filename}")
            archive.write_bytes(body)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Cached source archive checksum mismatch: {filename}")
        directory = CACHE / filename.split(".tar.", maxsplit=1)[0]
        if directory.is_symlink():
            raise RuntimeError("Refusing symlinked source directory.")
        if not directory.exists():
            with tarfile.open(archive) as source:
                source.extractall(CACHE, filter="data")


def run(args: list[str], *, directory: Path, log_name: str) -> None:
    print(f"{log_name}: {args[0]}", flush=True)
    with (CACHE / log_name).open("w") as log:
        subprocess.run(args, cwd=directory, stdout=log, stderr=subprocess.STDOUT, check=True)


def build(jobs: int) -> None:
    tools_directory = CACHE / "build-tools"
    if tools_directory.is_symlink():
        raise RuntimeError("Refusing symlinked build-tools directory.")
    if not (tools_directory / "bin/python").is_file():
        venv.EnvBuilder(with_pip=True).create(tools_directory)
    run(
        [
            str(tools_directory / "bin/python"),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            f"cmake=={CMAKE_VERSION}",
        ],
        directory=CACHE,
        log_name="cmake-install.log",
    )
    pg_source = CACHE / f"postgresql-{PG_VERSION}"
    run(
        [
            "./configure",
            f"--prefix={INSTALL}",
            "--without-icu",
            "--without-readline",
            "--without-zlib",
        ],
        directory=pg_source,
        log_name="postgres-configure.log",
    )
    run(["make", f"-j{jobs}"], directory=pg_source, log_name="postgres-build.log")
    run(["make", "install"], directory=pg_source, log_name="postgres-install.log")
    run(
        ["make", "-C", "contrib/btree_gist", "install"],
        directory=pg_source,
        log_name="btree-gist-install.log",
    )
    cmake = str(tools_directory / "bin/cmake")
    ts_source = CACHE / f"timescaledb-{TIMESCALE_VERSION}"
    ts_build = ts_source / "build"
    run(
        [
            cmake,
            "-S",
            str(ts_source),
            "-B",
            str(ts_build),
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DPG_CONFIG={INSTALL / 'bin/pg_config'}",
            "-DUSE_OPENSSL=OFF",
            "-DSEND_TELEMETRY_DEFAULT=OFF",
            "-DTELEMETRY=OFF",
            "-DREGRESS_CHECKS=OFF",
            "-DTAP_CHECKS=OFF",
        ],
        directory=CACHE,
        log_name="timescale-configure.log",
    )
    run(
        [cmake, "--build", str(ts_build), f"-j{jobs}"],
        directory=CACHE,
        log_name="timescale-build.log",
    )
    run([cmake, "--install", str(ts_build)], directory=CACHE, log_name="timescale-install.log")


def installation_record() -> dict[str, object]:
    return {
        "owner": OWNER,
        "repository": str(ROOT),
        "bin_dir": str(INSTALL / "bin"),
        "postgres_version": PG_VERSION,
        "timescale_version": TIMESCALE_VERSION,
        "cmake_version": CMAKE_VERSION,
        "source_sha256": {name: digest for name, _, digest in SOURCE_ARCHIVES},
        "telemetry": "disabled-at-build",
        "purpose": "isolated-loopback-tests-only; no TLS",
    }


def publish_record() -> None:
    directory = ROOT / "var/test-postgres16-timescale"
    for path in (ROOT / "var", directory, directory / "installation.json"):
        if path.is_symlink() or (path.exists() and path.stat().st_uid != os.getuid()):
            raise RuntimeError("Refusing unowned or symlinked runtime record path.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    record = directory / "installation.json"
    record.write_text(json.dumps(installation_record(), indent=2) + "\n")
    record.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    try:
        if not 1 <= args.jobs <= 16:
            raise ValueError("--jobs must be between 1 and 16")
        if " " in str(CACHE):
            raise RuntimeError("PostgreSQL's source build requires a cache path without spaces.")
        guard_paths()
        completed = CACHE / "installation.json"
        control = INSTALL / "share/postgresql/extension/timescaledb.control"
        if not (
            completed.is_file()
            and json.loads(completed.read_text()) == installation_record()
            and control.is_file()
            and f"default_version = '{TIMESCALE_VERSION}'" in control.read_text()
            and (INSTALL / "bin/postgres").is_file()
        ):
            download_sources()
            build(args.jobs)
            if not control.is_file() or TIMESCALE_VERSION not in control.read_text():
                raise RuntimeError("The pinned Timescale extension was not installed.")
            completed.write_text(json.dumps(installation_record(), indent=2) + "\n")
        publish_record()
        print(f"Private PG{PG_VERSION} + Timescale {TIMESCALE_VERSION}: {INSTALL}")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Private Timescale setup failed: {error}; logs: {CACHE}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
