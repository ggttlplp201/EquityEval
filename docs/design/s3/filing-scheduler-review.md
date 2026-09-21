# D4b final review

Fixed baseline: 9f7c48f4c2f5d5ed260c35c654d2538dee7a228a (D4a).
Scope: staged D036 implementation, sequential 0010, operator/snapshot helpers,
UI, tests and evidence. Two independent read-only review agents examined the
changes against the approved proposal and root/layer AGENTS/spec standards.

## Standards

No documented hard violations or material code-smell findings. Evidence remains
immutable, privilege boundaries narrow, missingness explicit, SEC transport reused,
and frontend rendering-only. Test clocks/providers are isolated from real audits.

## Specification

One P2 found and fixed before commit: a pre-dispatch cancellation had a finished_at
but no requested_at, so it incorrectly advanced Last HTTP completion. The projection
now requires dispatched, finalized evidence and excludes interrupted_unknown recovery
outcomes. Two real-DB regressions reproduce cancellation with and without an earlier
successful scheduled check; they failed before the fix and pass afterward. Cancelled
attempts remain visible and do not increment the actual dispatch count.

No other actionable spec mismatches or scope creep found. The six approved
refinements, fixed scope and literal absent-service status are implemented. No
applied migration or real acceptance evidence changed for the correction.

Totals: Standards 0; Specification 1 corrected, 0 outstanding. The review concerns
the bounded manual scheduler; it does not accept unattended service/rebase or any
financial publication/N1 capability.
