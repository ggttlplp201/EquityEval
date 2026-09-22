"""Hand-computed balance sheet identities and source uncertainty, all fictional."""

from dataclasses import replace
from datetime import date
from decimal import ROUND_UP, Decimal, Inexact, localcontext

import pytest
from equity_core.reconciliation import balance_sheet_identity
from equity_schema.concepts import Concept

from tests.core.metric_fixtures import balance


def inputs(assets="100", liabilities="60", equity="40", error=".5"):
    return tuple(
        balance(concept, value, absolute_error=error)
        for concept, value in (
            (Concept.TOTAL_ASSETS, assets),
            (Concept.TOTAL_LIABILITIES, liabilities),
            (Concept.EQUITY_INCLUDING_NONCONTROLLING_INTERESTS, equity),
        )
    )


@pytest.mark.parametrize(
    "assets,liabilities,equity,residual,matches",
    [
        ("100", "60", "40", "0", True),
        ("100", "120", "-20", "0", True),
        ("100", "60", "38.5", "1.5", True),
        ("100", "60", "38.49", "1.51", False),
        ("100", "60", "41.51", "-1.51", False),
        ("0", "0", "0", "0", True),
    ],
)
def test_identity_uses_inclusive_sum_of_absolute_source_uncertainty(
    assets, liabilities, equity, residual, matches
):
    sources = inputs(assets, liabilities, equity)
    result = balance_sheet_identity(*sources)
    assert result.calculation.value == Decimal(residual)
    assert result.tolerance == Decimal("1.5")
    assert result.matches is matches
    assert result.calculation.operands == sources
    assert ("balance_sheet_identity_mismatch" in result.calculation.flags) is (not matches)
    assert sources[0].value == Decimal(assets)  # never correct the facts to make them tie.


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "precision",
        "date",
        "edition",
        "currency",
        "parent",
        "negative_assets",
        "negative_liabilities",
        "huge",
    ],
)
def test_unavailable_or_incompatible_evidence_does_not_claim_reconciliation(change):
    assets, liabilities, equity = inputs()
    if change == "missing":
        assets = balance(Concept.TOTAL_ASSETS, None)
    elif change == "precision":
        equity = replace(equity, precision=None)
    elif change == "date":
        equity = balance(
            Concept.EQUITY_INCLUDING_NONCONTROLLING_INTERESTS, "40", end=date(2024, 12, 31)
        )
    elif change == "edition":
        equity = balance(Concept.EQUITY_INCLUDING_NONCONTROLLING_INTERESTS, "40", edition="other")
    elif change == "currency":
        equity = balance(Concept.EQUITY_INCLUDING_NONCONTROLLING_INTERESTS, "40", currency="EUR")
    elif change == "parent":
        equity = balance(Concept.EQUITY_PARENT, "40")
    elif change == "negative_assets":
        assets = balance(Concept.TOTAL_ASSETS, "-100")
    elif change == "negative_liabilities":
        liabilities = balance(Concept.TOTAL_LIABILITIES, "-60")
    else:
        assets = balance(Concept.TOTAL_ASSETS, "1e1001")
    result = balance_sheet_identity(assets, liabilities, equity)
    assert result.matches is None
    assert result.calculation.value is None
    assert result.calculation.flags
    assert result.calculation.operands == (assets, liabilities, equity)


def test_cancellation_is_exact_under_hostile_context():
    sources = inputs("1e60", "1e60", "1", error="0")
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.rounding = ROUND_UP
        ctx.traps[Inexact] = True
        result = balance_sheet_identity(*sources)
    assert result.calculation.value == Decimal("-1")
    assert result.tolerance == Decimal(0)
    assert result.matches is False
