# S1 proposed concept map

Status: ready for human review; **no enum or normalization rule is approved**. The 40 names below retain the definitions in [concept-candidates.md](concept-candidates.md). The [coverage matrix](coverage-matrix.md) and [exact observations](evidence/concept-observations.json) show what the archived sources actually contain.

## Selection proposal

Match accounting regime, reporting entity/instrument, taxonomy/tag semantics, exact unit and period, accession and historical cutoff before considering tag priority. A company-specific rule is limited to its inspected filing era. It cannot recover a custom or dimensional fact omitted from Company Facts. Keep competing observations; disagreement raises a quality flag rather than choosing the first or largest value.

The names in each candidate cell are alternatives to inspect, not a universal ordered coalesce list. Prefer the explicitly reported complete scope over components, subject to filing evidence. If that scope cannot be established, return NULL with a quality flag in the later reviewed implementation. Source-reported zero remains zero. Never interpolate, carry a prior period forward, sum unrelated tags, or synthesize a missing raw subtotal.

Units are currency, currency per share or shares as defined in the catalogue. Actual API compound unit keys use forms such as `USD/shares` and `TWD/shares`; do not multiply API amounts again by a statement display scale. Exact fiscal intervals win over `fy`, `fp` or a calendar frame.

## Forty concepts and conditional candidates

Tags are prefixed `us-gaap:` or `ifrs-full:` by their column unless another prefix is explicit. Only qualified names found somewhere in the captured cohort are listed. An empty cell means no complete-scope candidate was observed. Historical presence is not anchor coverage; see each JSON candidate's present flag and rows.

| # / proposed concept | US GAAP candidates | IFRS candidates | Required condition / rejected fallback |
| --- | --- | --- | --- |
| 1. `revenue` | `RevenueFromContractWithCustomerExcludingAssessedTax`; `Revenues`; `SalesRevenueNet`; `RevenueFromContractWithCustomerIncludingAssessedTax`; `RevenuesNetOfInterestExpense` | `Revenue`; `RevenueFromContractsWithCustomers` | Use reported consolidated scope. CRCL: Revenues; customer-contract revenue is only a component. JPM: retain net-of-interest basis. COST: total revenue includes membership fees. No universal first-present rule. |
| 2. `cost_of_revenue` | `CostOfGoodsAndServicesSold`; `CostOfRevenue`; `CostOfGoodsSold` | `CostOfSales` | Reported sales cost only. Distribution expenses and bank interest expense are not interchangeable substitutes. |
| 3. `gross_profit` | `GrossProfit` | `GrossProfit` | Direct reported subtotal only; absent is not automatically revenue minus costs. |
| 4. `research_and_development_expense` | `ResearchAndDevelopmentExpense` | `ResearchAndDevelopmentExpense` | Expensed R&D; no capitalized development or acquired in-process substitute. |
| 5. `selling_general_and_administrative_expense` | `SellingGeneralAndAdministrativeExpense` | — | Combined SG&A only. Do not sum separate general/admin and sales/marketing tags during ingestion. |
| 6. `operating_expenses` | `OperatingExpenses` | `OperatingExpenseExcludingCostOfSales` | Excludes cost of revenue. CostsAndExpenses includes a broader scope and is not a fallback; bank noninterest expense needs separate interpretation. |
| 7. `operating_income` | `OperatingIncomeLoss` | `ProfitLossFromOperatingActivities` | Reported operating subtotal. Bank pretax income is not an equivalent. |
| 8. `interest_expense` | `InterestExpenseNonoperating`; `InterestExpense`; `InterestExpenseOperating` | `FinanceCosts` | Preserve operating/nonoperating/finance-cost scope. No net-interest, interest-paid, tax-penalty or component fallback. TSM FY2024 FinanceCosts is expensed interest after capitalization, confirmed by the FY2025 comparative note; preserve that basis. |
| 9. `pretax_income` | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest`; `IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments` | `ProfitLossBeforeTax` | Continuing-operation and equity-method treatment must match. Domestic/foreign components are not the total. |
| 10. `income_tax_expense` | `IncomeTaxExpenseBenefit` | `IncomeTaxExpenseContinuingOperations` | Retain tax benefit sign and continuing-operations scope; no cash-tax/current-tax fallback. |
| 11. `net_income_parent` | `NetIncomeLoss` | `ProfitLossAttributableToOwnersOfParent` | Parent-attributable earnings. NetIncomeLossAvailableToCommonStockholdersBasic is a different scope when preferred dividends exist. |
| 12. `net_income_consolidated` | `ProfitLoss` | `ProfitLoss` | Includes NCI. Do not silently reuse parent net income when this tag is absent, even if other companies report equal amounts. |
| 13. `eps_basic` | `EarningsPerShareBasic`; `EarningsPerShareBasicAndDiluted` | `BasicEarningsLossPerShare` | Exact source earnings period and share instrument. Combined basic/diluted needs filing confirmation. |
| 14. `eps_diluted` | `EarningsPerShareDiluted`; `EarningsPerShareBasicAndDiluted` | `DilutedEarningsLossPerShare` | Loss-period basic=diluted is valid, not a reason to manufacture dilution. Split-recast context retained. |
| 15. `weighted_average_shares_basic` | `WeightedAverageNumberOfSharesOutstandingBasic` | `WeightedAverageShares` | Duration shares, not current shares. Preserve class/ordinary-share scope. |
| 16. `weighted_average_shares_diluted` | `WeightedAverageNumberOfDilutedSharesOutstanding` | `AdjustedWeightedAverageShares` | Duration diluted denominator, not a fully diluted capitalization table. |
| 17. `common_shares_outstanding` | `CommonStockSharesOutstanding`; `dei:EntityCommonStockSharesOutstanding` | `dei:EntityCommonStockSharesOutstanding` | Period-end and cover-page dates remain distinct observations. Do not use shares issued or weighted averages; classes/ADS require instrument metadata. |
| 18. `cash_and_cash_equivalents` | `CashAndCashEquivalentsAtCarryingValue` | `CashAndCashEquivalents` | Corporate cash only. Combined restricted-cash/reserve balances are excluded; JPM tag is historical only at the selected anchor. |
| 19. `short_term_investments` | `ShortTermInvestments`; `MarketableSecuritiesCurrent` | — | Reported current investment subtotal with source instruments retained. Do not substitute total financial assets or cash-plus-investments. |
| 20. `accounts_receivable_net` | `AccountsReceivableNetCurrent`; `AccountsReceivableNet` | `CurrentTradeReceivables` | Trade/net/current scope must match. No gross loans or broader receivables fallback. |
| 21. `inventory_net` | `InventoryNet` | `Inventories` | Net carrying amount. Service/bank absence does not mean zero. |
| 22. `current_assets` | `AssetsCurrent` | `CurrentAssets` | Classified current balance only; banks may not report one. |
| 23. `property_plant_equipment_net` | `PropertyPlantAndEquipmentNet` | `PropertyPlantAndEquipment` | Reported carrying amount. Right-of-use scope needs retained filing context; no historical carry-forward. |
| 24. `goodwill` | `Goodwill` | — | Goodwill-only carrying amount; combined goodwill/intangibles is excluded. |
| 25. `intangible_assets_net_excluding_goodwill` | `IntangibleAssetsNetExcludingGoodwill` | — | Both finite and indefinite lives where applicable. FiniteLivedIntangibleAssetsNet alone is not a general substitute. |
| 26. `total_assets` | `Assets` | `Assets` | Consolidated assets; same entity/date/unit as identity check. |
| 27. `accounts_payable_current` | `AccountsPayableCurrent` | `TradeAndOtherCurrentPayablesToTradeSuppliers` | Trade/current scope; related-party or combined accrual amounts cannot be silently excluded or added. |
| 28. `current_debt` | — | — | Total current borrowing scope is required. LongTermDebtCurrent, CommercialPaper and ShortTermBorrowings are components, not universal fallbacks. Lease policy remains a review item. |
| 29. `long_term_debt_noncurrent` | `LongTermDebtNoncurrent` | — | Explicit noncurrent amount. LongTermDebt can include current maturities; TSM LongtermBorrowings excludes separate bond amounts. No component aggregation here. |
| 30. `current_liabilities` | `LiabilitiesCurrent` | `CurrentLiabilities` | Classified total current liabilities only. |
| 31. `total_liabilities` | `Liabilities` | `Liabilities` | Direct reported total. No Assets minus Equity normalization; LiabilitiesAndStockholdersEquity is not liabilities. |
| 32. `equity_parent` | `StockholdersEquity` | `EquityAttributableToOwnersOfParent` | Parent equity; preserve temporary/redeemable equity distinctions. |
| 33. `equity_including_noncontrolling_interests` | `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` | `Equity` | Consolidated permanent equity; no parent-only fallback on missing NCI. |
| 34. `noncontrolling_interests` | `MinorityInterest` | `NoncontrollingInterests` | NCI equity carrying amount, not NCI earnings/comprehensive income/redeemable interests. |
| 35. `cash_from_operating_activities` | `NetCashProvidedByUsedInOperatingActivities` | `CashFlowsFromUsedInOperatingActivities` | Exact annual/YTD interval and cash-flow sign. Reporting-framework interest/dividend classifications retained. |
| 36. `capital_expenditures_ppe` | `PaymentsToAcquirePropertyPlantAndEquipment` | `PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` | Cash paid for PP&E. No acquisition, accrued capex, finance-lease addition or broad capital-investment substitute. |
| 37. `depreciation_and_amortization` | `DepreciationDepletionAndAmortization`; `DepreciationAndAmortization` | — | Combined reported amount; retain depletion/asset scope. Depreciation alone, impairments or accretion are not equivalent; no component sum. |
| 38. `share_based_compensation` | `ShareBasedCompensation`; `AllocatedShareBasedCompensationExpense` | `AdjustmentsForSharebasedPayments`; `ExpenseFromSharebasedPaymentTransactionsInWhichGoodsOrServicesReceivedDidNotQualifyForRecognitionAsAssets` | Recommend narrowing to reported cash-flow addback for P0; expensed/allocated values stay scope-qualified. TSM candidates differ. No net-of-tax or award-value fallback. |
| 39. `dividends_paid` | `PaymentsOfDividends`; `PaymentsOfDividendsCommonStock` | `DividendsPaidClassifiedAsFinancingActivities`; `DividendsPaid` | Use actual cash-flow payments with instrument scope retained. For TSM FY2024, select DividendsPaidClassifiedAsFinancingActivities; exclude DividendsPaid (equity appropriation), as confirmed in the later comparative filing. |
| 40. `share_repurchases` | `PaymentsForRepurchaseOfCommonStock` | — | Common repurchase cash payment; do not include withholding, authorizations, equity movement, unsettled amounts or inferred zero. |

## Company-specific rules proposed for review

| Company | Proposal | Evidence |
| --- | --- | --- |
| AAPL | Use current customer-contract revenue; explicit noncurrent debt excludes current maturities. Current debt lacks a single complete candidate here; do not silently use the term-debt current portion alone. Preserve year-end versus cover-date shares. | [Baseline notes](baseline-observations.md) |
| MSFT | No combined SG&A fallback from two expenses. Missing Company Facts combined D&A/intangibles require original-filing context, not an arithmetic patch. | [Baseline notes](baseline-observations.md) |
| JPM | Revenue is net of operating interest expense. Treat banking applicability separately from industrial FCFF ratios; do not use stale generic cash/PP&E/interest tags. | [Sector notes](special-sector-observations.md) |
| CRCL | Prefer reported total Revenues over customer-contract revenue for the total revenue concept; keep reserve income identified. Corporate cash excludes stablecoin holder reserves. Explicit repurchase zero is valid; missing dividends remains missing. | [Sector notes](special-sector-observations.md) |
| RBLX | CostsAndExpenses includes cost of revenue and is not the proposed operating_expenses scope. Preserve parent/consolidated earnings, anti-dilution and stock-class gaps. | [Baseline notes](baseline-observations.md) |
| TSM | Do not use FY2024 financial facts as FY2025. Preserve TWD, ordinary-share EPS and ADS identity; partial borrowing and expense tags are not complete totals. | [IFRS notes](ifrs-and-restatement-observations.md) |
| KHC | Keep accession-specific original and restated rows. Do not equate all later differences with error corrections; separate pension recast and non-reliance timing. | [Restatement notes](restatement-khc.md), [raw-row audit](ifrs-and-restatement-observations.md) |
| COST | Consolidated total revenue includes membership fees. Do not substitute net sales. Keep 52/53-week dates, direct reported cash dividends and source SBC before tax. | [Baseline notes](baseline-observations.md) |

## Proposed S2 boundary

Use these 40 names as the initial vocabulary, subject to the explicit scope refinements in the review brief. This is not a promise that all concepts are available for all companies. Defer original-filing extraction to a separately tested adapter; record missing/stale/ambiguous observations and report unsupported company/model combinations explicitly. Banks and stablecoin reserve models must not silently enter a generic industrial FCFF model.

Additional concepts needed for debt components, cash-flow reconciliation, common-share income, lease scope or sector models require their own reviewed additions. Do not stretch these names to satisfy a downstream formula.
