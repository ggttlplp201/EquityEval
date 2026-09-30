# S8c — saved financial statement lines

Status: implementation and verification in progress; commit/tag pending.
Branch: `codex/s8c-financials-ui`.
Baseline: `30c35c61b9f42602381acbf5c0ae2423ecc2b762` (clean S8b).
Acceptance: [pinned audited boundary](../design/s8c/acceptance.md).
Manual: [Saved Financials](../user-manual/saved-financials.md).

## Implementation

`/development/company/financials` presents a separate fictional company with
Income statement, Balance sheet and Cash flow sections. Three immutable local
snapshots: original annual, revised annual and directly reported first quarter.
No S6a selected metrics are relabelled as full statements. The checked exporter
uses existing Concept, PeriodSpec and UnitSpec semantics and content hashes.
No core, shared schema, API, migration, provider or production-publication change.

Exact source strings, dates, units, scope, source identity and revision lineage
are retained. Balance-sheet periods are instants, flows are durations, TTM is
disabled. Missing lines remain null/N/A. Visible amounts round at four decimals;
the shared evidence drawer retains exact strings. Shared navigation and Help
link the new page; existing S8a/S8b data and history behavior remain unchanged.

## Validation

Red-first exporter and selector tests were captured in `var/s8c-red-python.log`
and `var/s8c-red-node.log`. Focused exporter tests pass 20; Node tests pass 3.
Build, lint, types, independent reviews and all 7 S8c browser checks passed.
S8b browser regression passed all 6 tests; only the full commit gate remains pending.
See [review and repairs](../design/s8c/review.md). No checkpoint tag exists
until those checks complete. Final evidence and exact references will be recorded
after commit/tag; no completion is claimed here.

## Limitations and handoff

Selected statement lines only; coverage is not a full-filing completeness claim.
Only fictional calendar-year and direct-quarter sources are reviewed. No TTM,
YTD conversion, accounting total inference, investment verdict or live refresh.
Production data rights, normalization/publication and remaining company-page
milestones retain their gates. Stop at S8c after its reviewed checkpoint.


Browser evidence: `var/s8c-browser-recovery.log` is the final 7-pass Financials
run against `var/s8c-build-recovery.log`. It covers four widths, every edition,
exact source strings, N/A, keyboard/focus, invalid selectors, local GET-only
requests, actual pending DOM state, missing-fixture failure and Retry recovery.
Source fixture was restored byte-for-byte after fault injection. Screenshots:
`var/s8c-browser/financials-{320,390,768,1440}.png`; final neutral-focus 320/1440
and all responsive widths visually inspected. No table or page overflow.
Earlier failing/aborted browser logs remain preserved for traceability.

S8a browser regression passed 6 tests in `var/s8c-prior-browser-regression.log`.
That run also reproduced S8b's previously recorded client-navigation timeout;
five isolated unchanged Fundamentals-to-Reverse-DCF transitions subsequently
passed (`var/s8c-navigation-probe.log`). No cause or fix for the intermittent
framework/navigation behavior is claimed; the full unchanged S8b test subsequently passed all 6 checks
(`var/s8c-fundamentals-regression-final.log`). Existing frontend financial behavior is unchanged.
