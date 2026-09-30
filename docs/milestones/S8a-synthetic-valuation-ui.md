# S8a — synthetic valuation UI

Status: verified for the bounded fictional/read-only scope on 2026-09-29.
Baseline: `ee39ff2` (main). Branch: `codex/s8a-valuation-ui`.
Checkpoint tag: `milestone/s8a-synthetic-valuation-ui`.
Acceptance: [pinned design](../design/s8/acceptance.md).

## Delivered

Read-only `/development/valuation` uses the existing generated S7a TypeScript
contracts and audited Python core. Reverse DCF is the default. Named scenarios,
declared domains and solver states remain inspectable alongside observed market
common value, operating EV target, deterministic complete-roster span, terminal
contribution and seven-component economic-claims bridge.

Separate fixed presentation manifests supply two useful sensitivity grids and
no-solution, inconclusive, unavailable and multiple-solution examples. Missing
saved output is distinct. No S7a formula or audited test fixture was changed.
The exporter validates every manifest and generates public payloads only;
private author/rationale fields are excluded. The checked JSON is reproducible.

Scenario/root/source uncertainty remain separate. Exact decimal evidence,
assumptions, policy, source dates/IDs/hashes and claim-coverage exclusions use the
shared evidence drawer. Company, development navigation and Help link the view.
All values are fictional and frozen. Financial computation stays in core.

## Verification record

- Red exporter tests: collection failed because the exporter did not yet exist.
- Three Python presentation tests: bridge and sensitivity hand oracles, state
  preservation, uncertainty separation, deterministic public output and no-diff.
- Two Node presentation tests: missing versus zero, exact Decimal retention and
  five distinct solver labels.
- Browser suite: four widths (320/390/768/1440), default view, scenario/grid/cell
  controls, exact forecast row, evidence/Escape/focus return, state examples,
  responsive overflow, Company/Help/skip links and GET-only local requests.
- Two-axis review found one forecast-column ordering issue. Explicit field
  order replaces object enumeration; browser regression checks all eight columns.
- Production build passed; valuation route adds 5.9 kB with 112 kB first-load JS.
- Full suite **1,606 passed**; core **505 passed**; golden **110 passed**.
- Ruff/format/policy, generated contracts and fixture no-diff passed; mypy
  checked 90 source files and the Linux launcher; TypeScript/ESLint passed.
- Browser **6 passed** (five subtests and parent); Node presentation **2 passed**.
- Standards: no remaining findings. Specification: no remaining findings.
- Logs: `var/s8a-verification.log`, `var/s8a-build.log`,
  `var/s8a-browser.log`; required commit rerun: `var/s8a-commit-checks.log`.
  Two dependency deprecation warnings (Starlette/httpx and AnyIO) remain;
  neither is introduced by this UI. No test was skipped or weakened.

## Remaining production prerequisites

Reviewed real quote identity/retention rights and provider inputs, lifecycle
coverage, governed real normalization/PIT/fiscal inputs, eligible fundamentals
publication and real valuation assumption/evidence review remain necessary.
This milestone activates no provider, scheduler, application write, production
valuation or live assumption editor. Forward DCF, Monte Carlo and comps stay in
later scope. The accepted company 3/5/10-year history choices are unchanged.

## Corrective checkpoint — coordinator audit

Baseline `fff930f` and `milestone/s8a-synthetic-valuation-ui` are preserved.
The subsequent audit identified three gaps not caught by the initial review:
truthful null-span eligibility, visible selected bridge endpoints and direct
provenance controls for all financial values. The bounded correction addresses
all three and fixes the shared drawer's queued-close race revealed by consecutive
keyboard evidence inspections. See the appended [review](../design/s8/review.md).

No core formula, schema, API, migration, source manifest or generated valuation
fixture changed. There are no provider, production-data or scheduling side effects.
Corrective checkpoint tag: `milestone/s8a-synthetic-valuation-ui-corrected`.

Corrective verification completed on 2026-09-29:

- Full retry **1,607 passed**, core **505 passed**, golden **110 passed**.
- Python presentation **4 passed**; Node presentation **6 passed**; browser
  **6 passed** (four viewport subtests, navigation/shared-drawer subtest, parent).
- Fixture and generated-contract no-diff, Ruff/format/policy, ESLint,
  Python/Linux and TypeScript checks, and production build passed.
- Spec and standards follow-up: no remaining findings.
- Initial full attempt: two unchanged filing-monitor cases failed (lease loss
  and error outcome); all **34 monitor tests** then passed unchanged in isolation,
  followed by the successful full retry. No test or timing limits were relaxed.
  The transient cause remains unestablished; both logs are retained.
- Evidence: `var/s8a-correction-verification.log` (initial failure),
  `var/s8a-correction-monitor-rerun.log`,
  `var/s8a-correction-verification-retry.log`, `var/s8a-correction-build.log`,
  `var/s8a-correction-browser.log` and `var/s8a-correction-browser/`.
  Required commit-hook rerun: `var/s8a-correction-commit-checks.log`.

The previous S8a verification counts above describe the preserved original
checkpoint. This corrective record supersedes its acceptance assessment.


## Display-rounding correction — 2026-09-29

Baseline `4caf54b` and both prior S8a checkpoint tags remain unchanged.
New checkpoint: `milestone/s8a-rounded-display`.

Visible valuation values now round to at most four decimal places, trim trailing
zeros and preserve integer precision. Decimal digits round halfway away from
zero; percentages shift before rounding. The same presentation covers scenarios,
domains, forecasts, solver intervals/certificates, assumptions, sensitivity
axes/results/effects, claims, bridge endpoints and source uncertainty. Exact
saved values remain in the evidence drawer. Numeric structured fields are
explicitly selected so IDs, dates, hashes, names and unrecognized metadata remain
unchanged. N/A remains separate from zero. Rounded numerical interval endpoints
may coincide; their exact saved bounds remain available by selecting the value.

Captions, Help and the user manual distinguish rounded display from exact
saved evidence. No core, schema, API, migration, manifest, fixture or provider
changes are part of this correction. No next milestone has started.

Verification:

- Tests written first: the two new formatting tests failed before implementation.
  All **8 Node presentation tests** and **4 Python presentation tests** now pass.
- Production build passed, including frontend lint and TypeScript validation.
- Independent specification and standards reviews: no findings.
- Browser evidence and refreshed desktop/mobile captures:
  `var/s8a-rounding-browser/`; build: `var/s8a-rounding-build.log`.
- The mandatory commit hook records lint, all generated no-diff checks, Python
  and TypeScript checks, full/core/golden tests in
  `var/s8a-rounding-commit-checks.log`. This checkpoint is created only if all
  required gates pass; the annotated tag records final test totals.

- Browser **6 passed** on the unchanged suite retry, including all four viewport
  flows and Company navigation/shared drawer/Help. Initial run passed the four
  viewport flows but timed out at Company-to-valuation navigation. Isolated
  reproduction then passed, followed by the clean full browser retry. Cause
  remains unconfirmed; no timeout or assertion was weakened. Retained logs:
  `var/s8a-rounding-browser.log` and `var/s8a-rounding-browser-retry.log`.
