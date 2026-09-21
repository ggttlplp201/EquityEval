"""Offline identity assertions use fictional bodies, never the application stores."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from equity_ingest.archive import ArchiveError, LocalArchive

from scripts import review_crcl_identity as review


def filing(*, listing=True, reporting=True, prefix="dei", namespace="http://xbrl.sec.gov/dei/2025"):
    listing_text = (
        review.LISTING_STATEMENT if listing else "Filed March 9, 2026; period December 31, 2025"
    )
    return (
        f'<html xmlns:ix="{review.IX}" xmlns:{prefix}="{namespace}"><body>'
        f'<ix:nonNumeric name="{prefix}:TradingSymbol">CRCL</ix:nonNumeric>'
        f'<ix:nonNumeric name="{prefix}:SecurityExchangeName">'
        "New York Stock Exchange</ix:nonNumeric>"
        f'<ix:nonNumeric name="{prefix}:Security12bTitle">'
        "Class A common stock, par value $0.0001 per share</ix:nonNumeric>"
        f"<p>{listing_text}</p>"
        f"<p>{review.REPORTING_STATEMENT if reporting else 'Amendment'}</p>"
        "<p>IPO offering price: USD 31.00 per share; follow-on USD 130.00 per share.</p>"
        "</body></html>"
    ).encode()


@pytest.fixture
def captured(tmp_path):
    archive = LocalArchive(tmp_path / "raw")
    bodies = {
        review.SUBMISSIONS: json.dumps(
            {
                "cik": "0001876042",
                "name": "Circle Internet Group, Inc.",
                "tickers": ["CRCL"],
                "exchanges": ["NYSE"],
            }
        ).encode(),
        review.ORIGINAL: filing(),
        "filing_document/0001876042/0001876042-26-000228/crcl-20251231.htm": filing(
            reporting=False
        ),
        "filing_document/0001876042/0001876042-26-000248/crcl-20260630.htm": filing(),
    }
    captures = []
    for key, body in bodies.items():
        capture_id = uuid4()
        stored = archive.write(
            [body],
            source_key="fictional-test",
            source_object_key=key,
            params_hash="0" * 64,
            capture_id=capture_id,
            retrieved_at=datetime(2026, 9, 21, tzinfo=UTC),
            max_bytes=10000,
        )
        captures.append(
            {
                "capture_id": str(capture_id),
                "source_object_key": key,
                "blob_key": stored.blob_key,
                "body_sha256": stored.body_sha256,
                "byte_count": stored.byte_count,
            }
        )
    return {"captures": captures, "request_id": str(uuid4()), "execution_id": str(uuid4())}, archive


def test_reporting_and_offering_dollars_do_not_register_a_quote(captured):
    audit, archive = captured
    result = review.review_bodies(audit, archive)
    assert {key: field["value"] for key, field in result["fields"].items()} == {
        "symbol": "CRCL",
        "exchange_code": "NYSE",
        "share_class": "Class A common stock",
        "valid_from": "2025-06-05",
        "quote_currency": None,
    }
    assert result["blocking_reasons"] == ["quote_currency_unsubstantiated"]
    assert not result["registration_ready"] and not result["ordinary_request_eligible"]
    assert not result["financial_result"]
    assert result == review.review_bodies(audit, archive)
    assert len(result["fields"]["symbol"]["evidence"]) == 4


@pytest.mark.parametrize("field", ["body_sha256", "byte_count"])
def test_corrupt_archive_is_not_reviewable(captured, field):
    audit, archive = captured
    audit["captures"][0][field] = "0" * 64 if field == "body_sha256" else 1
    with pytest.raises(ArchiveError):
        review.review_bodies(audit, archive)


def test_missing_archive_is_not_reviewable(captured):
    audit, archive = captured
    (archive.root / audit["captures"][0]["blob_key"]).unlink()
    with pytest.raises(ArchiveError):
        review.review_bodies(audit, archive)


@pytest.mark.parametrize(
    "old,new",
    [
        (b">CRCL<", b">OTHER<"),
        (b"New York Stock Exchange", b"Other Exchange"),
        (b"Class A common stock", b"Class B common stock"),
        (b"http://xbrl.sec.gov/dei/2025", b"https://example.invalid/dei/2025"),
    ],
)
def test_conflicting_or_forged_cover_is_refused(old, new):
    with pytest.raises(ValueError, match="cover identity"):
        review.cover_evidence(review.xml_root(filing().replace(old, new)), "fixture")


def test_dei_namespace_is_resolved_not_guessed_from_prefix():
    result = review.cover_evidence(review.xml_root(filing(prefix="source")), "fixture")
    assert result["TradingSymbol"]["value"] == "CRCL"


def test_ambiguous_cover_is_refused():
    body = filing().replace(
        b"</body>", b'<ix:nonNumeric name="dei:TradingSymbol">CRCL</ix:nonNumeric></body>'
    )
    with pytest.raises(ValueError, match="ambiguous"):
        review.cover_evidence(review.xml_root(body), "fixture")


def test_filing_and_observation_dates_never_replace_listing_start():
    with pytest.raises(ValueError, match="no date fallback"):
        review.statement_evidence(
            review.xml_root(filing(listing=False)), "fixture", review.LISTING_STATEMENT
        )


def test_listing_statement_locator_resolves_exact_evidence():
    root = review.xml_root(filing())
    item = review.statement_evidence(root, "fixture", review.LISTING_STATEMENT)
    assert review.normalized_text(root.xpath(item["locator"])[0]) == item["value"]


def test_dtd_is_rejected_without_resolving_entities():
    with pytest.raises(ValueError, match="DTD"):
        review.xml_root(
            b'<!DOCTYPE x [<!ENTITY data SYSTEM "file:///does-not-exist">]><x>&data;</x>'
        )


def test_changed_audit_requires_new_review(tmp_path):
    path = tmp_path / review.AUDIT_PATH
    path.parent.mkdir(parents=True)
    path.write_text('{"quote_currency": "USD"}')
    with pytest.raises(ValueError, match="new evidence review"):
        review.read_audit(tmp_path)


@pytest.mark.parametrize("action,status", [("review", 0), ("check-registration", 2)])
def test_cli_reports_blocker_and_check_exits_nonzero(monkeypatch, capsys, action, status):
    monkeypatch.setattr(
        review,
        "application_review",
        lambda: {
            "registration_ready": False,
            "blocking_reasons": ["quote_currency_unsubstantiated"],
        },
    )
    monkeypatch.setattr("sys.argv", ["review_crcl_identity", action])
    assert review.main() == status
    assert json.loads(capsys.readouterr().out)["blocking_reasons"] == [
        "quote_currency_unsubstantiated"
    ]


def test_capture_timestamps_compare_instants_not_display_offsets():
    assert review.metadata_equal(
        datetime.fromisoformat("2026-09-21T10:07:35-07:00"), "2026-09-21 17:07:35+00:00"
    )
    assert not review.metadata_equal(
        datetime.fromisoformat("2026-09-21T10:07:35-07:00"), "2026-09-21 17:07:36+00:00"
    )


@pytest.mark.integration
def test_application_review_enforces_read_only_transaction(monkeypatch, db_admin, captured):
    from contextlib import nullcontext

    import psycopg

    audit, archive = captured
    monkeypatch.setattr(review, "read_audit", lambda root: audit)
    monkeypatch.setattr(review, "LocalArchive", lambda root: archive)
    monkeypatch.setattr(review.app_postgres, "guard", lambda runtime: None)
    monkeypatch.setattr(review.app_postgres, "verify", lambda runtime: None)
    monkeypatch.setattr(
        review.app_postgres, "owner_connection", lambda *args: nullcontext(db_admin)
    )
    # The command expects a runtime with a database name; this one never opens application settings.
    from types import SimpleNamespace

    monkeypatch.setattr(
        review.app_postgres, "configuration", lambda: (SimpleNamespace(database="test"), None)
    )

    def verify_read_only(db, audit, archive):
        assert db.execute("SHOW transaction_read_only").fetchone()["transaction_read_only"] == "on"
        assert (
            db.execute("SHOW transaction_isolation").fetchone()["transaction_isolation"]
            == "repeatable read"
        )
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction), db.transaction():
            db.execute("INSERT INTO issuers(id,legal_name) VALUES (%s,'not allowed')", (uuid4(),))

    monkeypatch.setattr(review, "verify_database_evidence", verify_read_only)
    before = review.database_snapshot(db_admin)
    result = review.application_review()
    assert result["same_snapshot_before_after"]
    assert result["database_snapshot"] == before == review.database_snapshot(db_admin)
    assert not result["registration_ready"]
    assert before["security_identifiers"]["count"] == before["analysis_requests"]["count"] == 0
