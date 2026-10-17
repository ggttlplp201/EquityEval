# Operational implementation roadmap

Canonical dependency/status list, reconciled 2026-10-17 through the
[D5l history evidence checkpoint](milestones/D5l-history-evidence.md). This links existing milestones and features;
it does not create substitute engines or duplicate feature backlogs.
The [milestone index](milestones/README.md) records checkpoints; each linked
feature/design retains its detailed acceptance criteria.

## What operates today

- **Implemented code:** W1 durable requests/leases/retries; S3 SEC transport,
  inventory, normalization and PIT infrastructure; S4a price/macro adapters and
  selectors; S5 source metrics/fiscal periods, explicit applicability/freshness/coverage,
  neutral rules/trends, accounting checks/history and X1 pure comparisons. S6a adds
  governed synthetic snapshot publication and read-only retrieval with generated contracts.
  S6b/S7a adds audited synthetic reverse DCF, immutable assumptions/runs, W1 publication
  and a trusted-local generated API.
- **Real application data:** one reviewed SEC source/policy, CRCL issuer/security,
  142 captures, twenty-six acquisition bootstraps and two completed filing checks
  (145 fetch attempts, two retained monitor response bodies). One application-owned
  schedule is paused after its bounded D4b slot; no background service is configured.
  Three immutable real normalization batches retain fourteen selected facts. Three real
  fundamentals requests retain the earlier D5j result plus separate D5k annual and
  closing-instant results: six supported metric definitions with explicit gaps;
  thirty-one requests in total. No exchange quote or membership. D5d reviews all eleven
  formerly missing exhibits; D5f closes the later CFO-release gap. D5g matches the
  earlier Q1 and annual comparative selected lines. D5h reviews all seven remaining
  registration bodies and reconciles selected editions. D5i closes the observation gap and publishes a new eligible two-concept batch
  at the exact October 15 observation. D5a remains historically blocked.
  [D5j](milestones/D5j-real-fundamentals.md) publishes descriptive FY2025 operating
  margin through a separate reviewed real-v2 contract, without a quote. D5k extends
  the supported set using ten directly reported concepts and separate period selectors.
- **Archived research:** D2 seven-company observations and identity research;
  D3d reviewed capture assertions and D3f web-search notes. Research is not an
  operating provider, normalized production fact or published financial result.
- **Development UI:** Company/Sector/Fundamentals/Financials/Valuation examples are fictional; pilot observations
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
| Real financial normalization and PIT selection | S3 + [S5](milestones/S5-ratios.md) real-data handoff | D5k ten-concept FY2025 batch eligible; prior D5i/D5a batches preserved | Ordinary source request or separately reviewed handoff; exact financial/event coverage and mappings | Real archived filings normalize through existing publication fence; accounting flags/source precision; as-reported/restated and filed/capture cutoffs verified without lookahead. |
| Published company ratios/valuation | S5 → [S6](api-contract.md) → S7/S8; [F1](features/F1-fundamentals-guide.md) | D5k publishes four annual and two instant metrics in separate results; four definitions remain globally unsupported. D5j is preserved. Synthetic S6a and S6b/S7a remain separate | Real selected facts; reviewed production S5 policies; S6 snapshots/API; S7 assumptions/valuation; price/actions for applicable ratios | Real values trace to operands/formula/source; 3/5/10-year coverage preserved; missing inputs remain gaps; valuation is a range with assumptions, never a buy/sell signal. |
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
   **S6b/S7a — audited synthetic reverse valuation implemented:** D038 approval of
   `5b85140` covers the [implementation](design/s7/implementation.md), sequential
   0012, immutable assumptions, certified Decimal solver, full bridge, W1 worker
   and generated API. See the [milestone](milestones/S6b-S7a-valuation-contract.md)
   for checkpoint verification and [manual](user-manual/saved-valuations.md) for
   the operator workflow. Real publication remains later. [S8a](milestones/S8a-synthetic-valuation-ui.md) adds a separate read-only fictional valuation view using these audited outputs; it does not connect production data. [S8b](milestones/S8b-fundamentals-ui.md) adds a separate fictional Company Fundamentals view over validated S6a payloads, with saved 3/5/10-year history and coverage.

4. Resolve S4 reference/quote evidence and source entitlement, S4b lifecycle and
   real governed normalization/PIT/profile/calendar/precision inputs. No source
   scope expansion, quote inference or provider activation occurred in S5.
5. After contract and data gates, connect eligible discoveries through reviewed
   W1b deduplication, publish the supported S5/S7/S6 results, and finish S8/W1/U1
   flows. X1 real coverage follows its constituent/universe dependencies.

N1 stock-specific discovery, CPI/PPI/Fed calendars, conditional assessments and
in-app/desktop/email delivery retain the existing [N1 plan](features/N1-news-and-macro-agent.md).
An SEC financial-filing detector does not complete those news/alert features.

S7a coordinator audit follow-up: [corrective checkpoint](milestones/S7a-corrections.md)
binds scenario values to provenance, proves bridge exclusions, and verifies source
share scales before milestone approval. The earlier checkpoint remains in Git.


S8c is complete at `milestone/s8c-financials-ui-corrected` for its bounded [saved Financials view](milestones/S8c-financials-ui.md).
The audited S6a metric payload is not a full-statement contract. S8c therefore
uses separate fictional source copies and normalized period/unit semantics,
without joining Company/Sector/Fundamentals identities. Annual and direct-quarter
editions are represented; balances stay instants and TTM stays unavailable.
Real statement publication retains its separate prerequisites; bounded S8d
integration is recorded below.

S8d Company Overview integration is complete at `milestone/s8d-company-overview`
with the independent missing-marker correction, 1,669 full tests and 26 browser checks. See the [milestone](milestones/S8d-company-overview.md).
The metadata manifest proves the current workspaces are separate fictional
examples, preserves their own default selectors and exposes exact linkage
and source evidence. It does not fulfill real-company publication prerequisites.

D5a is complete at `milestone/d5a-crcl-normalization` and publishes the first
bounded real CRCL normalization/PIT batch using the
existing governed D3c archives and S3 mapping/publisher/reader. Its separate
[results view and milestone](milestones/D5a-crcl-normalization.md) expose two FY2025
facts, five source captures, three filing editions and retained incomplete-history
flags. Exact replay reuses the batch; historical and original read-back are checked.
The application stays on migration 0010. No real S5/S6 analysis, price-dependent
ratios, valuations or sector results were published. Complete source/event coverage
and the existing downstream review gates remain the next prerequisites.

D5a's corrective checkpoint separates selected numeric/precision/metadata sources
from non-PIT filing review context, removes later precision/literals from the
before-filing view and validates mapping approver/scope during replay and standalone
verification. Its publication batch and original audit remain unchanged.

D5b is the next bounded step: a checked read-only readiness projection over the
D5a artifacts. It distinguishes normalized source facts from S5-eligible inputs,
shows the retained evidence gates and publishes no real metric. It introduces no
application write, source acquisition, quote identity, schema/API or formula
change; those remain prerequisites for real S5/S6 publication.

D5b is complete with a deterministic fail-closed artifact and
`/development/pilot/analysis`. Pipeline and normalization now lead to the same
two-input, zero-metric decision. The next proposal must define CRCL's reviewed
business/metric profile and exact source/history coverage before any source
expansion or real calculation publication.

D5c extends that saved analysis view with a [bounded safety review](milestones/D5c-crcl-safety.md).
All 19 scoped primary bodies are now retained; historical September knowledge
still has only three. Retrospective annual-pair/amendment checks pass, but eleven
exhibits and prior-period reclassification scope remain unresolved. Fresh October
inventory identifies two later events requiring a new current-cutoff review.
Next: bounded reconciliation/acquisition, new PIT batch, then dedicated real S6
publication review. No numeric margin, quote, provider or shared-contract change.


## D5d exhibit review and remaining phases

[D5d](milestones/D5d-crcl-exhibits.md) acquired all eleven D5c exhibit bodies in
three governed groups and reviewed them within explicit accounting scopes.
The annual earnings operands match the retained annual filing; tested quarterly
and comparative rows agree with retained periodic filings. Non-GAAP definition
changes, share-class reclassification and target-company SFRS representations
remain distinct from Circle reported GAAP restatement. No metric was published.
The earlier D5c missing-exhibit decision remains an immutable pre-exhibit snapshot.

**Next main gate:** separately pin current financial/event coverage, review the
later primary filings, settle remaining annual affected-line accounting scope,
and prepare a newly governed PIT batch. Real S6 publication needs its own accepted
contract/authorization. October evidence cannot retrofit September knowledge.
Acquisition agreement schedules/target financials are not substitutes for Circle
financial evidence; later transaction accounting needs separate review.

The foundation, source infrastructure and pure S5 engine are complete for their
accepted scopes. S6/S7 publication and S8 fundamentals/financials/valuation views
are verified with synthetic or fictional inputs; that is distinct from operating
real-company analysis. Remaining major phases are:

1. Real eligible fundamentals publication and corresponding UI integration.
2. Approved quote-provider operation and S4b corporate actions/lifecycle coverage.
3. Real valuation inputs, reviewed assumptions and publication/UI integration.
4. Ordinary W1 add/rerun/watchlist workflows, governed filing-to-analysis handoff
   and configured monitoring; the existing scheduler remains paused.
5. X1 real universe/taxonomy/membership and comparable constituent coverage.
6. N1 news/calendar ingestion and delivery, then U1 verified manual and release acceptance.

These are dependency stages, not equal-sized percentage-completion units. A
source-only operating-margin result does not need a quote; price-dependent
valuation and comparisons do.


## D5e current-window checkpoint

[D5e](milestones/D5e-crcl-current.md) retains the two later primary 8-Ks and fresh
required Facts/Submissions in one governed group. Both primaries were read in
full: one describes expanded Binance arrangements/private placement; the other
describes director/CFO departures. The latter links a previously unretained
CFO-departure Exhibit 99.1 (`final_leadershiptransiti.htm`), which was not silently
acquired beyond the pinned group or classified from parent metadata.

Fresh inventory matches the 21 scoped financial/event primaries. Its observation
at 2026-10-13 05:01:15.264075 UTC is distinct from the final body retrieval at
05:01:15.734230 UTC; neither changes September application knowledge. Fresh annual
Company Facts editions still match the original annual values. Actual repeated
Q2/H1 selected operands match across retained periodic editions. The earlier Q1
edition and blanket affected-line scope remain unconfirmed; no actual change is
inferred. No new PIT batch or metric was published.

Next: pin the exact outstanding CFO release and the evidence needed to resolve
remaining affected-line/edition scope, then reassess governed same-concept batch
preparation. Real S6 remains a separately explicit contract/authorization stage.
The major remaining product phases above are unchanged. These bounded evidence
milestones should not be confused with completion of operating real valuation.

## D5f checkpoint — leadership exhibit and retained accounting (2026-10-13)

Proposal `f72a5ed` follows D5e. The named CFO-transition exhibit is retained and
read in full: transition/search/comments, with no correction/restatement/non-reliance
identified in that body. Three governed captures preserve prior rows. Application
now holds 60 captures, 62 attempts, 12 bootstrap and two monitor requests, one
normalization batch, two facts and zero real metrics.

All six retained periodic/amendment bodies were searched for selected FY2025
contexts and reclassification passages. Earlier Q1/complete affected-line scope
remains unconfirmed; unrelated equity/fund-tax/liability changes do not clear it.
Exact next source candidate: IPO 424B4 `0001193125-25-135795/d737521d424b4.htm`,
identified from retained inventory only. Its content/sufficiency awaits review.
Fresh scoped inventory/annual editions match. No new PIT batch or real S6 output.
The major roadmap remains: resolve evidence/normalization eligibility, then
separately satisfy real S6 publication, broader metric inputs/history and later
valuation/sector stages. This checkpoint is not completion of those phases.
See [milestone](milestones/D5f-crcl-leadership.md).


## D5g checkpoint — IPO prospectus reconciliation (2026-10-13)

Proposal `4866b16` (D045) acquired the exact IPO 424B4 and mandatory inventories.
The reported Q1 selected pair matches the later Q1 comparative and all thirteen
retained Facts vintages. FY2024/FY2023 annual selected lines match the later annual
comparatives. These specific earlier-edition comparisons are now established.

The prior 21-primary roster covered K/Q/8-K, not registration history. Seven known
S-1/S-1/A/424B4 bodies remain unreviewed. Their correction/edition content cannot
be inferred from metadata. The next bounded evidence gate is their substantive
review in two BootstrapPlan groups (five plus two), each with mandatory inventories.
No additional acquisition is implicit. Then reassess completeness, affected-line
scope and current cutoff before proposing a new same-concept PIT normalization batch.

Current totals: 63 captures, 65 attempts, 13 bootstrap and two monitor requests,
one normalization batch, two facts, zero metrics. No shared-contract or real S6
publication occurred. Historical September knowledge is unchanged. The roadmap
remains in real-source/PIT safety; later main phases are real S6 publication,
reviewed price/provider and corporate-action coverage, broader fundamentals and
valuation assumptions/engines/UI, sector coverage, ordinary watchlist orchestration,
recurring operation and release/manual verification. Existing synthetic S6/S7/S8
checkpoints are implemented, not proof of real-company publication readiness.
See [milestone](milestones/D5g-crcl-prospectus.md).

## D5h checkpoint — registration history (2026-10-13)

All seven exact D5g registration/prospectus bodies were retained and reviewed in
two governed groups. Selected annual and interim editions reconcile against
18 periodic operands and 15 Facts vintages. Source-content reconciliation passes
within its selected-line scope; current temporal completeness does not. The final
inventory observation precedes final body retention, so neither full-day coverage
nor a current eligible batch is asserted. No new batch or metric was published.

Totals: 74 captures, 76 attempts, 15 bootstrap and two monitor requests, one batch,
two facts, zero metrics. Next: separately pin `company_facts/0001876042` and
`submissions/0001876042`, both captured after all retained bodies; review changed
inventory before current S3 preparation. Then real S5 applicability/accounting and
S6 publication remain the next main analysis gates. Broader fundamentals/history,
provider/quote and price/action coverage, valuation assumptions and real S7/S8,
sector coverage, automatic refresh and production watchlist/manual flows retain
their dependencies in the capability register. D5h is a bounded evidence milestone,
not completion of those product phases. See [milestone](milestones/D5h-crcl-registration.md).

## D5i checkpoint — eligible current normalization (2026-10-15)

A fresh governed Facts/Submissions pair postdates all reviewed bodies. Unchanged
content and exact metadata-vintage reconciliation support a new immutable S3 batch
at 2026-10-15T21:59:05.195192Z. This is retrospective knowledge at that observation,
not September knowledge or coverage through the full day. Independent standards,
specification and plausible-but-wrong numeric reviews cleared the pinned batch.
Live publication, exact replay, original/current/pre-filing selection and prior-row
preservation pass. Historical D5a blockers remain unchanged.

Totals: 76 captures, 78 attempts, 16 bootstrap and two monitor requests, two batches,
four selected facts, zero published real metrics. Next main gate: a separately
reviewed real-source S6 contract proposal. Existing synthetic-only evidence modes
and required quote identity cannot represent unpriced real CRCL fundamentals.
Source acquisition/reconciliation is complete for this bounded two-concept snapshot;
S4 provider/quote activation, broader S5/S6 product coverage, valuation, automation
and final dashboard phases remain governed by the capability register above.
See [milestone](milestones/D5i-crcl-observation.md).

## D5j proposal checkpoint — real source-only S6

[D048 / concrete packet](design/d5j/proposal.md) identifies the existing synthetic-only
input/result modes, required quote selector/storage fields and W1 request bindings.
It chooses separate real v2 endpoints/client and companion relational records,
with an explicitly discriminated W1 source-only intent and unchanged v1 behavior/statuses and
existing core math, typed policy/source evidence, additive migration and reviewed
source-only W1 intent. The coordinator has confirmed approval of this exact design under the user’s
continuation. The proposal itself published no metric; staged SQL/Pydantic/API
and pre-publication numeric reviews subsequently passed for the exact r3 boundary below.

## D5j completed boundary — one real annual metric

The separate real-v2 contract, companion 0013 tables and dedicated W1 intent
publish the exact reviewed D5i operands as descriptive FY2025 operating margin.
Snapshot `1a259fc4-7395-4111-939b-30c58919e230` has one valid metric and nine
null/unsupported slots with exact operand and applicability requirements.
The source observation is 2026-10-15T21:59:05.195192Z; later evaluation/publication
does not extend knowledge. All earlier batches, audits and v1 contracts are retained.
See [milestone](milestones/D5j-real-fundamentals.md) and [handoff](handoffs/d5j-real-fundamentals.md).

**Next main stage:** broader real fundamentals require explicit metric-specific
source and accounting applicability review, then governed normalization and
publication. Historical comparison and quarterly trends require complete aligned
periods. This bounded CRCL operating-margin chain is complete; it does not finish
the whole application. Separate remaining phases are approved quote/reference
data and S4b lifecycle coverage; real valuation assumptions/ranges; product
watchlist/company/sector integration; reviewed automatic refresh/monitor service;
and release/manual acceptance. Provider entitlement and quote identity remain
external blockers for price-dependent work. No scheduler is activated.

## D5k checkpoint — broader reported fundamentals and pause

The expanded 41-body accounting review and 101 matching-period comparisons support
a ten-concept FY2025 batch at the unchanged exact D5i observation. Existing S5 and
real-v2 contracts publish four annual metrics and two closing-instant metrics in
separate immutable snapshots. Each other-period slot remains an explicit gap;
gross margins, growth and ROA remain unsupported. Both closing balance identities
pass. D5j and all prior rows/audits are preserved. No new acquisition, schema/API,
provider/quote, valuation/sector or scheduler scope was introduced.

Application totals: 76 captures, 78 fetch attempts, 21 requests (16 bootstrap, two
monitor, three real fundamentals), three normalization batches, fourteen selected
facts, three real snapshots and six supported metric definitions across the latest
annual/instant pair. One paused schedule; zero quote identifiers or memberships.
Source knowledge remains 2026-10-15T21:59:05.195192Z, regardless of later publication.

**Pause after this milestone, as requested.** On resume, the next non-price gate
is a concrete earlier-history acquisition/review boundary: nine retained-inventory
draft/correspondence resources are missing, including four unsupported PDF bodies.
Comparative numeric rows alone cannot establish growth/ROA/history eligibility.
Other remaining major phases are approved quote/reference rights and S4b lifecycle;
real valuation assumptions/ranges; company/watchlist/sector product integration;
reviewed automatic refresh and recurring service; release/manual acceptance.
See [milestone](milestones/D5k-broader-fundamentals.md) and
[handoff](handoffs/d5k-broader-fundamentals.md).


## D5l resumed boundary — acquisition implemented, history eligibility blocked

The reviewed exact 47-body V2 contract and migration 0014 are applied. The governed
run retains 46 bodies (39 HTML/seven PDF) and ten mandatory pairs, then stops on the
ARS 8 MiB body limit. Seven retained PDFs also fail the required host memory-cap
check before parsing. Group 11 was correctly withheld. All old financial rows and
three snapshots are preserved; no new source normalization or metric is published.
The HTML text/reference index records specific accounting findings but does not
claim full selected-edition clearance. Gross margin, growth, ROA and history remain
blocked by exact source/runtime/accounting/cutoff requirements. See the
[milestone](milestones/D5l-history-evidence.md) and
[remaining unexecuted amendment candidate](design/d5l/remaining-boundary.md).
Stop after this major checkpoint before multi-company rollout. Remaining phases
include completing this source/history gate, multi-company governed coverage,
quote/reference rights and S4b lifecycle, real valuation assumptions/ranges,
company/watchlist/sector integration, reviewed recurring refresh, and release/manual
acceptance. No quote provider, scheduler, valuation or multi-company work was added.
