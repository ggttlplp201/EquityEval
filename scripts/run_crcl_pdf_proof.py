"""Synthetic-only Linux proof, using the exact governed parser/render workers."""

import hashlib
import importlib
import random
import subprocess
import sys
import zlib
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


def main() -> None:
    output = Path("/out")
    prove_controls(output / "controls.json")
    results: dict[str, Any] = {}
    source = output / "blank.pdf"
    source.write_bytes(blank())
    results["valid"] = render_pdf(
        source,
        KEY,
        python=Path(sys.executable),
        poppler=Path("/opt/poppler/bin"),
        output_dir=output / "pages",
    )
    if (
        not results["valid"]["renderedPages"]
        or results["valid"]["reason"] != "pdf_visual_review_required"
    ):
        raise ValueError("runtime_valid_render_failed")
    results["replay"] = render_pdf(
        source,
        KEY,
        python=Path(sys.executable),
        poppler=Path("/opt/poppler/bin"),
        output_dir=output / "pages",
    )
    if [(p["page"], p["sha256"], p["bytes"]) for p in results["replay"]["renderedPages"]] != [
        (p["page"], p["sha256"], p["bytes"]) for p in results["valid"]["renderedPages"]
    ]:
        raise ValueError("runtime_render_replay_failed")
    source.write_bytes(blank(b"0 0 1000000 792"))
    results["oversizedPage"] = inspect_pdf(source, KEY, python=Path(sys.executable))
    if results["oversizedPage"]["reason"] != "pdf_page_box":
        raise ValueError("runtime_page_limit_failed")
    # A one-GiB compressed content stream cannot fit under the 512-MiB parser cap.
    compressor = zlib.compressobj(9)
    pieces = [compressor.compress(b" " * 65536) for _ in range(16384)]
    compressed = b"".join(pieces) + compressor.flush()
    source.write_bytes(
        pdf(
            [
                b"<< /Type /Catalog /Pages 2 0 R >>",
                b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
                f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode()
                + compressed
                + b"\nendstream",
            ]
        )
    )
    results["compressedStream"] = inspect_pdf(source, KEY, python=Path(sys.executable))
    if results["compressedStream"]["status"] != "blocked" or results["compressedStream"][
        "reason"
    ] not in {"pdf_parser_memory", "pdf_parser_timeout", "pdf_parser_process_failed"}:
        raise ValueError("runtime_compressed_stream_not_bounded")
    results["compressedStreamPoppler"] = render_probe(source, output / "stream-probe")
    source.write_bytes(image_pdf(compressed, width=32768, height=32768, rgb=False))
    results["compressedImagePoppler"] = render_probe(source, output / "image-probe")
    exec_worker = "/opt/equity/equity_ingest/pdf_exec_worker.py"
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
    results["compressedImageDecoder"] = {
        "exitCode": decoded.returncode,
        "stdout": decoded.stdout.decode(errors="replace"),
        "stderrSha256": hashlib.sha256(decoded.stderr).hexdigest(),
        "inputSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    if decoded.returncode != 0:
        raise ValueError("runtime_compressed_image_decoder_failed")
    # Deterministic incompressible RGB at 1800x1800 produces >8MiB PNG at 100DPI.
    # The exact production exec wrapper must stop the real Poppler output at its cap.
    noise = random.Random(51051).randbytes(1800 * 1800 * 3)
    source.write_bytes(image_pdf(zlib.compress(noise), width=1800, height=1800, rgb=True))
    results["oversizedPngPoppler"] = render_probe(source, output / "png-limit-probe")
    if results["oversizedPngPoppler"]["outputBytes"] != 8 * 1024 * 1024 or results[
        "oversizedPngPoppler"
    ]["exitCode"] in (None, 0):
        raise ValueError("runtime_real_png_file_limit_not_proven")
    del noise
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
        results["workerWallTimeout"] = {"status": "bounded", "wallSeconds": 15}
    else:
        raise ValueError("runtime_worker_timeout_not_enforced")

    pypdf = importlib.import_module("pypdf")

    for kind, expected in (("encrypted", "pdf_encrypted"), ("pages", "pdf_page_count")):
        writer = pypdf.PdfWriter()
        for _ in range(101 if kind == "pages" else 1):
            writer.add_blank_page(width=612, height=792)
        if kind == "encrypted":
            writer.encrypt("synthetic-proof-only")
        writer.write(source)
        results[kind] = inspect_pdf(source, KEY, python=Path(sys.executable))
        if results[kind]["reason"] != expected:
            raise ValueError("runtime_structural_limit_failed")
    source.write_bytes(blank())
    page = Path(results["valid"]["renderedPages"][0]["path"])
    page.write_bytes(b"corrupt synthetic output")
    results["corruptReplay"] = render_pdf(
        source,
        KEY,
        python=Path(sys.executable),
        poppler=Path("/opt/poppler/bin"),
        output_dir=output / "pages",
    )
    if results["corruptReplay"]["reason"] != "pdf_render_existing_mismatch":
        raise ValueError("runtime_corrupt_replay_accepted")
    page.unlink()
    results["restoredValid"] = render_pdf(
        source,
        KEY,
        python=Path(sys.executable),
        poppler=Path("/opt/poppler/bin"),
        output_dir=output / "pages",
    )
    if results["restoredValid"]["reason"] != "pdf_visual_review_required":
        raise ValueError("runtime_valid_restore_failed")
    source.unlink()
    results["proofScriptSha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    results["status"] = "synthetic_proof_complete"
    (output / "synthetic-proof.json").write_bytes(canonical(results))
    (output / "built-toolchain.json").write_bytes(
        Path("/opt/bootstrap/built-toolchain.json").read_bytes()
    )


if __name__ == "__main__":
    main()
