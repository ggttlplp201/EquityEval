"""Trusted-tool build stage only; never receives a financial PDF or credentials."""

import hashlib
import json
import subprocess
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path("/opt/bootstrap")


def fetch(entry: dict[str, Any], target: Path) -> None:
    checksum = hashlib.sha256()
    count = 0
    with urllib.request.urlopen(entry["url"], timeout=60) as response, target.open("xb") as output:
        while chunk := response.read(65536):
            count += len(chunk)
            if count > 32 * 1024 * 1024:
                raise ValueError("Tool archive limit")
            checksum.update(chunk)
            output.write(chunk)
    if checksum.hexdigest() != entry["sha256"] or ("bytes" in entry and count != entry["bytes"]):
        raise ValueError("Tool archive identity mismatch")


def main() -> None:
    pins = json.loads((ROOT / "toolchain.json").read_bytes())
    source = ROOT / "poppler.tar.xz"
    wheel = ROOT / "pypdf-6.10.0-py3-none-any.whl"
    fetch(pins["poppler"], source)
    fetch(pins["pypdf"], wheel)
    with tarfile.open(source, "r:xz") as archive:
        archive.extractall(ROOT, filter="data")
    options = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_INSTALL_PREFIX=/opt/poppler",
        "-DENABLE_UTILS=ON",
        "-DENABLE_CPP=OFF",
        "-DENABLE_GLIB=OFF",
        "-DENABLE_GOBJECT_INTROSPECTION=OFF",
        "-DENABLE_QT5=OFF",
        "-DENABLE_QT6=OFF",
        "-DENABLE_BOOST=OFF",
        "-DENABLE_LIBCURL=OFF",
        "-DENABLE_NSS3=OFF",
        "-DENABLE_GPGME=OFF",
        "-DBUILD_GTK_TESTS=OFF",
        "-DBUILD_QT5_TESTS=OFF",
        "-DBUILD_QT6_TESTS=OFF",
        "-DBUILD_CPP_TESTS=OFF",
        "-DBUILD_MANUAL_TESTS=OFF",
    ]
    subprocess.run(
        ["cmake", "-S", str(ROOT / "poppler-26.05.0"), "-B", str(ROOT / "build"), *options],
        check=True,
    )
    subprocess.run(["cmake", "--build", str(ROOT / "build"), "--parallel", "2"], check=True)
    subprocess.run(["cmake", "--install", str(ROOT / "build")], check=True)
    subprocess.run(["python3", "-m", "venv", "/opt/runtime"], check=True)
    subprocess.run(
        ["/opt/runtime/bin/pip", "install", "--no-index", "--no-deps", str(wheel)], check=True
    )
    Path("/etc/ld.so.conf.d/equity-poppler.conf").write_text("/opt/poppler/lib\n")
    subprocess.run(["ldconfig"], check=True)
    manifest: dict[str, Any] = {
        "pins": pins,
        "packages": subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Package}=${Version}\n"], text=True
        ),
        "files": {},
    }
    files: dict[str, Any] = manifest["files"]
    for base in [
        "/opt/poppler",
        "/opt/runtime",
        "/usr/share/fonts",
        "/usr/share/poppler",
        "/usr/lib/x86_64-linux-gnu",
        "/usr/lib/python3.12",
    ]:
        for path in sorted(Path(base).rglob("*")):
            if path.is_file() and not path.is_symlink() and path.suffix != ".pyc":
                files[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    files["/usr/bin/python3.12"] = hashlib.sha256(
        Path("/usr/bin/python3.12").read_bytes()
    ).hexdigest()
    (ROOT / "built-toolchain.json").write_text(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
