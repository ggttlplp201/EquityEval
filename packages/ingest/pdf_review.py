"""Offline, bounded inspection of the eight exact D050 PDF resources."""

import hashlib
import json
import os
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Any

from equity_ingest.pdf_transfer import PdfCaptureBinding, pdf_body_limit
from equity_schema.crcl_history import CRCL_HISTORY_PDFS

ARS_KEY = "filing_document/0001876042/0001876042-26-000116/a2025annualreport0331.pdf"


def inspect_pdf(
    path: Path, resource_key: str, *, python: Path, capture: PdfCaptureBinding | None = None
) -> dict[str, Any]:
    body = path.read_bytes()
    result: dict[str, Any] = {
        "resourceKey": resource_key,
        "inputSha256": hashlib.sha256(body).hexdigest(),
        "byteCount": len(body),
        "status": "blocked",
        "reason": None,
        "pages": [],
        "visualReviewComplete": False,
        "limits": {
            "addressSpaceBytes": 512 * 1024 * 1024,
            "wallSeconds": 30,
            "pageCount": 400 if resource_key == ARS_KEY else 100,
            "textBytes": (8 if resource_key == ARS_KEY else 2) * 1024 * 1024,
        },
    }
    if resource_key not in CRCL_HISTORY_PDFS:
        return result | {"reason": "pdf_resource_not_reviewed"}
    if capture is not None and not capture.matches(resource_key, body):
        return result | {"reason": "pdf_capture_binding_invalid"}
    if len(body) > pdf_body_limit(resource_key):
        return result | {"reason": "pdf_body_limit"}
    if len(body) > 8 * 1024 * 1024 and capture is None:
        return result | {"reason": "pdf_capture_binding_required"}
    worker = Path(__file__).with_name("pdf_review_worker.py").resolve()
    if not python.is_file():
        return result | {"reason": "pdf_parser_unavailable"}
    with tempfile.TemporaryDirectory(prefix="equity-pdf-") as directory:
        root = Path(directory)
        source, output = root / "input.pdf", root / "review.json"
        source.write_bytes(body)
        command = [
            str(python),
            "-I",
            str(worker),
            str(source),
            str(output),
            "annual" if resource_key == ARS_KEY else "correspondence",
        ]
        try:
            with (root / "stderr").open("wb") as errors:
                completed = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=errors,
                    timeout=30,
                    check=False,
                    env={"PATH": os.defpath, "LC_ALL": "C", "TZ": "UTC"},
                )
            if completed.returncode != 0 or not output.is_file():
                return result | {"reason": "pdf_parser_process_failed"}
            parsed = json.loads(output.read_text())
            if parsed.get("status") not in {"parsed", "blocked"} or not isinstance(
                parsed.get("pages"), list
            ):
                return result | {"reason": "pdf_parser_result_invalid"}
            result.update(parsed)
            return result
        except subprocess.TimeoutExpired:
            return result | {"reason": "pdf_parser_timeout"}
        except (OSError, ValueError):
            return result | {"reason": "pdf_parser_unavailable"}


def _valid_png(data: bytes, width: int, height: int) -> bool:
    """Validate complete CRC/chunk/zlib structure within the already checked pixel cap."""
    offset, ended, saw_idat, idat_closed = 8, False, False, False
    compressed = []
    try:
        while offset < len(data):
            if offset + 12 > len(data):
                return False
            size = struct.unpack(">I", data[offset : offset + 4])[0]
            kind = data[offset + 4 : offset + 8]
            end = offset + 12 + size
            if end > len(data):
                return False
            value = data[offset + 8 : offset + 8 + size]
            crc = struct.unpack(">I", data[offset + 8 + size : end])[0]
            if zlib.crc32(kind + value) != crc:
                return False
            if offset == 8:
                if kind != b"IHDR" or size != 13 or value[10:13] != b"\0\0\0":
                    return False
            elif kind == b"IHDR":
                return False
            if kind == b"IDAT":
                if idat_closed:
                    return False
                saw_idat = True
                compressed.append(value)
            elif saw_idat:
                idat_closed = True
            if kind == b"IEND":
                ended = size == 0 and end == len(data)
                break
            offset = end
        if not ended or not saw_idat:
            return False
        expected = height * (1 + width * 3)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(b"".join(compressed), expected + 1)
        return (
            len(raw) == expected
            and decoder.eof
            and not decoder.unused_data
            and not decoder.unconsumed_tail
            and all(raw[index] <= 4 for index in range(0, expected, 1 + width * 3))
        )
    except (ValueError, struct.error, zlib.error):
        return False


def render_pdf(
    path: Path,
    resource_key: str,
    *,
    python: Path,
    poppler: Path,
    output_dir: Path,
    capture: PdfCaptureBinding | None = None,
) -> dict[str, Any]:
    """Render bounded page evidence; human visual inspection remains a separate gate."""
    import time

    review = inspect_pdf(path, resource_key, python=python, capture=capture)
    review["renderedPages"] = []
    if review["status"] != "parsed":
        return review
    review["status"] = "blocked"
    review["renderSettings"] = {
        "version": "26.05.0",
        "dpi": 100,
        "format": "PNG RGB8",
        "pageBox": "MediaBox",
        "antialias": True,
    }
    binaries = {name: (poppler / name).resolve() for name in ("pdfinfo", "pdftoppm")}
    if any(not binary.is_file() for binary in binaries.values()):
        return review | {"reason": "pdf_renderer_unavailable"}
    review["rendererBinaries"] = {
        name: {"path": str(binary), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
        for name, binary in binaries.items()
    }
    annual = resource_key == ARS_KEY
    deadline = time.monotonic() + (300 if annual else 120)
    total = 0
    worker = Path(__file__).with_name("pdf_exec_worker.py").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="equity-render-") as directory:
        root = Path(directory)
        source = root / "input.pdf"
        source.write_bytes(path.read_bytes())
        if hashlib.sha256(source.read_bytes()).hexdigest() != review["inputSha256"]:
            return review | {"reason": "pdf_input_changed"}

        def invoke(binary: Path, arguments: list[str]) -> tuple[int, bytes]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(str(binary), 0)
            command = [str(python), "-I", str(worker), str(binary), *arguments]
            with (root / "process.out").open("wb") as output:
                completed = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    timeout=min(15, remaining),
                    check=False,
                    env={"PATH": os.defpath, "LC_ALL": "C", "TZ": "UTC"},
                )
            return completed.returncode, (root / "process.out").read_bytes()

        try:
            for name, binary in binaries.items():
                code, version = invoke(binary, ["-v"])
                if code == 78:
                    return review | {"reason": "pdf_limits_unavailable"}
                if code or (name + " version 26.05.0").encode() not in version:
                    return review | {"reason": "pdf_renderer_version"}
            for page in review["pages"]:
                number = page["page"]
                stem = root / f"page-{number}"
                arguments = [
                    "-f",
                    str(number),
                    "-l",
                    str(number),
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
                code, _ = invoke(binaries["pdftoppm"], arguments)
                if code:
                    return review | {"reason": "pdf_render_process_failed"}
                png = stem.with_suffix(".png")
                if not png.is_file() or png.stat().st_size > 8 * 1024 * 1024:
                    return review | {"reason": "pdf_render_output_limit"}
                data = png.read_bytes()
                if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
                    return review | {"reason": "pdf_render_invalid_png"}
                width, height = struct.unpack(">II", data[16:24])
                if not 0 < width <= 2000 or not 0 < height <= 2000 or width * height > 4000000:
                    return review | {"reason": "pdf_render_pixels"}
                if [width, height] != page["renderPixels"] or data[24:26] != bytes((8, 2)):
                    return review | {"reason": "pdf_render_format"}
                if not _valid_png(data, width, height):
                    return review | {"reason": "pdf_render_invalid_png"}
                total += len(data)
                if total > (256 if annual else 64) * 1024 * 1024:
                    return review | {"reason": "pdf_render_aggregate_limit"}
                target = output_dir / f"{review['inputSha256']}-page-{number}.png"
                if target.exists():
                    if target.stat().st_size != len(data) or target.read_bytes() != data:
                        return review | {"reason": "pdf_render_existing_mismatch"}
                else:
                    with target.open("xb") as output:
                        output.write(data)
                review["renderedPages"].append(
                    {
                        "page": number,
                        "path": str(target),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data),
                        "command": [str(binaries["pdftoppm"]), *arguments],
                    }
                )
        except subprocess.TimeoutExpired:
            return review | {"reason": "pdf_render_timeout"}
        except OSError:
            return review | {"reason": "pdf_render_io"}
    return review | {
        "status": "rendered_pending_visual_review",
        "reason": "pdf_visual_review_required",
    }
