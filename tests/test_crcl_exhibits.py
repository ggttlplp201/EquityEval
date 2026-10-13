"""D5d never promotes absent or misidentified exhibit evidence."""

import pytest

from scripts import review_crcl_exhibits as exhibits


def test_exact_missing_exhibits_are_pinned_and_grouped_within_existing_cap():
    plan = exhibits.plan()
    assert len(plan) == 11
    assert len({row["resourceKey"] for row in plan}) == 11
    assert [len(group) for group in exhibits.groups(plan)] == [5, 5, 1]
    assert all(row["form"] == "8-K" for row in plan)
    assert {row["exhibit"] for row in plan} == {"3.1", "3.2", "99.1", "2.1"}
    with pytest.raises(ValueError):
        exhibits.groups([plan[0], plan[0]])


def test_source_acquisition_cannot_change_prior_rows_or_create_financial_results():
    from scripts.capture_crcl_exhibits import preserved

    before = {"source_captures": ["old"], "fact_resolutions": ["fact"]}
    assert preserved(before, {"source_captures": ["old", "new"], "fact_resolutions": ["fact"]})
    assert not preserved(before, {"source_captures": ["new"], "fact_resolutions": ["fact"]})
    assert not preserved(
        before, {"source_captures": ["old"], "fact_resolutions": ["fact", "extra"]}
    )


def test_missing_or_misidentified_capture_never_becomes_a_reviewed_exhibit():
    planned = exhibits.plan()
    capture = {
        "source_object_key": planned[0]["resourceKey"],
        "completed_at": "2026-10-13T03:00:00+00:00",
        "http_status": 200,
    }
    assert list(exhibits.capture_index([capture], planned)) == [planned[0]["resourceKey"]]
    assert exhibits.capture_index([], planned) == {}
    with pytest.raises(ValueError):
        exhibits.capture_index([capture, capture], planned)
    with pytest.raises(ValueError):
        exhibits.capture_index(
            [{**capture, "source_object_key": "filing_document/0001876042/unplanned.htm"}], planned
        )
    with pytest.raises(ValueError):
        exhibits.capture_index([{**capture, "completed_at": "2026-09-21T00:00:00+00:00"}], planned)
    with pytest.raises(ValueError):
        exhibits.capture_index([{**capture, "completed_at": "2026-10-13T03:00:00"}], planned)


def test_review_body_is_bound_to_content_and_exact_quotes():
    import hashlib

    body = b"<html><body>Section A. Revenue is reported.</body></html>"
    digest = hashlib.sha256(body).hexdigest()
    assert exhibits.checked_text(body, digest, ["Revenue is reported."])
    with pytest.raises(ValueError):
        exhibits.checked_text(body + b"changed", digest, ["Revenue is reported."])
    with pytest.raises(ValueError):
        exhibits.checked_text(body, digest, ["Revenue was restated."])


def test_statement_check_rejects_wrong_period_unit_column_and_signed_operand():
    header = "CONSOLIDATED STATEMENTS OF OPERATIONS (in thousands) Year Ended December 31, 2025"
    text = header + (
        " Total revenue and reserve income 2,746,642 Costs Operating income "
        "(loss) from continuing operations (96,435) Other income"
    )
    expected = [
        ("Total revenue and reserve income", ["2,746,642"]),
        ("Operating income (loss) from continuing operations", ["(96,435)"]),
    ]
    assert exhibits.statement_rows(text, header, expected)
    for changed in (
        text.replace("2025", "2024"),
        text.replace("thousands", "millions"),
        text.replace("(96,435)", "96,435"),
        text.replace("2,746,642", "1,676,253"),
    ):
        with pytest.raises(ValueError):
            exhibits.statement_rows(changed, header, expected)


def test_incomplete_acquisition_review_is_blocked_and_names_missing_bodies():
    result = exhibits.review_acquisition(None)
    assert len(result["missingExhibits"]) == 11
    assert result["reviewedCount"] == 0
    assert result["operatingMargin"] is None
    assert result["freshInventory"] is None
    assert "inventory" in result["nextStep"].lower()
    assert "two" not in result["nextStep"]
    assert "corroboration is unavailable" in " ".join(result["blockers"])
    partial = exhibits.review_acquisition({"groups": [{"captures": []}], "status": "incomplete"})
    assert partial["reviewedCount"] == 0
    assert "corroboration is unavailable" in " ".join(partial["blockers"])
    assert "corroborate those periods" not in " ".join(partial["blockers"])


def test_periodic_comparison_requires_consolidated_usd_exact_period_scale_and_sign(monkeypatch):
    from datetime import date
    from types import SimpleNamespace as Row

    import equity_ingest.filing as filing

    context = Row(
        id="c",
        valid=True,
        cik="0001876042",
        period_kind="duration",
        dimensions=(),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    unit = Row(
        id="u",
        valid=True,
        denominator_measures=(),
        numerator_measures=("{http://www.xbrl.org/2003/iso4217}USD",),
    )
    facts = [
        Row(
            qualified_tag="{http://fasb.org/us-gaap/2025}" + concept,
            context_id="c",
            unit_id="u",
            status="observed",
            scale=3,
            lexical_text=value,
            sign=sign,
            locator="fact/" + concept,
        )
        for concept, value, sign in [
            ("Revenues", "2,746,642", None),
            ("OperatingIncomeLoss", "96,435", "-"),
        ]
    ]
    parsed = Row(contexts=[context], units=[unit], facts=facts)
    monkeypatch.setattr(filing, "extract_inline_filing", lambda *args, **kwargs: parsed)
    capture = {"body_sha256": "test", "byte_count": 0, "capture_id": "capture"}

    def compare():
        return exhibits.periodic_evidence(
            capture, b"", [(0, "2025-01-01", "2025-12-31")], [["2,746,642"], ["(96,435)"]]
        )

    assert len(compare()) == 2
    for target, field, changed in [
        (unit, "numerator_measures", ("{http://www.xbrl.org/2003/iso4217}EUR",)),
        (context, "dimensions", ("segment",)),
        (context, "end_date", date(2024, 12, 31)),
        (facts[1], "sign", None),
        (facts[0], "scale", 6),
        (facts[0], "lexical_text", "1,676,253"),
    ]:
        original = getattr(target, field)
        setattr(target, field, changed)
        with pytest.raises(ValueError):
            compare()
        setattr(target, field, original)


def test_saved_review_and_projection_never_promote_financial_eligibility():
    import copy
    import json

    from scripts.export_crcl_exhibits import project

    saved = json.loads((exhibits.ROOT / exhibits.REPORT).read_bytes())
    assert saved["reviewedCount"] == 11
    assert saved["missingExhibits"] == []
    assert len(saved["details"]) == 11
    assert sum(len(row.get("periodicComparisons", [])) for row in saved["exhibits"]) == 22
    assert saved["historicalStatus"] == saved["currentStatus"] == "blocked"
    assert project(saved)["operatingMargin"] is None
    changed = copy.deepcopy(saved)
    changed["exhibits"][0]["finding"] = "safe"
    with pytest.raises(ValueError):
        project(changed)


def test_unavailable_prerequisite_records_blocked_attempt_without_implicit_retry(
    tmp_path, monkeypatch
):
    import json

    from scripts import capture_crcl_exhibits as capture

    monkeypatch.setattr(capture, "ROOT", tmp_path)
    target = tmp_path / capture.ACQUISITION
    target.parent.mkdir(parents=True)

    def unavailable(**kwargs):
        raise RuntimeError("sensitive runtime details must not appear")

    monkeypatch.setattr(capture, "recover", unavailable)
    capture.capture()
    result = json.loads(target.read_text())
    assert result["status"] == "blocked"
    assert result["errorType"] == "RuntimeError"
    assert result["originalRowsPreserved"] is None
    assert result["groups"] == []
    assert "sensitive" not in target.read_text()
    with pytest.raises(ValueError):
        capture.capture()
