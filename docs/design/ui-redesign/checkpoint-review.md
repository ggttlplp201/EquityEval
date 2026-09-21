# D1 redesign recovery checkpoint — 2026-09-20

Reviewed working-tree changes against `a9cb080` on `codex/sector-explorer`.
Scope: D1 handover/reconciliation, R1 design and pilot research already prepared,
D1a Sector redesign and D1b Company/News/Help development views. No pilot ingestion
or real-data UI is included in this checkpoint. Local `.impeccable/live` state is
preserved on disk and ignored, not erased or committed.

## Standards review

Independent review found no blocking standards, source-identity, date, missingness
or financial-boundary defects. The internal Company projection still selects
summary amounts by display heading. This is an optional robustness concern for
future expansion: use stable internal IDs and explicit unavailable placeholders
before extending it to a different source projection. The frozen fixture is
consistent, and this does not require a public-schema change.

## Spec review

Independent review found no bounded-scope omissions or wrong implementations.
All 143 preservation-checklist IDs remain unique and present. Four Sector graphs,
coverage/source semantics and exact Company snapshot links are retained. Longer
company history windows expose gaps. News services remain unconfigured. Release
manual, watchlist and R1 work is explicitly pending. Changed/new files were
inspected; no unexpected credential/private-key or binary artifacts were found.

## Checkpoint validation

Rerun on 2026-09-20 before the commit: repository lint, policy/vocabulary checks,
Python/TypeScript type checks, **963 full tests**, **225 core tests**, and **110
golden tests** passed. The optimized Next.js build passed. Eight production
browser route cases passed with no console/page errors; prior detailed D1b
interactive, responsive and print evidence remains applicable to this unchanged
UI. The normal pre-commit hook repeats the required checks against the staged tree.

Recoverable reference: `milestone/d1b-redesign`. See its annotated commit and
`docs/milestones/D1b-company-news-help.md`. Local verification logs and the original
tracked patch/untracked backup are under `var/d1b-checkpoint-*` and
`var/checkpoints/d1-redesign-2026-09-20`; they are not application data or deployment.
