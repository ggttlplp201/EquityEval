# S5b — Source-only liquidity follow-on

Status: complete for the bounded source-only calculation scope; full S5 remains in progress.
Baseline: 05edb36 / milestone/d4c-pilot-ui.
Checkpoint: milestone/s5b-liquidity.

After the user accepted the UI and asked to move on, resumed the existing S5
working-capital backlog without waiting for missing quote/provider data. Added
current_ratio and net_working_capital to the pure engine using existing selected
current_assets/current_liabilities concepts, exact arithmetic and provenance.
[Design and test boundary](../design/s5/liquidity.md).

Source-only formulas preserve missingness, reject mismatched dates/editions/
scopes/currencies and unusual negative component balances, and distinguish zero
liabilities from missing liabilities. A negative working-capital difference is
valid. No new schema, API, source activation, score or application publication.
UI remains as accepted; unavailable values show N/A.

Validation: tests specified before implementation; 36 new liquidity cases and
35 existing source-metric cases passed initially. All 261 core tests, Ruff and
strict mypy passed. Independent numeric and standards reviews found no issues.
The mandatory commit gate verifies the full/core/golden suites and static checks. The annotated checkpoint
records final counts. Numeric review focuses on plausible but wrong balances,
precision, period and ownership substitutions. Existing 3/5/10-year history is
unchanged. The manual adds concise terms and worked examples.

Next: remaining S5 supported definitions/interpretation and reviewed S6 result
publication. Debt/lease composition, ROE, EPS/action basis and source/provider
prerequisites remain their existing later slices; no placeholder becomes a value.
