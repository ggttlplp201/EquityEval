# D3c — Pinned bootstrap intent and acquisition readiness

Status: implementation checks passed; review findings resolved; final correction checks and application verification pending.
Date: 2026-09-21. Branch: `codex/source-bootstrap`.
Baseline: `59a8af7` / `milestone/d3b-crcl-capture`.
Implementation: `c2b02cf`.

## Authorized scope and diff

User explicitly requested the D031 review corrections before completion. The
[contract](../design/s3/bootstrap-intent.md) records bounded plan limits, immutable
resource/policy/window hashing, runtime and database enforcement, readiness, and
legacy behavior. Nine files changed (964 additions, 105 deletions) at implementation.

- `BootstrapPlan` replaces financial request options for acquisition.
- Migration 0007 adds immutable plan storage and typed fenced completion;
  ordinary requests and already-applied 0006 history retain their semantics.
- SEC pipeline stores identity selection/status, registration review readiness
  and blockers. Missing or malformed Submissions never claims readiness.
- Successful metadata uses result_reference/input_manifest; new successful
  bootstrap stage/execution error fields must be NULL.
- Existing one-shot CRCL command pins the dated plan before enqueue; owner
  registration stays idempotent and creates no quote or listing-date assumption.

## Validation

Created this milestone after the mandatory implementation checks passed:
1,060 full tests, 225 core, 110 golden, lint and Python/TypeScript types.
Expanded bootstrap/migration/plan selection: 74 passing targeted tests after corrections.
Coverage includes exact resource and policy boundaries, changed-plan idempotency,
unplanned history, absent/invalid Submissions, success/error semantics, typed-result
fencing, downgrade refusal, empty upgrade, populated ordinary and legacy 0006
upgrade, concurrent requests and cancellation/expiry/retry behavior.

[Independent review](../design/s3/bootstrap-intent-review.md) found one Standards
and two Spec findings. Both axes rechecked the corrections and report zero
remaining findings. Filename validators now match transport exactly, and terminal
idempotent CLI calls return the same persisted readiness without new dispatch.

## Application state before migration

Read-only verification: owned application PostgreSQL on 5433 is at 0006, separate
Redis on 6380 is healthy, and real configured SEC contact and reviewed policy exist.
There are 1 source/policy/issuer/security, 7 captures and 2 historical requests.
A local row-hash baseline covers those identities, captures and workflow history.
The earlier report of empty 0005 application state predates the completed D3b work.
No fixtures were imported and no credentials were printed.

Apply only reviewed migration 0007 after review, compare the legacy row baseline,
and run one bounded capture under a fresh explicit key. Record actual selected
Submissions capture, readiness, completion fields and archive/policy links here.

## Remaining registration boundary

Acquisition readiness means ready for identity registration review, not a
registered quote or financial result. The [D3b evidence review](../research/crcl-first-application-capture-2026-09-21.md)
contains a genuine listing-start statement; it is not automatically inserted.
Quote currency/validity and financial event/statement coverage require explicit
review before ordinary request publication/PIT → eligible S5 → minimal reviewed S6.
No quotes, watchlist memberships or financial normalization batches are created
by the bootstrap command. DCF, prices, monitoring and deployment remain out of scope.
