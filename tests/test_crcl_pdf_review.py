"""Bounded passive PDF review rejects unsafe geometry and unavailable runtimes."""

import json
import subprocess
import sys
from pathlib import Path

from equity_ingest.pdf_review import inspect_pdf

PYTHON = Path(
    "/Users/leon/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
)
KEY = "filing_document/0001876042/0000000000-24-002161/filename1.pdf"


def blank_pdf(box="0 0 612 792", extra=""):
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [" + box + "] " + extra + " >>").encode(),
    ]
    body = b"%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body += str(number).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(body)
    body += b"xref\n0 4\n0000000000 65535 f \n"
    body += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return body + f"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


def test_passive_parser_pins_hash_version_and_page_text(tmp_path):
    path = tmp_path / "input.pdf"
    path.write_bytes(blank_pdf())
    result = inspect_pdf(path, KEY, python=PYTHON)
    if sys.platform == "darwin":
        assert result["reason"] == "pdf_limits_unavailable"
        assert not result["pages"]
        return
    assert result["status"] == "parsed"
    assert result["parserVersion"] == "6.10.0"
    assert result["pages"][0]["renderPixels"] == [850, 1100]
    assert result["pages"][0]["text"] == ""
    assert result["visualReviewComplete"] is False


def test_parser_rejects_oversized_box_before_rendering(tmp_path):
    path = tmp_path / "input.pdf"
    path.write_bytes(blank_pdf("0 0 1000000 792"))
    result = inspect_synthetic_without_os_limits(path)
    assert result["status"] == "blocked"
    assert result["reason"] == "pdf_page_box"


def test_parser_unavailable_and_unapproved_resource_are_blocked(tmp_path):
    path = tmp_path / "input.pdf"
    path.write_bytes(blank_pdf())
    assert inspect_pdf(path, KEY, python=tmp_path / "missing")["reason"] == "pdf_parser_unavailable"
    assert inspect_pdf(path, KEY + "x", python=PYTHON)["reason"] == "pdf_resource_not_reviewed"


def test_active_page_is_not_automatically_eligible(tmp_path):
    path = tmp_path / "input.pdf"
    path.write_bytes(blank_pdf(extra="/AA << /O << /S /JavaScript /JS (bad) >> >>"))
    result = inspect_synthetic_without_os_limits(path)
    assert result["reason"] == "pdf_active_content"


def inspect_synthetic_without_os_limits(path):
    # Unit-test parser rules on tiny synthetic fixtures; never an eligibility path.
    worker = Path("packages/ingest/pdf_review_worker.py").resolve()
    code = (
        "import runpy,json,sys; from pathlib import Path; "
        "m=runpy.run_path(sys.argv[1]); "
        "print(json.dumps(m['inspect_document'](Path(sys.argv[2]),False)))"
    )
    result = subprocess.run(
        [str(PYTHON), "-I", "-c", code, str(worker), str(path)],
        check=True,
        capture_output=True,
        timeout=10,
    )
    return json.loads(result.stdout)


def test_synthetic_blank_page_parser_geometry(tmp_path):
    path = tmp_path / "blank.pdf"
    path.write_bytes(blank_pdf())
    result = inspect_synthetic_without_os_limits(path)
    assert result["status"] == "parsed"
    assert result["parserVersion"] == "6.10.0"
    assert result["pages"][0]["renderPixels"] == [850, 1100]


def test_renderer_never_runs_when_resource_limit_is_unavailable(tmp_path, monkeypatch):
    from equity_ingest import pdf_review

    path = tmp_path / "input.pdf"
    path.write_bytes(blank_pdf())
    monkeypatch.setattr(
        pdf_review,
        "inspect_pdf",
        lambda *a, **k: {
            "status": "blocked",
            "reason": "pdf_limits_unavailable",
            "pages": [],
            "visualReviewComplete": False,
        },
    )
    monkeypatch.setattr(
        pdf_review.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no renderer allowed")),
    )
    result = pdf_review.render_pdf(
        path, KEY, python=PYTHON, poppler=tmp_path, output_dir=tmp_path / "pages"
    )
    assert result["reason"] == "pdf_limits_unavailable"
    assert result["renderedPages"] == []
    assert not (tmp_path / "pages").exists()


def test_renderer_requires_pinned_version_before_any_page(tmp_path, monkeypatch):
    import hashlib
    from types import SimpleNamespace

    from equity_ingest import pdf_review

    path = tmp_path / "input.pdf"
    path.write_bytes(blank_pdf())
    for name in ("pdfinfo", "pdftoppm"):
        (tmp_path / name).write_bytes(b"synthetic executable identity")
    monkeypatch.setattr(
        pdf_review,
        "inspect_pdf",
        lambda *a, **k: {
            "status": "parsed",
            "reason": None,
            "pages": [{"page": 1, "renderPixels": [850, 1100]}],
            "inputSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "visualReviewComplete": False,
        },
    )
    calls = []

    def execute(command, **kwargs):
        calls.append(command)
        kwargs["stdout"].write(b"pdfinfo version 25.01.0\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(pdf_review.subprocess, "run", execute)
    result = pdf_review.render_pdf(
        path, KEY, python=PYTHON, poppler=tmp_path, output_dir=tmp_path / "pages"
    )
    assert result["reason"] == "pdf_renderer_version"
    assert len(calls) == 1 and calls[0][-1] == "-v"
    assert result["renderedPages"] == []


def png_bytes(width=1, height=1):
    import struct
    import zlib

    def chunk(kind, value):
        return (
            struct.pack(">I", len(value))
            + kind
            + value
            + struct.pack(">I", zlib.crc32(kind + value))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\0\xff\xff\xff"))
        + chunk(b"IEND", b"")
    )


def mocked_renderer(tmp_path, monkeypatch, payload=None, pages=1):
    import hashlib
    from types import SimpleNamespace

    from equity_ingest import pdf_review

    source = tmp_path / "input.pdf"
    source.write_bytes(blank_pdf())
    for name in ("pdfinfo", "pdftoppm"):
        (tmp_path / name).write_bytes(b"fixture binary")
    monkeypatch.setattr(
        pdf_review,
        "inspect_pdf",
        lambda *a, **k: {
            "status": "parsed",
            "reason": None,
            "pages": [{"page": n, "renderPixels": [1, 1]} for n in range(1, pages + 1)],
            "inputSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "visualReviewComplete": False,
        },
    )

    def execute(command, **kwargs):
        if command[-1] == "-v":
            kwargs["stdout"].write((Path(command[3]).name + " version 26.05.0\n").encode())
        else:
            Path(command[-1]).with_suffix(".png").write_bytes(
                png_bytes() if payload is None else payload
            )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(pdf_review.subprocess, "run", execute)
    return lambda: pdf_review.render_pdf(
        source, KEY, python=PYTHON, poppler=tmp_path, output_dir=tmp_path / "pages"
    )


def test_render_replay_verifies_identical_pages_and_rejects_changed_bytes(tmp_path, monkeypatch):
    run = mocked_renderer(tmp_path, monkeypatch)
    first = run()
    assert first["status"] == "rendered_pending_visual_review"
    second = run()
    assert second["status"] == first["status"]
    assert second["renderedPages"][0]["sha256"] == first["renderedPages"][0]["sha256"]
    assert not second["visualReviewComplete"]
    Path(first["renderedPages"][0]["path"]).write_bytes(b"changed existing evidence")
    assert run()["reason"] == "pdf_render_existing_mismatch"


def test_invalid_complete_png_is_blocked(tmp_path, monkeypatch):
    run = mocked_renderer(tmp_path, monkeypatch, payload=png_bytes()[:-12])
    assert run()["reason"] == "pdf_render_invalid_png"


def test_oversized_actual_png_is_blocked(tmp_path, monkeypatch):
    run = mocked_renderer(tmp_path, monkeypatch, payload=b"x" * (8 * 1024 * 1024 + 1))
    assert run()["reason"] == "pdf_render_output_limit"


def test_renderer_timeout_is_not_an_empty_success(tmp_path, monkeypatch):
    from equity_ingest import pdf_review

    run = mocked_renderer(tmp_path, monkeypatch)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("fixture", 15)

    monkeypatch.setattr(pdf_review.subprocess, "run", timeout)
    result = run()
    assert result["reason"] == "pdf_render_timeout" and not result["renderedPages"]


def test_real_bounded_exec_refuses_unsupported_cap_or_blocks_large_allocation(tmp_path):
    worker = Path("packages/ingest/pdf_exec_worker.py").resolve()
    marker = tmp_path / "must-not-complete"
    code = (
        "from pathlib import Path; value=bytearray(768*1024*1024); "
        "Path(__import__('sys').argv[1]).write_text('unsafe')"
    )
    result = subprocess.run(
        [str(PYTHON), "-I", str(worker), str(PYTHON), "-I", "-c", code, str(marker)],
        capture_output=True,
        timeout=15,
    )
    assert not marker.exists()
    if sys.platform == "darwin":
        assert result.returncode == 78
    else:
        assert result.returncode != 0


def test_encrypted_and_page_cap_are_explicit_parser_blocks(tmp_path):
    for kind, expected in (("encrypted", "pdf_encrypted"), ("pages", "pdf_page_count")):
        path = tmp_path / (kind + ".pdf")
        code = (
            "import pypdf,sys; w=pypdf.PdfWriter(); "
            "[w.add_blank_page(width=612,height=792) "
            "for _ in range(101 if sys.argv[2]=='pages' else 1)]; "
            "w.encrypt('fixture') if sys.argv[2]=='encrypted' else None; w.write(sys.argv[1])"
        )
        subprocess.run([str(PYTHON), "-I", "-c", code, str(path), kind], check=True, timeout=10)
        assert inspect_synthetic_without_os_limits(path)["reason"] == expected


def test_text_limit_is_blocked_without_truncating_to_success(tmp_path):
    worker = Path("packages/ingest/pdf_review_worker.py").resolve()
    code = """
import runpy,types,json,sys
from pathlib import Path
m=runpy.run_path(sys.argv[1])
page=types.SimpleNamespace(mediabox=[0,0,612,792],cropbox=[0,0,612,792],extract_text=lambda:'x'*(2*1024*1024+1))
reader=types.SimpleNamespace(is_encrypted=False,pages=[page],trailer={})
fake=types.SimpleNamespace(__version__='6.10.0',PdfReader=lambda *a,**k:reader)
m['inspect_document'].__globals__['importlib'].import_module=lambda name:fake
print(json.dumps(m['inspect_document'](Path('synthetic-only'),False)))
"""
    result = subprocess.run(
        [str(PYTHON), "-I", "-c", code, str(worker)], capture_output=True, check=True, timeout=10
    )
    parsed = json.loads(result.stdout)
    assert parsed["reason"] == "pdf_text_limit" and not parsed["pages"]


def test_reversed_nonfinite_and_outside_crop_boxes_are_blocked(tmp_path):
    for box, extra in (
        ("612 792 0 0", ""),
        ("0 0 nan 792", ""),
        ("0 0 612 792", "/CropBox [0 0 900 900]"),
    ):
        path = tmp_path / "invalid.pdf"
        path.write_bytes(blank_pdf(box, extra))
        assert inspect_synthetic_without_os_limits(path)["status"] == "blocked"


def test_parser_timeout_is_deterministically_blocked(tmp_path, monkeypatch):
    from equity_ingest import pdf_review

    path = tmp_path / "input.pdf"
    path.write_bytes(blank_pdf())

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("parser", 30)

    monkeypatch.setattr(pdf_review.subprocess, "run", timeout)
    assert pdf_review.inspect_pdf(path, KEY, python=PYTHON)["reason"] == "pdf_parser_timeout"


def test_small_compressed_image_cannot_bypass_real_host_limit_gate(tmp_path):
    import pytest
    from equity_ingest.pdf_review import render_pdf

    if sys.platform != "darwin":
        pytest.skip("This regression records this macOS host's verified limit refusal")
    path = tmp_path / "compressed-image.pdf"
    code = """
import pypdf,sys
from pypdf.generic import NameObject,NumberObject,DictionaryObject,DecodedStreamObject
w=pypdf.PdfWriter(); page=w.add_blank_page(width=612,height=792)
image=DecodedStreamObject(); image.set_data(b'\\0'*(1024*1024)); image=image.flate_encode()
for key,value in {'/Type':NameObject('/XObject'),'/Subtype':NameObject('/Image'),
 '/Width':NumberObject(100000),'/Height':NumberObject(100000),
 '/BitsPerComponent':NumberObject(8),'/ColorSpace':NameObject('/DeviceRGB')}.items():
 image[NameObject(key)]=value
page[NameObject('/Resources')]=DictionaryObject({NameObject('/XObject'):DictionaryObject({NameObject('/Im1'):w._add_object(image)})})
stream=DecodedStreamObject();stream.set_data(b'q 612 0 0 792 0 0 cm /Im1 Do Q')
page[NameObject('/Contents')]=w._add_object(stream);w.write(sys.argv[1])
"""
    subprocess.run([str(PYTHON), "-I", "-c", code, str(path)], check=True, timeout=10)
    assert path.stat().st_size < 10000
    result = render_pdf(path, KEY, python=PYTHON, poppler=tmp_path, output_dir=tmp_path / "pages")
    assert result["reason"] == "pdf_limits_unavailable"
    assert not result["pages"] and not result["renderedPages"]


def test_render_process_failure_preserves_completed_page_roster(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from equity_ingest import pdf_review

    run = mocked_renderer(tmp_path, monkeypatch, pages=2)
    previous = pdf_review.subprocess.run

    def execute(command, **kwargs):
        if command[-1].endswith("page-2"):
            return SimpleNamespace(returncode=-9)
        return previous(command, **kwargs)

    monkeypatch.setattr(pdf_review.subprocess, "run", execute)
    for _ in range(2):
        result = run()
        assert result["reason"] == "pdf_render_process_failed"
        assert [page["page"] for page in result["renderedPages"]] == [1]


def test_png_oversized_dimensions_are_blocked(tmp_path, monkeypatch):
    run = mocked_renderer(tmp_path, monkeypatch, payload=png_bytes(2001, 1))
    assert run()["reason"] == "pdf_render_pixels"


def test_contents_fixture_reaches_exact_flate_limit_and_rejects_other_errors(tmp_path):
    import zlib

    from scripts.run_crcl_pdf_proof import stream_pdf

    path = tmp_path / "tiny-compressed.pdf"
    path.write_bytes(stream_pdf(zlib.compress(b" " * 1024)))
    worker = Path("packages/ingest/pdf_review_worker.py").resolve()
    # Tiny synthetic bytes only: lower the parser limit in this test process.
    code = """
import runpy,json,sys
from pathlib import Path
import pypdf.filters as filters
from pypdf.errors import LimitReachedError
m=runpy.run_path(sys.argv[1])
filters.ZLIB_MAX_OUTPUT_LENGTH=64
result=m['inspect_document'](Path(sys.argv[2]),False)
assert result['reason']=='pdf_parser_decompression_limit', result
for error in (LimitReachedError('Limit reached while decompressing.'),
              ValueError('Limit reached while decompressing.'),
              RuntimeError('Limit reached while decompressing.')):
    try:
        raise error
    except Exception as caught:
        assert not m['is_flate_decompression_limit'](caught)
# A wrong exception raised by an actual decompression frame must not match.
original=filters.zlib.decompressobj
filters.zlib.decompressobj=lambda: (_ for _ in ()).throw(ValueError('wrong'))
try:
    filters._decompress_with_limit(b'x')
except Exception as caught:
    assert not m['is_flate_decompression_limit'](caught)
finally:
    filters.zlib.decompressobj=original
print(json.dumps(result))
"""
    result = subprocess.run(
        [str(PYTHON), "-I", "-c", code, str(worker), str(path)],
        check=True,
        capture_output=True,
        timeout=10,
    )
    assert json.loads(result.stdout)["status"] == "blocked"
