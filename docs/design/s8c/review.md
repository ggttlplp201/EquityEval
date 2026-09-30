# S8c independent review

Fixed baseline: `30c35c61b9f42602381acbf5c0ae2423ecc2b762`.
Review used the working diff plus all untracked S8c files before commit. No
implementation commits existed at first review. Spec source is the pinned local
acceptance; the repository has no configured issue-tracker skill document.

## Spec axis

Reviewer: `s8a_spec_review` (reused independent reviewer).
P2: raw string equality treated precision-only source changes as restatements.
Fixed with validated Decimal equality for status classification only; exact
financial source strings and their evidence identities remain unchanged. Red-first
regressions cover 40 versus 40.0 and 0 versus -0.00. No remaining specification
findings after rereview, including scoped failure states and manual.

## Standards axis

Reviewer: `s8a_standards_review` (reused independent reviewer).
The same P2 restatement issue and an undefined CSS border token were reported.
Both repaired; the table uses shared --line. No additional actionable smells or
remaining standards findings after rereview. Shared schema/API/core untouched.
React review: one server-side fixture read, only selected snapshot serialization,
direct imports, event-driven navigation and drawer state, labelled controls,
semantic tables, focus return and no frontend financial math.

## Verification repairs

ESLint caught an unused destructuring binding, removed before final build.
Visual inspection found the global table minimum width clipped columns on mobile;
Financials now uses locally scoped fixed responsive columns and wrapping labels.
The test verifies all table columns fit and resets scroll/focus before screenshots.
An initial loading test waited for a navigation it deliberately held, so its
locator could not inspect pending state. A second attempt using a frame read
also waited on navigation and was stopped. The test now observes actual pending
DOM status and disabled controls before holding the request, retaining both
assertions and a bounded failure timeout. No app timeout/assertion was weakened.

Final browser and full commit-gate evidence is recorded in the milestone. Review
completion alone does not mark those gates passed.

The real missing-fixture test subsequently exposed an application recovery bug:
React boundary reset alone did not reread the server-side source file. Retry now
performs a fresh local GET reload. The same exact snapshot recovery assertion is
retained. The browser error selector is scoped to the Financials main element,
so Next's separate route-announcer alert cannot satisfy it.
