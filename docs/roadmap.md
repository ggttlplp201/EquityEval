# Operational implementation roadmap

Canonical dependency/status list, reconciled 2026-09-21 from `b4c1e19` /
`milestone/d3f-currency-search`. This links existing milestones and features;
it does not create substitute engines or duplicate feature backlogs.
The [milestone index](milestones/README.md) records checkpoints; each linked
feature/design retains its detailed acceptance criteria.

## What operates today

- **Implemented code:** W1 durable requests/leases/retries; S3 SEC transport,
  inventory, normalization and PIT infrastructure; S4a price/macro adapters and
  selectors; bounded S5 pure metrics/history and X1 pure comparisons.
- **Real application data:** one reviewed SEC source/policy, CRCL issuer/security,
  12 captures, three acquisition bootstraps and one completed D4a filing check
  (13 fetch attempts, one retained monitor response body). No exchange quote, membership,
  normalization batch or financial-analysis result. These counts describe the D4a checkpoint.
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
| Automatic SEC filing monitoring | [S3](milestones/S3-ingestion.md) + [W1d](features/W1-watchlist-analysis.md); [D4a detection](milestones/D4a-filing-monitor.md) then D4b scheduling | D4a one-shot detector verified; recurring service not configured | Reviewed monitor request/result, registered issuer/security, approved SEC policy, W1 leases, shared limiter | D4a: pinned cutoff/forms/baseline, immutable evidence, exact metadata diff, auditable no-change/new/amendment/incomplete/error, concurrency/retry tests and bounded real check. D4b: explicitly configured recurring execution, health/lag/recovery and no duplicate dispatch. |
| Scheduled quarterly/annual updates | S3/W1; D4b poll scheduling and later W1b handoff | Not operating | D4a, reviewed schedule/budget, operator service configuration | Discover actual 10-Q/10-K and amendments, including late/out-of-order arrivals; never assume earnings dates are filing availability. Missed poll recovery preserves pinned windows/history. No OS scheduler in D4a. |
| Approved quote/reference-data provider | [S4](milestones/S4-prices-macro.md), [licence register](data-licences.md), [D3f](milestones/D3f-quote-currency-search.md) | Externally blocked: compatible retained-use entitlement and explicit CRCL currency evidence absent | Exact endpoint/account entitlement, rights for raw/normalized retention, reviewed resource adapter | Retention/attribution/redistribution scope recorded; authoritative issuer/class/exchange/currency/date binding archived through governed attempts; no inference from reporting USD. |
| Quote registration | [D3d](milestones/D3d-quote-identity-review.md) / D3f conditional follow-up | Blocked; zero identifiers | Qualifying archived currency evidence and effective date, existing issuer/security identity | Narrow idempotent writer; overlap/conflict/identity/date tests; immutable source link and history; no membership or financial publication side effect. |
| Live/delayed production prices | S4a activation, [S4b](milestones/S4-prices-macro.md#remaining-scope-and-next-handoff), S6/S8 | Adapter/storage code exists; no operating price source | Approved provider, registered quote, reviewed lifecycle/session coverage, application policy | Real bounded capture and exact-date selection, visible source time/delay/staleness/gaps; no stale failure silently revived; source lineage reaches displayed prices. |
| Corporate-action processing | S4b action/ADS lifecycle review | Planned; not operating | Concrete shared contract, action source rights, instrument lifecycle evidence | Splits/dividends/share-class/ADS changes retain effective/known-at evidence; prevent adjusted/raw/share-basis mixing; restatement and out-of-order action regressions. |
| Ordinary company analysis requests | [W1b](features/W1-watchlist-analysis.md), S3/S4 stages → S5/S7 | Request/source-stage infrastructure exists; zero ordinary application requests | Quote identity, explicit plan/coverage, eligible implemented engines | Every applicable stage considered; unavailable/unsupported remains visible; immutable results, retry/cancel/fencing, no duplicate membership/results. |
| Real financial normalization and PIT selection | S3 + [S5](milestones/S5-ratios.md) real-data handoff | Infrastructure and reviewed fixtures exist; zero application batches | Ordinary source request or separately reviewed handoff; exact financial/event coverage and mappings | Real archived filings normalize through existing publication fence; accounting flags/source precision; as-reported/restated and filed/capture cutoffs verified without lookahead. |
| Published company ratios/valuation | S5 → [S6](api-contract.md) → S7/S8; [F1](features/F1-fundamentals-guide.md) | Bounded pure metrics and fictional UI exist; production publication/valuation pending | Real selected facts; S5 policy completion; S6 snapshots/API; S7 assumptions/valuation; price/actions for applicable ratios | Real values trace to operands/formula/source; 3/5/10-year coverage preserved; missing inputs remain gaps; valuation is a range with assumptions, never a buy/sell signal. |
| Real sector-wide data/comparisons | [X1](milestones/X1-sector-explorer.md), D024, S6 | Pure calculations/fictional graphs verified; real publication blocked | Reviewed universe/taxonomy/membership history, constituent fundamentals/prices/actions, common basis, S6 | Graphs use real eligible constituents; aggregate vs median explicit; coverage/exclusions/calculation/source details; historical membership and no lookahead; thresholds remain versioned policy. |
| Automatic result refresh after eligible filings | W1b + S5/S6; D4a discovery → reviewed financial handoff | Not operating; D4a reports discovery eligibility/blockers only | Complete discovery, quote/coverage gates, explicit reviewed deduplicated handoff, published snapshot contract | One eligible filing edition queues one logical downstream job; late completion cannot replace newer result; old snapshots retained; amendment is not automatically restatement/non-reliance. |
| Production watchlist/search/add/rerun | [W1a–c](features/W1-watchlist-analysis.md), S6/S8/U1 | Membership/request primitives implemented; production search/UI/full analysis pending | Search/identity source, quote registry, S6 API, W1b engine results | Resolve ambiguous instruments; atomic add+request; repeat-click idempotency; visible progress/errors; remove/re-add and explicit rerun preserve history; verified user-manual walkthrough. |

## Next execution sequence

1. **D4a — completed bounded tracer:** approved monitor contract, CLI/worker,
   immutable evidence and saved UI verified. One real CRCL poll found no new
   scoped filings. See the D4a milestone for counts, times and acceptance.
   No automatic scheduler or downstream financial enqueue in this slice.
2. **D4b — Scheduling readiness:** after D4a acceptance, review/configure the
   application-owned polling service, cadence, health/recovery and operational
   lifecycle. OS-level scheduling requires its own explicit task; D4a installs none.
3. **In parallel dependency order, not duplicate implementation:** resolve S4
   reference/quote evidence and source entitlement; review S4b lifecycle and
   S5/S6 financial publication boundaries. D4a can proceed while quote currency
   remains blocked; production analysis cannot bypass that blocker.
4. Connect eligible discoveries to W1b only through the reviewed deduplicated
   handoff, then publish S5/S7/S6 results and complete S8/W1 UI and U1 acceptance.
   X1 real coverage follows its constituent/universe dependencies.

N1 stock-specific discovery, CPI/PPI/Fed calendars, conditional assessments and
in-app/desktop/email delivery retain the existing [N1 plan](features/N1-news-and-macro-agent.md).
An SEC financial-filing detector does not complete those news/alert features.
