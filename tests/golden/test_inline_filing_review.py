"""Independent scope/unit review cases for the bounded Inline XBRL reader."""

import pytest
from equity_ingest.filing import FilingDimension

from tests.test_inline_filing import CONTEXT, TAXONOMY, UNIT, document, extract, numeric, selection


@pytest.mark.parametrize("location", ["segment", "scenario"])
def test_unreviewed_text_after_dimension_is_not_silently_removed(location):
    member = (
        f'<xbrli:{location}><d:explicitMember dimension="g:ShareClassAxis">'
        f"g:ADSMember</d:explicitMember>UNREVIEWED_SCOPE_TEXT</xbrli:{location}>"
    )
    context = (
        CONTEXT.replace("</xbrli:entity>", member + "</xbrli:entity>")
        if location == "segment"
        else CONTEXT.replace("</xbrli:context>", member + "</xbrli:context>")
    )
    extracted = extract(document(numeric("100"), context=context))
    reviewed = FilingDimension(
        "{" + TAXONOMY + "}ShareClassAxis", "{" + TAXONOMY + "}ADSMember", location
    )
    assert selection(extracted, expected_dimensions=(reviewed,)).status == "unsupported"
    assert not extracted.contexts[0].valid


@pytest.mark.parametrize("placement", ["before", "after"])
def test_unreviewed_text_around_unit_measures_cannot_supply_an_amount(placement):
    if placement == "before":
        unit = UNIT.replace('<xbrli:unit id="u">', '<xbrli:unit id="u">UNKNOWN_UNIT_CONTENT')
    else:
        unit = UNIT.replace("</xbrli:measure>", "</xbrli:measure>UNKNOWN_UNIT_CONTENT")
    extracted = extract(document(numeric("100"), unit=unit))
    assert selection(extracted).status == "unsupported"
    assert not extracted.units[0].valid
