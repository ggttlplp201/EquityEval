# Why did this change? — design and acceptance packet

Status: proposed design and future implementation acceptance, 2026-09-19.
This document delivers the interaction, mathematical boundaries and test cases.
It does **not** implement a calculation, publish a contract or claim that the
numeric tests below have been executed. No provider activation is required.

This refines [F1 fundamentals](../../features/F1-fundamentals-guide.md) and
[X1 Sector Explorer](../../features/X1-sector-explorer.md). Preserve their existing
calculations, graph interactions, source tracking, applicability exclusions and
3/5/10-year company history choices. It does not replace valuation, the watchlist,
news/macro monitoring or the existing assumptions/thesis design.

The requested small real-data pilot covers **CRCL, MSTR, COIN, HOOD, USAR, MP and
GOOGL**. Review evidence and business/instrument applicability for all seven;
missing or unsupported results are valid pilot findings. Existing MSFT/RBLX
archives remain regression evidence, not the prioritized user pilot. The ticker
list does not prove instrument identity, current business classification or a
usable source mapping. Those need the existing reviewed resolution process.

## Delivery sequence and boundaries

1. Incorporate this workflow into the Figma redesign and review it alongside the
   existing feature-preservation checklist. Application implementation remains
   behind the UI-redesign-first sequence in [D1](../../milestones/D1-design-handover.md).
2. Complete the bounded SEC source-to-core pilot, retaining original precision,
   compatible periods and pinned source evidence. Preserve gaps instead of using
   a different company's complete data to imply coverage of the requested seven.
3. Implement the first supported pure-core explanation using an eligible annual
   operating-margin pair, where its business profile and inputs support that
   metric. GOOGL is a candidate to investigate, not a declaration of validated
   eligibility. Other annual gross/net margin pairs can follow the same pattern.
4. Review result publication and immutable comparison identity through the
   existing S6/F1/X1 shared-contract process before wiring production screens.
   Company price/EPS, verified EPS/share bridges and sector composition attribution
   retain their additional prerequisites below.

The first future numeric slice is internal, pure Python in `packages/core`:
no I/O, database migration, normalized concept, source activation or public API.
Preserve `Decimal | None` and evidence-bearing flags. This packet does not settle
schema shape, field names, persistent statuses or an endpoint contract.

## User workflow

Provide **Why did this change?** from a company ratio row, a pair of history
observations and relevant sector graph/table observations. The action opens a
keyboard-accessible comparison panel; it preserves the selected chart context
and does not silently navigate to a mutable latest company record.

1. **Choose the comparison.** Show the two immutable snapshots/observations,
   metric, method, periods or quote dates, history mode, business-profile version,
   source cutoffs and the selected universe where relevant. Default to an
   explicit previous comparable observation only when one exists. Otherwise let
   the user select a supported comparison or explain what is missing.
2. **Identify what changed.** Distinguish a new reporting period, a revision of
   the same period, newly available data, a changed assumption, a changed profile,
   a changed formula and a changed universe/method. These are different changes;
   none should be silently described as business performance.
3. **Show the mathematical explanation.** Display both endpoint amounts and
   ratios, signed contributions, the net change and the named attribution method.
   A compact waterfall may help, but include an accessible numerical table.
   Use percentage points for margin changes, multiple turns for P/E and currency
   per share for EPS. Every amount and contribution opens its exact evidence.
4. **Inspect related observations.** Link any cross-metric observation to the
   underlying periods, figures, source snapshots and applicability rules. For
   example, “Operating margin fell 5 percentage points while revenue increased”
   is a measured relationship, not proof that prices, demand or costs caused it.
5. **Inspect possible business explanations.** Keep these separate from the
   arithmetic. Show supporting filing/news evidence, who made an attribution,
   alternative explanations, counterevidence, uncertainty and what further
   evidence would distinguish the alternatives. “Insufficient evidence” is a
   complete state. A company statement remains management's attribution unless
   independently substantiated.
6. **Continue research.** Let the future thesis-continuity workflow reference the
   comparison and its evidence. A suggested interpretation must not edit source
   facts, saved calculations or the user's assumptions/thesis automatically.

The numerical explanation and neutral rule-based observations work without AI.
An optional later AI explanation consumes the frozen evidence and applicable
rules; it cannot invent a cause or overwrite authoritative records. Do not imply
that an unavailable AI service prevents access to facts, math or source links.

## Reuse and missing components

| Existing component | Reuse and boundary |
| --- | --- |
| [FinancialInput and precision evidence](../../../packages/core/inputs.py) | Exact selected source context, lineage, original precision and blocking flags. |
| [Calculation and margin functions](../../../packages/core/metrics.py) | Verified endpoint calculations, exact operands, formula revision, source/period/scope/unit checks and local Decimal arithmetic. |
| [Period assembly](../../../packages/core/periods.py) | Existing eligible annual, quarter and TTM transformations with retained source operands. Unsupported fiscal calendars stay unsupported. |
| [History math](../../../packages/core/history.py) | Comparable series identity, 3/5/10-year windows, evidence-bearing samples and explicit gaps; currently no change decomposition. |
| [Company evidence and multiples](../../../packages/core/company.py) | Reproducible hashes and cap/common-income multiples. This is not an implemented price/diluted-EPS calculation. |
| [Sector calculations](../../../packages/core/sectors.py) | Aggregate numerator/denominator totals, method, constituents, cohort identity, coverage and exclusions. |
| [Sector contract proposal](../sector-explorer/contract-proposal.md) | Frozen result selection, provenance, constituent snapshot drilldown and shared-contract gates. |

There is no implemented ratio-change attribution, verified price/EPS attribution
or diluted-EPS earnings/share bridge in these modules. No generalized business
cause engine is implied by existing source calculations.

## Proposed two-point numerical convention

For an eligible ratio `R = N / D`, let the earlier endpoint be `N0 / D0` and the
later endpoint be `N1 / D1`. Propose a symmetric allocation that averages the two
possible orders of updating numerator and denominator:

```text
numerator contribution   = (N1 - N0) / 2 * (1 / D0 + 1 / D1)
denominator contribution = (N0 + N1) / 2 * (1 / D1 - 1 / D0)
net change               = N1 / D1 - N0 / D0
```

In exact arithmetic, the two contributions sum to the net change. Name the
convention **Average of the two update orders** and version it. It allocates the
interaction symmetrically; it does not establish a causal business mechanism.
Calling a component an “effect” must not imply a causal estimate.

Keep signed contributions in ratio units. In particular, do not divide them by
a zero or tiny net change to claim a percentage of the explanation. Offsetting
contributions can be useful even when the endpoint ratio is unchanged. There is
no automatic investment judgment associated with a higher or lower ratio.

### Input and precision validity

- Recompute or verify both endpoint calculations using the existing metric rules.
  Do not decompose arbitrary UI numbers or evidence records that fail to reproduce
  their purported endpoint calculation and input hashes.
- Require finite numeric inputs and positive denominators distinguishable from
  zero at their original evidenced precision at both endpoints. Unknown precision
  must not be inferred from JSON digits or formatted display values.
- Preserve negative and zero margin numerators. A loss can be an eligible amount;
  it is not a missing input and must not be removed to improve a presentation.
- Match issuer/instrument, currency, accounting basis, metric definition,
  consolidation/ownership scope, formula revision and supported comparable period
  lengths. Do not silently compare quarter with annual, reported with adjusted,
  basic with diluted, or incompatible fiscal calendars.
- First implementation: comparable annual periods selected under one pinned
  source/history policy. `FinancialInput.history_key` includes cutoffs; do not
  bypass a mismatch to enable arbitrary cross-snapshot comparison. A later
  reviewed comparison boundary can identify intentionally different cutoffs while
  preserving each endpoint's own evidence.
- A revised same-period amount is a **revision comparison**, not a new period's
  growth. Changes of formula, profile or assumption have their own comparison
  explanations and cannot masquerade as changes in reported facts.
- Reuse the local Decimal context and numeric-range safeguards. Test endpoint
  reconstruction against a documented computational rounding bound. This bound
  is distinct from reported source uncertainty. Do not silently assign numerical
  rounding residuals to one contribution, round operands before calculation, or
  produce a plausible zero/infinity on unsupported magnitudes.
- Freeze the two endpoint identities, all operand/source references, applicable
  policies and formula revision in the internal result or its retained inputs.
  Public/persistent representation remains a shared-contract review item.
- Ineligible input produces no decomposition value and retains its existing
  evidence/flags. The presentation distinguishes missing, unsupported, not
  applicable and not meaningful without changing storage missingness semantics.

### P/E: price versus EPS is a different basis from cap versus earnings

A price/EPS bridge needs an eligible raw close and verified diluted EPS on the
same instrument, currency, split/ADS basis and reviewed quote session. Positive,
precision-distinguishable EPS is required at both endpoints. Dividend-adjusted
or total-return prices cannot substitute for the required price basis. F1/S4b
price, calendar and corporate-action gates remain in force.

The current company/sector P/E is complete common-equity market capitalization
divided by income available to common. A bridge on those inputs is labelled
**Capitalization versus common earnings**. Capitalization can change through
share counts, share classes and corporate actions as well as quoted prices.
Do not label its numerator contribution a pure price contribution.

Period-end ownership shares and weighted-average diluted shares are not
interchangeable. Cap/common-income and price/diluted-EPS multiples therefore
cannot be silently equated. A profit-to-loss transition makes P/E N/M; retain
the earnings change and describe the transition without fabricating a negative
multiple or a numerical P/E change to an unavailable endpoint.

### EPS: earnings and share-count attribution needs a verified identity

Require the filing's matching attributable-earnings numerator and weighted-average
share denominator for the exact reported EPS basis. Consolidated or parent net
income is not automatically that numerator. Diluted EPS may involve numerator
adjustments, two-class allocations and anti-dilution treatment.

The source reconciliation must support the identity, and the recomputed ratio
must agree within the source's stated precision. A coincidental arithmetic match
alone is insufficient evidence of compatible meaning. If the identity is not
reviewed, retain reported EPS and share observations separately and show
**Attribution unsupported for these inputs**.

Do not substitute period-end shares, combine basic and diluted inputs, blindly
sum quarterly EPS into TTM, infer a split from the numbers, or label SBC expense
as dilution. Any zero/loss EPS growth label continues to follow F1's existing
rules; an earnings/share amount bridge does not authorize a growth percentage.

## Sector comparisons and composition changes

For eligible **Sector total** ratios, the same convention can later operate on
sums over one explicit, identical eligible issuer cohort at both endpoints.
Preserve common-income losses, aggregate precision rules, source dates and the
existing coverage/comparison gates. A nonpositive aggregate denominator is N/M.

An unchanged sector label does not prove an unchanged comparable population.
Check dated universe/membership, taxonomy, business-profile/applicability rules,
contributor identities, coverage and accounting/method definitions. Display
changes to these before attributing an apparent change to operating performance.
Even identical roster IDs are insufficient if different companies contribute
usable inputs at the two dates.

Do not silently switch to an intersection to make the bridge work. A future
matched-cohort comparison needs its own explicit cohort, exclusions and coverage,
and must be distinguished from the published all-members result. A broader
composition/performance decomposition is separate future work with reviewed
ordering and reconciliation rules.

**Median company** and **simple mean company** ratios are not ratios of sector
numerator/denominator totals. The first release must not reuse the aggregate
bridge for those methods. It can show endpoint values, eligibility/population
changes and constituent evidence while stating that attribution for this method
is unsupported. A change of selected method is a method comparison, not a
historical performance move.

Preserve all four X1 graphs, the aggregate-versus-median distinction, small-sample
labels, full-roster coverage and existing 10/70%/80% comparison policy. A small
watchlist remains **Selected companies**, not a full sector. Business-model
composition and suitable-cohort selection add context without erasing excluded
companies or relaxing gates to obtain a result.

## Hand-computed acceptance cases

These cases specify future tests. They are not executed test results and synthetic
inputs do not approve a production source, profile or normalized concept.

| Case | Endpoints | Expected contributions and result |
| --- | --- | --- |
| P/E price and EPS both change | Price 60→90; EPS 3→6 | P/E 20×→15×; price +7.5×; EPS −12.5×; net −5×. No inference about why either input changed. |
| Operating margin | Income 20→30; revenue 100→200 | 20%→15%; income +7.5 percentage points; revenue −12.5 points; net −5 points. |
| Loss margin | Income −20→−10; revenue 100→200 | −20%→−5%; income +7.5 points; revenue +7.5 points; net +15 points. Retain the loss facts. |
| Offsetting contributions | Numerator 10→20; denominator 100→200 | 10%→10%; +7.5 and −7.5 points; net zero. Never divide the components by net change. |
| Verified EPS identity, synthetic only | Attributable earnings 100→200; matching weighted shares 50→100 | EPS 2→2; earnings +1.5 per share; share count −1.5 per share. |
| Numerator only | Income 20→30; revenue unchanged at 100 | Margin +10 points; numerator +10 points; denominator zero. |
| Identical inputs | Income 20→20; revenue 100→100 | Both contributions and net change zero. |
| Undefined endpoint | Required denominator missing, zero, negative, or no greater than its original absolute error | No numerical bridge; preserved source amounts and explicit reasons. |
| P/E profit to loss | Price 60 unchanged; EPS 3→−1 | 20×→N/M; earnings amount transition remains visible; no numeric P/E bridge. |
| Same-period revised facts | Same period, old and revised filing values | Revision comparison label; never describe as new-period operating growth. |
| Sector contributors change | New, removed or newly ineligible contributor | Ordinary aggregate bridge unavailable; show cohort/coverage changes. |
| Sector method changes | Sector total→median company | Method comparison; no ordinary two-factor bridge. |

### Future red/green verification

1. Add meaningful tests before numeric implementation: the hand-computed valid
   cases above, existing source fixture lineage, and the ineligible cases below.
   Record the expected failure of missing new behavior; do not count a test that
   already passes through the old endpoint calculator as evidence of a new bridge.
2. Implement only the eligible internal annual-margin slice. Keep unsupported
   P/E/EPS and sector-method cases explicit instead of adding placeholder math.
3. Verify contribution sum versus endpoint delta, endpoint reversal, one-operand
   changes, zero-net offsetting changes, negative numerator and unchanged inputs.
   Use exact simple examples plus a documented rounding oracle for repeating
   divisions; do not test only rounded display values.
4. Reject mismatched source editions/policies, currencies, periods, scope,
   instrument/share bases, formula/profile definitions, false endpoint hashes,
   absent precision, nonfinite values and unsupported numeric magnitudes. Assert
   exact source references remain attached on both success and failure.
5. Test independence from caller Decimal precision/rounding and that source
   uncertainty is not confused with computational error tolerance. Test sector
   cohort/method shifts separately before any later sector bridge is enabled.
6. Run the repository's required core/full checks and independent numerical
   review before a numeric commit. Focus review on plausible but incorrect
   results. This documentation-only delivery adds no code and claims none of
   those future checks as completed.

## Design acceptance before dependent implementation

- Company and relevant sector entry points exist, with keyboard access and an
  accessible contribution table rather than hover-only explanations.
- Both endpoint contexts, method, units, dates and source actions remain visible.
- The mathematical explanation works without AI and remains visibly separate
  from sourced business interpretation and user-authored research expectations.
- Missing, unsupported, N/M, revision, profile-change and cohort-change examples
  are represented; incomplete evidence does not become a negative company score.
- No ratio correlation is presented as a proven business cause; alternatives and
  uncertainty have a clear place even when no narrative conclusion is supported.
- Existing source drawers, immutable snapshots, sector methods/coverage and
  3/5/10-year company history controls remain preserved.
