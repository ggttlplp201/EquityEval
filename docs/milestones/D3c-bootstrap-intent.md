# D3c — Pinned bootstrap intent and acquisition readiness

Status: reviewed implementation and bounded live application capture verified; registration review remains pending.
Date: 2026-09-21. Branch: `codex/source-bootstrap`.
Baseline: `59a8af7` / `milestone/d3b-crcl-capture`.
Implementation: `c2b02cf`; reviewed corrections `bba701a`.
Recovery: `milestone/d3c-bootstrap-intent`; verified capture: `milestone/d3c-pinned-capture`.

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
1,060 full tests initially. After review corrections, the mandatory hook passed
1,065 full tests, 225 core, 110 golden, lint and Python/TypeScript types.
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

Application migration 0007 succeeded after the reviewed recovery checkpoint.
Every preexisting identity/policy/capture/request/execution/stage/event row matches
the saved hash baseline (new request column is NULL for legacy rows). The idempotent
owner seed reused its existing records. One bounded live request then captured
five HTTP200 responses under the exact plan, with no acquisition gaps.

[Application audit](../research/crcl-pinned-bootstrap-2026-09-21.json):
request `19340d60-6544-4ac5-8d69-241f166e28a1`, execution
`d5e8458f-da16-4b83-a371-1572e8e625a7`. Selected identity capture:
`0e93340d-a10c-40eb-b463-047c23be58bf` (SEC Submissions, status captured).
`registration_review_ready=true`, blocking reasons empty. Every new completed
stage and execution has NULL error_code/error_detail. The typed result_reference,
input manifest and archived source manifest agree with the immutable request plan.
Hashes/counts, actual timestamps, source-policy and attempt links were verified.

Repeating `crcl-pinned-bootstrap-20260921` returned identical saved readiness,
manifest and execution with `dispatched=false`. Counts remained 12 captures /
12 attempts / 3 requests. There is still 1 source/policy/issuer/security and zero
quote identifiers, watchlist memberships or normalization batches. The test
fixtures remain in their separate PostgreSQL/Redis runtimes.

Inspect the saved result without another SEC dispatch:

```sh
.venv/bin/python scripts/project_python.py -m scripts.bootstrap_crcl capture --key crcl-pinned-bootstrap-20260921
```

No external configuration is missing for this bounded acquisition. Remaining
registration blockers are substantive review of quote currency/validity and an
explicit quote registration decision; capture readiness grants neither. Financial
event/statement coverage, publication and PIT/core eligibility remain separate.

## Remaining registration boundary

Acquisition readiness means ready for identity registration review, not a
registered quote or financial result. The [D3b evidence review](../research/crcl-first-application-capture-2026-09-21.md)
contains a genuine listing-start statement; it is not automatically inserted.
Quote currency/validity and financial event/statement coverage require explicit
review before ordinary request publication/PIT → eligible S5 → minimal reviewed S6.
No quotes, watchlist memberships or financial normalization batches are created
by the bootstrap command. DCF, prices, monitoring and deployment remain out of scope.
