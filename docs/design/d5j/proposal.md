# D5j — Real source-only fundamentals publication contract

Status: **approved for narrow implementation** after independent standards/spec
review and coordinator confirmation of the user’s “continue until finished”
authorization. D048 records this explicit contract boundary. Baseline is pushed D5i
`f42222682892e8602b884e5aaf64c44af9b85d63`; the application has two real normalization
batches/four facts and zero real financial metrics. This proposal commit changes documentation only; subsequent implementation must
follow the exact reviewed shape. No concept, missingness, provider or quote scope
expansion is approved.

## Problem and proved prerequisite

D5i published immutable batch `b49859b5-9f27-455a-87a4-e6fe776f5314` through existing
S3. Independent standards/specification/numeric review and live replay/readback
prove the exact FY2025 revenue and operating-income inputs eligible at the fresh
2026-10-15T21:59:05.195192Z observation. All prior rows and historical D5a blockers
remain unchanged. See [D5i](../../milestones/D5i-crcl-observation.md) and its pinned
[publication audit](../../research/crcl-observation-publication-2026-10-15.json).
This is a bounded historical annual source snapshot at that knowledge cutoff,
not a claim of latest-quarter coverage or eligibility after that observation.

The existing real-publication path cannot represent it honestly:

| Existing contract | Concrete blocker |
| --- | --- |
| `packages/schema/fundamentals.py`, `SelectionKey` | `quote_identifier_id` is a required UUID. No reviewed CRCL exchange quote exists. |
| Same file, `InputManifest` and `FundamentalsPayload` | `evidence_mode` permits only `synthetic`, with a fixed synthetic fixture label. Real inputs cannot use that label. |
| `infra/migrations/versions/0011_fundamentals_publication.py` | Input-review quote ID is NOT NULL with a security-identifier FK; input/result version and evidence-mode checks enforce the synthetic contract. |
| `fundamentals_enqueue` in 0011 and `packages/schema/workflow.py` | Existing ordinary request bindings pass and require quote identity. A source-bootstrap request is not an authorized financial-publication request. |
| `packages/schema/openapi/fundamentals.json` and generated TS | The public API exposes the same required quote/synthetic types. A frontend-only bypass would contradict stored and generated contracts. |

`packages/schema/AGENTS.md` requires a concrete proposal and review of shared
schema/API shape and states that new production-source scope requires its own
reviewed contract. D037 approved synthetic S6a only. Reporting USD is not exchange
quote currency; no quote or synthetic fixture identity may be fabricated.

## Proposed narrow contract change

The following names/shapes are review targets, not implemented alternatives.
Preserve v1 synthetic contracts, all saved synthetic snapshots and existing valuation
readers exactly. Add explicit `s6-input-v2` / `s6-fundamentals-v2` real-source types
with `evidence_mode: "real"` and no synthetic fixture label. Do not relax the v1
literal to a generic string or reinterpret old records under new semantics.

The new selector has `selection_kind: "issuer_fundamentals"`, issuer and security
IDs, annual period start/end, reporting basis/currency, exact history mode/filed
cutoff/captured-before, frozen evaluation date/time, profile/freshness/history/trend
policy revisions and content hash, history years and engine revision. It has no
quote field. Reporting currency is explicitly a statement unit. Quoted/price-based
selectors, cross-version valuation consumption and quote registration are excluded.
The new `/v2/real-fundamentals` endpoints specified below accept only this
selector; there is no response union with the existing synthetic endpoints.

Reuse existing typed FinancialInput/StatementSelection, Calculation, period,
precision and source lineage responsibilities. The real reviewed manifest must
validate every batch/resolution/observation/capture against storage, exact issuer,
period, consolidation scope, unit, edition, source locator/hash/time and selected
quality flags. Bind the D5i preparation hashes and all required reviewed evidence;
free-text proof references alone are insufficient. Policy evidence links must resolve
to retained capture IDs/hashes/locators and a dated review record. Preserve direct
versus derived operand lineage; do not copy source values into unchecked literals.

Keep the seven existing public statuses and Decimal-string/null semantics. Unknown
applicability and unavailable operands retain their requested roster slots/reasons;
do not shrink coverage to the one supported ratio. No new concept_std member or
missing-data meaning is proposed. Existing formulas remain in `packages/core`.

## W1 and storage boundary

Add a narrow reviewed source-fundamentals request intent on the existing W1 queue,
with workspace/issuer/security/review identity, explicit idempotency key and parent
request. It has no quote or watchlist membership. Preserve current quoted request
requirements. Do not reuse bootstrap/monitor intent, invent a membership, or add a
parallel queue. SQL must enforce the discriminator and null quote/membership only
for this specific reviewed intent; all other request kinds retain their constraints.

Use a new sequential additive migration after current head 0012 (0013 if still next).
**Choose companion real tables**, preserving every 0011 synthetic table/constraint,
writer and reader. The new records below use UUID primary keys unless specified;
all immutable records reject update/delete/truncate. No polymorphic foreign keys.

| Added table | Keys and mandatory relations/invariants |
| --- | --- |
| `real_fundamentals_policy_reviews` | ID, issuer FK, canonical policy text/hash UNIQUE, reviewer/reason/reviewed_at, effective/known dates; owns the exact profile/freshness/history/trend bundle. |
| `real_fundamentals_policy_evidence` | PK `(policy_review_id,evidence_index)`; FK to policy review and retained `source_captures`; locator/hash must match retained source. |
| `real_fundamentals_input_reviews` | ID; workspace/issuer/security FKs; policy-review FK; canonical manifest/hash UNIQUE per workspace, compatibility text/hash, expected payload hash, reviewer/reason/time. SQL requires v2/real/issuer_fundamentals and forbids quote keys and fixture_label. Security must belong to issuer. |
| `real_fundamentals_review_inputs` | PK `(review_id,input_index)`; FK to real review and existing periods/units/semantic_scopes/mapping_revisions; selection hash plus normalized resolution/batch/observation bindings validated against their existing FKs and stored selection. |
| `real_fundamentals_review_captures` | PK `(review_id,capture_id)`; FK to real review and source_captures; exact hash/time, no unbound or missing captures compared with manifest. |
| `real_fundamentals_review_history` | PK `(review_id,sample_index)`; FK to real review and real snapshot, exact payload hash/quarter end; no synthetic history can satisfy it. Initially empty, so history remains missing. |
| `real_fundamentals_request_intents` | `request_id` PK/FK to existing analysis_requests; `review_id` FK to real input review; immutable, one intent per request. Deferred constraint requires every real-kind request to have exactly one matching intent before commit. |
| `real_fundamentals_input_snapshots` | ID; request FK UNIQUE; creating execution/request composite FK to analysis_executions; review FK; UNIQUE `(id,request_id,review_id)`; frozen review must equal request intent. |
| `real_fundamentals_calculation_payloads` | `payload_hash` PK, `dependency_hash` UNIQUE, canonical payload text/time; SQL checks canonical hash, v2/real/issuer_fundamentals and no quote/fixture fields. |
| `real_fundamentals_snapshots` | ID; request FK UNIQUE; execution UNIQUE with execution/request composite FK; input snapshot UNIQUE with input/request/review composite FK; payload-hash FK, review FK, stage FK, lease identity, outcome and generated_at. Only a fenced real writer creates it. |
| `latest_real_fundamentals` | PK `(workspace_id,issuer_id,security_id,compatibility_hash)`; FKs to workspace/issuer/security, latest request and optional real snapshot; request/snapshot monotonic sequence fields with snapshot sequence <= latest-request sequence. No membership/scope or synthetic snapshot FK. |

Re-use `fundamentals_canonical` / `fundamentals_hash` from 0011, not new arithmetic
or canonicalization. Compatibility is the hash of the canonical complete real
selector plus explicit `s6-fundamentals-v2`/real discriminators. The selector pins
observation, policy content and engine; each different dependency has a separate
latest key. Real and synthetic namespaces are separate even if financial dates
match. Payload hash and reviewed expected output must match before publication.

The migration extends only the existing W1 trigger/shape constraints to add
`real_fundamentals`. Its quote, membership, bootstrap_plan, filing_monitor_plan and
all market-plan/source/window fields must be NULL; retrieval_vintage equals the
reviewed captured_before. An optional parent request must be real-kind in the same
workspace/security. Existing bootstrap/monitor and quoted shapes remain unchanged.
Add these exact entry points and guards:

- `real_fundamentals_enqueue(workspace,review,key,parent,max_attempts)` validates the
  reviewed manifest/policies and atomically creates the ordinary W1 request, existing
  request-key/execution/state/event records, real intent and latest-request pointer.
  It uses existing idempotency/fencing primitives, not `workflow_enqueue_bootstrap`.
- `workflow_claim_real_fundamentals(worker,seconds,request)` claims only that kind
  with the existing row lock/epoch/token rules. Extend the existing generic claim
  routing to exclude real-kind jobs from quoted/bootstrap/monitor workers; no new
  queue/state machine. Existing retry/heartbeat/cancel infrastructure remains.
- `real_fundamentals_freeze(lease,stage,review)` checks exact intent, current execution,
  epoch/token/lease and immutable review before creating/reusing the real input.
- `real_fundamentals_publish(lease,stage,input,payload)` validates current lease and
  success stage, intent/input/review equality, canonical expected output and no
  changed dependencies; creates one real snapshot per logical request and updates
  only the matching latest-real key using request sequence, never completion time.
- Real stage/intent/success guards reject unreviewed intents, source acquisition,
  quoted or valuation stages and terminal success without the required snapshot.
  Runtime privileges permit these narrow writers only; direct table writes remain
  denied. Existing synthetic functions and their grants remain unchanged.

The real publication functions must independently enforce issuer/workspace/period/
source/policy ownership and all composite links; Python validation alone is not a
substitute. Disposable tests cover every constraint and cross-kind request attack.
The implementation must supply exact SQL/Pydantic changes for review before apply;
this design chooses the relational responsibilities rather than leaving an alternate
v1-table extension open.

## Chosen public API and generated-client compatibility

Add a separate trusted-local read-only router with **two new endpoints**, no union
or replacement of existing `/analysis-snapshots` and `/companies/.../fundamentals`:

- `GET /v2/real-fundamentals/snapshots/{snapshot_id}`: UUID path; no query selectors.
- `GET /v2/companies/{issuer_id}/real-fundamentals`: required `security_id` UUID and
  `compatibility_key` SHA-256 query fields only. No default/partial selector, quote,
  scope or workspace parameter. The exact complete selector lives in the snapshot;
  its key is obtained from the reviewed request, never guessed by the browser.

The workspace is bound by trusted-local application composition as in v1. Reject
unknown query fields with 422. Both routes use read-only DB transactions; latest
uses repeatable read. A v1/synthetic snapshot ID is absent from this namespace and
returns 404. A v2 snapshot cannot be consumed through a v1 endpoint.

`RealSnapshotResponse` contains snapshot_id, request_id, execution_id,
input_snapshot_id, generated_at, compatibility_key, payload_hash, existing
completed/completed_with_gaps outcome and `result: RealFundamentalsPayload` with
version `s6-fundamentals-v2`, evidence_mode real and the exact source-only selector.
`RealLatestResponse` contains that snapshot plus latest_request_id and the existing
W1 latest_request_state enum, keeping work status distinct from saved success.

404 uses `RealNoResult {code: snapshot_not_found | no_compatible_snapshot,
message: "N/A"}` with no financial values. No compatible completed snapshot returns
404 even if work exists; a previous compatible success may accompany a newer work
state. Reuse these existing meanings, not new missingness statuses. Invalid or
corrupt stored real payloads fail closed; do not return an unverified success.

Generate a **separate** `packages/schema/openapi/real_fundamentals.json` and
`packages/schema/types/real-fundamentals.ts` from the new models/router. Existing
fundamentals and valuation generated files must remain byte-identical. Add separate
regeneration/no-diff checks and v1 compatibility tests. The development analysis UI
uses the explicit new client only after reviewed real publication; it renders core
outputs/provenance and performs no financial arithmetic. No public write endpoints,
provider activation, scheduler, ordinary watchlist flow or external deployment.

## First production policy and numerical scope

Only CRCL FY2025 descriptive reported operating margin is eligible for a candidate:
existing `packages/core/metrics.py::operating_margin` divides selected operating
income by selected total revenue, including reserve income. Keep the loss sign,
source thousands scale, original inline precision and consolidated annual context.
Do not adjust IPO compensation, substitute net income, infer recurring earnings,
apply generic technology thresholds or describe token-holder reserves as issuer
cash. D5c's stablecoin/distribution-economics profile supplies the reviewed rationale;
convert its proof links to typed retained evidence and pin a new real policy revision.

Retain the existing full metric applicability roster: operating margin supported,
other metrics unresolved with their exact missing accounting/scope requirements.
No other metric, financial-strength label, buy/sell signal, valuation, trend or sector
conclusion is authorized. Three-year history is the proposed explicit initial
history request; absent eligible historical snapshots remain missing, never inferred
from statement comparisons. Keep accounting identity checks unavailable with exact
missing operands rather than treating absent assets/liabilities/equity as a pass.

Before a future numeric publication, separately pin concrete policy content and the
frozen evaluation instant. Proposed freshness policy is annual-historical-only:
365-day maximum age from the selected period end, no inferred expected-quarter
or filing deadline, and an explicit label that the request is FY2025 rather than
latest-period analysis. The age threshold is a reviewable analytical policy, not a
source fact. Preserve a stale classification if actual evaluation fails the accepted
policy; never widen it to force valid. The existing status engine evaluates this
policy. Observation-time and evaluation-time remain distinct; advancing the source
cutoff would require a new governed observation and review, outside this packet.

## Required red-first proof before any real metric

1. Reject real evidence in v1 and synthetic evidence in v2; unknown versions and
   ambiguous selectors fail closed. Old synthetic serialization/readback unchanged.
2. Reject fabricated/mismatched quote, issuer, security, capture, filing, unit,
   period, edition, precision, policy reference and changed reviewed hashes. Reject
   unsupported post-observation completeness or source-known lookahead.
3. Hand-computed small signed margin examples, zero/negative/missing denominator,
   scale/sign mistakes and swapped operands; independent plausible-but-wrong review
   of the actual candidate and all operand precision before live publication.
4. Prove the new W1 source-only intent cannot enter quoted/valuation paths; stale
   lease, cancellation, forged review, duplicate/concurrent publication, retry,
   generation/late completion and exact replay preserve prior results.
5. Verify full roster/status/coverage and missing accounting/history behavior;
   stale annual results cannot produce current rankings or financial labels.
6. Disposable migration upgrade/constraints/readback and rollback where supported;
   synthetic v1 API compatibility; regenerated schema no-diff checks; full make
   check/build; desktop/mobile/keyboard provenance and corrupt-artifact recovery;
   local GET-only browser requests. No frontend finance math.
7. Pin concrete manifest/input/output/policy hashes for independent standards,
   specification and numeric pre-publication review. Only after approval publish
   once, replay and verify application rows, immutable history and real provenance.

## Decision and stopping point

D5i completes the bounded acquisition/reconciliation/current-normalization chain.
The shared-contract design is now approved; implementation and its independent
SQL/Pydantic/API review remain required before migration application. This proposal
does not claim D5j implemented or publish a numerical operating margin. The next
action is the approved contract implementation, followed by a separately pinned
and independently reviewed real numeric candidate before live publication.
Broader S4 rights/quote/price/action work, broader S5 fundamentals, S7 valuation,
sector coverage, recurring operation and product integration remain separate phases.
