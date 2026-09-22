# S5b follow-on — Annual return on assets

Continues the existing S5/F1 returns backlog after milestone/s5b-liquidity, under
the user's instruction to continue implementation. Reuses approved concepts and
internal Calculation/FinancialInput outputs. No schema, public API, stored status,
source policy or UI change.

## Formula and source boundary

ROA = consolidated net income / ((opening total assets + closing total assets) / 2).

Example: annual net income 10, opening assets 80 and closing assets 120 give
average assets 100 and ROA 0.10 (10%). A loss of 20 gives -20%; zero income gives
zero. This uses two endpoint balances, not average daily assets. No automatic
industry score or investment verdict is assigned.

The first supported boundary is a reported twelve-calendar-month income input,
validated by existing annual_amount. Non-January fiscal years and leap days are
supported when month boundaries align. Quarter/YTD periods are not annualized.
52/53-week calendars and multi-filing assembled TTM remain outside this slice.

Opening assets must be dated exactly the day before the income period begins;
closing assets must match its end. All three selected inputs must have the same
filing edition, issuer/history policy, reporting currency and accounting basis,
with consolidated scope. Use net_income_consolidated and total_assets exactly;
never substitute parent-only income, current assets, or just ending assets.
An annual filing's comparable beginning/end balances can meet the same-edition
rule. A convenient prior year's original filing does not establish compatible
restatement treatment. Cross-edition acceptance remains a later reviewed boundary.

Both asset endpoints must independently be positive and distinguishable from zero
at their own source precision. Unknown precision, zero/negative assets, unavailable
inputs or incompatible evidence return None with flags. A positive average never
hides a bad endpoint. Original values and all operands remain attached.

The average uses the existing bounded exact Decimal context; its addition/division
must not round before the final ratio. An unrepresentable intermediate result
returns a flagged gap. Ratio rounding retains the existing 50-digit context and
is independent of the caller's precision, rounding and traps.

## Reuse and verification

Extract the existing common selection/identity/unit validation into a private
helper used by both old metrics and the new flow-plus-balances calculation.
Existing period/family/scope guards remain unchanged. Reuse annual_amount,
_denominator and _calculate; no second source-selection or fiscal-period engine.
All arithmetic remains in core. The UI stays as accepted, with N/A for unavailable
published values; these internal functions do not manufacture application results.

Hand-calculated tests precede implementation. Cases cover positive/loss/zero
income; missing inputs; each endpoint's precision/sign; date swaps and boundaries;
quarter/YTD/52-week rejection; currency, basis, edition, history, family and concept
mismatches; retained source flags; hostile Decimal context and unsupported numeric
magnitude. Core regressions protect existing liquidity, flow and period behavior.
Independent numeric/standards review and the mandatory commit gate follow.

## Final review

Two independent read-only reviews compared the staged change with 5f02303.
Standards: no findings. Spec/numeric: no findings, including plausible incorrect
results from source mixing, endpoint dates, invalid balances or rounded averages.
The shared guard extraction preserves old flow/liquidity behavior.
All 297 core tests passed, including 36 new ROA cases; Ruff and strict mypy passed.
The required commit hook validates the final full/core/golden suites and static
checks. Its final counts are retained in the annotated milestone tag.
