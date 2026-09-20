# Sector Explorer implementation review

Baseline: `bd437db` (`milestone/s5-source-metrics`), implementation branch
`codex/sector-explorer`. Review includes tracked changes and all newly added
core, fixture, web and documentation files. This is the X1 calculation and
fictional-graph checkpoint, not production-universe/API acceptance.

## Numeric and standards review

The S5 period prerequisite was implemented and independently reviewed before
Sector Explorer implementation began: 167 core tests passed at that boundary.
Later integration review added two capex regressions and tightened the boundary.

Independent reviewers considered plausible but incorrect values, not only crashes:

| Finding | Resolution / verification |
| --- | --- |
| Negative reported PPE purchases could disappear inside a positive TTM sum, allowing FCF to look valid. | Two observed failing regressions cover a negative component and a negative YTD-derived quarter. Period assembly now preserves `negative_cash_ppe_capex` and returns no derived value. Review independently confirmed downstream FCF stays unavailable. |
| Median metadata exposed sum-of-ratios/count totals, which described a mean rather than the median. | Median numerator/denominator totals are unavailable; the value is the distribution's P50. A skewed 1/2/100 example distinguishes the methods. |
| A positive company denominator within source uncertainty could enter a median or mean. | Individual near-zero eligibility is checked before inclusion; the aggregate uses its separate summed uncertainty. |
| Aggregate growth could round current/prior to 1 before subtracting 1. | Compute the exact difference before dividing. Positive/negative tiny deltas survive extreme amount scales and hostile Decimal contexts. The existing company growth formula already used an exact difference. |
| Source fixture discarded industry parent IDs. | Preserve hierarchy metadata so industries appear through drilldown and are not mislabeled as sectors. |
| A distribution with one distinct company value had a zero-width bar. | Render a visible glyph at the actual value, retaining the closed single-value interval and company count. |
| Evidence heading called every roster snapshot a contributor; sign counts were ambiguous for margins. | Disclose roster snapshots including excluded issuers; identify the sign basis and zero-denominator count separately. |
| Fictional company snapshot identity omitted prior capitalization and profile/context fields. | Hash the full immutable company projection, including all evidence, applicable metrics and calculation context. |
| Whole-sector unsupported/stale causes were hidden by generic missing-input status. | Preserve issuer exclusion causes when projecting an unavailable sector status; add wholly unsupported/stale regressions. |
| SVG titles with multiple text children caused a React hydration mismatch. | Supply each title as a single complete string and recheck in the browser. |

The independent standards review confirms pure core modules, shared fundamentals
formulas, no browser financial arithmetic, explicit missing values and original
source evidence. The independent specification review covers source B052–B056.
The root separately reviews the sector engine and presentation behavior.

`EvidenceValue`, `CompanyMetric`, `CompanySnapshot` and history points are internal
trusted evaluated projections, not new normalized source facts or public API
contracts. Callers must establish source selection, approved profiles, freshness,
TTM comparability, complete roster and policy/context identities. Calendar-period
assembly supports exact calendar quarters/years; 52/53-week and transition years
remain unsupported. No common-income concept is inferred from consolidated income.

## Validation record

- Numeric tests were written and observed failing before each new numeric behavior
  or review repair. Source examples 150×/55× and 190→191 are hand-computed anchors.
- Focused tests cover same cohorts, losses/zeros/missingness, exact thresholds,
  unknown full capitalization, source basis/units/dates/precision, duplicates,
  profile failures, historical modes, concentration and frozen prior top-five sets.
- Presentation tests verify numeric pass-through, method/benchmark alignment,
  N/M and missing rows, low-coverage scatter suppression, gaps and histogram bins.
- Final verification passed: 950 full tests, 225 core tests, 110 golden tests,
  lint/types, production build and the desktop/mobile browser flow. Detailed
  evidence is in the milestone log. Mandatory checks also run through the
  unchanged commit hook.

## Acceptance that remains open

A fictional, immutable in-memory projection is not durable snapshot publication.
The normal `/sectors` route names the missing complete licensed universe/taxonomy,
common-income/capitalization, applicable profile/freshness policies and S6 snapshot
storage/API. Real-source spot checks, historical membership/filing reconstruction,
API-to-chart equality and saved-result reopen/failed-refresh behavior remain X1c/d.
The development context labels its backcast as current-members history and disables
historical-sector percentile claims. Fundamentals keeps 3/5/10-year options;
Sector Explorer uses separate 1/3/5-year line windows.
