# Observed candidate coverage at the pinned anchors

Status: S1 research, not approved normalization coverage. Each cell concerns only the exact candidate tags listed in [concept-map.md](concept-map.md), the pinned accession, period and unit. It does not assert every possible filing tag has been searched or that a mapped value is safe.

- **O**: one or more candidate rows observed for the exact period/unit. Economic scope still requires the concept-map conditions.
- **D**: candidate rows occur in the anchor filing, but only for a different period, instant or unit. Do not substitute them.
- **H**: candidate tag exists elsewhere in the captured payload, with no row in the anchor filing. It may be older or later; it is not current evidence.
- **A**: none of the listed candidate tags exists in the captured payload. This is not an assertion that the economic item is zero or absent from the original filing.

All matched rows and other anchor rows, including competing tags and metadata, are in [concept-observations.json](evidence/concept-observations.json). Archived body hashes are verified before extracting these observations. Scope-excluded alternatives are described in the map and company notes.

| # | Proposed concept | AAPL | MSFT | JPM | CRCL | RBLX | TSM | KHC | COST |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `revenue` | O | O | O | O | O | H | O | O |
| 2 | `cost_of_revenue` | O | O | A | A | O | H | O | O |
| 3 | `gross_profit` | O | O | A | A | A | H | O | H |
| 4 | `research_and_development_expense` | O | O | A | A | O | H | O | A |
| 5 | `selling_general_and_administrative_expense` | O | A | A | A | A | A | O | O |
| 6 | `operating_expenses` | O | O | A | O | A | H | A | A |
| 7 | `operating_income` | O | O | A | O | O | H | O | O |
| 8 | `interest_expense` | H | O | O | O | O | H | O | O |
| 9 | `pretax_income` | O | O | O | O | O | H | O | O |
| 10 | `income_tax_expense` | O | O | O | O | O | H | O | O |
| 11 | `net_income_parent` | O | O | O | O | O | H | O | O |
| 12 | `net_income_consolidated` | A | A | H | O | O | H | O | O |
| 13 | `eps_basic` | O | O | O | O | O | H | O | O |
| 14 | `eps_diluted` | O | O | O | O | O | H | O | O |
| 15 | `weighted_average_shares_basic` | O | O | O | O | O | H | O | O |
| 16 | `weighted_average_shares_diluted` | O | O | O | O | O | H | O | O |
| 17 | `common_shares_outstanding` | O | O | O | A | O | O | O | O |
| 18 | `cash_and_cash_equivalents` | O | O | H | O | O | H | O | O |
| 19 | `short_term_investments` | O | O | A | A | O | A | H | O |
| 20 | `accounts_receivable_net` | O | O | A | O | O | H | O | A |
| 21 | `inventory_net` | O | O | A | A | A | H | O | O |
| 22 | `current_assets` | O | O | A | O | O | H | O | O |
| 23 | `property_plant_equipment_net` | O | O | H | O | O | H | O | O |
| 24 | `goodwill` | H | O | O | O | O | A | O | D |
| 25 | `intangible_assets_net_excluding_goodwill` | H | H | A | O | O | A | O | A |
| 26 | `total_assets` | O | O | O | O | O | H | O | O |
| 27 | `accounts_payable_current` | O | O | A | A | O | H | H | O |
| 28 | `current_debt` | A | A | A | A | A | A | A | A |
| 29 | `long_term_debt_noncurrent` | O | O | A | A | O | A | A | O |
| 30 | `current_liabilities` | O | O | A | O | O | H | O | O |
| 31 | `total_liabilities` | O | O | O | O | O | H | O | O |
| 32 | `equity_parent` | O | O | O | O | O | H | O | O |
| 33 | `equity_including_noncontrolling_interests` | A | A | H | O | O | H | O | O |
| 34 | `noncontrolling_interests` | A | A | A | O | O | H | O | H |
| 35 | `cash_from_operating_activities` | O | O | O | O | O | H | O | O |
| 36 | `capital_expenditures_ppe` | O | O | A | O | O | H | O | O |
| 37 | `depreciation_and_amortization` | O | A | A | O | O | A | O | O |
| 38 | `share_based_compensation` | O | O | O | O | O | H | O | O |
| 39 | `dividends_paid` | O | O | O | A | A | H | O | O |
| 40 | `share_repurchases` | O | O | O | O | H | A | H | O |

## Anchor periods

| Company | Accession | Duration start | End / instant | Currency |
| --- | --- | --- | --- | --- |
| AAPL | 0000320193-25-000079 | 2024-09-29 | 2025-09-27 | USD |
| MSFT | 0000950170-25-100235 | 2024-07-01 | 2025-06-30 | USD |
| JPM | 0001628280-26-008131 | 2025-01-01 | 2025-12-31 | USD |
| CRCL | 0001876042-26-000062 | 2025-01-01 | 2025-12-31 | USD |
| RBLX | 0001315098-26-000024 | 2025-01-01 | 2025-12-31 | USD |
| TSM | 0001628280-26-025362 | 2025-01-01 | 2025-12-31 | TWD |
| KHC | 0001637459-19-000049 | 2017-12-31 | 2018-12-29 | USD |
| COST | 0000909832-25-000101 | 2024-09-02 | 2025-08-31 | USD |

TSM FY2025 has no IFRS rows at this accession in this capture. Its FY2024 secondary examples appear in [the IFRS notes](ifrs-and-restatement-observations.md); they are not substituted into this matrix. Cover-page shares have their actual observation date, so a D cell is expected when that differs from year-end. KHC uses FY2018 as its main anchor; the formal FY2017 original/revised comparison is documented separately.

O totals are deliberately not marketed as coverage percentages: some candidates are economically incompatible, and the 40-concept set alone cannot support every planned valuation/ratio.
