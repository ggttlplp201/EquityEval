# First-source capture: concrete contract review

Status: user-approved 2026-09-21; implemented in D3b. D031 follows the separate
application runtime checkpoint D3a. See [implementation](identity-bootstrap.md).

The initial D3b request options below were superseded by the explicitly authorized
[2026-09-21 review correction](bootstrap-intent.md): new requests pin a bounded
versioned acquisition plan and expose typed readiness. Preserve this proposal as
the initial decision record, not the current enqueue signature.

## Observed blocker

A fresh application database cannot start the currently accepted S3 path:

1. `security_identifiers.source_capture_id` is mandatory (0001).
2. `analysis_requests.quote_identifier_id` is mandatory (0002). Enqueue checks
   both the source-backed identifier and its current validity interval.
3. A live `FetchRequest` needs an active W1 request/stage/lease (S3 contract).
4. The source capture needed by step 1 is created by that live fetch.

This was confirmed from the separately migrated empty application database and
the existing request/transport constraints.
Its issuer, security, policy, capture and normalization tables are empty.
S1's CRCL manifests contain `fetched_at`, hashes and bytes, but no request or
completion timestamps. Copying `fetched_at` into those missing fields would
fabricate capture evidence. Test seed rows do not resolve application cold start.

## Approved bounded change

Add a distinct **source_bootstrap** request trigger within existing W1 storage.
Reuse W1 idempotency, claim/renew, stage fencing, retries, cancellation, audit
and terminal states. Reuse `SecTransport`, `DatabaseAttemptStore`, `LocalArchive`
and the shared Redis SEC limiter. Do not create a second downloader or lease system.

In one new migration:

- Allow `analysis_requests.quote_identifier_id` to be NULL **only** for this new
  trigger. Keep security and workspace mandatory; the registered issuer/CIK and
  class identity must come from the reviewed identity packet.
- Enforce that bootstrap requests have no membership, parent, market plan or
  quote identifier. All ordinary manual refresh and watchlist-add requests retain
  mandatory, validated quotes. Watchlist memberships remain unchanged.
- Add one narrow enqueue function for bootstrap with an explicit idempotency
  key, existing requested periods/history options and a registered security ID.
  Runtime still cannot insert directly into workflow or evidence tables.
- Extend claiming with an explicit source-bootstrap mode. Existing two-argument
  callers retain ordinary requests only; the bootstrap worker claims only the new
  trigger. Both modes keep existing lease/fence enforcement.
- Do not let bootstrap work update any latest financial-result pointer or enter
  price/valuation stages. A source-only worker claims and verifies its trigger;
  ordinary workers reject that trigger before doing work.

The new Python helper returns the existing RequestHandle. Request hashing includes
trigger, workspace, security, periods, history/cutoff/vintage and retry policy.
Identical retries resolve to the same request; changed parameters with the same
key fail. The SEC source run manifest records the genuinely absent quote as NULL.
This is missing **identity**, not a change to financial NULL/status semantics.

Fresh successful captures then support an owner-reviewed identifier registration.
Its date must be evidenced; a filing's publication date is not automatically its
listing start. Complete the covered non-reliance/filing review, normalize and
publish, then enqueue an ordinary source-backed analysis. S6 follows eligible S5.
If quote validity cannot be substantiated, keep that subsequent request blocked.

## Acceptance before using application evidence

- Migrate an empty database through head and existing populated W1 fixtures forward.
- Prove ordinary watchlist/manual requests still reject NULL, mismatched, expired
  and future quotes; bootstrap rejects quote/membership/market/parent payloads.
- Exercise real DB claim/renew/expiry/cancel/retry and concurrent idempotency;
  stale workers must not dispatch or finalize a capture.
- Run the existing transport with deterministic HTTP fixtures on a genuine
  bootstrap request; verify exact policy, timestamps, archive bytes and attempt
  linkage. No test fixtures enter the application DB.
- Successful bootstrap cannot produce a valuation or claim watchlist membership.
- On application execution, use actual SEC contact, existing shared limiter,
  reviewed SEC policy and real timestamps; preserve failed HTTP outcomes.
- Do not clear inventory/event/precision gaps merely because bootstrap succeeds.
- All mandatory suites, schema boundary review and migration smoke must pass.

## Scope and review requested

The user explicitly approved this precise W1/S3 extension after reviewing it. It changes shared
request schema, beyond the already implemented UI and operational runtime.
It neither freezes the S6 API nor approves DCF, new providers or news delivery.
