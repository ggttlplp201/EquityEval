"""D049 ten-concept FY2025 preparation; no earlier-period eligibility claim."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import date
from typing import Any

from equity_ingest.financial_types import (
    Completeness,
    CoverageRequest,
    NormalizationBundle,
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

from scripts.normalize_crcl import ACCESSION, ROOT
from scripts.prepare_crcl_observation import prepare as prior_prepare
from scripts.review_crcl_broader import REPORT, SPECS, retained, review

OUTPUT = "docs/research/crcl-broader-preparation-2026-10-15.json"


def prepare() -> tuple[NormalizationBundle, dict[str, Any]]:
    assessed = review()
    if (
        assessed["status"] != "ready_for_fy2025_preparation"
        or assessed["historicalAnalysisEligible"]
    ):
        raise ValueError("Broader review not eligible for exact current-only scope")
    old, _ = prior_prepare()
    inputs = old.inputs
    filing = next(f for f in inputs.filings if f.accession == ACCESSION)
    base_scope = old.scopes[0]
    import json

    descriptor = json.loads(base_scope.descriptor_json)
    descriptor["payment_basis"] = "actual_cash_payment"
    cash_scope = ScopeSpec(
        evidence_id("d5k-cash-payment-scope", [inputs.issuer_id, descriptor]),
        inputs.issuer_id,
        None,
        "consolidated",
        1,
        canonical_json(descriptor),
        content_hash(descriptor),
    )
    requests = []
    for family, scope, concepts in (
        (
            "income",
            base_scope,
            (Concept.OPERATING_INCOME, Concept.REVENUE, Concept.NET_INCOME_CONSOLIDATED),
        ),
        ("cash_flow", base_scope, (Concept.CASH_FROM_OPERATING_ACTIVITIES,)),
        ("cash_flow", cash_scope, (Concept.CAPITAL_EXPENDITURES_PPE,)),
        (
            "balance_sheet",
            base_scope,
            (
                Concept.CURRENT_ASSETS,
                Concept.CURRENT_LIABILITIES,
                Concept.TOTAL_ASSETS,
                Concept.TOTAL_LIABILITIES,
                Concept.EQUITY_INCLUDING_NONCONTROLLING_INTERESTS,
            ),
        ),
    ):
        period = period_spec(
            None if family == "balance_sheet" else date(2025, 1, 1), date(2025, 12, 31)
        )
        requests.append(
            CoverageRequest(
                evidence_id("d5k-coverage", [filing.id, family, scope.id, period.id]),
                filing.id,
                period,
                scope,
                unit_spec("USD"),
                family,
                "us_gaap",
                "periodic_complete",
                "audited",
                "covered",
                REPORT,
                concepts,
                "instant" if family == "balance_sheet" else "annual",
            )
        )
    rules = reviewed_cohort_rules(inputs.cik, inputs.filings, tuple(requests))
    if len(rules) != 10 or {r.concept.value for r in rules} != set(SPECS):
        raise ValueError("Existing reviewed concept map cannot represent exact scope")
    rules = tuple(
        replace(
            r,
            reference="d5k:" + r.reference,
            evidence_references=(*r.evidence_references, REPORT),
            rationale=r.rationale
            + "; D049 verifies exact FY2025 audited source and reserve/cash scope.",
        )
        for r in rules
    )
    completeness = Completeness(
        "complete",
        date(2025, 12, 31),
        inputs.captured_before.date(),
        (
            REPORT,
            "sha256:" + content_hash(assessed),
            "inventory_observed_at:" + inputs.captured_before.isoformat(),
            (
                "Only FY2025 full-year and closing balances; earlier comparative "
                "history remains unproved"
            ),
        ),
    )
    new = replace(
        inputs,
        requests=tuple(requests),
        rules=rules,
        mapping_revision_id=evidence_id("d5k-reviewed-mapping", rules),
        inventory_completeness=completeness,
        event_completeness=completeness,
    )
    _, bodies = retained()
    bundle = normalize_verified_bytes(bodies[str(inputs.companyfacts_capture_id)], new)
    if bundle.quality_flags or len(bundle.resolutions) != 10:
        raise ValueError("Existing normalizer did not prove exact current scope")
    observations = {o.id: o for o in bundle.observations}
    for resolution in bundle.resolutions:
        if (
            resolution.status != "observed"
            or resolution.selected_observation_id not in observations
        ):
            raise ValueError("Unresolved broader operand")
        source = observations[resolution.selected_observation_id]
        proof = assessed["precisionProof"][resolution.concept_std.value]["fact"]
        if source.numeric_value != proof["value"]:
            raise ValueError("Normalized and original inline amount differ")
    return bundle, assessed["precisionProof"]


def generated() -> dict[str, Any]:
    bundle, proof = prepare()
    return {
        "kind": "d5k-broader-normalization-preparation",
        "inputHash": bundle.input_manifest_hash,
        "outputHash": bundle.output_manifest_hash,
        "inputs": asdict(bundle.inputs),
        "bundle": asdict(bundle),
        "sourcePrecision": proof,
        "metricPublication": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = canonical_json(generated()) + "\n"
    p = ROOT / OUTPUT
    if args.check:
        if p.read_text() != text:
            raise ValueError("Broader preparation differs")
    else:
        p.write_text(text)
    print(OUTPUT)


if __name__ == "__main__":
    main()
