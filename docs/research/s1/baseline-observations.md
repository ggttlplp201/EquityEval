# AAPL, MSFT, RBLX and COST observations

Status: S1 evidence for review; no production mapping selected. Company Facts
retrieved 2026-09-11. Full rows and exact source labels are retained in
[concept-observations.json](evidence/concept-observations.json); body hashes,
retrieval times and source URLs are in the [manifest](evidence/manifest.json).
The [coverage matrix](coverage-matrix.md) checks all 40 proposed concepts for
these four companies, including candidate absence and different-period rows.

## Exact scope used below

All dollar figures are raw USD, not statement display millions or thousands.
Duration observations use the entire annual interval below; instant observations
use its end unless a different date is stated. `fy=2025`, `fp=FY`, form `10-K`
are filing focus metadata, not a substitute for the actual measured period.

| Company | Accession | Annual start → end | Filed |
| --- | --- | --- | --- |
| AAPL | 0000320193-25-000079 | 2024-09-29 → 2025-09-27 | 2025-10-31 |
| MSFT | 0000950170-25-100235 | 2024-07-01 → 2025-06-30 | 2025-07-30 |
| RBLX | 0001315098-26-000024 | 2025-01-01 → 2025-12-31 | 2026-02-11 |
| COST | 0000909832-25-000101 | 2024-09-02 → 2025-08-31 | 2025-10-08 |

## Apple

- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` is
  **416,161,000,000 USD**; `CostOfGoodsAndServicesSold` is 220,960,000,000 and
  reported `GrossProfit` is 195,201,000,000. The original filing also tags
  product-only revenue with a dimensional context: same tag does not imply
  the same economic scope.
- `OperatingExpenses` is **62,151,000,000**, with combined
  `SellingGeneralAndAdministrativeExpense` **27,601,000,000** and
  `ResearchAndDevelopmentExpense` **34,550,000,000**. These are directly
  reported observations; no sum is used to create a missing raw fact.
- `LongTermDebtNoncurrent` is **78,328,000,000**; `LongTermDebt` is
  **90,678,000,000**; `LongTermDebtCurrent` is **12,350,000,000** and
  `CommercialPaper` is **7,979,000,000**. None of the latter components alone
  is the proposed total current-debt concept. Debt principal/maturity schedules
  are also distinct from carrying amounts.
- Year-end `us-gaap:CommonStockSharesOutstanding` is **14,773,260,000 shares**
  at **2025-09-27**. `dei:EntityCommonStockSharesOutstanding` is
  **14,776,353,000 shares** at **2025-10-17**, the cover-page observation.
  Basic weighted-average shares are **14,948,500,000** and diluted are
  **15,004,697,000** for the annual duration. Preserve all four meanings.
- The same annual filing contains prior comparative intervals, including
  2022-09-25 → 2023-09-30 and 2023-10-01 → 2024-09-28, still marked
  `fy=2025`. Selecting on fiscal-focus year would mix periods.
- `PaymentsForRepurchaseOfCommonStock` is **90,711,000,000**, while
  `PaymentsRelatedToTaxWithholdingForShareBasedCompensation` is
  **5,960,000,000**. Do not merge them. The current generic interest-expense,
  goodwill and total-intangibles candidates lack anchor observations; historical
  tag existence cannot fill those gaps.

## Microsoft

- Customer-contract revenue is **281,724,000,000 USD**, operating income is
  **128,528,000,000**, and `OperatingExpenses` is **65,365,000,000**.
  No combined `SellingGeneralAndAdministrativeExpense` candidate is present in
  this payload. Separate sales/marketing and general/admin figures are not a
  directly reported combined fact.
- `ShortTermInvestments` is **64,323,000,000** and corporate cash is
  **30,242,000,000**. The combined cash/short-term-investment tag is not a cash
  replacement. Current/noncurrent receivables also have separate scopes.
- `PaymentsToAcquirePropertyPlantAndEquipment` is **64,551,000,000** cash paid;
  `PropertyPlantAndEquipmentNet` is **204,966,000,000** carrying amount.
  Neither says that all capital additions were paid in cash.
- The filing's cash-flow line is custom
  **`msft:DepreciationAmortizationAndOther`**, **34,153,000,000 USD** for the
  annual interval (literal `34,153`, scale 6, context
  `C_7102029d-8d6c-44c5-b166-04cf41443b1e`, unit `U_USD`). It is absent from
  Company Facts and includes **other** items. Extracting the custom tag would
  still not make it equivalent to D&A alone. Do not manufacture a combined
  amount from depreciation and intangible amortization.
- `FiniteLivedIntangibleAssetsNet` is **22,604,000,000** at year-end. The
  proposed total-intangibles-excluding-goodwill candidate has no current anchor
  row. A company/era-specific finite-lived equivalence needs note review; it
  is not a general fallback.
- Cash common dividends (`PaymentsOfDividendsCommonStock`) are
  **24,082,000,000**; common repurchases are **18,420,000,000**. Retain cash-flow
  instrument scope and do not substitute dividend declarations.

## Roblox

- Revenue is **4,890,551,000 USD**; `CostOfGoodsAndServicesSold` is
  **1,072,299,000**. `CostsAndExpenses` is **6,122,893,000** and includes cost
  of revenue. It is not the catalogue's operating-expenses-excluding-cost-of-sales
  scope. Neither reported `GrossProfit` nor combined SG&A is supplied by the
  inspected candidate tags.
- The original filing uses custom
  **`rblx:InfrastructureAndTrustAndSafetyExpenses`**, **1,153,454,000 USD**
  (literal `1,153,454`, scale 3, context `c-1`, unit `usd`, annual interval).
  The Company Facts payload has no `rblx` namespace. Original-filing extraction
  must preserve this distinct line rather than relabel it R&D or SG&A.
- Parent `NetIncomeLoss` is **-1,065,057,000**; consolidated `ProfitLoss` is
  **-1,071,618,000**. NCI equity is **-19,504,000**. Negative NCI is not a
  parsing error and must not be clipped to zero.
- Basic and diluted EPS are both **-1.54 USD/shares**; basic and diluted
  weighted-average shares are both **689,612,000 shares**. Loss-period
  anti-dilution must not be replaced with a guessed diluted capital structure.
- Total point-date common shares are **708,359,000** at 2025-12-31. The original
  also reports **661,289,000 Class A shares** using `CommonClassAMember` at that
  date. A combined share count and a traded class are not interchangeable.
- Current short-term investments appear under both `ShortTermInvestments` and
  `MarketableSecuritiesCurrent`, each **1,849,823,000**. Equal duplicate economic
  observations must not be summed. Current dividends-paid candidates are absent;
  repurchase history has no annual anchor observation. Missing remains missing.

## Costco

- Both `Revenues` and `RevenueFromContractWithCustomerExcludingAssessedTax`
  supply **275,235,000,000 USD** at the consolidated annual scope. Net sales
  alone are **269,912,000,000**, with membership fees **5,323,000,000** in the
  original statement. Use the directly reported total for the proposed revenue
  concept, preserving its basis. Same-tag product/segment contexts differ.
- SG&A is **24,966,000,000**; no exact current candidate for gross profit,
  separate operating-expenses subtotal or net trade receivables is observed.
  Do not derive these during ingestion.
- The goodwill candidate occurs in the anchor filing for an earlier instant,
  **2024-09-01**, value **994,000,000**. That is not a 2025-08-31 observation;
  the matrix marks the distinction. A prior comparative cannot silently become
  the current balance.
- `ShareBasedCompensation` is **860,000,000**; net-of-tax allocated SBC is
  **677,000,000**. The latter is not the cash-flow addback's scope.
- `PaymentsOfDividendsCommonStock` is **2,183,000,000**; common repurchases
  are **903,000,000**; withholding payments are **393,000,000**. Preserve
  separate tags and cash-flow meanings.
- Annual periods are 2024-09-02 → 2025-08-31, 2023-09-04 → 2024-09-01,
  and 2022-08-29 → 2023-09-03. The last is a 53-week year. Calendar-quarter
  frames and fixed day counts cannot replace the fiscal intervals.

## Five direct filing checks

[Spot-check evidence](evidence/filing-spot-checks.json) preserves the exact
literal, scale, non-dimensional context, unit, period, accession, expected API
value and both archived hashes for these checks:

| Company / line | Filing literal / scale | Raw API value, USD |
| --- | --- | ---: |
| AAPL consolidated revenue | 416,161 / 6 | 416,161,000,000 |
| AAPL operating cash flow | 111,482 / 6 | 111,482,000,000 |
| MSFT cash PP&E purchases | 64,551 / 6 | 64,551,000,000 |
| RBLX consolidated revenue | 4,890,551 / 3 | 4,890,551,000 |
| COST consolidated revenue | 275,235 / 6 | 275,235,000,000 |

All five source comparisons agree. This is source reconnaissance, not a full
hand-checked normalized statement or executed production golden fixture. Original
filings, including the custom examples above, are archived with their URLs in
[filing-manifest.json](evidence/filing-manifest.json).
