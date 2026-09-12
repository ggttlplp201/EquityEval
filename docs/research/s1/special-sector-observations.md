# S1 special-sector observations: JPM and CRCL

Status: evidence-only candidate observations, 2026-09-11. This document does not approve concept members, mapping priority, company overrides, missing-data contracts, or valuation eligibility. No production code or normalization was run.

## Evidence and selection

Only the two archived Company Facts payloads in [the manifest](evidence/manifest.json) were inspected locally. SHA-256 is checked against the decompressed original response. No network requests were made for this audit. Source labels below are API taxonomy labels, not verified issuer presentation labels. Raw filings and custom/dimensional contexts remain a separate evidence requirement.

All 40 concepts in [the proposed catalogue](concept-candidates.md) are inspected for each company. Candidate tags are an explicit search set, not an exhaustive assertion that no other tag can represent the concept. **A** means a row exists for the exact pinned accession and period; it does not establish economic equivalence. **H** means the tag exists but has no exact anchor row (an illustrative latest-period row is shown). **O** means a row in the anchor accession has a different date/interval. **Absent** means the exact tag does not exist anywhere in this saved payload. No absence becomes zero.

Rows 1–16 and 35–40 use duration **D = 2025-01-01 through 2025-12-31**; rows 17–34 use instant **I = 2025-12-31**. All A observations retain those periods and the accession/filed date shown in the company section. Values are original API units, not display millions. H and O observations show their own full metadata.

## JPM: FY2025 anchor

- Accession: `0001628280-26-008131`; form: `10-K`; filed: `2026-02-13`; fiscal focus: `2025 / FY`.
- Source: [JPM Company Facts](https://data.sec.gov/api/xbrl/companyfacts/CIK0000019617.json).
- Archived response: [raw/JPM-20260911T141423209446Z.json.gz](evidence/raw/JPM-20260911T141423209446Z.json.gz); fetched at `2026-09-11T14:14:23.209446+00:00`.
- Raw-response SHA-256: `e43e1ce75230d81dc20399e0466b13f856103fe7fc4b2bbedde7ea75018326ac`.

| # / proposed concept | Observed exact tags and values / explicit gaps | Scope observation |
| --- | --- | --- |
| 1 / `revenue` | A `us-gaap:Revenues` (Revenues): **182,447,000,000 USD**, D<br>A `us-gaap:RevenuesNetOfInterestExpense` (Revenues, Net of Interest Expense): **182,447,000,000 USD**, D<br>Absent: `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` | Both reported tags are net of interest expense in this anchor; do not subtract interest again when constructing bank revenue. |
| 2 / `cost_of_revenue` | Absent: `us-gaap:CostOfRevenue`, `us-gaap:CostOfGoodsAndServicesSold`, `us-gaap:CostOfGoodsSold` | No inspected cost-of-sales tag; interest expense and credit-loss provisions are not a substitute. |
| 3 / `gross_profit` | Absent: `us-gaap:GrossProfit` | No reported gross-profit candidate; do not invent a gross margin. |
| 4 / `research_and_development_expense` | Absent: `us-gaap:ResearchAndDevelopmentExpense` | No inspected R&D expense candidate; technology costs are not the same scope. |
| 5 / `selling_general_and_administrative_expense` | Absent: `us-gaap:SellingGeneralAndAdministrativeExpense` | No combined SG&A candidate; retain separately reported bank expense categories. |
| 6 / `operating_expenses` | A `us-gaap:NoninterestExpense` (Noninterest Expense): **95,640,000,000 USD**, D<br>Absent: `us-gaap:OperatingExpenses` | Noninterest expense is observed, but not interchangeable with an industrial-company operating-expense subtotal. |
| 7 / `operating_income` | Absent: `us-gaap:OperatingIncomeLoss` | No operating-income candidate; net interest income is not operating income or EBIT. |
| 8 / `interest_expense` | H `us-gaap:InterestExpense` (Interest Expense): 24,356,000,000 USD; 2024-01-01 through 2024-03-31; acc. `0000019617-24-000326`; filed 2024-05-01<br>A `us-gaap:InterestExpenseOperating` (API label missing): **97,898,000,000 USD**, D<br>Absent: `us-gaap:InterestExpenseNonoperating` | Operating interest expense is observed. Generic InterestExpense is only historical; use requires explicit bank scope. |
| 9 / `pretax_income` | A `us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` (Income (Loss) from Continuing Operations before Income Taxes, Noncontrolling Interest): **72,595,000,000 USD**, D | Continuing-operations pretax scope retained. |
| 10 / `income_tax_expense` | A `us-gaap:IncomeTaxExpenseBenefit` (Income Tax Expense (Benefit)): **15,547,000,000 USD**, D | Total expense, not current tax or cash taxes. |
| 11 / `net_income_parent` | A `us-gaap:NetIncomeLoss` (Net Income (Loss) Attributable to Parent): **57,048,000,000 USD**, D | Parent earnings; income available to common stockholders is different (see detail table). |
| 12 / `net_income_consolidated` | H `us-gaap:ProfitLoss` (Net Income (Loss), Including Portion Attributable to Noncontrolling Interest): 17,923,000,000 USD; 2013-01-01 through 2013-12-31; acc. `0000019617-14-000289`; filed 2014-02-20 | No anchor ProfitLoss row; do not substitute parent earnings as consolidated income. |
| 13 / `eps_basic` | A `us-gaap:EarningsPerShareBasic` (Earnings Per Share, Basic): **20.05 USD/shares**, D | Observed candidate; no mapping priority or override approved. |
| 14 / `eps_diluted` | A `us-gaap:EarningsPerShareDiluted` (Earnings Per Share, Diluted): **20.02 USD/shares**, D | Observed candidate; no mapping priority or override approved. |
| 15 / `weighted_average_shares_basic` | A `us-gaap:WeightedAverageNumberOfSharesOutstandingBasic` (Weighted Average Number of Shares Outstanding, Basic): **2,776,500,000 shares**, D | Observed candidate; no mapping priority or override approved. |
| 16 / `weighted_average_shares_diluted` | A `us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding` (Weighted Average Number of Shares Outstanding, Diluted): **2,781,500,000 shares**, D | Observed candidate; no mapping priority or override approved. |
| 17 / `common_shares_outstanding` | A `us-gaap:CommonStockSharesOutstanding` (Common Stock, Shares, Outstanding): **2,696,200,000 shares**, I<br>O `dei:EntityCommonStockSharesOutstanding` (Entity Common Stock, Shares Outstanding): 2,697,032,375 shares; instant 2026-01-31; acc. `0001628280-26-008131`; filed 2026-02-13 | Period-end source differs from the later cover-page point date; retain exact dates. |
| 18 / `cash_and_cash_equivalents` | H `us-gaap:CashAndCashEquivalentsAtCarryingValue` (Cash and Cash Equivalents, at Carrying Value): 278,793,000,000 USD; instant 2018-12-31; acc. `0000019617-19-000054`; filed 2019-02-26 | Old cash tag does not establish 2025 coverage. Bank cash and restricted-cash aggregate need separate scope. |
| 19 / `short_term_investments` | Absent: `us-gaap:ShortTermInvestments` | No current-investment candidate; bank securities are not automatically short-term investments. |
| 20 / `accounts_receivable_net` | Absent: `us-gaap:AccountsReceivableNetCurrent` | Loans and financing receivables are not trade accounts receivable. |
| 21 / `inventory_net` | Absent: `us-gaap:InventoryNet` | Absent tag does not imply zero inventory. |
| 22 / `current_assets` | Absent: `us-gaap:AssetsCurrent` | No classified current-assets candidate. |
| 23 / `property_plant_equipment_net` | H `us-gaap:PropertyPlantAndEquipmentNet` (Property, Plant and Equipment, Net): 29,677,000,000 USD; instant 2023-09-30; acc. `0000019617-23-000524`; filed 2023-11-01 | Historical PP&E presence does not establish anchor coverage. |
| 24 / `goodwill` | A `us-gaap:Goodwill` (Goodwill): **52,731,000,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 25 / `intangible_assets_net_excluding_goodwill` | H `us-gaap:OtherIntangibleAssetsNet` (Other Intangible Assets, Net): 808,000,000 USD; instant 2017-09-30; acc. `0000019617-17-000552`; filed 2017-11-01<br>A `us-gaap:FiniteLivedIntangibleAssetsNet` (Finite-Lived Intangible Assets, Net): **1,300,000,000 USD**, I<br>Absent: `us-gaap:IntangibleAssetsNetExcludingGoodwill` | Finite-lived intangibles is only part of the requested all-intangibles scope; no approved substitution. |
| 26 / `total_assets` | A `us-gaap:Assets` (Assets): **4,424,900,000,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 27 / `accounts_payable_current` | Absent: `us-gaap:AccountsPayableCurrent` | Combined payable/accrual tags do not establish current trade payables. |
| 28 / `current_debt` | A `us-gaap:ShortTermBorrowings` (Short-term Debt): **64,776,000,000 USD**, I<br>Absent: `us-gaap:LongTermDebtCurrent`, `us-gaap:DebtCurrent` | ShortTermBorrowings is only a borrowing component; current maturities and other bank funding remain distinct. |
| 29 / `long_term_debt_noncurrent` | H `us-gaap:LongTermDebt` (Long-term Debt): 269,929,000,000 USD; instant 2014-06-30; acc. `0000019617-14-000409`; filed 2014-08-04<br>Absent: `us-gaap:LongTermDebtNoncurrent` | Including-current-maturities debt is observed elsewhere; it cannot be labeled noncurrent. |
| 30 / `current_liabilities` | Absent: `us-gaap:LiabilitiesCurrent` | No classified current-liabilities candidate. |
| 31 / `total_liabilities` | A `us-gaap:Liabilities` (Liabilities): **4,062,462,000,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 32 / `equity_parent` | A `us-gaap:StockholdersEquity` (Stockholders' Equity Attributable to Parent): **362,438,000,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 33 / `equity_including_noncontrolling_interests` | H `us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` (Stockholders' Equity, Including Portion Attributable to Noncontrolling Interest): 247,573,000,000 USD; instant 2015-12-31; acc. `0000019617-16-000902`; filed 2016-02-23 | Consolidated-equity tag is historical only; no anchor substitution. |
| 34 / `noncontrolling_interests` | Absent: `us-gaap:MinorityInterest` | No inspected noncontrolling-equity tag; not a zero claim. |
| 35 / `cash_from_operating_activities` | A `us-gaap:NetCashProvidedByUsedInOperatingActivities` (Net Cash Provided by (Used in) Operating Activities): **-147,782,000,000 USD**, D | Negative operating cash flow is the reported sign; bank lending/trading flows need sector-aware interpretation. |
| 36 / `capital_expenditures_ppe` | Absent: `us-gaap:PaymentsToAcquirePropertyPlantAndEquipment` | No cash-paid-for-PP&E candidate; original filing needs inspection. |
| 37 / `depreciation_and_amortization` | A `us-gaap:DepreciationAmortizationAndAccretionNet` (Depreciation, Amortization and Accretion, Net): **8,821,000,000 USD**, D<br>Absent: `us-gaap:DepreciationAndAmortization`, `us-gaap:DepreciationDepletionAndAmortization` | Available subtotal explicitly includes accretion; broader than D&A and requires scope review. |
| 38 / `share_based_compensation` | A `us-gaap:ShareBasedCompensation` (Share-based Payment Arrangement, Noncash Expense): **3,614,000,000 USD**, D | Observed candidate; no mapping priority or override approved. |
| 39 / `dividends_paid` | A `us-gaap:PaymentsOfDividends` (Payments of Dividends): **16,625,000,000 USD**, D<br>Absent: `us-gaap:PaymentsOfDividendsCommonStock` | Cash dividends paid is not automatically common-only. |
| 40 / `share_repurchases` | A `us-gaap:PaymentsForRepurchaseOfCommonStock` (Payments for Repurchase of Common Stock): **31,591,000,000 USD**, D | Cash repurchases, not treasury-stock carrying value. |


### Additional observed sector context

These are separate raw observations, not newly approved concepts or an instruction to add/sum tags. **D** and **I** retain the exact anchor periods above; all rows use this section's accession and filing date.

| Exact source tag | API label | Period | Raw value and unit |
| --- | --- | --- | --- |
| `us-gaap:InterestIncomeOperating` | Interest Income, Operating | D | 193,341,000,000 USD |
| `us-gaap:InterestExpenseOperating` | API label missing | D | 97,898,000,000 USD |
| `us-gaap:InterestIncomeExpenseNet` | Interest Income (Expense), Net | D | 95,443,000,000 USD |
| `us-gaap:NoninterestIncome` | Noninterest Income | D | 87,004,000,000 USD |
| `us-gaap:RevenuesNetOfInterestExpense` | Revenues, Net of Interest Expense | D | 182,447,000,000 USD |
| `us-gaap:NoninterestExpense` | Noninterest Expense | D | 95,640,000,000 USD |
| `us-gaap:InterestIncomeExpenseAfterProvisionForLoanLoss` | Interest Income (Expense), after Provision for Loan Loss | D | 81,231,000,000 USD |
| `us-gaap:CashAndDueFromBanks` | Cash and Due from Banks | I | 21,742,000,000 USD |
| `us-gaap:InterestBearingDepositsInBanks` | Interest-bearing Deposits in Banks and Other Financial Institutions | I | 321,596,000,000 USD |
| `us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` | Cash, Cash Equivalents, Restricted Cash and Restricted Cash Equivalents | I | 343,338,000,000 USD |
| `us-gaap:RestrictedCashAndCashEquivalents` | Restricted Cash and Cash Equivalents | I | 29,000,000,000 USD |
| `us-gaap:Deposits` | Deposits | I | 2,559,320,000,000 USD |
| `us-gaap:ShortTermBorrowings` | Short-term Debt | I | 64,776,000,000 USD |
| `us-gaap:LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities` | Long-term Debt and Lease Obligation, Including Current Maturities | I | 435,206,000,000 USD |
| `us-gaap:LongTermDebtMaturitiesRepaymentsOfPrincipalInNextRollingTwelveMonths` | Long-term Debt, Maturities, Repayments of Principal in Next Rolling Twelve Months | I | 42,589,000,000 USD |
| `us-gaap:AccountsPayableAndAccruedLiabilitiesCurrentAndNoncurrent` | Accounts Payable and Accrued Liabilities | I | 316,794,000,000 USD |
| `us-gaap:AccountsPayableAndOtherAccruedLiabilities` | Accounts Payable and Other Accrued Liabilities | I | 130,136,000,000 USD |
| `us-gaap:FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss` | API label missing | I | 1,467,664,000,000 USD |
| `us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic` | Net Income (Loss) Available to Common Stockholders, Basic | D | 55,681,000,000 USD |
| `us-gaap:AmortizationOfIntangibleAssets` | Amortization of Intangible Assets | D | 292,000,000 USD |



## CRCL: FY2025 anchor

- Accession: `0001876042-26-000062`; form: `10-K`; filed: `2026-03-09`; fiscal focus: `2025 / FY`.
- Source: [CRCL Company Facts](https://data.sec.gov/api/xbrl/companyfacts/CIK0001876042.json).
- Archived response: [raw/CRCL-20260911T141448625425Z.json.gz](evidence/raw/CRCL-20260911T141448625425Z.json.gz); fetched at `2026-09-11T14:14:48.625425+00:00`.
- Raw-response SHA-256: `f7139545b482a7b31520225bc155cb41241b82f004eb8fbca55f4ab66d1426af`.

| # / proposed concept | Observed exact tags and values / explicit gaps | Scope observation |
| --- | --- | --- |
| 1 / `revenue` | A `us-gaap:Revenues` (Revenues): **2,746,642,000 USD**, D<br>A `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` (Revenue from Contract with Customer, Excluding Assessed Tax): **109,820,000 USD**, D<br>Absent: `us-gaap:RevenuesNetOfInterestExpense` | Total revenue and customer-contract revenue materially differ; reserve income is separate in the detail table. |
| 2 / `cost_of_revenue` | Absent: `us-gaap:CostOfRevenue`, `us-gaap:CostOfGoodsAndServicesSold`, `us-gaap:CostOfGoodsSold` | OtherCostOfOperatingRevenue is only one expense component; no total cost-of-revenue candidate. |
| 3 / `gross_profit` | Absent: `us-gaap:GrossProfit` | No reported gross-profit candidate; a net-of-distribution subtotal needs original filing evidence. |
| 4 / `research_and_development_expense` | Absent: `us-gaap:ResearchAndDevelopmentExpense` | No R&D expense candidate; a tax-reconciliation R&D tag cannot substitute. |
| 5 / `selling_general_and_administrative_expense` | Absent: `us-gaap:SellingGeneralAndAdministrativeExpense` | No combined SG&A candidate; labor, marketing and other expenses are not summed to fill it. |
| 6 / `operating_expenses` | A `us-gaap:OperatingExpenses` (Operating Expenses): **1,179,426,000 USD**, D<br>Absent: `us-gaap:NoninterestExpense` | Observed operating-expense subtotal; scope requires the filing statement. |
| 7 / `operating_income` | A `us-gaap:OperatingIncomeLoss` (Operating Income (Loss)): **-96,435,000 USD**, D | Observed candidate; no mapping priority or override approved. |
| 8 / `interest_expense` | A `us-gaap:InterestExpenseNonoperating` (API label missing): **1,226,000 USD**, D<br>Absent: `us-gaap:InterestExpense`, `us-gaap:InterestExpenseOperating` | Nonoperating interest expense; reserve income must not be netted against it. |
| 9 / `pretax_income` | A `us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` (Income (Loss) from Continuing Operations before Income Taxes, Noncontrolling Interest): **-102,893,000 USD**, D | Observed candidate; no mapping priority or override approved. |
| 10 / `income_tax_expense` | A `us-gaap:IncomeTaxExpenseBenefit` (Income Tax Expense (Benefit)): **-33,375,000 USD**, D | Observed candidate; no mapping priority or override approved. |
| 11 / `net_income_parent` | A `us-gaap:NetIncomeLoss` (Net Income (Loss) Attributable to Parent): **-69,508,000 USD**, D | Parent loss differs from consolidated loss by noncontrolling interests. |
| 12 / `net_income_consolidated` | A `us-gaap:ProfitLoss` (Net Income (Loss), Including Portion Attributable to Noncontrolling Interest): **-69,518,000 USD**, D | Consolidated loss is separately reported; do not replace it with NetIncomeLoss. |
| 13 / `eps_basic` | A `us-gaap:EarningsPerShareBasic` (Earnings Per Share, Basic): **-0.44 USD/shares**, D | Loss-period basic EPS. |
| 14 / `eps_diluted` | A `us-gaap:EarningsPerShareDiluted` (Earnings Per Share, Diluted): **-0.44 USD/shares**, D | Loss-period diluted EPS equals basic; anti-dilutive shares remain separate. |
| 15 / `weighted_average_shares_basic` | A `us-gaap:WeightedAverageNumberOfSharesOutstandingBasic` (Weighted Average Number of Shares Outstanding, Basic): **158,699,000 shares**, D | Weighted-average denominator, not shares outstanding at year end. |
| 16 / `weighted_average_shares_diluted` | A `us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding` (Weighted Average Number of Shares Outstanding, Diluted): **158,699,000 shares**, D | Weighted-average diluted denominator; does not imply a current fully diluted capitalization. |
| 17 / `common_shares_outstanding` | Absent: `us-gaap:CommonStockSharesOutstanding`, `dei:EntityCommonStockSharesOutstanding` | Both inspected outstanding-share tags absent; class/dimensional filing extraction required. |
| 18 / `cash_and_cash_equivalents` | A `us-gaap:CashAndCashEquivalentsAtCarryingValue` (Cash and Cash Equivalents, at Carrying Value): **1,526,046,000 USD**, I | Corporate cash candidate is distinct from the much larger restricted-cash aggregate. |
| 19 / `short_term_investments` | Absent: `us-gaap:ShortTermInvestments` | No inspected current-investment candidate; long-term investments are not a substitute. |
| 20 / `accounts_receivable_net` | A `us-gaap:AccountsReceivableNetCurrent` (Accounts Receivable, after Allowance for Credit Loss, Current): **62,866,000 USD**, I | Observed standard receivables; confirm trade/non-trade composition in filing. |
| 21 / `inventory_net` | Absent: `us-gaap:InventoryNet` | No inventory tag; no zero substitution. |
| 22 / `current_assets` | A `us-gaap:AssetsCurrent` (Assets, Current): **77,801,467,000 USD**, I | Reported current assets may include stablecoin reserve balances; not free operating working capital. |
| 23 / `property_plant_equipment_net` | A `us-gaap:PropertyPlantAndEquipmentNet` (Property, Plant and Equipment, Net): **22,791,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 24 / `goodwill` | A `us-gaap:Goodwill` (Goodwill): **265,742,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 25 / `intangible_assets_net_excluding_goodwill` | A `us-gaap:IntangibleAssetsNetExcludingGoodwill` (Intangible Assets, Net (Excluding Goodwill)): **411,146,000 USD**, I<br>A `us-gaap:FiniteLivedIntangibleAssetsNet` (Finite-Lived Intangible Assets, Net): **144,316,000 USD**, I<br>Absent: `us-gaap:OtherIntangibleAssetsNet` | Total intangibles excluding goodwill differs from finite-lived subtotal; do not use the smaller subtotal. |
| 26 / `total_assets` | A `us-gaap:Assets` (Assets): **78,713,207,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 27 / `accounts_payable_current` | Absent: `us-gaap:AccountsPayableCurrent` | Combined payables and accruals is observed, but not current trade payables alone. |
| 28 / `current_debt` | Absent: `us-gaap:LongTermDebtCurrent`, `us-gaap:ShortTermBorrowings`, `us-gaap:DebtCurrent` | No total current-borrowings candidate; absent is not zero. |
| 29 / `long_term_debt_noncurrent` | Absent: `us-gaap:LongTermDebtNoncurrent`, `us-gaap:LongTermDebt` | Zero ConvertibleDebtNoncurrent is a component, not proof total noncurrent debt is zero. |
| 30 / `current_liabilities` | A `us-gaap:LiabilitiesCurrent` (Liabilities, Current): **75,328,395,000 USD**, I | Reported current liabilities include economic obligations needing stablecoin scope; not conventional operating payables. |
| 31 / `total_liabilities` | A `us-gaap:Liabilities` (Liabilities): **75,382,434,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 32 / `equity_parent` | A `us-gaap:StockholdersEquity` (Stockholders' Equity Attributable to Parent): **3,329,327,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 33 / `equity_including_noncontrolling_interests` | A `us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` (Stockholders' Equity, Including Portion Attributable to Noncontrolling Interest): **3,330,773,000 USD**, I | Observed candidate; no mapping priority or override approved. |
| 34 / `noncontrolling_interests` | A `us-gaap:MinorityInterest` (Stockholders' Equity Attributable to Noncontrolling Interest): **1,446,000 USD**, I | Noncontrolling equity is separately reported. |
| 35 / `cash_from_operating_activities` | A `us-gaap:NetCashProvidedByUsedInOperatingActivities` (Net Cash Provided by (Used in) Operating Activities): **542,129,000 USD**, D | Observed candidate; no mapping priority or override approved. |
| 36 / `capital_expenditures_ppe` | A `us-gaap:PaymentsToAcquirePropertyPlantAndEquipment` (Payments to Acquire Property, Plant, and Equipment): **12,432,000 USD**, D | PP&E cash spending excludes separately observed software-development payments. |
| 37 / `depreciation_and_amortization` | A `us-gaap:DepreciationAndAmortization` (Depreciation, Depletion and Amortization, Nonproduction): **76,627,000 USD**, D<br>A `us-gaap:DepreciationDepletionAndAmortization` (Depreciation, Depletion and Amortization): **76,627,000 USD**, D<br>Absent: `us-gaap:DepreciationAmortizationAndAccretionNet` | Two equal reported combined D&A tags; no priority approved. Depreciation-only is not equivalent. |
| 38 / `share_based_compensation` | A `us-gaap:ShareBasedCompensation` (Share-based Payment Arrangement, Noncash Expense): **566,177,000 USD**, D | Retain reported SBC and period; do not substitute award grants/fair values. |
| 39 / `dividends_paid` | Absent: `us-gaap:PaymentsOfDividends`, `us-gaap:PaymentsOfDividendsCommonStock` | No inspected dividends-paid tag; preferred income-statement dividend impact cannot establish cash dividends. |
| 40 / `share_repurchases` | A `us-gaap:PaymentsForRepurchaseOfCommonStock` (Payments for Repurchase of Common Stock): **0 USD**, D | The zero is explicitly reported, unlike missing dividends/current debt. |


### Additional observed sector context

These are separate raw observations, not newly approved concepts or an instruction to add/sum tags. **D** and **I** retain the exact anchor periods above; all rows use this section's accession and filing date.

| Exact source tag | API label | Period | Raw value and unit |
| --- | --- | --- | --- |
| `us-gaap:Revenues` | Revenues | D | 2,746,642,000 USD |
| `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` | Revenue from Contract with Customer, Excluding Assessed Tax | D | 109,820,000 USD |
| `us-gaap:InterestAndDividendIncomeOperating` | Interest and Dividend Income, Operating | D | 2,636,822,000 USD |
| `us-gaap:InvestmentIncomeNonoperating` | Investment Income, Nonoperating | D | 47,672,000 USD |
| `us-gaap:OtherCostOfOperatingRevenue` | Other Cost of Operating Revenue | D | 2,102,000 USD |
| `us-gaap:LaborAndRelatedExpense` | Labor and Related Expense | D | 844,878,000 USD |
| `us-gaap:MarketingExpense` | Marketing Expense | D | 25,718,000 USD |
| `us-gaap:CashAndCashEquivalentsAtCarryingValue` | Cash and Cash Equivalents, at Carrying Value | I | 1,526,046,000 USD |
| `us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` | Cash, Cash Equivalents, Restricted Cash and Restricted Cash Equivalents | I | 77,419,733,000 USD |
| `us-gaap:RestrictedCashNoncurrent` | Restricted Cash, Noncurrent | I | 2,792,000 USD |
| `us-gaap:IncreaseDecreaseInDeposits` | Increase (Decrease) in Deposits | D | 31,139,764,000 USD |
| `us-gaap:LiabilitiesCurrent` | Liabilities, Current | I | 75,328,395,000 USD |
| `us-gaap:Liabilities` | Liabilities | I | 75,382,434,000 USD |
| `us-gaap:AccountsPayableAndAccruedLiabilitiesCurrent` | Accounts Payable and Accrued Liabilities, Current | I | 360,609,000 USD |
| `us-gaap:AccountsPayableOtherCurrent` | Accounts Payable, Other, Current | I | 20,341,000 USD |
| `us-gaap:ConvertibleDebtNoncurrent` | Convertible Debt, Noncurrent | I | 0 USD |
| `us-gaap:OperatingLeaseLiabilityCurrent` | Operating Lease, Liability, Current | I | 2,686,000 USD |
| `us-gaap:OperatingLeaseLiabilityNoncurrent` | Operating Lease, Liability, Noncurrent | I | 11,978,000 USD |
| `us-gaap:LongTermInvestments` | Long-term Investments | I | 84,265,000 USD |
| `us-gaap:PaymentsToDevelopSoftware` | Payments to Develop Software | D | 56,200,000 USD |
| `us-gaap:Depreciation` | Depreciation | D | 3,000,000 USD |
| `us-gaap:AmortizationOfIntangibleAssets` | Amortization of Intangible Assets | D | 73,664,000 USD |
| `us-gaap:NetIncomeLoss` | Net Income (Loss) Attributable to Parent | D | -69,508,000 USD |
| `us-gaap:ProfitLoss` | Net Income (Loss), Including Portion Attributable to Noncontrolling Interest | D | -69,518,000 USD |
| `us-gaap:NetIncomeLossAttributableToNoncontrollingInterest` | Net Income (Loss) Attributable to Noncontrolling Interest | D | -10,000 USD |
| `us-gaap:MinorityInterest` | Stockholders' Equity Attributable to Noncontrolling Interest | I | 1,446,000 USD |
| `us-gaap:StockholdersEquity` | Stockholders' Equity Attributable to Parent | I | 3,329,327,000 USD |
| `us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` | Stockholders' Equity, Including Portion Attributable to Noncontrolling Interest | I | 3,330,773,000 USD |
| `us-gaap:AntidilutiveSecuritiesExcludedFromComputationOfEarningsPerShareAmount` | Antidilutive Securities Excluded from Computation of Earnings Per Share, Amount | D | 31,832,000 shares |
| `us-gaap:PaymentsForRepurchaseOfCommonStock` | Payments for Repurchase of Common Stock | D | 0 USD |
| `us-gaap:PaymentsRelatedToTaxWithholdingForShareBasedCompensation` | Payment, Tax Withholding, Share-based Payment Arrangement | D | 269,732,000 USD |



## Economic mismatches requiring a reviewed decision

1. **JPM revenue is already net of interest expense.** The two observed revenue tags both report USD 182,447,000,000. Operating interest income, operating interest expense and net interest income are separate facts. Treating revenue as an industrial gross-sales measure or subtracting the interest expense again would misstate the economics. Noninterest expense is not a generic operating-cost mapping, and no anchor operating-income tag was observed.

2. **JPM has no inspected classified current-assets/current-liabilities total.** Deposits (USD 2,559,320,000,000), short-term borrowing, longer-term funding, loans and bank securities retain their own scope. None establishes conventional trade working capital. The available long-term debt tag includes current maturities and capital leases; it is not noncurrent debt. CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents is not the requested unrestricted cash concept.

3. **CRCL total and customer-contract revenue are not alternatives.** Revenues is USD 2,746,642,000; the customer-contract tag is USD 109,820,000; operating interest/dividend income is USD 2,636,822,000. The anchor filing must confirm issuer labels and reserve-income scope before an override. A generic priority preferring customer-contract revenue would discard most reported revenue. No sum is approved or used as a replacement raw fact.

4. **CRCL corporate cash must remain distinct from the reserve/custodial aggregate.** CashAndCashEquivalentsAtCarryingValue is USD 1,526,046,000; combined cash/restricted cash is USD 77,419,733,000. The payload alone does not identify the exact stablecoin-holder asset and liability presentation or prove availability to shareholders. Preserve the corporate cash candidate and require filing context for reserve balances; do not deduct the full combined aggregate in net debt or enterprise value.

5. **Ownership scope is observable.** CRCL NetIncomeLoss (USD -69,508,000) differs from ProfitLoss (USD -69,518,000); parent equity (USD 3,329,327,000) differs from equity including noncontrolling interests (USD 3,330,773,000). JPM income available to common shareholders (USD 55,681,000,000) differs from NetIncomeLoss (USD 57,048,000,000). EPS denominators must preserve these distinctions.

6. **Missing tags and reported zero are different evidence states.** CRCL common-share cash repurchases are explicitly zero for D. Its inspected dividends-paid and total current-debt tags are absent. ConvertibleDebtNoncurrent is explicitly zero but only for that component. Neither warrants zero-filling the broader missing concept.

7. **Historical tags must not be carried forward.** JPM's cash carrying-value tag ends at 2018-12-31, PP&E at 2023-09-30, generic InterestExpense at 2024-03-31, and ProfitLoss at 2013-12-31 in these saved responses. CRCL class-specific point-date common shares are not supplied by either inspected outstanding-share tag; annual weighted-average shares are not a replacement.

## Original-filing evidence still needed

The exact custom qualified names cannot be established from Company Facts, because this endpoint omits issuer extension taxonomies. No extension name is invented here. The following are concrete extraction targets for the pinned filings:

- **CRCL** [FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1876042/000187604226000062/crcl-20251231.htm): identify exact tag/context/unit and balance-sheet line for stablecoin-holder reserves and corresponding redemption/holder liabilities; verify reserve income tagged `us-gaap:InterestAndDividendIncomeOperating`; identify distribution/transaction expense and the reported revenue-less-distribution subtotal; retrieve class-specific common-share counts and confirm whether their missing Company Facts coverage is dimensional; check payables composition and current/noncurrent financing. Confirm whether D&A includes software amortization, noting separate `PaymentsToDevelopSoftware` cash spending.

- **JPM** [FY2025 filing index](https://www.sec.gov/Archives/edgar/data/19617/0001628280-26-008131-index.htm): inspect the bank statements for current `PropertyPlantAndEquipmentNet` replacement/presentation and capital-spending cash-flow context; inspect net-revenue/interest-expense presentation, noninterest expenses, restricted-cash reconciliation, debt including current maturities, and finite-lived/other intangible coverage. Retrieve custom tags if those reported lines use extensions; do not infer a new extension tag from an old standard tag.

## Verification performed

- Decompressed both archives and verified raw SHA-256 against the saved manifest.
- Inspected all 40 candidate groups for each company with exact accession, exact fiscal interval/instant, unit and source row selection; all A rows match the stated filing date/form/fiscal focus.
- Explicit H/O examples retain their own metadata; absent names were checked against the complete saved taxonomy/tag dictionaries.
- Financial-statement semantic equivalence and custom/dimensional extraction are pending; these are not hand-checked normalized golden fixtures.

## Original-filing follow-up: confirmed 2026-09-12

The local [filing manifest](evidence/filing-manifest.json) now contains complete
CRCL and JPM HTML archives. The following observations supersede the extraction
requests above where answered; they do not approve additional normalized concepts.
Values below retain original context and display scale; source archives supply
full surrounding statements and namespaces.

### CRCL reserves, distribution costs and shares

CRCL accession `0001876042-26-000062`: instant `c-6` is 2025-12-31;
annual `c-1` is 2025-01-01 through 2025-12-31. Currency unit `usd` is USD.

| Exact Inline XBRL tag | Context | Filing literal / scale | Amount, USD | Scope |
| --- | --- | --- | ---: | --- |
| `crcl:CashAndCashEquivalentsSegregatedForTheBenefitOfStablecoinHolders` | c-6 | 75,067,932 / 3 | 75,067,932,000 | Segregated holder reserves, not corporate unrestricted cash |
| `crcl:CashAndCashEquivalentsSegregatedForCorporateHeldStablecoins` | c-6 | 822,963 / 3 | 822,963,000 | Separate corporate-held stablecoin reserve presentation |
| `us-gaap:DepositLiabilityCurrent` | c-6 | 74,912,567 / 3 | 74,912,567,000 | Standard tag for the holder-deposit liability; do not invent a custom tag |
| `us-gaap:InterestAndDividendIncomeOperating` | c-1 | 2,636,822 / 3 | 2,636,822,000 | Reserve-income line, distinct from customer-contract revenue |
| `crcl:DistributionAndTransactionCosts` | c-1 | 1,661,549 / 3 | 1,661,549,000 | Distribution and transaction costs |
| `crcl:DistributionTransactionAndOtherCosts` | c-1 | 1,663,651 / 3 | 1,663,651,000 | Broader subtotal including other costs |

The actual custom qualified names are absent from the Company Facts taxonomy
set. In the same filing, `us-gaap:CommonStockSharesOutstanding` uses context
`c-8`, dimension `us-gaap:CommonClassAMember`, end 2025-12-31, unit `shares`,
literal `223.6`, scale 6. This is rounded **223,600,000 Class A shares**, not
an unrounded company-wide count. Class context and source precision must survive
an original-filing adapter. This confirms a concrete share observation omitted
from the inspected Company Facts outstanding-share candidates.

### JPM bank asset and cash-flow scope

JPM accession `0001628280-26-008131`: instant `c-30` is 2025-12-31;
annual `c-1` is 2025-01-01 through 2025-12-31, unit `usd`.

| Exact Inline XBRL tag | Context | Filing literal / scale | Amount, USD | Reason not to substitute |
| --- | --- | --- | ---: | --- |
| `us-gaap:CashAndDueFromBanks` | c-30 | 21,742 / 6 | 21,742,000,000 | Bank cash/due-from scope, not automatically corporate cash/equivalents |
| `jpm:PropertyPlantAndEquipmentAndOperatingLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization` | c-30 | 36,244 / 6 | 36,244,000,000 | Explicitly includes operating-lease ROU assets; not the historical PP&E-only concept |
| `us-gaap:LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities` | c-30 | 435,206 / 6 | 435,206,000,000 | Includes current maturities and capital leases; not noncurrent debt alone |
| `us-gaap:DepreciationAmortizationAndAccretionNet` | c-1 | 8,821 / 6 | 8,821,000,000 | Includes accretion, so not D&A-only |
| `us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` | c-30 | 343,338 / 6 | 343,338,000,000 | Combined cash/restricted cash; not the unrestricted cash candidate |

A complete cash-PP&E payment mapping remains unestablished. Securities purchase
cash flows and business acquisitions are not PP&E capex. This unresolved scope
is recorded as missing rather than filled from nearby cash-flow numbers.
