"""Small explicitly fictional evidence graph for storage tests; never a market fixture."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from psycopg import Connection, sql
from psycopg.types.json import Jsonb


def insert(connection: Connection[Any], table: str, **values: Any) -> None:
    """Owner-only fictional fixture insertion, with S3 policy provenance when present."""
    if (
        table == "source_captures"
        and connection.execute(
            "SELECT to_regclass('public.capture_policy_links') AS table_name"
        ).fetchone()["table_name"]
    ):
        with connection.transaction():
            policy = connection.execute(
                "SELECT id FROM source_policy_revisions WHERE source_id=%s AND review_key=%s",
                (values["source_id"], values["terms_review_reference"]),
            ).fetchone()
            policy_id = policy["id"] if policy else uuid4()
            if policy is None:
                _insert_record(
                    connection,
                    "source_policy_revisions",
                    id=policy_id,
                    source_id=values["source_id"],
                    review_key=values["terms_review_reference"],
                    licence_label="Fictional test evidence only",
                    content_scope="Fixture",
                    redistribution_status="unknown",
                    permitted_use="Automated tests only",
                    attribution_requirements="Not a production source-policy review",
                    terms_urls=["https://example.invalid/test-policy"],
                    reviewed_at=values["requested_at"],
                    reviewed_by="test-fixture",
                    review_artifact_reference="tests/evidence_seed.py",
                    review_artifact_sha256="a" * 64,
                )
            _insert_record(connection, table, **values)
            _insert_record(
                connection,
                "capture_policy_links",
                capture_id=values["id"],
                policy_revision_id=policy_id,
            )
        return
    _insert_record(connection, table, **values)


def _insert_record(connection: Connection[Any], table: str, **values: Any) -> None:
    """Compose identifiers and bind values without SQL interpolation."""
    connection.execute(
        sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, values)),
            sql.SQL(", ").join(sql.Placeholder() for _ in values),
        ),
        list(values.values()),
    )


def publish(connection: Connection[Any], batch: UUID, *, output_hash: str = "b" * 64) -> None:
    connection.execute(
        "UPDATE normalization_batches SET state='published', published_at=now(), "
        "input_manifest_hash=%s, output_manifest_hash=%s WHERE id=%s",
        (str(batch).replace("-", "") * 2, output_hash, batch),
    )


def seed_evidence(
    connection: Connection[Any],
    *,
    value: Decimal = Decimal("100"),
    status: str = "observed",
    publish_batch: bool = False,
    issuer_id: UUID | None = None,
    security_id: UUID | None = None,
    period_id: UUID | None = None,
    scope_id: UUID | None = None,
    unit_id: UUID | None = None,
    mapping_id: UUID | None = None,
    filed_date: str = "2025-02-01",
    accession: str | None = None,
    concept: str = "revenue",
    captured_at: str = "2026-09-12T00:00:00Z",
    source_object_key: str | None = None,
    start_date: str | None = "2024-01-01",
    end_date: str = "2024-12-31",
    statement_family: str = "income",
    scope_kind: str = "consolidated",
    descriptor: dict[str, Any] | None = None,
    unit_key: str = "USD",
    namespace: str = "us-gaap",
    tag: str = "Revenues",
    authority_class: str = "periodic_complete",
    assurance: str = "audited",
    reporting_basis: str = "us_gaap",
    form: str = "10-K",
    coverage_state: str = "covered",
    acceptance_at: datetime | None = None,
    acceptance_time_basis: str | None = None,
) -> dict[str, UUID]:
    names = (
        "source capture issuer security quote unit period scope mapping batch filing "
        "filing_version coverage observation resolution flag"
    ).split()
    ids = {name: uuid4() for name in names}
    now = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    insert(
        connection,
        "sources",
        id=ids["source"],
        source_key=str(ids["source"]),
        name="Fictional test source",
        base_url="https://example.invalid",
        terms_review_reference="test-only",
        content_scope="test fixture",
    )
    insert(
        connection,
        "source_captures",
        id=ids["capture"],
        source_id=ids["source"],
        source_object_key=source_object_key or str(ids["issuer"]),
        request_url="https://example.invalid/fixture",
        request_params_hash="a" * 64,
        requested_at=now,
        completed_at=now,
        fetched_at=now,
        http_status=200,
        body_sha256="a" * 64,
        blob_key="test-only/fixture.json.gz",
        byte_count=1,
        content_type="application/json",
        terms_review_reference="test-only",
    )
    if issuer_id is None:
        insert(
            connection,
            "issuers",
            id=ids["issuer"],
            legal_name="Fictional issuer",
            first_seen_at=now,
        )
    else:
        ids["issuer"] = issuer_id
    if security_id is None:
        insert(
            connection,
            "securities",
            id=ids["security"],
            issuer_id=ids["issuer"],
            instrument_kind="common",
            share_class_label="ordinary",
            active=True,
        )
    else:
        ids["security"] = security_id
    insert(
        connection,
        "security_identifiers",
        id=ids["quote"],
        security_id=ids["security"],
        symbol=str(ids["quote"]),
        exchange_code="TEST",
        quote_currency="USD",
        valid_from="2020-01-01",
        source_capture_id=ids["capture"],
    )
    if unit_id is None:
        existing = connection.execute(
            "SELECT id FROM units WHERE unit_key=%s", (unit_key,)
        ).fetchone()
        if existing:
            ids["unit"] = existing["id"]
        else:
            insert(
                connection,
                "units",
                id=ids["unit"],
                unit_key=unit_key,
                numerator_measures=["iso4217:" + unit_key],
                denominator_measures=[],
            )
    else:
        ids["unit"] = unit_id
    if period_id is None:
        kind = "duration" if start_date else "instant"
        existing = connection.execute(
            "SELECT id FROM periods WHERE period_kind=%s AND start_date IS NOT DISTINCT FROM %s "
            "AND end_date=%s",
            (kind, start_date, end_date),
        ).fetchone()
        if existing:
            ids["period"] = existing["id"]
        else:
            insert(
                connection,
                "periods",
                id=ids["period"],
                period_kind=kind,
                start_date=start_date,
                end_date=end_date,
            )
    else:
        ids["period"] = period_id
    if scope_id is None:
        insert(
            connection,
            "semantic_scopes",
            id=ids["scope"],
            issuer_id=ids["issuer"],
            scope_kind=scope_kind,
            descriptor_schema_version=1,
            descriptor_json=Jsonb(descriptor or {"ownership": scope_kind, "dimensions": {}}),
            content_sha256=str(ids["scope"]).replace("-", "") * 2,
        )
    else:
        ids["scope"] = scope_id
    if mapping_id is None:
        insert(
            connection,
            "mapping_revisions",
            id=ids["mapping"],
            revision_key=str(ids["mapping"]),
            content_sha256=str(ids["mapping"]).replace("-", "") * 2,
            code_revision="test-only",
            approved_at=now,
            approved_by="test-reviewer",
            reviewed_scope="Fictional storage fixture",
        )
    else:
        ids["mapping"] = mapping_id
    insert(
        connection,
        "normalization_batches",
        id=ids["batch"],
        issuer_id=ids["issuer"],
        mapping_revision_id=ids["mapping"],
        normalizer_revision="test-v1",
        source_authority_policy_revision="test-v1",
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
    insert(
        connection,
        "filings",
        id=ids["filing"],
        issuer_id=ids["issuer"],
        accession=accession or str(ids["filing"]),
    )
    insert(
        connection,
        "filing_versions",
        id=ids["filing_version"],
        filing_id=ids["filing"],
        metadata_capture_id=ids["capture"],
        filed_date=filed_date,
        form=form,
        report_period_end=end_date,
        source_url="https://example.invalid/filing",
        metadata_hash="c" * 64,
        acceptance_at=acceptance_at,
        acceptance_time_basis=(acceptance_time_basis or "verified_timezone")
        if acceptance_at
        else None,
    )
    insert(
        connection,
        "statement_coverage",
        id=ids["coverage"],
        batch_id=ids["batch"],
        filing_version_id=ids["filing_version"],
        period_id=ids["period"],
        statement_family=statement_family,
        reporting_basis=reporting_basis,
        scope_id=ids["scope"],
        currency_unit_id=ids["unit"],
        authority_class=authority_class,
        assurance=assurance,
        coverage_state=coverage_state,
        evidence_locator="test:/statement",
    )
    if status in {"observed", "source_nil"}:
        insert(
            connection,
            "source_observations",
            id=ids["observation"],
            source_capture_id=ids["capture"],
            filing_version_id=ids["filing_version"],
            source_locator="test:/value",
            namespace=namespace,
            tag=tag,
            period_id=ids["period"],
            unit_id=ids["unit"],
            semantic_scope_id=ids["scope"],
            numeric_value=value if status == "observed" else None,
            value_state="numeric" if status == "observed" else "source_nil",
            original_numeric_text=str(value) if status == "observed" else None,
            raw_dimensions=Jsonb({}),
            context_knowledge="known_empty",
            parser_revision="test-v1",
            transform_metadata=Jsonb([]),
            raw_metadata=Jsonb({"source_unit": unit_key}),
        )
    insert(
        connection,
        "fact_resolutions",
        id=ids["resolution"],
        coverage_id=ids["coverage"],
        concept_std=concept,
        semantic_scope_id=ids["scope"],
        unit_id=ids["unit"],
        status=status,
        selected_observation_id=ids["observation"]
        if status in {"observed", "source_nil"}
        else None,
        reason=None if status == "observed" else "Test fixture unresolved input",
    )
    if status != "observed":
        insert(
            connection,
            "data_quality_flags",
            id=ids["flag"],
            batch_id=ids["batch"],
            resolution_id=ids["resolution"],
            issuer_id=ids["issuer"],
            period_id=ids["period"],
            rule_key="test.missingness",
            severity="error",
            message="Test missing value",
            evidence_references=Jsonb(["test:/value"]),
            raised_at=now,
        )
    if publish_batch:
        publish(connection, ids["batch"])
    return ids
