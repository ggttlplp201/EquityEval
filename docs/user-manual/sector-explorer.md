# Sector Explorer: compare groups, then inspect companies

Status: development walkthrough using fictional companies and source evidence.
The ordinary `/sectors` page lists the real-data prerequisites. It does not report
market observations until approved sources and immutable result services exist.
This chapter was checked against the production-built development view on
2026-09-19; real-data product walkthrough acceptance remains X1d/U1.

## Open and read the graphs

Run `npm run dev --workspace @equity/web` from the project root and open
`http://127.0.0.1:3000/development/sectors`. The banner identifies fictional data.
Every displayed company, capitalization and financial figure in that route is a
verification fixture, including the historical observations. Never interpret the
fictional comparisons as current market research.

1. Choose the evaluation date, metric and calculation method. These controls
   select one dated result for the linked graphs and market reference.
2. Begin with the sector bars. **Sector total** combines amounts before division.
   **Median company** describes the middle eligible company. **Simple mean** is
   an advanced average of eligible company ratios, sensitive to extreme values.
   The same sector can have very different values under these methods.
3. Select a sector to inspect its company distribution and source details.
   Industry controls narrow the declared roster; they do not silently discard
   companies with unavailable metrics. Unclassified issuers remain visible.
4. Select up to four sectors in the history chart and choose one, three or five
   years. A gap means the observation is unavailable or failed its comparison
   gates. The chart does not fill missing quarters. Fundamentals keeps its
   separate three-, five- and ten-year history options.
5. Select a distribution bin to filter its company table. Search or pin a
   company, then open its evidence. The detail identifies the particular frozen
   company snapshot used in that calculation, not a newer observation.
6. Read growth versus valuation as two separate measurements. A point combines
   trailing P/E and trailing revenue growth from the selected date and method.
   Neither its position nor its color is a recommendation. Unavailable or
   insufficiently covered groups appear in the exclusion list rather than at zero.

Charts have accompanying tables or lists for keyboard access and exact values.
Source details show the formula, input totals, dates, coverage and exclusions.
The production interface will retrieve these records by immutable snapshot ID;
the development drawer verifies the same navigation using local fixtures.

## What the methods mean

| Term | Meaning |
| --- | --- |
| Trailing / TTM | The last twelve months of eligible reported financial periods, not next year's forecast. |
| Sector total P/E | Sum of eligible common-equity market capitalizations divided by the same companies' summed income available to common shareholders. Known losses stay in the denominator. |
| Median company P/E | The middle ratio among companies with a meaningful positive earnings denominator. Loss-making companies are excluded from this distribution and disclosed. |
| Simple mean P/E | Sum of those eligible company ratios divided by their count. Large ratios can dominate it. This is not a capitalization-weighted sector ratio. |
| P/S | Capitalization divided by revenue. Sector total uses sums over one matched cohort. |
| P/FCF | Capitalization divided by cash from operations minus cash purchases of property, plant and equipment. Negative FCF remains in sector totals; a nonpositive total denominator is N/M. |
| Operating margin | Operating income divided by revenue; negative margins are valid. Sector total divides summed amounts. |
| FCF margin | The same defined FCF divided by revenue. It does not describe cash available after every possible investment. |
| Revenue growth | Current TTM revenue divided by comparable prior-year TTM revenue, minus one. Sector total uses exactly the same company IDs in both sums and excludes nonpositive prior bases. |
| Growth breadth | Fraction of companies with valid growth observations whose revenue grew. Unchanged and declining companies stay in its denominator. |
| Profit / cash breadth | Fraction of companies with known applicable earnings / FCF amounts that are positive. Missing amounts never become losses. |
| P25 / P50 / P75 | Values at the 25th, 50th (median) and 75th percentiles of the eligible company distribution, using the documented interpolation method. They are not forecasts. |
| Concentration | The top five companies' share of complete sector capitalization on a stated date. Unknown full capitalization makes this unavailable. |
| Growth excluding top five | Growth after removing the same five companies ranked by **prior-date** capitalization from both current and prior revenue sums. It is different from current concentration. |

For three companies worth 100 each with earnings 10, 1 and −9, sector total P/E
is 300 / 2 = **150×**. The two profitable company P/Es are 10× and 100×, so their
median and mean are **55×**. Removing the loss from the sector total would give a
misleading answer. If total earnings were zero or negative, total P/E would be
**N/M**, not zero and not a negative valuation multiple.

Likewise, sector revenue can rise while most companies shrink. A matched cohort
moving from 190 to 191 has aggregate growth of about 0.53%; it can simultaneously
have −10% median company growth and only 10% growth breadth. Examine both the
aggregate result and its distribution.

## Coverage and unavailable results

- **N:** all issuers in the independently declared roster, including unsupported
  and missing companies. It is not just the companies the pipeline ingested.
- **K:** issuers with complete eligible inputs for the metric. A known zero or
  loss can count in K even when it cannot yield a company multiple.
- **V:** companies contributing to the selected calculation method.
- **Issuer coverage:** K/N. **Capitalization coverage:** contributing companies'
  cap divided by complete roster cap. If any required full-roster cap is unknown,
  capitalization coverage is unavailable; the known subset is not substituted.
- **Limited coverage:** a computed value can remain visible with its limitations,
  but cannot enter numerical ranks, scatter comparisons or summary conclusions.
- **N/M:** the requested ratio is not mathematically meaningful under its
  denominator rule. **Unavailable:** required data or evidence is missing,
  stale, incompatible or unsupported. Neither state means zero.

The development comparison policy is explicit: at least ten contributors,
70% issuer coverage and 80% capitalization coverage. All three gates must pass.
A small fully observed industry still has a small sample; displaying its number
is not permission to rank it. These are versioned verification policies, not a
claim that production source/applicability contracts have been approved.

Historical-sector comparisons require classifications effective and known at
each historical date, plus eligible company facts known then. A reconstruction
using today's constituents is labeled **Current members' history** and cannot
support historical-sector percentile claims. A historical interpretation needs
twelve eligible quarter ends across the documented three-year window. Equality
to P25 or P75 remains within the middle range.

## Real-data prerequisites

The project still needs an approved complete issuer roster, licensed dated
sector/industry assignments, common-shareholder earnings, complete multi-class
capitalization and reviewed point-date quote/action policies. It also needs the
S6 immutable company/sector snapshot and public API contracts. A watchlist alone
cannot stand in for the full U.S. sector universe. The development feature does
not activate a data provider or claim these prerequisites are satisfied.
