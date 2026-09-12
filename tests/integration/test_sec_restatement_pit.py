"""Real KHC archive -> normalization -> publication -> S2 historical selection.

The four financial rows are the already reviewed S1 CompanyFacts observations.
The May 2019 non-reliance event is a separately archived TEST-ONLY annotation of
S1's reviewed dates/link, not an extracted SEC 8-K: its raw filing is not pinned.
Inventory/event completeness deliberately stays unknown throughout these tests.
"""

import json
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from equity_ingest.archive import LocalArchive
from equity_ingest.financial_types import (
    EvidenceCapture,
    canonical_json,
    content_hash,
    evidence_id,
)
from equity_ingest.publisher import publish_bundle
from equity_ingest.sec_normalize import (
    normalize_verified_bytes,
    period_spec,
    reviewed_cohort_rules,
)
from equity_schema.concepts import Concept
from equity_schema.pit import HistoryMode, PitQuery, read_statement, read_statements

from tests.evidence_seed import insert
from tests.normalization_db_seed import seed_normalization_inputs
from tests.sec_normalization_seed import cohort_input

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = "0001637459-18-000015"
REVISED = "0001637459-19-000049"
CONCEPTS = (Concept.NET_INCOME_PARENT, Concept.NET_INCOME_CONSOLIDATED)


def _reviewed_inputs():
    body, inputs = cohort_input("KHC")
    period = period_spec(date(2017, 1, 1), date(2017, 12, 30))
    filings, requests = [], []
    for accession, filed, report_end in (
        (ORIGINAL, date(2018, 2, 16), period.end_date),
        (REVISED, date(2019, 6, 7), date(2018, 12, 29)),
    ):
        source_url = (
            f"https://www.sec.gov/Archives/edgar/data/1637459/"
            f"{accession.replace('-', '')}/{accession}-index.htm"
        )
        filing = replace(
            inputs.filings[0],
            id=evidence_id("test-restatement-version", accession),
            filing_id=evidence_id("test-filing", accession),
            accession=accession,
            filed_date=filed,
            report_period_end=report_end,
            source_url=source_url,
            metadata_hash=content_hash([accession, filed, report_end, source_url]),
        )
        filings.append(filing)
        for concept in CONCEPTS:
            template = next(request for request in inputs.requests if concept in request.concepts)
            requests.append(
                replace(
                    template,
                    id=evidence_id("test-restatement-request", [accession, concept]),
                    filing_version_id=filing.id,
                    period=period,
                    concepts=(concept,),
                    evidence_locator="docs/research/s1/restatement-khc.md",
                )
            )
    return body, replace(
        inputs,
        filings=tuple(filings),
        requests=tuple(requests),
        rules=reviewed_cohort_rules(inputs.cik, tuple(filings), tuple(requests)),
    )


def _test_only_event(db_admin, inputs, fixture, tmp_path):
    """Pin the test annotation itself; never mislabel CompanyFacts as 8-K bytes."""
    event = fixture["non_reliance"]
    source_id, capture_id, filing_id, version_id, event_id = (uuid4() for _ in range(5))
    annotation = canonical_json(
        {
            "kind": "TEST-ONLY manually reviewed public-event annotation",
            "limitation": "SEC 8-K body not archived; not production event extraction",
            "review_reference": "docs/research/s1/restatement-khc.md",
            "event": event,
        }
    ).encode()
    captured_at = max(capture.completed_at for capture in inputs.captures)
    source_url = "https://example.invalid/test-only/khc-non-reliance-annotation"
    archive = LocalArchive(tmp_path / "test-event-archive")
    archived = archive.write(
        [annotation],
        source_key="test-only-event-annotation",
        source_object_key=event["accession"],
        params_hash=content_hash(event),
        capture_id=capture_id,
        retrieved_at=captured_at,
        max_bytes=4096,
    )
    assert (
        archive.read_blob(archived.blob_key, archived.body_sha256, archived.byte_count)
        == annotation
    )
    with db_admin.transaction():
        insert(
            db_admin,
            "sources",
            id=source_id,
            source_key="test-only-event-annotation",
            name="TEST-ONLY KHC public-event annotation",
            base_url="https://example.invalid",
            terms_review_reference="test-only-no-sec-event-body",
            content_scope="Synthetic test annotation, not raw SEC event evidence",
        )
        insert(
            db_admin,
            "source_captures",
            id=capture_id,
            source_id=source_id,
            source_object_key=event["accession"],
            request_url=source_url,
            request_params_hash=content_hash(event),
            requested_at=captured_at,
            fetched_at=captured_at,
            completed_at=captured_at,
            http_status=200,
            body_sha256=archived.body_sha256,
            byte_count=archived.byte_count,
            blob_key=archived.blob_key,
            content_type="application/json",
            terms_review_reference="test-only-no-sec-event-body",
        )
        original = next(filing for filing in inputs.filings if filing.accession == ORIGINAL)
        insert(
            db_admin,
            "filings",
            id=original.filing_id,
            issuer_id=inputs.issuer_id,
            accession=original.accession,
        )
        period = inputs.requests[0].period
        insert(db_admin, "periods", **asdict(period))
        insert(
            db_admin,
            "filings",
            id=filing_id,
            issuer_id=inputs.issuer_id,
            accession=event["accession"],
        )
        insert(
            db_admin,
            "filing_versions",
            id=version_id,
            filing_id=filing_id,
            metadata_capture_id=capture_id,
            filed_date=event["announced_date"],
            form="8-K",
            source_url=event["source_url"],
            metadata_hash=content_hash(event),
        )
        insert(
            db_admin,
            "filing_events",
            id=event_id,
            issuer_id=inputs.issuer_id,
            event_kind="non_reliance",
            announced_date=event["announced_date"],
            effective_date=event["determined_date"],
            source_filing_version_id=version_id,
            evidence_locator="docs/research/s1/restatement-khc.md",
            description="TEST-ONLY manual annotation; SEC 8-K body not archived or extracted",
        )
        insert(
            db_admin,
            "filing_event_scopes",
            event_id=event_id,
            filing_id=original.filing_id,
            period_id=period.id,
        )
    capture = EvidenceCapture(
        capture_id,
        source_id,
        event["accession"],
        source_url,
        archived.body_sha256,
        archived.byte_count,
        captured_at,
        captured_at,
        "test_only_event_annotation",
    )
    return replace(inputs, captures=(*inputs.captures, capture), filing_event_ids=(event_id,))


@pytest.fixture
def published_khc(db_admin, db, tmp_path):
    fixture = json.loads((ROOT / "tests/golden/khc_restatement.json").read_text())
    body, inputs = _reviewed_inputs()
    seed_normalization_inputs(db_admin, inputs)
    inputs = _test_only_event(db_admin, inputs, fixture, tmp_path)
    bundle = normalize_verified_bytes(body, inputs)
    published = publish_bundle(db, bundle)
    coordinates = db.execute(
        "SELECT r.concept_std,c.period_id,c.scope_id,c.currency_unit_id,r.unit_id "
        "FROM fact_resolutions r JOIN statement_coverage c ON c.id=r.coverage_id "
        "WHERE c.batch_id=%s",
        (published.batch_id,),
    ).fetchall()
    by_concept = {row["concept_std"]: row for row in coordinates}

    def query(concept, cutoff, **changes):
        row = by_concept[concept.value]
        return replace(
            PitQuery(
                issuer_id=inputs.issuer_id,
                period_id=row["period_id"],
                scope_id=row["scope_id"],
                unit_id=row["unit_id"],
                reporting_currency_unit_id=row["currency_unit_id"],
                statement_family="income",
                concepts=(concept,),
                batch_ids=(published.batch_id,),
                capture_ids=published.capture_ids,
                filing_event_ids=published.filing_event_ids,
                mapping_revision_id=inputs.mapping_revision_id,
                normalizer_revision=inputs.normalizer_revision,
                authority_policy_revision=inputs.authority_policy_revision,
                captured_before=inputs.captured_before,
                mode=changes.pop("mode", HistoryMode.AS_FILED_BY_DATE),
                filed_cutoff=cutoff,
                original_history_complete=published.original_history_complete,
            ),
            **changes,
        )

    return fixture, inputs, bundle, published, query


@pytest.mark.parametrize(
    "cutoff,accession,values",
    [
        (date(2018, 2, 16), ORIGINAL, ("10999000000", "10990000000")),
        (date(2019, 6, 6), ORIGINAL, ("10999000000", "10990000000")),
        (date(2019, 6, 7), REVISED, ("10941000000", "10932000000")),
    ],
)
def test_real_archive_editions_preserve_parent_and_consolidated(
    db, published_khc, cutoff, accession, values
):
    fixture, inputs, _, _, query = published_khc
    result = read_statements(db, tuple(query(concept, cutoff) for concept in CONCEPTS))
    assert not result.flags
    assert tuple(s.facts[0].value for s in result.statements) == tuple(map(Decimal, values))
    assert {s.facts[0].accession for s in result.statements} == {accession}
    assert result.statements[0].query.scope_id != result.statements[1].query.scope_id
    for selected in result.statements:
        fact = selected.facts[0]
        expected = next(
            item
            for item in fixture["observations"]
            if item["row"]["accn"] == accession and item["locator"] == fact.source_locator
        )
        assert fact.value == Decimal(expected["row"]["val"])
        assert fact.source_url == fixture["source_url"]
        assert fixture["raw_sha256"] in fact.source_hashes
        assert inputs.companyfacts_capture_id in fact.capture_ids
        assert fact.original_numeric_text == str(expected["row"]["val"])
        assert "blocking_quality_flag" in selected.flags
        assert not selected.usable_for_valuation  # Historical completeness remains unknown.


def test_public_event_cutoff_is_inclusive_and_does_not_use_private_date(db, published_khc):
    _, inputs, _, _, query = published_khc
    for concept in CONCEPTS:
        before_filing = read_statement(db, query(concept, date(2018, 2, 15)))
        assert before_filing.facts[0].value is None
        assert "coverage_unavailable" in before_filing.flags
        for cutoff in (date(2019, 5, 2), date(2019, 5, 5)):
            selected = read_statement(db, query(concept, cutoff))
            assert "non_reliance" not in selected.flags
            assert not selected.event_ids
        announced = read_statement(db, query(concept, date(2019, 5, 6)))
        assert announced.facts[0].accession == ORIGINAL
        assert "non_reliance" in announced.flags
        assert announced.event_ids == inputs.filing_event_ids
        assert not announced.usable_for_valuation


def test_original_and_latest_views_keep_non_reliance_on_affected_edition(db, published_khc):
    _, inputs, bundle, published, query = published_khc
    assert {flag.rule_key for flag in bundle.quality_flags} == {
        "inventory_history_incomplete",
        "event_history_incomplete",
    }
    assert not published.original_history_complete
    assert inputs.inventory_completeness.state == inputs.event_completeness.state == "unknown"
    for concept, original_value, revised_value in zip(
        CONCEPTS, ("10999000000", "10990000000"), ("10941000000", "10932000000"), strict=True
    ):
        original = read_statement(
            db, query(concept, date(2019, 6, 8), mode=HistoryMode.ORIGINAL_AS_FILED)
        )
        latest = read_statement(db, query(concept, None, mode=HistoryMode.LATEST_REPORTED))
        assert original.facts[0].value == Decimal(original_value)
        assert original.facts[0].accession == ORIGINAL
        assert {"earliest_available", "non_reliance"} <= set(original.flags)
        assert latest.facts[0].value == Decimal(revised_value)
        assert latest.facts[0].accession == REVISED
        assert "revised_view" in latest.flags
        assert "non_reliance" not in latest.flags
        assert not latest.event_ids
        assert "blocking_quality_flag" in original.flags
        assert "blocking_quality_flag" in latest.flags
        assert not original.usable_for_valuation and not latest.usable_for_valuation


def test_current_archive_cannot_claim_2018_retrieval_vintage(db, published_khc):
    _, _, _, _, query = published_khc
    for concept in CONCEPTS:
        selected = read_statement(
            db, query(concept, date(2018, 2, 17), captured_before=datetime(2018, 2, 17, tzinfo=UTC))
        )
        assert selected.facts[0].value is None
        assert "capture_unavailable" in selected.flags
        assert not selected.usable_for_valuation


def test_publication_replay_preserves_both_editions_and_pit_hash(db, published_khc):
    _, _, bundle, published, query = published_khc
    original_query = query(Concept.NET_INCOME_PARENT, date(2018, 2, 16))
    before = read_statement(db, original_query)
    replay = publish_bundle(db, bundle)
    after = read_statement(db, original_query)
    revised = read_statement(db, query(Concept.NET_INCOME_PARENT, date(2019, 6, 7)))
    assert replay.reused and replay.batch_id == published.batch_id
    assert before == after
    assert before.input_hash != revised.input_hash
    assert db.execute("SELECT count(*) AS n FROM normalization_batches").fetchone()["n"] == 1
    assert db.execute("SELECT count(*) AS n FROM fact_resolutions").fetchone()["n"] == 4
