# D036 / D4b — Application-owned filing scheduling proposal

Status: D036 approved by delegated coordinator on 2026-09-21; implementation authorized.
Prepared 2026-09-21 against `9f7c48f` / `milestone/d4a-filing-monitor`,
migration `0009_monitor_result_identity`.
Approver: task `01a0bbd2-bd4d-77c2-86f6-2a34fef283f1`.

## Decision requested and scope

Approve one additive internal schedule contract, sequential migration 0010,
manual application tick/worker commands and saved UI. Reuse D4a exactly for
acquisition/comparison and W1 exactly for request leases/executions. No public
S6 API, provider activation, OS cron, installed daemon or downstream dispatch.
Spec section 1.4 allows an application jobs table; this slice needs no new
scheduler dependency. A continuously running application service remains a
separate operational configuration after this tracer.

**Choose fixed-scope scheduling plus typed `rebase_required` in D4b.** There is
no automatic rolling window and no rebase writer in this proposal. The existing
CRCL window is 2025-01-01 through 2026-09-21. A slot with a later cutoff is blocked
before enqueue/network. Approval of this proposal does not approve a larger
window, new history resource set or new baseline seed.

## Versioned identity and persisted contract

Internal version `sec-filing-schedule-v1`; exact JSON field allowlists, aware
timestamps canonicalized to UTC, canonical arrays/hashes and SQL/Python parity.
Proposed additive storage:

| Record | Fields and invariant |
| --- | --- |
| `filing_schedules` | UUID; workspace/security/issuer/CIK/source/policy UUID identities; creation time; stable operator creation key and canonical hash. Identity immutable. Unique workspace/security/source/policy scheduling identity prevents duplicate active schedules; create with same key/body returns existing, changed body fails. |
| `filing_schedule_revisions` | UUID, schedule UUID, revision number, predecessor, version, created/effective UTC, actor/reason, owner review reference, config JSON/hash. Append only; unique schedule/revision. Complete config includes active/paused, anchor, cadence, jitter, exact scope/resources, initial eligible D4a baseline, attempt limits, budget and lag threshold. No credentials/contact text. |
| `filing_schedule_state` | One governed mutable row: current revision, revision epoch, last resolved slot index, current unresolved slot, last eligible result and next retry gate. Lock/CAS boundary; reconstruction uses immutable revisions/slots/events and W1 records. Runtime cannot directly write. |
| `filing_schedule_slots` | UUID, schedule/revision, integer slot index, nominal and due UTC, cutoff, exact materialized D4a plan/hash, deterministic key, unique request FK, reserved attempt units, created time. Unique schedule/slot index and unique request. Immutable; an unresolved slot is at most one per schedule. |
| `filing_schedule_events` | Append-only typed lifecycle facts: create/revise/pause/resume, materialized/resolved, retry/deferred/blocked, missed range, tick outcome. Event UUID, schedule/revision/slot, operation key/hash, DB timestamp and allowlisted details. Unique operation/event identity makes repeated identical transitions no-op. Completed slot references exact W1 request/execution and D4a result/manifest; never overwrites them. |

There is no new filing-result shape and no concept enum change. Plan/result
missingness stays D035. Runtime gets SELECT and narrow SECURITY DEFINER functions,
not direct INSERT/UPDATE/DELETE. Owner-reviewed configuration/revision entry points
are separate from ordinary tick privileges. Database guards reject identity/policy
mismatch, invalid baseline, excessive budget, overlapping revision activation,
foreign workspace use, unknown fields and stale revision epochs.

Initial concrete bounds (proposed operational policy, not financial conventions):
cadence integer 300..86400 seconds; jitter integer 0..min(60, cadence/10);
max attempts 1..3 as W1; resources 1..11 as D4a; one unresolved poll per schedule;
lag threshold >= cadence; reserved HTTP-attempt budget 1..10000 per rolling 24h.
Budget must accommodate one poll's worst case. No hidden defaults; every
value appears in the reviewed config. Changing budget/jitter/lag/state makes an
immutable revision, never edits an old config. Scope/policy/resource/baseline
identity changes are rejected with `rebase_required`, not accepted as routine
cadence revisions. A later provider policy requires its own reviewed lineage.

## UTC slots and exact materialization

Anchor is immutable for the schedule lifetime. Slot k >= 0 has nominal time
`anchor + k * cadence`; to keep identity unambiguous, **cadence/anchor changes
are not supported in v1** (a future reviewed replacement schedule is required).
State/budget/jitter/lag revisions apply only to not-yet-materialized slots and
must explicitly pin their first effective slot index greater than the last
materialized/resolved index. Revision intervals never overlap or retroact.
Jitter is deterministic:
first 8 bytes (unsigned big-endian) of SHA256 over version, schedule UUID,
revision UUID and decimal k in a specified newline-delimited encoding, modulo
(jitter_seconds + 1). Due = nominal + jitter. Cutoff = nominal, not tick time.
Zero jitter is valid. SQL and Python use the same encoding and hand-checked cases.
The effective revision determines all slot values; repeats never recompute
against a later config.

A tick uses database UTC time for eligibility, never an operator backdated clock.
It locks state, reconciles any terminal W1 result, then processes at most one
eligible latest slot. Enqueue and slot insertion happen in **one transaction**
with the existing `workflow_enqueue_monitor`. Slot plan contains the fixed
issuer/source/policy/forms/window/resources and the last eligible exact D4a
prior-result lineage (or the explicitly reviewed initial baseline). Baseline
cutoff <= slot cutoff <= DB creation time. Stable request key:
`sec-schedule-v1:<schedule UUID>:<slot index>`. A stored key reused with a
different plan fails. Plan is persisted once; retries never select a new
baseline, cutoff, resources or revision.

Concurrency serializes on schedule state and W1's existing workspace enqueue
lock; all governed paths use lock order workspace -> schedule state -> W1 request
state/execution -> stage/attempt, taking earlier locks before existing W1 helpers.
Tests must force opposing tick/claim/pause/retry interleavings to reject deadlocks. Workers claim
only the slot request through `workflow_claim_monitor` and W1 fence/lease epoch.
Ordinary/bootstrap claimers remain excluded. Tick/materialization needs no
second long-lived lease: its atomic transaction is the fence; actual provider
work is outside the transaction and uses W1. A stale tick revision fails CAS.
Concurrent/repeated ticks yield one slot/request; concurrent workers yield one
current lease. Returning an existing terminal slot never opens the network.

## Missed slots, retry and operator lifecycle

No invented historical checks. With no unresolved request, a late tick selects
the most recent nominal slot whose jittered due <= DB now and persists one
`missed_range` event for older never-materialized indexes, with count and
reason. It does not enqueue a burst. Those intervals remain visibly unchecked;
a current source fetch cannot prove historical availability. An unresolved slot
blocks later materialization; after it resolves, recovery uses the same latest
slot rule. Forward clock jumps use missed-range recovery; backward jumps never
decrease a slot cursor or authorize early execution.

Terminal complete eligible D4a outcomes advance the schedule baseline by a
governed reconciliation transaction verifying exact request/execution/manifest.
Terminal incomplete/error never advances it. D4a's prior success remains visible
with the newer failure. Terminal logical polls are never reopened. Subsequent
slots may use the last eligible baseline within the identical fixed scope;
structural scope/history failures set `rebase_required` rather than auto-expand.

Transient W1 execution failure/expired lease uses existing retry executions on
the same immutable request, max 3, delay min(3600, 60 * 2^(attempt_no-1)).
Provider Retry-After/shared cooldown is never shortened; next eligibility is the
later applicable gate. A terminal incomplete/error poll introduces an observable
schedule backoff min(3600, cadence * 2^(consecutive unsuccessful polls-1)),
bounded arithmetically before exponentiation. Backoff resets only after eligible
complete discovery. Unreviewable policy/Retry-After requires operator attention.
No sleeping while holding DB locks; a tick returns its deferred reason/time.

Create accepts a reviewed exact config and starts paused unless that config
explicitly says active. Pause/resume uses a stable operation key and expected
revision; identical repeat returns the saved transition, different content under
the same key fails. Pausing prevents materialization and new scheduled claims/
dispatches. An HTTP request already dispatched may finish, archive and finalize;
pause cannot unsend it. Queued work remains pinned for resume; lease recovery
does not mutate its plan. Resume is a new revision, not a fresh immediate poll;
it honors backoff, budget, scope expiry and the next/latest due slot. Invalid or
expired scope stays blocked even if configured active. Global W1 claim and source
attempt boundaries must enforce pause for scheduled requests, so using the old
direct monitor CLI cannot bypass schedule controls. Result finalization remains
allowed for already received evidence.

Manual `tick` materializes/reconciles at most one slot and returns its state.
Separate explicit `run-slot` executes that slot through D4a; `tick --run` may
compose both sequentially. `inspect` is read-only. No force/ignore-budget,
future-slot or browser-triggered provider action. Repeating early/paused/no-due/
blocked tick creates no request or HTTP attempt and deduplicates unchanged
lifecycle evidence; a unique operator invocation can still have an audit entry.

## Budget, SEC policy and crash recovery

Use existing reviewed SEC contact/policy, `SecTransport`, raw archive and the
same Redis limiter key across all SEC hosts/workers (configured rate <=10/s,
existing hard 10/s window). Never create a per-schedule rate limiter. Missing
contact, invalid policy or unavailable coordination fails closed.

Bounded schedule budget is conservative **HTTP-attempt reservation units**.
Each slot reserves 3 * resource_count * W1_max_attempts units (transport supports
at most three sequences per resource). Capacity includes all nonterminal slots
and terminal slots completed within the preceding 24 hours, across all revisions
of the same schedule. No refund for unused/cancelled/unknown attempts until that
retention elapses. Paused/changed revisions cannot reset spend. Lowering a budget
below existing reservations defers new work, not deletes history. The admission
transaction checks/reserves under the schedule lock. A governed source-attempt
guard rejects attempts beyond the slot total; replay without network has no
new attempt charge. Budget never bypasses the shared SEC limiter. UI reports
reserved versus actual attempts separately; this is a conservative scheduling
allowance, not a claim about provider billing.

Crash before enqueue commit: neither slot nor request exists. Crash after commit:
the same slot/request is found and claimed. Crash after capture: existing D4a
replay avoids re-fetching completed resource evidence. Crash after result:
reconcile its verified saved manifest and W1 state without network. Stale leases
cannot capture/finalize. Unknown network outcome remains `interrupted_unknown`;
a retry can cause another real HTTP call when the earlier response was lost.
We guarantee no duplicate logical polls and no extra HTTP from healthy repeated/
concurrent ticks; **exactly-once remote HTTP across crashes is not promised**.
Such retries count against the reservation and preserve every attempt.

## Explicit rebase gate

Versioned blocked event `sec-filing-schedule-block-v1` contains reason
`rebase_required`, schedule/revision, proposed slot/cutoff, prior request/
execution/manifest hash, old scope hash, triggering mismatch (expired window,
changed required resources/forms/policy/version or structural coverage failure),
detected time and `requires_owner_review=true`. It does not contain an approved
replacement scope, invent a new baseline or report no_change. The last valid
manifest/captures remain immutable and accessible.

Extending the window or moving to another SEC policy needs a separate proposal
with an exact new scope, retained previous lineage, full baseline/current
coverage and typed rebase acceptance. No D4b command creates that approval.
An expired schedule cannot poll stale cutoffs indefinitely to appear healthy.
If actual dispatch/recovery occurs after the pinned window's final UTC day,
block new dispatch even when an old due slot cutoff is inside that window;
evidence already received may still finalize and is labelled late.

## Saved UI, health and operational truth

Keep the existing dark/mint pipeline components and D4a evidence disclosure.
A separate saved schedule panel shows config version/active-or-paused state,
fixed window, cadence/jitter/budget, next nominal/due time, last tick time,
last HTTP completion, last eligible success and cutoff, lag/unchecked intervals,
current request/result, retries/backoff, coverage/rebase flags and all blockers.
Health is an orthogonal projection, not a rewritten D4a outcome:
`not_configured`, `paused`, `ready`, `waiting`, `lagging`,
`degraded`, `rebase_required` with explicit reason list. Null last success
means never succeeded. Lag seconds = max(0, snapshot_as_of - earliest outstanding
due); no due item means zero, with missed intervals reported separately.
Keep slot lag distinct from source freshness and time since eligible success.

Snapshot includes audit hash, generated-at UTC and counts. Values are computed
in Python/SQL and rendered in TS; no financial math in frontend. Label
"Saved manual scheduler check; background service not configured." Active
configuration is not proof of an active worker. This tracer records manual
invocations only; it does not invent a heartbeat or display live-service status.
A future service needs explicit runtime registration/heartbeat and stale-health
acceptance before that label can change.

## Narrow real tracer after approval

1. Apply 0010 only after isolated migration/tests. Preserve D4a audit/hash and
   row-hash inventory; do not regenerate old artifacts with new timestamps.
2. Create exactly one reviewed CRCL schedule, initial D4a prior-result baseline,
   exact approved source/policy/forms/resources/window, hourly cadence,
   zero jitter, lag_threshold_seconds=3600, max_attempts=1,
   budget=3 (one root resource), active. Anchor = the next
   whole UTC minute after configuration creation; include exact anchor/config
   hash in the acceptance artifact before execution. This is one bounded
   manual slot, not authorization to run indefinitely.
3. If the slot is due and can execute before 2026-09-22T00:00:00Z, execute one
   bounded real check with current CRCL policy/contact and shared limiter.
   Repeated and concurrent terminal ticks/run attempts must add zero HTTP.
   Real outcome may differ from D4a; do not manufacture no_change.
4. Pause the schedule after the one slot, preserve the transition and saved
   health/result. Report that no service is configured.
5. If approval/testing misses the window, persist/review `rebase_required`;
   do not backdate anchor, silently extend scope or make a live call. Finish
   isolated fake-clock/provider tests and saved honest blocked UI. A real
   successful tracer then remains explicitly incomplete pending rebase review.

## Acceptance and migration boundaries

See [test plan](filing-scheduler-test-plan.md). Upgrade populated 0009 preserves
all old row hashes and D4a manifest bytes. New 0010 adds tables/functions/guards;
do not edit 0008/0009 or existing result JSON. Down migration refuses with any
schedule/revision/slot/event history; empty downgrade removes only new objects
and restores exact prior entry points/privileges. Runtime direct mutations and
generic claim/completion bypass tests required.

Full/core/golden/lint/typecheck/build and browser acceptance before final
commit/tag. Documentation-only proposal gets link/whitespace validation now;
no schema, migration, application DB or live SEC change before approval.

Still non-operating: unattended recurring service/health alerts, window rebasing,
quote provider/registration, prices/actions, financial normalization/publication,
automatic financial refresh, production watchlist full analysis, real sectors,
stock-specific news/CPI/PPI/Fed discovery and notifications in all channels.
D4b neither sends messages/alerts nor installs any external scheduler.

## Approved acceptance refinements

Coordinator approval requires monotonic latest eligible baseline advancement; full
scheduler scope equality including resources/forms/policy/version; final dispatch
revalidation of pause and budget; semantic event deduplication; resolution of failed
slots without baseline advancement; and literal saved/manual service status. These
refinements are mandatory and tested. The approval does not extend the filed window.
