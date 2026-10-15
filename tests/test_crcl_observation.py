from datetime import date
from uuid import uuid4

import pytest


def test_current_pair_plan_has_explicit_window_and_no_filing_expansion(monkeypatch):
    from types import SimpleNamespace

    from scripts import capture_crcl_safety as shared

    plans = []

    def enqueue(db, **kwargs):
        plans.append(kwargs["plan"])
        return SimpleNamespace(request_id=uuid4())

    monkeypatch.setattr(shared, "enqueue_source_bootstrap", enqueue)
    monkeypatch.setattr(shared, "claim_source_bootstrap", lambda *a, **kw: None)
    identities = {k: uuid4() for k in ["issuer", "source", "policy", "workspace", "security"]}
    with pytest.raises(ValueError, match="already exists"):
        shared.capture_group(
            None, identities, (), 1, "unused", "unused", inventory_end=date(2026, 10, 15)
        )
    assert plans[0].inventory_end == date(2026, 10, 15)
    assert plans[0].resources == ("company_facts/0001876042", "submissions/0001876042")


def test_missing_or_partial_observation_never_clears_current_eligibility():
    import json

    from scripts import review_crcl_observation as review
    from scripts.normalize_crcl import ROOT

    saved = json.loads((ROOT / review.ACQUISITION).read_text())
    saved["groups"][0]["captures"].pop()
    for acquisition in (None, saved):
        result = review.review_acquisition(acquisition)
        assert result["candidateBatch"]["status"] == "blocked"
        assert result["operatingMargin"] is None


def test_new_preparation_is_current_and_preserves_old_blocked_batch():
    from scripts.normalize_crcl import load_preparation
    from scripts.prepare_crcl_observation import prepare

    new, proof = prepare()
    old, _ = load_preparation()
    assert new.original_history_complete and not new.quality_flags
    assert old.original_history_complete is False and len(old.quality_flags) == 2
    assert new.inputs.mapping_revision_id == old.inputs.mapping_revision_id
    assert new.inputs.captured_before.isoformat() == "2026-10-15T21:59:05.195192+00:00"
    assert all(c.completed_at <= new.inputs.captured_before for c in new.inputs.captures)
    assert set(proof) == {"revenue", "operating_income"}


@pytest.fixture
def fresh_documents():
    import json

    from equity_ingest.archive import LocalArchive

    from scripts.normalize_crcl import RESOURCES, ROOT
    from scripts.review_crcl_observation import ACQUISITION

    audit = json.loads((ROOT / ACQUISITION).read_text())
    captures = {c["source_object_key"]: c for c in audit["groups"][0]["captures"]}
    archive = LocalArchive(ROOT / "var/raw")
    documents = {
        k: json.loads(archive.read_blob(c["blob_key"], c["body_sha256"], c["byte_count"]))
        for k, c in captures.items()
    }
    return documents[RESOURCES[0]], documents[RESOURCES[1]], captures[RESOURCES[1]]


@pytest.mark.parametrize("mutation", ["metadata", "value", "edition", "unit", "acceptance"])
def test_plausible_changes_require_fresh_review(fresh_documents, mutation):
    import copy
    from datetime import datetime
    from uuid import UUID

    from scripts.review_crcl_observation import compare_documents, metadata_rows

    facts, inventory, capture = fresh_documents
    old = copy.deepcopy(inventory)
    if mutation in {"metadata", "acceptance"}:
        accession = next(iter(metadata_rows(inventory)))
        index = inventory["filings"]["recent"]["accessionNumber"].index(accession)
        field = "items" if mutation == "metadata" else "acceptanceDateTime"
        inventory["filings"]["recent"][field][index] = (
            "4.02" if mutation == "metadata" else "2026-10-15T23:59:59.000Z"
        )
    else:
        units = facts["facts"]["us-gaap"]["OperatingIncomeLoss"]["units"]
        annual = next(
            r
            for r in units["USD"]
            if r.get("start") == "2025-01-01" and r.get("end") == "2025-12-31"
        )
        if mutation == "value":
            annual["val"] = 96435000
        elif mutation == "edition":
            annual["accn"] = "0001876042-26-999999"
        else:
            units["EUR"] = units.pop("USD")
    result = compare_documents(
        facts,
        inventory,
        old,
        datetime.fromisoformat(capture["completed_at"]),
        UUID(capture["capture_id"]),
    )
    assert not result["matched"]


def test_pair_timing_and_duplicate_scope_fail_closed():
    import copy
    import json

    from scripts import review_crcl_observation as review
    from scripts.normalize_crcl import ROOT

    saved = json.loads((ROOT / review.ACQUISITION).read_text())
    changed = copy.deepcopy(saved)
    changed["groups"][0]["captures"][0]["completed_at"] = "2026-10-15T22:00:00+00:00"
    assert (
        "facts_retrieved_after_inventory_observation"
        in review.review_acquisition(changed)["candidateBatch"]["reasonCodes"]
    )
    changed = copy.deepcopy(saved)
    changed["groups"][0]["captures"].append(changed["groups"][0]["captures"][0])
    with pytest.raises(ValueError):
        review.review_acquisition(changed)


def test_unavailable_runtime_records_blocked_audit(tmp_path, monkeypatch):
    import json

    from scripts import capture_crcl_observation as capture

    monkeypatch.setattr(capture, "ROOT", tmp_path)
    (tmp_path / "docs/research").mkdir(parents=True)

    def unavailable():
        raise RuntimeError("unavailable")

    monkeypatch.setattr(capture, "verify_previous", unavailable)
    capture.capture()
    report = json.loads((tmp_path / capture.ACQUISITION).read_text())
    assert report["status"] == "blocked" and report["originalRowsPreserved"] is None
    with pytest.raises(ValueError):
        capture.capture()


def test_historical_metadata_rebinding_is_explicit_and_source_pinned():
    from scripts.review_crcl_observation import review

    result = review()
    metadata = result["metadataRebinding"]
    assert metadata["status"] == "reviewed_source_vintage_difference"
    assert len(metadata["rows"]) == 3
    assert all(set(r["changedFields"]) == {"acceptanceDateTime"} for r in metadata["rows"])
    assert all(r["oldCaptureId"] != r["newCaptureId"] for r in metadata["rows"])
    assert "cause" in metadata["limit"]


def test_new_versions_store_fresh_acceptance_and_metadata_hash(fresh_documents):
    import json
    from datetime import datetime
    from uuid import UUID

    from equity_ingest.financial_types import content_hash
    from equity_ingest.sec_inventory import parse_submissions

    from scripts.prepare_crcl_observation import prepare

    _, inventory, capture = fresh_documents
    parsed = parse_submissions(
        json.dumps(inventory).encode(),
        expected_cik="0001876042",
        capture_id=UUID(capture["capture_id"]),
    )
    bundle, _ = prepare()
    for filing in bundle.inputs.filings:
        row = next(f for f in parsed.filings if f.accession == filing.accession)
        assert filing.metadata_capture_id == UUID(capture["capture_id"])
        assert filing.acceptance_at == row.acceptance_at
        assert filing.metadata_hash == content_hash(row.raw_metadata)
        assert filing.acceptance_at < datetime.fromisoformat(capture["completed_at"])


def test_projection_rejects_changed_preparation_and_unreviewed_publication():
    import copy
    import json

    from scripts.export_crcl_observation import project
    from scripts.normalize_crcl import ROOT
    from scripts.prepare_crcl_observation import OUTPUT
    from scripts.review_crcl_observation import REPORT

    review = json.loads((ROOT / REPORT).read_text())
    prep = json.loads((ROOT / OUTPUT).read_text())
    result = project(review, prep, None)
    assert result["operatingMargin"] is None and result["facts"] == []
    changed = copy.deepcopy(prep)
    changed["inputHash"] = "0" * 64
    with pytest.raises(ValueError):
        project(review, changed, None)
    with pytest.raises(ValueError):
        project(review, prep, {"batch": {"id": "invented"}})


def test_published_projection_preserves_operands_and_rejects_forged_audit():
    import copy
    import json

    from scripts.export_crcl_observation import project
    from scripts.normalize_crcl import ROOT
    from scripts.prepare_crcl_observation import OUTPUT
    from scripts.publish_crcl_observation import PUBLICATION
    from scripts.review_crcl_observation import REPORT

    review = json.loads((ROOT / REPORT).read_text())
    prep = json.loads((ROOT / OUTPUT).read_text())
    audit = json.loads((ROOT / PUBLICATION).read_text())
    result = project(review, prep, audit)
    assert {f["id"]: f["value"] for f in result["facts"]} == {
        "revenue": "2746642000",
        "operating_income": "-96435000",
    }
    assert result["operatingMargin"] is None
    for field, value in (("priorRowsPreserved", False), ("outputHash", "0" * 64)):
        changed = copy.deepcopy(audit)
        changed[field] = value
        with pytest.raises(ValueError):
            project(review, prep, changed)
