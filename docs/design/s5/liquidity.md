# S5b follow-on — Source-only liquidity calculations

User authorized continuing functional implementation after accepting D4c's UI.
This bounded addition resumes the existing S5/F1 working-capital backlog while
quote/provider dependencies stay pending. It uses only approved current_assets
and current_liabilities concepts and existing selected FinancialInput evidence.
No schema, concept enum, public API, source policy or saved status changes.

## Arithmetic and eligibility

- Current ratio = reported consolidated current assets / current liabilities.
  Result unit is multiple: 150 / 100 = 1.5, not 150%.
- Net working capital = reported consolidated current assets - current liabilities.
  Result is in the original currency: 150 - 100 = 50; 50 - 100 = -50.
  This is total reported NWC, not operating working capital, unrestricted cash,
  debt capacity or a cash-flow forecast.

Both operands must be selected observed facts, the exact requested concepts,
instant balance-sheet amounts at the same date, same filing edition, issuer,
currency, reporting basis and history selection policy. Existing source/provenance
and semantic-scope guards apply. No summing instant balances into TTM, no total-
asset fallback and no parent/consolidated substitution. Unsupported classified
balances remain missing, including businesses whose statements do not report them.

Negative reported current assets or current liabilities produce a flagged gap;
the original values remain inspectable. A negative NWC difference is valid.
Zero current assets is valid. Zero current liabilities gives N/A for the ratio,
but subtraction can still return working capital. Missing values never become zero.

The ratio reuses the existing positive-denominator/source-precision guard:
liabilities must exceed their explicit absolute error. Unknown precision blocks
the ratio. Subtraction uses the existing exact Decimal operation without inventing
precision; unsupported magnitude or rounded monetary subtraction yields a gap.
Both retain operands, flags and s5-source-metrics-v1 formula revision. No liquidity
threshold, industry judgment, score or buy/sell interpretation is introduced.

## Reuse and verification

Extend the existing shared source guard with an explicit balance-sheet mode;
default income/cash-flow behavior is unchanged. Reuse Calculation, _calculate,
_denominator and exact _difference, keeping arithmetic in core. New functions
are internal engine capabilities; publishing real values follows S6/selected-
source integration, and the accepted UI stays unchanged with N/A placeholders.

Hand-calculated tests were written first and failed on the absent functions.
They cover 1.5x / 50 and 0.5x / -50 examples, zeros/missing/negative inputs,
precision, date/currency/edition/history/basis/scope/concept/family mismatches,
source flags, hostile Decimal contexts and unsupported magnitude. Existing
source-metric and period tests protect the shared guard's old behavior.
Independent numeric and standards review precede the mandatory full commit gate.

## Final review

Two independent read-only reviews compared the staged change with 05edb36.
Standards: no findings. Spec/numeric: no findings, including plausible wrong
values from incompatible instant dates, editions, scopes, units and precision.
Default flow validation remains unchanged. All 261 core tests passed, including
36 new liquidity cases; Ruff and strict mypy passed. The mandatory checkpoint
hook verifies the full tree, core and golden suites before commit.
