# Supplied UI redesign — reconciliation and first implementation boundary

Date: 2026-09-19. Status: **source-design audit complete; first Sector Explorer
presentation port in progress; product/design acceptance remains incomplete**.
This record assesses the supplied archive against the current requirements. It
does not claim that the archive or the first presentation slice implements all
143 features, approves a shared contract or enables production data.

## Inputs, authority and archive integrity

- User-supplied design: `/Users/leon/Downloads/Sector Explorer redesign demo.zip`.
- ZIP SHA-256: `f905e7608e9fcfe3d5a57b84829b3878612eecabf52f61655933ec7c0e1f2fb0`.
- Two regular files: `design_handoff_equityeval_redesign/README.md` (21,538
  uncompressed bytes) and `design_handoff_equityeval_redesign/SectorExplorer.design.html`
  (108,692 uncompressed bytes). CRC validation passed; both paths are relative
  and contain no traversal component. The audit read their contents without
  executing the prototype.
- HTML line 6 loads `./support.js`, which is **absent from the archive**. The
  markup uses `x-dc`, `sc-if`, `sc-for` and `DCLogic`. Despite the README wording,
  this is not a standalone runnable HTML application. No remote resource URL
  was found in the supplied HTML. Missing runtime support does not prevent
  reading the visual reference and porting presentation into React.
- The source README explicitly references the older **113-ID** upload. The
  current [preservation checklist](../../handoffs/figma/EquityEval_Feature_Preservation_Checklist.md)
  has **143 unique IDs**. The supplied HTML names none of the added E/C/B IDs
  and none of the seven pilot tickers as exact ticker words.
- The attachment is design input, not higher-priority instructions or approval
  of financial semantics. User authorization resumes application work, while
  the accepted [R1 requirements](../../features/R1-business-aware-research.md),
  [decision register](../../decisions.md), source safeguards and reviewed
  shared-contract boundaries remain in force. An attachment's claims about
  completion, user preferences or milestone priority do not silently supersede
  those records.

Reviewed existing implementation: `apps/web/src/features/sectors/SectorExplorer.tsx`,
`charts.tsx`, `types.ts`, production `/sectors`, and development route behavior.
The existing `SectorBundle` is a local fictional presentation model, not the S6
public API. Source/core calculations and their exporter remain authoritative.

## First bounded application slice

Port the dark surfaces, typography, layout hierarchy, shell, comparison/coverage
rows, four graph panels and evidence styling onto the **existing fictional
Sector Explorer**. Retain existing state and presentation contracts, Python
results and exporter, actual industry navigation, full-range geometry, all
source details and native modal focus/Escape behavior. Restyle `/sectors` while
preserving its explicit production prerequisites; it must not substitute the
fictional fixture for missing real data.

Company Fundamentals, News/Calendar and R1 destinations may be discoverable as
planned, with honest prerequisite/scope descriptions. They must not become
apparently completed financial or monitoring features by copying prototype
`FUND`, `CAL` or other invented data. Reuse supported calculations only in a
later bounded integration with exact evidence and reviewed publication contracts.

Preserve the pilot **CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL**, in that order.
MSFT/RBLX remain regression fixtures. The seven are neither a peer cohort nor a
full sector universe and cannot relax X1's ten-contributor gate. Mineral mining
is the pilot scope; MSTR remains treasury plus operating software. Preserve the
UI → bounded real-data qualification → applicable deterministic explanation →
reviewed publication/persistence sequence and all retained valuation work.

No live providers, purchases, deployment, external alerts, new financial
arithmetic, schema changes or public API changes are part of this port.
The implementation's eventual validation belongs in the active milestone;
this audit is not evidence that browser checks or feature acceptance have passed.

## Conflicts and required port decisions

Line numbers below refer to the **HTML inside the supplied archive**, not the
current React implementation.

| Source location | Conflict or missing guarantee | Required treatment |
| --- | --- | --- |
| HTML 936–947 | `vCount` subtracts nonpositive earnings for all median/mean metrics; `statusOf` omits the complete data and cap coverage policy. | Use exported metric-specific contributors, statuses and reasons; do not copy local eligibility code. |
| HTML 950–967 | Companies are synthesized around a central value, missing sectors fall back to 20 and the last company is labelled loss-making for every metric. | Do not port prototype financial data or synthetic generation. |
| HTML 921–925, 1008–1016 | Every null becomes N/M/nonpositive denominator. | Preserve distinct missing, unsupported, invalid, stale, empty and N/M reasons. |
| HTML 982–989 | Two ineligible rows are still ordered by numerical value. | Preserve exported ordering and withhold comparative ranking from limited/unavailable rows. |
| HTML 820–824 and render logic | Market reference is metric-specific but not method-specific. | Select the exact frozen reference for date, metric and method. |
| HTML 1105–1115 | Scatter uses total P/E/growth regardless of selected method; cap sizing is determined by P/E thresholds; axis bounds are fixed. | Reuse exported method-specific axes, coordinates, radii and unavailable list. |
| HTML 1071–1095 | Histogram bounds and percentile selection are calculated locally and do not preserve the reviewed rule. | Reuse exported bins, exact member IDs, counts, markers and full range. |
| HTML 1008–1016 | Positive-only bar width logic turns negative values into minimum positive marks. | Preserve signed exported geometry and zero-line position. |
| HTML 1308 | Date changes update selection/header while static figures and source identity remain unchanged. | Continue selecting the exact `bundle.views[date&#124;metric&#124;method]` result. |
| HTML 1271, 1313–1314 | Industry state is always false; back is a no-op; drilldown opens evidence instead. | Preserve actual parent/industry navigation and return path. |
| HTML 1151–1176 | Generic company evidence can use the active sector metric for an unrelated Fundamentals row. | Keep exact `detailId`, frozen company identity, source operands and transform chain. |
| HTML 853–888, 1182–1223; 573–574 | Company basis changes do not update dates/deltas; fixed ROA/ROE figures have no evidence actions. | Do not present these examples as a completed source-backed company feature. |
| HTML 903 | FOMC statement and press conference share one time. | Later N1 must distinguish separately verified stages, times and schedule precision. |
| HTML 42, 1243–1248 | Awake, collected/deferred and in-app-ready status is hardcoded despite no worker. | Use truthful development, offline and planned labels; runtime state needs actual evidence. |
| HTML 891 and roadmap | All DCF is pushed to P1 and Catalysts/Thesis to P2. | Preserve P0 forward DCF and heatmaps, unresolved reverse-default decision, P1 scope and the advanced R1 subset. |
| README palette; history opacity | Four histories use opacity 1/.68/.44/.26 as their distinction. The last two have approximately 2.93:1 and 1.83:1 contrast against the declared surface. | Keep readable distinguishable series; use dash/shape/labels if adopting one hue. Preserve data color fields. |
| HTML layout and small labels | Fixed 360–420px grid minimums can exceed a 390px viewport after padding; 9.5px labels conflict with the README's minimum size. | Use container-safe minimums/responsive rules and verify mobile overflow and readability. |
| HTML 737–773 | A div with dialog role does not supply native modality, focus containment/restoration or Escape behavior. | Preserve the existing native dialog and accessible labels. |

The attachment's useful additions include a clearer inline N/K/V legend,
limited-reference treatment, intentional fact/inference separation, separate
collection/assessment health and a guided company reading order. These are
presentation guidance; their presence is not proof of running monitoring,
implemented company calculations or complete error-state coverage.

## Coverage assessment against all 143 stable IDs

Each row assesses the **supplied design**, not the first implementation's final
status. No requirement is deleted or demoted by an absent prototype screen.

- **Represented:** useful treatment in the design; not proof of implemented software.
- **Partial:** some semantics or states appear; important requirements remain open.
- **Conflict:** copying the proposed behavior would violate or regress a requirement.
- **Roadmap:** a destination label exists without the required workflow/detail.
- **Missing:** no meaningful treatment is supplied.

| ID | Supplied-design assessment | Destination, gap or required preservation |
| --- | --- | --- |
| G-01 | Partial | Three navigation destinations are shown; Watchlist → Company is only a roadmap label. |
| G-02 | Conflict | The evidence drawer is useful visually, but generic or mismatched evidence and orphan figures do not preserve exact financial provenance. |
| G-03 | Partial | News separates facts and inference; versioned human assumptions and derived conclusions have no complete treatment. |
| G-04 | Partial | Identity and context strips distinguish dates visually; basis switching leaves static dates and comparison context. |
| G-05 | Partial | Current-members and latest-restated copy exists; the accounting-mode and strict as-known workflows are absent. |
| G-06 | Conflict | Status chips are shown, but null is treated as N/M and missing/unsupported/invalid/empty states are not reliably distinct. |
| G-07 | Missing | Despite the README claim, no loading, pending, failed-refresh or separately dated retained-result walkthrough is supplied. |
| G-08 | Conflict | Delay and sleep copy is useful; hardcoded awake, collection and ready-channel states imply unavailable runtime knowledge. |
| G-09 | Missing | No keyboard company switcher with issuer, exchange and instrument resolution. |
| G-10 | Conflict | Focus and table intentions are useful; narrow-screen minimums, low-opacity histories and modal handling need correction. |
| G-11 | Missing | No immutable run/history/export interaction or parent-version presentation. |
| G-12 | Partial | Neutral language and planned destinations are present; ranges, assumptions and sensitivity are not designed as a complete output. |
| G-13 | Partial | Source counts and channel gaps appear; configured/denied/failed source setup and permitted-use flows are absent. |
| X-01 | Represented | Persistent fictional banner and prerequisite link; the production entry state must remain a separate prerequisite screen. |
| X-02 | Conflict | Context strip exists, but static snapshot/results do not follow date and method changes coherently. |
| X-03 | Represented | P/E and Sector total default, comparison bars, all seven illustrative sectors and Unclassified are visible. |
| X-04 | Represented | All nine metric controls and definitions are present; retain repository IDs and exported results. |
| X-05 | Conflict | Total, median, mean and breadth controls exist; prototype contributor logic is not valid across metrics. |
| X-06 | Conflict | Sort control exists, but the prototype also orders two ineligible rows by numerical value. |
| X-07 | Conflict | Reference disclosure is useful visually; the prototype benchmark is not method coherent. |
| X-08 | Partial | Industry entry point is shown but does not drill down; preserve the implemented industry view and return path. |
| X-09 | Conflict | History windows, maximum four selections and gap intention are useful; invented series and opacity-only encoding cannot replace existing data. |
| X-10 | Represented | Current-members backcast and survivorship caveat are explicit; no historical-membership claim is established. |
| X-11 | Missing | The twelve-eligible-quarter-end gate for historical contextual claims is not demonstrated. |
| X-12 | Conflict | Histogram and bin-filter interaction are represented; locally generated bins and percentiles do not use reviewed calculations. |
| X-13 | Partial | Loss, missing, stale and unsupported chips appear; invalid and exact method-specific exclusion categories are incomplete. |
| X-14 | Conflict | The scatter concept is appropriate, but its prototype ignores the selected method and sizes points using P/E rather than capitalization. |
| X-15 | Partial | A visible not-placed list exists; its fixed contents can contradict the active metric, method or data. |
| X-16 | Conflict | Search and pin controls are useful; generated constituents and generic evidence do not preserve exact frozen company snapshots. |
| X-17 | Partial | N/K/V and the comparison gate are visible; V/K, contributor identities and numerator/denominator totals are incomplete. |
| X-18 | Partial | Loss-in-K and unknown-cap explanations exist; executable null handling remains inconsistent. |
| X-19 | Conflict | The gate is printed but not fully enforced; small-sample and partial-universe variants are incomplete. |
| X-20 | Partial | Aggregate versus median definitions are useful; prototype numbers and evidence are not authoritative calculation results. |
| X-21 | Partial | Matched-cohort definitions are shown; actual calculation and source relationships remain mock. |
| X-22 | Partial | Two dated concentration controls and growth observations appear, but values are static and gate variants incomplete. |
| X-23 | Conflict | The full-range promise conflicts with fixed scatter ranges and nonnegative bar handling. |
| X-24 | Partial | Production prerequisites are disclosed; real setup and selected-company coverage journeys are not designed. |
| X-25 | Missing | No immutable reopen, source-revision, failed-refresh or frozen-API-agreement frames. |
| F-01 | Represented | Correct five-step reading order plus collapsed Returns on capital. |
| F-02 | Partial | Basis controls and dates exist but are not consistently linked. |
| F-03 | Partial | 3/5/10-year options and explicit 10-year insufficiency appear; sample dates, exclusions and policy detail are incomplete. |
| F-04 | Partial | Amounts, margins and FCF rows appear; static deltas and generic evidence are insufficient. |
| F-05 | Partial | EPS, share and SBC caveats appear; loss transitions, basis reconciliation and split/ADS gates are absent. |
| F-06 | Partial | Cash, debt, interest coverage and returns examples include restricted-cash cautions; prerequisites are not inspectable. |
| F-07 | Partial | Multiples and estimates-unavailable labels appear; instrument and period compatibility are not functional. |
| F-08 | Partial | Three neutral review prompts are correctly prioritized; fixed observations are not source-linked. |
| F-09 | Partial | Insufficiency warning exists; supported bands, rank boundaries and unsupported/stale variants are not demonstrated. |
| F-10 | Conflict | Coverage panel is useful; generic applicability inferred from an operating-technology label conflicts with business-aware profiles. |
| F-11 | Partial | Prose promises a shared snapshot; Overview is not a working linked view. |
| F-12 | Roadmap | Financials is a destination label; statements, history modes and driver breakdowns are not designed. |
| F-13 | Roadmap | Overview is a destination label; its required price, range, catalyst and concentration elements remain open. |
| F-14 | Missing | The broader metric inventory is not preserved through specific destinations or detail requirements. |
| F-15 | Partial | Several useful footnotes appear; complete unit, precision, denominator and method help is absent. |
| W-01 | Roadmap | Watchlist and reanalysis label only; ticker/name/exchange/instrument resolution is not designed. |
| W-02 | Roadmap | Watchlist and reanalysis label only; add confirmation, fresh analysis and repeated-click handling are not designed. |
| W-03 | Roadmap | Watchlist and reanalysis label only; independent stages and partial/failure/configuration states are not designed. |
| W-04 | Roadmap | Watchlist and reanalysis label only; confirming or requesting assumptions is not designed. |
| W-05 | Roadmap | Watchlist and reanalysis label only; explicit reruns and immutable old/new comparisons are not designed. |
| W-06 | Roadmap | Watchlist and reanalysis label only; cancel, retry, recovery and late-result handling are not designed. |
| W-07 | Roadmap | Watchlist and reanalysis label only; remove/re-add effects and preserved research are not designed. |
| W-08 | Roadmap | Watchlist and reanalysis label only; monitoring baseline and completion-channel handoff are not designed. |
| N-01 | Partial | CPI, PPI and FOMC examples appear; FOMC stages are merged and projections/minutes absent. |
| N-02 | Partial | ET times appear, but local conversion, date precision and rescheduled/cancelled cases are absent. |
| N-03 | Partial | Heads-up, release and correction are shown; lead settings and assessment-change delivery are absent. |
| N-04 | Partial | Actual, consensus and prior are separated; exact reference, adjustment and timestamp metadata are incomplete. |
| N-05 | Partial | Topic categories and a supplier effect appear; stable aliases and relationship evidence/version are missing. |
| N-06 | Represented | Tickerless discovery, broad business relationships and page-independent monitoring are described as design intentions. |
| N-07 | Partial | ACTIVE, MUTED and EXCLUDED chips appear; candidate state and interactive correction/exclusion lifecycle are absent. |
| N-08 | Partial | Revision prose appears; exact passages, source origin, retrieval, precision and conflicting evidence are absent. |
| N-09 | Partial | Proposal versus adoption is distinguished; full legislative and product-stage treatment is absent. |
| N-10 | Partial | Useful fact/inference, business driver, horizon, confidence, reliability and materiality fields are shown. |
| N-11 | Partial | Counterevidence and reversal conditions appear; missing metrics, next review and model prerequisites are incomplete. |
| N-12 | Partial | No-causation warning only; compatible observed price-reaction detail is absent. |
| N-13 | Partial | Retained revision concept appears; pinned topic/profile/cutoff/model identity and combined drivers are absent. |
| N-14 | Partial | Calendar and one assessment appear; durable unified record and per-stock explanation routing are absent. |
| N-15 | Partial | Three channel chips appear; pause/mute, verified email and permission setup are absent, and ready is overstated. |
| N-16 | Missing | No complete queue, attempt, acknowledgement, retry or exclusion-recheck delivery states. |
| N-17 | Partial | Separate collection and assessment health is useful; stalled, error and recovery variants are incomplete. |
| N-18 | Partial | Quiet-hours, sleep and baseline prose appears; delayed-discovery, catch-up and deduplication journey is absent. |
| N-19 | Partial | Unconfigured source count appears; budget, fair discovery and coverage boundaries are not designed. |
| U-01 | Roadmap | Help and manual destination only; no single versioned content-source interaction. |
| U-02 | Roadmap | First-use walkthrough is not designed. |
| U-03 | Partial | How-to-read content and inline limitations appear; full keyboard-accessible contextual terminology is absent. |
| U-04 | Roadmap | History/data glossary and related teaching are not designed. |
| U-05 | Roadmap | Finance/economics glossary and worked definitions are not designed. |
| U-06 | Roadmap | Monitoring/channel/outage walkthrough is not designed. |
| U-07 | Partial | Sector reading cards preserve key concepts; the complete versioned manual flow remains open. |
| R-01 | Conflict | Generic DCF P1 label shifts the original P0 forward-DCF scope. |
| R-02 | Conflict | Generic DCF P1 label obscures original P0 WACC requirements and alternatives. |
| R-03 | Conflict | Generic DCF P1 label shifts original P0 terminal-value requirements. |
| R-04 | Roadmap | Reverse DCF is retained; the D004 default decision remains open. |
| R-05 | Conflict | Scenarios and sensitivity P1 label loses the original P0 heatmap distinction. |
| R-06 | Missing | Monte Carlo distributions, correlations and probability-output scope are absent. |
| R-07 | Roadmap | Comps destination only; peer editing, warnings and diagnostics are not designed. |
| R-08 | Roadmap | Scenarios destination only; complete assumptions, mechanism and probability validation are not designed. |
| R-09 | Roadmap | Assumption registry destination appears without the advanced continuity subset. |
| R-10 | Conflict | Catalysts is labelled P2 despite existing P1 scope and the selected N1 advance. |
| R-11 | Conflict | Thesis is labelled P2 despite existing P1 scope and the advanced continuity subset. |
| R-12 | Conflict | Conviction rubric is labelled P2 rather than the preserved P1 scope; its future validation is not designed. |
| R-13 | Missing | Deferred conviction and position-size research requirements are absent. |
| R-14 | Conflict | Calibration label P2 obscures the advanced saved-expectation subset. |
| R-15 | Roadmap | Generic Financials/Noise destination; no normalized-earnings waterfall treatment. |
| R-16 | Partial | Some YoY and TTM controls appear; seasonality diagnostics and warnings are absent. |
| R-17 | Roadmap | Noise destination only; factor and event-study requirements are not designed. |
| R-18 | Partial | News assessment exists; source classes and default primary-disclosure filtering are absent. |
| R-19 | Roadmap | Noise and base rates destination only; named datasets and unavailable states are not designed. |
| R-20 | Missing | Business-driver models are absent; a generic technology profile cannot substitute. |
| R-21 | Missing | Risk-text changes and evidence comparison are absent. |
| R-22 | Missing | Management incentives and capital-structure analysis are absent. |
| R-23 | Partial | Supplier/customer topics and Overview roadmap appear; exposures and concentration detail are incomplete. |
| R-24 | Missing | Ownership, control and liquidity research scope is absent. |
| R-25 | Missing | Classified Form 4 activity and price-event overlays are absent. |
| R-26 | Missing | Holding horizon, after-tax assumptions and annualized-return context are absent. |
| E-01 | Missing | No two-endpoint ratio/history comparison selection with exact context. |
| E-02 | Missing | No deterministic numerator/denominator contribution panel or named convention. |
| E-03 | Missing | No attribution validity and source-operand inspection flow. |
| E-04 | Missing | No distinction between price/EPS and cap/common-earnings change attribution. |
| E-05 | Missing | No matching EPS numerator/share bridge and dilution-basis safeguards. |
| E-06 | Missing | No performance/restatement/source/profile/universe/method change classification. |
| E-07 | Missing | No matched cross-metric observation workflow with exact source links. |
| E-08 | Missing | No evidence-backed possible-business-causes panel linked to a numerical change. |
| E-09 | Missing | No same-cohort sector change attribution or explicit composition-change workflow. |
| E-10 | Missing | No comparison actions, save-expectation link or complete AI-disabled explanation flow. |
| C-01 | Missing | No Save expectation form with reasoning, evidence, falsification and review timing. |
| C-02 | Missing | No immutable research revision with exact instrument and source/profile context. |
| C-03 | Missing | No earnings-review queue and uncertain/failed/duplicate/unchanged event states. |
| C-04 | Missing | No original reasoning versus new evidence comparison. |
| C-05 | Missing | No continuity comparison limitations for partial/restated/changed-profile evidence. |
| C-06 | Missing | No human retain, revise or retire workflow with rationale and preserved history. |
| C-07 | Missing | No complete research distinction between facts, math, human judgment and proposed AI text. |
| C-08 | Missing | No draft/active validation preserving dated falsification and unknown event dates. |
| B-01 | Missing | No ordered seven-name pilot; no separation between selected companies and a sector universe. |
| B-02 | Missing | No visible versioned business-model, segment lifecycle and exact instrument profile. |
| B-03 | Missing | No profile policy covering relevant metrics, eligibility, peers, drivers and method support. |
| B-04 | Missing | No dated company/segment overlays with acquisition and historical-scope boundaries. |
| B-05 | Missing | No evidence-backed profile correction/version comparison preserving old analyses. |
| B-06 | Partial | Some unavailable-state labels overlap incidentally; no R1 applicability framework preserving all distinctions and retained facts. |
| B-07 | Missing | No separate established-software, hardware, early-stage and mixed-platform economics. |
| B-08 | Missing | No distinct stablecoin, platform, asset manager, treasury-plus-operations and direct-token profiles. |
| B-09 | Missing | No dated USAR/MP operating, development, ramp, integration and segment lifecycle safeguards. |
| B-10 | Missing | No mineral-mining pilot boundary, MSTR non-miner distinction or separate later mining/energy families. |
| B-11 | Partial | No-runway footnote overlaps incidentally; reviewed specialized-definition and concept/contract boundaries are absent. |
| B-12 | Missing | No business/lifecycle composition or separately identified suitable-cohort rationale. |

Coverage inventory: **143 rows, 143 unique IDs** — G:13, X:25, F:15, W:8,
N:19, U:7, R:26, E:10, C:8, B:12. The row identities and order were checked
against the current checklist when this audit was saved.

## Verification required for the bounded port

- Date, metric and method switches preserve coherent frozen charts, company
  snapshots, coverage and evidence; original values stay in the Python export.
- Total → median → mean → breadth preserves method labels, contributor semantics,
  unavailable rows, full ranges and eligible-only ordering.
- A limited/unknown-cap market reference retains its disclosure without a
  comparative marker; unavailable/limited sectors never appear at zero.
- Actual sector → industry → bin filter → search/pin → frozen source → return
  works, including clearing composed filters.
- Four selected histories remain distinguishable; missing quarters stay gaps;
  1/3/5-year sector controls remain separate from future 3/5/10-year company history.
- Keyboard activation, focus visibility, modal Escape/focus return and chart table
  alternatives survive. Check narrow and 390px layouts for page overflow,
  table containment, units and exact coverage labels.
- `/sectors` continues to show prerequisites; development remains persistently
  fictional. Planned Company/News/R1 entry points cannot imply live feature state.
- Run appropriate frontend checks/build and browser verification after edits.
  No application tests were run by this read-only source-design audit, and no
  numeric feature acceptance is implied by this document.

## Related retained requirements

- [R1 umbrella](../../features/R1-business-aware-research.md)
- [Change explanations](../research-refinements/change-explanations.md)
- [Research continuity](../research-refinements/research-continuity.md)
- [Business profiles](../research-refinements/business-profiles.md)
- [Pilot profile evidence](../../research/pilot-business-profiles-2026-09-19.md)
- [D1 milestone](../../milestones/D1-design-handover.md)
- [X1 milestone](../../milestones/X1-sector-explorer.md)
- [Feature-preservation checklist](../../handoffs/figma/EquityEval_Feature_Preservation_Checklist.md)


## D1b follow-on — bounded Company, News and Help views

Recorded 2026-09-19 after the supplied-design audit. The application now contains
bounded Company, News and Help views alongside the Sector Explorer port. This
section records the implementation scope observed during independent code
review; integrated build/browser/print verification and final milestone status
remain the coordinating implementation task's responsibility. The original
**143-row supplied-design assessment above is unchanged and historical**. It is
not a claim that these later application views are absent, nor does this addendum
mark all requirements accepted.

### Shared navigation and honest state

`WorkbenchShell` connects `/development/sectors`, `/development/company`,
`/development/news`, `/help` and the existing `/sectors` data-readiness screen.
The active route has an accessible current-page indication and a shared skip
link. Company and Sector results retain the fictional-input banner; News uses
**Not monitoring**, and Help identifies itself as a development guide. No
hardcoded awake state or active monitoring service is introduced.

This addresses part of G-01/G-08/G-10/G-13 and replaces dead planned navigation
with bounded destinations. It does not implement security resolution, watchlist
membership, source settings, providers or full workflow state. Shared evidence
presentation retains the native dialog and exact supplied source details;
keyboard integration must be verified on each route.

### Company Fundamentals — existing fictional evidence only

The Company view uses an offline Python presentation export tied to existing
fictional company snapshots. Sector constituent links carry the selected issuer
and evaluation date into this view. The user can change fictional company/date,
inspect source amounts and metrics, compare available saved snapshot values and
choose a requested **3Y, 5Y or 10Y** company-history window. Core financial
arithmetic is not copied into the browser.

| Requirements advanced by the bounded view | Implemented presentation and retained limit |
| --- | --- |
| X-16; G-02/G-04/G-06 | Company context, frozen snapshot/source access, exact amount basis/period and explicit missing reasons. Production source identity and public API acceptance remain open. |
| F-01/F-04/F-15 | Ordered Growth → Profitability → Cash generation → Balance sheet → Valuation, plus Returns on capital disclosure. Only supplied revenue growth, operating margin, FCF margin, multiples and source amounts render; unavailable gross/net margins or separate cash operands are disclosed. |
| F-02 (basis) | Current available basis is TTM; quarterly and annual views are explicitly not supplied. No universal production default is approved. |
| F-03/F-09 | Requested 3/5/10-year windows remain selectable, with dates, missing quarters, tables and explicit insufficiency. Only two fictional company snapshot dates exist; no own-history percentile, rank or silent shortening is introduced. Sector history cannot substitute. |
| F-05/F-06/F-07/F-10 | EPS, price-per-share, balance-sheet/return inputs, forward estimates, valuation range and business-profile applicability are not invented. Available historical multiples are not a valuation verdict; no cash-runway output is introduced. |
| G-07; E-01/E-03/E-06 | Pending selection and saved snapshot values give basic context for inspection. A snapshot-value comparison is not implemented numerical attribution, change classification or business-cause explanation. |

Complete F1 remains open: real company sources, additional metrics and reporting
bases, qualified long history, neutral evidence-driven prompts, Overview/Financials
integration, reviewed applicability and immutable production result services.
R1 numerical attribution and its reviewed convention are not implemented by this
view. The fictional sector label does not become a business/lifecycle profile.

### News & Calendar — navigation and readiness, no monitoring

The News view now has functional **Calendar**, **Stock topics** and **Monitor
health** sections, an all-pilot/per-company filter, topic-category filtering,
clear filters and an explicit no-catalog-match state. The seven real pilot
symbols remain **CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL** in supplied order.
These controls filter a planning catalog; they do not add stocks, save topic
subscriptions or activate background work.

| Requirements advanced by the bounded view | Implemented presentation and retained limit |
| --- | --- |
| N-01/N-02/N-03/N-04 | The unconfigured calendar explains intended CPI/PPI coverage and separate FOMC statement, press conference, scheduled projections and minutes. No dates, release values, consensus or event alerts are fabricated. Lead-time and schedule settings remain unconfigured. |
| N-05/N-06/N-07; B-01/B-07/B-08/B-09/B-10 | Proposed stock-specific coverage includes tickerless relevance and distinct business/project questions. The catalog is not an active topic profile or a current-news assertion. Evidence-backed discovery, candidate approval, persistent corrections, muting and exclusions remain future work. |
| N-08/N-09/N-10/N-11/N-12/N-13 | Explanatory content separates facts from conditional inference, legal/product stages, counterevidence, uncertainty and possible driver effects. No collected evidence, generated assessment, measured reaction or numerical valuation impact is claimed. |
| N-14/N-15/N-16/N-17/N-18/N-19; G-08/G-13 | Collection, assessment and host/delivery readiness are separate. In-app, desktop and email are all unconfigured; permission and host state are not guessed. Outage, quiet-hours, coverage and acknowledgement meanings are explained without fake active health or delivery records. |

N1 is not a background service in this build. There are no connected news/calendar
providers, workers, event/assessment store, inbox history, email configuration or
notifications. W1 financial reruns and monitoring-baseline integration remain
pending. The static pilot questions are not reviewed profile-policy records;
B-02 through B-05 and B-12 still need their evidenced, versioned implementation.

### Help, glossary and printable development guide

`/help` now explains the actual Sector and Company demonstrations, source/date
semantics, numerical units, missing and unsupported states, coverage, history,
future research workflows and troubleshooting. A searchable glossary includes
no-match and clear-search behavior, contextual anchors and worked illustrations.
Print styles use the same rendered content, remove navigation/search controls
and expose every glossary entry even when a screen search is active.

This advances U-01/U-03/U-04/U-05/U-07 and teaches the currently usable parts of
U-02. It is a **development guide**, not completed release-manual acceptance.
The real add-stock → stages → assumptions → rerun → comparison flow and N1
channel/topic/lead-time configuration walkthrough in U-02/U-06 remain pending
because those services are not implemented. Printed and screen terminology must
remain consistent with each later shipped capability.

### Explicit interpretation of X-09's visual encoding

The original checklist says **stable distinguishable colors**. The accepted
visual adaptation is a **single full-contrast accent with distinguishable line
patterns and sector labels** for up to four simultaneous histories. Pattern,
legend, accessible name and table must identify the same sector; color alone
must not carry identity. The sector color field remains available in the data
model. This is an explicit presentation interpretation of X-09, not deletion of
series distinguishability or permission to lower contrast using opacity.

Stability remains an acceptance condition: changing date, metric or history
window must not swap identities, and removing another selected series must not
silently change the surviving sectors' encoding. Initial review found patterns
chosen by the compressed selection index. The coordinating implementation now
retains a pattern slot for each selected sector, reuses only free slots for new
selections, and supplies the same mapping to chart and legend. This preserves
surviving identities when another selection changes. A deliberate single-sector
drilldown begins a new selection. Add/remove and context-change browser checks
remain part of ongoing D1b validation; code inspection alone is not a passed
visual acceptance test.

### Independent integration review at this checkpoint

Read-only review covered `WorkbenchShell`, the Help page and glossary/styles,
Company's contextual help/source links, and the News shared-shell integration.
Focused shell/Help ESLint and the web TypeScript check passed. Static review found
no new provider activation, fabricated current financial figures or implicit
saved-research behavior in these shared/Help views.

The following concrete issues were sent to the coordinating task and their
code corrections were inspected. This audit changed no application files:

- Company help anchors now use `#cash-debt` and a newly supplied `#returns`
  definition, replacing missing destinations.
- News's shared skip-link target now has `tabIndex={-1}`, matching other main
  landmarks. Actual keyboard focus transfer remains a browser check.
- Company history now uses an interactive chart group and keyboard-scrollable
  region. SVG title content is a single string to avoid hydration problems.
- Sector histories now retain selected-sector pattern slots as described above;
  selection-edit stability still needs its integrated browser check.

Print rules preserve the full glossary DOM and explicitly override search-hidden
entries for print. Actual print pagination, readability, keyboard behavior and
route navigation remain browser checks, not conclusions from passing TypeScript.
No overall 143-feature completion or real-data readiness is asserted here.

### D1b verification completion

Integrated browser checks now verify stable history patterns after selection
changes, exact Sector-to-Company snapshots, native modal focus/Escape, News and
Help skip navigation, all topic/search controls, and no page overflow at
320/390/768/1440px. The optimized production build and eight route cases pass
without console/page errors. A filtered Help print retains all 52 definitions;
final PDF inspection confirms readable text and white paper margins after
correcting the print color-scheme cascade. See [D1b](../../milestones/D1b-company-news-help.md)
for exact scope and evidence. Full feature/source acceptance is still separate.
