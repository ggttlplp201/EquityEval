"""The fictional graph fixture exercises the same source-to-sector path as core."""

from decimal import Decimal

from equity_core.sectors import calculate_sector

from scripts.build_sector_fixture import AS_OF, POLICY, company, evaluation, roster


def test_fixture_loss_remains_in_aggregate_and_is_excluded_from_company_pe():
    companies = tuple(company(f"computing-{i + 1:02d}", "computing", i, AS_OF) for i in range(12))
    membership = roster(tuple(item.issuer_id for item in companies), AS_OF, "computing")
    total = calculate_sector(membership, companies, metric="pe", method="total", policy=POLICY)
    median = calculate_sector(membership, companies, metric="pe", method="median", policy=POLICY)
    assert total.n == total.k == total.v == 12
    assert total.negative_count == 1
    assert median.v == 11
    assert total.value != median.value
    details = {}
    raw = evaluation(total, "computing", "Computing", "pe", details, include_companies=True)
    assert raw["value"] == total.value
    assert raw["distribution"]["excluded"]
    assert sum(item["count"] for item in raw["distribution"]["bins"]) == 11
    assert all(item["detailId"] in details for item in raw["companies"])
    loss = next(item for item in raw["companies"] if item["id"] == "computing-12")
    assert loss["value"] is None and loss["status"] == "nm"
    assert companies[0].revenue.absolute_error == Decimal("2.0")


def test_fixture_missing_cap_and_unsupported_profiles_remain_visible():
    companies = tuple(company(f"health-{i + 1:02d}", "health", i, AS_OF) for i in range(12))
    membership = roster(tuple(item.issuer_id for item in companies), AS_OF, "health")
    result = calculate_sector(membership, companies, metric="pe", method="total", policy=POLICY)
    assert result.n == 12 and result.k == 11
    assert result.cap_coverage is None
    assert not result.comparison_allowed
    detail = evaluation(result, "health", "Health", "pe", {}, include_companies=True)
    assert detail["status"] == "limited"
    unsupported = company("property-finance-01", "property-finance", 0, AS_OF)
    membership = roster((unsupported.issuer_id,), AS_OF, "property-finance")
    result = calculate_sector(
        membership, (unsupported,), metric="pfcf", method="total", policy=POLICY
    )
    assert result.value is None
    assert result.excluded[0].reasons == ("unsupported_profile",)


def test_whole_sector_unavailable_status_keeps_profile_and_staleness_causes():
    from dataclasses import replace

    companies = tuple(
        company(f"property-finance-{i + 1:02d}", "property-finance", i, AS_OF) for i in range(12)
    )
    membership = roster(tuple(item.issuer_id for item in companies), AS_OF, "property-finance")
    unsupported = calculate_sector(
        membership, companies, metric="pfcf", method="total", policy=POLICY
    )
    row = evaluation(
        unsupported, "property-finance", "Property & finance", "pfcf", {}, include_companies=True
    )
    assert row["value"] is None and row["status"] == "unsupported"
    assert "unsupported_profile" in row["reasons"]
    stale_companies = tuple(
        replace(
            item,
            common_income=replace(item.common_income, usable=False, flags=("stale_financials",)),
        )
        for item in companies
    )
    stale = calculate_sector(
        membership, stale_companies, metric="pe", method="total", policy=POLICY
    )
    row = evaluation(
        stale, "property-finance", "Property & finance", "pe", {}, include_companies=True
    )
    assert row["value"] is None and row["status"] == "stale"
    assert "stale_financials" in row["reasons"]
    assert "no_contributors" in row["reasons"]
    mixed_companies = tuple(replace(item, applicable_metrics=()) for item in stale_companies)
    mixed = calculate_sector(
        membership, mixed_companies, metric="pe", method="total", policy=POLICY
    )
    row = evaluation(
        mixed, "property-finance", "Property & finance", "pe", {}, include_companies=True
    )
    assert row["status"] == "stale"
    assert {"stale_financials", "unsupported_profile"}.issubset(row["reasons"])
