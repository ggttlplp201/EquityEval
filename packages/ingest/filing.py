"""Conservative extraction from verified archived Inline XBRL 1.1 XHTML bytes.

This is a bounded source reader, not a DTS/schema validator or concept mapper.
Unsupported facts retain evidence and cannot supply selected amounts. Numeric
transforms are the exact registry-4/5 num-dot-decimal and fixed-zero definitions.

Primary specifications reviewed for this implementation:
https://www.xbrl.org/specification/inlinexbrl-part1/rec-2013-11-18/inlinexbrl-part1-rec-2013-11-18.html
https://specifications.xbrl.org/work-product-index-inline-xbrl-transformation-registry-4.html
https://specifications.xbrl.org/work-product-index-inline-xbrl-transformation-registry-5.html
https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-06-29.pdf
"""

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, cast

from lxml import etree

IX = "http://www.xbrl.org/2013/inlineXBRL"
XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
XHTML = "http://www.w3.org/1999/xhtml"
ISO4217 = "http://www.xbrl.org/2003/iso4217"
TRANSFORMS = frozenset(
    f"http://www.xbrl.org/inlineXBRL/transformation/{version}"
    for version in ("2020-02-12", "2022-02-16")
)
MAX_BODY_BYTES = 64 * 1024 * 1024
MAX_NUMERIC_CHARS = 4096
MAX_SCALE = 10000
FactStatus = Literal["observed", "source_nil", "text", "unsupported"]
SelectionStatus = Literal["observed", "source_nil", "missing", "ambiguous", "unsupported"]


class FilingIntegrityError(ValueError):
    """Bytes do not match the pinned capture; no extraction was attempted."""


@dataclass(frozen=True)
class FilingIssue:
    code: str
    locator: str
    detail: str


@dataclass(frozen=True)
class FilingDimension:
    axis: str
    member: str
    location: str


@dataclass(frozen=True)
class FilingContext:
    id: str
    entity_scheme: str | None
    entity_identifier: str | None
    cik: str | None
    period_kind: str | None
    start_date: date | None
    end_date: date | None
    dimensions: tuple[FilingDimension, ...]
    raw_xml: str
    locator: str
    valid: bool


@dataclass(frozen=True)
class FilingUnit:
    id: str
    numerator_measures: tuple[str, ...]
    denominator_measures: tuple[str, ...]
    raw_xml: str
    locator: str
    valid: bool


@dataclass(frozen=True)
class FilingFact:
    id: str | None
    kind: str
    qualified_tag: str
    raw_name: str | None
    context_id: str | None
    unit_id: str | None
    lexical_text: str
    scale: int | None
    sign: str | None
    decimals: str | None
    precision: str | None
    format_qname: str | None
    attributes: tuple[tuple[str, str], ...]
    value: Decimal | None
    status: FactStatus
    locator: str
    evidence_locators: tuple[str, ...]
    issue_codes: tuple[str, ...]


@dataclass(frozen=True)
class FilingExtraction:
    capture_sha256: str
    byte_count: int
    cik: str
    contexts: tuple[FilingContext, ...]
    units: tuple[FilingUnit, ...]
    facts: tuple[FilingFact, ...]
    issues: tuple[FilingIssue, ...]
    complete: bool


@dataclass(frozen=True)
class FilingSelection:
    status: SelectionStatus
    value: Decimal | None
    fact: FilingFact | None
    candidate_locators: tuple[str, ...]
    reason: str


class _Unsupported(ValueError):
    pass


def _cik(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,10}", value) or int(value) == 0:
        raise ValueError("Expected a nonzero SEC CIK digit string of at most ten characters")
    return value.zfill(10)


def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _children(node: etree._Element) -> list[etree._Element]:
    return [child for child in node if isinstance(child.tag, str)]


def _locator(node: etree._Element) -> str:
    # Clark-name ElementPath is unambiguous even if a document rebinds prefixes.
    return "elementpath:" + node.getroottree().getelementpath(node)


def _xml(node: etree._Element) -> str:
    return etree.tostring(node, encoding="unicode", with_tail=False)


def _qname(node: etree._Element, lexical: str | None) -> str:
    if lexical is None:
        raise _Unsupported("missing_qname")
    lexical = lexical.strip()
    pieces = lexical.split(":")
    if len(pieces) > 2 or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", p) for p in pieces):
        raise _Unsupported("invalid_qname")
    prefix, local = (pieces[0], pieces[1]) if len(pieces) == 2 else (None, pieces[0])
    namespace = node.nsmap.get(prefix)
    if not namespace or not re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", namespace):
        raise _Unsupported("unresolved_qname")
    return _tag(namespace, local)


def _require_resource(node: etree._Element) -> None:
    element_only = {
        _tag(XBRLI, name)
        for name in (
            "context",
            "entity",
            "period",
            "segment",
            "scenario",
            "unit",
            "divide",
            "unitNumerator",
            "unitDenominator",
        )
    }
    for part in node.iter():
        if (
            isinstance(part.tag, str)
            and part.tag in element_only
            and ((part.text or "").strip() or any((child.tail or "").strip() for child in part))
        ):
            raise _Unsupported("unrecognized_resource_text")
    parent = node.getparent()
    grandparent = parent.getparent() if parent is not None else None
    if (
        parent is None
        or parent.tag != _tag(IX, "resources")
        or grandparent is None
        or grandparent.tag != _tag(IX, "header")
    ):
        raise _Unsupported("invalid_resource_placement")


def _only(node: etree._Element, name: str) -> etree._Element:
    found = node.findall(_tag(XBRLI, name))
    if len(found) != 1:
        raise _Unsupported("invalid_context_structure")
    return found[0]


def _date(node: etree._Element) -> date:
    text = (node.text or "").strip()
    if _children(node) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise _Unsupported("unsupported_period")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise _Unsupported("invalid_period") from exc


def _context(
    node: etree._Element, cik: str, duplicate_ids: set[str], issues: list[FilingIssue]
) -> FilingContext:
    identifier = node.get("id", "")
    scheme = raw_identifier = actual_cik = period_kind = None
    start = end = None
    dimensions: list[FilingDimension] = []
    valid = True
    try:
        _require_resource(node)
        if not identifier or identifier in duplicate_ids:
            raise _Unsupported("duplicate_id" if identifier else "missing_id")
        entity, period = _only(node, "entity"), _only(node, "period")
        if any(
            c.tag not in {_tag(XBRLI, "entity"), _tag(XBRLI, "period"), _tag(XBRLI, "scenario")}
            for c in _children(node)
        ):
            raise _Unsupported("invalid_context_structure")
        identity = _only(entity, "identifier")
        scheme, raw_identifier = identity.get("scheme"), identity.text
        if scheme != "http://www.sec.gov/CIK" or _children(identity):
            raise _Unsupported("unverified_entity")
        if not raw_identifier or not re.fullmatch(r"[0-9]{10}", raw_identifier):
            raise _Unsupported("unverified_entity")
        actual_cik = _cik(raw_identifier)
        if actual_cik != cik:
            raise _Unsupported("wrong_entity")
        if any(
            c.tag not in {_tag(XBRLI, "identifier"), _tag(XBRLI, "segment")}
            for c in _children(entity)
        ):
            raise _Unsupported("unknown_context_scope")
        periods = [c.tag for c in _children(period)]
        if periods == [_tag(XBRLI, "instant")]:
            period_kind, end = "instant", _date(_only(period, "instant"))
        elif periods == [_tag(XBRLI, "startDate"), _tag(XBRLI, "endDate")]:
            period_kind = "duration"
            start, end = _date(_only(period, "startDate")), _date(_only(period, "endDate"))
            if start > end:
                raise _Unsupported("invalid_period")
        else:
            raise _Unsupported("unsupported_period")
        for parent, location in ((entity, "segment"), (node, "scenario")):
            containers = parent.findall(_tag(XBRLI, location))
            if len(containers) > 1:
                raise _Unsupported("unknown_context_scope")
            for container in containers:
                if (container.text or "").strip() or not _children(container):
                    raise _Unsupported("unknown_context_scope")
                for dimension in _children(container):
                    if dimension.tag != _tag(XBRLDI, "explicitMember") or _children(dimension):
                        raise _Unsupported("unknown_context_scope")
                    dimensions.append(
                        FilingDimension(
                            _qname(dimension, dimension.get("dimension")),
                            _qname(dimension, dimension.text),
                            location,
                        )
                    )
        if len({d.axis for d in dimensions}) != len(dimensions):
            raise _Unsupported("duplicate_dimension")
    except (ValueError, _Unsupported) as exc:
        valid = False
        issues.append(FilingIssue(str(exc), _locator(node), "Context is not selectable"))
    return FilingContext(
        identifier,
        scheme,
        raw_identifier,
        actual_cik,
        period_kind,
        start,
        end,
        tuple(sorted(dimensions, key=lambda d: (d.axis, d.member, d.location))),
        _xml(node),
        _locator(node),
        valid,
    )


def _measures(parent: etree._Element) -> tuple[str, ...]:
    children = _children(parent)
    if not children or any(c.tag != _tag(XBRLI, "measure") or _children(c) for c in children):
        raise _Unsupported("invalid_unit")
    values = tuple(_qname(c, c.text) for c in children)
    for value in values:
        qname = etree.QName(value)
        if not (
            (qname.namespace == ISO4217 and re.fullmatch(r"[A-Z]{3}", qname.localname))
            or (qname.namespace == XBRLI and qname.localname in {"pure", "shares"})
        ):
            raise _Unsupported("unsupported_unit_measure")
    return values


def _unit(node: etree._Element, duplicate_ids: set[str], issues: list[FilingIssue]) -> FilingUnit:
    identifier = node.get("id", "")
    numerator: tuple[str, ...] = ()
    denominator: tuple[str, ...] = ()
    valid = True
    try:
        _require_resource(node)
        if not identifier or identifier in duplicate_ids:
            raise _Unsupported("duplicate_id" if identifier else "missing_id")
        children = _children(node)
        if len(children) == 1 and children[0].tag == _tag(XBRLI, "divide"):
            division = _children(children[0])
            if [c.tag for c in division] != [
                _tag(XBRLI, "unitNumerator"),
                _tag(XBRLI, "unitDenominator"),
            ]:
                raise _Unsupported("invalid_unit")
            numerator, denominator = _measures(division[0]), _measures(division[1])
        else:
            numerator = _measures(node)
    except _Unsupported as exc:
        valid = False
        issues.append(FilingIssue(str(exc), _locator(node), "Unit is not selectable"))
    return FilingUnit(identifier, numerator, denominator, _xml(node), _locator(node), valid)


def _text_without_excluded(node: etree._Element) -> str:
    pieces = [node.text or ""]
    for child in node:
        if isinstance(child.tag, str) and child.tag != _tag(IX, "exclude"):
            pieces.append(_text_without_excluded(child))
        pieces.append(child.tail or "")
    return "".join(pieces)


def _continued_text(
    node: etree._Element, ids: dict[str, etree._Element], duplicate_ids: set[str]
) -> tuple[str, tuple[str, ...]]:
    pieces, locators = [], []
    current = node
    visited: set[str] = set()
    visited_nodes = [node]
    while True:
        pieces.append(_text_without_excluded(current))
        locators.append(_locator(current))
        reference = current.get("continuedAt")
        if reference is None:
            return "".join(pieces), tuple(locators)
        if reference in visited or reference in duplicate_ids or reference not in ids:
            raise _Unsupported("invalid_continuation")
        visited.add(reference)
        following = ids[reference]
        if following.tag != _tag(IX, "continuation"):
            raise _Unsupported("invalid_continuation")
        if any(
            following in prior.iterancestors() or prior in following.iterancestors()
            for prior in visited_nodes
        ):
            raise _Unsupported("invalid_continuation")
        visited_nodes.append(following)
        current = following


def _number(lexical: str, format_qname: str | None, scale: int, sign: str | None) -> Decimal:
    if len(lexical) > MAX_NUMERIC_CHARS:
        raise _Unsupported("numeric_limit")
    text = lexical.strip(" \t\r\n")
    if format_qname:
        fmt = etree.QName(format_qname)
        if fmt.namespace not in TRANSFORMS or fmt.localname not in {
            "num-dot-decimal",
            "fixed-zero",
        }:
            raise _Unsupported("unsupported_transform")
        if fmt.localname == "fixed-zero":
            text = "0"  # An explicit source transform, never a missing-value substitution.
        else:
            text = re.sub(r"[\t\r\n]", " ", text)
            if not re.fullmatch(r"[, \u00a00-9]*(?:\.[ \u00a00-9]+)?", text):
                raise _Unsupported("invalid_numeric")
            text = text.replace(",", "").replace(" ", "").replace("\u00a0", "")
    if not re.fullmatch(r"\+?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", text):
        raise _Unsupported("invalid_numeric")
    value = Decimal(text)
    digits = value.as_tuple()
    # Tuple construction shifts the decimal exponent exactly, independent of the
    # caller's Decimal context; no multiply/scaleb operation can round the source.
    assert isinstance(digits.exponent, int)
    return Decimal((1 if sign == "-" else 0, digits.digits, digits.exponent + scale))


def _fact(
    node: etree._Element,
    contexts: dict[str, FilingContext],
    units: dict[str, FilingUnit],
    ids: dict[str, etree._Element],
    duplicate_ids: set[str],
    invalid_continuations: set[str],
    issues: list[FilingIssue],
) -> FilingFact:
    kind = etree.QName(node).localname
    qualified_tag = ""
    context_id, unit_id = node.get("contextRef"), node.get("unitRef")
    lexical = "".join(cast(str, text) for text in node.itertext())
    value = None
    scale = None
    format_qname = None
    status: FactStatus = "unsupported"
    locators: tuple[str, ...] = (_locator(node),)
    codes: tuple[str, ...] = ()
    try:
        qualified_tag = _qname(node, node.get("name"))
        if node.get("id") in duplicate_ids:
            raise _Unsupported("duplicate_id")
        if (
            node.get("target")
            or node.get("tupleRef")
            or any(p.tag == _tag(IX, "tuple") for p in node.iterancestors())
        ):
            raise _Unsupported("unsupported_target_or_tuple")
        if node.get("format") is not None:
            format_qname = _qname(node, node.get("format"))
        if context_id is None or context_id not in contexts or not contexts[context_id].valid:
            raise _Unsupported("invalid_context")
        nil = node.get(_tag(XSI, "nil"))
        if nil not in {None, "true", "false", "1", "0"}:
            raise _Unsupported("invalid_nil")
        is_nil = nil in {"true", "1"}
        if kind == "nonNumeric":
            lexical, locators = _continued_text(node, ids, duplicate_ids | invalid_continuations)
            if is_nil and (lexical.strip() or _children(node) or node.get("continuedAt")):
                raise _Unsupported("invalid_nil")
            if format_qname or node.get("escape") not in {None, "false", "0"}:
                raise _Unsupported("unsupported_text_transform")
            status = "source_nil" if is_nil else "text"
        elif kind == "nonFraction":
            if unit_id is None or unit_id not in units or not units[unit_id].valid:
                raise _Unsupported("invalid_unit")
            if (
                node.get("continuedAt") is not None
                or _children(node)
                or any(p.tag == _tag(IX, "nonFraction") for p in node.iterancestors())
            ):
                raise _Unsupported("unsupported_numeric_structure")
            if node.get("sign") not in {None, "-"}:
                raise _Unsupported("invalid_sign")
            raw_scale = node.get("scale", "0")
            if not re.fullmatch(r"[+-]?[0-9]{1,6}", raw_scale) or abs(int(raw_scale)) > MAX_SCALE:
                raise _Unsupported("invalid_scale")
            scale = int(raw_scale)
            decimals, precision = node.get("decimals"), node.get("precision")
            if is_nil:
                if lexical.strip() or decimals is not None or precision is not None:
                    raise _Unsupported("invalid_nil")
                status = "source_nil"
            else:
                if (decimals is None) == (precision is None):
                    raise _Unsupported("invalid_accuracy")
                if decimals is not None and not re.fullmatch(r"INF|[+-]?[0-9]+", decimals):
                    raise _Unsupported("invalid_accuracy")
                if precision is not None and not re.fullmatch(r"INF|[1-9][0-9]*", precision):
                    raise _Unsupported("invalid_accuracy")
                value = _number(lexical, format_qname, scale, node.get("sign"))
                status = "observed"
        else:
            raise _Unsupported("unsupported_fraction")
    except _Unsupported as exc:
        codes = (str(exc),)
        issues.append(
            FilingIssue(str(exc), _locator(node), "Fact retained without a selectable amount")
        )
    return FilingFact(
        node.get("id"),
        kind,
        qualified_tag,
        node.get("name"),
        context_id,
        unit_id,
        lexical,
        scale,
        node.get("sign"),
        node.get("decimals"),
        node.get("precision"),
        format_qname,
        tuple(sorted((cast(str, key), cast(str, value)) for key, value in node.attrib.items())),
        value,
        status,
        _locator(node),
        locators,
        codes,
    )


def extract_inline_filing(
    body: bytes,
    *,
    expected_sha256: str,
    expected_byte_count: int,
    expected_cik: str,
) -> FilingExtraction:
    """Verify immutable bytes, then read the supported single-document XHTML subset.

    ``complete`` describes extraction coverage, not filing or historical coverage.
    A local unsupported fact does not invalidate an independently reviewed fact;
    malformed/unsafe documents have no facts. Context IDs do not establish business
    scope by themselves: selection requires an exact reviewed dimension set.
    """
    cik = _cik(expected_cik)
    digest = hashlib.sha256(body).hexdigest()
    if digest != expected_sha256 or len(body) != expected_byte_count:
        raise FilingIntegrityError("Archived filing hash or byte count does not match capture")
    issues: list[FilingIssue] = []

    def failed(code: str, detail: str) -> FilingExtraction:
        return FilingExtraction(
            digest, len(body), cik, (), (), (), (FilingIssue(code, "document", detail),), False
        )

    if len(body) > MAX_BODY_BYTES:
        return failed("document_limit", "Filing exceeds the bounded XML reader limit")
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        recover=False,
        huge_tree=False,
        remove_comments=False,
    )
    try:
        root = etree.fromstring(body, parser)
    except etree.XMLSyntaxError:
        return failed(
            "malformed_xml", "Source is not well-formed supported XHTML; no HTML recovery"
        )
    if getattr(root.getroottree().docinfo, "doctype", None) or any(
        isinstance(n, etree._Entity) for n in root.iter()
    ):
        return failed("unsafe_xml", "DTD and entity-bearing documents are unsupported")
    if root.tag != _tag(XHTML, "html"):
        return failed("unsupported_document", "Expected a namespace-qualified XHTML document")
    nodes = [n for n in root.iter() if isinstance(n.tag, str)]
    fact_nodes = [
        n
        for n in nodes
        if n.tag in {_tag(IX, name) for name in ("nonFraction", "nonNumeric", "fraction")}
    ]
    if not fact_nodes:
        return failed("no_inline_facts", "No supported Inline XBRL 1.1 fact elements")
    counts = Counter(n.get("id") for n in nodes if n.get("id") is not None)
    duplicates = {identifier for identifier, count in counts.items() if count > 1 and identifier}
    ids = {n.get("id", ""): n for n in nodes if n.get("id") not in duplicates}
    contexts = tuple(
        _context(n, cik, duplicates, issues) for n in nodes if n.tag == _tag(XBRLI, "context")
    )
    units = tuple(_unit(n, duplicates, issues) for n in nodes if n.tag == _tag(XBRLI, "unit"))
    context_map, unit_map = {c.id: c for c in contexts}, {u.id: u for u in units}
    references = Counter(n.get("continuedAt") for n in nodes if n.get("continuedAt") is not None)
    shared = {reference for reference, count in references.items() if count > 1 and reference}
    facts = tuple(
        _fact(n, context_map, unit_map, ids, duplicates, shared, issues) for n in fact_nodes
    )
    return FilingExtraction(
        digest, len(body), cik, contexts, units, facts, tuple(issues), not issues
    )


def select_filing_fact(
    extraction: FilingExtraction,
    *,
    qualified_tag: str,
    context_id: str,
    unit_id: str,
    expected_dimensions: tuple[FilingDimension, ...] = (),
) -> FilingSelection:
    """Select only an exact reviewed tag/context/unit/scope, retaining repetitions.

    Qualified tags use expanded Clark names (``{namespaceURI}LocalName``), never
    an inferred prefix. Equal repeats require equal value, accuracy and transform
    evidence; conflicting or unsupported matching rows are never silently skipped.
    """
    if not qualified_tag.startswith("{") or "}" not in qualified_tag:
        raise ValueError("Selection requires an expanded namespace-qualified tag")
    candidates = tuple(
        f
        for f in extraction.facts
        if f.qualified_tag == qualified_tag
        and f.context_id == context_id
        and f.unit_id == unit_id
        and f.kind in {"nonFraction", "fraction"}
    )
    locators = tuple(f.locator for f in candidates)
    if not candidates:
        return FilingSelection("missing", None, None, (), "No exact source fact")
    contexts = tuple(c for c in extraction.contexts if c.id == context_id)
    expected = tuple(sorted(expected_dimensions, key=lambda d: (d.axis, d.member, d.location)))
    if len(contexts) != 1 or not contexts[0].valid or contexts[0].dimensions != expected:
        return FilingSelection("unsupported", None, None, locators, "Context or scope not reviewed")
    if any(f.status not in {"observed", "source_nil"} for f in candidates):
        return FilingSelection(
            "unsupported", None, None, locators, "Matching evidence is unsupported"
        )
    signatures = {
        (f.status, f.value, f.decimals, f.precision, f.scale, f.sign, f.format_qname)
        for f in candidates
    }
    if len(signatures) != 1:
        return FilingSelection(
            "ambiguous", None, None, locators, "Conflicting repeated source facts"
        )
    first = candidates[0]
    status: SelectionStatus = "source_nil" if first.status == "source_nil" else "observed"
    return FilingSelection(
        status,
        first.value,
        first,
        locators,
        "Exact reviewed evidence; all matching repetitions retained",
    )
