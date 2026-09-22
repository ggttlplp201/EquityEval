# Operational implementation roadmap

Canonical dependency/status list, reconciled 2026-09-22 through the
[S6a fundamentals publication](milestones/S6a-fundamentals-publication.md). This links existing milestones and features;
it does not create substitute engines or duplicate feature backlogs.
The [milestone index](milestones/README.md) records checkpoints; each linked
feature/design retains its detailed acceptance criteria.

## What operates today

- **Implemented code:** W1 durable requests/leases/retries; S3 SEC transport,
  inventory, normalization and PIT infrastructure; S4a price/macro adapters and
  selectors; S5 source metrics/fiscal periods, explicit applicability/freshness/coverage,
  neutral rules/trends, accounting checks/history and X1 pure comparisons. S6a adds
  governed synthetic snapshot publication and read-only retrieval with generated contracts.
- **Real application data:** one reviewed SEC source/policy, CRCL issuer/security,
  12 captures, three acquisition bootstraps and two completed filing checks
  (14 fetch attempts, two retained monitor response bodies). One application-owned
  schedule is paused after its bounded D4b slot; no background service is configured.
  No exchange quote, membership, normalization batch or financial-analysis result.
- **Archived research:** D2 seven-company observations and identity research;
  D3d reviewed capture assertions and D3f web-search notes. Research is not an
  operating provider, normalized production fact or published financial result.
- **Development UI:** Company/Sector examples are fictional; pilot observations
  and pipeline audits have distinct saved-data labels. News/calendar views are
  unconfigured. No background SEC poller, automatic result refresh or delivery
  scheduler is operating.

## Ordered capability register

| Capability | Existing owner / scheduled slice | Current status | Dependencies | Acceptance before calling it operational |
| --- | --- | --- | --- | --- |
| Automatic SEC filing monitoring | [S3](milestones/S3-ingestion.md) + [W1d](features/W1-watchlist-analysis.md); [D4a detection](milestones/D4a-filing-monitor.md) and [D4b scheduling](milestones/D4b-filing-scheduler.md) | Detector and bounded manual schedule verified; schedule paused, recurring service not configured | Reviewed monitor request/result, registered issuer/security, approved SEC policy, W1 leases, shared limiter | D4a: pinned cutoff/forms/baseline, immutable evidence, exact metadata diff, auditable no-change/new/amendment/incomplete/error, concurrency/retry tests and bounded real check. D4b: manual slot/health/recovery and repeat dedup verified. Recurring operation additionally needs reviewed rebase and explicit service configuration. |
| Scheduled quarterly/annual updates | S3/W1; D4b poll scheduling and later W1b handoff | Not operating | D4a, reviewed schedule/budget, operator service configuration | Discover actual 10-Q/10-K and amendments, including late/out-of-order arrivals; never assume earnings dates are filing availability. Missed poll recovery preserves pinned windows/history. No OS scheduler in D4a. |
| Approved quote/reference-data provider | [S4](milestones/S4-prices-macro.md), [licence register](data-licences.md), [D3f](milestones/D3f-quote-currency-search.md) | Externally blocked: compatible retained-use entitlement and explicit CRCL currency evidence absent | Exact endpoint/account entitlement, rights for raw/normalized retention, reviewed resource adapter | Retention/attribution/redistribution scope recorded; authoritative issuer/class/exchange/currency/date binding archived through governed attempts; no inference from reporting USD. |
| Quote registration | [D3d](milestones/D3d-quote-identity-review.md) / D3f conditional follow-up | Blocked; zero identifiers | Qualifying archived currency evidence and effective date, existing issuer/security identity | Narrow idempotent writer; overlap/conflict/identity/date tests; immutable source link and history; no membership or financial publication side effect. |
| Live/delayed production prices | S4a activation, [S4b](milestones/S4-prices-macro.md#remaining-scope-and-next-handoff), S6/S8 | Adapter/storage code exists; no operating price source | Approved provider, registered quote, reviewed lifecycle/session coverage, application policy | Real bounded capture and exact-date selection, visible source time/delay/staleness/gaps; no stale failure silently revived; source lineage reaches displayed prices. |
| Corporate-action processing | S4b action/ADS lifecycle review | Planned; not operating | Concrete shared contract, action source rights, instrument lifecycle evidence | Splits/dividends/share-class/ADS changes retain effective/known-at evidence; prevent adjusted/raw/share-basis mixing; restatement and out-of-order action regressions. |
| Ordinary company analysis requests | [W1b](features/W1-watchlist-analysis.md), S3/S4 stages → S5/S7 | Request/source-stage infrastructure exists; zero ordinary application requests | Quote identity, explicit plan/coverage, eligible implemented engines | Every applicable stage considered; unavailable/unsupported remains visible; immutable results, retry/cancel/fencing, no duplicate membership/results. |
| Real financial normalization and PIT selection | S3 + [S5](milestones/S5-ratios.md) real-data handoff | Infrastructure and reviewed fixtures exist; zero application batches | Ordinary source request or separately reviewed handoff; exact financial/event coverage and mappings | Real archived filings normalize through existing publication fence; accounting flags/source precision; as-reported/restated and filed/capture cutoffs verified without lookahead. |
| Published company ratios/valuation | S5 → [S6](api-contract.md) → S7/S8; [F1](features/F1-fundamentals-guide.md) | S5 engine and narrow synthetic S6a snapshots/API implemented; production publication/valuation pending | Real selected facts; reviewed production S5 policies; S6 snapshots/API; S7 assumptions/valuation; price/actions for applicable ratios | Real values trace to operands/formula/source; 3/5/10-year coverage preserved; missing inputs remain gaps; valuation is a range with assumptions, never a buy/sell signal. |
| Real sector-wide data/comparisons | [X1](milestones/X1-sector-explorer.md), D024, S6 | Pure calculations/fictional graphs verified; real publication blocked | Reviewed universe/taxonomy/membership history, constituent fundamentals/prices/actions, common basis, S6 | Graphs use real eligible constituents; aggregate vs median explicit; coverage/exclusions/calculation/source details; historical membership and no lookahead; thresholds remain versioned policy. |
| Automatic result refresh after eligible filings | W1b + S5/S6; D4a discovery → reviewed financial handoff | Not operating; D4a reports discovery eligibility/blockers only | Complete discovery, quote/coverage gates, explicit reviewed deduplicated handoff, published snapshot contract | One eligible filing edition queues one logical downstream job; late completion cannot replace newer result; old snapshots retained; amendment is not automatically restatement/non-reliance. |
| Production watchlist/search/add/rerun | [W1a–c](features/W1-watchlist-analysis.md), S6/S8/U1 | Membership/request primitives implemented; production search/UI/full analysis pending | Search/identity source, quote registry, S6 API, W1b engine results | Resolve ambiguous instruments; atomic add+request; repeat-click idempotency; visible progress/errors; remove/re-add and explicit rerun preserve history; verified user-manual walkthrough. |

## Next execution sequence

1. **D4a — completed bounded tracer:** approved monitor contract, CLI/worker,
   immutable evidence and saved UI verified. One real CRCL poll found no new
   scoped filings. See the D4a milestone for counts, times and acceptance.
   No automatic scheduler or downstream financial enqueue in this slice.
2. **D4b — Scheduling readiness completed:** [D036](design/s3/filing-scheduler-proposal.md)
   and its [milestone](milestones/D4b-filing-scheduler.md) record the verified manual
   slot, lifecycle/budget/recovery and saved UI. The real slot found no new scoped
   filings; repeat/concurrent ticks added no work. The schedule is paused.
   Next review is scope replacement/rebase and explicit application-worker service
   configuration: the fixed window ends 2026-09-21 UTC. No automatic scope
   expansion or OS-level scheduler was installed.
3. **S6a — synthetic fundamentals publication implemented:** D037's narrow
   contract reuses S5 and W1 for immutable inputs/results, exact cache reuse,
   enqueue-time selection intent and read-only API. See the
   [milestone](milestones/S6a-fundamentals-publication.md) and
   [operator/manual chapter](user-manual/saved-fundamentals.md). UI is unchanged.
   S6b assumptions/model contracts and a separately reviewed real-data tracer
   remain next decisions; D004/D005 still gate the full valuation/P0 API freeze.
4. Resolve S4 reference/quote evidence and source entitlement, S4b lifecycle and
   real governed normalization/PIT/profile/calendar/precision inputs. No source
   scope expansion, quote inference or provider activation occurred in S5.
5. After contract and data gates, connect eligible discoveries through reviewed
   W1b deduplication, publish the supported S5/S7/S6 results, and finish S8/W1/U1
   flows. X1 real coverage follows its constituent/universe dependencies.

N1 stock-specific discovery, CPI/PPI/Fed calendars, conditional assessments and
in-app/desktop/email delivery retain the existing [N1 plan](features/N1-news-and-macro-agent.md).
An SEC financial-filing detector does not complete those news/alert features.
