# Candidate concept catalogue — 40 entries

Status: accepted as the starting vocabulary for S2 on 2026-09-12. No concept_std
enum or normalization adapter has been implemented. Exact tag observations, conditional rules
and gaps are in [concept-map.md](concept-map.md) and the
[coverage matrix](coverage-matrix.md).

Each observation retains original taxonomy/tag, unit, exact period, filing
accession/date, retrieval evidence and source value. Normalized names cannot
erase differences in economic scope.

| # | Proposed concept | Period and unit | Definition / mapping hazard |
| --- | --- | --- | --- |
| 1 | `revenue` | Duration; reporting currency | Reported consolidated revenue; preserve bank and reserve-income distinctions. |
| 2 | `cost_of_revenue` | Duration; reporting currency | Reported cost of revenue/sales. Do not manufacture a subtotal from unrelated expense tags. |
| 3 | `gross_profit` | Duration; reporting currency | Reported gross profit. A derived gross profit would need a separately reviewed transform. |
| 4 | `research_and_development_expense` | Duration; reporting currency | Expensed R&D; distinguish capitalized development costs and acquired in-process R&D. |
| 5 | `selling_general_and_administrative_expense` | Duration; reporting currency | Combined SG&A only when the source actually reports that scope. |
| 6 | `operating_expenses` | Duration; reporting currency | Operating expenses as defined by the filing; do not interchange with total costs including cost of sales. |
| 7 | `operating_income` | Duration; reporting currency | Reported operating income/loss; not automatically EBIT where scope differs. |
| 8 | `interest_expense` | Duration; reporting currency | Separate expense from net interest and capitalized interest; bank economics need a separate treatment. |
| 9 | `pretax_income` | Duration; reporting currency | Income before tax; preserve continuing/discontinued-operation and ownership scope. |
| 10 | `income_tax_expense` | Duration; reporting currency | Tax expense or benefit, retaining source sign; distinguish current cash tax from total expense. |
| 11 | `net_income_parent` | Duration; reporting currency | Income attributable to the parent; distinguish income available to common shareholders after preferred dividends. |
| 12 | `net_income_consolidated` | Duration; reporting currency | Income including noncontrolling interests; never silently substitute parent-only income. |
| 13 | `eps_basic` | Duration; currency per share | Reported basic EPS with matching earnings and weighted-average share scope. |
| 14 | `eps_diluted` | Duration; currency per share | Reported diluted EPS; retain loss-period anti-dilution and split-recast context. |
| 15 | `weighted_average_shares_basic` | Duration; shares | Weighted-average basic shares for the exact earnings period; not a balance-sheet instant. |
| 16 | `weighted_average_shares_diluted` | Duration; shares | Diluted weighted-average shares; not the current fully diluted capital structure. |
| 17 | `common_shares_outstanding` | Instant; shares | Point-date ordinary/common shares with class and instrument identity; cover-page and period-end dates differ. |
| 18 | `cash_and_cash_equivalents` | Instant; reporting currency | Corporate cash/equivalents; do not combine with restricted cash or stablecoin holder reserves. |
| 19 | `short_term_investments` | Instant; reporting currency | Reported current investments; instruments and cash-equivalent exclusions need review. |
| 20 | `accounts_receivable_net` | Instant; reporting currency | Net trade receivables; distinguish loans, non-trade balances and gross/allowance presentations. |
| 21 | `inventory_net` | Instant; reporting currency | Net inventory; no zero substitution for banks/services that do not report inventory. |
| 22 | `current_assets` | Instant; reporting currency | Reported classified current assets; unclassified financial balance sheets may have no equivalent. |
| 23 | `property_plant_equipment_net` | Instant; reporting currency | Net PP&E; keep right-of-use assets and investment property separate unless source scope includes them. |
| 24 | `goodwill` | Instant; reporting currency | Carrying amount of goodwill; never net it against unrelated acquisition balances. |
| 25 | `intangible_assets_net_excluding_goodwill` | Instant; reporting currency | Net recognized intangibles excluding goodwill; finite/indefinite-life scope must match. |
| 26 | `total_assets` | Instant; reporting currency | Consolidated assets for the chosen reporting entity and date. |
| 27 | `accounts_payable_current` | Instant; reporting currency | Current trade payables; do not substitute a combined payable/accrual tag without reviewed scope. |
| 28 | `current_debt` | Instant; reporting currency | Current borrowings including relevant maturities only when coverage is explicit; lease treatment unresolved. |
| 29 | `long_term_debt_noncurrent` | Instant; reporting currency | Noncurrent borrowings; distinguish debt including current maturities and leases. |
| 30 | `current_liabilities` | Instant; reporting currency | Reported classified current liabilities; absent classification remains a gap. |
| 31 | `total_liabilities` | Instant; reporting currency | Consolidated liabilities; neither liabilities-plus-equity nor derived subtraction is a raw fact. |
| 32 | `equity_parent` | Instant; reporting currency | Equity attributable to parent shareholders; distinguish redeemable temporary equity. |
| 33 | `equity_including_noncontrolling_interests` | Instant; reporting currency | Total consolidated equity including noncontrolling interests, when reported. |
| 34 | `noncontrolling_interests` | Instant; reporting currency | Noncontrolling equity carrying amount; do not confuse with minority income or redeemable interests. |
| 35 | `cash_from_operating_activities` | Duration; reporting currency | Reported operating cash flow with retained sign and exact YTD/annual interval. |
| 36 | `capital_expenditures_ppe` | Duration; reporting currency | Cash paid for PP&E; distinguish acquisitions, finance leases and unpaid additions. |
| 37 | `depreciation_and_amortization` | Duration; reporting currency | Reported combined D&A with scope; depreciation-only is not an equivalent mapping. |
| 38 | `share_based_compensation` | Duration; reporting currency | Proposed P0 scope: reported noncash cash-flow SBC addback. Income-statement expense, capitalized amounts, grants and award fair values are distinct. |
| 39 | `dividends_paid` | Duration; reporting currency | Cash dividends paid; common-only versus all equity instruments needs explicit source scope. |
| 40 | `share_repurchases` | Duration; reporting currency | Cash spent repurchasing common shares; separate withheld shares, excise taxes and unsettled obligations. |


## Boundaries of this first catalogue

This is a starting set for source research, not a promise that every planned
ratio is computable. Cash-flow reconciliation also needs investing/financing
cash flows, FX effects, restricted-cash reconciliation and total cash change.
Lease liabilities, income available to common shareholders, debt instrument
splits, incremental invested capital, adjusted EPS and bank-specific metrics may
need further concepts after evidence review. They must not be synthesized into
raw facts to satisfy an arbitrary catalogue size.

Ratios, enterprise value, free cash flow, NOPAT, net debt, TTM and effective tax
rates are derived outputs or transforms, not additional ingested facts. Their
formula and missing-input policies belong in the later reviewed contracts.

## Evidence required for each proposed mapping

- Identify the company, saved payload checksum, namespace/tag and source label.
- Select an exact unit, interval/instant and filing accession; inspect all
  competing rows rather than choosing a value simply because it is newest.
- Compare the filing's statement scope and unit scale with the raw API value.
- Mark results as observed, ambiguous, absent in the inspected scope, or requiring
  original-filing extraction. An absent tag does not imply a zero balance.
- Record any proposed override with the evidence and rationale for review.
- Keep reported values separate from any proposed period arithmetic or conversion.

The S1 starting vocabulary was accepted for S2 on 2026-09-12. Enum implementation
follows the reviewed S2 shape; future additions or scope changes require explicit
review as the sources reveal further distinctions.
