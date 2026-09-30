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
