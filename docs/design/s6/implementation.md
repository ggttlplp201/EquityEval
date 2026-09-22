# Approved S6a implementation record

Baseline `bd40e6a`, `milestone/s5c-engine-handoff`. D037 records the user's
“move on” approval relayed by the milestone coordinator on 2026-09-22.

S6a/S6b split approved. S6a preserves the seven S5 evaluated statuses exactly,
explicit compatible selectors and complete versioned policy contents. No profile,
quote, basis, period, history window, age or trend default is inferred. Unknown
snapshot or no exact compatible latest result is typed 404. S6b/S7 keeps DCF,
assumptions, valuation ranges and unresolved D004/D005; no placeholder model rows.

Only migration 0011 may be added; 0001–0010 and all existing evidence stay intact.
Immutable input manifests, typed source FKs, content-addressed verified payloads,
request-owned snapshots and exact latest pointers reuse W1 fencing and ordering.
Publication is atomic; calculation occurs outside that transaction. Explicit
reruns get new snapshot IDs even when identical payloads are reused. Retries
cannot publish twice; failures and stale workers cannot replace successful data.

Canonicalization v1 is deterministic UTF-8 JSON with sorted keys, ordered arrays,
exact Decimal strings and no floats/nonfinite values. Semantic input/policy/time
contents and engine revision are hashed; request/execution/generation envelope
identity is excluded from reuse. Snapshot reads return the original saved result.

Implementation uses an owner-reviewed manifest approval for governed fixture
publication, typed relational source links and exact database-backed selection
validation at owner review. The owner computes and pins an expected payload digest;
this private fixture review does not publish a result. The worker independently
calculates from frozen request inputs before the SQL writer checks that digest. The first tracer is synthetic and visibly
labelled throughout. There is no real-publication approval or implicit promotion
of CRCL captures to normalized financial evidence. No providers or recurring
services are activated. Read-only API is workspace-bound and exposes only the
sanitized public projection, never the private input manifest or archive paths.

Required acceptance: adversarial schema/immutability and downgrade guards;
canonicalization/cache isolation; crash/retry/concurrency/lease/membership/order;
no-lookahead and saved status/coverage; generated OpenAPI/TypeScript no-diff;
read-only API isolation. Full/core/golden/lint/type/build checks and independent
final audit precede the milestone commit/tag. Existing UI stays as accepted.


The immutable request intent is declared by `enqueue_fundamentals`, a narrow W1
wrapper, before work is claimed. It advances latest-request state even when work
fails before freeze. Latest successful snapshot remains separately reachable.
Writer connections explicitly require idle autocommit; numerical work holds no
transaction. API read transactions are read-only and workspace-bound.

The complete selected history window is requested work. A missing history
comparison, a nonvalid metric, or a requested unresolved/failed accounting or trend
result produces `completed_with_gaps`. Empty optional accounting/trend inputs are
not requested work. Seven metric statuses retain their independent S5 meanings.

History compares complete profile/freshness contents in addition to identity,
metric, units, period/history basis, formula and engine revision. Revisions alone
cannot certify policy equivalence. Public evidence preserves source tags, actual
retrieval times, scope and exact operand coefficients; arbitrary private source
transform metadata is hashed, with only identity-decimal operation exposed.

See [S6a milestone](../../milestones/S6a-fundamentals-publication.md) and
[manual](../../user-manual/saved-fundamentals.md) for validation and operation.

Exact replay uses the original stored canonical payload, without re-running an
engine that may have changed since commit. First publication still requires the
pinned build. Envelope generation timestamps normalize to UTC for stable reads
across database session timezones.
