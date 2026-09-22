# S5 metric inventory

This inventory preserves the original SPEC 4.1 backlog alongside F1. It records
the boundary of the first source-metric slice; it does not declare all S5 complete.
Every future metric requires the same evidence, period, precision and missingness
guards. An absent input never authorizes a fallback to another concept.

| Metric family | First-slice disposition | Remaining dependency |
| --- | --- | --- |
| Revenue amount and YoY growth | Implemented selected source amount and exact comparable calendar-quarter/year pairs | Reviewed 52/53-week fiscal alignment and multi-period/TTM assembly remain later S5. |
| Gross, operating and consolidated net margins | Implemented direct ratios; explicitly named derived gross margin from matching revenue/cost | Approved consolidated net income is absent for some reviewed companies; no parent-income substitution. |
| CFO, PPE-capex FCF and FCF margin | Implemented same-period and same-edition inputs with cash-PPE sign checks | Quarter-from-YTD/TTM reconstruction remains later S5. |
| EPS and growth | Deferred from this slice | Instrument/split compatibility, quarter/TTM EPS policy; loss transitions follow those eligible inputs. |
| P/E trailing, P/B, P/S, earnings yield | Deferred | Usable raw-price/calendar evidence, eligible per-share or complete issuer-capitalization denominator and S4b identity/action basis. |
| Forward P/E and PEG | Deferred | Reviewed dated estimates and compatible horizon/EPS basis; no estimate-provider activation in this slice. |
| Price/FCF and FCF yield | Deferred | Complete issuer capitalization and compatible positive FCF; no one-class shortcut. |
| EV/EBITDA, EV/Sales, EV/EBIT, EV/FCFF | Deferred | Reviewed EV components and enterprise-compatible denominator; EBIT/EBITDA definitions are not supplied by operating income alone. |
| Generic EV/FCF | Unsupported convention | Do not pair EV with CFO-minus-PPE FCF. Resolve a named compatible FCFF definition in S7. |
| Current ratio and reported net working capital | Implemented pure same-date balance-sheet ratio/subtraction; [liquidity boundary](liquidity.md) | Real selected current-assets/current-liabilities inputs; public snapshot integration remains S6. No operating-NWC, cash or health-score inference. |
| ROA, ROE | Deferred | Beginning/end balance alignment; common-income/equity vocabulary and precision for ROE. |
| ROIC, ROIIC, ROIC–WACC spread | Deferred | Reviewed NOPAT, tax, invested-capital and dated WACC policies. |
| EBITDA margin, FCF conversion | Deferred | Reviewed EBITDA or matching net-income denominator and suitability conventions. |
| DuPont | Deferred | Reviewed ownership/scope basis, average balances and decomposition. |
| Net debt/EBITDA, interest coverage, debt/equity, FCF/debt | Deferred | Complete current/noncurrent debt and lease policy; compatible equity; reviewed EBIT/EBITDA and positive interest. |
| DSO, DIO, DPO, cash conversion cycle | Deferred | Reviewed average-balance dates, flow denominators and day-count conventions. |
| Piotroski F-score, Altman Z, Beneish M, Sloan accruals | Deferred | Reviewed formula versions, issuer applicability, historical inputs and neutral interpretation; no automatic conviction/stock score. |
| Share count change and SBC context | Deferred | Reviewed split/class/ADS history and comparison bases; SBC is not identical to dilution. |
| 3/5/10-year own-history bands | Implemented pure aggregation of already eligible, evidence-bearing quarter-end samples with explicit policy | Actual historical input collection, per-sample selection/freshness/calendar and versioned product defaults remain S4/S5/S6. |
| Peer comparisons | P1 | Approved compatible peer universe and eligibility policy; no peer percentile in this slice. |
| Runtime accounting identities | Later S5 validation slice | Reviewed comparable assets/liabilities/equity, cash reconciliation and segment coverage; mismatch raises flags without correction. |

The next slice should complete reviewed period assembly and applicability/freshness
rules before public API and snapshot integration. [Source-metric boundary](source-metrics.md)
and [F1 conflict map](../../features/F1-fundamentals-guide.md) retain the exact gates.
