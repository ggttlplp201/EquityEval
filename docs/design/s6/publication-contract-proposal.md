# S6 review packet — immutable source-metric publication

Status: **approved for narrow S6a implementation under D037**, 2026-09-22.
The decisions and constraints are recorded in [S6a implementation](implementation.md).
S6b/S7 and real-data publication remain outside this approval. S5 source-only acceptance is in
[the handoff audit](../s5/acceptance-handoff.md). This packet advances the deferred
S2 input/result records and existing W1 publication controls; it does not create
a parallel job system, relax source rights or enable new provider calls.

## Proposed first contract slice

S6a publishes only eligible S5 source amounts, period assemblies, ten registered
metrics, their applicability/freshness assessments, accounting checks, neutral
observations and optional existing 3/5/10-year own-history results. An unsupported
metric remains in the requested coverage roster with its reason. This is a
**fundamentals analysis**, not fair value, an investment recommendation or a
completed DCF. The real application presently has no normalized financial batch
or analysis snapshot. Ordinary W1 requests still require reviewed quote identity;
this proposal does not smuggle a source-bootstrap request into that path.

Existing X1 calculations and four graph interfaces remain separate consumers.
Publishing real sectors additionally requires D024 universe, membership,
constituent snapshot and capitalization/common-income gates. No selected-watchlist
result becomes a sector-wide result through this contract.

D004 (P0 reverse DCF) and D005 (meaning of the P0 range) remain unresolved. Review
those before claiming a complete P0 API freeze. Proposed sequence: approve a
narrow versioned S6a fundamentals contract first, then S6b assumptions/model
contracts before S7. Do not represent a deterministic sensitivity range as a
probability distribution or invent a DCF result in a fundamentals payload.

## Reuse and concrete record responsibilities

Names below are proposed table/model responsibilities for review, not migration
instructions. Preserve the applied 0001–0010 history; later migration numbering
must be resolved sequentially against the actual repository head.

| Record | Proposed identity and required invariants |
| --- | --- |
| Existing W1 request / request state / execution / stage attempts | Reuse existing request parameters, logical idempotency, current execution/epoch, lease owner/token, cancellations and append-only events. No new queue or generic job identity. |
| Immutable `analysis_input_snapshots` | UUID, one frozen input manifest for the logical request's computation, request and creating execution, frozen selection/evaluation context, engine build, canonical manifest hash and typed input references. Freeze after governed acquisition/selection and before calculation. A retry uses the frozen manifest; different selections require a new request. |
| Typed selected-source references | Exact existing selected resolutions/observations, filing edition and accession, capture/batch/event IDs and quality flag IDs, period/unit/scope records, mapping/normalizer/authority/selection revisions. Retain original source URL/locator/hash/transform, numeric text and precision evidence; enforce issuer and ownership consistency. References are not unchecked arbitrary UUID strings. |
| Immutable policy/review revisions | Applicability roster, issuer/business/lifecycle/instrument assignment, effective and source-known dates, reviewer/evidence; freshness/cadence/expected filing deadline; calendar boundaries and exact reviewed selection sets; cross-edition compatibility; precision, trend and history policies. Persist typed links to retained evidence and review identity. A free-text evidence reference accepted by a synthetic pure test is insufficient production evidence. |
| Immutable calculation payload | Canonical Decimal-string/None outputs, exact Calculation and PeriodAmount operands/coefficient lineage, formulas, assessments, flags, accounting residual/tolerance, observations and coverage. Content-addressed payload can be reused only after exact dependency-key equality and digest verification. It is not a published analysis identity. |
| Immutable `analysis_snapshots` and stage outcomes | New UUID, request/execution/input-snapshot references, payload hash/reference, generation time, frozen evaluation time, engine/rule/policy versions and explicit completed/completed-with-gaps outcome. Unique published snapshot per logical request and completing execution; failed/cancelled execution cannot publish. |
| Guarded latest-result projection | Separate latest requested work from last successful compatible snapshot. Compare monotonic existing request ordering and membership generation, not completion clock. Maintain exact issuer/security/quote, basis, period and history selection key; incompatible results have different pointers. |

Source observations remain immutable facts. Reviewed policies remain assumptions
or analytical policy. Calculations and observations remain immutable conclusions.
An input manifest is not a replacement source table; the payload is not an
editable assumption store. S7 will add typed assumption-set/model-run references
through its own reviewed contract, never an unvalidated placeholder JSON field.

## Frozen input and result envelope

Proposed context fields: workspace, issuer, security and exact selected quote
identity when required; requested scope/metric roster; financial period kind and
start/end, reporting currency, accounting/consolidation/earnings basis; history
mode; inclusive filed cutoff and precise captured-before timestamp; source-known
limits; frozen evaluation date/time with declared timezone semantics. Keep source
filed date precision separate from capture instants. A date-only publication
must not be upgraded to an invented exact time.

The manifest includes every retained source reference, selected and excluded
input, source quality flag, scope/unit descriptor, precision uncertainty and
method; direct versus assembled periods, coefficients and calendar/edition
reviews; exact business-profile assignment and policy contents, not just a label.
Unknown or inapplicable inputs retain their reasons and roster position. No
currency, common earnings, debt, EBITDA, price, EPS action basis or peer data is
inferred to make the output look complete.

Proposed metric envelope: metric ID, formula and evaluation revision, Decimal
string or null, unit (fraction/multiple/currency/shares/per-share), exact operand
references, internal-source flags, projected applicability/status/reasons, source
and period dates, frozen age and optional own-history comparison. Keep source
fact status distinct from the new evaluated status. Stale valid numbers may be
retained with their dated state; they cannot drive rankings or financial labels.
A status-only update on retrieval would mutate the saved conclusion and is
prohibited. A current-age display, if later approved, must be visibly separate
from the stored evaluation.

Coverage contains the full requested applicability roster, complete valid/N/M
count, applicable count, unresolved count, per-status counts and the exact
formula/revision. Unknown applicability or zero applicable metrics gives null
coverage. Missing results cannot shrink the denominator. Observations retain rule
ID/version, exact metric-result references and policy context; review items remain
at most three distinct topics. Reconciliation failures retain actual amounts,
residuals, uncertainty and reasons; no source correction or successful valuation
claim is implied by a completed-with-gaps result.

History contains the selected 3/5/10-year window, explicit minimum, boundaries,
expected quarter ends, every eligible/excluded sample, sample-specific input
snapshots/cutoffs/policies and comparison result. Do not shorten a window or fill
missing quarters. Calendar fiscal periods and history's calendar-quarter-end
observation dates are different concepts and must remain separate fields.

## Exact cache identity versus rerun identity

Compute a canonical dependency hash from the full manifest contents relevant to
calculation, including scope/identity, all input versions and exclusions, temporal
cutoffs, frozen evaluation time, calculation build/revisions, calendar/edition/
precision reviews and applicability/freshness/history/trend/display policies.
Use deterministic UTF-8 serialization, sorted object keys and explicit ordered
arrays; reject nonfinite numbers and serialize Decimals as exact strings without
float conversion. Preserve meaningful scale/precision as explicit evidence.
Define and test canonicalization before freezing its version. Version strings
alone cannot stand in for mutable policy content.

Exclude request/execution/snapshot envelope UUIDs and generation timestamps from
the reusable calculation key. They do not change math. Include evaluation time:
aging or a changed expected-filing evaluation is a new calculation context.
Source-only acquisitions, incomplete retrieval and errors are never a valid
cached financial result. An identical payload may be referenced by multiple new
immutable snapshots after exact-key/digest checks; a changed exclusion, precision,
profile, source cutoff or engine build must miss the cache.

An explicit rerun creates a new W1 request/execution and **new snapshot UUID**,
even if its exact frozen inputs/evaluation permit payload reuse. A transport retry
of the same logical request reuses that request and may publish at most one
snapshot. Cache reuse never assigns an old snapshot ID to a new rerun. Reading
an existing snapshot by ID returns the saved payload exactly, without reselecting
facts, recalculating metrics, aging labels or changing its historical profile.

## Atomic publication and failure behavior

1. Select and freeze a consistent manifest under the existing source publication
   and PIT rules. Do not use `SKIP LOCKED` to select an inconsistent set of facts.
2. Calculate outside a long database transaction from those immutable inputs.
   Verify all supported outputs, policy lineage, evidence keys and canonical hash.
3. In one short transaction lock the existing request control/current execution;
   recheck request epoch, lease/token/expiry, cancellation and stage state. Verify
   manifest ownership and the pinned source/identity/membership generation.
4. Insert/reuse verified immutable payload, insert one request-owned snapshot,
   attach the completed stage/event, and complete the execution atomically.
   Unique constraints and idempotent exact-match replay handle a crash after commit.
5. Update the compatible latest pointer only if request ordering and membership
   generation still qualify. An older worker can never overwrite a newer result.
   Removing/re-adding a watchlist member cannot resurrect an old publication.

Failed or blocked refresh leaves the earlier dated successful snapshot reachable
separately from the newer request's failure/gaps. Never splice its numbers into
new unavailable selections, silently change result identity, or describe old data
as fresh. Existing source_bootstrap and filing_check outcomes remain their own
typed results, with no financial publication side effects. The paused D4b
schedule remains paused; connecting discoveries to financial work is a separate
reviewed deduplicated handoff.

## Candidate API behavior for review

| Candidate operation | Proposed behavior |
| --- | --- |
| `GET /companies/{issuerId}/fundamentals` | Select a compatible **saved** snapshot using explicit identity/period/basis/history selectors; response always identifies the exact snapshot/context and current request separately. It never performs a hidden acquisition or analysis. No implicit default profile/window/quote is approved here. |
| `GET /analysis-snapshots/{snapshotId}` | Return the immutable saved envelope and evidence permissions exactly. Unknown snapshot is 404; unavailable metrics within a known snapshot are null with reasons, not a fabricated 200 result. |
| Explicit analysis/rerun command | Reuse W1 request creation and its idempotency semantics; the route name, request shape and authentication are reviewed with W1/S6. Reject unresolved identity/intent instead of bypassing quote/source gates. |
| Evidence drilldown | Resolve typed authorized retained evidence from the same snapshot; no implicit current-data lookup or exposure of private operator/contact credentials. |

Review parameter conflicts (snapshot ID versus alternate selection parameters),
validation/error codes, authorization/workspace boundaries and source-retention
rights. Recommended policy: immutable-ID retrieval rejects conflicting selector
parameters; unresolvable latest selection returns an explicit no-result outcome,
not the nearest or newest incompatible snapshot. Decide the concrete envelope
and HTTP codes during review, then generate OpenAPI/TypeScript from the agreed
models and enforce regeneration/no-diff. No routes are implemented by this packet.

## Acceptance plan before publication

- Migrations on clean and upgraded stores; constraints prevent mismatched issuer,
  input/request/execution ownership, mutation and duplicate logical publications.
  Keep all applied migrations and prior capture audits intact.
- Replay exact hand-computed S5 fixtures through serialization; Decimal strings,
  fraction units, negative/zero/N/M/missing/stale and source precision round-trip
  without float conversion, default values or changed classification.
- Reproduce saved results from exact retained inputs and engine/policy revisions;
  reject edited payloads and source/period/calendar/edition mismatches.
- Change each cache dependency individually: source or capture vintage, exclusions,
  precision, business/profile revision/content, period, history mode/cutoffs,
  3/5/10 window/minimum, freshness/deadline, evaluation date and engine build.
  Every semantic change must isolate cache entries; exact matches may reuse payload.
- Explicit rerun gets new request/execution/snapshot IDs; retry gets no second
  snapshot. Inject crashes before/after transaction commit and before response.
- Exercise lease expiry, cancellation, retry epochs, out-of-order completion,
  concurrent publishers and watchlist removal/re-add. No stale worker updates
  the latest result or materializes duplicate publication.
- A restatement, policy change or later capture cannot modify old snapshot bytes.
  Historical retrieval uses original source cutoffs; no lookahead through later
  profiles/calendars/filing editions or current membership.
- Failed refresh and complete-with-gaps preserve earlier result identity/dates,
  while the new request remains visible. Stale numbers cannot generate labels.
- Coverage keeps omitted/unsupported/inapplicable/unresolved results honest;
  evidenced N/M counts as covered; zero/unknown denominator yields null coverage.
- Accounting mismatches remain evidence-bearing and cannot be hidden by recomputing
  favorable metrics. Cash/segment checks stay explicitly unsupported until scoped.
- Overview/Company/sector drilldown must select the same saved company snapshot;
  X1 still enforces method, universe and full-roster coverage gates independently.
- Golden/restatement, core, full integration, lint/typecheck and OpenAPI/generated
  client no-diff checks pass. Browser/keyboard/manual flows are required when the
  API is connected to UI; this proposal has not changed UI.
- One separately authorized real-data tracer must pass governed normalization,
  selection and evidence checks before any production figure is published. A
  synthetic snapshot test never satisfies this prerequisite.

## Review decisions and present blockers

D037 approved the narrow S6a/S6b split, status mapping, immutable input/payload/
snapshot records, canonicalization, W1 publication, exact retrieval and generated
contract. See the implementation record and S6a milestone for the resulting code
and validation. Production profile, age/deadline, history sufficiency and trend
defaults remain explicit review inputs rather than test values adopted silently.
D021/D024 and D027 retain their remaining production/profile/sector boundaries.

Real publication additionally lacks reviewed financial normalization/selection,
production fiscal/profile/precision inputs and the existing ordinary-request quote
identity gate. Approved reference-data entitlement and explicit CRCL quotation
currency remain absent; reporting USD is not proof of quote currency. No source
calls, new concepts, migrations, API routes, recurring service or publication
are authorized merely by this document's presence.
