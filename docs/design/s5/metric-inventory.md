# S5 metric inventory

This inventory preserves the original SPEC 4.1 backlog alongside F1. Updated
2026-09-22 through the source-only engine handoff; it does not declare full
S5/F1 or application publication complete. See [acceptance and blockers](acceptance-handoff.md).
Every future metric requires the same evidence, period, precision and missingness
guards. An absent input never authorizes a fallback to another concept.

| Metric family | Current disposition | Remaining dependency |
| --- | --- | --- |
| Revenue amount and YoY growth | Implemented selected source amount and exact comparable calendar-quarter/year pairs | Reviewed fiscal quarter/year growth and period assembly are supported; unequal weekly exposures and assembled fiscal TTM growth remain explicit gaps. See [fiscal calendars](fiscal-calendars.md). |
| Gross, operating and consolidated net margins | Implemented direct ratios; explicitly named derived gross margin from matching revenue/cost | Approved consolidated net income is absent for some reviewed companies; no parent-income substitution. |
| CFO, PPE-capex FCF and FCF margin | Implemented same-period and same-edition inputs with cash-PPE sign checks | Calendar and reviewed fiscal YTD/TTM reconstruction are implemented; real calendar/source evidence and S6 publication remain required. |
| EPS and growth | Deferred from this slice | Instrument/split compatibility, quarter/TTM EPS policy; loss transitions follow those eligible inputs. |
| P/E trailing, P/B, P/S, earnings yield | X1 has pure evaluated cap/common-income P/E and cap/revenue P/S helpers; source-backed/per-share paths and P/B/yield remain gated | Usable raw-price/calendar evidence, eligible per-share or complete issuer-capitalization denominator and S4b identity/action basis. |
| Forward P/E and PEG | Deferred | Reviewed dated estimates and compatible horizon/EPS basis; no estimate-provider activation in this slice. |
| Price/FCF and FCF yield | X1 has an evaluated cap/cash-PPE-FCF helper; source-backed publication and yield remain gated | Complete issuer capitalization and compatible positive FCF; no one-class shortcut. |
| EV/EBITDA, EV/Sales, EV/EBIT, EV/FCFF | Deferred | Reviewed EV components and enterprise-compatible denominator; EBIT/EBITDA definitions are not supplied by operating income alone. |
| Generic EV/FCF | Unsupported convention | Do not pair EV with CFO-minus-PPE FCF. Resolve a named compatible FCFF definition in S7. |
| Current ratio and reported net working capital | Implemented pure same-date balance-sheet ratio/subtraction; [liquidity boundary](liquidity.md) | Real selected current-assets/current-liabilities inputs; public snapshot integration remains S6. No operating-NWC, cash or health-score inference. |
| ROA | Implemented pure reported-annual consolidated income / mean opening and closing total assets; [boundary](return-on-assets.md) | Exact same-edition dates and positive endpoints with precision; assembled TTM, 52/53-week calendars and real publication remain later work. |
| ROE | Deferred | Common-income/equity vocabulary and precision; no parent-equity shortcut. |
| ROIC, ROIIC, ROIC–WACC spread | Deferred | Reviewed NOPAT, tax, invested-capital and dated WACC policies. |
| EBITDA margin, FCF conversion | Deferred | Reviewed EBITDA or matching net-income denominator and suitability conventions. |
| DuPont | Deferred | Reviewed ownership/scope basis, average balances and decomposition. |
| Net debt/EBITDA, interest coverage, debt/equity, FCF/debt | Deferred | Complete current/noncurrent debt and lease policy; compatible equity; reviewed EBIT/EBITDA and positive interest. |
| DSO, DIO, DPO, cash conversion cycle | Deferred | Reviewed average-balance dates, flow denominators and day-count conventions. |
| Piotroski F-score, Altman Z, Beneish M, Sloan accruals | Deferred | Reviewed formula versions, issuer applicability, historical inputs and neutral interpretation; no automatic conviction/stock score. |
| Share count change and SBC context | Deferred | Reviewed split/class/ADS history and comparison bases; SBC is not identical to dilution. |
| 3/5/10-year own-history bands | Implemented pure aggregation of already eligible, evidence-bearing quarter-end samples with explicit policy | Actual historical input collection, per-sample source selection/calendar evidence and versioned production defaults remain S4/S6. Internal freshness evaluation now exists. |
| Peer comparisons | P1 | Approved compatible peer universe and eligibility policy; no peer percentile in this slice. |
| Runtime accounting identities | Consolidated assets/liabilities/equity including NCI reconciliation implemented with exact source uncertainty | Cash reconciliation and segment coverage need complete scoped concepts; no repairs or substitutions. |
| Applicability, freshness, coverage and neutral observations | Implemented internal caller-policy evaluation, source reconstruction, whole-roster counts and top-three deduplication | Actual issuer profiles and product defaults remain reviewed production policy; no automatic specialized interpretation. |
| Quarterly revenue trend | Three consecutive direct quarterly YoY assessments with explicit versioned tolerance and edition/context checks | No inferred threshold; assembled-quarter or arbitrary cross-snapshot comparisons remain unsupported. |
| R1 ratio-change attribution | Proposed D027 convention; not activated | Review symmetric allocation and comparison boundary before implementation; no causal inference from ratios. |

The remaining unblocked source-only boundary is complete. The next step is the
[S6 contract review](../s6/publication-contract-proposal.md) before public API
and snapshot integration. [Source-metric boundary](source-metrics.md)
and [F1 conflict map](../../features/F1-fundamentals-guide.md) retain the exact gates.
