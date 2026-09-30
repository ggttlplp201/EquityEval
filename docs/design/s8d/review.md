# S8d two-axis review

Fixed baseline: ee50c317874dbcc1464d5fdc2fb971411dd31b56.
Review command: `git diff ee50c31` plus the new files listed by `git status --short`;
pre-commit working-tree review, no S8d commits existed at review time.
Sources: root and apps/web AGENTS, docs/spec.txt, pinned S8d acceptance.
The repository has no docs/agents/issue-tracker.md; this local pinned acceptance
is the spec source, as in earlier S8 milestones.

Independent reviewers: s8a_spec_review and s8a_standards_review; they reviewed
separately while browser validation continued.

## Spec

Initial findings: P2 shifted missing-context paragraphs; P2 unavailable history
dates opened the current snapshot rather than each date's own evidence; P3
rounded source amounts described as exact. Fixed all three. Added actual rendered
component assertions for each financial section and computing-12's March/June
unavailable P/E evidence, plus browser section assertions. Narrow rereview:
all three resolved, no remaining findings; final gates pending at review time.

## Standards

Initial P2: missing-context paragraphs attached to unrelated metrics. Corrected
original section semantics; generic fallback N/A. Section-scoped tests guard
against recurrence. Narrow rereview: resolved, no new standards issues; reviewer
did not rerun tests. No additional actionable architectural smells.

Early coordinator review also caught dropped $ and × markers from generic
rounding. A local unit-aware formatter now reuses S8a exact decimal rounding;
red-first unit tests preserve %, ×, $, null/N/A and full raw evidence precision.

## Browser recovery correction

The final browser flow reproduced a retained not-found boundary: a Next Link
changed the malformed-query URL to the default but left N/A visible. An isolated
Chromium reproduction confirmed it. The recovery control now uses a native GET
form to the same local default route; the browser assertion still activates the
actual user control and waits for the exact saved view. It is not replaced by
programmatic navigation. The full S8d browser run subsequently passes all seven
checks. Error Retry similarly rereads the restored manifest via a fresh GET.

## Coordinator final review — missing sentinel correction

The coordinator's separate two-axis audit of 8f04518 found a High compatibility
bug: equal literal N/A fields could count as affirmative proof. The bounded
corrective change rejects N/A (case/whitespace variants), blank strings, empty
containers and unsupported scalar leaves recursively, including tuple scopes.
It does not mutate metadata or loosen exact comparison of legitimate strings.
Red-first evidence: `var/s8d-sentinel-red.log` (14 failures, 19 passes before fix).
The corrected 33 metadata tests plus 13 existing Company tests pass (46 total).
The generated metadata manifest is byte-identical. Both independent local
reviewers rereviewed the correction with no remaining findings; neither reran
tests. Final corrected gate and tag are recorded in the milestone after passing.

The coordinator also requested final commit/count/clean-tree traceability, which
is completed after the corrected implementation gate. The initial 8f04518
checkpoint is preserved; it will not receive the milestone tag.

## Corrected checkpoint

Corrected commit `bdc3a977128be19c371269d5f32405e7a997b8fd` passed its mandatory hook: 1,669 full,
505 core, 110 golden, 26 Node, lint/types/exports. All 26 browser checks pass on
the corrected build. The annotated milestone/s8d-company-overview tag points to
this corrected implementation; the initial commit and 39 earlier refs remain
unchanged. Final documentation records exact evidence and stopping scope.
