"""Reproducible, offline real-source pilot presentation; not a published S6 result.

Reuses immutable S1 archives, the reviewed SEC normalizer and Inline XBRL reader.
No transport, database mutation, invented PIT selection or financial arithmetic.
Amounts are source observations; incomplete history blocks all calculated metrics.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from equity_ingest.archive import LocalArchive
from equity_ingest.filing import extract_inline_filing, select_filing_fact
from equity_ingest.financial_types import (
    Completeness,
    CoverageRequest,
    EvidenceCapture,
    FilingMetadata,
    NormalizationInput,
    ScopeSpec,
    canonical_json,
    content_hash,
    evidence_id,
)
from equity_ingest.sec_normalize import (
    normalize_verified_bytes,
    period_spec,
    reviewed_cohort_rules,
    unit_spec,
)
from equity_schema.concepts import Concept

from scripts.export_company_fundamentals import calendar_window

Row = dict[str, Any]
ROOT = Path(__file__).resolve().parents[1]
REVIEWED_AT = "2026-09-20"
CIKS = {
    "CRCL": "0001876042",
    "MSTR": "0001050446",
    "COIN": "0001679788",
    "HOOD": "0001783879",
    "USAR": "0001970622",
    "MP": "0001801368",
    "GOOGL": "0001652044",
}
ACCESSION = "0001876042-26-000062"
PERIOD = period_spec(date(2025, 1, 1), date(2025, 12, 31))
FILED = date(2026, 3, 9)
CONCEPTS = (
    (Concept.REVENUE, "Total revenue and reserve income", "Revenues"),
    (Concept.OPERATING_INCOME, "Operating income (loss)", "OperatingIncomeLoss"),
)


def load_catalog(root: Path) -> Row:
    result: Row = json.loads(
        (root / "docs/research/seven-company-pilot-identities.json").read_text()
    )
    return result


def _capture(item: Row, role: str, source_object_key: str) -> EvidenceCapture:
    # Legacy S1 manifests lack an independently recorded completion timestamp.
    # This required DTO field is an offline compatibility placeholder only; these
    # references must never be published as genuine application capture rows.
    captured = datetime.fromisoformat(item["fetched_at"])
    return EvidenceCapture(
        evidence_id("pilot-archive-reference", [item["raw_file"], item["raw_sha256"]]),
        evidence_id("pilot-source-reference", "sec"),
        source_object_key,
        item["url"],
        item["raw_sha256"],
        item["raw_bytes"],
        captured,
        captured,
        role,
    )


def _section(heading: str, rows: Row) -> Row:
    return {
        "heading": heading,
        "rows": [{"label": key, "value": str(value)} for key, value in rows.items()],
    }


def build_crcl_observations(root: Path) -> Row:
    evidence = root / "docs/research/s1/evidence"
    companyfacts = next(
        item
        for item in json.loads((evidence / "manifest.json").read_text())["requests"]
        if item["ticker"] == "CRCL" and item["status"] == "archived"
    )
    original = next(
        item
        for item in json.loads((evidence / "filing-manifest.json").read_text())["requests"]
        if item["id"] == "CRCL-filing" and item["status"] == "archived"
    )
    filing_url = (
        "https://www.sec.gov/Archives/edgar/data/1876042/000187604226000062/crcl-20251231.htm"
    )
    if (
        companyfacts["url"] != "https://data.sec.gov/api/xbrl/companyfacts/CIK0001876042.json"
        or original["url"] != filing_url
    ):
        raise ValueError("CRCL source identity changed; review the new archive separately")
    archive = LocalArchive(evidence)
    body = archive.read_blob(
        companyfacts["raw_file"], companyfacts["raw_sha256"], companyfacts["raw_bytes"]
    )
    filing_body = archive.read_blob(
        original["raw_file"], original["raw_sha256"], original["raw_bytes"]
    )
    source = _capture(companyfacts, "financial_facts", "companyfacts:0001876042")
    document = _capture(original, "reviewed_coverage", f"filing:{ACCESSION}")
    issuer = evidence_id("pilot-issuer-reference", CIKS["CRCL"])
    filing = FilingMetadata(
        evidence_id("pilot-filing-version", [ACCESSION, source.body_sha256]),
        evidence_id("pilot-filing", ACCESSION),
        issuer,
        ACCESSION,
        source.id,
        FILED,
        "10-K",
        filing_url,
        content_hash([CIKS["CRCL"], ACCESSION, FILED, PERIOD]),
        PERIOD.end_date,
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
        evidence_id("pilot-scope-reference", [issuer, descriptor]),
        issuer,
        None,
        "consolidated",
        1,
        canonical_json(descriptor),
        content_hash(descriptor),
    )
    request = CoverageRequest(
        evidence_id("pilot-coverage-reference", [filing.id, PERIOD.id, scope.id]),
        filing.id,
        PERIOD,
        scope,
        unit_spec("USD"),
        "income",
        "us_gaap",
        "periodic_complete",
        "audited",
        "covered",
        "docs/research/s1/concept-map.md#CRCL",
        tuple(item[0] for item in CONCEPTS),
        "annual",
    )
    incomplete = Completeness(
        "unknown",
        PERIOD.end_date,
        date.fromisoformat(REVIEWED_AT),
        ("S1 archives do not establish exhaustive filing/non-reliance history",),
    )
    rules = reviewed_cohort_rules(CIKS["CRCL"], (filing,), (request,))
    inputs = NormalizationInput(
        issuer,
        CIKS["CRCL"],
        source.id,
        (source, document),
        (filing,),
        (request,),
        rules,
        evidence_id("pilot-mapping-reference", rules),
        "companyfacts-json-v1",
        "companyfacts-reviewed-v1",
        "sec-reviewed-s1-v1",
        datetime(2026, 9, 20, tzinfo=UTC),
        incomplete,
        incomplete,
    )
    bundle = normalize_verified_bytes(body, inputs)
    extraction = extract_inline_filing(
        filing_body,
        expected_sha256=document.body_sha256,
        expected_byte_count=document.byte_count,
        expected_cik=CIKS["CRCL"],
    )
    observations = {item.id: item for item in bundle.observations}
    resolutions = {item.concept_std: item for item in bundle.resolutions}
    contexts = [item for item in extraction.contexts if item.id == "c-1"]
    units = [item for item in extraction.units if item.id == "usd"]
    context_valid = (
        len(contexts) == 1
        and contexts[0].valid
        and contexts[0].cik == CIKS["CRCL"]
        and contexts[0].period_kind == "duration"
        and contexts[0].start_date == PERIOD.start_date
        and contexts[0].end_date == PERIOD.end_date
        and not contexts[0].dimensions
        and len(units) == 1
        and units[0].valid
        and units[0].numerator_measures == ("{http://www.xbrl.org/2003/iso4217}USD",)
        and not units[0].denominator_measures
    )
    flags = {flag.rule_key for flag in bundle.quality_flags} | {
        "legacy_completion_timestamp_unknown",
        "unpublished_archive_observations",
    }
    details: Row = {}
    amounts = []
    for concept, label, tag in CONCEPTS:
        resolution = resolutions[concept]
        observation = (
            observations.get(resolution.selected_observation_id)
            if resolution.selected_observation_id is not None
            else None
        )
        selected = select_filing_fact(
            extraction,
            qualified_tag=f"{{http://fasb.org/us-gaap/2025}}{tag}",
            context_id="c-1",
            unit_id="usd",
            expected_dimensions=(),
        )
        match = (
            context_valid
            and resolution.status == "observed"
            and observation is not None
            and observation.numeric_value is not None
            and selected.status == "observed"
            and selected.value == observation.numeric_value
            and selected.fact is not None
        )
        if not match:
            flags.add("original_filing_crosscheck_failed")
        value = observation.numeric_value if match and observation else None
        fact = selected.fact
        detail_id = f"real|CRCL|{ACCESSION}|{concept.value}"
        rule = next((item for item in rules if item.concept == concept), None)
        details[detail_id] = {
            "title": label,
            "subtitle": (
                "CRCL · FY2025 · archived reported observation. "
                "Calculation eligibility is blocked; not a current valuation."
            ),
            "sections": [
                _section(
                    "Source identity",
                    {
                        "CIK": CIKS["CRCL"],
                        "Accession": ACCESSION,
                        "Form": "10-K",
                        "Filed date": FILED,
                        "Period": f"{PERIOD.start_date} → {PERIOD.end_date}",
                        "Original filing SHA256": document.body_sha256,
                        "Company Facts SHA256": source.body_sha256,
                        "Original filing bytes": document.byte_count,
                        "Company Facts bytes": source.byte_count,
                        "Capture completion timestamp": (
                            "Unknown in legacy S1 manifests. Offline DTO uses fetched_at only "
                            "as a required-field placeholder; not a recorded completion event."
                        ),
                    },
                ),
                _section(
                    "Exact filing observation",
                    {
                        "Concept": concept.value,
                        "Tag": f"{{http://fasb.org/us-gaap/2025}}{tag}",
                        "Context": "c-1",
                        "Context validation": "Exact period, issuer and empty dimensions"
                        if context_valid
                        else "Failed",
                        "Unit": "usd · iso4217:USD",
                        "Literal": fact.lexical_text if fact else "Unavailable",
                        "Scale": fact.scale if fact else "Unavailable",
                        "Sign": (fact.sign or "positive") if fact else "Unavailable",
                        "Decimals": fact.decimals if fact else "Unavailable",
                        "Value (USD)": format(value, "f") if value is not None else "Unavailable",
                        "Matching filing occurrences": len(selected.candidate_locators),
                        "Filing locators": "\n".join(selected.candidate_locators),
                        "Company Facts locator": observation.source_locator
                        if observation
                        else "Unavailable",
                        "Company Facts numeric token": observation.original_numeric_text
                        if observation
                        else "Unavailable",
                        "Company Facts transform": observation.transform_metadata
                        if observation
                        else "Unavailable",
                        "Cross-check": "Exact value agreement"
                        if match
                        else "Failed; amount withheld",
                        "Whole-document extraction": "Complete"
                        if extraction.complete
                        else "Incomplete",
                        "Extraction issue count": len(extraction.issues),
                        "Extraction coverage note": (
                            "Only these exact supported facts were cross-checked. Other extraction "
                            "issues remain; this is not complete financial-statement coverage."
                        ),
                    },
                ),
                _section(
                    "Mapping, history and eligibility",
                    {
                        "Mapping reference": rule.reference if rule else "Unavailable",
                        "Mapping rationale": rule.rationale if rule else "Unavailable",
                        "Scope": scope.descriptor_json,
                        "Normalizer": inputs.normalizer_revision,
                        "Input manifest SHA256": bundle.input_manifest_hash,
                        "Output manifest SHA256": bundle.output_manifest_hash,
                        "Flags": ", ".join(sorted(flags)),
                        "Publication": "Offline normalization only; no published PIT selection",
                        "Calculation eligibility": "Blocked",
                        "Reason": (
                            "Incomplete filing/non-reliance history. Legacy S1 captures have no "
                            "application capture-policy links; no published PIT result is asserted."
                        ),
                    },
                ),
            ],
            "sources": [
                {
                    "label": "SEC original CRCL 10-K",
                    "url": filing_url,
                    "accession": ACCESSION,
                    "capturedAt": original["fetched_at"],
                    "transform": (
                        "LocalArchive hash/count verification → existing Inline XBRL reader "
                        "→ exact c-1/usd/empty-dimension selection; original sign and scale."
                    ),
                    "licence": "SEC disclosure; bounded research reuse, docs/data-licences.md",
                },
                {
                    "label": "SEC Company Facts archive",
                    "url": source.request_url,
                    "accession": ACCESSION,
                    "capturedAt": companyfacts["fetched_at"],
                    "transform": (
                        "Verified archived bytes → existing reviewed_cohort_rules "
                        "→ normalize_verified_bytes; exact accession/period, no fallback."
                    ),
                    "licence": "SEC disclosure; no new live source activated",
                },
            ],
        }
        amounts.append(
            {
                "id": concept.value,
                "label": label,
                "value": format(value, "f") if value is not None else None,
                "valueLabel": f"${value:,.0f}" if value is not None else "—",
                "period": f"{PERIOD.start_date} → {PERIOD.end_date}",
                "detailId": detail_id,
                "statusLabel": "Observed · calculation eligibility blocked"
                if match
                else "Unavailable · original filing cross-check failed",
            }
        )
    return {
        "observedFiling": {
            "accession": ACCESSION,
            "form": "10-K",
            "periodStart": str(PERIOD.start_date),
            "periodEnd": str(PERIOD.end_date),
            "filed": str(FILED),
            "url": filing_url,
            "capturedAt": original["fetched_at"],
            "companyfactsCapturedAt": companyfacts["fetched_at"],
        },
        "amounts": amounts,
        "details": details,
        "flags": sorted(flags),
    }


def export(root: Path = ROOT) -> Row:
    catalog = load_catalog(root)
    companies = catalog["companies"]
    if catalog["reviewedAt"] != REVIEWED_AT or [
        (row["ticker"], row["cik"]) for row in companies
    ] != list(CIKS.items()):
        raise ValueError("Pilot issuer identity/order differs from the reviewed catalog")
    observed = build_crcl_observations(root)
    output = []
    for company in companies:
        is_crcl = company["ticker"] == "CRCL"
        history = {}
        for years in (3, 5, 10):
            start, end, expected = calendar_window(REVIEWED_AT, years)
            history[str(years)] = {
                "windowStart": str(start),
                "windowEnd": str(end),
                "coverageLabel": f"0 eligible of {len(expected)} completed quarter-end snapshots",
                "note": (
                    "No published, eligible point-in-time company history in this pilot. "
                    "An annual filing observation is not a quarter-end valuation snapshot. "
                    "No percentile, interpolation or sector rank is available."
                ),
            }
        reasons = (
            [
                "Filing inventory and non-reliance event coverage are incomplete.",
                "No published PIT selection is supplied by this archived research artifact.",
            ]
            if is_crcl
            else [
                "Exact filing, period and concept mappings/archives are not yet reviewed.",
                "A dated business/identity reference does not establish numeric eligibility.",
            ]
        )
        metric_specs = [
            ("revenue_yoy", "Revenue growth", ["A reviewed comparable prior period is missing."]),
            (
                "operating_margin",
                "Operating margin",
                [
                    "The reported operating loss is retained; source eligibility remains blocked.",
                    "Business applicability must be reviewed independently of data availability.",
                ]
                if is_crcl
                else [],
            ),
            (
                "fcf_margin",
                "Cash generation",
                ["Comparable CFO and cash PPE purchases are not supplied; no FCFF inference."],
            ),
            (
                "balance_sheet",
                "Balance sheet",
                ["Corporate cash, holder/customer assets and obligations require separate scopes."],
            ),
            (
                "pe",
                "P/E",
                ["Missing quote, earnings/share bridge and action/calendar coverage."],
            ),
            ("ps", "P/S", ["No reviewed common-equity market value for the exact security scope."]),
        ]
        detail_id = observed["amounts"][0]["detailId"] if is_crcl else None
        metrics = [
            {
                "id": key,
                "label": label,
                "value": None,
                "valueLabel": "—",
                "statusLabel": "Unavailable · prerequisites missing",
                "reasons": reasons + additional,
                "detailId": detail_id,
            }
            for key, label, additional in metric_specs
        ]
        output.append(
            {
                **company,
                **({"observedFiling": observed["observedFiling"]} if is_crcl else {}),
                "amounts": observed["amounts"] if is_crcl else [],
                "metrics": metrics,
                "history": history,
            }
        )
    payload: Row = {
        "kind": "real-source-pilot",
        "reviewedAt": REVIEWED_AT,
        "companies": output,
        "details": observed["details"],
    }
    return {**payload, "snapshotId": content_hash(payload)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "apps/web/src/features/pilot/evidence.json"
    body = json.dumps(export(), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.check:
        if target.read_text() != body:
            raise SystemExit("Pilot artifact differs from its pinned source evidence")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)


if __name__ == "__main__":
    main()
