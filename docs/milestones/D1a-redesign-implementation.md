# D1a — Supplied redesign: Sector Explorer implementation

Date: 2026-09-19. Status: bounded Sector Explorer presentation slice implemented and verified.
Baseline: a9cb080, milestone/x1-core-graphs. The owner supplied
`Sector Explorer redesign demo.zip` and explicitly authorized resuming application
work through the coordinating task. This advances D1's design-first pause into a
bounded existing-interface port; it does not activate real sources or monitoring.

## Archive and reconciliation

Original README/HTML and checksums are preserved in
[the source archive record](../originals/ui-redesign-2026-09-19/manifest.json).
Two entries passed CRC, relative-path, file-type and size checks. The HTML refers
to a missing `support.js`; it is usable as markup/design input but cannot be
claimed as a self-contained running prototype. No prototype script was executed.

[The complete reconciliation](../design/ui-redesign/reconciliation.md) maps all
143 checklist IDs. The supplied design references the older 113-ID brief and
omits the E/C/B refinement workflows. Its fabricated data and JavaScript financial
arithmetic are not production inputs. Unsupported meanings and incomplete design
states remain requirements; they are not silently removed.

## Bounded implementation

- Apply the supplied charcoal/mint/Helvetica visual system to the existing Sector
  Explorer and production-readiness page, retaining all four linked graphs.
- Reuse existing React selection state, Python-exported values/counts/eligibility/
  ordering/geometry, exact `detailId` evidence and current internal types.
- Preserve real industry navigation, search/bin/pin composition, method/date
  coherence, missing/limited rows, historical gaps and table alternatives.
- Add readable coverage guidance and method-specific market-reference disclosure.
- Retain native modal focus/Escape; add scrim close and keyboard skip navigation.
- Adapt mobile layouts and use full-contrast line patterns for four same-hue
  histories; prototype opacity-only series are insufficiently distinguishable.
- Label Company, News and R1 destinations as planned. No new company metrics,
  artificial source records, active health states or saved-thesis behavior.

The seven-company pilot remains CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL; MSFT/RBLX
remain regression fixtures. The current core, fixture, exporter, schemas and
source adapters are unchanged. F1 history, W1 full reruns, N1 macro/stock topics
and all three alert channels, U1 and the full R1 scope remain in the checklist.

## Verification

- Existing presentation regressions: **8 passed**.
- Root lint, schema/web TypeScript checks and optimized Next.js production build:
  **passed**. The production build was started locally and smoke-checked.
- Browser comparison against the unchanged fixture: **all 42 valid UI combinations**
  (dates × metrics × permitted methods) matched exact snapshot IDs, values,
  N/K/V, coverage, bar status, market reference and scatter cohorts/axis values.
  Breadth intentionally permits only its equal-company method.
- **13 linked-flow assertions passed**: four-history cap and distinct patterns,
  five-year window, real industry drilldown/back, histogram membership, pinning,
  clearing filters, exact company snapshot and visible limited-market disclosure.
- Actual keyboard/pointer checks: native modal prevents background focus; Escape
  closes and restores the triggering button; scrim click closes. Search retains a
  loss-making N/M company with source access. The advanced control fits mobile.
- Desktop 1440px, tablet 768px, mobile 390px and narrow 320px: no page-level
  horizontal overflow. Charts/tables have contained scrolling; no chart-label
  clipping or declared leaf-text font sizes below 10px in the checked mobile view.
- Normal `/` redirects to `/sectors`: four production prerequisites remain, with
  no fictional chart substituted. The explicit demo link works. No browser
  exceptions, hydration errors or framework overlays were observed.
- Independent review found and fixed the market legend swatch, Y-label clipping
  and mobile tick crowding. Visual checks also corrected endpoint dates and
  right-edge scatter labels. Financial arithmetic, ordering/gates, types and
  snapshot/source IDs remain unchanged; `git diff --check` passes.

Evidence in `var/`: `redesign-snapshot-checks.json`, `redesign-flow-checks.json`,
`redesign-desktop.png`, `redesign-mobile.png`, `redesign-mobile-top.png`,
`redesign-readiness.png`. The browser comparison scripts are retained alongside
these records. Static code review and the 143-row design reconciliation are
separate from source/data acceptance. The former 950-test checkpoint remains
historical; the full backend suite was not repeated for this presentation-only
change. No new numeric engine, live-data or complete-product acceptance is claimed.

The local preview runs at `http://127.0.0.1:3101/development/sectors`; normal data
readiness is `http://127.0.0.1:3101/sectors`. No deployment, new provider connection,
subscription, external alert, schema or public API change occurred. This slice is
in the working tree; no new commit or milestone tag was created.

## Next handoff

Complete remaining Company/News/Watchlist/Help and R1 design flows against the
143-ID reconciliation. Prepare the seven-company identity/filing/coverage pilot
under the existing reviewed boundaries. S6 API/result/profile/thesis contracts and
any new numerical method retain their sequential review and test prerequisites.

Follow-on: the owner subsequently authorized filling missing screens in the same
design. [D1b](D1b-company-news-help.md) records Company/News/Help implementation;
D1a's original verification and supplied-design assessment remain historical.
