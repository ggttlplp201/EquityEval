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
