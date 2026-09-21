# D1b — Company, News and Help development workspace

Date: 2026-09-19. Status: bounded implementation complete and verified.
Baseline: D1a working tree on `codex/sector-explorer`, HEAD `a9cb080`.
Authorization: the owner said to mimic the design, fill missing parts and continue
with the next implementation step. D029 records this bounded continuation.

## Delivered scope

- Shared charcoal/mint navigation and native evidence drawer. Sector constituent
  links open the exact company and evaluation date without changing its source
  snapshot. Existing Sector graphs, methods and coverage remain intact.
- `/development/company`: 84 explicitly fictional issuers, two evaluation dates,
  six existing Python-calculated metrics, exact source amounts and provenance.
  Guided growth, profitability, cash, balance sheet and valuation sections retain
  unsupported inputs and reasons. Returns on capital remain visibly unavailable.
- Company history retains 3/5/10-year options. Only one or two supplied company
  observations are plotted; missing quarters and unusable observations remain
  gaps. No sector history is substituted and no percentile/rank is activated.
  The three-year initial view is a demonstration choice, not a new product policy.
- Snapshot comparison displays sourced values available by the selected date.
  March excludes June from the comparison, plotted history and client evidence.
  Unknown issuer/date query values return not found, never another issuer's data.
- `/development/news`: Calendar, Stock topics and Monitor health views; all seven
  pilot companies and topic-category filters; separate CPI/PPI/FOMC stages and
  collection, assessment, host and three-channel delivery states. All sources,
  workers and deliveries remain explicitly unconfigured. Topics are a proposed
  catalog, not stories, active subscriptions or a fixed discovery allowlist.
- `/help`: development walkthroughs, 52 searchable definitions, contextual links
  and a printable guide. Planned workflows are distinguished from implemented
  demonstrations. This advances U1 without claiming its full release acceptance.
- Sector history pattern slots now remain stable when another selected series
  is removed or added. The single-accent adaptation of X-09 is explicit in the
  design reconciliation. All original 143 requirement rows remain preserved.

The company exporter projects existing core results, statuses and evidence.
Presentation types remain internal; no public API, production schema, normalized
concept, financial formula, provider policy or live-data connection changed.
Business profiles, causal/numerical change explanations, saved expectations,
watchlist resolution/full analysis and real-data publication remain later work.

## Verification

- 21 Python presentation tests pass (13 Company, 8 Sector), including exact
  equality of all 1,008 metric observations and 168 source details against the
  unchanged Sector fixture, future-date exclusion, gaps and null geometry.
- Independent numeric review found a malformed source-date identity gap; matching
  detail IDs and actual quarter ends are now enforced, with two red/green tests.
- Browser: all 42 Sector snapshot combinations match; 16 linked-flow checks pass,
  including stable patterns and exact Sector → Company source identity.
- Company browser regression: 10 issuer/date cases spanning eligible, N/M, stale,
  missing and unsupported states; 180 metric/window selections, 1,149 assertions.
  Values, statuses, reasons, source hashes, periods, geometry and gaps match the
  exporter. No future snapshot appears in the March comparison.
- Native source dialog blocks background focus; Escape closes and restores the
  triggering metric button. Interactive chart points and scroll regions remain
  keyboard accessible. SVG text hydration and two glossary-link defects found
  during browser/review work were fixed.
- `make lint typecheck` passes, including policy/vocabulary checks and full mypy
  (52 files). A namespace/module-identity conflict found by the full check was
  resolved by making the existing `scripts` directory an explicit Python package;
  checks were not weakened. Optimized Next.js production build passes.
- Company at 320/390/768/1440px has no page overflow; wide charts stay contained
  and accept keyboard scrolling. News Calendar/Topics/Health and Help pass the
  same four widths, skip-link checks, and 43 filter/search/navigation checks.
- The filtered Help print includes all 52 definitions across 13 pages, even when
  only 11 match the on-screen query. Final production PDF inspection confirms white paper margins and last-page
  space, dark readable text, and complete content after the print fixes.
- Eight production route cases pass: normal readiness redirect, all four
  development/Help destinations, and unknown issuer, unknown date and ambiguous
  query recovery. Unavailable selections display no company values and offer a
  recovery link. No console or page errors occur in the final production run.
  Next's streamed not-found response can have HTTP 200; no HTTP-status guarantee
  is claimed for this internal development route.

Evidence is retained under `var/d1b-*`; the scripts compare generated artifacts,
not independently fabricated expected financial calculations. Existing core
calculation tests remain the numerical authority. The initial 2026-09-19 delivery was a working-tree slice. The user then
authorized a reviewed recovery checkpoint on 2026-09-20; see
[checkpoint review](../design/ui-redesign/checkpoint-review.md) and the annotated
`milestone/d1b-redesign` tag. No deployment, monitoring schedule or external alert
was created.

## Next handoff

Prepare the seven-company source/identity/coverage pilot: CRCL, MSTR, COIN, HOOD,
USAR, MP, GOOGL, retaining dated instrument and business-profile evidence. Reuse
existing SEC/source stages and explicitly report provider/coverage gaps. Advance
S6's sequential snapshot/result/profile/thesis contract review before connecting
production data and persisted workflows. Keep the full F1/X1/W1/N1/R1/U1 feature
set and 5–10-year history options in the acceptance plan.

The local production preview is `http://127.0.0.1:3101/development/company`; shared
navigation reaches Sector Explorer, News, Help and production data readiness.

Checkpoint rerun (2026-09-20): 963 full, 225 core and 110 golden tests pass,
as do lint/types, optimized build and eight production browser route cases.

The authorized next source slice is recorded in [D2](D2-real-data-pilot.md),
with the separate real-source pilot and its exact publication/eligibility gaps.
