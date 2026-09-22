# Internal evaluation, neutral interpretation and accounting checks

This completes the remaining source-only evaluation boundary in the
[completion plan](completion-plan.md). Core consumes reviewed policy records;
it does not approve profiles, choose product defaults, fetch data, persist new
statuses or publish results. Existing facts remain Decimal/None plus source flags.
All examples and policy assignments in tests are fictional.

## Evaluating a source calculation

`assessment.py` routes ten supported source metric IDs back through their existing
calculators, plus checked-enum reported amounts. It compares the reconstructed
calculation with the supplied result and rebuilds PeriodAmount inputs. Altered
values, formula revisions, units or assemblies cannot become observations.
The registry reuses FinancialInput, Calculation, PeriodAmount and company evidence
validation. New financial formulas are not hidden inside this projection.

Every evaluation retains the Calculation and a frozen evaluation date, reviewed
issuer/business-model/lifecycle/instrument profile, its applicability roster,
effective/known dates, evidence and version, and the explicit freshness policy.
Only consolidated-issuer interpretation is supported by this slice. A bank,
insurer, REIT, stablecoin or other specialized business receives factual results
and no financial interpretation until its particular metric applicability is
reviewed. The module has no ticker/sector guess or automatic production assignment.
Applicability is true, false or unresolved with a rationale, independent of data
availability. Profile corrections create distinct input records, never edit facts.

Projection status is valid, not meaningful, missing, invalid, stale, unsupported
or inapplicable. These are internal evaluations only; D021/S6 still reviews their
public/storage mapping. Nonpositive or precision-indistinguishable denominators
are N/M when their required evidence is complete. Unknown precision is missing,
not an inferred zero error. Source/period/currency/semantic failures cannot become
N/M merely because a denominator is also nonpositive.

Freshness uses the most recent period end in the calculation (the current growth
endpoint, closing asset point or final TTM quarter), not an opening balance or
prior-year comparison base. Age exactly at the caller's maximum is allowed;
older is stale. If an explicit expected period and filing deadline are supplied,
a later evaluation without that period is stale. The deadline itself is allowed.
No 180/450-day default is activated. No input may have a later financial end or
filing selection cutoff than the frozen evaluation date. A saved evaluation does
not read the clock when reopened. Stale values retain their sources and numeric
value where available, but cannot drive financial observations or coverage.

Coverage is complete valid or evidenced N/M results / all explicitly applicable
metrics, in an isolated Decimal context. The full policy roster is counted;
omitted supported results are missing, omitted unknown definitions unsupported.
Unresolved applicability or zero applicable metrics gives no coverage fraction.
Separate status counts remain. Invalid/stale/missing/unsupported is not a stock
score. Duplicate metric results or mixed/edited evaluation contexts are rejected.
Company summaries also require one source history/currency policy, current end,
compatible flow window/assembly method and current reporting edition among
non-invalid results. Instant balances may accompany the matching flow end.
An invalid cell remains unavailable with its reasons; it cannot supply a value
or interpretation. Legitimate unavailable period wrappers preserve the underlying
missing/unsupported classification instead of becoming integrity failures.

## Neutral rules and three review items

`observations` emits source-linked measured revenue direction, negative operating/
consolidated income and CFO short of cash PPE purchases. Each record retains the
exact assessed metrics, dates/policies, rule ID and revision. It makes no causal
or investment-value claim; related metrics remain individually available.
`review_items` chooses at most three distinct topics, deterministically ordered
by data, cash, then operating observations and fixed rule/metric IDs. Related
negative earnings or FCF/margin signals share one item retaining every evidence
link. Stale/unavailable/inapplicable metrics permit data-review prompts only.
Extreme reported margins retain their true value plus a data-review prompt.
There is no universal healthy ratio, confidence score, buy/sell or bargain label.

`trends.py` accepts exactly three consecutive, comparable quarterly revenue YoY
assessments. The caller supplies a nonnegative fraction tolerance, revision and
evidence; the proposed 1 percentage point is only a synthetic test policy.
Both changes strictly above tolerance means rising; both strictly below its
negative means falling; both absolute changes at/below tolerance means broadly
stable; other eligible combinations are mixed. Negative growth can have a rising
rate; this does not mean revenue is growing. Changed context/profile/currency/
calendar, stale or edited values, gaps/duplicates and absent edition review block
the label. Sources use one pinned history context; arbitrary cross-snapshot trend
comparisons remain outside this boundary. Fiscal direct quarters are supported;
assembled-quarter trend projection is explicitly unsupported in this revision.

## Runtime balance-sheet reconciliation

`balance_sheet_identity` reuses the existing consolidated total assets, total
liabilities and equity INCLUDING NCI concepts. Same instant, edition, currency,
PIT policy and semantic scope are required. Residual = assets − liabilities −
equity; tolerance = sum of the three evidenced absolute uncertainties. Inclusive
absolute residual ≤ tolerance reconciles. A mismatch returns the true residual
and `balance_sheet_identity_mismatch`; it never repairs source values. Negative
consolidated equity remains valid; negative assets/liabilities do not. Parent or
common equity cannot substitute. Missing precision yields no reconciliation
claim. Bounded exact Decimal arithmetic preserves cancellation under hostile
ambient contexts. The calculation and each operand/precision record remain.

The future orchestrator must retain applicable accounting checks with the result
and respect their flags. This pure callable is not application integration.
Cash-change reconciliation and segment totals lack complete reviewed scope/
concept coverage; these checks remain explicit blockers, not guessed identities.

## Verification boundary

Tests were written first and initially failed on missing assessment,
reconciliation and trend modules. Hand-calculated fixtures include the supplied
−7,270% operating margin, −8m cash-PPE FCF / −8% margin, −12% revenue growth,
three-rate tolerance boundaries, 1/3 coverage and 1.5 reconciliation uncertainty.
Adversarial tests cover source omission, dates/deadlines, complete N/M, stale
N/M, unreviewed/inapplicable profiles, edited calculations/periods, unsupported
instruments, precision, issuer/currency/edition/period mismatch and Decimal traps.
No UI, shared schema, application data, approved provider or live source changed.

Independent review found one classification bug: using all company projection
eligibility flags as integrity errors changed missing annual amounts to invalid.
A regression reproduced it; only a reconstruction mismatch now constitutes that
integrity failure. The review also identified the company-summary selection
boundary; additional regressions and checks reject mixed currencies, current
windows, editions and history cutoffs. Review follow-up covers both repairs.
