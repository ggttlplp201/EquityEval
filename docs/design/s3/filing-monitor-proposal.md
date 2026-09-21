# D035 / D4a — Incremental SEC filing monitor contract and review

Status: D035 approved by delegated coordinator on 2026-09-21, with the mandatory refinements below; implementation authorized.
Baseline: `b4c1e19`, migration `0007_bootstrap_intent`.
Delegated approver: coordinator task `01a0bbd2-bd4d-77c2-86f6-2a34fef283f1`,
explicitly authorized to audit/approve checkpoints while the user is AFK.

## Why a narrow shared change is needed

The existing quote-free `source_bootstrap` plan requires Company Facts plus
Submissions and supports an identity-readiness result. Reusing it as a monitor
would misstate intent and fetch unnecessary resources. Ordinary requests require
a quote. S3's unchanged response currently means HTTP 304 only; a byte-identical
HTTP 200 currently creates another capture. A monitor needs an explicit discovery
intent/result and honest unchanged-body attempt evidence.

## Approved request boundary

Migration 0008 adds nullable immutable `analysis_requests.filing_monitor_plan` JSONB and a
`sec_filing_monitor` trigger. Other triggers require the new column NULL. Monitor
requests require quote/membership/parent/market/financial options absent, using
neutral legacy defaults as bootstrap does. Existing rows are not rewritten.

Version `sec-filing-monitor-v1` pins:
- issuer UUID, canonical positive CIK, source UUID and reviewed policy revision UUID;
- inclusive filed-date inventory start/end (bounded to 730 days for this tracer);
- an explicit UTC acceptance cutoff, no later than request creation;
- exact supported forms (subset of 10-Q, 10-K, 10-Q/A, 10-K/A; nonempty, unique);
- exact root plus at most ten same-CIK history resource keys; only advertised
  history may be used. Missing newly advertised history is incomplete, never an
  implicit broadening of this request;
- a tagged baseline lineage: an owner-reviewed initial D3c seed approval with
  exact request/execution/plan hash/manifest hash/capture, or an exact terminal
  eligible prior monitor request/execution/manifest ID/hash/version. The initial
  cutoff is no later than the seed HTTP request start. Later captures/cutoff
  come from the pinned complete result. Arbitrary capture lists are not accepted.
  The baseline cutoff must not exceed the current cutoff.

The filed window is explicit and identical for baseline/current comparison.
Acceptance cutoff filters verified timezone-bearing acceptance timestamps
inclusively. Missing/naive/invalid acceptance metadata in an in-scope filing
prevents a complete result rather than inventing a timezone. These are source
metadata cutoffs, not a claim that a subsequently fetched source was publicly
known at that historical instant. Capture timestamps remain separate.

A narrow enqueue function reuses W1 idempotency keys, immutable request hashes,
executions, events, retries and lease fencing. Canonical ordering is part of the
hash. Reusing a key with changed intent fails. A terminal key returns the saved
result without fetch/dispatch. An explicit new poll has its own key and auditable
attempt even when its result is unchanged. Concurrent claims are single-owner.
Ordinary and bootstrap claim paths must exclude monitor requests.

## Acquisition and byte identity

Reuse approved SEC source policy/contact, Redis budget, `SecTransport`, archive,
Submissions parsing and inventory assembly. No new provider or licence is added.
Monitor resources are enforced at the database attempt boundary as bootstrap
resources are today. Live attempts require the same current stage/lease fence.

The additional S3 attempt outcome `content_unchanged` for a successful
HTTP 200 response whose fully archived body hash AND byte count equal a verified
same-source/resource/policy capture. Preserve the actual HTTP 200 headers, request
and completion times and the reused capture reference. Never relabel it HTTP 304
or replace the old capture's retrieval timestamp. The database finalizer validates
same source/resource/params/policy and records the observed body hash/length.
The response body must be verified before reuse; an unverified cache is not enough.
This behavior is enabled for the monitor path only, preserving other transport
semantics. HTTP 304 retains its existing conditional-validator rules.

A changed raw body can create a new immutable capture even when no in-scope filing
changed (e.g. another form was added): that is distinct new evidence, not a
duplicate capture. Identical HTTP 200/304 bodies reuse prior captures. Retries reuse
already completed evidence for the same pinned execution intent where safe;
interrupted network attempts remain honestly recorded and never fabricated as success.

## Comparison and immutable completion

Compare accession-keyed exact tuples: form, filing date, report date, primary
document and raw acceptance metadata/time basis. Preserve source locators and
capture IDs. Source row ordering is not identity. Do not rely on max filed date:
late arrivals/backdated filings remain detectable within the pinned window.

Outcomes are distinct: `no_change`, `new_filing`, `amendment`, `mixed_changes`,
`incomplete`, `error`. Amendments are separate accessions/editions; `/A` alone
establishes neither restatement nor non-reliance. Conflicting/duplicate accessions,
metadata mutation for an existing accession, disappearing baseline filings,
missing advertised history, malformed metadata and missing cutoff evidence are
explicit incomplete/error results. No incomplete/error run advances an eligible
baseline. Do not erase previously observed filings to manufacture no-change.

Persist a versioned archived run manifest and typed fenced stage result in the
existing `analysis_stage_attempts.result_reference`, alongside the immutable
input plan. Result records baseline/current captures, cutoff, checks, differences,
outcome/flags, manifest reference and downstream disposition. SQL guards verify
capture ownership/policy and execution capture/reuse provenance before completion.
A successful execution requires the typed monitor result; generic stage completion
cannot bypass it. Old requests/captures/manifests/results remain unchanged.

D4a downstream disposition is always **not dispatched**, with explicit
`handoff_not_implemented` and actual quote/coverage blockers. It creates no
ordinary request, membership, normalization batch or financial publication.
A future handoff needs explicit review/deduplication acceptance; discovery is not
analysis readiness. Terminal error attempts/results remain auditable; crash/lease
expiry follows existing W1 retry/fencing rather than overwriting history.

## Migration, operator and UI

Additive migration 0008 for request shape, governed enqueue/claim/result
functions and the narrow unchanged-body evidence extension. Runtime has no direct
writes. Preserve populated 0007 history. Downgrade refuses once monitor/new attempt
history exists; empty downgrade restores previous contracts. No concept enum or
public S6 API changes.

CLI/worker accepts explicit plan and idempotency key; supports inspect/replay and
one bounded poll using current application settings. No OS scheduler, credential
acquisition, provider activation or automatic background loop. CLI diagnostics and
checked-in audit exports omit contacts, credentials and local raw paths.

The existing pipeline saved snapshot will gain a separately labelled monitor
section: readiness, checked time, acceptance cutoff/filed window, exact baseline,
change list/outcome and downstream blockers. Counts distinguish acquisition
bootstraps from monitor requests. Historical D3c–f artifacts remain pinned; the
new snapshot must compare their original rows rather than demand that cumulative
counts never increase after an authorized monitor run.

## Required acceptance

Unit and isolated database tests: exact cutoff equality; before/after cutoff;
naive/missing/malformed acceptance; out-of-order/backdated additions; amendments;
duplicate/conflicting/disappearing accessions; missing history and unplanned
resources; identical 200/304 bodies; unchanged financial scope with changed raw
body; idempotent terminal retry/concurrent claim; crash before/after capture and
result; stale lease; invalid policy/issuer/capture and generic completion bypass.
No duplicate downstream work because this tracer has no dispatch path.

Run focused/full/core/golden/lint/types/build/browser checks, then one bounded
real CRCL poll if current policy/contact/limiter are valid. Record its actual
outcome without inventing a changed filing. Verify old evidence row hashes,
current counts, UI provenance and zero new ordinary/financial work; commit/tag.

## Accepted review refinements (authoritative over the draft above)

1. Baseline is a tagged union, never arbitrary capture IDs. `initial_seed` pins
   an owner-reviewed seed approval plus exact D3c request/execution, plan hash,
   result-manifest hash and Submissions capture. Its acceptance cutoff is no later
   than the seed HTTP **request start** or current cutoff. `prior_monitor_result`
   pins the prior request/execution, manifest ID/hash and contract version; it
   must be terminal complete/eligible. Its captures/cutoff/window/forms/policy
   become the exact baseline. Scope/version changes require a reviewed rebase.
   A narrow immutable `filing_monitor_seed_approvals` record expresses the
   initial reviewed lineage; runtime cannot create or edit seed approvals.
2. Every HTTP 200 body, including an identical body, stays archived with an
   immutable governed attempt-payload descriptor (`source_attempt_payloads`:
   attempt FK, fetched/archived timestamp, blob reference, SHA256 and byte count).
   Source/params/policy are bound through that immutable attempt. Equality can
   avoid a second logical capture only after the new attempt payload is archived
   and verified; it never discards the raw body. Actual status/headers stay 200.
3. Required history is the advertised set whose date ranges overlap the pinned
   filed window. Non-overlapping history is explicitly excluded. Missing/malformed
   range metadata or more overlapping resources than the cap produces incomplete
   coverage (`history_limit_exceeded` where applicable), never silent truncation.
4. `no_change` requires complete baseline AND current coverage. Out-of-scope raw
   changes may create distinct captures with `no_change` for scoped filings.
   UI checked-at is actual attempt completion, separate from acceptance cutoff,
   filed window and source-known limits.
5. No downstream dispatch, amendment/restatement inference or quote/membership/
   normalization/publication side effects. Existing fencing/history remain intact.

Approval was delivered in this task by coordinator
`01a0bbd2-bd4d-77c2-86f6-2a34fef283f1`; no further pause is required for this
accepted bounded scope. The acceptance matrix is in
[filing-monitor-test-plan.md](filing-monitor-test-plan.md).

## Acceptance hardening

Migration 0009 adds a unique completed monitor result per execution. It prevents
ambiguous prior-result selection even if a caller directly invokes the governed
completion twice. It changes no result fields or review scope. It follows 0008
sequentially because 0008 was already applied for the real poll; applied migration
history and source evidence were preserved. See the D4a milestone for verification.
