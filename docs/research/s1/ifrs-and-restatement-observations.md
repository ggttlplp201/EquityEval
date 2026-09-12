# S1 IFRS and restatement observations

Status: archived-source observations for review, not an approved concept map or
golden fixture. Inspected locally on 2026-09-11. This document does not create
normalization rules, perform currency/ADS conversions, or fill missing facts.

## Evidence and reproducibility

The source is the [Company Facts archive manifest](evidence/manifest.json).
Checksums below are SHA-256 of the decompressed response bytes; both were
independently recomputed and matched the manifest.

| Company | Archive | Retrieved at (UTC) | SHA-256 |
| --- | --- | --- | --- |
| KHC | [raw JSON gzip](evidence/raw/KHC-20260911T141504081902Z.json.gz) | 2026-09-11T14:15:04.081902+00:00 | 8fad66c16e535f7749f19126a986a9f43a087ca2472d063fa7742106196d88ac |
| TSM | [raw JSON gzip](evidence/raw/TSM-20260911T141459576388Z.json.gz) | 2026-09-11T14:14:59.576388+00:00 | d3ebb91e3ad78c9482e238c4db36df60b295a3b49ca137774706f4f5e526044a |

Array indices in this document are zero-based within the named unit array and
are locators into this specific payload, not permanent fact identifiers.
Preserve the checksum, namespace/tag, unit, exact interval, accession and row
metadata together. No network request was made for this local analysis.

## KHC: actual original and restated observations

The confirmed parent-income tag is `us-gaap:NetIncomeLoss`. Its API description
identifies income attributable to the parent. Unit is `USD`, with values already
expressed in dollars, not millions. Every row below covers the exact duration
`2017-01-01` through `2017-12-30`.

| Unit-array index | Raw value, USD | accn | filed | fy | fp | form | frame |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| 76 | 10999000000 | 0001637459-18-000015 | 2018-02-16 | 2017 | FY | 10-K | absent |
| 77 | 10941000000 | 0001637459-19-000049 | 2019-06-07 | 2018 | FY | 10-K | absent |
| 78 | 10941000000 | 0001637459-20-000027 | 2020-02-14 | 2019 | FY | 10-K | absent |
| 79 | 10941000000 | 0001637459-20-000168 | 2020-11-13 | null | null | 8-K | CY2017 |

These are all four USD observations in this archive for that exact tag and
duration. They reproduce the filing-verified 10,999 million to 10,941 million
pair in [the existing restatement research](restatement-khc.md). The values as
presented in millions must not be stored with a second scale conversion.

The fiscal-report metadata changes while the measured duration remains FY2017.
Filtering `fy == 2017` would discard all three subsequent observations. Requiring
`frame` would discard the original and first restated rows. Repetition of an
unchanged amount in 2020 is not evidence of a new error restatement.

The original/revised `us-gaap:ProfitLoss` USD rows at indices 65/66 are
10990000000/10932000000 for the same interval and accessions. This is consolidated
income including noncontrolling interests, a different proposed concept.

`us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic` matches parent income
for FY2017 but is not an interchangeable fallback. For FY2016
(`2016-01-04` through `2016-12-31`), in accession
`0001637459-18-000015` (filed 2018-02-16; fy 2017; fp FY; 10-K),
`NetIncomeLoss` USD index 51 is 3632000000 whereas
`NetIncomeLossAvailableToCommonStockholdersBasic` USD index 51 is 3452000000.
The ownership and preferred-dividend distinction is observable in the archive.

The filing identifies the 58 million parent-income reduction as error correction
and gives zero ASU-adoption effect for that line. In contrast, FY2017 cost of
products sold goes 16,529 million to 16,485 million for errors, then to 17,043
million after a separate pension-presentation recast. The archive has the original
under deprecated `us-gaap:CostOfGoodsSold` USD index 45 (16529000000) and the
restated/recast comparative under `us-gaap:CostOfGoodsAndServicesSold` USD index 8
(17043000000). Tag migration and accounting recast cannot be treated as error
correction alone. [Filing reconciliation](https://www.sec.gov/Archives/edgar/data/1637459/000163745919000049/R9.htm)

A proposed filed-date regression can use 2018-02-17 and 2019-06-08 as unambiguous
calendar dates bracketing these observations. It must return 10999000000 and
10941000000 respectively for this exact tag/unit/period. This is a hand-verified
expected pair, not an executed database or normalization test. A separate
non-reliance event was announced on May 6, 2019; preliminary information in that
8-K is not the June audited value. The four Company Facts rows do not establish
what every market participant knew between these filings. [Non-reliance 8-K](https://www.sec.gov/Archives/edgar/data/1637459/000163745919000033/may2019form8-k.htm)

## TSM: primary FY2025 coverage is missing for IFRS facts

The inspected archive contains 334 `ifrs-full` concepts, one `dei` concept and
one `srt` concept. All 334 IFRS concept objects have null `label` and
`description`; do not invent source labels or silently promote identifier
spelling into a verified definition.

The [cohort's FY2025 20-F](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/tsm-20251231.htm)
has accession `0001628280-26-025362`, but that accession appears in **zero IFRS
rows** in this payload. It appears in one DEI share row and one SRT authorization
row. Across every IFRS row, maximum period end is `2024-12-31` and maximum filed
date is `2025-04-17`. There are 5,470 IFRS observations from 20-F and 501 from
6-K; a filing-type filter limited to 10-K/10-Q would miss the entire IFRS history.

This is an observed endpoint-coverage gap, not proof that FY2025 statements or
XBRL do not exist. Current FY2025 IFRS coverage must remain absent/stale and point
to original-filing extraction. FY2024 data below are a separately labelled
historical research sample, never an automatic fallback for FY2025.

The available FY2025 DEI row is:

```json
{"end":"2025-12-31","val":25932524521,"accn":"0001628280-26-025362","fy":2025,"fp":"FY","form":"20-F","filed":"2026-04-16","frame":"CY2025Q4I"}
```

Its source path is `facts.dei.EntityCommonStockSharesOutstanding.units.shares[8]`.
The corresponding FY2024 DEI row at index 7 is 25932733242 shares at
2024-12-31, filed 2025-04-17 in accession 0001193125-25-083423.
Combining the FY2025 share count with FY2024 income as if one reporting period
would erase this observed coverage mismatch.

## TSM: historical FY2024 mapping observations for 40 proposals

The following table corresponds one-for-one to
[the 40 proposed concepts](concept-candidates.md). Every IFRS name is in
`ifrs-full` unless a different namespace is written. “Observed candidate”
means an exact row is present and its name is economically relevant; it does not
mean the filing scope is approved. Null labels/descriptions and unresolved note
context limit inference. “No observed” means absent from this archived scope,
never an economic zero.

All FY2024 examples use accession `0001193125-25-083423`, form `20-F`,
filed `2025-04-17`, fy `2024`, fp `FY`. Duration observations cover
`2024-01-01` to `2024-12-31`; instants have end `2024-12-31` and no
`start`. Exact units, values, indices and duration/instant flags are in the
appendix. No current FY2025 IFRS mapping is claimed.

| # | Proposed concept | Observed tag or excluded nearby tag | Assessment | Scope finding |
| --- | --- | --- | --- | --- |
| 1 | `revenue` | `Revenue`; `RevenueFromContractsWithCustomers` | Observed FY2024 candidates | Both TWD values match in this period; Revenue also has USD. Equality does not establish an interchangeable scope for all periods. |
| 2 | `cost_of_revenue` | `CostOfSales` | Observed FY2024 candidate | Retain cost-of-sales scope and positive source value. |
| 3 | `gross_profit` | `GrossProfit` | Observed FY2024 candidate | Reported subtotal; no subtraction performed. |
| 4 | `research_and_development_expense` | `ResearchAndDevelopmentExpense` | Observed FY2024 candidate | Expense only; do not combine capitalized development. |
| 5 | `selling_general_and_administrative_expense` | `GeneralAndAdministrativeExpense`; `SalesAndMarketingExpense` | No observed combined candidate | Separate G&A and sales/marketing values; do not sum into a reported combined fact. |
| 6 | `operating_expenses` | `OperatingExpenseExcludingCostOfSales` | Observed FY2024 candidate | Explicitly excludes cost of sales; retain definition. |
| 7 | `operating_income` | `ProfitLossFromOperatingActivities` | Observed FY2024 candidate | Reported operating subtotal; not automatic EBIT. |
| 8 | `interest_expense` | `FinanceCosts`; `InterestExpenseOnBorrowings`; `InterestExpenseOnBonds`; `InterestExpenseOnLeaseLiabilities`; `InterestCostsCapitalised` | Ambiguous scope | FinanceCosts differs from component amounts; examine capitalization and expense scope in the filing before mapping. |
| 9 | `pretax_income` | `ProfitLossBeforeTax` | Observed FY2024 candidate | Consolidated pretax scope must be retained. |
| 10 | `income_tax_expense` | `IncomeTaxExpenseContinuingOperations` | Observed FY2024 candidate | Explicit continuing-operations scope; preserve sign. |
| 11 | `net_income_parent` | `ProfitLossAttributableToOwnersOfParent` | Observed FY2024 candidate | Distinct from consolidated ProfitLoss and ordinary-holder earnings scope. |
| 12 | `net_income_consolidated` | `ProfitLoss` | Observed FY2024 candidate | Includes noncontrolling interests; parent result differs. |
| 13 | `eps_basic` | `BasicEarningsLossPerShare` | Observed FY2024 candidate | TWD/shares and USD/shares are separate units; no ADS conversion is encoded. |
| 14 | `eps_diluted` | `DilutedEarningsLossPerShare` | Observed FY2024 candidate | Separate from basic despite rounded USD values matching. |
| 15 | `weighted_average_shares_basic` | `WeightedAverageShares` | Observed FY2024 candidate | Annual duration in shares; ordinary/ADS identity requires filing evidence. |
| 16 | `weighted_average_shares_diluted` | `AdjustedWeightedAverageShares` | Observed FY2024 candidate | Annual duration; diluted denominator scope requires filing confirmation. |
| 17 | `common_shares_outstanding` | `dei:EntityCommonStockSharesOutstanding`; `NumberOfSharesIssuedAndFullyPaid` | Observed DEI candidate; IFRS alternative rejected | Use exact instant and instrument scope. Issued-and-fully-paid is a different concept and has rounded figures; do not silently substitute it. |
| 18 | `cash_and_cash_equivalents` | `CashAndCashEquivalents` | Observed FY2024 candidate | Instant, TWD and USD; restricted cash is not automatically included. |
| 19 | `short_term_investments` | `CurrentFinancialAssetsAtAmortisedCost`; `CurrentFinancialAssetsAtFairValueThroughOtherComprehensiveIncome`; `CurrentFinancialAssetsAtFairValueThroughProfitOrLoss` | No observed combined candidate | Three separate measurement categories; no approved combined investment fact. |
| 20 | `accounts_receivable_net` | `CurrentTradeReceivables` | Observed FY2024 candidate, net scope pending | Confirm allowance/net presentation in original statements. |
| 21 | `inventory_net` | `Inventories` | Observed FY2024 candidate, net scope pending | Confirm carrying amount and write-down presentation; do not infer zero from missing periods. |
| 22 | `current_assets` | `CurrentAssets` | Observed FY2024 candidate | Classified consolidated current assets. |
| 23 | `property_plant_equipment_net` | `PropertyPlantAndEquipment` | Observed FY2024 candidate, carrying scope pending | Do not combine separately tagged right-of-use assets. |
| 24 | `goodwill` | `IntangibleAssetsAndGoodwill` | No observed goodwill-only carrying tag | Combined tag cannot fill goodwill-only concept. Impairment-expense tags are not carrying amounts. |
| 25 | `intangible_assets_net_excluding_goodwill` | `IntangibleAssetsAndGoodwill` | No observed excluding-goodwill carrying tag | Combined tag cannot fill this concept; do not infer goodwill is zero. |
| 26 | `total_assets` | `Assets` | Observed FY2024 candidate | Consolidated assets, exact instant. |
| 27 | `accounts_payable_current` | `TradeAndOtherCurrentPayablesToTradeSuppliers`; `TradeAndOtherCurrentPayablesToRelatedParties` | Ambiguous scope | Trade-and-other wording and separate related-party balance prevent automatic total-trade-payable mapping. |
| 28 | `current_debt` | `CurrentPortionOfLongtermBorrowings`; `ShorttermBorrowings` | Incomplete aggregate coverage | Current maturities observed; ShorttermBorrowings has no FY2024-end row. That absence is not zero or complete current-debt coverage. |
| 29 | `long_term_debt_noncurrent` | `LongtermBorrowings`; `NoncurrentPortionOfNoncurrentBondsIssued` | Incomplete aggregate coverage | Loans/borrowings and separate noncurrent bonds differ greatly; one tag is not total noncurrent debt. Lease treatment remains unresolved. |
| 30 | `current_liabilities` | `CurrentLiabilities` | Observed FY2024 candidate | Classified current liabilities. |
| 31 | `total_liabilities` | `Liabilities` | Observed FY2024 candidate | Reported consolidated liabilities; no assets-minus-equity derivation. |
| 32 | `equity_parent` | `EquityAttributableToOwnersOfParent` | Observed FY2024 candidate | Parent equity distinct from Equity. |
| 33 | `equity_including_noncontrolling_interests` | `Equity` | Observed FY2024 candidate | Consolidated equity including noncontrolling interests. |
| 34 | `noncontrolling_interests` | `NoncontrollingInterests` | Observed FY2024 candidate | Equity carrying amount, not income attribution. |
| 35 | `cash_from_operating_activities` | `CashFlowsFromUsedInOperatingActivities` | Observed FY2024 candidate | Annual cash flow; do not use CashFlowsFromUsedInOperations before later cash-flow adjustments. |
| 36 | `capital_expenditures_ppe` | `PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` | Observed FY2024 candidate | Positive raw purchase/payment value; sign interpretation belongs to reviewed cash-flow transform. |
| 37 | `depreciation_and_amortization` | `DepreciationExpense`; `AmortisationExpense` | No observed combined candidate | Separate raw amounts; depreciation alone is not combined D&A. No sum manufactured. |
| 38 | `share_based_compensation` | `AdjustmentsForSharebasedPayments`; `ExpenseFromSharebasedPaymentTransactionsInWhichGoodsOrServicesReceivedDidNotQualifyForRecognitionAsAssets` | Ambiguous expense/addback scope | FY2024 expense and cash-flow adjustment differ; canonical definition must choose and record scope. |
| 39 | `dividends_paid` | `DividendsPaidClassifiedAsFinancingActivities`; `DividendsPaid` | Conflicting candidates | Same-period values differ; prefer cash-flow-labelled candidate for investigation but do not approve mapping until dividend-note reconciliation. |
| 40 | `share_repurchases` | `IncreaseDecreaseThroughTreasuryShareTransactions`; `srt:StockRepurchaseProgramNumberOfSharesAuthorizedToBeRepurchased` | No observed cash-repurchase candidate | Equity movement and authorization share count are not cash spent on repurchases. |

## TSM: currency, share basis and conflicting scope

- FY2024 `Revenue` is 2894307700000 TWD and 88268000000 USD in separate
  arrays for the same duration/accession. `RevenueFromContractsWithCustomers`
  has the same TWD value but no USD unit anywhere in this archive. Retain the
  currency key; never choose USD merely because the traded ticker is a US ADS.
  The source archive itself does not explain the translation basis. The cohort
  describes convenience USD presentation; the applicable filing exchange-rate
  note must be linked before that becomes a verified conversion policy.
- FY2024 EPS is 44.68 TWD/shares basic and 44.67 diluted, versus 1.36
  USD/shares for both after source rounding. Weighted-average denominators are
  25927600000 and 25929700000 shares. The endpoint unit `shares` does not encode
  ordinary shares versus ADS or an ADS ratio. No ADS-ratio concept exists in
  the inspected namespaces. Verify the instrument ratio and effective date from
  the filing/depositary before comparing to a USD ADS price; do not multiply
  income, EPS or outstanding shares during raw ingestion.
- The FY2024 `NumberOfSharesIssuedAndFullyPaid` value is 25932700000 shares,
  while DEI outstanding is 25932733242. Different labels/scopes and rounding
  mean issued shares, outstanding shares, weighted-average shares and ADS units
  must stay distinct.
- `DividendsPaid` is 414915500000 TWD, while
  `DividendsPaidClassifiedAsFinancingActivities` is 363055200000 TWD for the
  identical period/accession. Neither tag spelling nor newest-date selection
  resolves this difference. A dividend-note/cash-flow reconciliation is needed
  before normalizing common/all-holder cash dividends.
- `AdjustmentsForSharebasedPayments` is 1242700000 TWD while
  `ExpenseFromSharebasedPaymentTransactionsInWhichGoodsOrServicesReceivedDidNotQualifyForRecognitionAsAssets`
  is 1646200000 TWD. This exposes a needed expense-versus-addback choice in
  concept 38, not an excuse to choose the more convenient amount.
- `FinanceCosts`, borrowing/bond/lease interest components and
  `InterestCostsCapitalised` all exist with different amounts. Their
  relationship requires the expense/capitalization note; no total or
  net-of-capitalized-interest formula is approved here.
- `LongtermBorrowings` is 31824400000 TWD while separate
  `NoncurrentPortionOfNoncurrentBondsIssued` is 926604500000 TWD.
  The first tag cannot represent all noncurrent debt. Missing FY2024
  `ShorttermBorrowings` must remain missing; its latest measured date in
  this archive is 2021-12-31.
- The archive repeats FY2022/FY2023 TWD observations in the FY2024 filing.
  Their `fy` is 2024 despite earlier start/end dates. The USD history does
  not have the same comparative repetitions. Period selection must use exact
  start/end and selected filing mode before tag and currency resolution.

## Open review items and documentation handoff

1. The primary FY2025 TSM financial coverage gap needs explicit reporting and
   original-filing evidence. A present DEI row does not make IFRS coverage current.
2. The 40-proposal catalogue intentionally omits combinations needed by this
   issuer: combined SG&A/D&A, debt totals, and separate goodwill/intangibles
   cannot be asserted as observed facts from these nearby tags.
3. Original TSM statements/notes are still needed for expense/capitalization,
   dividend and SBC scope, receivable/inventory/PP&E carrying presentation,
   convenience currency and ADS identity. Archived Company Facts is not enough
   to certify every mapping.
4. At inspection, `README.md`, `cohort.md`, `source-boundaries.md` and
   `S1-sec-recon.md` still describe downloads/empirical inspection as pending.
   `restatement-khc.md` still calls `NetIncomeLoss` unverified and lists
   start/unit/fy/fp/repetitions as unknown. This document resolves those local
   observations; root should update those status statements and link this file.
5. No production schema or concept vocabulary, mapping priority, currency
   conversion, missing-data policy, or automatic fallback is authorized by
   these research observations alone.

## Appendix: exact TSM FY2024 rows

Values below are raw numeric values from the archived payload. They are not
displayed in millions. All rows share the FY2024 accession/form/filing metadata
defined above. D = duration 2024-01-01..2024-12-31 and frame CY2024; I = instant
2024-12-31 with no start and frame CY2024Q4I. Each row locator is
`facts.ifrs-full.<tag>.units[<unit>][<index>]`.
The table also includes nearby excluded tags so the ambiguity is reproducible.

| Tag | Unit | Array index | D/I | Raw value |
| --- | --- | ---: | --- | ---: |
| `Revenue` | `TWD` | 25 | D | 2894307700000 |
| `Revenue` | `USD` | 8 | D | 88268000000 |
| `RevenueFromContractsWithCustomers` | `TWD` | 19 | D | 2894307700000 |
| `CostOfSales` | `TWD` | 25 | D | 1269954100000 |
| `CostOfSales` | `USD` | 8 | D | 38729900000 |
| `GrossProfit` | `TWD` | 25 | D | 1624353600000 |
| `GrossProfit` | `USD` | 8 | D | 49538100000 |
| `ResearchAndDevelopmentExpense` | `TWD` | 25 | D | 204181800000 |
| `ResearchAndDevelopmentExpense` | `USD` | 8 | D | 6227000000 |
| `GeneralAndAdministrativeExpense` | `TWD` | 22 | D | 83745000000 |
| `GeneralAndAdministrativeExpense` | `USD` | 7 | D | 2554000000 |
| `SalesAndMarketingExpense` | `TWD` | 25 | D | 13143600000 |
| `SalesAndMarketingExpense` | `USD` | 8 | D | 400800000 |
| `OperatingExpenseExcludingCostOfSales` | `TWD` | 25 | D | 301070400000 |
| `OperatingExpenseExcludingCostOfSales` | `USD` | 8 | D | 9181800000 |
| `ProfitLossFromOperatingActivities` | `TWD` | 25 | D | 1322053000000 |
| `ProfitLossFromOperatingActivities` | `USD` | 8 | D | 40318800000 |
| `FinanceCosts` | `TWD` | 25 | D | 10495400000 |
| `FinanceCosts` | `USD` | 8 | D | 320100000 |
| `InterestExpenseOnBorrowings` | `TWD` | 25 | D | 150800000 |
| `InterestExpenseOnBonds` | `TWD` | 25 | D | 19278100000 |
| `InterestExpenseOnLeaseLiabilities` | `TWD` | 16 | D | 373400000 |
| `InterestCostsCapitalised` | `TWD` | 8 | D | 9310300000 |
| `ProfitLossBeforeTax` | `TWD` | 25 | D | 1405840000000 |
| `ProfitLossBeforeTax` | `USD` | 8 | D | 42874000000 |
| `IncomeTaxExpenseContinuingOperations` | `TWD` | 25 | D | 248316100000 |
| `IncomeTaxExpenseContinuingOperations` | `USD` | 8 | D | 7572900000 |
| `ProfitLossAttributableToOwnersOfParent` | `TWD` | 25 | D | 1158380200000 |
| `ProfitLossAttributableToOwnersOfParent` | `USD` | 8 | D | 35327200000 |
| `ProfitLoss` | `TWD` | 25 | D | 1157523900000 |
| `ProfitLoss` | `USD` | 8 | D | 35301100000 |
| `BasicEarningsLossPerShare` | `TWD/shares` | 25 | D | 44.68 |
| `BasicEarningsLossPerShare` | `USD/shares` | 8 | D | 1.36 |
| `DilutedEarningsLossPerShare` | `TWD/shares` | 25 | D | 44.67 |
| `DilutedEarningsLossPerShare` | `USD/shares` | 8 | D | 1.36 |
| `WeightedAverageShares` | `shares` | 24 | D | 25927600000 |
| `AdjustedWeightedAverageShares` | `shares` | 10 | D | 25929700000 |
| `NumberOfSharesIssuedAndFullyPaid` | `shares` | 18 | I | 25932700000 |
| `CashAndCashEquivalents` | `TWD` | 35 | I | 2127627000000 |
| `CashAndCashEquivalents` | `USD` | 17 | I | 64886500000 |
| `CurrentFinancialAssetsAtAmortisedCost` | `TWD` | 13 | I | 101971300000 |
| `CurrentFinancialAssetsAtAmortisedCost` | `USD` | 6 | I | 3109800000 |
| `CurrentFinancialAssetsAtFairValueThroughOtherComprehensiveIncome` | `TWD` | 14 | I | 192202700000 |
| `CurrentFinancialAssetsAtFairValueThroughOtherComprehensiveIncome` | `USD` | 7 | I | 5861600000 |
| `CurrentFinancialAssetsAtFairValueThroughProfitOrLoss` | `TWD` | 17 | I | 207700000 |
| `CurrentFinancialAssetsAtFairValueThroughProfitOrLoss` | `USD` | 8 | I | 6300000 |
| `CurrentTradeReceivables` | `TWD` | 17 | I | 270683200000 |
| `CurrentTradeReceivables` | `USD` | 8 | I | 8255100000 |
| `Inventories` | `TWD` | 17 | I | 287868800000 |
| `Inventories` | `USD` | 8 | I | 8779200000 |
| `CurrentAssets` | `TWD` | 17 | I | 3088352100000 |
| `CurrentAssets` | `USD` | 8 | I | 94185800000 |
| `PropertyPlantAndEquipment` | `TWD` | 25 | I | 3234980100000 |
| `PropertyPlantAndEquipment` | `USD` | 8 | I | 98657500000 |
| `IntangibleAssetsAndGoodwill` | `TWD` | 27 | I | 26282500000 |
| `IntangibleAssetsAndGoodwill` | `USD` | 8 | I | 801500000 |
| `Assets` | `TWD` | 17 | I | 6691764700000 |
| `Assets` | `USD` | 8 | I | 204079400000 |
| `TradeAndOtherCurrentPayablesToTradeSuppliers` | `TWD` | 17 | I | 72800600000 |
| `TradeAndOtherCurrentPayablesToTradeSuppliers` | `USD` | 8 | I | 2220200000 |
| `TradeAndOtherCurrentPayablesToRelatedParties` | `TWD` | 17 | I | 1426000000 |
| `TradeAndOtherCurrentPayablesToRelatedParties` | `USD` | 8 | I | 43500000 |
| `CurrentPortionOfLongtermBorrowings` | `TWD` | 16 | I | 59857900000 |
| `CurrentPortionOfLongtermBorrowings` | `USD` | 7 | I | 1825500000 |
| `LongtermBorrowings` | `TWD` | 10 | I | 31824400000 |
| `LongtermBorrowings` | `USD` | 5 | I | 970500000 |
| `NoncurrentPortionOfNoncurrentBondsIssued` | `TWD` | 17 | I | 926604500000 |
| `NoncurrentPortionOfNoncurrentBondsIssued` | `USD` | 8 | I | 28258700000 |
| `CurrentLiabilities` | `TWD` | 17 | I | 1308655900000 |
| `CurrentLiabilities` | `USD` | 8 | I | 39910200000 |
| `Liabilities` | `TWD` | 17 | I | 2412493100000 |
| `Liabilities` | `USD` | 8 | I | 73574000000 |
| `EquityAttributableToOwnersOfParent` | `TWD` | 17 | I | 4244266500000 |
| `EquityAttributableToOwnersOfParent` | `USD` | 8 | I | 129437800000 |
| `Equity` | `TWD` | 34 | I | 4279271600000 |
| `Equity` | `USD` | 8 | I | 130505400000 |
| `NoncontrollingInterests` | `TWD` | 17 | I | 35005100000 |
| `NoncontrollingInterests` | `USD` | 8 | I | 1067600000 |
| `CashFlowsFromUsedInOperatingActivities` | `TWD` | 25 | D | 1826177100000 |
| `CashFlowsFromUsedInOperatingActivities` | `USD` | 8 | D | 55693100000 |
| `PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` | `TWD` | 25 | D | 956006500000 |
| `PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` | `USD` | 8 | D | 29155400000 |
| `DepreciationExpense` | `TWD` | 25 | D | 653610500000 |
| `DepreciationExpense` | `USD` | 8 | D | 19933200000 |
| `AmortisationExpense` | `TWD` | 25 | D | 9186100000 |
| `AmortisationExpense` | `USD` | 8 | D | 280200000 |
| `AdjustmentsForSharebasedPayments` | `TWD` | 16 | D | 1242700000 |
| `AdjustmentsForSharebasedPayments` | `USD` | 6 | D | 37900000 |
| `ExpenseFromSharebasedPaymentTransactionsInWhichGoodsOrServicesReceivedDidNotQualifyForRecognitionAsAssets` | `TWD` | 8 | D | 1646200000 |
| `DividendsPaidClassifiedAsFinancingActivities` | `TWD` | 25 | D | 363055200000 |
| `DividendsPaidClassifiedAsFinancingActivities` | `USD` | 8 | D | 11072100000 |
| `DividendsPaid` | `TWD` | 25 | D | 414915500000 |
| `IncreaseDecreaseThroughTreasuryShareTransactions` | `TWD` | 3 | D | -3089200000 |

Validated appendix extraction: 93 exact archived rows. Both source checksums were independently verified. No golden tests or production mappings were generated.

## Follow-up: original TSM FY2025 filing review, 2026-09-12

This follow-up resolves the currency/ADS questions and selected FY2024 scope
questions from the initial Company Facts-only analysis above. It uses a separate
source: [archived FY2025 filing](evidence/raw/TSM-filing-20260911T143353489715Z.html.gz),
recorded in [filing-manifest.json](evidence/filing-manifest.json), accession
`0001628280-26-025362`, retrieved
`2026-09-11T14:33:53.489715+00:00`. The decompressed 10,355,816 bytes hash to
`c3ebd05cd8fb383f53fc21a0ac497ee12cf908b709c380f9bec4f39c4916647b`;
this checksum was recomputed and matched. The manifest retains the earlier
IncompleteRead attempt as a separate failed transport event.

### Currency and instrument basis verified in the original filing

The Exchange Rates discussion and Note 3 state that TSMC reports in New Taiwan
dollars. USD amounts are reader-convenience translations, generally using
NT$31.37 per US$1.00 at December 31, 2025. This is the filing's stated historical
translation basis, not a market FX series or a valuation assumption. The filing
does not assert that its amounts could actually be exchanged at that rate.
[Original 20-F, Exchange Rates and Note 3](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/tsm-20251231.htm)

The Inline XBRL unit id `twd` measures `iso4217:TWD`; `usd` measures
`iso4217:USD`. The per-share unit ids `twdPerShare` and `usdPerShare`
divide the respective currency by `xbrli:shares`. NT$, NT dollars and New
Taiwan dollars in prose refer to this TWD unit; do not invent an NTD unit key.
Financial statement monetary presentation is in millions, while EPS is in
currency per share. For example, cash/equivalents fact `f-63` carries
`scale="6"`, but EPS facts below carry `scale="0"`.

The filing explicitly states that one ADS represents five common shares.
Its cover identifies 25,932,524,521 common shares, par value NT$10, outstanding
at December 31, 2025. This agrees exactly with the archived Company Facts DEI
row. Item 10's capital description repeats that count for December 31, 2025
and February 28, 2026; it must not be labelled a live September 2026 share count.
[Original 20-F, cover, share-ownership footnote and Item 10](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/tsm-20251231.htm)

| Inline fact id | Tag | Unit id | Context | Printed value | Scale | Meaning |
| --- | --- | --- | --- | ---: | ---: | --- |
| f-28 | dei:EntityCommonStockSharesOutstanding | shares | c-3 | 25,932,524,521 | 0 | Ordinary/common shares at 2025-12-31 |
| f-384 | ifrs-full:BasicEarningsLossPerShare | twdPerShare | c-1 | 65.47 | 0 | FY2025 ordinary-share EPS |
| f-385 | ifrs-full:BasicEarningsLossPerShare | usdPerShare | c-1 | 2.09 | 0 | FY2025 ordinary-share EPS, convenience USD |
| f-392 | ifrs-full:BasicEarningsLossPerShare | twdPerShare | c-9 | 327.37 | 0 | FY2025 equivalent ADS EPS |
| f-393 | ifrs-full:BasicEarningsLossPerShare | usdPerShare | c-9 | 10.44 | 0 | FY2025 equivalent ADS EPS, convenience USD |

Context `c-3` is the 2025-12-31 instant. Context `c-1` covers
2025-01-01 through 2025-12-31 without a segment. Context `c-9` has the same
duration but adds `ifrs-full:ClassesOfShareCapitalAxis` =
`tsm:AmericanDepositarySharesMember`. Thus identical tag/unit/period alone
does not distinguish ordinary and ADS EPS in the original filing. This is
concrete evidence for retaining dimensions in any later original-filing adapter.

The statement also presents FY2024 ordinary basic EPS of 44.68 TWD and equivalent
ADS EPS of 223.39 TWD in explicit comparative columns. A fivefold multiplication
of an already rounded ordinary EPS does not necessarily reproduce the separately
rounded ADS EPS. Preserve reported values and instrument context; any conversion
needs an explicit transform and precision policy. Note 27 identifies the
denominators as weighted-average common shares, including the FY2024 basic
25,927.6 million and diluted 25,929.7 million shares. These are not ADS counts.
[Original 20-F, EPS statement rows and Note 27](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/tsm-20251231.htm)

### Explicit FY2024 comparative context resolves three scope hazards

The findings below use the FY2024 column and duration context `c-6`
(2024-01-01 through 2024-12-31) in this FY2025 filing. They are not inferred
from FY2025 figures. They validate the same amounts in the older API anchor
while retaining this later source accession and filed date separately.

| Question | Verified FY2024 comparative context | Mapping consequence |
| --- | --- | --- |
| Cash dividends vs equity appropriations | Equity statement `DividendsPaid` fact f-506, scale 6, is 414,915.5 million TWD under earnings appropriations. Cash-flow statement `DividendsPaidClassifiedAsFinancingActivities` fact f-986, scale 6, is 363,055.2 million TWD. | For this TSM era, exclude DividendsPaid as a cash-payment fallback. The financing cash-flow tag is the supported cash-paid observation; equity appropriations are a separate scope. |
| SBC expense vs cash-flow addback | Note 29's FY2024 employee-benefit table separates equity-settled SBC of 1,242.7 million TWD and cash-settled SBC of 403.5 million, reporting total expense of 1,646.2 million. Cash-flow addback f-734 is 1,242.7 million; total-expense f-3009 is 1,646.2 million. | The difference is verified scope, not bad data. A cash-flow-addback concept can use the former; it must not be labelled total SBC expense. |
| Finance costs vs gross interest | Note 24's FY2024 table includes bonds 19,278.1, leases 373.4, bank loans 150.8 and other interest 3.4 million TWD, then deducts capitalized interest 9,310.3 million to report FinanceCosts 10,495.4 million. Facts f-2610 and f-2607 carry the total and capitalized amount. | FinanceCosts is expensed interest after capitalization in this inspected era. Gross borrowing costs and cash interest paid remain different measures. |

Source: [original 20-F, comparative equity/cash-flow statements and Notes 24/29](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/tsm-20251231.htm).
These observations supersede the corresponding pending-note questions earlier
in this document; no production mapping priority or concept rename is enacted.

### Endpoint coverage and review result remain separate

The original FY2025 filing contains IFRS Inline XBRL facts and supplies the
source context above. That does not insert them into the captured Company Facts
response: its FY2025 IFRS row count remains zero, with FY2024 as the latest
observed financial period. The endpoint gap is not caused by an NTD-versus-TWD
unit spelling mismatch in this filing. Its underlying cause is not established
by this research.

Reviewed the TSM/KHC portions of `concept-map.md`. The ownership distinction,
exact-period selection, KHC error-versus-recast distinction, and missing FY2025
policy are supported. Beyond removal of hypothetical unobserved tags being
handled by root, the substantive correction is TSM DividendsPaid: its role as
equity appropriations is now verified, so it should be explicitly excluded
from cash-dividend selection for this era. The SBC and FinanceCosts conditions
can now cite their verified comparative note scopes above.
