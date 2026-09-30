"""Bounded D5a replay of the five governed D3c captures; no source acquisition."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from equity_ingest.archive import LocalArchive
from equity_ingest.filing import extract_inline_filing, select_filing_fact
from equity_ingest.financial_types import (
    Completeness,
    CoverageRequest,
    EvidenceCapture,
    FilingMetadata,
    NormalizationBundle,
    NormalizationInput,
    ScopeSpec,
    canonical_json,
    content_hash,
    evidence_id,
)
from equity_ingest.sec_inventory import assemble_inventory, parse_submissions
from equity_ingest.sec_normalize import (
    normalize_verified_bytes,
    period_spec,
    reviewed_cohort_rules,
    unit_spec,
)
from equity_schema.concepts import Concept

from scripts.review_crcl_identity import read_audit

ROOT = Path(__file__).resolve().parents[1]
CIK = "0001876042"
ACCESSION = "0001876042-26-000062"
CUTOFF = datetime.fromisoformat("2026-09-21T17:07:36.842185+00:00")
PERIOD = period_spec(date(2025, 1, 1), date(2025, 12, 31))
FILINGS = {
    ACCESSION: (
        "2026-03-09",
        "10-K",
        "2025-12-31",
        "crcl-20251231.htm",
        "2026-03-09T12:36:51+00:00",
    ),
    "0001876042-26-000228": (
        "2026-07-13",
        "10-K/A",
        "2025-12-31",
        "crcl-20251231.htm",
        "2026-07-13T20:40:02+00:00",
    ),
    "0001876042-26-000248": (
        "2026-08-05",
        "10-Q",
        "2026-06-30",
        "crcl-20260630.htm",
        "2026-08-05T13:02:57+00:00",
    ),
}
RESOURCES = (
    f"company_facts/{CIK}",
    f"submissions/{CIK}",
    *(f"filing_document/{CIK}/{accession}/{row[3]}" for accession, row in FILINGS.items()),
)
CONCEPTS = ((Concept.REVENUE, "Revenues"), (Concept.OPERATING_INCOME, "OperatingIncomeLoss"))
REVIEW = "docs/design/d5a/proposal.md"


def resource_url(key: str) -> str:
    if key == RESOURCES[0]:
        return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
    if key == RESOURCES[1]:
        return f"https://data.sec.gov/submissions/CIK{CIK}.json"
    _, cik, accession, filename = key.split("/")
    compact = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{filename}"


def prepare(
    audit: dict[str, Any], archive: LocalArchive
) -> tuple[NormalizationBundle, dict[str, Any]]:
    """Pure archived preparation; production must separately verify the pinned DB lineage."""
    plan = audit["bootstrap_plan"]
    issuer, source = UUID(plan["issuer_id"]), UUID(plan["source_id"])
    rows = audit["captures"]
    if (
        plan["cik"] != CIK
        or len(rows) != 5
        or {row["source_object_key"] for row in rows} != set(RESOURCES)
        or len({row["capture_id"] for row in rows}) != 5
    ):
        raise ValueError("Expected exactly five distinct reviewed CRCL resources")
    indexed = {row["source_object_key"]: row for row in rows}
    captures, bodies = [], {}
    for key, role in zip(
        RESOURCES,
        (
            "financial_facts",
            "filing_inventory",
            "reviewed_coverage",
            "amendment_review",
            "quarterly_review",
        ),
        strict=True,
    ):
        row = indexed[key]
        fetched, completed = (
            datetime.fromisoformat(row["fetched_at"]),
            datetime.fromisoformat(row["completed_at"]),
        )
        if (
            UUID(row["source_id"]) != source
            or row["request_url"] != resource_url(key)
            or row["http_status"] != 200
            or fetched.utcoffset() is None
            or completed.utcoffset() is None
            or not fetched <= completed <= CUTOFF
        ):
            raise ValueError("Capture identity or retrieval time differs from reviewed scope")
        bodies[key] = archive.read_blob(row["blob_key"], row["body_sha256"], row["byte_count"])
        captures.append(
            EvidenceCapture(
                UUID(row["capture_id"]),
                source,
                key,
                row["request_url"],
                row["body_sha256"],
                row["byte_count"],
                fetched,
                completed,
                role,
            )
        )
    recent = parse_submissions(bodies[RESOURCES[1]], expected_cik=CIK, capture_id=captures[1].id)
    inventory = assemble_inventory(
        recent, (), boundary_start=date(2025, 1, 1), boundary_end=CUTOFF.date()
    )
    if inventory.flags:
        raise ValueError("Ambiguous or incomplete advertised inventory requires review")
    filings = []
    for accession, expected in FILINGS.items():
        matches = [item for item in inventory.filings if item.accession == accession]
        if len(matches) != 1:
            raise ValueError("Each reviewed accession requires exactly one metadata row")
        item = matches[0]
        actual = (
            str(item.filed_date),
            item.form,
            str(item.report_period_end),
            item.primary_document,
            item.acceptance_at.isoformat() if item.acceptance_at else None,
        )
        if actual != expected or item.acceptance_time_basis != "verified_timezone":
            raise ValueError("Filing identity, period or acceptance differs from reviewed scope")
        filings.append(
            FilingMetadata(
                evidence_id("d5a-filing-version", [issuer, accession, item.raw_metadata]),
                evidence_id("filing", [issuer, accession]),
                issuer,
                accession,
                captures[1].id,
                item.filed_date,
                item.form,
                resource_url(f"filing_document/{CIK}/{accession}/{item.primary_document}"),
                content_hash(item.raw_metadata),
                item.report_period_end,
                item.acceptance_at,
                item.acceptance_time_basis,
            )
        )
    descriptor = {
        "consolidation": "consolidated",
        "instrument": None,
        "context_knowledge": "unknown",
        "scope_evidence": "docs/research/s1/concept-map.md",
        "cash_scope": "not_applicable",
        "payment_basis": "as_reported",
        "revenue_basis": "reported_complete_scope",
    }
    scope = ScopeSpec(
        evidence_id("d5a-scope", [issuer, descriptor]),
        issuer,
        None,
        "consolidated",
        1,
        canonical_json(descriptor),
        content_hash(descriptor),
    )
    request = CoverageRequest(
        evidence_id("d5a-coverage", [filings[0].id, scope.id]),
        filings[0].id,
        PERIOD,
        scope,
        unit_spec("USD"),
        "income",
        "us_gaap",
        "periodic_complete",
        "audited",
        "covered",
        REVIEW,
        tuple(item[0] for item in CONCEPTS),
        "annual",
    )
    rules = reviewed_cohort_rules(CIK, tuple(filings), (request,))
    if {rule.concept for rule in rules} != {item[0] for item in CONCEPTS} or len(rules) != 2:
        raise ValueError("The existing reviewed mapping does not cover this exact scope")
    incomplete = Completeness("unknown", PERIOD.end_date, CUTOFF.date(), (REVIEW,))
    inputs = NormalizationInput(
        issuer,
        CIK,
        captures[0].id,
        tuple(captures),
        tuple(filings),
        (request,),
        rules,
        evidence_id("d5a-reviewed-mapping", rules),
        "companyfacts-json-v1",
        "companyfacts-reviewed-v1",
        "sec-reviewed-s1-v1",
        CUTOFF,
        incomplete,
        incomplete,
    )
    bundle = normalize_verified_bytes(bodies[RESOURCES[0]], inputs)
    proof = crosscheck(bundle, bodies[RESOURCES[2]], captures[2])
    return bundle, proof


def crosscheck(
    bundle: NormalizationBundle, body: bytes, capture: EvidenceCapture
) -> dict[str, Any]:
    extraction = extract_inline_filing(
        body,
        expected_sha256=capture.body_sha256,
        expected_byte_count=capture.byte_count,
        expected_cik=CIK,
    )
    contexts = [item for item in extraction.contexts if item.id == "c-1"]
    units = [item for item in extraction.units if item.id == "usd"]
    if (
        len(contexts) != 1
        or not contexts[0].valid
        or contexts[0].cik != CIK
        or contexts[0].period_kind != "duration"
        or contexts[0].start_date != PERIOD.start_date
        or contexts[0].end_date != PERIOD.end_date
        or contexts[0].dimensions
        or len(units) != 1
        or not units[0].valid
        or units[0].denominator_measures
        or units[0].numerator_measures != ("{http://www.xbrl.org/2003/iso4217}USD",)
    ):
        raise ValueError("Original filing context, period, dimensions or unit disagrees")
    observations = {item.id: item for item in bundle.observations}
    resolutions = {item.concept_std: item for item in bundle.resolutions}
    proof = {}
    for concept, tag in CONCEPTS:
        selected = select_filing_fact(
            extraction,
            qualified_tag=f"{{http://fasb.org/us-gaap/2025}}{tag}",
            context_id="c-1",
            unit_id="usd",
            expected_dimensions=(),
        )
        resolution = resolutions[concept]
        observation = (
            observations.get(resolution.selected_observation_id)
            if resolution.selected_observation_id
            else None
        )
        if (
            resolution.status != "observed"
            or observation is None
            or observation.numeric_value is None
            or selected.status != "observed"
            or selected.fact is None
            or selected.value != observation.numeric_value
        ):
            raise ValueError("Company Facts and original filing do not agree on a selected value")
        occurrences = [
            fact for fact in extraction.facts if fact.locator in selected.candidate_locators
        ]
        if not occurrences or any(
            fact.scale != 3
            or fact.decimals != "-3"
            or fact.precision is not None
            or fact.sign != selected.fact.sign
            for fact in occurrences
        ):
            raise ValueError("Original filing source precision requires a separate review")
        proof[concept.value] = {
            "capture_id": str(capture.id),
            "fact": asdict(selected.fact),
            "candidate_locators": selected.candidate_locators,
            "context": asdict(contexts[0]),
            "unit": asdict(units[0]),
            "extractor_issue_count": len(extraction.issues),
            "companyfacts_observation": asdict(observation),
        }
    return proof


def load_preparation(root: Path = ROOT) -> tuple[NormalizationBundle, dict[str, Any]]:
    return prepare(read_audit(root), LocalArchive(root / "var/raw"))
