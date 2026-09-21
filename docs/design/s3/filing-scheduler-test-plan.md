# D036 / D4b — Scheduler acceptance matrix

Status: approved acceptance matrix; implementation and bounded real acceptance
recorded in [D4b](../../milestones/D4b-filing-scheduler.md). Rows describe required
invariants, not a claim that every permutation is a separate test. No live service configured.
Contract: [proposal](filing-scheduler-proposal.md).
Baseline: 0009 / milestone/d4a-filing-monitor.

| Area | Adversarial cases | Required observation |
| --- | --- | --- |
| Configuration | Unknown fields/version, invalid identities/policy, contact unavailable, UTC-naive times, bool-as-int, cadence/jitter/budget bounds, conflicting creation key | Reject before provider access; exact creation repeat reuses identity; no credentials exported |
| Revision | Stale epoch, duplicate operation key, altered repeat body, retroactive effective slot, overlapping revisions, scope/policy/resource/anchor/cadence edits | CAS/idempotency enforced; immutable prior revisions; forbidden scope change gives reviewed rebase gate |
| Clock/math | Exact due boundary, before/after, deterministic jitter endpoints, cross-midnight, leap day, DST offset inputs, backward/large forward DB clock, overflow | Hand-computed UTC cases agree SQL/Python; no future cutoff; deterministic key/plan |
| Materialization | Concurrent ticks on separate DB connections, rollback before commit, crash after slot+enqueue, repeated terminal tick | One atomic slot/request, never orphaned request/slot; zero extra HTTP from repeat |
| Baseline | Foreign/ineligible/missing/corrupt manifest, wrong result identity/hash, same cutoff, previous incomplete/error followed by success | Exact eligible predecessor only; incomplete/error never advances baseline; saved successful history retained |
| Worker fencing | Concurrent claims, expired owner, retry race, crash after capture/result before completion, direct old CLI bypass | W1 ownership preserved; terminal result replay no HTTP; source/stage guards prevent bypass |
| HTTP truth | Healthy concurrent execution, identical 200, valid 304, failed/unknown transport, response lost before archival | Healthy one poll only; body/time/status retained; unknown remains unknown; bounded retry may make another actual HTTP request |
| Budget | Parallel admissions, limit exact/exceeded, prepared/cancelled/unknown attempts, redirects, replay, configuration lowered/raised, pause/resume, 24h boundary, unresolved long-running slot | Worst-case reservation atomic and never refunded early; all revisions share spend; actual attempts cannot exceed reserved bound; replay does not fabricate HTTP |
| Shared limiter | Competing ordinary/monitor workers, Redis failure/state loss, mismatched rate config, HTTP429/503 Retry-After and unrepresentable delay | Existing global cap/contact/policy enforced; fail closed; no per-schedule bypass or shortened cooldown |
| Backoff | Retry exhaustion, saturated exponent, repeated failure, subsequent eligible complete result | Bounded visible gates; same request intent through execution retry; terminal poll immutable; baseline/error history honest |
| Pause/resume | Before materialize/claim/dispatch, during live response, queued poll, active lease expires, simultaneous pause/tick | No new post-pause dispatch; already-dispatched evidence can finish; resume honors exact pending plan, budget/backoff/expiry |
| Missed runs | Long downtime, unresolved predecessor, paused interval, near due with jitter | One latest eligible poll; durable skipped range/count; no fabricated historical checks or catch-up burst |
| Rebase gate | Cutoff next UTC day, dispatch/recovery after window, newly required history, policy/form/version changes, incomplete baseline/current | No silent window/resource change, no false no_change, typed reason plus old manifest lineage; no new HTTP for expired scope |
| Migration | Populated 0009 upgrade/hash replay, empty downgrade/re-upgrade, nonempty downgrade, privilege/entry-point bypass | Old rows/manifests unchanged; sequential 0010 only; populated downgrade refused before destructive DDL |
| Negative boundaries | Diff application counts and direct monitor scheduled path guards | No quotes, memberships, normalization, financial requests/results, publication, notifications or N1 rows/tasks |

## Saved UI/browser acceptance

Exercise active/paused/no-success, waiting/running/degraded/lagging/rebase_required
through deterministic scheduler/health tests; browser acceptance uses the actual
saved paused tracer. A full visual variant gallery remains future UI work.
Inspect config, last-success/last-attempt distinction, null states, UTC times,
missed coverage, current outcome and baseline provenance. A saved timestamp
must not be advertised as live. A configured-active schedule is still labelled
background service not configured.

Verify native keyboard disclosures/focus, safe source links, no clipping at
320/390/768/1440, current pipeline sections and navigation, Company 3/5/10Y,
no browser mutation/provider fetch and no new console errors. Record desktop
and narrow screenshots and request audit. Use existing exporter/hash verifier
and Python-calculated health, not parallel TypeScript scheduling logic.

## Bounded real acceptance

After approval only: validate exact config, pre-change row hashes and D4a artifact
SHA. One CRCL root-resource due slot within its valid UTC window; current
policy/contact/shared limiter. Inspect actual request/result/capture/attempt counts
and repeat same tick/slot concurrently without new requests or HTTP. Pause
afterward. Save independently verifiable scheduler audit and UI projection;
preserve original D4a JSON. If the window expires, record rebase_required without
a live call and mark real success acceptance pending; do not weaken the test.

Run focused tests, full/core/golden/lint/typecheck, optimized build, browser
acceptance and application read-only verification before commit/tag. Tests use
isolated stores and fake clocks/providers; live SEC calls are never test fixtures.
