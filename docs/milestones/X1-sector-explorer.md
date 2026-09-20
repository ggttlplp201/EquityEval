# X1 — Sector Explorer

Status: S5 prerequisite and X1a/b development checkpoint implemented and verified,
2026-09-19. Full real-data X1 acceptance remains open. Separate additive feature requested
by the user after the current fundamentals work. Branch: `codex/sector-explorer`.
Baseline: completed source-metric checkpoint `bd437db`, tag
`milestone/s5-source-metrics` (867 full-suite tests, 150 core tests).

The [source and acceptance map](../features/X1-sector-explorer.md) preserves the
full requested scope. The [contract proposal](../design/sector-explorer/contract-proposal.md)
separates internal pure calculations from later reviewed storage and HTTP API.
The original DOCX, searchable transcription, diagram and checksums are preserved
under [originals](../originals/sector-explorer/manifest.json). All five rendered
source pages were read; the diagram is illustrative, not market observations.

## Ordered work and evidence

| Phase | Status | Deliverable / remaining dependency |
| --- | --- | --- |
| Prerequisite — S5 periods | Complete | Complete source-preserving annual/quarter/YTD/TTM assembly and integration with existing fundamentals formulas; tests before numeric code and independent review. |
| X1a — Sector calculations | Complete for internal evaluated-input boundary | Aggregate / median / explicit simple mean, matched cohorts, breadth, concentration, distribution, N/K/V and coverage gates. Pure core, Decimal, source lineage. |
| X1b — Graph interface | Complete for fictional development view | Bars first, linked history/distribution/scatter, methods, benchmark, source and company drilldown, keyboard/mobile tables. Use explicitly fictional data for verification while real prerequisites are unavailable. |
| X1c — Durable data/API | Review pending | Licensed complete roster/classifications, effective/known-at membership, compatible common earnings/capitalization, frozen company and sector snapshots, S6 public API/generated types/cache/publication. |
| X1d — Real-source acceptance | Pending | Full selected universe, historical membership and filings, immutable snapshot reopening, API-to-chart equality, approved profiles and source rights, manual walkthrough. |

The implementation must not turn fictional graph checks into a claim that X1c/d
passed. Ordinary sector views remain unavailable until the required sources and
contracts exist. The current source pipeline is not a complete U.S. universe.

## Specific missing data prerequisites

- A dated complete U.S. operating-equity issuer roster, independent of metrics.
- Approved taxonomy provider/version, usage rights, and effective/known-at sector
  and industry assignments; unknown assignments remain Unclassified.
- Complete common-equity capitalization across classes/ADS, correct point-date
  ownership, eligible quotes and calendar/action evidence.
- Income available to common and compatible earnings scope. The existing
  normalized parent/consolidated-income concepts are not interchangeable with it.
- Comparable TTM facts, explicit source precision, freshness/profile policy and
  per-date membership for genuine historical sector comparisons.
- Reviewed immutable fundamentals and sector snapshots/public API. Existing W1
  request/source stages do not already publish those result records.

## Acceptance checklist

Track source B052–B056 independently: arithmetic; roster/cohort integrity; growth
and immutable history; graph-to-result equality/accessibility; safe interpretation.
Retain the 150× total / 55× median example and the 190→191 aggregate-growth
example in tests. A selected history window never fabricates missing observations.
Sector line controls are 1/3/5 years; F1 retains its separate 3/5/10-year options.


## Progress log

- Preserved and read the source DOCX, all five rendered pages, tables and chart.
  Recorded conflicts, missing prerequisites and an S6 contract proposal.
- Finished the S5 period prerequisite first. Its 167-test core suite and independent
  numeric review passed before starting Sector Explorer implementation.
- Added shared evaluated company projections and pure sector calculations;
  tests cover the supplied 150×/55× example and 190→191 breadth example.
- Added effective/known-date membership selection and sector-history projection
  reusing fundamentals percentile math. Current-members mode has no historical
  sector percentiles; excluded quarters remain explicit gaps.
- Built linked development graph views and a separate unavailable real-data route.
  Deterministic core-generated fictional snapshots and desktop/mobile browser
  checks now pass. Production data/API acceptance stays open.

The [manual chapter](../user-manual/sector-explorer.md) accompanies this work.


## Verified checkpoint — 2026-09-19

- Full repository suite: **950 passed**; core: **225 passed**; golden: **110 passed**.
- Repository lint and strict Python/TypeScript checks passed. Independent numeric,
  standards and spec reviews are recorded in [review](../design/sector-explorer/review.md).
- `npm run build --workspace @equity/web` passed with all three routes rendered.
  The development route has 114 kB first-load JavaScript; this excludes its large
  preloaded fictional data/provenance payload and is not a production-data budget.
- Verified the production build in Chromium at 1440 px and 390 px. The browser
  checked exact bar values and snapshot IDs against the generated artifact,
  date/total/median/mean transitions, keyboard histogram filtering, search/pin,
  exact company snapshot details and Escape, industry navigation, four-sector
  history selection, five-year window, cap sizing, breadth labeling, unsupported
  profile visibility, visible market-reference coverage, zero page overflow on
  mobile and both entry routes.
  No hydration/runtime errors occurred. Browser automation used bundled Playwright
  with the installed Chromium runtime because `agent-browser` was unavailable.
- Fictional fixture: 84 issuers, seven top-level groups including Unclassified,
  twelve industry groups, nine metrics, two dates, 54 linked presentation views
  and five years of quarter observations with explicit gaps. It uses current
  members' history and disables historical-sector percentiles. A deterministic
  gzip artifact (~2.1 MB) preserves complete provenance. All-method preloading
  remains a development performance limitation; S6 will load relevant snapshots.
- [User manual](../user-manual/sector-explorer.md) walkthrough checked against these
  controls. The full application's U1 release walkthrough remains open.

Reproduce with the root/web README commands. The unchanged mandatory commit hook
runs all required checks again over the staged checkpoint. Tag:
`milestone/x1-core-graphs`; use `git show milestone/x1-core-graphs` for its commit.

## Next handoff

Resolve D021/D024's concrete company/membership/snapshot/API contracts in the
sequential S6 review, then implement X1c. Obtain the approved dated issuer roster
and taxonomy rights, common-income and complete-capitalization evidence, supported
profile/freshness rules and historical membership. Wire real company/sector
snapshots into the graph adapter and verify X1d's complete-universe, saved-result,
API equality and failed-refresh acceptance. No live source or public endpoint has
been activated by this checkpoint. Preserve the existing F1/N1/W1 backlog.
