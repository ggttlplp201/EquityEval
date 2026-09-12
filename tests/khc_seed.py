"""Pinned KHC facts with hand-reviewed filing/event annotations for PIT tests.

This is not a production SEC normalizer. The raw Company Facts rows and source
hash are verified independently by tests/golden/test_khc_source.py.
"""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from psycopg.types.json import Jsonb

from tests.evidence_seed import insert, publish


def seed_khc(connection):
    with connection.transaction():
        return _seed_khc(connection)


def _seed_khc(connection):
    fixture = json.loads((Path(__file__).parent / "golden/khc_restatement.json").read_text())
    ids = {
        key: uuid4()
        for key in (
            "source capture issuer security unit period parent_scope "
            "consolidated_scope mapping batch"
        ).split()
    }
    now = datetime.fromisoformat(fixture["capture_time"])
    insert(
        connection,
        "sources",
        id=ids["source"],
        source_key="sec-companyfacts",
        name="SEC Company Facts",
        base_url="https://data.sec.gov",
        terms_review_reference="S1-SEC-public-filings",
        content_scope="SEC public facts",
    )
    insert(
        connection,
        "source_captures",
        id=ids["capture"],
        source_id=ids["source"],
        source_object_key="companyfacts/0001637459",
        request_url=fixture["source_url"],
        request_params_hash="a" * 64,
        requested_at=now,
        completed_at=now,
        fetched_at=now,
        http_status=200,
        body_sha256=fixture["raw_sha256"],
        blob_key=fixture["archive"],
        byte_count=fixture["raw_bytes"],
        content_type="application/json",
        terms_review_reference="S1-SEC-public-filings",
    )
    insert(
        connection,
        "issuers",
        id=ids["issuer"],
        cik="0001637459",
        legal_name="Kraft Heinz",
        first_seen_at=now,
    )
    insert(
        connection,
        "securities",
        id=ids["security"],
        issuer_id=ids["issuer"],
        instrument_kind="common",
        share_class_label="common",
        active=True,
    )
    insert(
        connection,
        "units",
        id=ids["unit"],
        unit_key="USD",
        numerator_measures=["iso4217:USD"],
        denominator_measures=[],
    )
    insert(
        connection,
        "periods",
        id=ids["period"],
        period_kind="duration",
        start_date="2017-01-01",
        end_date="2017-12-30",
    )
    for key, kind in [("parent_scope", "parent"), ("consolidated_scope", "consolidated")]:
        insert(
            connection,
            "semantic_scopes",
            id=ids[key],
            issuer_id=ids["issuer"],
            scope_kind=kind,
            descriptor_schema_version=1,
            descriptor_json=Jsonb({"ownership": kind, "evidence": "S1 KHC raw-row audit"}),
            content_sha256=str(ids[key]).replace("-", "") * 2,
        )
    insert(
        connection,
        "mapping_revisions",
        id=ids["mapping"],
        revision_key="khc-hand-reviewed-v1",
        content_sha256="d" * 64,
        code_revision="S1-5746e7d",
        approved_at=now,
        approved_by="S1/S2 review",
        reviewed_scope="KHC FY2017 parent and consolidated income only",
    )
    insert(
        connection,
        "normalization_batches",
        id=ids["batch"],
        issuer_id=ids["issuer"],
        mapping_revision_id=ids["mapping"],
        normalizer_revision="khc-fixture-v1",
        source_authority_policy_revision="periodic-v1",
        created_at=now,
        state="building",
    )
    insert(
        connection,
        "normalization_inputs",
        batch_id=ids["batch"],
        source_capture_id=ids["capture"],
        role="financial_payload",
    )
    filings = {}
    for item in fixture["observations"]:
        row = item["row"]
        if row["accn"] not in filings:
            filing, version = uuid4(), uuid4()
            filings[row["accn"]] = (filing, version)
            insert(connection, "filings", id=filing, issuer_id=ids["issuer"], accession=row["accn"])
            insert(
                connection,
                "filing_versions",
                id=version,
                filing_id=filing,
                metadata_capture_id=ids["capture"],
                filed_date=row["filed"],
                form=row["form"],
                report_period_end=row["end"],
                source_url="https://www.sec.gov/Archives/edgar/data/1637459/"
                + row["accn"].replace("-", ""),
                metadata_hash="b" * 64,
            )
        filing, version = filings[row["accn"]]
        scope = ids["parent_scope"] if item["tag"] == "NetIncomeLoss" else ids["consolidated_scope"]
        concept = (
            "net_income_parent" if item["tag"] == "NetIncomeLoss" else "net_income_consolidated"
        )
        coverage, observation, resolution = uuid4(), uuid4(), uuid4()
        insert(
            connection,
            "statement_coverage",
            id=coverage,
            batch_id=ids["batch"],
            filing_version_id=version,
            period_id=ids["period"],
            statement_family="income",
            period_label="annual",
            reporting_basis="us_gaap",
            scope_id=scope,
            currency_unit_id=ids["unit"],
            authority_class="periodic_complete",
            assurance="audited",
            coverage_state="covered",
            evidence_locator=item["locator"],
        )
        insert(
            connection,
            "source_observations",
            id=observation,
            source_capture_id=ids["capture"],
            filing_version_id=version,
            source_locator=item["locator"],
            namespace="us-gaap",
            tag=item["tag"],
            period_id=ids["period"],
            unit_id=ids["unit"],
            semantic_scope_id=scope,
            numeric_value=Decimal(str(row["val"])),
            value_state="numeric",
            original_numeric_text=str(row["val"]),
            context_knowledge="unknown",
            parser_revision="khc-fixture-v1",
            transform_metadata=Jsonb([]),
            raw_metadata=Jsonb(row),
        )
        insert(
            connection,
            "fact_resolutions",
            id=resolution,
            coverage_id=coverage,
            concept_std=concept,
            semantic_scope_id=scope,
            unit_id=ids["unit"],
            status="observed",
            selected_observation_id=observation,
        )
    # A cited, manually reviewed public-event annotation, not a generated monetary fact.
    event = fixture["non_reliance"]
    filing, version, event_id = uuid4(), uuid4(), uuid4()
    insert(connection, "filings", id=filing, issuer_id=ids["issuer"], accession=event["accession"])
    insert(
        connection,
        "filing_versions",
        id=version,
        filing_id=filing,
        metadata_capture_id=ids["capture"],
        filed_date=event["announced_date"],
        form="8-K",
        source_url=event["source_url"],
        metadata_hash="e" * 64,
    )
    insert(
        connection,
        "filing_events",
        id=event_id,
        issuer_id=ids["issuer"],
        event_kind="non_reliance",
        announced_date=event["announced_date"],
        effective_date=event["determined_date"],
        source_filing_version_id=version,
        evidence_locator="docs/research/s1/restatement-khc.md",
        description="Hand-reviewed public non-reliance annotation",
    )
    insert(
        connection,
        "filing_event_scopes",
        event_id=event_id,
        filing_id=filings[event["affected_accession"]][0],
        period_id=ids["period"],
    )
    ids["non_reliance_event"] = event_id
    publish(connection, ids["batch"])
    return ids
