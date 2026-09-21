# D031 review corrections: pinned identity acquisition

User authorized implementation of the review requirements on 2026-09-21.
Baseline: `59a8af7`, following genuine D3b captures at migration 0006.
This is the sequential shared-contract correction; no new public API is defined.

## Immutable plan

`BootstrapPlan` version `sec-identity-bootstrap-v1` pins issuer/CIK, source and
policy revision IDs, an inclusive inventory window of at most 730 days, and exact
canonical resource keys. Company Facts and Submissions are required; at most five
explicit filings and ten explicit same-CIK history documents may be added. These
are conservative bootstrap acquisition limits, not limits on fundamentals history.
The product's 3/5/10-year history options remain unchanged.

Resource ordering is canonical ASCII ordering in Python and SQL. New request
hashes include the exact versioned plan, workspace/security and one to three
attempts. Financial periods, history modes, valuation/market options, membership,
parent and quote inputs are not part of this bootstrap interface. W1 stores its
existing neutral defaults for those legacy columns. Ordinary requests are unchanged.

Migration 0007 adds nullable immutable request `bootstrap_plan` JSONB. Existing
0006 rows retain NULL as genuinely unrecorded intent; migration neither infers a
plan from manifests nor rewrites past completion/error history. New bootstrap
inserts require the validated plan. Unknown historical plans cannot dispatch
through the new worker or transport guard. Ordinary rows require NULL.

The worker rejects a different plan or descriptor before network/stage work.
The database attempt guard independently restricts exact resource, source/policy
and registered issuer. Advertised history outside the pinned list produces an
explicit gap without fetching it. Planned but unadvertised history is likewise a
gap, not permission to fetch an untrusted filename. New discoveries need a new
reviewed plan and idempotency key; they cannot silently broaden an existing request.

## Typed completion and readiness

The fenced `workflow_complete_bootstrap_stage` function stores a versioned JSON
result in existing `analysis_stage_attempts.result_reference`, with the plan in
`input_manifest` and a matching audit event. The result contains the archive
manifest reference and readiness: identity capture ID, captured/unavailable status,
`registration_review_ready`, and blocking reasons. The source manifest v2 also
retains this readiness and the exact persisted plan.

Readiness requires the successfully captured and parsed SEC Submissions root.
The database verifies that the selected capture belongs to the planned source,
policy and issuer, and was captured or explicitly reused by this execution.
Missing/malformed Submissions remains unavailable even if Company Facts succeeded.
Incomplete inventory, source failures and unplanned advertised history keep
registration review blocked. Readiness means the acquisition packet is available
for review; it never means quote registration, financial eligibility or approval.

Successful bootstrap stages/executions have NULL error fields. Manifest metadata
and capture-only descriptions no longer occupy `error_code`. New success guards
prevent generic W1 completion from bypassing the typed manifest result or writing
successful error fields. Ordinary completion behavior and old records are preserved.
Retries/cancellation/fencing, SEC transport/archive and Redis limits are reused.

## Application command and migration

The existing `scripts.bootstrap_crcl` register/capture command remains the one-shot
application path. It uses the reviewed policy and issuer/security seed and now pins
its dated 2025-01-01 through 2026-09-21 resource plan before enqueue. Its end date
cannot drift across retries. It does not auto-register quotes or invent listing dates.
Old request keys cannot be reused for new pinned intent. A fresh explicit key is
required for the new bounded capture. A terminal key never dispatches again.

Downgrade refuses once pinned requests exist; empty downgrade restores frozen 0006
functions exactly. Upgrade preserves populated ordinary and legacy bootstrap rows.
Tests use isolated PostgreSQL/Redis fixtures, never application evidence. Application
migration/capture follow full checks and review; the next milestone record follows
those checks rather than claiming completion in advance.
