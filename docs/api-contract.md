# API contract status

**Public HTTP API not defined — review milestone S6.** No API routes or OpenAPI
artifact are implemented. S2 includes reviewed internal storage interfaces and a
generated TypeScript financial-concept union; these are not an HTTP API contract.
The separate [S3 source protocol](design/s3/source-contract.md) is implemented
under D008. The [S4 provider extension](design/s4/source-contract.md) is proposed
for review. Neither freezes S6 endpoints.

At S6: review P0 endpoints, provenance for filing and non-filing sources, units,
missing values, errors, point-in-time selection, immutable run inputs and DCF
output semantics. Generate OpenAPI and TS types and enforce regeneration/no-diff
in CI. Cover DCF inputs/results before freezing even though S7 implements its math.
