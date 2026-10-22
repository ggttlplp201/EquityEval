"""Synthetic-only Linux proof, using the exact governed parser/render workers."""

import hashlib
import importlib
import random
import subprocess
import sys
import zlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from equity_ingest.pdf_review import inspect_pdf, render_pdf

from scripts.crcl_pdf_runtime import canonical, prove_controls

KEY = "filing_document/0001876042/0000000000-24-002161/filename1.pdf"


def pdf(objects: list[bytes]) -> bytes:
    body = b"%PDF-1.4\n"
    offsets = [0]
    for number, item in enumerate(objects, 1):
        offsets.append(len(body))
        body += str(number).encode() + b" 0 obj\n" + item + b"\nendobj\n"
    offset = len(body)
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    body += b"".join(f"{n:010d} 00000 n \n".encode() for n in offsets[1:])
    return (
        body
        + (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{offset}\n%%EOF\n"
        ).encode()
    )


def blank(box: bytes = b"0 0 612 792") -> bytes:
    return pdf(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [" + box + b"] >>",
        ]
    )


def image_pdf(compressed: bytes, *, width: int, height: int, rgb: bool) -> bytes:
    # Draw the XObject, ensuring Poppler actually invokes the image decoder.
    content = b"q 1296 0 0 1296 0 0 cm /Im1 Do Q"
    color = "DeviceRGB" if rgb else "DeviceGray"
    return pdf(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1296 1296] "
            b"/Resources << /XObject << /Im1 4 0 R >> >> /Contents 5 0 R >>",
            (
                f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
                f"/BitsPerComponent 8 /ColorSpace /{color} /Length {len(compressed)} "
                "/Filter /FlateDecode >>\nstream\n"
            ).encode()
            + compressed
            + b"\nendstream",
            f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
        ]
    )


def render_probe(source: Path, stem: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        "-I",
        "/opt/equity/equity_ingest/pdf_exec_worker.py",
        "/opt/poppler/bin/pdftoppm",
        "-f",
        "1",
        "-l",
        "1",
        "-singlefile",
        "-png",
        "-r",
        "100",
        "-aa",
        "yes",
        "-aaVector",
        "yes",
        str(source),
        str(stem),
    ]
    try:
        result = subprocess.run(command, capture_output=True, timeout=15, check=False)
        code: int | None = result.returncode
        stderr_hash = hashlib.sha256(result.stderr).hexdigest()
    except subprocess.TimeoutExpired:
        code, stderr_hash = None, None
    png = stem.with_suffix(".png")
    size = png.stat().st_size if png.exists() else 0
    if code == 78 or size > 8 * 1024 * 1024:
        raise ValueError("runtime_poppler_caps_failed")
    evidence = {
        "exitCode": code,
        "wallTimeout": code is None,
        "outputBytes": size,
        "stderrSha256": stderr_hash,
        "inputSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "command": command,
    }
    png.unlink(missing_ok=True)
    return evidence


class CheckpointResults(dict[str, Any]):
    def __init__(self, checkpoint: Path) -> None:
        super().__init__()
        self.checkpoint = checkpoint

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        temporary = self.checkpoint.with_suffix(".pending")
        temporary.write_bytes(canonical(self))
        temporary.replace(self.checkpoint)

    def probe(
        self,
        name: str,
        operation: Callable[[], dict[str, Any]],
        accepts: Callable[[dict[str, Any]], bool],
        *,
        requires: tuple[str, ...] = (),
    ) -> None:
        checks = dict(self.get("checks", {}))
        if any(checks.get(required) != "passed" for required in requires):
            self[name] = {
                "status": "skipped",
                "reason": "prerequisite_failed",
                "requires": requires,
            }
            checks[name] = "skipped"
        else:
            try:
                value = operation()
                self[name] = value
                checks[name] = "passed" if accepts(value) else "failed"
            except Exception as error:
                self[name] = {
                    "status": "failed",
                    "exceptionType": type(error).__name__,
                    "reason": str(error)[:256],
                }
                checks[name] = "failed"
        self["checks"] = checks


def main() -> None:
    output = Path("/out")
    (output / "built-toolchain.json").write_bytes(
        Path("/opt/bootstrap/built-toolchain.json").read_bytes()
    )
    # Effective isolation is a prerequisite for every subsequent probe.
    prove_controls(output / "controls.json")
    results = CheckpointResults(output / "synthetic-progress.json")
    source = output / "fixture.pdf"
    exec_worker = "/opt/equity/equity_ingest/pdf_exec_worker.py"

    def parse(body: bytes) -> dict[str, Any]:
        source.write_bytes(body)
        return inspect_pdf(source, KEY, python=Path(sys.executable))

    def render(body: bytes) -> dict[str, Any]:
        source.write_bytes(body)
        return render_pdf(
            source,
            KEY,
            python=Path(sys.executable),
            poppler=Path("/opt/poppler/bin"),
            output_dir=output / "pages",
        )

    def poppler(body: bytes, name: str) -> dict[str, Any]:
        source.write_bytes(body)
        return render_probe(source, output / name)

    results.probe(
        "valid",
        lambda: render(blank()),
        lambda row: (
            bool(row.get("renderedPages")) and row["reason"] == "pdf_visual_review_required"
        ),
    )
    results.probe(
        "replay",
        lambda: render(blank()),
        lambda row: (
            [(p["page"], p["sha256"], p["bytes"]) for p in row["renderedPages"]]
            == [(p["page"], p["sha256"], p["bytes"]) for p in results["valid"]["renderedPages"]]
        ),
        requires=("valid",),
    )
    results.probe(
        "oversizedPage",
        lambda: parse(blank(b"0 0 1000000 792")),
        lambda row: row["reason"] == "pdf_page_box",
    )
    compressor = zlib.compressobj(9)
    compressed = (
        b"".join(compressor.compress(b" " * 65536) for _ in range(16384)) + compressor.flush()
    )
    stream = pdf(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
            f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode()
            + compressed
            + b"\nendstream",
        ]
    )
    results.probe(
        "compressedStream",
        lambda: parse(stream),
        lambda row: (
            row["status"] == "blocked"
            and row["reason"]
            in {"pdf_parser_memory", "pdf_parser_timeout", "pdf_parser_process_failed"}
        ),
    )
    results.probe(
        "compressedStreamPoppler", lambda: poppler(stream, "stream-probe"), lambda row: True
    )
    image = image_pdf(compressed, width=32768, height=32768, rgb=False)
    results.probe("compressedImagePoppler", lambda: poppler(image, "image-probe"), lambda row: True)

    def decode_image() -> dict[str, Any]:
        source.write_bytes(image)
        decode = (
            "import pypdf,sys; r=pypdf.PdfReader(sys.argv[1]);\n"
            "try: r.pages[0]['/Resources']['/XObject']['/Im1'].get_object().get_data()\n"
            "except Exception as e:\n"
            " print(type(e).__name__); raise SystemExit(0 if type(e).__name__ in "
            "{'MemoryError','LimitReachedError'} else 2)\nraise SystemExit(1)"
        )
        decoded = subprocess.run(
            [sys.executable, "-I", exec_worker, sys.executable, "-I", "-c", decode, str(source)],
            capture_output=True,
            timeout=15,
            check=False,
        )
        return {
            "exitCode": decoded.returncode,
            "stdout": decoded.stdout.decode(errors="replace"),
            "stderrSha256": hashlib.sha256(decoded.stderr).hexdigest(),
            "inputSha256": hashlib.sha256(image).hexdigest(),
        }

    results.probe("compressedImageDecoder", decode_image, lambda row: row["exitCode"] == 0)
    noise = random.Random(51051).randbytes(1800 * 1800 * 3)
    noise_pdf = image_pdf(zlib.compress(noise), width=1800, height=1800, rgb=True)
    del noise
    results.probe(
        "oversizedPngPoppler",
        lambda: poppler(noise_pdf, "png-limit-probe"),
        lambda row: row["outputBytes"] == 8 * 1024 * 1024 and row["exitCode"] not in (None, 0),
    )

    def wall_timeout() -> dict[str, Any]:
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-I",
                    exec_worker,
                    sys.executable,
                    "-I",
                    "-c",
                    "import time; time.sleep(30)",
                ],
                capture_output=True,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "bounded", "wallSeconds": 15}
        return {"status": "failed", "reason": "timeout_not_enforced"}

    results.probe("workerWallTimeout", wall_timeout, lambda row: row["status"] == "bounded")

    def structural(kind: str) -> dict[str, Any]:
        pypdf = importlib.import_module("pypdf")
        writer = pypdf.PdfWriter()
        for _ in range(101 if kind == "pages" else 1):
            writer.add_blank_page(width=612, height=792)
        if kind == "encrypted":
            writer.encrypt("synthetic-proof-only")
        writer.write(source)
        return inspect_pdf(source, KEY, python=Path(sys.executable))

    results.probe(
        "encrypted", lambda: structural("encrypted"), lambda row: row["reason"] == "pdf_encrypted"
    )
    results.probe(
        "pages", lambda: structural("pages"), lambda row: row["reason"] == "pdf_page_count"
    )

    def corrupt_replay() -> dict[str, Any]:
        Path(results["valid"]["renderedPages"][0]["path"]).write_bytes(b"corrupt synthetic output")
        return render(blank())

    results.probe(
        "corruptReplay",
        corrupt_replay,
        lambda row: row["reason"] == "pdf_render_existing_mismatch",
        requires=("valid",),
    )

    def restore_valid() -> dict[str, Any]:
        Path(results["valid"]["renderedPages"][0]["path"]).unlink()
        return render(blank())

    results.probe(
        "restoredValid",
        restore_valid,
        lambda row: row["reason"] == "pdf_visual_review_required",
        requires=("corruptReplay",),
    )
    source.unlink(missing_ok=True)
    results["proofScriptSha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    failed = [name for name, status in results["checks"].items() if status != "passed"]
    results["status"] = "synthetic_proof_failed" if failed else "synthetic_proof_complete"
    (output / "synthetic-proof.json").write_bytes(canonical(results))
    if failed:
        raise ValueError("runtime_synthetic_checks_failed:" + ",".join(failed))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        Path("/out/failure.json").write_bytes(
            canonical(
                {
                    "status": "synthetic_proof_failed",
                    "type": type(error).__name__,
                    "reason": str(error)[:256],
                }
            )
        )
        raise
