# D5a — First governed CRCL normalization and PIT

Status: complete for the bounded D5a scope.
Recovery checkpoint: annotated `milestone/d5a-crcl-normalization`, created only
after the implementation commit passes its mandatory hook.
Baseline: ff4cfa32dffab9505a1c840ed7ac33cb3df2e7a8 (clean corrected S8d).
Proposal checkpoint: 24bd2ae, committed after mandatory full/core/golden/lint/types.
Branch: codex/d5a-crcl-normalization.
[Concrete proposal, source audit, acceptance and red-first plan](../design/d5a/proposal.md).
[Immutable real publication audit](../research/crcl-normalization-2026-09-30.json).
[User guide](../user-manual/real-normalization.md).

## Real outcome

Batch `923458e4-242d-4731-9f57-9fd6779d7e9a` was published at
2026-09-30T00:55:38.969756-07:00. Owner mapping
`b4b8a7fa-f01d-5b60-8a15-9f4668c2d40d` has its genuine approval time, separate from
the original SEC acceptance/retrieval times. Application migration remains 0010.

- One mapping revision and one published batch, exact replay reused.
- Five retained captures in the batch, three filing identities/versions, one
  annual consolidated coverage row, nine source observations/candidates, two
  selected resolutions and two quality flags.
- FY2025 revenue/reserve income: 2,746,642,000 USD; operating income: −96,435,000 USD.
- March 9 filed cutoff selects both original facts. March 8 selects neither.
  Original mode retains `earliest_available`; all observed modes are valuation-ineligible.
- `inventory_history_incomplete` and `event_history_incomplete` remain errors;
  the PIT summary is `blocking_quality_flag`. Exact underlying IDs are retained.
- All prior public-table rows preserved. No new capture, request, execution,
  quote identifier, watchlist membership or financial/valuation result was added.

The original annual report, July amendment and August quarterly filing remain
separate. The amendment adds Circle Reserve Fund statements; no restatement edge
was invented. No quarterly or comparative coverage was extrapolated. Nine retained
Company Facts candidates do not mean nine independently selected/eligible facts.

Input hash `7970f9dc775f50f0c136ce66234e1a5478cd682fce75517ae24f222458caff47`;
output hash `1971a99bc729858fc3d60c703834d7d3444b8c0a2ad38f6f2f902730c2e445f5`.
Audit SHA256 `db58bf64ca5a84501e02417af563e931074beaa6574fdef51a3a47c2fc4917db`.

## Implementation and verification

The bounded CLI checks the immutable D3c audit and DB/policy/request lineage,
replays archive hashes, binds exact inventory metadata/context/units/periods and
reuses the reviewed normalizer. Source precision stays separate from unknown
Company Facts precision. No shared schema, API, concept enum or engine changes.

The red-first preparation suite initially failed because the module did not exist.
33 focused pure/export/disposable-DB tests now pass, covering malformed inputs,
late captures, issuer/accession/date/context/unit/sign/precision disagreement,
zero versus missing, exact replay, concurrency and late transaction rollback.
The complete application orchestration is tested against a disposable runtime.
Existing S3/PIT suites retain broader vintage/amendment/out-of-order coverage.

Independent spec and standards reviews caught and resolved read-back transaction
ownership and aggregate-versus-underlying quality-flag handling before any app
write. Original-history/earlier-cutoff checks were strengthened before publication.
Final spec and standards reviews have no remaining actionable findings; see
[review record](../design/d5a/review.md). The actual read-only
`--check --verify-application` matches the saved audit.

`/development/pilot/normalization` is a checked read-only local artifact, linked
from Financial normalization. Existing dated D2–D4 fixtures remain intact and
labelled by their original checkpoint. The page reuses the exact-decimal display
and evidence drawer, uses N/A for unavailable values, and documents dates/flags
in inspectable source details. `/help#real-normalization` and the manual explain
use and terminology. Production build passed. 44 browser checks passed: Company 7, Financials 7,
Fundamentals 6, normalization 7, pipeline 11 and valuation 6. The final changed-page
run passed 24/24. Four widths (320/390/768/1440), signed USD values, exact drawers,
keyboard/focus, before-filing N/A, earliest-available mode, GET-only requests and
corrupted-artifact Retry were checked. Screenshots are in `var/d5a-browser`.
An initial combined-run pipeline navigation timeout passed isolation and final
rerun; no claim is made that the pre-existing intermittent CSR delay was fixed.
Existing Next.js cache-size warnings remain. The existing macOS/iCloud hidden
editable-pointer race also recurred during standalone make; gates use the prior
validated, repository-local editable path inherited through PYTHONPATH.
Complete gate: **1,702 full tests** (two existing upstream warnings), **505 core**,
**110 golden**, **27 Node**, Ruff/policy/generated exports, ESLint, mypy **97 files**
plus the Linux launcher check, and TypeScript pass. Logs:
`var/d5a-full-checks.log` and the mandatory `var/d5a-commit-checks.log`.
Browser logs: `var/d5a-browser.log` (initial mixed run),
`var/d5a-pipeline-recheck.log` (isolated pass), `var/d5a-final-browser.log` (24/24).
All 58 pre-existing refs and the five saved Company/Overview/Fundamentals/
Financials/Valuation artifacts remain unchanged. No hook is bypassed.
[Next-step handoff](../handoffs/d5a-real-normalization.md).

## Stop boundary

D5a stops before real S5/S6 analysis publication. Source/event-history review,
applicability/accounting coverage and downstream prerequisites remain explicit.
No provider activation, quote-currency inference, live prices, scheduler service,
new schema/migration, source refresh, ratios, valuation or sector result.


## Corrective checkpoint — source roles, historical evidence and mapping approval

The coordinator authorized moving the annotated D5a tag from initial implementation
`8ad2fbf659416315bafbcab94d201a65ca62136c` only after these corrections pass all gates.
The original tag object was `ca9159c4b742f855e38696c9ffe142b93f204960`; the original
implementation remains in branch history. No other recovery ref may move.

Observed-fact drawers now identify the selected Company Facts observation, original
10-K precision cross-check and Submissions metadata with distinct transforms.
Amendment/Q2 material is separate non-PIT review context. Before-filing drawers
show only the unavailable selection, with no future literals, scales, contexts,
source links or review material. Mapping replay and standalone verify validate
`approved_by` and `reviewed_scope` alongside all existing mapping identity fields.

The original publication audit/hash, batch, source rows and numeric results are
unchanged. [Corrected provenance audit](../research/crcl-normalization-provenance-2026-09-30.json)
binds the generated presentation to truthful source-chain/context capture groups.
Red-first logs: `var/d5a-provenance-red.log` (3 expected failures),
`var/d5a-remaining-red.log` (5 expected failures). Focused: 40 passing tests in
`var/d5a-correction-focused.log`; read-only application check passes in
`var/d5a-correction-application-check.log`. Both correction reviews are clear.
Corrected production build and all **44 browser checks** pass, including negative
assertions for both before-filing facts at 320/390/768/1440, source-chain membership,
review-context separation, GET-only operation, keyboard/focus and artifact recovery.
Log: `var/d5a-correction-browser.log`; screenshots: `var/d5a-correction-browser`.
The corrected checkpoint is gated by the mandatory hook in
`var/d5a-correction-commit-checks.log`: **1,709 full / 505 core / 110 golden** Python
tests, **28 Node** tests, Ruff/policy/generated artifacts, mypy/TypeScript and ESLint.
The annotated tag moves only after that hook succeeds. The original application
audit and all other prior recovery refs remain unchanged; the tree is left clean.
