# Copy this prompt into Figma AI

Redesign equityEval, a personal equity research workbench, using the attached project package. Work on the UI design and prototype first. The application is partially implemented: today's Sector Explorer works on fictional data, while several company, watchlist and monitoring functions are planned. Preserve both existing functionality and the full planned product scope without making planned services appear live.

Read `docs/handoffs/figma/EquityEval_Figma_Design_Handover.md` and `docs/handoffs/figma/EquityEval_Feature_Preservation_Checklist.md` first. The checklist has 143 stable feature IDs (the original 113 plus 30 E/C/B refinements). Use its status legend and map every ID to a screen, component/state, or explicitly retained future feature. Consult the original specs and feature documents for details. Current milestone records override older statements about implementation status.

Create a coherent, professional, graph-led research interface. Make it approachable for a five-minute review and deep enough to inspect every source and assumption. You may freely redesign colors, typography, layout, navigation and hierarchy. The existing code/screenshots and unfinished MCP canvas show behavior and context; they are not a mandatory visual style. Use readable charts, aligned numeric tables, clear units and restrained color. Avoid ornamental dashboard cards, arbitrary stock scores and BUY/SELL labels.

The initial user-facing pilot is CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL, in that order; keep all seven. MSFT/RBLX remain regression fixtures. Mining means minerals, and MSTR is treasury plus software, not a Bitcoin miner. Use the dated profile evidence in the handover; USAR/MP have mixed operating/development/ramp scope. No additional energy ticker has been supplied.

Design these connected areas:

1. Sector Explorer with four primary, linked graphs: sector comparison bars; historical trends for up to four sectors; company distribution histogram; and growth-versus-valuation scatter. Preserve sector/industry drilldown, search, pinning, bin filters, table alternatives, all metric/method/date controls, market reference, coverage/exclusions and the exact frozen company source drawer.
2. Company Overview and Financials/Ratios, including guided Fundamentals in this order: Growth, Profitability, Cash generation, Balance sheet, Valuation; Returns on capital expandable. Retain TTM/quarter/annual context and optional 3/5/10-year company history, with honest insufficient-history states.
3. Watchlist: search and resolve the exact issuer/security/exchange/share class, add stock, stage progress, partial failures/retry/cancel, run analysis again, remove/re-add and compare preserved analysis versions. Adding a stock initiates the full applicable analysis; it does not fabricate unavailable model stages.
4. News and economic calendar: CPI/PPI/Fed heads-up and release/correction states; continuous company-specific topic discovery and evidence-backed conditional impact assessments, including relevant ecosystem/regulatory news with no ticker mention. Preserve topic editing/muting/exclusions, revision history, in-app/desktop/email channels, quiet hours and separate collection/assessment health.
5. Help, glossary and onboarding, with contextual definitions, source/data settings and a printable manual destination.
6. Bring a small research-continuity workflow into the first company experience: save expectation, why, evidence, weakening/falsification condition and review date/event; compare later earnings evidence against that original reasoning; let the user retain/revise/retire with rationale. Reuse versioned thesis/assumptions/snapshots, not a separate journal. Keep full conviction/calibration and remaining DCF, Comps, Scenarios, Catalysts, Noise and advanced research on explicit future pages. The checklist preserves their detailed requirements; do not drop them because the working code does not yet expose them.

Add “Why did this change?” to company ratios/history and relevant sector views. Separate tested deterministic numerical contributions from possible business causes with cited evidence, alternatives and uncertainty. Cross-metric observations link to exact figures/periods/sources. AI is optional; it cannot overwrite facts, calculations or saved assumptions.

Make the visible, versioned analysis profile depend on business model, lifecycle and instrument. Support explicit company/segment overlays, correction and old-version reopening. Each profile defines relevant metrics/validity, peers, driver inputs, explanatory rules and supported methods; unavailable fields never become a bad score. Preserve base loss/cash/debt/dilution facts. Current F1 runway exclusions remain until reviewed. Sector views expose business-model composition and cohort suitability.

Preserve these financial meanings:

- Sector total P/E is a ratio of sums including losses. Median company P/E describes eligible profitable companies. Advanced simple mean is a third method. Label each explicitly.
- Missing, zero, stale, unsupported, invalid, N/M and limited coverage are distinct. Retain numerator/denominator definitions, complete roster and contributor counts, capitalization coverage, exclusions and reasons.
- Limited or unknown coverage cannot produce comparative rankings, scatter points or confident summaries. Never populate missing observations with zero or interpolate missing financial data.
- Shared graph context does not imply identical P/E and growth constituent sets; expose each axis's eligible cohort and coverage.
- Selected companies are not the entire market. Current-members history is not historical sector membership. Sector 1/3/5-year line controls do not replace Fundamentals 3/5/10-year options.
- Distinguish immutable sourced facts, versioned human assumptions and computed conclusions. Every displayed financial result must have a route to its exact evidence. Source updates and new analyses never overwrite saved runs.
- Financial math and gates belong to the existing Python core. In a code prototype, consume the supplied values; do not replace them with new browser-side formulas. Do not invent or approve public API/schema changes.

Use labelled fictional examples in all designs. News assessments must distinguish facts from inference, confidence from source reliability, and conditional business effects from guaranteed stock-price predictions. Monitoring must not require an open company page; a sleeping local machine cannot claim continuous uptime.

Deliver editable desktop and mobile screens, reusable components/tokens, key prototype journeys and annotated keyboard/focus/empty/loading/error/limited states. Include the feature-ID-to-frame mapping and a candid list of unfinished items. Preserve the four linked Sector Explorer graphs and complete the small-watchlist company journey, including profile → why changed → save expectation → earnings review, before broadening market coverage. Complete the news/help design scope as well. A single comparison-bar page is not the full redesign.

The old `FIGMA_STATUS.md` describes an interrupted MCP attempt only. You may start a fresh design; no MCP tool, plan upgrade, old node ID, credential or API subscription is needed to understand this package. Do not configure real sources or send notifications as part of the UI redesign.
