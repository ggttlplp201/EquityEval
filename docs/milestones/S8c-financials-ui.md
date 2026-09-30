# S8c — saved financial statement lines

Status: complete for the bounded fictional/read-only scope, including the
independent coordinator coverage-evidence correction.
Branch: `codex/s8c-financials-ui`.
Baseline: `30c35c61b9f42602381acbf5c0ae2423ecc2b762` (clean S8b).
Final implementation commit: `7a96cb645cf58a7c369a9eb650d9465d3a7d54e7`.
Final annotated tag: `milestone/s8c-financials-ui-corrected`.
Original implementation: `c0f6bc60a2c6ed0643662eefc2f009fd8f481c8c` and
`milestone/s8c-financials-ui`, both preserved.
Acceptance: [pinned audited boundary](../design/s8c/acceptance.md).
Manual: [Saved Financials](../user-manual/saved-financials.md).

## Delivered scope

`/development/company/financials` presents a separate fictional company with
Income statement, Balance sheet and Cash flow sections. Three immutable local
snapshots: original annual, revised annual and directly reported first quarter.
No S6a selected metrics are relabelled as full statements. The checked exporter
uses existing Concept, PeriodSpec, UnitSpec and canonical content hashes. No
core, shared schema, API, migration, provider or production-publication change.

Exact source strings, dates, units, scope, source identity and revision lineage
are retained. Balance-sheet periods are instants; flows are durations; TTM is
disabled. Missing lines remain null/N/A. Visible amounts round at four decimals;
the shared drawer retains exact strings. Both supplied coverage counts open the
exact statement coverage, selected-row roster/evidence and snapshot identity.
React does not calculate amounts or coverage. Shared navigation and Help link
the new page; S8a/S8b financial behavior and 3/5/10-year history stay unchanged.

## Independent reviews and corrections

[Review record](../design/s8c/review.md) retains both axes and their rereviews.
Initial spec/standards review found precision-only edits mislabelled as financial
restatements, plus an undefined CSS border token. Fixed using Decimal equality
for status only (exact source strings retained), signed-zero regressions and the
existing --line token. Rereviews found no remaining issues in those changes.

A separate coordinator two-axis review against baseline 30c35c6 found:

- **Spec P2:** coverage counts had no clickable provenance. Corrected in 7a96cb6;
  all six controls open exact supplied counts and their statement's row evidence.
  A red-first Node test injects distinctive supplied counts to detect browser
  recomputation; browser assertions compare the complete saved coverage and rows.
  Narrow independent spec rereview found no remaining coverage issue.
- **Standards Low:** committed milestone/index/roadmap status was stale. The
  corrective commit incorporated the staged traceability updates, and this final
  record identifies both implementation commits and immutable checkpoint tags.

The coordinator's hold arrived just after the original tag was created. That tag
was preserved; the documentation commit was stopped pending review results.
`var/s8c-record-commit-checks-interrupted.log` is a partial, intentionally stopped
run, not a completed or failed gate. No S8d work began.

## Verification and evidence

- **20 Python source tests**: exact source-pointer/period/unit/snapshot binding,
  temporal and incompatible-input rejection, nulls/coverage, content-bound IDs,
  separate editions and financial versus formatting restatement distinction.
- **4 S8c Node tests**: fail-closed exact selectors, rounded/exact values, actual
  server route isolation and inspectable supplied coverage/row/source identity.
- **7 Financials browser tests**, `var/s8c-corrected-browser.log`: 320/390/768/1440,
  every edition, all six coverage controls, full exact source evidence, N/A,
  keyboard/focus, invalid selectors, local GET-only requests, actual pending DOM
  status and disabled control, missing-fixture error and Retry recovery to the
  exact snapshot. Fault injection restores the source fixture byte-for-byte.
- Production build: `var/s8c-corrected-build.log`. Final screenshots in
  `var/s8c-browser/`; all four responsive widths were inspected, with 320px
  inspected again after the coverage correction. Every column fits its container.
- Mandatory corrected commit hook: `var/s8c-corrected-commit-checks.log` —
  **1,636 full tests** (two existing upstream warnings), **505 core**, **110
  golden**, Ruff/policy, generated contracts and deterministic exports, **18
  Node tests** (S8a 8 + S8b 6 + S8c 4), ESLint, Python types (**93 sources** plus
  Linux launcher) and TypeScript. Original gate: `var/s8c-commit-checks.log`.
- Prior browser regressions: **6 S8a** in
  `var/s8c-prior-browser-regression.log`; **6 S8b** in
  `var/s8c-fundamentals-regression-final.log`. The coverage correction changes no
  S8a/S8b or shared-component code; their 14 Node checks also pass in the final
  corrected hook. One earlier S8b client-navigation timeout was preserved; five
  isolated unchanged transitions and the full unchanged rerun passed. No root
  cause or permanent fix for that pre-existing intermittent behavior is claimed.

Verification repaired mobile table clipping and a real Retry lifecycle bug:
boundary reset did not reread the restored file, so Retry now performs a fresh
local GET. Test harness corrections avoided waiting on intentionally held
navigation and disambiguated the Financials error panel from Next's announcer.
Assertions and timeout limits were not weakened. Earlier failing logs are retained.
Red-first logs: `var/s8c-red-python.log`, `var/s8c-red-node.log`,
`var/s8c-restatement-red.log`, `var/s8c-coverage-red.log`.

The corrective implementation left a clean tree. Main, all S8a/S8b refs and the
original S8c tag were verified unchanged. This final documentation-only record
runs the required hook again (`var/s8c-final-record-checks.log`); it does not
change the tagged implementation. The final task response reports its commit.

## Limits and stopping point

Selected statement lines only; coverage is not full-filing completeness. Only
fictional calendar-year and direct-quarter sources are reviewed. No TTM, YTD
conversion, inferred accounting totals, investment verdict, live refresh or real
publication. Production source/normalization/publication gates remain open.
Stop at corrected S8c. S8d and recurring activation have not started.
