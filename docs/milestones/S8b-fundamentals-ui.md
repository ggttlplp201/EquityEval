# S8b — read-only fictional fundamentals

Status: pending checkpoint; implementation, focused checks and reviews are complete.
The full commit hook and creation of the planned tag have not completed.
Task: EquityEval milestone build log, continued on 2026-09-29.
Branch: `codex/s8b-fundamentals-ui`; baseline `f46bf52`.
Planned tag: `milestone/s8b-fundamentals-ui` (not yet created).
Dependencies: S5 source engines, S6a public contracts, D1b shell/drawer, S8a rounding.
Source: [F1](../features/F1-fundamentals-guide.md), S6a and
[pinned acceptance](../design/s8b/acceptance.md).

## Scope and artifacts

`/development/company/ratios` adds a separate fictional S6a Fundamentals view,
linked from Company and shared navigation. D1b's Sector-derived company values
are never joined to it. The route selects an exact offline snapshot, not a
published application database result. Only the selected payload reaches the
browser. Annual and instant basis selections remain separate; no annual-to-TTM
relabeling or mixed-period summary is inferred.

Five sections retain Growth → Profitability → Cash generation → Balance sheet
→ Valuation order; Returns on capital expands independently. All seven statuses,
actual values/nulls/reasons and separate coverage counts survive. At most three
saved neutral review/observation items render. The existing number formatter
rounds visible values to four decimals while the shared drawer retains exact
source values, operands, coefficients, formula revisions, dates, IDs and hashes.

3/5/10-year controls select saved PublicHistory windows without shortening them.
The UI shows eligible/excluded counts, IDs/reasons, missing quarter ends and
minimum samples. Saved quartiles supply an accessible chart and matching table;
insufficient windows show N/A. The public contract contains no time-series sample
values; none are invented. Historical drawers expose saved snapshot references
and never present current operands as sources for past percentiles.

Production fixture recipe: `scripts/fixtures/fundamentals-presentation.json`.
Typed source builder: `scripts/fundamentals_presentation_inputs.py`.
Exporter: `python scripts/project_python.py -m scripts.export_fundamentals`,
with `--check` in `make lint`. It validates canonical InputManifest roundtrips,
executes unchanged core and validates FundamentalsPayload output. Seven examples,
two reference evaluation dates and three requested history windows yield 24
exact offline snapshots. Capture/batch/edition/observation identities bind the exact fictional input vintage,
and scope identities bind their descriptors. Source inputs and explicit policies are fictional;
no production defaults are established. Help and the manual include walkthroughs.

## Decisions and reviews

See [review](../design/s8b/review.md). Two-axis review findings on history
provenance and tied chart labels were repaired and re-reviewed with no remaining
findings. A CSS-module build error and SVG-text test harness error were fixed;
screenshot inspection strengthened navigation readiness checks and the loading
state. No timeout/assertion was weakened.

## Validation evidence

- Red-first Python exporter tests failed before the exporter existed; **9 passed**
  after implementation: independent ratio/FCF/ROA/quartile oracles, all seven
  statuses/counts, 3/5/10 windows/exclusions, future-data exclusion and no-diff.
- Red-first Node presentation tests failed before the presentation module existed;
  **6 passed** with tied-label and exact-route ambiguity regressions. Existing S8a **8** remain in lint.
- Production build and standalone Python/TypeScript checks passed.
- Browser: 320/390/768/1440, all status examples, exact saved selector/history,
  N/A/N/M/retained stale values, evidence and focus, chart ties, future-data
  exclusion, Company/S8a/Help links, invalid selectors, local GET-only/no API.
- Logs: `var/s8b-build.log` (initial CSS failure),
  `var/s8b-build-final.log`, `var/s8b-build-reviewed.log`,
  `var/s8b-browser.log` (initial SVG harness error),
  `var/s8b-browser-final.log` (6 passed before screenshot readiness fix),
  `var/s8b-browser-reviewed.log`, and `var/s8b-browser/`.
- Mandatory commit hook runs lint, generated no-diff checks, Python/TS types,
  full/core/golden suites on the exact staged tree. Final totals are recorded in
  the annotated checkpoint tag and `var/s8b-commit-checks.log`.

## Limitations and handoff

No provider/live-data access, real publication, migrations, API/schema/generated
contract changes, writes, watchlist orchestration, peers/forward estimates,
scores, recommendations or price targets. The S6a registry does not publish a
usable P/E here; the saved unsupported row remains N/A. PublicHistory lacks
sample values/operands; history snapshot references remain visible. Real
quote/basis/calendar, fiscal/PIT normalization, source rights and production
policy/publication prerequisites remain unchanged. S8c/S8d have not started.


Final visual verification: completed snapshots at all four widths were inspected,
with no page overflow. The browser selector helper verifies the new URL, exact
saved snapshot ID and first visible metric/status before further assertions or
capture. The S8a regression suite also passed **6 tests** after navigation changes
(`var/s8b-valuation-regression.log`). Content-bound fixture identity was then
verified by a sixth Python regression and an independent standards follow-up;
final rebuilt evidence is `var/s8b-build-checkpoint.log` and
`var/s8b-browser-checkpoint.log`.


Coordinator follow-up found ignored unknown query keys and first-match selection
of duplicate saved candidates. Red regressions confirmed the gaps. Export now
rejects duplicate example IDs/dates and final selection keys; the actual route
allowlists example/date/years and requires exactly one candidate. Python and
Node route tests pass; browser includes the unknown-key case. Both review axes
confirmed the repair. Final build: `var/s8b-build-selector.log`; final browser:
`var/s8b-browser-selector.log`.

`var/s8b-browser-checkpoint.log` passed all four viewport flows but timed out on
navigation to Reverse DCF. Isolated Company → Fundamentals → Reverse DCF passed.
Navigation checks now wait for completed destination content between link clicks,
retaining all timeouts and assertions. The clean final browser pass is recorded below; earlier logs remain as the
diagnostic record. Full commit-hook verification is still pending.


Final pre-commit browser result: **6 passed** in `var/s8b-browser-selector.log`,
including the navigation/invalid-selector/GET-only footer subtest. All four
completed-snapshot screenshots were regenerated under `var/s8b-browser/`.
The final selector build passed. Full checkpoint completion remains conditional
on the mandatory hook and the subsequently created annotated tag.
