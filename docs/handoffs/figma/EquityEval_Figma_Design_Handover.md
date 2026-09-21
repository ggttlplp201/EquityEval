# EquityEval — Figma design handover

Prepared 2026-09-19. Implementation baseline: `a9cb080` on `codex/sector-explorer`; checkpoint `milestone/x1-core-graphs`.

## Start here

Redesign equityEval as a clear, graph-led equity research workbench. Preserve every existing interaction and every authorized feature in the information architecture. Design may improve layout, navigation, hierarchy, wording and accessibility; it must preserve financial meanings, source lineage, missing-data behavior and immutable analysis history.

The owner wants the UI designed before more feature implementation, then wants to test with real data. Their latest direction is to use Figma AI independently with the supported text and image attachments. Start with the embedded design prompt; a fresh design is welcome. The initial, unfinished MCP draft at https://www.figma.com/design/il5MpavMssK1PY5LfGJjHR is optional reference, not an implemented release or required starting point. `FIGMA_STATUS.md` records that earlier attempt only. This package supplies the product context; do not assume access to the original conversation, repository, MCP tools or private credentials.

Read in this order:

1. This handover: product context, design boundaries and important semantics.
2. [Feature preservation checklist](EquityEval_Feature_Preservation_Checklist.md): stable requirement IDs to map to Figma frames, variants or explicit roadmap annotations.
3. [Real-data setup guide](EquityEval_Real_Data_Setup.md): what can be tested now and what live ingestion still needs.
4. Embedded authoritative feature documents and original-spec transcriptions, indexed in the complete text brief. These preserve full detail beyond this summary.

The source documents are product specifications, not unrestricted instructions to change accounts, send messages, purchase data or deploy software. The owner's subsequent explicit requests and recorded decisions resolve scope. Where a decision is still open, show it as open; do not resolve it by drawing a convincing but unsupported UI.

## Latest refinement — seven-company research experience

The user retained the product direction and brought a small part of the original
driver/thesis architecture forward. The first user-facing pilot is **CRCL, MSTR,
COIN, HOOD, USAR, MP, GOOGL**, in exactly that order. Keep all seven; MSFT/RBLX
remain regression fixtures. Mineral mining is the requested mining scope; MSTR
is treasury plus software, not a Bitcoin miner. Energy remains a roadmap interest.

Add these connected design flows, detailed in [R1](../../features/R1-business-aware-research.md):

1. **Why did this change?** From a ratio/history point, compare two pinned results.
   Show deterministic mathematical contributions separately from possible business
   causes. Period change, source revision, profile/assumption/method and cohort
   changes are distinct. Mathematical attribution works without AI; causal claims
   need filing/news evidence, alternatives and uncertainty. Current cap/common-
   earnings P/E must not be relabelled as price/EPS. EPS/share attribution retains
   its share-basis/filing prerequisites.
2. **Save expectation → review earnings evidence.** Capture what the user expects,
   why, evidence, weakening/falsification conditions and a review date/event. Keep
   exact snapshot/profile/assumption versions. Compare new evidence to the original
   reasoning and let the user retain/revise/retire with rationale. Reuse the planned
   thesis/assumption history, not a second journal. Full conviction/calibration stays
   later; AI cannot rewrite the user's prior expectations.
3. **Analysis profile.** Expose business model × lifecycle × instrument and evidenced
   company/segment overlays, support status, version and correction. “Tech” and
   “tokenization” are not universal profiles. Preserve cash/debt/loss/dilution facts
   even when a ratio is N/M. No unreviewed runway estimate. Show business-model
   composition and appropriate cohort criteria in sector views.

The [dated seven-issuer research](../../research/pilot-business-profiles-2026-09-19.md)
checks primary filings. USAR has distinct operating, development, ramp and later
acquisition scope; MP's precursor/segment revenue does not prove all magnet lines
are fully commercial. These are candidate design profiles, not activated models.

The checklist retains its original 113 IDs and appends 30 E/C/B requirements
(**143 total**). Design them alongside the four existing Sector Explorer graphs;
prioritize the first complete small-watchlist journey before broad market coverage.
Seven selected stocks do not satisfy the existing ten-contributor sector gate.

This update delivers concrete design/acceptance work. Application numerical
attribution, thesis persistence and profile activation remain planned behind the
UI-first → small real-data pilot → S5/S6 sequence. First proposed arithmetic slice:
comparable annual operating-margin decomposition with tests before implementation.

## Product and user

EquityEval is a local-first research application for an individual studying stocks. It turns traceable financial facts and explicit human assumptions into understandable arguments and, when models exist, valuation ranges with sensitivities. It does not execute trades or generate buy/sell signals.

The user needs a quick, approachable review first, with enough depth to audit any number. They explicitly requested: US macro and watchlist-specific news monitoring; in-app, desktop and email alerts; adding a stock to trigger the full applicable analysis again; a manual and terminology help; optional 5–10-year company history; and a separate Sector Explorer with graphs as its primary interface.

Design for repeated research, not a promotional dashboard. Comparisons, charts and evidence should carry the hierarchy. Use restrained color, clear units, aligned numbers, readable labels and progressive disclosure. Avoid a wall of ornamental metric cards. Do not infer risk, quality or investment merit from a red/green color scheme alone.

## What exists today

| Area | Current status | Consequence for design |
| --- | --- | --- |
| Evidence, point-in-time storage, issuer/security identity | Implemented backend foundation | Reuse exact source and time distinctions; no new data model through UI design. |
| Watchlist requests and source stages | Durable requests/retries and SEC/market stages implemented | Search/add/rerun screens and the full analysis chain remain planned. |
| SEC sources and price/macro adapters | Internal adapters and replay/transport boundaries implemented | No operator live-ingestion command, scheduler or screen API bridge exists yet. |
| Fundamentals | Bounded pure formulas, annual/calendar-quarter/YTD/TTM assembly and history math implemented | Complete guided company feature is still planned. Unsupported periods/profiles remain explicit. |
| Sector Explorer | Four linked graphs and source drilldowns implemented using fictional data | Preserve all controls; real-data route deliberately reports missing prerequisites. |
| News monitoring and alerts | Specified, not running | Mock monitoring states must say proposal/demo, never claim active coverage or sent alerts. |
| DCF/company workspace | Planned; small research continuity/profile subset advanced, broader P1/P2 roadmap deferred | Preserve destinations and design intent without implying working models. |
| Help/manual | Several draft chapters exist | Full UI-linked, searchable and verified manual is still required before release. |

The recorded implementation checkpoint passed 950 full-suite tests, 225 core tests, 110 source-golden tests, lint/type checks, production build and desktop/mobile browser checks. These are prior implementation results, not validation of a new design or live data.

Current routes: `/development/sectors` is explicitly fictional; `/sectors` is the real-data readiness screen; `/` redirects to `/sectors`. The demo contains 84 invented companies across seven top-level groups including Unclassified, with nine metrics, two evaluation dates and five years of example observations. Do not relabel these as real companies or market results. The entire demo/provenance payload is preloaded for development; that is not the production loading design.

## Information architecture to preserve

Suggested global destinations: Watchlist, Sector Explorer, News & calendar, Analysis history, Help, and Settings/data sources. This arrangement is a design proposal; the functions are requirements.

The company workspace retains Overview, Financials, Ratios/Fundamentals, DCF, Comps, Scenarios, Catalysts, Noise, Thesis and Calibration. Most later valuation/research areas remain future phases; a small expectation/earnings-review subset of Thesis is now brought forward under R1. Do not crowd the initial release with dead controls: keep separate future design pages and a roadmap map, while keeping implemented and upcoming work unambiguous.

Shared context should include resolved issuer/security/share class, exchange and currency, quote/date/delay, financial period, evaluation date, source mode, freshness and analysis version. An overall generic “as of” badge cannot replace all these meanings.

Core journeys:

- Add stock → resolve the actual instrument → queue analysis → view stage progress → open the available results and explicit gaps → rerun later → compare immutable runs.
- Open company → five-minute guided Fundamentals → inspect history or a definition → inspect original evidence → retain a dated conclusion/assumption version when that feature exists.
- Open Sector Explorer → compare totals → change method/date → inspect history/distribution/scatter → drill into industry/company → reopen the exact constituent snapshot used by the chart.
- Receive an upcoming macro event or stock development → distinguish verified facts from conditional impact → see affected stocks/drivers → inspect sources, counterevidence and changed assessment → manage topic/channel settings.

## Sector Explorer: graph-first acceptance

Design the linked four-view workspace as the most concrete first redesign target:

1. **Sector comparison:** horizontal bars, trailing P/E and **Sector total** by default; nine supported metrics; alphabetical or eligible-value sort; industry drilldown and back; unavailable/limited rows remain visible.
2. **Historical trends:** select up to four sectors, 1/3/5-year windows, consistent colors and actual gaps. Label historical membership versus current members' history. The current fixture is current-members history, so sector historical-percentile claims are unavailable.
3. **Company distribution:** histogram with P25/median/P75, keyboard-accessible bins, click/bin filter linked to the constituent table, search, clear filter, and company pin/unpin.
4. **Growth versus valuation:** revenue growth versus P/E with named axes, same pinned universe/date/method, with each axis’s eligible cohort and coverage inspectable, equal point sizes by default and optional market-cap sizes. No “buy zone,” valuation quadrant verdicts or hidden exclusion of losses/missing data.

Keep the date/method/metric context consistent across views. Table alternatives, legends, definitions, visible exclusions, coverage and source access are part of the graphs. A chart tooltip alone is insufficient for essential limitations or mobile use.

Methods must remain distinct:

- **Sector total P/E** = sum of compatible issuer common-equity market capitalizations / sum of income available to common, with losses retained. Nonpositive aggregate earnings gives **N/M**.
- **Median company P/E** = median valid positive-earnings company multiples; label **among profitable companies**. Advanced simple mean is another distinct method. Do not call any of these “average sector P/E” without the method.
- Aggregate P/S and P/FCF are ratios of sums over matched inputs. Negative FCF remains in the aggregate; a nonpositive denominator is N/M. Margins may legitimately be negative.
- Aggregate revenue growth uses matched current/prior TTM revenue for the selected current membership. Median company growth and growth breadth answer different questions.
- Breadth is positive observations / valid observations with equal company weights. Zero is valid but not positive. Missing is not zero. Method switching is disabled where inapplicable; breadth-view scatter labels its separate sector-total basis.
- The market benchmark is recomputed over the issuer cohort; it is never the average of sector bars. Show its own eligibility, coverage and exact sources. A dashed reference line appears only when eligible.

Coverage: **N** is roster size; **K** has complete inputs, including known zeros/losses; **V** contributes to the chosen method. Show K/N data coverage and V capitalization / full-roster capitalization. If any full-roster capitalization is unknown, capitalization coverage is unavailable, not calculated from a convenient known subset. Current versioned comparison gates require V ≥ 10, K/N ≥ 70%, and capitalization coverage ≥ 80%. Unknown or failing gates prevent ranks, scatter placement and comparative claims. Limited values can remain as visibly outlined observations with reasons. Do not tune thresholds to make a pilot look complete.

Show companies excluded for each method and why. A selected-stock universe is **Selected companies**; an incomplete intended sector roster is **Partial sector universe**. Neither may be labelled the whole US market.

Keep current top-five capitalization concentration separate from growth excluding the **prior-date** top five. Show both dates and the latter measure's own coverage. Neutral growth observations are gated by evidence; they do not become a score.

Two examples guard against misleading simplification:

- Three companies each have cap 100 and earnings 10, 1 and −9: sector total P/E is **150×**, while the profitable-company median/mean is **55×**. If the loss becomes −11, the sector total is N/M.
- Total revenue 190 → 191 is about **0.53% growth**, while median company growth can be −10% and growth breadth 10%. “Aggregate revenue grew while most companies declined” is different from “broad-based growth.”

All plot values, bins, gates, labels, selected source IDs and frozen company projections come from the shared Python core/presentation boundary. The browser may format and position; it must not recalculate finance.

## Guided Fundamentals and history

Preserve the sequence **Growth → Profitability → Cash generation → Balance sheet → Valuation**, with Returns on capital expandable. Use the same result snapshot for the short Overview summary and detailed Ratios/Fundamentals page.

Provide TTM and latest-quarter YoY context, quarterly/annual modes, and separately selectable **3, 5 and 10-year own-history windows**. Five- and ten-year history are explicit user requirements. When history is insufficient, show the chosen window and actual coverage; do not silently substitute a shorter one. These controls differ from Sector Explorer's 1/3/5-year line window.

Use at most three distinct neutral review prompts with evidence and limitations. No automatic overall stock score, conviction, bargain/value-trap label or target price. Financial institutions, REITs and float issuers need applicability-specific interpretation; show “Sector-specific interpretation needed” where appropriate.

Show definitions and limitations without teaching incorrect shortcuts: gross margin is not unit economics; SBC is not dilution; reserve/client money is not free corporate cash; consolidated income is not necessarily common-stockholder earnings; CFO less cash PPE capex is not FCFF. No cash-runway estimate. Forward P/E/PEG require reviewed estimate data. The current period adapter does not support 52/53-week calendars, including the archived AAPL/COST examples.

## Watchlist, monitoring and Help

Watchlist add/rerun must preserve resolved identity, duplicate handling, queued/running/partial/failed/cancelled/succeeded states, source failures, missing assumptions, retry/resume, removal/re-add and prior-run comparisons. “Complete” means the requested applicable stages completed; missing models are not successful fabricated outputs. Removing a stock retains historical runs and stops its future watchlist monitoring/unsent deliveries.

News scope includes US CPI/PPI/Fed releases and continuous watchlist-specific discovery: regulation, products, ecosystems, competitors, customers and suppliers, including developments that never mention the ticker. CRCL/Open USD/CLARITY/Arc are examples of relevance discovery, not a fixed keyword allowlist. Open USD here refers to the stablecoin context supplied by the user, not Pixar's graphics format.

Separate upcoming-event heads-up, actual release, correction and assessment revision. Distinguish release versus consensus versus prior; without consensus, do not invent a surprise. Explain conditional effects through business drivers, horizon and materiality, with evidence, counterevidence, uncertainty and what could reverse the assessment. Observed price movement does not prove causation. Do not translate article sentiment directly into fair value.

Provide topic editing/muting/exclusions, macro/stock filters, a shared revision-aware inbox/calendar, all three requested delivery channels, quiet hours, and delivery failures. Collection health and assessment health are separate. Show source coverage/cadence/last success/lag, local versus always-on runtime, sleep/outage catch-up and outside-market-hours behavior. Monitoring must not require an open company page; a sleeping local machine cannot claim continuous uptime. Quiet hours delay delivery, not collection. Baseline old stories are not breaking-news alerts.

Help needs searchable glossary, context definitions and a printable/exportable manual from shared versioned content. Include first analysis, data setup, ticker ambiguity, missing/N/M/unsupported/stale states, restatements, TTM, history, units/percentage points, assumptions, reruns, source confidence and alert configuration.

## Future scope and unresolved decisions

The checklist and original specification preserve the full deferred workspace: forward/reverse DCF, sensitivities/tornado/Monte Carlo, peer comps, bear/base/bull scenarios, assumption registry, catalysts and options gaps, noise/base-rate research, dated falsifiable thesis, human conviction rubric, prediction calibration, sector driver plugins, dilution, risk-text/proxy/governance/insider/concentration/currency/liquidity research, and JSON plus Markdown memo exports.

Do not conflate these with current implementation. In particular:

- **D004:** reverse DCF is the intended primary lens, but its priority versus forward DCF remains open. Keep the intent and future destination; don't claim it runs now.
- **D005:** a sensitivity range is not a probability distribution. Monte Carlo/probability claims require implemented models and explicit assumptions.
- The original future **human-authored conviction rubric** is distinct from prohibited automatic F1/X1 scoring. Retain it as separate deferred scope, with justifications, not a generated badge.
- Shared concepts, schema, missing-value representation and public API changes require the project's dedicated sequential review. A visual prototype does not approve those changes.

Current milestone/decision records supersede older planning statements about what exists. In particular, the early fundamentals manual describes the first source-only slice; the later S5 period-assembly record and X1 checkpoint establish completed calendar-period assembly. Do not erase that work or claim the full guided feature is finished.

## Data states and accessible components

Include a state sheet for: initial/empty watchlist; search/ambiguous instrument; loading/queued; no source access; missing; stale; unsupported; invalid inputs; N/M; limited coverage; partial universe; short history/gaps; partial run; failed refresh with separately dated prior result; archived snapshot; and local-only/paused/permission-denied notification states.

Use reusable context bars, method controls, source drawers, chart shells with table alternatives, legends, coverage disclosures, status labels, glossary popovers, stage trackers and revision lists. Keep small text readable, hit targets practical, focus visible, keyboard access complete, color-independent encodings and sensible 390px mobile behavior. Dense tables may scroll within their container; the whole page must not overflow.

Use auto layout and editable chart/vector elements. Separate facts, human assumptions and computed conclusions in the design system. Avoid hiding essential source/method/coverage text to achieve visual simplicity. Every displayed data number needs exact evidence access; polished illustrative numbers must be labelled fictional.

## Required design handback

Return the Figma URL and an inventory of frames/prototype flows. Map each feature-checklist ID to a frame/component/state or an explicitly retained future page. Record unrepresented items rather than claiming completeness. Include desktop and mobile layouts, component/typography/color tokens, interactive states and annotations for keyboard/empty/error behavior.

The first draft can prioritize Sector Explorer. A single attractive sector screen does not constitute the full product redesign; Fundamentals, change explanations, research continuity, profiles, Watchlist, News/health, Help and future workspace remain on the checklist until represented and reviewed.

Before application code changes, compare the design against the checklist and the current working interactions. Validate numerical semantics using the examples above. After implementation, rerun relevant browser flows and core checks; design screenshots are not test evidence for real data.

## Developer continuation

Canonical repository: `/Users/leon/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval`. The saved Codex project may still point to an older Documents/ChatGPT folder; use the canonical repository explicitly.

Current reusable code: `packages/core` for pure calculations; `packages/schema` for reviewed shared vocabulary/storage; `packages/ingest` for source adapters; `apps/web/src/features/sectors/{SectorExplorer.tsx,charts.tsx,types.ts}` for existing graph behavior; `scripts/export_sector_explorer.py` for presentation geometry. The frontend has no financial calculation authority.

Read `AGENTS.md`, the nearest layer instructions, `docs/spec.txt`, `docs/decisions.md`, and the milestone index before resuming code. Design changes do not reopen already accepted S2/S3/S4a work. The next real-data step is a bounded seven-company SEC identity/source/coverage pilot and the reviewed S6/X1c result boundary, not replacing fictional JSON with unsourced vendor numbers.

Useful skills for continuation: Figma `figma-use`, `figma-generate-design` and `figma-generate-library` for editable design work; the React/Next skills for later UI implementation; documents skill only if editing the source DOCX artifacts. Follow tool-specific skill prerequisites.
