# S8c — pinned acceptance (2026-09-29)

Baseline: `30c35c61b9f42602381acbf5c0ae2423ecc2b762`.
Branch: `codex/s8c-financials-ui`. Continue the company-page milestone after S8b.

## Audited data gap and bounded implementation

S6a FundamentalsPayload publishes selected metrics under one period basis, not
complete statements. D1b uses a different sector snapshot identity. SEC
StatementSelection/PeriodSpec/UnitSpec have normalized semantics but no immutable
public statement export suitable for this page. The real pilot is archived
research, not a published financial statement. Do not join these identities.

Create the smallest local synthetic presentation payload, like X1/D1b, outside
shared schema/API/core. Reuse Concept, period_spec, unit_spec and canonical
content hashing. The standalone fictional company has three saved editions:
original annual, revised annual, and directly reported first quarter. Income,
balance sheet and cash flow show selected reviewed lines, not a complete filing.
Every supplied value copies an exact fixture string; no financial calculation,
aggregation, interpolation or implied accounting total. Annual and quarter flows
have explicit durations; balances are instants. TTM is disabled because no
reviewed TTM statement export exists. Unsupported data remains null / N/A.

## Acceptance

- Strict typed exporter validates numeric strings, concept/statement mapping,
  original source text, currency USD/unit/scale 1, consolidated scope, dates,
  period kinds, edition/restatement lineage, unique selector keys and evidence.
  Source IDs/hashes and snapshot IDs bind content. Reproducible --check gate.
- Exact-one GET selection by basis/edition; unknown keys, duplicate parameters,
  duplicate candidates and unsupported basis fail closed. Server sends one saved
  snapshot and selector metadata only. No future/revised rows in original payload.
- `/development/company/financials`: three statement sections, Annual/Quarterly
  controls, TTM disabled, saved-edition selection. Coverage is supplied count of
  reviewed lines, never a claim of full filing coverage. Concise N/A placeholders.
- Existing shell/navigation, evidence drawer and S8a maximum four display decimals;
  exact raw strings in evidence. Identity, source fixture pointer/hash, accession,
  filed/known/retrieved dates, unit/scale, scope, transform and prior-source lineage.
- Saved editions retain separate history modes and restatement status. No browser
  arithmetic, finance advice, real publication, provider/scheduler activation or
  changes to S8a/S8b financial behavior.
- Tests first for semantics, invalid source/period/identity, missingness, lineage,
  selectors and rounding. Browser 320/390/768/1440, exact selection, drawer keyboard
  and focus, navigation, loading/error, invalid query and local GET-only requests.
- Lint, types, deterministic export, focused/full/core/golden, optimized build,
  S8a/S8b browser regression and independent spec/standards review before commit.
  Record exact evidence, annotated milestone tag and clean tree; stop at S8c.
