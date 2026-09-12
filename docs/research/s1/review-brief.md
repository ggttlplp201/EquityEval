# S1 — decisions for review

Research completed 2026-09-12. This is the review gate required by
BUILD_GUIDE Part 5, S1. Approval would accept the starting financial vocabulary
and source-handling direction for the S2 design; the actual schema remains a
separate review before implementation.

## Recommended decision

Approve the [40 proposed concepts](concept-map.md) as the initial vocabulary,
with their explicit scopes and the following rules:

1. A number must match the entity/share instrument, accounting basis, source tag,
   unit, actual period and filing version. Dates, class identity and raw provenance
   are retained. A newer filing's `fy` is not the year of every comparative fact.
2. Use only a directly reported observation of the intended scope. Missing,
   stale, conflicting or incompatible observations stay unavailable with a
   quality explanation. Reported zero stays zero. No synthesized raw subtotal,
   guessed value or prior-period carry-forward.
3. Keep scope variants explicit: parent versus consolidated earnings/equity;
   ordinary versus ADS/class shares; noncurrent debt versus all maturities;
   corporate cash versus restricted/holder reserves. For P0 SBC, use the reported
   noncash cash-flow addback; the income-statement expense is a different scope.
   Cash dividends must be actual cash-flow payments with instrument scope retained.
4. Correct the original spec's source assumption: Company Facts is the first
   adapter, with explicit coverage gaps. Original-filing extraction is a separate
   S3 slice with context/scale tests, not an automatic tag fallback. Display the
   available facts and withhold dependent outputs if essential inputs are missing.
   Banks and stablecoin reserve models need explicit model applicability decisions.

This starting set does not make every valuation computable. Current-debt totals,
complete D&A, classified bank working capital and some company-year facts are
not covered by the inspected complete-scope candidates. Add reviewed component
concepts or source extraction when required; do not stretch the definitions.

## Evidence behind the recommendations

| Finding | What would otherwise go wrong |
| --- | --- |
| CRCL total revenue is $2.747bn; customer-contract revenue is $109.820m. | A universal customer-contract-tag priority would omit most revenue. |
| CRCL holder reserves are distinct from corporate cash. | Treating reserves as shareholder cash would distort enterprise value. |
| TSM FY2025 financial facts are absent from the captured Company Facts response. | A latest-available fallback would silently present FY2024 as FY2025. |
| MSFT cash-flow D&A includes “other”; JPM PP&E includes lease assets. | Similar tag names would create plausible but incompatible values. |
| KHC FY2017 parent income changes from $10.999bn to $10.941bn in a later filing. | Replacing history would leak future information into historical analysis. |

The [coverage matrix](coverage-matrix.md), company notes and exact source rows
support these observations. Five manually specified filing-to-API spot checks
agree; this does not claim complete normalized golden fixtures or a working
point-in-time database.

## What follows approval

S2 will propose identifiers, source/filing/retrieval versions, period/unit/share
scope, quality flags and point-in-time query behavior. It will also accommodate
the newly requested [US macro/watchlist agent](../../features/N1-news-and-macro-agent.md)
and its in-app, desktop and email delivery records. Those schema/API decisions
will be concrete and reviewable before code is written.

Still open for S2: date-cutoff timezone/inclusivity; handling non-reliance events
and retrieval vintages; current-debt/lease components; exact representation of
scope and quality information. S1 approval does not silently settle these.
