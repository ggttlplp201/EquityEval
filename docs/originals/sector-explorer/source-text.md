# Sector Explorer — source transcription

Original document order; B identifiers are transcription references, not financial concepts.

## B001
EquityEval sector explorer

## B002
New feature specification for Codex   •   Graphs and sector comparisons

## B003
Build a graph-based view of whole sectors: compare their P/E and other key ratios, track growth over time, and see how widely that growth is shared among companies. The view should help the user choose sectors for further research while keeping business growth, valuation and investment returns distinct.

## B004
Delivery scope. This is a separate, additive feature. Keep the current fundamentals implementation running under its existing spec. Schedule Sector Explorer after its calculation, source-tracking and comparison prerequisites are available; share those components rather than creating a second ratio engine.

## B005
The main screen is a graph

## B006
Default to a horizontal bar chart of sector-wide trailing P/E. Show every sector in the selected market universe, including visible unavailable rows. Let the user switch the metric or open a sector to see its history and company distribution. Tables support drilldown and accessibility; graphs are the primary interface.

## B008
Graph example: six sectors are shown for layout only. Production includes the full selected sector list, dates, coverage and tooltip details. “Sector total” and “median” are different calculations, defined on page 3.

## B009
What users should be able to answer

## B010
Which sectors have higher or lower measured multiples? Is sector revenue expanding? Are most companies improving, or only a few large ones? How does today compare with that sector’s own history? Growth alone does not establish that today’s stock prices offer attractive future returns.

## B012
Required graphs and interactions

## B013 — table

| Graph | Behavior and interpretation |
| --- | --- |
| Sector comparison bars | One bar per sector. Metric picker: P/E, P/S, P/FCF, revenue YoY, operating margin, FCF margin and growth breadth. Use a shared zero baseline, unit and period. N/M and missing values stay visible as labeled rows, never zero-length bars. |
| Sector history lines | Select up to four sectors; show quarter-end observations for 1, 3 or 5 years where available. Default to the selected metric and same aggregation as the bars. Gaps remain gaps. Hover shows constituent dates, coverage, membership mode and source snapshot. |
| Within-sector distribution | Histogram of eligible company ratios, plus median and 25th–75th percentile markers. Separate counts show loss-makers, zero denominators, stale and missing inputs. Clicking a bin filters the company table; selecting a company opens its fundamentals view. |
| Growth versus valuation scatter | One point per sector; X = trailing P/E, Y = TTM revenue YoY. Equal-size points by default, with optional market-cap sizing. Show the method for each axis. Sectors without meaningful P/E appear in an adjacent unavailable list; no “best investment” quadrant. |

## B015
Graph controls

## B016
Pin universe, taxonomy, as of date, period and calculation method above the graph. Offer Sector total and Typical company views; the metric registry defines their formulas. Put Simple mean under an advanced control for eligible company ratios, with its sample and outlier sensitivity shown. Every control change refreshes all linked graphs from the same result snapshot.

## B017
Keep sector colors consistent across charts. Allow alphabetical or numeric sorting, compare-to-market and sector → industry drilldown. The market reference uses the same metric and method, never an average of sector bars. Where exclusions apply, label it “Market reference — eligible companies” and show coverage and excluded profiles. A company can be pinned on its sector distribution.

## B018
Tooltips expose the definition, numerator and denominator when applicable, eligible and total company counts, market-cap coverage, oldest financial period, quote date and exclusion reasons. Provide a searchable constituent table and keyboard-accessible data table for every chart. Distinguish stale data with text; preserve readable labels on small screens.

## B019
Universe and source requirements

## B020
Start with a declared U.S. operating-equity universe using supported USD financial data. Load a complete, dated issuer roster independently of metric availability. Deduplicate share classes and depositary receipts; align total common-equity capitalization to common earnings. Watchlist-only data must be named “Selected companies,” never “Entire sector.”

## B021
Record taxonomy provider, version and effective assignments. GICS or another approved taxonomy may be used; do not silently translate SIC into GICS or invent classifications. Membership and classification data need an approved source and usage rights. Unknown assignments stay visible in an Unclassified group. [1]

## B023
How sector averages are calculated

## B024
Default to Sector total for P/E, P/S, P/FCF, revenue growth and margins. Offer Typical company as a separate view. Use Decimal calculations and the fundamentals spec’s period, scope, currency and denominator safeguards. Formulas below are EquityEval policy; they need not reproduce a provider’s float-adjusted index figures. [2]

## B025 — table

| Measure | Sector total | Typical company |
| --- | --- | --- |
| P/E | Sum common-equity market caps / sum TTM income available to common. Retain eligible losses. Sum earnings ≤ 0 → N/M. | Median valid positive-earnings company P/E; label “among profitable companies.” |
| P/S and P/FCF | Sum market caps / sum matching revenue or FCF. Retain negative FCF. Denominator ≤ 0 → N/M. | Median valid company multiple; show positive-denominator eligibility share. |
| Operating and FCF margin | Sum operating income or FCF / sum revenue, including losses and cash use. Require positive aggregate revenue. | Median valid company margin; negative margins remain included. |
| Revenue YoY | For one matched issuer set, sum current TTM revenue / sum prior TTM revenue − 1. Require positive prior company revenue and comparable periods. | Median valid company revenue YoY; zero or negative bases are separately disclosed. |
| Growth breadth | Count with revenue YoY > 0 / count with valid revenue YoY. Also show counts unchanged and declining. | Same equal-company measure; do not weight by market cap. |
| Profit and cash breadth | Count with positive common earnings or FCF / count with known corresponding amounts. Zero is not positive; missing is not a loss. | Same equal-company measure; show N/M ratio eligibility separately. |
| Concentration | Top five issuers’ market cap / full roster market cap; unavailable if full capitalization is unknown. Compute growth without those five using the same matched set in both periods. | Show the median beside total growth so size concentration is visible. |

## B027
Use exactly the same eligible companies in each aggregate numerator and denominator. Missing earnings excludes both that issuer’s market cap and earnings from aggregate P/E; a real loss does not. Never sum EPS or market-cap-weight individual P/E ratios arithmetically and call the result sector P/E. Simple mean, if selected, is sum of valid company ratios / count and carries its own label.

## B028
Worked calculation. Three issuers each have market cap 100; their common earnings are 10, 1 and −9. Company P/Es are 10×, 100× and N/M. Profitable-company median and simple mean are 55×; sector total P/E is 300 / 2 = 150×. Profitable share is 2/3. All three firms count as having complete earnings data.

## B029
Keep numerator totals and denominator totals available for extreme values. Do not silently trim outliers or cap ratios. If a chart needs a zoomed axis, mark off-screen observations and offer the full range. Preserve unrounded numbers in calculations.

## B031
Coverage history and interpretation

## B032
Coverage is part of every graph

## B033
For each metric, report roster count N, complete input count K, contributing issuer count V for the selected method, and exclusion counts. V includes losses for Sector total P/E and only eligible positive-earnings multiples for its median. Data coverage is K/N; complete loss-making cases count in K even when their company P/E is N/M. Market-cap coverage is the selected method’s contributing cohort cap / full roster cap. If full roster capitalization is unknown, that percentage is unavailable, not estimated from the known subset.

## B034
Proposed comparison gate: at least 10 eligible observations, 70% issuer data coverage and 80% market-cap coverage. Use V for the minimum count. Unavailable cap coverage fails the gate. These are versioned display thresholds, not investment standards. Below a gate, show an outlined “Limited coverage” value and details; suppress comparison ranks, scatter placement and financial summary labels. For a median P/E, always disclose V/K profitable-ratio eligibility even when data coverage is complete.

## B035
Rows distinguish missing, stale, N/M, unsupported profile and limited coverage. A fully covered but tiny sector still shows its factual statistics with “Small sample.” If the roster itself is incomplete, label the entire result “Partial sector universe” and suppress whole-sector claims.

## B036
Growth must describe the same cohort

## B037
Use issuer membership at the current comparison date for both periods of a YoY growth calculation, then match eligible current and prior facts. Show exclusions and cohort changes. Freeze the top-five exclusion set by prior-period market cap; disable this comparison if those rankings are unavailable. Compute both periods on that set. Also show top-five market-cap share at the selected current date, with its separate date label.

## B038
Example: one company grows revenue from 100 to 110; nine others each fall from 10 to 9. Sector revenue grows from 190 to 191 (+0.53%), while median growth is −10% and growth breadth is 10%. Show “Aggregate revenue grew; most observed companies declined.” Never label this broad-based growth.

## B039
History and comparability

## B040
Default history uses membership and public filings available at each historical date, including firms later delisted or reclassified. Save effective and known-at dates to prevent future information entering past results. If historical membership is unavailable, offer “Current members’ history” explicitly and disable historical-sector percentile claims. [3]

## B041
Align TTM basis and exclude stale inputs; show fiscal-end dispersion and restatement policy. A changing roster, fiscal calendar, acquisition or currency effect can change reported growth. Do not call it organic growth without supporting data. Financials and REITs require approved profiles for their applicable measures; generic industrial cash-flow and debt comparisons must not be forced onto them.

## B042
Labels support investigation

## B043
Show growth, profitability, cash generation, valuation context and concentration separately. Use “Aggregate revenue expanding,” “62% of observed companies growing,” or “P/E above this sector’s historical middle range.” Valuation history requires at least 12 eligible quarter-end samples in a three-year window, using the same method and coverage gates. Use linear-interpolated P25 and P75 boundaries; equality stays inside the band.

## B044
No overall investment score or “worth buying” badge. Higher growth with a lower multiple is an observation with a research prompt about persistence, margins, business mix and risk. Sector fundamentals do not directly measure an ETF’s return; index membership, weights, fees and concentration can differ. A sector fund can remain narrowly concentrated. [4]

## B046
Data contract and acceptance criteria

## B047
Add a Sector Explorer backlog item after the ongoing fundamentals work. Reuse normalized company facts, immutable snapshots, pure calculation code, source drawers and chart components. Keep this document separate from the currently executing task’s approved scope.

## B048 — table

| Proposed record | Required fields |
| --- | --- |
| SectorSnapshot | id, universeId/version, taxonomyId/version, membershipMode, membershipSnapshotId, sectorLevel, asOf, capturedBefore, period, currency, metricMethod, rulesVersion, policyVersion, constituentSnapshotIds[], metrics[] |
| SectorMetric | metricId, method, value|null, numeratorTotal|null, denominatorTotal|null, status/reasons, N/K/V, meaningfulCompanyCount, issuerCoverage, capCoverage|null, excludedByReason, median/p25/p75, financialDateRange, quoteDate, cohortId, benchmarkRef |
| Membership and lineage | issuerId, taxonomy code, effectiveFrom/to, knownAt, sourceRef, issuer snapshot ID, included/excluded reason. Preserve the raw facts and contributions behind every plotted value. |

## B050
Propose a sector endpoint during API design: GET /sectors/metrics with pinned universe, date, period and method; a separate snapshotId retrieves an immutable result. Cache by all selection fields, input manifests and methodology versions. Recompute on source revisions or membership changes; save a new result rather than altering old snapshots. Loading, failed refresh and empty history must remain usable.

## B051
Acceptance tests

## B052
1  Aggregate arithmetic. The three-company example on page 3 produces 150× sector P/E, 55× profitable median, two-thirds profitable and 100% data coverage. Changing the loss to −11 makes aggregate earnings zero and P/E N/M, never zero or infinity.

## B053
2  Full-sector integrity. A missing earnings input removes the same issuer from both aggregate sums and reduces coverage. Duplicate listings never double-count an issuer. An incomplete roster cannot present a whole-sector headline; unknown market caps never yield fabricated coverage.

## B054
3  Growth and history. The 190-to-191 example shows +0.53% aggregate growth, −10% median and 10% breadth. Matching, exclusions and top-five membership are identical across its two periods. A later filing or reclassification cannot change a saved historical result.

## B055
4  Graph correctness. Every bar, point and line observation matches its API value and tooltip. Method changes update labels and benchmarks. Unsupported and N/M sectors remain visible; missing history is a gap. Outliers are disclosed, colors are not the only signal, and keyboard and small-screen views retain units and dates.

## B056
5  Safe interpretation. Test threshold boundaries, sector profiles and zero bases. Low coverage suppresses comparative claims. Rapid growth or low P/E never generates a buy, bargain or promised-return label. Company drilldown opens the same source snapshot used in the sector graph.

## B057
References

## B058
[1] S&P and MSCI  Global Industry Classification Standard methodology

## B059
[2] MSCI  Fundamental Data Methodology  Index level ratios

## B060
[3] CFA Institute  Backtesting and Simulation

## B061
[4] Investor gov  Asset Allocation and Diversification
