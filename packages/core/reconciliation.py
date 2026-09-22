"""Evidence-bearing accounting checks; never repair a reported financial fact."""

from dataclasses import dataclass
from decimal import Decimal, DecimalException

from equity_core.inputs import FinancialInput
from equity_core.metrics import Calculation, _source_issues
from equity_core.periods import _exact_sum
from equity_schema.concepts import Concept


@dataclass(frozen=True)
class AccountingCheck:
    calculation: Calculation
    tolerance: Decimal | None
    matches: bool | None
    rule_revision: str = "s5-accounting-checks-v1"


def balance_sheet_identity(
    assets: FinancialInput, liabilities: FinancialInput, equity: FinancialInput
) -> AccountingCheck:
    """Assets − liabilities − equity INCLUDING NCI, within source uncertainty.

    Negative consolidated equity is valid here; parent/common equity is not an
    interchangeable operand. No arbitrary relative tolerance is introduced.
    """
    operands = (assets, liabilities, equity)
    problems = _source_issues(
        operands,
        (
            Concept.TOTAL_ASSETS,
            Concept.TOTAL_LIABILITIES,
            Concept.EQUITY_INCLUDING_NONCONTROLLING_INTERESTS,
        ),
        balance_sheet=True,
    )
    if any(source.precision is None for source in operands):
        problems.add("accounting_precision_unknown")
    if any(source.value is not None and source.value < 0 for source in (assets, liabilities)):
        problems.add("negative_accounting_balance")
    flags = {flag for source in operands for flag in source.flags} | problems
    residual = tolerance = None
    matches = None
    if not problems:
        try:
            residual = _exact_sum(
                tuple(source.value for source in operands if source.value is not None), (1, -1, -1)
            )
            tolerance = _exact_sum(
                tuple(
                    source.precision.absolute_error
                    for source in operands
                    if source.precision is not None
                ),
                (1, 1, 1),
            )
            matches = residual.copy_abs() <= tolerance
            if not matches:
                flags.add("balance_sheet_identity_mismatch")
        except (DecimalException, ValueError):
            residual = tolerance = None
            flags.add("unsupported_numeric_range")
    calculation = Calculation(
        "balance_sheet_residual",
        residual,
        assets.unit.unit_key,
        operands,
        tuple(sorted(flags)),
        "s5-accounting-checks-v1",
    )
    return AccountingCheck(calculation, tolerance, matches)
