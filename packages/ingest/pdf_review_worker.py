"""Isolated passive D050 parser entry point; invoked with bounded resources."""

import hashlib
import importlib
import json
import math
import resource
import sys
from pathlib import Path
from typing import Any


def inspect_document(path: Path, annual: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "blocked", "reason": "pdf_parser_error", "pages": []}
    try:
        parser = importlib.import_module("pypdf")
        result["parserVersion"] = parser.__version__
        if parser.__version__ != "6.10.0":
            raise ValueError("pdf_parser_version")
        reader = parser.PdfReader(path, strict=True)
        if reader.is_encrypted:
            raise ValueError("pdf_encrypted")
        count = len(reader.pages)
        if not 1 <= count <= (400 if annual else 100):
            raise ValueError("pdf_page_count")
        # Follow passive object references only; never execute actions or extract attachments.
        seen: set[int] = set()
        stack = [reader.trailer]
        while stack:
            obj = stack.pop()
            if hasattr(obj, "get_object"):
                obj = obj.get_object()
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            if len(seen) > 100000:
                raise ValueError("pdf_object_limit")
            if isinstance(obj, dict):
                if set(obj) & {
                    "/JS",
                    "/JavaScript",
                    "/OpenAction",
                    "/AA",
                    "/EmbeddedFiles",
                    "/EF",
                    "/XFA",
                    "/RichMediaContent",
                }:
                    raise ValueError("pdf_active_content")
                if obj.get("/S") in {
                    "/JavaScript",
                    "/Launch",
                    "/SubmitForm",
                    "/ImportData",
                    "/GoToR",
                    "/Rendition",
                }:
                    raise ValueError("pdf_active_content")
                stack.extend(obj.values())
            elif isinstance(obj, (list, tuple)):
                stack.extend(obj)
        total = 0
        for number, page in enumerate(reader.pages, 1):
            media, crop = [float(v) for v in page.mediabox], [float(v) for v in page.cropbox]
            for box in (media, crop):
                if not all(math.isfinite(v) for v in box) or not (
                    0 < box[2] - box[0] <= 1440 and 0 < box[3] - box[1] <= 1440
                ):
                    raise ValueError("pdf_page_box")
            if not (
                media[0] <= crop[0] < crop[2] <= media[2]
                and media[1] <= crop[1] < crop[3] <= media[3]
            ):
                raise ValueError("pdf_page_box")
            width, height = (
                math.ceil((media[2] - media[0]) * 100 / 72),
                math.ceil((media[3] - media[1]) * 100 / 72),
            )
            if max(width, height) > 2000 or width * height > 4000000:
                raise ValueError("pdf_page_pixels")
            text = page.extract_text() or ""
            encoded = text.encode("utf-8")
            total += len(encoded)
            if total > (8 if annual else 2) * 1024 * 1024:
                raise ValueError("pdf_text_limit")
            result["pages"].append(
                {
                    "page": number,
                    "locator": f"PDF page {number}",
                    "text": text,
                    "textSha256": hashlib.sha256(encoded).hexdigest(),
                    "mediaBox": media,
                    "cropBox": crop,
                    "renderPixels": [width, height],
                }
            )
        result.update(status="parsed", reason=None, pageCount=count)
    except ModuleNotFoundError:
        result["reason"] = "pdf_parser_unavailable"
    except MemoryError:
        result["reason"] = "pdf_parser_memory"
    except ValueError as error:
        result["reason"] = str(error) if str(error).startswith("pdf_") else "pdf_parser_error"
    except Exception:
        result["reason"] = "pdf_parser_error"
    return result


def main() -> None:
    path, output, annual = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] == "annual"
    try:
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
    except (OSError, ValueError):
        result = {"status": "blocked", "reason": "pdf_limits_unavailable", "pages": []}
    else:
        result = inspect_document(path, annual)
    output.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
