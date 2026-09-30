# S8d — Company Overview integration

Status: complete for the bounded fictional/read-only scope, including the final
independent missing-marker correction.
Branch: `codex/s8d-company-overview`.
Baseline: `ee50c317874dbcc1464d5fdc2fb971411dd31b56`.
Corrected implementation: `bdc3a977128be19c371269d5f32405e7a997b8fd`.
Annotated tag: `milestone/s8d-company-overview` (points to corrected implementation).
Original implementation: `8f04518fdb650d4533a61fa23b3f337a937d9f3d` (preserved, untagged).
Acceptance: [pinned before implementation](../design/s8d/acceptance.md).
Reviews: [two axes and coordinator correction](../design/s8d/review.md).
Manual: [Company Overview](../user-manual/company-overview.md).

## Delivered scope

`/development/company` keeps the existing calculations and saved 3/5/10-year
history while adding Overview, Financials, Fundamentals and Reverse DCF cards.
All 168 views (84 fictional issuers, two evaluation dates) have checked metadata
linkage. The selected Overview is ready only for itself; the three other
workspaces are separate fictional examples. Their links open their own defaults.
No financial amounts are joined, recomputed, or republished across workspaces.

The deterministic local exporter retains exact identities, per-amount scope,
source selectors, date precision, actual local file/payload hashes and distinct
declared source hashes. Missing security/known/retrieved/as-of proof cannot
establish compatibility. Null, N/A and blank proof stay unavailable, including
nested metadata. Cutoffs are not relabelled as retrieval times. Runtime server
reads verify the exact four-file roster and byte hashes, then project only the
selected issuer's saved financial history and corresponding linkage evidence.

Counts and dates open exact linkage/history/source evidence. GET selectors
reject unknown keys, repeats, unsupported pairs and ambiguous candidates.
Four-decimal formatting retains %, × and $, with full precision in the drawer.
N/A, keyboard/focus, responsive layout, pending selection and recovery are tested.
No core/schema/API/migration/provider/scheduler change. The four existing source
fixtures are byte-identical to the baseline.

## Reviews and corrections

Independent local spec/standards reviews found shifted context paragraphs,
incorrect snapshot links for unavailable dates, and an exact-versus-rounded
caption mismatch. Corrected and rereviewed with no remaining findings. An early
coordinator check caught dropped $/× units; a unit-aware display wrapper reuses
the existing exact-decimal formatter. Actual rendered section/date regressions
now cover the errors rather than checking phrases anywhere in a source file.

The coordinator's final independent review found **High: equal literal N/A
fields could count as compatibility proof**. The bounded corrective commit
requires affirmative nonmissing string leaves recursively through dictionaries,
lists and tuples. Case/whitespace handling is confined to detecting N/A/blank
markers; legitimate strings and equality remain exact and evidence is never
mutated. Red-first regression: 14 failures and 19 passes before the correction.
Both narrow rereviews found no remaining issue. The initial commit was preserved;
only the corrected implementation received the milestone tag.

## Verification

- **46 focused Python tests:** 33 metadata/compatibility checks plus 13 existing
  Company presentation tests. `var/s8d-corrected-python.log`.
- **26 Node tests:** S8a 8, S8b 6, S8c 4, S8d 8. Exact selection, server file/hash
  rejection, selected-date isolation, supplied counts, exact evidence, units,
  section-specific missing reasons and date-specific unavailable evidence.
- **26 browser checks:** S8d 7, S8a 6, S8b 6, S8c 7, run sequentially against the
  corrected build in `var/s8d-corrected-browser.log`. The original verified runs
  remain in `var/s8d-browser-verified.log` and `var/s8d-prior-browser.log`.
  All four widths (320/390/768/1440), full precision, units, linkage evidence,
  history, actual navigation/recovery, keyboard/focus and local GET-only traffic
  pass. All four Overview screenshots in `var/s8d-browser/` were inspected.
  Existing wide tables retain horizontal scrolling; new cards fit each width.
- **Production build:** `var/s8d-corrected-build.log`. Lint/types and deterministic
  exporter no-diff: `var/s8d-corrected-lint-types.log`. The sentinel correction
  does not change the generated manifest or any frontend file.
- **Mandatory corrected commit hook:** `var/s8d-corrective-commit-checks.log` —
  **1,669 full tests** (two existing upstream warnings), **505 core**, **110
  golden**, Ruff/policy, generated contracts/exports, **26 Node**, ESLint,
  Python types (**94 sources** plus Linux launcher), TypeScript. Original hook:
  `var/s8d-commit-checks.log` — 1,649 full, 505 core, 110 golden, 26 Node.
- **Preservation:** all **39 prior refs** unchanged; main and previous milestone
  tags preserved. Four source fixture byte hashes and unchanged core/schema/API
  are recorded in `var/s8d-preservation-check.json`. The corrected implementation
  left a clean tree; the annotated tag target/type were verified before this
  documentation-only record. This record runs the same mandatory hook in
  `var/s8d-final-record-checks.log`; its final commit SHA is reported in the task.

Earlier failing logs are retained. Browser verification found missing explicit
selector names and a retained not-found boundary: a client Link changed the URL
but left N/A visible. A native GET form fixes actual user-control recovery; the
assertion was not replaced by programmatic navigation. Error Retry performs a
fresh GET, and fault injection restores the exact manifest bytes. The generated
Next cache's duplicate declarations were resolved by rebuilding generated output
(old cache retained in var), without relaxing source type rules.
Red logs: `var/s8d-red-python.log`, `var/s8d-red-node.log`,
`var/s8d-units-red.log`, `var/s8d-sentinel-red.log`.

## Limits and stopping point

These remain separate fictional datasets, not a unified real-company analysis.
No live source, recommendation, composite score, AI narrative or new calculation.
Real data/publication, provider access, background monitoring and other original
Overview features retain their separate gates. Stop at corrected S8d.
