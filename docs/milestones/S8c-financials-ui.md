# S8c — saved financial statement lines

Status: bounded corrective pass in progress after independent coordinator review.
Original implementation commit: `c0f6bc60a2c6ed0643662eefc2f009fd8f481c8c`.
Original annotated tag: `milestone/s8c-financials-ui` (preserved).
Corrected commit/tag pending successful corrective verification.
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
S8b browser regression passed all 6 tests. The mandatory full commit gate passed.
See [review and repairs](../design/s8c/review.md). The checkpoint tag resolves to the tested implementation commit above.
This final record follows that checkpoint in a documentation-only commit.

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
`var/s8c-browser/financials-{320,390,768,1440}.png`; all four final neutral-focus
responsive screenshots visually inspected. No table or page overflow.
Earlier failing/aborted browser logs remain preserved for traceability.

S8a browser regression passed 6 tests in `var/s8c-prior-browser-regression.log`.
That run also reproduced S8b's previously recorded client-navigation timeout;
five isolated unchanged Fundamentals-to-Reverse-DCF transitions subsequently
passed (`var/s8c-navigation-probe.log`). No cause or fix for the intermittent
framework/navigation behavior is claimed; the full unchanged S8b test subsequently passed all 6 checks
(`var/s8c-fundamentals-regression-final.log`). Existing frontend financial behavior is unchanged.


## Final checkpoint evidence

- `var/s8c-commit-checks.log`: mandatory hook passed on implementation commit
  `c0f6bc6`: **1,636 full tests** (two existing upstream warnings), **505 core**,
  **110 golden**, Ruff/policy, generated contracts and all three deterministic
  UI exporters, **17 Node tests** (S8a 8 + S8b 6 + S8c 3), ESLint, Python types
  (**93 sources** plus Linux launcher check) and TypeScript.
- New S8c source suite: **20 tests**, including exact source-pointer binding,
  temporal/period/unit rejection, explicit nulls, content-bound identity and
  financial-vs-formatting restatement distinction.
- `var/s8c-build-recovery.log`: optimized production build passed, including the
  new route and actual Retry reload repair.
- `var/s8c-browser-recovery.log`: **7 passed**. Prior regressions: **6 S8a** in
  `var/s8c-prior-browser-regression.log`, **6 S8b** in
  `var/s8c-fundamentals-regression-final.log`. Earlier failed attempts remain
  documented above; assertions and timeout limits were not weakened.
- Spec/standards reviewers rereviewed their fixes with no remaining findings;
  the standards reviewer additionally checked the real Retry recovery repair.
- Before final recording, working tree was clean after implementation commit.
  `main` and every S8a/S8b checkpoint ref matched `var/s8c-prior-refs.json`.
  No diff in core, shared schemas, APIs or migrations. Final documentation commit
  runs the mandatory hook again (`var/s8c-record-commit-checks.log`).

S8c is the stopping checkpoint. S8d, production financial statements, real
publication and recurring activation are not started by this milestone.


Coordinator requested a hold after the implementation commit and tag had already
been created. The documentation-only commit was interrupted before completion
(`var/s8c-record-commit-checks-interrupted.log`, partial run, not a failed or
completed gate). The existing tag is preserved. No S8d work starts; final record
and clean-tree checkpoint await the additional independent review results.


## Corrective scope

Additional coordinator spec review found orphan coverage counts; both supplied
available/requested counts now open the exact saved coverage, statement row
roster/evidence and snapshot identity. No browser count calculation was added.
Focused Node and four-width browser tests cover all six controls. Standards review
found stale committed traceability text; these records are included in the new
corrective commit. The original commit/tag stay immutable; the final corrected
checkpoint will use `milestone/s8c-financials-ui-corrected` after checks pass.


Corrective focused evidence: **20 Python source tests**, **4 Node UI/route tests**,
**7 Financials browser tests** (`var/s8c-corrected-browser.log`) and optimized
build (`var/s8c-corrected-build.log`) passed. All six counts open their exact
statement coverage and row evidence; 320px screenshot re-inspected with every
column and count visible. Narrow independent spec rereview found no remaining
coverage issues. The correction does not change S8a/S8b or shared components;
their already-passed full browser regressions above remain applicable, and their
14 Node regressions run again in the corrected mandatory hook. Corrective full
hook evidence will be `var/s8c-corrected-commit-checks.log`; tag/commit references
are finalized only after successful completion.
