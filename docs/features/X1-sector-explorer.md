# X1 — Sector Explorer

Status: user-authorized separate feature, 2026-09-19. Implementation follows the
current fundamentals prerequisite; this document is not a claim of production
sector coverage. The existing S5 source-metric/history checkpoint is `bd437db`.
Read the [preserved source](../originals/sector-explorer/source-text.md),
[manifest](../originals/sector-explorer/manifest.json) and
[contract proposal](../design/sector-explorer/contract-proposal.md).

The user explicitly requested implementation after current fundamentals work,
with graphs as the main interface, visible methods/coverage/exclusions and reuse
of source tracking. This authorization does not need to be requested again.
Proposed public API, schema, normalized concepts and source activation retain
existing sequential review boundaries. Original documents remain unchanged.

## Product boundary

Sector Explorer is an additive research view. Its default is a horizontal bar
chart of trailing P/E using **Sector total**. Every sector in the declared
universe remains visible, including unavailable rows and an Unclassified group.
Tables support drilldown and accessibility; they do not replace the graphs.

Linked controls pin universe/version, taxonomy/version, date, TTM period,
currency, membership mode and method. Every chart uses one immutable result.
Sector total, Typical company and advanced Simple mean have distinct labels and
calculations. A market reference is calculated from the eligible issuer universe
using the same method, not from an average of sector bars. Industry drilldown
requires evidenced taxonomy assignments; it cannot infer industry from a name.

Required views are comparison bars; quarter-end history for up to four sectors;
company-ratio histograms with median/P25/P75; and sector TTM revenue growth versus
trailing P/E scatter. Low-coverage and nonmeaningful observations remain visible
in an adjacent list rather than at zero. The scatter has no investment-ranking
quadrants. Optional market-cap point sizing requires known capitalization and
must not alter either axis calculation.

Source history controls are 1/3/5 years. Preserve F1's separate 3/5/10-year
comparison option; this feature does not remove the longer fundamentals history.
Sector historical-middle-range wording needs twelve eligible quarter-end samples
within three years, all with the same method and passing coverage gates. A
one-year chart is not evidence for a three-year historical claim.

## Calculation and coverage policy

All arithmetic stays in `packages/core`, using Decimal and existing fundamentals
outputs and precision/provenance safeguards. The renderer only formats values and
positions marks. Retain unrounded company inputs, aggregate totals and formula
revisions. No source facts are overwritten by derived values.

| Measure | Sector total | Typical company / advanced mean |
| --- | --- | --- |
| P/E | Sum eligible complete common-equity capitalization / sum matching TTM income available to common, retaining real losses. Nonpositive sum earnings is N/M. | Median / simple mean of valid positive-earnings company multiples; label “among profitable companies.” |
| P/S, P/FCF | Sum caps / sum matching revenue or CFO-minus-PPE FCF; retain negative FCF. Nonpositive aggregate denominator is N/M. | Median / simple mean of eligible positive-denominator company multiples. |
| Operating / FCF margin | Sum matching operating income or FCF / sum revenue; include negative numerators and require positive aggregate revenue. | Median / simple mean of valid company margins, including negative margins. |
| TTM revenue YoY | Sum current / sum prior revenue minus one for exactly the same matched issuers; each prior company revenue must be positive and comparable. | Median / simple mean of valid company growth. |
| Growth breadth | Positive growth count / valid growth count, with unchanged and declining counts. | Same equal-company measure; no method-dependent cap weighting. |
| Profit / cash breadth | Positive known common earnings / known earnings, or positive known FCF / known FCF. Zero is not positive. | Same equal-company measure; missing is not loss. |

N is the deduplicated declared roster count. K is the count with complete, fresh,
applicable, comparable inputs for the metric, independently of selected method;
fully evidenced losses and exact zeros count in K even when a multiple is N/M.
V is the selected method's contributing count. Missing, stale, invalid or
unsupported inputs stay in N and have explicit reasons; they do not count in K.
For growth, a complete zero/negative prior base can count in K but cannot enter V.
If a ratio's precision is unknown, retain known raw amounts but exclude the
unsupported calculation with a reason. K requires the precision evidence needed
by that metric's calculation. These are internal calculation-policy proposals,
not new storage statuses.

Data coverage is K/N, with no fabricated percentage for N=0. Cap coverage is the
selected method's contributing capitalization / full declared roster cap. ANY
unknown/invalid roster capitalization makes the latter percentage unavailable,
even if the missing issuer is excluded from the selected metric. Unsupported
profiles remain in the denominator; do not quietly redefine the sector.
Profitable-company P/E additionally exposes V/K. Do not confuse earnings-known
profit breadth with the price-and-earnings coverage of P/E.

The source proposes versioned display gates of V >= 10, K/N >= 70%, and cap
coverage >= 80%; unknown cap coverage fails. Pass them as an explicit policy in
core and the development fixture, not a hidden universal investment threshold.
Limited values may render with an outlined mark and reasons but receive no
comparative rank, scatter placement or financial summary label. A tiny complete
sector has factual values plus Small sample. An incomplete roster is labelled
Partial sector universe; it cannot make whole-sector claims even if its known
subset passes the numeric thresholds.

Aggregate numerator and denominator use identical issuer IDs. For P/E, removing
an issuer with missing earnings removes its cap too; a real loss remains. Never
sum EPS, average sector bars, or use arithmetic cap-weighted company P/E as the
sector total. No outlier trimming, winsorization or silent axis caps; a zoomed
view must identify off-screen values and retain a full-range option.

Growth starts with current-date membership and matches both financial periods.
For growth excluding the five largest issuers, freeze the five by prior-period
cap over that declared roster; unknown rankings disable that comparison. Remove
that same set from both matched periods. Show current-date top-five cap share
separately, with its date. No remaining eligible issuer means unavailable growth,
not zero. A deterministic issuer-ID tie break is versioned and disclosed.

## Reuse and exact prerequisites

| Existing component | Reuse | Remaining gap |
| --- | --- | --- |
| `core/inputs.py`, `core/metrics.py` | Selected facts, precision, source amounts, margins, FCF and growth safeguards | Fiscal/YTD/TTM assembly is the current fundamentals prerequisite; sector aggregation must use compatible finished outputs. |
| `core/history.py` | Exact percentile interpolation, explicit windows, missing sample/exclusion records | Sector samples need per-date membership, coverage and method identity before eligibility; never pass current-member history off as historical-sector history. |
| `schema/pit.py` | Frozen query and source selections, filing/capture cutoffs and revision lineage | A later capture does not establish strict historical workspace knowledge. Effective dates and knowledge dates remain separate. |
| `schema/market_selection.py`, S4 provider records | Quote identity, currency, raw/adjusted field separation and market provenance | Its usable flag is not session/calendar/action eligibility. S4b, usable session evidence and approved price retention rights remain open. |
| S2 issuer/security identities | Deduplicate issuers across share classes and depositary receipts | No taxonomy, complete market roster, historical membership or full capitalization record exists. No automatic ticker classification. |
| F1 / W1 / S6 plans | Company result identity, immutable snapshot and guarded publication design | Analysis snapshot storage and the public API have not been implemented or approved. Reuse their eventual contract rather than create a second result system. |
| S8 / U1 plans | Shared provenance, chart accessibility and manual conventions | There are no existing runnable company views/source drawers to pretend to reuse. Production drilldown must open the exact constituent snapshot. |

No live source currently establishes the declared complete U.S. operating-equity
roster or licensed taxonomy. GICS is not inferred from SIC; an alternative also
needs reviewed source, version, rights and effective assignments. Watchlist-only
coverage must be named Selected companies. Unknown assignments remain visible.

Income available to common is not a checked-in normalized concept. Parent or
consolidated net income is not its substitute: the existing JPM source audit
shows different parent and common earnings. A trusted evaluated snapshot may
supply an explicitly evidenced common-income amount in the future; synthetic
fixtures can test that boundary now, without claiming ingest supports it.

Complete capitalization must cover every relevant common-equity class and avoid
counting an ADS and its underlying shares twice. Weighted-average diluted shares
cannot substitute for point-date ownership. USD support does not authorize
implicit FX translation. Financials, insurers, REITs and other special profiles
need explicit per-metric applicability; do not copy generic industrial FCF/debt
comparisons onto them. Mixed profiles stay visible with metric-specific exclusions.

## Delivery phases

1. Finish the active fundamentals period/eligibility slice and record its own
   tests/review. Preserve the previous source-metric checkpoint and full F1 backlog.
2. Implement pure Sector calculations on explicitly trusted evaluated company
   inputs, with the source's arithmetic cases and adversarial coverage/cohort
   fixtures. No new normalized concepts, live providers or database/API contract.
3. Build a graph-first development view fed precomputed, clearly fictional
   snapshots from that core. Controls, tooltips, exclusions and accessibility
   must reflect the fixture exactly. Production starts with unavailable data;
   fictional companies cannot enter normal source storage or appear as live data.
4. Review S6 membership/result/snapshot/cache/public API additions and remaining
   S4/S5 data prerequisites. Implement durable sources and snapshots only after
   the applicable review. No endpoint in the proposal is already implemented.
5. Connect the real graph view and company drilldown, verify full acceptance with
   an approved complete universe, then finish the user manual and release record.

A working development view is useful implementation evidence, but does not meet
production full-sector, real-source, saved-history or API-value acceptance. The
milestone log must distinguish each of these rather than mark X1 finished early.

## Source and acceptance trace

| Source blocks | Requirement | Acceptance evidence |
| --- | --- | --- |
| B003–B010, B047 | Separate additive feature after fundamentals; graphs first | Separate X1 milestone/branch scope; fundamentals checkpoint precedes feature math. |
| B013, B016–B018 | All four charts, linked methods, benchmark, dates, tables, drilldown | Graph marks/tooltips equal precomputed values; later API and exact company snapshot end-to-end check. |
| B020–B021 | Complete dated roster, deduplication, taxonomy rights, Unclassified | Incomplete-roster and conflicting duplicate fixtures; approved real source required for production acceptance. |
| B024–B029, B052 | Aggregate, median, simple mean, negative earnings/FCF, no clipping | Caps 100/100/100 and earnings 10/1/−9 yield total 150×, median/mean 55×, profit breadth 2/3, data coverage 100%; replacing −9 with −11 yields N/M. |
| B033–B035, B053, B056 | N/K/V, full-cap denominator, gate boundaries, profile exclusions | Missing earnings removes both sums; unknown cap yields no cap coverage; threshold equality, zero roster and small/partial universe cases. |
| B037–B043, B054 | Matched growth, concentration, historical membership and bands | 190→191 yields 1/190 growth, −10% median, 10% breadth; identical matched/top-five cohorts; later filing/classification cannot mutate a saved result. |
| B040–B044 | Honest historical mode and neutral wording | Current-members fallback is explicit and cannot generate sector historical percentiles; low coverage suppresses claims; no buy/bargain/return promises. |
| B048–B050 | Immutable typed result/provenance and complete cache identity | Proposed S6 review, then source-revision/membership/cache separation, failed-refresh and immutable retrieval tests. |
| B055–B056 | Graph semantics, accessibility and safe interpretation | Missing values are gaps/visible rows; numerical sorting handles unavailable values; outlier disclosure; keyboard, small-screen, units/dates and same-snapshot drilldown. |

Original references are recorded in the manifest; this integration document does
not claim external methodology or provider rights have been newly verified.
