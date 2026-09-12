"""Owner-only reviewed archive metadata setup for disposable normalization tests."""

import json
from pathlib import Path
from uuid import uuid4

from equity_ingest.financial_types import content_hash

from tests.evidence_seed import insert

ROOT = Path(__file__).resolve().parents[1]


def seed_normalization_inputs(db_admin, inputs):
    evidence = ROOT / "docs/research/s1/evidence"
    entries = []
    for filename in ("manifest.json", "filing-manifest.json"):
        entries.extend(json.loads((evidence / filename).read_text())["requests"])
    blobs = {item["raw_sha256"]: item["raw_file"] for item in entries if "raw_sha256" in item}
    with db_admin.transaction():
        if not db_admin.execute(
            "SELECT 1 FROM issuers WHERE id=%s", (inputs.issuer_id,)
        ).fetchone():
            insert(
                db_admin,
                "issuers",
                id=inputs.issuer_id,
                cik=inputs.cik,
                legal_name="Pinned SEC cohort fixture",
                first_seen_at=inputs.captured_before,
            )
        for scope in {request.scope.id: request.scope for request in inputs.requests}.values():
            if (
                scope.instrument_id is not None
                and not db_admin.execute(
                    "SELECT 1 FROM securities WHERE id=%s", (scope.instrument_id,)
                ).fetchone()
            ):
                insert(
                    db_admin,
                    "securities",
                    id=scope.instrument_id,
                    issuer_id=inputs.issuer_id,
                    instrument_kind=scope.scope_kind,
                    share_class_label=scope.scope_kind,
                )
        for capture in inputs.captures:
            if not db_admin.execute(
                "SELECT 1 FROM sources WHERE id=%s", (capture.source_id,)
            ).fetchone():
                insert(
                    db_admin,
                    "sources",
                    id=capture.source_id,
                    source_key=str(capture.source_id),
                    name="Reviewed SEC archive fixture",
                    base_url="https://data.sec.gov",
                    terms_review_reference="S1-SEC-public-filings",
                    content_scope="SEC public filings",
                )
            if not db_admin.execute(
                "SELECT 1 FROM source_captures WHERE id=%s", (capture.id,)
            ).fetchone():
                insert(
                    db_admin,
                    "source_captures",
                    id=capture.id,
                    source_id=capture.source_id,
                    source_object_key=capture.source_object_key,
                    request_url=capture.request_url,
                    request_params_hash="a" * 64,
                    requested_at=capture.fetched_at,
                    completed_at=capture.completed_at,
                    fetched_at=capture.fetched_at,
                    http_status=200,
                    body_sha256=capture.body_sha256,
                    blob_key="docs/research/s1/evidence/" + blobs[capture.body_sha256],
                    byte_count=capture.byte_count,
                    content_type="application/json",
                    terms_review_reference="S1-SEC-public-filings",
                )
        insert(
            db_admin,
            "mapping_revisions",
            id=inputs.mapping_revision_id,
            revision_key="S3-reviewed-fixture-" + str(uuid4()),
            content_sha256=content_hash(inputs.rules),
            code_revision=inputs.normalizer_revision,
            approved_at=inputs.captured_before,
            approved_by="S1 reviewed evidence / S3 implementation review",
            reviewed_scope="Pinned cohort anchor only; no other issuer or era",
        )
