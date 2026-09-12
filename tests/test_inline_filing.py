"""Explicit Inline XBRL values specified before the original-filing extractor."""

import hashlib
from datetime import date
from decimal import Decimal, localcontext

import pytest
from equity_ingest.filing import (
    FilingDimension,
    FilingIntegrityError,
    extract_inline_filing,
    select_filing_fact,
)

XBRLI = "http://www.xbrl.org/2003/instance"
IX = "http://www.xbrl.org/2013/inlineXBRL"
TAXONOMY = "http://fasb.org/us-gaap/2025"
TAG = "{" + TAXONOMY + "}Revenue"
ISO4217 = "http://www.xbrl.org/2003/iso4217"
USD = "{" + ISO4217 + "}USD"
CONTEXT = """<xbrli:context id="c"><xbrli:entity>
<xbrli:identifier scheme="http://www.sec.gov/CIK">0000000001</xbrli:identifier>
</xbrli:entity><xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate>
<xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context>"""
UNIT = '<xbrli:unit id="u"><xbrli:measure>iso:USD</xbrli:measure></xbrli:unit>'


def document(facts, *, context=CONTEXT, unit=UNIT, extra="", transform_ns=None):
    transform_ns = transform_ns or "http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"
    return f'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="{IX}"
xmlns:xbrli="{XBRLI}" xmlns:g="{TAXONOMY}"
xmlns:iso="http://www.xbrl.org/2003/iso4217"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns:d="http://xbrl.org/2006/xbrldi" xmlns:ixt="{transform_ns}">
<head/><body><ix:header><ix:resources>{context}{unit}</ix:resources></ix:header>
{facts}{extra}</body></html>'''.encode()


def numeric(text="1", attrs='decimals="0"', *, identifier="f"):
    return f'''<ix:nonFraction id="{identifier}" name="g:Revenue" contextRef="c"
unitRef="u" {attrs}>{text}</ix:nonFraction>'''


def extract(body):
    return extract_inline_filing(
        body,
        expected_sha256=hashlib.sha256(body).hexdigest(),
        expected_byte_count=len(body),
        expected_cik="0000000001",
    )


def selection(extraction, **kwargs):
    return select_filing_fact(extraction, qualified_tag=TAG, context_id="c", unit_id="u", **kwargs)


@pytest.mark.parametrize(
    "text,attrs,expected",
    [
        ("1,234.500", 'decimals="-3" scale="3" format="ixt:num-dot-decimal"', "1234500"),
        ("12.50", 'precision="4" scale="-2" sign="-"', "-0.1250"),
        (
            "9007199254740993.0000000000000001",
            'decimals="16" scale="2"',
            "900719925474099300.00000000000001",
        ),
        ("0", 'decimals="INF"', "0"),
        ("—", 'decimals="0" format="ixt:fixed-zero"', "0"),
        ("12,34 56\u00a0789.01", 'decimals="2" format="ixt:num-dot-decimal"', "123456789.01"),
    ],
)
def test_exact_numeric_scale_sign_and_precision(text, attrs, expected):
    with localcontext() as ctx:
        ctx.prec = 6
        result = extract(document(numeric(text, attrs)))
    chosen = selection(result)
    assert result.complete
    assert chosen.status == "observed"
    assert chosen.value == Decimal(expected)
    assert chosen.fact.lexical_text == text
    assert chosen.fact.locator.startswith("elementpath:")
    assert result.contexts[0].start_date == date(2025, 1, 1)
    assert result.units[0].numerator_measures == (USD,)


def test_source_nil_is_distinct_from_zero():
    result = extract(document(numeric("", 'xsi:nil="true"')))
    assert result.complete
    assert selection(result).status == "source_nil"
    assert selection(result).value is None


@pytest.mark.parametrize(
    "text,attrs,code",
    [
        ("-100", 'decimals="0"', "invalid_numeric"),
        ("1e3", 'decimals="0"', "invalid_numeric"),
        ("NaN", 'decimals="0"', "invalid_numeric"),
        ("12,345", 'decimals="0"', "invalid_numeric"),
        ("—", 'decimals="0"', "invalid_numeric"),
        ("1", 'decimals="0" sign="+"', "invalid_sign"),
        ("1", 'decimals="0" scale="1.1"', "invalid_scale"),
        ("1", 'decimals="0" scale="1000000"', "invalid_scale"),
        ("1", 'decimals="0" precision="2"', "invalid_accuracy"),
        ("1", 'precision="0"', "invalid_accuracy"),
        ("1", "", "invalid_accuracy"),
        ("1", 'xsi:nil="true"', "invalid_nil"),
        ("1", 'xsi:nil="invalid" decimals="0"', "invalid_nil"),
        ("1", 'decimals="0" format="ixt:unknown"', "unsupported_transform"),
        ("1", 'decimals="0" continuedAt="cont"', "unsupported_numeric_structure"),
        ("1<ix:exclude>2</ix:exclude>", 'decimals="0"', "unsupported_numeric_structure"),
        ("<span>100</span>", 'decimals="0"', "unsupported_numeric_structure"),
    ],
)
def test_bad_or_unsupported_numeric_evidence_never_becomes_amount(text, attrs, code):
    result = extract(document(numeric(text, attrs)))
    assert not result.complete
    assert result.facts[0].value is None
    assert selection(result).status == "unsupported"
    assert code in {issue.code for issue in result.issues}


def test_transform_namespace_is_not_inferred_from_its_prefix():
    result = extract(
        document(
            numeric("10,000", 'decimals="0" format="ixt:num-dot-decimal"'),
            transform_ns="https://untrusted.invalid/transformations",
        )
    )
    assert selection(result).status == "unsupported"
    assert result.facts[0].format_qname.startswith("{https://untrusted.invalid/")


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.replace("0000000001", "0000000002"),
        lambda c: c.replace("http://www.sec.gov/CIK", "https://untrusted.invalid/CIK"),
        lambda c: c.replace("2025-12-31", "2024-12-31"),
        lambda c: c.replace("2025-12-31", "2025-12-31T00:00:00"),
        lambda c: c.replace(
            "</xbrli:entity>", "<xbrli:segment><g:Unknown/></xbrli:segment></xbrli:entity>"
        ),
    ],
)
def test_unknown_context_cannot_supply_selectable_fact(change):
    result = extract(document(numeric(), context=change(CONTEXT)))
    assert not result.contexts[0].valid
    assert selection(result).status == "unsupported"
    assert result.facts[0].value is None


def test_explicit_dimensions_require_exact_reviewed_selection():
    member = (
        '<xbrli:segment><d:explicitMember dimension="g:ShareClassAxis">'
        "g:ADSMember</d:explicitMember></xbrli:segment>"
    )
    result = extract(
        document(numeric(), context=CONTEXT.replace("</xbrli:entity>", member + "</xbrli:entity>"))
    )
    dimension = FilingDimension(
        "{" + TAXONOMY + "}ShareClassAxis", "{" + TAXONOMY + "}ADSMember", "segment"
    )
    assert result.contexts[0].dimensions == (dimension,)
    assert selection(result).status == "unsupported"
    assert selection(result, expected_dimensions=(dimension,)).value == Decimal("1")


def test_typed_dimensions_are_preserved_but_unsupported():
    segment = (
        '<xbrli:segment><d:typedMember dimension="g:Axis">'
        "<g:Code>A</g:Code></d:typedMember></xbrli:segment>"
    )
    result = extract(
        document(numeric(), context=CONTEXT.replace("</xbrli:entity>", segment + "</xbrli:entity>"))
    )
    assert "typedMember" in result.contexts[0].raw_xml
    assert selection(result).status == "unsupported"


def test_duplicate_context_ids_are_not_resolved_by_order():
    result = extract(
        document(numeric(), context=CONTEXT + CONTEXT.replace("2025-12-31", "2024-12-31"))
    )
    assert selection(result).status == "unsupported"
    assert "duplicate_id" in {issue.code for issue in result.issues}


def test_currency_per_share_division_is_kept_as_unit_evidence():
    unit = """<xbrli:unit id="u"><xbrli:divide><xbrli:unitNumerator>
<xbrli:measure>iso:USD</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator>
<xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>"""
    result = extract(document(numeric("2.09", 'decimals="2"'), unit=unit))
    assert result.units[0].denominator_measures == ("{" + XBRLI + "}shares",)
    assert selection(result).value == Decimal("2.09")


def test_conflicting_repeated_facts_are_ambiguous():
    result = extract(document(numeric("1") + numeric("2", identifier="g")))
    assert selection(result).status == "ambiguous"
    assert selection(result).value is None
    assert len(selection(result).candidate_locators) == 2


def test_identical_repeated_facts_keep_all_evidence_locators():
    result = extract(document(numeric("1") + numeric("1", identifier="g")))
    assert selection(result).value == Decimal("1")
    assert len(selection(result).candidate_locators) == 2


def test_non_numeric_continuation_and_exclusion_preserve_text_only():
    fact = """<ix:nonNumeric id="n" name="g:Note" contextRef="c" continuedAt="cont">
First<ix:exclude>discard</ix:exclude> second</ix:nonNumeric>"""
    extra = '<ix:continuation id="cont"> third</ix:continuation>'
    result = extract(document(fact, extra=extra))
    assert result.facts[0].lexical_text == "\nFirst second third"
    assert result.facts[0].status == "text"
    assert result.facts[0].value is None


@pytest.mark.parametrize(
    "extra",
    [
        '<ix:continuation id="cont" continuedAt="cont">cyclic</ix:continuation>',
        "",
    ],
)
def test_bad_continuation_is_not_silently_truncated(extra):
    fact = (
        '<ix:nonNumeric id="n" name="g:Note" contextRef="c" continuedAt="cont">'
        "First</ix:nonNumeric>"
    )
    result = extract(document(fact, extra=extra))
    assert result.facts[0].status == "unsupported"
    assert not result.complete


def test_untrusted_tag_namespace_is_not_matched_by_local_name():
    body = document(numeric()).replace(TAXONOMY.encode(), b"https://untrusted.invalid/taxonomy")
    result = extract(body)
    assert selection(result).status == "missing"


@pytest.mark.parametrize(
    "body",
    [
        b"<html><p>Malformed</html>",
        b'<!DOCTYPE html [<!ENTITY secret SYSTEM "file:///etc/passwd">]><html>&secret;</html>',
        b'<html xmlns="http://www.w3.org/1999/xhtml"><body>ordinary HTML</body></html>',
    ],
)
def test_non_inline_or_unsafe_xml_returns_explicit_document_gap(body):
    result = extract(body)
    assert not result.complete
    assert result.facts == ()
    assert result.issues


def test_capture_hash_and_size_are_verified_before_parsing():
    body = document(numeric())
    for sha, size in [("a" * 64, len(body)), (hashlib.sha256(body).hexdigest(), len(body) + 1)]:
        with pytest.raises(FilingIntegrityError):
            extract_inline_filing(
                body, expected_sha256=sha, expected_byte_count=size, expected_cik="1"
            )


def test_resource_context_outside_inline_header_is_not_selectable():
    body = document(numeric(), context="").replace(b"</body>", CONTEXT.encode() + b"</body>")
    assert selection(extract(body)).status == "unsupported"


def test_empty_transform_attribute_is_not_treated_as_absent():
    assert (
        selection(extract(document(numeric("1", 'decimals="0" format=""')))).status == "unsupported"
    )


def test_nested_numeric_child_does_not_escape_unsupported_parent():
    inner = numeric("1", identifier="inner")
    outer = numeric(inner, 'decimals="0" scale="3"').replace(
        'name="g:Revenue"', 'name="g:Other"', 1
    )
    assert selection(extract(document(outer))).status == "unsupported"


def test_same_continuation_cannot_be_claimed_by_two_facts():
    first = (
        '<ix:nonNumeric id="n" name="g:Note" contextRef="c" continuedAt="cont">'
        "First</ix:nonNumeric>"
    )
    second = first.replace('id="n"', 'id="m"')
    result = extract(
        document(first + second, extra='<ix:continuation id="cont">tail</ix:continuation>')
    )
    assert all(f.status == "unsupported" for f in result.facts)


def test_unit_namespace_cannot_borrow_iso4217_currency_meaning():
    body = document(numeric()).replace(ISO4217.encode(), b"https://untrusted.invalid/currency")
    assert selection(extract(body)).status == "unsupported"


def test_unknown_scope_tail_is_not_hidden_by_a_reviewed_dimension():
    member = (
        '<xbrli:segment><d:explicitMember dimension="g:ShareClassAxis">'
        "g:ADSMember</d:explicitMember>UNREVIEWED_SCOPE_TEXT</xbrli:segment>"
    )
    result = extract(
        document(numeric(), context=CONTEXT.replace("</xbrli:entity>", member + "</xbrli:entity>"))
    )
    dimension = FilingDimension(
        "{" + TAXONOMY + "}ShareClassAxis", "{" + TAXONOMY + "}ADSMember", "segment"
    )
    assert selection(result, expected_dimensions=(dimension,)).status == "unsupported"


@pytest.mark.parametrize("scope", ["context", "entity", "period", "unit"])
def test_element_only_resource_cannot_ignore_free_text(scope):
    body = document(numeric()).replace(
        f"</xbrli:{scope}>".encode(), f"UNKNOWN_SCOPE</xbrli:{scope}>".encode()
    )
    assert selection(extract(body)).status == "unsupported"


def test_element_only_resource_allows_comments_and_whitespace():
    body = document(numeric()).replace(
        b"</xbrli:entity>", b"<!-- explanation -->\n </xbrli:entity>"
    )
    assert selection(extract(body)).value == Decimal("1")
