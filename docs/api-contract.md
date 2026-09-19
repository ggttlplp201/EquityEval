# API contract status

**Public HTTP API not defined — review milestone S6.** No API routes or OpenAPI
artifact are implemented. S2 includes reviewed internal storage interfaces and a
generated TypeScript financial-concept union; these are not an HTTP API contract.
The separate [S3 source protocol](design/s3/source-contract.md) is implemented
under D008. The [S4 provider extension](design/s4/source-contract.md) is implemented
under accepted D019. Neither freezes S6 endpoints.

At S6: review P0 endpoints, provenance for filing and non-filing sources, units,
missing values, errors, point-in-time selection, immutable run inputs and DCF
output semantics. Generate OpenAPI and TS types and enforce regeneration/no-diff
in CI. Cover DCF inputs/results before freezing even though S7 implements its math.

## F1 fundamentals proposal for S6

The [F1 integration plan](features/F1-fundamentals-guide.md) adds a candidate
`GET /companies/{issuerId}/fundamentals` projection and immutable snapshot
retrieval. These are proposals, not existing routes or an approved API. D021
tracks the outstanding review; use S5's tested definitions as inputs to S6.

Review identity mapping (`instrumentId` versus security/quote), financial period,
accounting/earnings basis, inclusive filing cutoff, capture timestamp, source-known
limits and a frozen evaluation timestamp. Include selected **3/5/10-year history
window**, sample policy and excluded sample metadata. Return Decimal strings,
units/fractions, typed evidence references, formula/rule versions, coverage and
reasons for valid, N/M, missing, invalid, stale or unsupported results. Preserve
underlying source statuses/NULLs rather than replacing storage semantics.

Integrate fundamentals results with the analysis input/snapshot persistence
already deferred from S2; do not create duplicate source or snapshot models.
Cache identity must include every selection field, input manifest, mapping/
normalizer/selection revisions and rule, freshness, applicability, precision,
comparison and display-sensitivity policy versions. Snapshot retrieval returns
the saved evaluation, not newly aged labels. Each explicit W1 rerun creates a new request/execution and a new immutable
analysis snapshot ID even if its F1 calculation payload is reusable. Linking a
new execution only to an old analysis snapshot does not satisfy W1. Retries
within the same logical request must not publish duplicate snapshots.

Review guarded publication/latest-result pointers, restart/retry behavior and
failed refresh: show the prior dated snapshot separately, never substitute its
values into a newer unavailable selection. Carry market observation dates with
composite evidence keys. Only after sequential review should migrations, public
models, OpenAPI and generated TS be implemented.
