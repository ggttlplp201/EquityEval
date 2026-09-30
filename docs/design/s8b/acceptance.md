# S8b — pinned acceptance (2026-09-29)

Baseline: `f46bf529edf4d333df2346045ff7b371b4993388`.
Branch: `codex/s8b-fundamentals-ui`. Authorization: milestone coordinator's
bounded S8b request after the completed S8a rounding checkpoint.

## Audit and reuse

Read F1, D1b, S6a contracts/implementation, generated FundamentalsPayload,
Company navigation, shared evidence drawer and saved-fundamentals manual.
Use `/development/company/ratios` as a separate explicitly fictional S6a
example. D1b's Sector-derived fixture has different snapshot/input identity;
no values, histories or company identities are combined. Link both views.
Reuse S8a numeric display (four decimals, exact evidence) and the shared drawer.

S6a requires one period basis per payload. Annual operations and instant balance
sheets therefore use separate saved selections, never a relabelled mixed result.
TTM is not inferred from annual data. All selections expose their actual basis.
PublicHistory has saved quartiles and eligible/excluded IDs but no sample values;
show an accessible quartile chart/table only with available saved bands. Do not
invent a timeline, sample values or benchmark. Missing sections/values show N/A.

## Required behavior

- Reproducible production presentation fixtures outside tests build typed
  InputManifest objects, validate canonical roundtrips, call unchanged Python
  calculate_payload and validate public output. Exporter supports --check and
  joins the normal no-diff gate. No test helper imports in presentation code.
- Read-only local GET selection sends only the requested saved snapshot to the
  browser. Explicit identity, currency, basis, financial/evaluation/filing/capture
  dates and snapshot/payload/input hashes remain available. Unknown/ambiguous
  selections fail closed. Earlier selections cannot expose future payload values.
- Growth → Profitability → Cash generation → Balance sheet → Valuation;
  expandable Returns on capital. Preserve all seven metric statuses, actual
  saved values/null/reasons, and separate coverage counts. At most three total
  saved neutral observations/review items; no score or investment verdict.
- 3/5/10-year selection retrieves each exact saved PublicHistory window. Show
  requested bounds, minimum, eligible/excluded counts and IDs/reasons, missing
  quarter ends and insufficiency. Never shorten the window. Chart geometry is
  presentation only; percentiles and comparison relations come from core.
- Every financial value opens exact evidence: operands/coefficients/formula
  revisions, source values/tags/precision/dates, selection hashes/IDs and snapshot.
  Keyboard dialog close/focus return, table access, mobile containment and Help.
- Fictional cases cover valid, N/M, missing, invalid, stale, unsupported and
  inapplicable metrics, complete/insufficient history and excluded samples.

## Verification and boundary

Write focused tests before implementation where practical. Python verifies
manifest/payload validation, calculation oracles, all statuses, saved history,
future-data exclusion and deterministic export. Node verifies formatting/status
and grouping. Browser checks 320/390/768/1440, selectors, history, evidence/focus,
navigation, GET-only local requests and overflow. Run build, lint, Python/TS
types, generated no-diff, full/core/golden; independent spec/standards review;
repair findings before a new commit and annotated milestone tag.

No core formulas, S5/S6 contracts/types, API, migration, providers/live data,
application writes, watchlist orchestration, sector peers, forward estimates,
scores or recommendations. Preserve prior commits/tags; stop at S8b.
