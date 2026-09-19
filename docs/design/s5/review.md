# S5 source-metric numeric review

Scope: the first implementation on `codex/s5-source-metrics`, compared with
planning checkpoint `c1f2697`. Review date: 2026-09-19. This is not acceptance
of all S5 or of the guided product. Two independent agents reviewed standards
and specification adherence, focusing on believable incorrect financial values.
The root also checked interpolation boundaries and failure handling.

## Findings and repairs

| Finding | Repair and regression |
| --- | --- |
| Fixed-50-digit interpolation rounded identical high-precision samples below themselves; opposing large values could yield a false zero median. | History interpolation now uses bounded sufficient exact precision. Identical samples remain within their band; `10^60` and `−(10^60−1)` yield median `0.5`. The independent reviewer rechecked the repair. |
| Fact units matched even when the selected statements' reporting currencies differed. | Financial input comparison includes effective reporting currency; an inconsistent explicit whole-money reporting currency blocks the operand. Tests reject plausible USD FCF formed from mismatched statement currency contexts. |
| The archived-normalization fixture helper dropped batch/period errors and inferred usability from observed amounts. | Preserve applicable quality evidence and block affected outputs. Archived AAPL/MSFT incompleteness remains visible; the FCF arithmetic example uses a separately identified synthetic complete-evidence selection. No real source eligibility is asserted from observed numbers alone. |
| Invalid source period dates were flagged by projection but growth still dereferenced the invalid date. | Growth rejects unsupported date types and preserves the source gap instead of crashing. Regression was observed failing before repair. |

All actionable findings in the bounded review were addressed. Reviewers found
no additional scoped formula issue; later TTM/EPS/price/API work was deliberately
excluded from this claim.

## Validation

Numeric expectations were written before implementation. Focused tests cover
source identity/lineage, precision evidence, missing values, incompatible periods/
editions/scopes/currencies/bases, capex signs, consolidated income, known flags,
Decimal context/overflow/underflow/loss of digits, calendar comparisons, each
3/5/10-year window, missing quarters, duplicates/conflicts and percentile equality.
The extreme-margin and negative-FCF examples are explicitly synthetic.

Focused verification: **150 core tests passed**; core Ruff and mypy checks passed.

The commit hook requires `make lint typecheck test test-core test-golden` and is
not bypassed. Verification uses the existing disposable Timescale/Postgres test
profile and repository-owned Redis, not application databases or live providers.
The validated strict-editable package path is passed to child processes to avoid
the already documented iCloud hidden-`.pth` recurrence; no dependency changes.

The first full gate passed 850 tests but 17 Redis-dependent setups failed at
`Isolated Redis did not start`. The existing helper probes immediately after
daemon startup; its server log shows readiness just afterward. An ownership-
checked status call confirmed Redis 8.8.1 ready on the repository test port.
The full mandatory gate was retried after readiness; no test was skipped and
no application service or financial implementation was changed for this retry.

## Remaining trust and integration boundaries

Inputs are projections of trusted, previously selected PIT records. Pure core
checks their supplied identity, flags and lineage; it does not re-query storage,
rebuild private selection hashes or prove database relationships. The unchanged
schema/PIT regression suite owns those selection guarantees. Normalizer fixture
tests exercise the boundary with archived evidence but are not a new DB PIT test.

History receives already evaluated comparable metrics. Its explicit series key
and input hash are supplied by the caller; core does not establish per-sample
source freshness, sector suitability, price calendar/action eligibility or fetch
historical observations. Minimums in fixtures are explicit policies, not activated
product defaults. Source-only arithmetic and raw amounts do not claim investment
merit or complete financial-statement validation. Accounting identity checks,
TTM/EPS and the remaining metric inventory are later S5 work.
