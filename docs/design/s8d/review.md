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
