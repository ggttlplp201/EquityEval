# S8a review record

Fixed point: `ee39ff2`. Reviewed working changes on `codex/s8a-valuation-ui`
against [acceptance](acceptance.md), root/web AGENTS and the original specification.
The pre-commit review uses `git diff ee39ff2` plus new files because the checkpoint
must not be committed before its gates pass.

## Standards

Independent reviewer found one blocking forecast-table defect: enumerating JSON
object values could label amounts under the wrong heading after sorted export.
Explicit typed fields now follow the eight headers. The browser test asserts the
entire reference row against the independent hand oracle. A short payload
variable name was also clarified. Follow-up review: no remaining findings.

## Specification

Independent reviewer confirmed the same forecast defect and later corrected the
manual's sensitivity description: a named axis may override the supplied solved
parameter. Both fixes were re-reviewed. Final review: no remaining findings.

## Browser diagnosis

The browser test repeatedly reproduced a pending Next client-router transition
after interacting with the view. Capturing the selected value and suppressing
unrelated Company prefetch did not eliminate it. The bounded offline example
selector now uses standard local GET navigation; it preserves a shareable URL
and reloads only the selected public payload. The same complete browser suite
passes afterward. The exact underlying Next transition cause was not established.
The large unrelated Company fixture is no longer speculatively prefetched.

## Verified UI evidence

Six browser tests (five subtests and their parent) pass: 320/390/768/1440 layouts,
default reverse view, named scenarios, all eight forecast columns, keyboard
disclosures and sensitivity cells, source drawer/Escape/focus restoration,
no-solution/non-unique/inconclusive/unavailable/missing examples, Company/Help/skip
navigation and local GET-only/no-API requests. Captures and network evidence:
`var/s8a-browser/`; log: `var/s8a-browser.log`. Desktop and narrow captures inspected.

No schema, API, migration, engine formula or S7a seed/test fixture changed.
Final full/core/golden and commit-hook evidence belongs to the milestone record.

## Coordinator corrective audit — 2026-09-29

The original independent review missed three acceptance gaps at `fff930f`:
its span label asserted eligibility even when no span existed, selected bridge
endpoints were not visible together, and some financial values were plain text
without direct evidence controls. The original commit/tag remain unchanged.

The corrective diff adds a span presentation gate with exact reasons: at least
two named scenarios, exact unique agreement with the declared assumption roster,
every result converged with a representative, and a saved non-null span. The
browser never derives the span. Follow-up spec review found the two-of-three
roster edge case; failing/then-passing tests now cover it and duplicate/unknown
names. Node tests transpile at the web workspace's ES2022 target.

The selected bridge exposes saved operating EV, signed adjustment, common
equity, shares and conditional per-share value as exact decimal strings.
Non-converged output fields remain N/A. Six Node presentation tests and four
Python presentation tests cover state labels, roster eligibility, exact signed
passthrough and independent reference endpoints.

A reusable EvidenceValue button now connects financial values directly to the
shared drawer: domains/results, forecast amounts, assumption values, terminal
contribution/threshold, numerical intervals/counters, sensitivity axes/results/
effects/ranks, bridge components/endpoints and source uncertainty. Dates and
forecast-year labels remain ordinary context. Expanded browser checks exposed
a queued native dialog close event dismissing a new inspection. Escape now
uses controlled cancellation; state closes the dialog without stale close-event
callbacks. Close-button and backdrop behavior in the Company view are checked.

Spec and standards reviewers rechecked the final changes and reported no
remaining findings. Corrective browser evidence lives in
`var/s8a-correction-browser/` and `var/s8a-correction-browser.log`, preserving the
original checkpoint's captures. Full gate results are recorded in the milestone.

The first corrective full gate failed two unchanged parameterized filing-monitor
cases (`test_advertised_history_requires_only_overlap_and_never_truncates`,
True/1 and True/11): acquisition raised LeaseLost in one; the other returned
error instead of incomplete. No monitor/transport/schema code is in this diff.
The complete unchanged filing-monitor file then passed **34 tests** in isolation
(`var/s8a-correction-monitor-rerun.log`). The exact transient cause was not
established; no tests, assertions or timing limits were relaxed. The initial
failed log is preserved as `var/s8a-correction-verification.log`; the full retry
is separate in `var/s8a-correction-verification-retry.log`.


## Display-rounding review — 2026-09-29

Fixed point `4caf54b`; bounded working diff reviewed independently on standards
and specification axes. Both found no findings. Financial computation and exact
saved evidence remain untouched. The shared formatter uses Decimal-string digits
and BigInt for display rounding, avoiding binary-float precision loss. Explicit
structured numeric fields protect metadata. Added red/green tests exercise
halfway cases, signs, carry, exponent notation, percentage scaling, large
integers, missing values and immutable metadata/evidence.

The four viewport browser regressions check rounded main-view numbers, original
exact strings in keyboard-accessible evidence, all solver states and source
controls. Detailed execution evidence belongs to the milestone record.
