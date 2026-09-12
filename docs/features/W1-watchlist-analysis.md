# W1 — Watchlist additions trigger full analysis

Status: S2 durable requests and S3 SEC source stages implemented; remaining
engines, UI and monitoring follow. Task: EquityEval — milestone build log.
See [S3 implementation](../design/s3/implementation.md) for the tested add/rerun boundary.

## Requested behavior

The user can search for a stock, choose the correct exchange/share instrument,
and add it to a watchlist. A successful addition automatically starts a fresh
analysis of that stock through every available analysis stage. Users can also
choose **Run analysis again** later. The word “model” in this request means the
complete analysis workflow, not model retraining or just a single DCF calculation.

Proposed first-version behavior: adding one stock analyzes that stock. It does
not rerun every other watchlist member. Repeated clicks on the same add action
do not create duplicate memberships or duplicate work. Re-adding after a genuine
removal creates a new analysis request. An explicit rerun after completion creates
a new execution even when source data has not changed.

## End-to-end workflow

1. Resolve ticker, exchange, issuer, security/share class and data availability.
   Show a choice if a ticker is ambiguous; never silently select a different
   exchange or substitute an ADS for its underlying ordinary share.
2. Save watchlist membership and durably record an analysis request in one
   transaction. The UI can immediately show queued progress.
3. Refresh financial filings/facts, prices and macro observations through the
   configured sources. Once N1 is available, build or refresh its sourced topic
   profile, collect relevant news/driver metrics and create baseline impact
   assessments alongside macro context. Include the security in monitoring;
   see [N1 stock topics](N1-stock-topic-monitoring.md). Discovery gaps remain
   visible and do not prevent independent financial stages from completing.
4. Normalize using the reviewed concepts; perform provenance, period, currency,
   instrument, freshness and accounting checks. Preserve available data and gaps.
5. Recompute available ratios and valuation models in the core engine. Reuse an
   explicitly confirmed assumption-set version if selected. Otherwise request
   the missing assumptions; do not invent discount rates, growth forecasts or
   financial facts to make a valuation appear complete.
6. Save a new analysis snapshot containing exact input references, calculation
   versions, stage outcomes, flags, assumptions and available outputs. Link any
   new model run to its previous version without changing the previous run.
7. Update the company overview and watchlist with the new result, or show why
   some stages need input or failed. Retain a clearly dated last successful result.
   Send a completion alert through enabled, configured channels where selected.

“Full analysis” means every applicable implemented stage is considered. A bank
without a supported DCF model or a company with missing fundamentals returns
an explicit unsupported/partial outcome. The UI must not present it as a
successful complete valuation. Missing credentials yield a configuration issue;
other independent stages can still finish.

## Freshness, retries and history

A new execution refreshes mutable source endpoints according to source quotas
and retry rules, recording checked/fetched times. Immutable filings may be reused
from verified archives; “run again” must still recompute outputs and create a
new snapshot. Do not reuse an old calculation solely because the ticker matches.
Source outages may use the last capture only under an explicit, labelled stale-data
policy; unavailable data must not masquerade as freshly fetched.

A repeated transport request with the same idempotency key returns the same
logical request. A retry is a new attempt under that request, not another user
request. Duplicate Add/transport requests coalesce, while distinct explicit Refresh
requests queue separately with their own identities, even if their parameters match.
Restart recovery resumes or retries unfinished stages without duplicating
snapshots or alerts. Manual cancellation preserves completed evidence and must
not publish an incomplete run as complete.

Removing a stock stops future watchlist monitoring and unsent watchlist-only
notifications. It does not delete archived analyses or automatically cancel a
shared/manual analysis still needed elsewhere. Users can cancel their active
analysis explicitly. Never offer or perform broker actions.

## Build slices

| Slice | Milestone | Acceptance |
| --- | --- | --- |
| W1a — Membership/request/snapshot design | S2 | Reviewed stable security identity, unique active membership, atomic request creation, immutable result history and precise execution states. |
| W1b — Orchestration | After S3/S4/S5/S7 engines and reviewed contract | Durable stages; retries/deduplication; recomputation with pinned assumptions; transparent partial results. |
| W1c — Add/search/rerun UI | S6/S8 | Search by ticker/name/exchange; resolved instrument; add/remove; live progress and stage errors; last/new result comparison; rerun action. |
| W1d — Monitoring and completion alerts | N1 | New stocks enter the configured news/event coverage; delivery respects watchlist state and channel preferences. |

## Required verification

Test ambiguous/reused tickers, ordinary/ADS selection, duplicate and concurrent
adds, process failure between membership and enqueue, retry after timeout,
removal/re-addition, two tabs requesting reruns, stale/unavailable upstream data,
missing assumptions, unsupported models, cancellation/restart and out-of-order
completion. Verify that an earlier snapshot is unchanged, the newest finished
request cannot be replaced by an older late result, and duplicate attempts do
not duplicate user alerts. Manual acceptance: add a supported stock, follow the
stages, inspect sources, edit/confirm assumptions, rerun and compare both snapshots.
