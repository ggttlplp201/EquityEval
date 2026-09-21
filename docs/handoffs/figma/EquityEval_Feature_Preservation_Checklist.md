# EquityEval — feature preservation checklist for Figma

Prepared 2026-09-19 against the verified `milestone/x1-core-graphs` checkpoint
(`a9cb080`). This is a portable design acceptance matrix, not a claim that every
listed feature is implemented. Its purpose is to let a designer change the
layout and visual system without deleting functionality, concealing data limits,
or turning planned capabilities into apparently live product features.

EquityEval is a local-first equity research and valuation workbench. It helps a
person inspect evidence, understand fundamentals, compare sectors, state and
challenge assumptions, and eventually evaluate valuation ranges. It does not
trade or issue BUY/SELL signals. The user wants the interface redesigned before
further feature work, then wants to test the application with real data.

## How to use this matrix

Keep these stable IDs in Figma frame annotations or an accompanying coverage
sheet. For each ID, record its destination frame/component, interaction and
relevant empty/error/limited state. Destinations below describe information
architecture, not mandatory tab names or layouts. Reorganizing is welcome;
removing the behavior or its evidence is not.

Status legend:

- **DEV:** implemented and verified in the fictional-data development interface;
  production source/API acceptance remains open.
- **CORE:** implemented internal calculations, source or workflow foundation;
  this does not mean a corresponding product screen or live source is available.
- **PLAN:** authorized product scope or original P0 requirement whose complete
  UI/workflow is not implemented.
- **P1 / P2:** retained original deferred roadmap; design its place and dependencies
  without presenting it as working now.
- **REVIEW:** policy, data rights or shared-contract decision remains open. Show
  the unresolved dependency; a design choice cannot approve it.

The four Sector Explorer graphs are the current visible application. The full
company workspace, watchlist controls, background news agent and delivery
channels are still planned. There is no approved complete real-sector data feed,
production sector snapshot store or public results API at this checkpoint.

## Shared application rules and states

| ID | Status | Suggested destination | Behavior/state that must survive redesign |
| --- | --- | --- | --- |
| G-01 | PLAN; X1 DEV | App shell/navigation | Keep Watchlist → Company and a separate Sector Explorer destination. Make later research workspaces discoverable without implying they are implemented. |
| G-02 | PLAN; X1 DEV | Numeric cells, chart marks, shared evidence drawer | Every financial value is inspectable: source name, accession/URL where applicable, retrieval time, transform/formula chain, source licence, exact input/result identity and applicable dates. No orphan numbers. |
| G-03 | CORE / PLAN | Evidence, assumption and output components | Visually separate immutable sourced facts, versioned human assumptions and derived conclusions. An editable conclusion must not masquerade as a source fact. |
| G-04 | CORE / PLAN | Global and local date/context controls | Preserve reporting period, balance-sheet date, quote date, evaluation date, filing cutoff and capture vintage. A single generic “as of” label cannot collapse distinct meanings. |
| G-05 | CORE / PLAN; X1 DEV | History controls/header | Clearly distinguish as-reported/filing-date reconstruction, later-restated views and strict workspace-as-known evidence where supported. Never blend modes without a label. Unknown intraday knowledge remains unknown. |
| G-06 | CORE / PLAN; X1 DEV | Values, badges, charts and tables | Distinguish missing, N/A/unsupported, N/M/nonmeaningful, stale, invalid, limited coverage and empty universe. No zero substitution; N/M is not a measured zero. Explain why an output is unavailable. |
| G-07 | CORE / PLAN; X1 DEV | Refresh and result history | Keep loading, pending, failure and current snapshot identity visible. After failure, any prior successful result is separately dated; it is never relabelled as freshly recomputed. |
| G-08 | CORE / PLAN | Source/worker settings, shared status | Delayed quotes show age and delay. Local monitoring shows worker/host availability; do not imply collection while the laptop sleeps or the worker is stopped. |
| G-09 | PLAN | Company switcher | Keyboard-first ticker switching; resolve issuer, exchange and instrument ambiguity. Do not silently exchange ordinary shares for ADS or another share class. |
| G-10 | PLAN; X1 DEV | Entire app | Dense usable information hierarchy, keyboard actions, visible focus, accessible chart alternatives, non-color-only states, mobile-readable units/dates and manageable table overflow. |
| G-11 | PLAN | Saved run/history/export | Assumption changes create new model runs; preserve parent/version relationships. Export a run as JSON and a readable Markdown memo. No destructive editing of saved results. |
| G-12 | PLAN | Valuation outputs | Present supported ranges, assumptions and sensitivity. Never invent a single fair-value certainty, probability distribution, BUY/SELL badge or broker action. Sensitivity ranges are not probability intervals. |
| G-13 | PLAN | Source configuration | Show configured/unconfigured/denied/failed sources and permitted usage. Credentials and account setup are separate from financial results; missing credentials do not become missing-company facts. |

## X1 — Sector Explorer: all four graphs are primary

All **DEV** rows refer to the fictional fixture route. `/sectors` currently shows
real-data prerequisites; `/development/sectors` is an explicitly fictional
verification interface. The latter is not a complete U.S. market sample.

| ID | Status | Suggested destination | Behavior/state that must survive redesign |
| --- | --- | --- | --- |
| X-01 | DEV | Sector Explorer header | Persistent fictional-data label in demonstration mode. In the real-data entry state, show explicit missing prerequisites instead of substituting demo observations. |
| X-02 | DEV; production PLAN | Pinned context bar | Pin and expose universe/version, taxonomy/version, date, TTM period, currency, membership mode, calculation/policy revision and snapshot identity. Linked charts must use one coherent frozen result context. |
| X-03 | DEV | Main horizontal comparison bars | Default to trailing P/E and **Sector total**. Show every declared sector, including Unclassified and unavailable sectors. Bars are the primary comparison interface; the table supports them. |
| X-04 | DEV | Metric switcher | Preserve P/E, P/S, P/FCF, TTM revenue YoY, operating margin, FCF margin, growth breadth, profit breadth and cash breadth with units and definitions. |
| X-05 | DEV | Method switcher and chart title | Distinct **Sector total**, **Typical company (median)** and advanced **Simple mean**. Label positive-earnings company P/E as “among profitable companies.” Breadth is an equal-company count ratio, not a method-weighted valuation. |
| X-06 | DEV | Comparison controls | Alphabetic and eligible numeric ordering. Limited/unavailable rows remain visible and do not gain comparative ranks. Never silently hide a sector because its inputs are poor. |
| X-07 | DEV | Market-reference mark/detail | Show a benchmark recomputed from the eligible issuer universe with the same method and visible coverage. It is not an average of sector bars. |
| X-08 | DEV | Bar/sector drilldown | Selecting a sector links detail, distribution and company table. Support evidenced industry drilldown and a clear return path; classification must not be inferred from a company name. |
| X-09 | DEV | Historical trend graph | Select up to four sectors with distinguishable series encodings (D028 adopts one hue with matching high-contrast line patterns), quarter-end observations and 1/3/5-year windows. Missing/excluded observations are visible gaps, never interpolated financial values. |
| X-10 | CORE; DEV uses current members | History mode/explanation | Distinguish historical membership from current-members history. Current-members fallback cannot claim historical-sector percentile bands. True historical sector comparisons require per-date membership and knowledge evidence. |
| X-11 | CORE / PLAN | Historical context panel | Historical-middle-range wording requires at least twelve eligible quarter ends within three years with matching policy/method and passing coverage. A one-year chart is not proof of a three-year claim. |
| X-12 | DEV | Company distribution histogram | Preserve histogram, median/P25/P75, exact bin bounds/counts and excluded categories. Selecting a bin filters the company table; support keyboard selection and clearing filters. |
| X-13 | DEV | Distribution/table exclusion summary | Show loss-making, zero/nonmeaningful, missing, stale, invalid and unsupported company counts with reasons; do not disguise excluded issuers as an omitted small footnote. |
| X-14 | DEV | Growth-versus-valuation scatter | Trailing P/E on x, TTM revenue YoY on y; equal point sizes by default, optional capitalization sizing. Sizing never changes either axis. No “buy/avoid” or investment-ranking quadrants. |
| X-15 | DEV | Scatter unavailable list | Limited coverage, N/M and missing sectors remain in an adjacent visible list, not plotted at zero. Explain why each is absent from the scatter. |
| X-16 | DEV | Company table/drawer | Search and pin companies; show company metric, status, reasons and frozen snapshot identity. Opening a constituent reveals the exact evaluated company snapshot used by that sector result, not the latest unrelated data. |
| X-17 | DEV | Coverage panel and tooltips | Define **N = declared deduplicated issuer roster; K = complete usable metric inputs; V = method contributors**. Show K/N, V/K for profitable-company P/E, contributor IDs/exclusions, numerator/denominator totals and cap coverage. |
| X-18 | CORE / DEV | Coverage explanation | Known loss/zero can count in K even when a company multiple is N/M. A missing/invalid capitalization anywhere in the declared roster makes full-roster cap coverage unavailable. Missing does not equal loss. |
| X-19 | CORE / DEV; policy versioned | Limited/small/partial states | Explicit comparison policy is V ≥ 10, K/N ≥ 70%, cap coverage ≥ 80%. Unknown cap coverage fails. Limited values may have outlined marks plus reasons but no ranking/scatter/financial summary claim. Tiny complete groups show Small sample; partial universes cannot claim full-sector coverage. These are display rules, not investment standards. |
| X-20 | CORE / DEV | Formula/method detail | Aggregate P/E is sum complete issuer caps ÷ sum matched income available to common, including real losses. Nonpositive aggregate earnings is N/M. Median/mean use eligible company multiples; they are different questions. No summed EPS, average of sector bars or cap-weighted company-P/E substitute. |
| X-21 | CORE / DEV | Formula/method detail | Aggregate P/S, P/FCF and margins use matching issuer cohorts in both sums; retain negative FCF/income where defined. Growth uses the same current-membership matched issuers in current and prior periods, with positive comparable prior revenue for growth contributors. |
| X-22 | CORE / DEV | Breadth/concentration context | Preserve positive/unchanged/declining growth counts, positive-known earnings/FCF breadth, dated current top-five cap share and growth excluding the prior-cap top five. Unknown ranking disables the latter; prior and current concentration measures are not interchangeable. |
| X-23 | DEV | Chart scales/accessibility | Preserve full ranges and extreme values. No silent outlier trimming or axis caps. Any zoom must expose off-screen values and offer full range. Tooltips/tables retain exact values, units, dates, coverage and methods. |
| X-24 | PLAN / REVIEW | Real-data prerequisites and source setup | Require approved dated operating-equity roster, taxonomy rights/version, effective/known-at membership, complete common-equity cap across classes/ADS, common earnings, compatible TTM/precision/freshness, supported profiles and reviewed immutable API/snapshots. Selected companies must be labelled as such, not an entire sector. |
| X-25 | PLAN | Refresh/history/error frames | Real-source acceptance must cover immutable snapshot reopening, new-source revisions yielding new results, retained prior result after failed refresh, and chart values equal to the API's frozen result. Fixture verification does not establish this. |

Synthetic method examples to retain in documentation or design QA: three caps of
100 with common earnings 10, 1 and −9 give total P/E 150×, median 55× and profit
breadth 2/3. Changing −9 to −11 makes aggregate earnings zero and total P/E N/M.
A cohort growing from 190 to 191 can have aggregate growth about 0.53%, median
company growth −10% and growth breadth 10%; do not call that broad-based growth.
These are illustrative examples, not observations about real stocks.

## F1 — Company Fundamentals and original P0 company views

The source-only calculations and eligible-sample history mathematics exist;
the complete company UI, public result API and stored Fundamentals snapshots do
not. Calendar annual/quarter/YTD/TTM assembly was completed before X1; supported
calendar periods do not imply universal 52/53-week fiscal coverage.

| ID | Status | Suggested destination | Behavior/state that must survive redesign |
| --- | --- | --- | --- |
| F-01 | PLAN | Ratios → Fundamentals | Beginner first pass in about five minutes: **Growth → Profitability → Cash generation → Balance sheet → Valuation**, expandable Returns on capital. Preserve this reading order even if layout changes. |
| F-02 | PLAN | Fundamentals controls | TTM proposed default, latest-quarter YoY context, fiscal-year/historical views, distinct balance-sheet and quote dates. A proposed default is not an already approved universal policy. |
| F-03 | CORE / PLAN | Company history controls | **3-, 5- and 10-year options** are an explicit user requirement. Show sample dates, eligible/excluded counts, policy and insufficiency. Never shorten the selected window silently. These differ from X1's 1/3/5-year graph controls. |
| F-04 | CORE / PLAN | Growth/profitability/cash cards and series | Preserve reported amounts, revenue YoY, gross/operating/consolidated-net margins, CFO, CFO-minus-PPE-capex FCF and FCF margin with exact evidence and compatible periods. Derived gross profit is labelled derived. |
| F-05 | PLAN | Growth/EPS/share detail | EPS amount changes and profit/loss/break-even transitions; growth percentages require eligible bases. Reported, adjusted and forecast EPS differ. Weighted-average diluted shares differ from ownership shares; SBC is not dilution. Split/class/ADS evidence may block comparison. |
| F-06 | PLAN | Balance-sheet and returns sections | Cash/net cash/net debt, debt composition, interest coverage, ROA/ROE and common-versus-consolidated scope with explicit prerequisites. Restricted/client/reserve cash is not freely available cash. No invented cash-runway estimate. |
| F-07 | CORE internal multiples; production PLAN | Valuation section | P/E, P/S and P/FCF need compatible instrument/capitalization and earnings/flow evidence. Forward P/E/PEG need reviewed dated estimates; otherwise unavailable. No revenue-growth substitution for EPS estimates. |
| F-08 | PLAN | Neutral observations/review prompts | At most three distinct, deduplicated factual review prompts: data issues first, then cash/debt, operating trends and valuation context. No aggregate stock score, automatic conviction, price target, bargain/value-trap or buy/sell label. |
| F-09 | CORE / PLAN | History bands and context | Own-history percentile math is not intrinsic value. Insufficient history gives no band/rank. P25/P75 equality stays within the middle band; stale/unsupported data cannot earn a favorable rank. Peer comparison remains P1. |
| F-10 | PLAN | Applicability/coverage panel | Show valid, N/M, stale, missing, invalid and unsupported counts separately. Fully evidenced N/M can be covered but unrankable. Fix applicability by issuer profile, not availability; banks/insurers/REITs/float businesses may need sector-specific interpretation. |
| F-11 | PLAN | Overview summary | Overview and Ratios display the same immutable Fundamentals snapshot/coverage. A refresh does not independently recompute conflicting labels in different tabs. |
| F-12 | PLAN | Financials | Statements, as-reported/latest-restated switch, TTM/quarter/annual, segment and driver breakdown, evidence-linked quality details and later normalized-earnings waterfall. |
| F-13 | PLAN | Overview | Price chart/event markers, available valuation range/current-price placement, ratios/history context, quality flags, next three catalysts and top-five customer concentration/next renewal. Planned outputs remain explicitly unavailable until their engines exist. |
| F-14 | PLAN / P1 | Ratios broader inventory | Do not lose original P/B, earnings/FCF yields, EV/EBITDA/EV/Sales/EV/EBIT, ROIC/ROIIC/ROIC–WACC, EBITDA margin, FCF conversion, DuPont, leverage, working-capital metrics and Piotroski/Altman/Beneish/Sloan families. Their definitions, inputs/applicability and neutral interpretation still need implementing review. |
| F-15 | PLAN | Method/definition help | Explain percentages versus percentage points, flow versus instant dates, source precision/near-zero denominators, gross margin versus unit economics, PPE-capex FCF versus FCFF, negative denominators and extreme margins. Generic EV divided by CFO-minus-PPE FCF is not an approved convention. |

## W1 — Watchlist additions and complete applicable reanalysis

Durable membership/request and SEC/price/macro source stages exist internally.
The product search/add/rerun screens, complete financial stages and monitoring
integration remain planned. “Run analysis” means an analysis workflow, not ML
model retraining.

| ID | Status | Suggested destination | Behavior/state that must survive redesign |
| --- | --- | --- | --- |
| W-01 | CORE / PLAN | Search/add stock | Search ticker/name/exchange, resolve issuer/security/share class and source availability, explicitly choose ambiguous results. Do not silently substitute an ADS or different exchange. |
| W-02 | CORE / PLAN | Add confirmation and progress | Successful addition queues a fresh analysis for that stock through all applicable implemented stages. Repeated clicks coalesce; adding one stock does not imply rerunning the entire watchlist. |
| W-03 | CORE / PLAN | Per-stock analysis progress | Queued, running, stage success, partial, failed, unavailable/configuration issue and unsupported model are distinguishable. Independent financial stages can finish when one source or news stage fails. |
| W-04 | PLAN | Missing-input/assumption step | Reuse an explicitly confirmed assumption version or request missing assumptions. Do not invent discount rates/growth forecasts to force a complete valuation. |
| W-05 | CORE / PLAN | Run analysis again/result history | Every explicit rerun creates a new request/execution and new immutable analysis snapshot, even when a calculation payload is reused. A transport retry belongs to its existing request. Show old/new snapshot comparison. |
| W-06 | CORE / PLAN | Cancel/retry/recovery controls | Cancel explicitly; preserve completed evidence. Retry/resume unfinished stages without duplicate snapshots/alerts. Older late results must not overwrite the newest finished request. |
| W-07 | CORE / PLAN | Remove/re-add | Removing stops future watchlist monitoring and unsent watchlist-only alerts but preserves archived research. It does not necessarily cancel a shared/manual analysis. Re-add creates a fresh membership/baseline without replaying old pending alerts. |
| W-08 | PLAN | Completion and monitoring handoff | New stocks enter N1 topic discovery/baseline and shared macro context when available; selected configured channels can deliver completion alerts. Keep discovery gaps and financial outcomes distinct. |

## N1 — Macro and stock-topic monitoring, inbox and alerts

This entire product feature is authorized but not running at the current
checkpoint. The design must retain all three requested delivery channels and
continuous discovery. A prototype “live” indicator cannot stand in for a worker.

| ID | Status | Suggested destination | Behavior/state that must survive redesign |
| --- | --- | --- | --- |
| N-01 | PLAN | Macro calendar | US CPI, PPI and FOMC; separate statement, scheduled projections, press conference and minutes. Payrolls/PCE are next source additions after adapter checks. |
| N-02 | PLAN | Event detail/time controls | Verified release time/timezone and local conversion; unknown time stays unconfirmed. Handle revised schedules, postponed/cancelled events and distinct stages. Never infer exact dates from a weekday pattern. |
| N-03 | PLAN; defaults REVIEW | Lead-time settings | Advance briefs with configurable lead times, quiet hours and frequency; proposed 24-hour/1-hour defaults are not hardcoded product facts. Separate heads-up, release, correction and assessment-change purposes. |
| N-04 | PLAN | Release brief | Published actual, reference period/units, headline/core, monthly/yearly, seasonal adjustment and revisions. Timestamped consensus only when available; prior-release comparison is not “market surprise.” |
| N-05 | PLAN | Stock topics/profile | Products, competitors, partners, customers, suppliers, industry and regulations; stable identity/aliases, category, why related, affected driver, relationship evidence and freshness. Separate macro context from stock-specific relevance. |
| N-06 | PLAN | Continuous discovery/coverage | Find new relevant announcements with no ticker mention and no existing topic alias, outside market hours and with company pages closed. Follow known topics and broader discovery. CRCL/Open USD/CLARITY/Arc are examples, never a fixed allowlist. |
| N-07 | PLAN | Topic management | Automatically add evidence-supported topics; uncertain relationships remain candidates. Users can add, correct, follow hypotheses, mute/remove and inspect inclusion reasons. Explicit exclusions survive automatic profile refresh. |
| N-08 | PLAN | Evidence and metric history | Preserve passages, publication/event/retrieval times and precision, source origin/revisions, interests, conflicts and metrics/definitions. Reposts are not independent corroboration; balances, activity and revenue are separate measures. |
| N-09 | PLAN | Regulatory/product stages | Legislative proposal/committee/chamber/enactment/implementation are distinct. Testnet is not production use; an announcement is not proof of business success. Unknown milestone dates remain unknown. |
| N-10 | PLAN | Impact assessment | Name what changed and why the stock matters; separate facts/inference, driver direction (favorable/adverse/mixed/insufficient), horizon, offsetting channels, materiality, source reliability and confidence. No invented probability or forced direction. |
| N-11 | PLAN | Assessment evidence/limitations | Show counterevidence, missing metrics, conditions that would overturn the conclusion and next review. Numerical valuation impact requires tested applicable core model and confirmed assumptions; otherwise unavailable. |
| N-12 | PLAN | Price reaction detail | Show observed reaction only with compatible prices, window, session, currency, delay/freshness. Coincident movement is not measured causation or proof an event was priced in. |
| N-13 | PLAN | Combined stock explanation/history | Show reinforcing and offsetting drivers without summing sentiment into fair value or double-counting evidence. Pin topic/profile/relevance versions, cutoffs/model/prompt and superseded assessment. News never silently edits saved facts, assumptions or runs. |
| N-14 | PLAN | Unified calendar/inbox | One durable brief/assessment record, source links, change history and why each affected stock was included. One development may affect several stocks differently; combine delivery while preserving those explanations. |
| N-15 | PLAN | In-app/desktop/email settings | Preserve **all three channels**, channel pause/mute, topic/event mute, verified email setup and desktop/OS permission activation. SEC contact email is a different setting and is not auto-enrolled. |
| N-16 | PLAN | Delivery status/failure | Queued, attempted, provider-acknowledged, failed/retry, disabled, permission-denied or unconfigured states. Provider acknowledgement is not confirmed reading/display. Recheck membership/topic exclusions before send. |
| N-17 | PLAN | Monitoring health | Local versus always-on mode, effective cadence, configured-source coverage, last successful fetch, collection delay/errors, assessment backlog and recovery. Healthy polling with stalled analysis is delayed monitoring, not “no relevant news.” |
| N-18 | PLAN | Outage/catch-up behavior | Quiet hours affect delivery, not collection. Backfill is a baseline, not breaking news. Recover late-indexed/revised stories and missed material developments with original timestamps; label delayed discovery and avoid duplicates. |
| N-19 | PLAN | Budgets/partial coverage | Show source/model limits and incomplete coverage; fair discovery across active stocks. Claim coverage only for configured sources/windows, never the entire internet. Collection depends on worker/host availability. |

## U1 — Help, terminology and first-use teaching

| ID | Status | Suggested destination | Behavior/state that must survive redesign |
| --- | --- | --- | --- |
| U-01 | Draft content; product PLAN | Searchable Help | One versioned manual content source for in-app Help, contextual links and printable/exportable documentation. Screen labels/examples must match the finished interface. |
| U-02 | PLAN | First-use walkthrough | Source setup → resolve/add stock → follow stages → inspect evidence → supply/confirm missing assumptions → rerun → compare immutable results. Explain partial/unsupported results honestly. |
| U-03 | PLAN | Contextual definitions | Plain-English meaning, unit, formula, useful worked example, why it matters and limitations for every implemented input/headline. Keyboard/mobile access cannot rely solely on hover. |
| U-04 | Draft chapters; product PLAN | History/data glossary | Explain issuer/ticker/CIK/security/ADS, annual/quarter/YTD/TTM, filing date/restatement/retrieval vintage, source precision, N/A/N/M, coverage versus usability and 3/5/10-year insufficiency. |
| U-05 | PLAN | Finance/economics glossary | Explain revenue/income/cash/debt/capex/EPS/dilution, ratios, EV/equity, DCF/FCFF/WACC/terminal value, sensitivity versus probability, CPI/PPI/core/headline, basis points, FOMC, consensus/surprise and revisions. |
| U-06 | PLAN | Monitoring walkthrough | Configure three channels, lead times and quiet hours; follow/correct/mute topic; inspect assessment/counterevidence; troubleshoot outages/permissions; explain local worker/sleep and always-on operation. |
| U-07 | DEV chapter; release PLAN | Sector walkthrough | Teach total versus median, N/K/V and cap coverage, exclusions, method changes, graph filtering, current-members history and exact snapshot/source drilldown. Do not describe the fictional fixture as live data. |

## Retained valuation, judgment and advanced research roadmap

These original features must have a place in the long-term navigation/components
and a status in design coverage. They need not all appear as enabled controls in
an initial release. N1 advances specific calendar/news/alert functions; it does
not make all P1/P2 engines available.

| ID | Status | Suggested destination | Behavior/state that must survive redesign |
| --- | --- | --- | --- |
| R-01 | P0 PLAN | DCF → Forward | FCFF bridge from revenue/EBIT/NOPAT/reinvestment; user-set 5–10-year forecast and fade; assumption controls with kind, value/unit, confidence, evidence, rationale and sensitivity. Core results recompute through the backend, not browser financial formulas. |
| R-02 | P0 PLAN | DCF → WACC | Dated risk-free/ERP; regression beta with R²/error/window/scatter, bottom-up beta and manual beta with rationale; debt-cost alternatives and lease/minority/cross-holding treatment. Missing approved inputs remain gaps. |
| R-03 | P0 PLAN | DCF → Terminal value | Gordon-growth/exit-multiple selection, enforced terminal-growth constraint, TV share of enterprise value always visible and high-share flag. Sensitivity is not a probability forecast. |
| R-04 | P1; default REVIEW | DCF → Reverse | Solve one implied variable at current price; compare against achieved history, peers and supported base rates. Preserve reverse-DCF primary-lens intent; whether it is the initial P0 default remains unresolved (D004). |
| R-05 | P0 heatmap PLAN; tornado P1 | DCF → Sensitivity | WACC × terminal growth and growth × terminal margin heatmaps; tornado ranks input sensitivity and pins top three assumptions. No fixed target price substituted for sensitivity context. |
| R-06 | P1 | DCF → Monte Carlo | Input distributions/bounds and correlation matrix; valuation histogram, price marker, percentiles and supported probability output. Do not mock these as computed when only deterministic sensitivity exists (D005). |
| R-07 | P1 | Comps | Editable peer set: SIC/sector, manual and later statistical selection; accounting/profile/fiscal-calendar warnings; regression line, subject highlight, R², residual ranking and justified multiple/implied value. Low sample diagnostic policy remains explicit. |
| R-08 | P1 | Scenarios | Bear/base/bull full assumption overrides, validated probability weights summing to one and required mechanism text. Expected value/return, payoff distribution and upside/downside capture; not arbitrary ±30% haircuts. |
| R-09 | PLAN: small continuity subset advanced; rest P1 | Assumption registry | Every input's value/unit/kind/confidence/source/rationale/setter/date/sensitivity; bulk-clone with inherited age; side-by-side run diff; stale judgment and revised-underlying-data alerts. |
| R-10 | P1, selected calendar scope advanced in N1 | Catalysts | Timeline/date window, user estimated direction/magnitude/confidence already priced in, options-implied move/gap when supported, manual events and resolution/realized-move log. Known earnings, lockups, regulation, maturities, renewals and other sourced dates. |
| R-11 | PLAN: small continuity subset advanced; rest P1 | Thesis | Required dated falsification (“I am wrong if X by Y”), why mispriced, strongest external bear case/link, bias checklist and version history/diff. Save validation is part of the feature, not optional helper text. |
| R-12 | P1 | Human conviction rubric | Individually justified data quality, estimate dispersion, model agreement, durability, fragility, information edge and reflexivity dimensions; missing justification blocks save. This future human thesis rubric is separate from F1/X1; those outputs must not automatically feed a stock score. |
| R-13 | P1 | Conviction/position-size research | Preserve original why-mispriced constraint and eventual capped quarter-Kelly-style heuristic with its assumptions/limitations. It is deferred, not a recommendation or current result. |
| R-14 | PLAN: saved expectation subset advanced; scoring P1/P2 | Prediction/calibration | Dated claim/probability/resolve-by record, resolution/outcome and Brier score; later calibration curve, per-sector hit rate and overconfidence view. Keep historical claims unchanged. |
| R-15 | PLAN under original noise/financials scope | Financials/Noise | GAAP-to-normalized earnings waterfall with explicit adjustments; management add-backs as revenue share over 12+ quarters. Retain separate reported versus user-normalized figures and evidence. |
| R-16 | Original requirement; later engine work | Financials/Noise | Offer YoY and TTM alongside QoQ; seasonality diagnostics/warnings when supported. Do not infer seasonal decomposition is implemented from the presence of time-series charts. |
| R-17 | P2 | Noise → Factors/event study | Market/size/value/momentum/idiosyncratic decomposition; configurable event abnormal-return/CAR windows and comparison with options-implied move. Quantitative causal/event-study claims require this engine. |
| R-18 | P2; relevant subset advanced in N1 | Noise → News | Preserve primary disclosure, analyst target/rating, aggregator and opinion classes; default new-information/primary-disclosure filter. Article frequency is not independent evidence. |
| R-19 | Original future requirement | Base-rate panel | Name-specific consensus accuracy, post-earnings drift, realized/implied earnings moves, analyst-target hit rate and sustained-growth base rates; unavailable datasets stay explicit. |
| R-20 | PLAN: seven-company profile framework advanced; specialist models remain reviewed future work | Business-driver models | SaaS, bank/insurer residual-income or DDM, float/asset-based issuer, marketplace, cyclical, biotech rNPV and SOTP models with appropriate inputs. Generic industrial FCFF must not be applied to every profile. |
| R-21 | P2 | Risk disclosures | Added/removed/materially reworded risk factors, MD&A and critical estimates between filings with source text and dates. |
| R-22 | P2 | Management/capital structure | Proxy compensation metrics/horizons/peer groups; projected dilution from converts/warrants/RSUs/SBC/ATM and realistic buyback offsets. |
| R-23 | Original future requirement; relevant topics advanced in N1 | Business exposures/Overview | Customer/supplier/geographic/channel concentration, contract renewals/exclusivity/change-of-control; regulation and currency revenue/cost/hedging exposure. Keep links to affected business lines and catalysts. |
| R-24 | Original future requirement | Ownership/liquidity | Dual class/control/float, short interest/borrow/days-to-cover, index/13F concentration; ADV/spread and implementable size context. No broker execution. |
| R-25 | Original future requirement | Price/event overlays | Form 4 activity classified planned 10b5-1 versus discretionary; unclassified activity cannot imply discretionary conviction. |
| R-26 | Original future requirement | Thesis/return context | Holding period, resolution horizon and after-tax assumptions; annualized expected return rather than absolute upside as the eventual headline when its model exists. |

## R1 refinement — numerical explanations, continuity and business profiles

Appended 2026-09-19. The original 113 IDs remain stable; these 30 additions bring
this checklist to **143**. See [R1](../../features/R1-business-aware-research.md).
These are authorized design requirements, not implemented application features.
D1 remains UI-first; the first complete data experience follows the seven-name
watchlist before broader sector coverage.

| ID | Status | Suggested destination | Behavior/state that must survive redesign |
| --- | --- | --- | --- |
| E-01 | PLAN | Ratio/history → Why did this change? | Select two exact endpoints; show metric, period, source cutoff, snapshot and comparison kind before explaining. |
| E-02 | PLAN / REVIEW | Mathematical change panel | Deterministic, tested numerator/denominator contributions in appropriate units; visible versioned convention and rounding bound; no AI dependency. |
| E-03 | PLAN | Validity and source details | Preserve source operands, precision, compatible scope/currency/period/method; unavailable attribution retains original facts and reasons. |
| E-04 | PLAN / REVIEW | P/E change | Distinguish price/EPS from capitalization/common-earnings attribution; split/ADS/share-class/session and earnings-basis gates remain. Loss/zero transitions can be N/M, never invented multiples. |
| E-05 | PLAN / REVIEW | EPS change | Matching filing numerator and weighted-average shares, basic/diluted and anti-dilution/two-class evidence. No period-end-share substitution or unreviewed TTM EPS summation. |
| E-06 | PLAN | Change classification | Separate period performance, restatement, newly available data, changed assumptions/profile, changed universe and changed method. |
| E-07 | PLAN | Cross-metric observations | Link each factual observation to matched figures, dates and sources; do not infer business causes from correlation. |
| E-08 | PLAN | Possible business explanations | Cite filing/news support; distinguish management explanation from inference; show alternatives, counterevidence, uncertainty and insufficient-evidence states. |
| E-09 | PLAN / REVIEW | Sector change detail | Same-cohort aggregate bridge only when valid; composition/eligibility/profile changes explicit. Median/mean attribution not approximated by ratio-of-sums math. |
| E-10 | PLAN | Explanation actions and empty states | Open exact evidence; save user expectation; compare versions. AI-disabled flow still works; proposed narrative never rewrites facts/calculations/assumptions. |
| C-01 | PLAN; existing thesis subset advanced | Save expectation | Expectation, why, supporting evidence, weakening/falsification condition and review date/event; reusable from company result/change detail. |
| C-02 | PLAN / REVIEW | Research history | Immutable revision/authorship with exact instrument, source/analysis/assumption/profile context. Reuse thesis/assumption design, no duplicate journal. |
| C-03 | PLAN / REVIEW | Earnings review queue | New eligible earnings evidence and dated review triggers; uncertain/rescheduled event, duplicate update, failed refresh and unchanged evidence states. |
| C-04 | PLAN | Review new evidence | Original reasoning/evidence beside new facts and numerical changes; periods and sources inspectable; no retrospective editing of expectation. |
| C-05 | PLAN | Comparison limitations | Partial, stale, corrected/restated, changed-profile/basis and incomparable evidence remain explicit, not forced proof/disproof. |
| C-06 | PLAN | Retain / revise / retire | User decision and rationale; revision creates linked history. Source updates and AI do not choose the user's new belief. |
| C-07 | PLAN | Authorship and evidence boundary | Facts, deterministic math, user judgment and proposed AI prose visibly distinct. Manual/rule-based operation remains useful without AI. |
| C-08 | PLAN / REVIEW | Draft and active thesis validation | Preserve dated falsification; unknown event date stays unconfirmed. Small continuity does not claim full conviction/Brier/calibration shipped or infer probabilities from prose. |
| B-01 | PLAN | Pilot watchlist | Preserve CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL in supplied order. MSFT/RBLX remain regression fixtures; neither seven names nor a theme is a sector universe. |
| B-02 | PLAN / REVIEW | Analysis profile header | Visible business model, lifecycle by segment and exact instrument; sector/theme only context; profile identity/version and support status. |
| B-03 | PLAN / REVIEW | Profile definition | Relevant metrics, denominator/sign/period rules, peer criteria, required drivers, neutral explanations and supported versus proposed valuation/scenario methods. |
| B-04 | PLAN / REVIEW | Segment/company overlays | Explicit evidence, effective/known dates, author/version and scope; acquisitions or mixed lifecycle do not rewrite earlier periods. |
| B-05 | PLAN / REVIEW | Correct profile | Evidence-backed user correction, comparison and new version; old saved analyses retain old profile/rules and assumptions. |
| B-06 | PLAN | Unavailable metric states | Distinguish N/M, not applicable, missing and unsupported; retain losses/cash/debt/dilution. No missing-data bad score or universal valuation verdict. |
| B-07 | PLAN | Tech family detail | Established software, hardware/semiconductors, early-stage/pre-commercial and mixed platforms have separate economics. No inference that tech means low revenue. |
| B-08 | PLAN | Tokenization family detail | Stablecoin issuer, fee platform/exchange, asset manager, treasury plus operations and direct-token instrument remain distinct. Customer reserves/assets and token prices/volume are not corporate cash/revenue. |
| B-09 | PLAN | Mineral/project lifecycle | USAR/MP require dated operating/development/ramp/integration and product/segment evidence; planned capacity, resource estimates or precursor sales do not prove full commercialization. |
| B-10 | PLAN; later families retained | Mining/energy roadmap | Mineral mining in pilot; MSTR not a miner; Bitcoin-miner support later. Energy production, transport, utilities and renewable development distinct; no extra ticker assumed. |
| B-11 | PLAN / REVIEW | Funding/specialized definitions | Runway stays excluded under current F1 until definitions, cash/claims/period/assumptions and inputs pass review. New specialized metrics do not bypass concepts/schema review. |
| B-12 | PLAN / REVIEW | Sector composition / peers | Show business-model/lifecycle composition and suitable-cohort rationale; separately named filtered cohorts, coverage/exclusions and original X1 gates remain. |

## Conflicts and open decisions designers must not resolve silently

1. **Reverse DCF:** original principles call it default, original phasing places it
   in P1. D004 remains open. Preserve intent and future space; do not invent a
   current reverse-solve result.
2. **Range versus probability:** original principles request a distribution,
   while P0 deterministic DCF precedes P1 Monte Carlo/scenarios. D005 remains
   open. A sensitivity grid cannot be labelled a probability interval.
3. **Scores:** F1 has neutral observations and no automatic stock score or
   conviction; X1 has no sector investment ranking. Original future human thesis
   conviction is a separate P1 feature. It has not been deleted or authorized to
   consume Fundamentals labels automatically.
4. **History:** preserve company Fundamentals 3/5/10 years and separate sector
   trend 1/3/5 years. Three-year company default, freshness/interpretation policy
   and production eligibility still have D021 review items.
5. **Sources/contracts:** fixtures do not approve taxonomy rights, new normalized
   financial concepts, production snapshots, data providers or public endpoints.
   D024 records the concrete Sector Explorer shared-contract proposal.
6. **Original documents versus user changes:** original attachments are preserved
   requirements, not proof of implemented features. The user explicitly added
   N1/W1/U1/F1/X1 and retained long history. Latest milestone records take
   precedence over stale implementation-status sentences in earlier planning
   tables; the original future feature families are retained.

## Design acceptance pass

Also review ratio change → mathematical/evidence split → save expectation → later
earnings evidence → human retain/revise/retire, with AI disabled and changed
profile/period/source states. Verify all seven pilot names and dated profile
composition. Full specialized models remain unavailable until reviewed.

For every ID, mark **covered now**, **represented as planned/deferred**, or
**open decision**, and give its frame/component link. A redesign is not complete
if it has only ideal populated desktop screens. Include the following review
flows and state variants:

- Sector total → median → mean; date/metric switch keeps all graphs and evidence
  coherent; compare benchmark and N/K/V; find an unavailable sector.
- Sector → industry → distribution bin → searched/pinned company → exact source
  snapshot; clear filters and navigate back by keyboard.
- Four-sector history with a missing quarter and explicit current-members mode;
  1/3/5-year sector controls distinct from 3/5/10-year company history.
- Limited/small/partial universe, unknown cap coverage, loss-making N/M,
  unsupported profile, extreme value and empty data, including mobile and focus.
- Watchlist ambiguous instrument → add → queued/partial stages → missing
  assumptions → rerun → old/new comparison; failed refresh, cancellation and
  remove/re-add. Label these as planned interactions until implemented.
- New topic without ticker mention → candidate/supported relationship → impact
  assessment/counterevidence → correction/mute → material revision → one inbox
  item plus three channel states. Show healthy polling with stalled assessment,
  denied desktop permission, unverified email and local-worker downtime.
- Help opens from each headline/term and explains the exact units, dates and
  limitation present on screen. Future DCF/scenario/thesis views retain required
  validation, assumptions and immutable history without fabricated outputs.

## Source map

Paths below are relative to this checklist so they work in a bundle preserving
the repository's `docs` tree. The matrix is self-contained; these files preserve
full definitions, original source blocks and implementation evidence.

- [Original product spec](../../spec.txt): §0 principles; §4 ratios/DCF/plugins/comps/scenarios;
  §5 noise; §6 conviction/calibration; §7 assumptions; §8 catalysts; §9 research
  considerations; §10 UI/interactions; §11 original P0/P1/P2 phasing.
- [Decision register](../../decisions.md): D004/D005 open valuation semantics;
  D013–D018 user extensions; D020–D022 F1; D023–D025 X1 and verified boundary.
- [Milestone index](../../milestones/README.md) and
  [X1 milestone](../../milestones/X1-sector-explorer.md).
- [X1 feature and acceptance map](../../features/X1-sector-explorer.md),
  [preserved Sector spec](../../originals/sector-explorer/source-text.md) and
  [X1 contract proposal](../../design/sector-explorer/contract-proposal.md).
- [F1 feature/conflict map](../../features/F1-fundamentals-guide.md),
  [preserved Fundamentals spec](../../originals/fundamentals/source-text.md),
  [S5 milestone](../../milestones/S5-ratios.md) and
  [metric inventory](../../design/s5/metric-inventory.md). Inventory prose records
  an earlier slice; use the milestone for completed period/X1 prerequisites.
- [W1 watchlist/reanalysis](../../features/W1-watchlist-analysis.md).
- [N1 macro/news](../../features/N1-news-and-macro-agent.md),
  [N1 stock topics](../../features/N1-stock-topic-monitoring.md) and
  [CRCL example](../../features/N1-crcl-topic-example.md).
- [U1 manual requirement](../../features/U1-user-manual.md) and
  [manual index](../../user-manual/README.md).

- [R1 refinements and profile evidence](../../features/R1-business-aware-research.md): D026/D027; appended E/C/B requirements.
