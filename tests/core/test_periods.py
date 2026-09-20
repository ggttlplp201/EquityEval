"""Period arithmetic uses fictional values with complete source-shaped evidence."""

from datetime import date
from decimal import Decimal

from equity_core.periods import annual_amount
from equity_schema.concepts import Concept

from tests.core.metric_fixtures import operand


def test_direct_calendar_annual_retains_source_value_and_evidence():
    source = operand(Concept.REVENUE, "120", absolute_error="0.5")
    result = annual_amount(source)
    assert result.value == Decimal("120")
    assert result.operands == (source,)
    assert result.coefficients == (1,)
    assert result.period.start_date == date(2025, 1, 1)
    assert result.period.end_date == date(2025, 12, 31)
    assert result.precision == source.precision
    assert result.formula_id == "direct_annual"
    assert not result.blocking_flags


def test_annual_requires_exact_twelve_calendar_month_flow():
    for source in (
        operand(Concept.REVENUE, "120", end=date(2025, 9, 30)),
        operand(Concept.REVENUE, "120", end=date(2025, 12, 30)),
        operand(Concept.REVENUE, "120", start=date(2025, 1, 2)),
        operand(Concept.EPS_DILUTED, "12"),
        operand(Concept.WEIGHTED_AVERAGE_SHARES_DILUTED, "10"),
        operand(Concept.TOTAL_ASSETS, "100", start=None),
        operand(Concept.NET_INCOME_PARENT, "30"),
    ):
        result = annual_amount(source)
        assert result.value is None
        assert result.blocking_flags
        assert result.operands == (source,)


def quarters(concept=Concept.REVENUE):
    return tuple(
        operand(concept, value, start=start, end=end)
        for value, start, end in (
            ("10", date(2025, 1, 1), date(2025, 3, 31)),
            ("20", date(2025, 4, 1), date(2025, 6, 30)),
            ("30", date(2025, 7, 1), date(2025, 9, 30)),
            ("40", date(2025, 10, 1), date(2025, 12, 31)),
        )
    )


def test_ttm_sums_four_quarters_and_adds_uncertainties():
    from equity_core.periods import ttm_from_quarters

    sources = quarters()
    result = ttm_from_quarters(sources)
    assert result.value == Decimal("100")
    assert result.period.start_date == date(2025, 1, 1)
    assert result.period.end_date == date(2025, 12, 31)
    assert result.operands == sources
    assert result.coefficients == (1, 1, 1, 1)
    assert result.precision.absolute_error == Decimal("2")
    assert set(result.precision.observation_ids) == {
        source.fact.observation_ids[0] for source in sources
    }
    assert not result.blocking_flags


def test_ttm_never_sums_missing_overlapping_gapped_or_incompatible_quarters():
    from dataclasses import replace

    from equity_core.periods import ttm_from_quarters
    from equity_schema.pit import HistoryMode

    q1, q2, q3, q4 = quarters()
    wrong_policy = replace(
        q4,
        selection=replace(
            q4.selection,
            query=replace(
                q4.selection.query,
                mode=HistoryMode.LATEST_REPORTED,
            ),
        ),
    )
    cases = (
        (q1, q2, q3),
        (q1, q2, q3, q3),
        (q1, q3, q2, q4),
        (q1, q2, q3, operand(Concept.REVENUE, "40", start=date(2026, 1, 1), end=date(2026, 3, 31))),
        (
            q1,
            q2,
            q3,
            operand(Concept.REVENUE, None, start=date(2025, 10, 1), end=date(2025, 12, 31)),
        ),
        (
            q1,
            q2,
            q3,
            operand(
                Concept.REVENUE,
                "40",
                start=date(2025, 10, 1),
                end=date(2025, 12, 31),
                currency="EUR",
            ),
        ),
        (
            q1,
            q2,
            q3,
            operand(Concept.COST_OF_REVENUE, "40", start=date(2025, 10, 1), end=date(2025, 12, 31)),
        ),
        (q1, q2, q3, wrong_policy),
    )
    for sources in cases:
        result = ttm_from_quarters(sources)
        assert result.value is None
        assert result.blocking_flags
        assert result.operands == sources
        assert result.precision is None


def test_derived_precision_stays_unknown_and_decimal_math_is_exact_in_hostile_context():
    from dataclasses import replace
    from decimal import ROUND_UP, Inexact, localcontext

    from equity_core.periods import ttm_from_quarters

    sources = quarters()
    unknown = (*sources[:3], replace(sources[3], precision=None))
    assert ttm_from_quarters(unknown).precision is None
    assert ttm_from_quarters(unknown).value == Decimal("100")
    large = tuple(
        operand(Concept.REVENUE, value, start=source.period.start_date, end=source.period.end_date)
        for source, value in zip(sources, ("1e60", "1", "-1e60", "2"), strict=True)
    )
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.rounding = ROUND_UP
        ctx.traps[Inexact] = True
        result = ttm_from_quarters(large)
    assert result.value == Decimal("3")
    assert result.precision.absolute_error == Decimal("2")
    overflow = (
        *sources[:3],
        operand(Concept.REVENUE, "1e1001", start=date(2025, 10, 1), end=date(2025, 12, 31)),
    )
    assert ttm_from_quarters(overflow).value is None
    assert "unsupported_numeric_range" in ttm_from_quarters(overflow).flags


def test_cross_filing_quarters_require_exact_reviewed_revision_evidence():
    from dataclasses import replace

    from equity_core.periods import RevisionCompatibility, ttm_from_quarters

    from tests.core.metric_fixtures import identity

    sources = tuple(
        replace(
            source,
            selection=replace(
                source.selection,
                filing_version_ids=(identity("quarter-edition-" + str(index)),),
            ),
        )
        for index, source in enumerate(quarters())
    )
    blocked = ttm_from_quarters(sources)
    assert blocked.value is None
    assert "revision_compatibility_unproven" in blocked.flags
    proof = RevisionCompatibility(
        tuple(source.selection.input_hash for source in sources),
        ("synthetic:reviewed-no-conflicting-revisions",),
        "synthetic-review-v1",
    )
    result = ttm_from_quarters(sources, revision_compatibility=proof)
    assert result.value == Decimal("100")
    assert result.revision_compatibility is proof
    wrong = replace(proof, input_hashes=("a" * 64,))
    blocked = ttm_from_quarters(sources, revision_compatibility=wrong)
    assert blocked.value is None
    assert "revision_compatibility_mismatch" in blocked.flags


def test_quarter_from_same_fiscal_start_ytd_subtracts_and_preserves_precision():
    from equity_core.periods import quarter_from_ytd

    current = operand(
        Concept.CASH_FROM_OPERATING_ACTIVITIES, "70", start=date(2024, 7, 1), end=date(2025, 3, 31)
    )
    prior = operand(
        Concept.CASH_FROM_OPERATING_ACTIVITIES, "45", start=date(2024, 7, 1), end=date(2024, 12, 31)
    )
    result = quarter_from_ytd(current, prior)
    assert result.value == Decimal("25")
    assert result.period.start_date == date(2025, 1, 1)
    assert result.period.end_date == date(2025, 3, 31)
    assert result.operands == (current, prior)
    assert result.coefficients == (1, -1)
    assert result.precision.absolute_error == Decimal("1")
    assert not result.blocking_flags


def test_ytd_subtraction_rejects_different_fiscal_start_edition_or_quarter_length():
    from equity_core.periods import quarter_from_ytd

    current = operand(Concept.REVENUE, "70", end=date(2025, 9, 30))
    for prior in (
        operand(Concept.REVENUE, "45", start=date(2025, 4, 1), end=date(2025, 6, 30)),
        operand(Concept.REVENUE, "45", end=date(2025, 6, 30), edition="different"),
        operand(Concept.REVENUE, "45", end=date(2025, 3, 31)),
        operand(Concept.REVENUE, "45", end=date(2025, 7, 31)),
        operand(Concept.REVENUE, "45", end=date(2025, 12, 31)),
        operand(Concept.REVENUE, None, end=date(2025, 6, 30)),
    ):
        result = quarter_from_ytd(current, prior)
        assert result.value is None
        assert result.blocking_flags


def test_ttm_annual_plus_current_ytd_minus_prior_ytd_covers_exact_year():
    from equity_core.periods import ttm_from_annual_ytd

    annual = operand(Concept.REVENUE, "100", start=date(2024, 1, 1), end=date(2024, 12, 31))
    current = operand(Concept.REVENUE, "80", end=date(2025, 9, 30))
    prior = operand(Concept.REVENUE, "60", start=date(2024, 1, 1), end=date(2024, 9, 30))
    result = ttm_from_annual_ytd(annual, current, prior)
    assert result.value == Decimal("120")
    assert result.period.start_date == date(2024, 10, 1)
    assert result.period.end_date == date(2025, 9, 30)
    assert result.operands == (annual, current, prior)
    assert result.coefficients == (1, 1, -1)
    assert result.precision.absolute_error == Decimal("1.5")
    assert not result.blocking_flags


def test_annual_ytd_bridge_rejects_shifted_years_fiscal_starts_and_missing_periods():
    from equity_core.periods import ttm_from_annual_ytd

    annual = operand(Concept.REVENUE, "100", start=date(2024, 1, 1), end=date(2024, 12, 31))
    current = operand(Concept.REVENUE, "80", end=date(2025, 9, 30))
    prior = operand(Concept.REVENUE, "60", start=date(2024, 1, 1), end=date(2024, 9, 30))
    for sources in (
        (
            annual,
            current,
            operand(Concept.REVENUE, "60", start=date(2024, 1, 1), end=date(2024, 6, 30)),
        ),
        (
            annual,
            operand(Concept.REVENUE, "80", start=date(2026, 1, 1), end=date(2026, 9, 30)),
            prior,
        ),
        (
            annual,
            operand(Concept.REVENUE, "80", start=date(2025, 4, 1), end=date(2025, 12, 31)),
            prior,
        ),
        (annual, operand(Concept.REVENUE, "80", end=date(2025, 12, 31)), prior),
        (annual, operand(Concept.REVENUE, None, end=date(2025, 9, 30)), prior),
        (
            operand(Concept.REVENUE, "100", start=date(2024, 1, 1), end=date(2024, 12, 28)),
            current,
            prior,
        ),
        (
            operand(Concept.REVENUE, "100", start=date(2024, 1, 1), end=date(2024, 9, 30)),
            current,
            prior,
        ),
    ):
        result = ttm_from_annual_ytd(*sources)
        assert result.value is None
        assert result.blocking_flags


def test_invalid_extreme_dates_and_duplicate_observation_identity_fail_closed():
    from dataclasses import replace

    from equity_core.periods import ttm_from_quarters

    q1, q2, q3, q4 = quarters()
    maximum = operand(Concept.REVENUE, "10", start=date(9999, 10, 1), end=date.max)
    result = ttm_from_quarters((maximum, q2, q3, q4))
    assert result.value is None
    duplicated = replace(
        q4,
        selection=replace(
            q4.selection,
            facts=(replace(q4.fact, observation_ids=q1.fact.observation_ids),),
        ),
        precision=replace(q4.precision, observation_ids=q1.precision.observation_ids),
    )
    result = ttm_from_quarters((q1, q2, q3, duplicated))
    assert result.value is None
    assert "duplicate_period_observation" in result.flags


def test_ytd_bridge_allows_leap_year_and_non_january_fiscal_start_with_revision_proof():
    from equity_core.periods import RevisionCompatibility, ttm_from_annual_ytd

    annual = operand(
        Concept.REVENUE, "100", start=date(2023, 3, 1), end=date(2024, 2, 29), edition="annual"
    )
    current = operand(
        Concept.REVENUE, "35", start=date(2024, 3, 1), end=date(2024, 5, 31), edition="current"
    )
    prior = operand(
        Concept.REVENUE, "20", start=date(2023, 3, 1), end=date(2023, 5, 31), edition="current"
    )
    assert ttm_from_annual_ytd(annual, current, prior).value is None
    proof = RevisionCompatibility(
        tuple(item.selection.input_hash for item in (annual, current, prior)),
        ("synthetic:compatible-revision-review",),
        "test-review-v1",
    )
    result = ttm_from_annual_ytd(annual, current, prior, revision_compatibility=proof)
    assert result.value == Decimal("115")
    assert result.period.start_date == date(2023, 6, 1)
    assert result.period.end_date == date(2024, 5, 31)
    assert result.revision_compatibility is proof


def test_revision_review_cannot_override_issuer_basis_scope_or_source_flags():
    from dataclasses import replace

    from equity_core.periods import RevisionCompatibility, ttm_from_quarters
    from equity_ingest.financial_types import canonical_json, content_hash

    from tests.core.metric_fixtures import identity

    q1, q2, q3, q4 = quarters()
    descriptor = {
        "consolidation": "consolidated",
        "instrument": None,
        "context_knowledge": "unknown",
        "scope_evidence": "different reviewed scope",
        "cash_scope": "not_applicable",
        "payment_basis": "as_reported",
        "revenue_basis": "reported_complete_scope",
    }
    new_scope = replace(
        q4.scope,
        id=identity("different-scope"),
        descriptor_json=canonical_json(descriptor),
        content_sha256=content_hash(descriptor),
    )
    candidates = (
        replace(q4, selection=replace(q4.selection, reporting_basis="ifrs")),
        replace(
            q4,
            selection=replace(
                q4.selection,
                query=replace(q4.selection.query, issuer_id=identity("different-issuer")),
            ),
        ),
        replace(q4, selection=replace(q4.selection, flags=("unresolved_restatement",))),
        replace(
            q4,
            scope=new_scope,
            selection=replace(
                q4.selection, query=replace(q4.selection.query, scope_id=new_scope.id)
            ),
        ),
    )
    for candidate in candidates:
        sources = (q1, q2, q3, candidate)
        proof = RevisionCompatibility(
            tuple(item.selection.input_hash for item in sources), ("synthetic:review",), "review-v1"
        )
        result = ttm_from_quarters(sources, revision_compatibility=proof)
        assert result.value is None
        assert result.blocking_flags


def test_revision_compatibility_record_requires_immutable_explicit_evidence():
    import pytest
    from equity_core.periods import RevisionCompatibility

    for hashes, refs, revision in (
        ((), ("review",), "v1"),
        (("bad-hash",), ("review",), "v1"),
        (("a" * 64, "a" * 64), ("review",), "v1"),
        (("a" * 64,), (), "v1"),
        (("a" * 64,), (" ",), "v1"),
        (("a" * 64,), ("review",), " "),
    ):
        with pytest.raises(ValueError):
            RevisionCompatibility(hashes, refs, revision)


def test_negative_cash_ppe_source_cannot_disappear_inside_positive_ttm_total():
    from equity_core.metrics import free_cash_flow
    from equity_core.periods import ttm_from_quarters

    capex = quarters(Concept.CAPITAL_EXPENDITURES_PPE)
    negative = operand(
        Concept.CAPITAL_EXPENDITURES_PPE, "-10", start=date(2025, 1, 1), end=date(2025, 3, 31)
    )
    amount = ttm_from_quarters((negative,) + capex[1:])
    assert amount.value is None
    assert "negative_cash_ppe_capex" in amount.flags
    cash = ttm_from_quarters(quarters(Concept.CASH_FROM_OPERATING_ACTIVITIES))
    assert free_cash_flow(cash, amount).value is None
    assert annual_amount(operand(Concept.CAPITAL_EXPENDITURES_PPE, "-1")).value is None


def test_negative_derived_ppe_quarter_is_unavailable_without_erasing_sources():
    from equity_core.periods import quarter_from_ytd

    current = operand(Concept.CAPITAL_EXPENDITURES_PPE, "5", end=date(2025, 6, 30))
    prior = operand(Concept.CAPITAL_EXPENDITURES_PPE, "10", end=date(2025, 3, 31))
    amount = quarter_from_ytd(current, prior)
    assert amount.value is None
    assert "negative_cash_ppe_capex" in amount.flags
    assert amount.operands == (current, prior)
