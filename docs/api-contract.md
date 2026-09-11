# API contract status

**Not defined — review milestone S6.** S0 has no API routes, Pydantic domain
models, OpenAPI artifact, or generated domain types. The schema TypeScript
module is only a compileable workspace reservation. Do not treat it as a contract.

At S6: review P0 endpoints, provenance for filing and non-filing sources, units,
missing values, errors, point-in-time selection, immutable run inputs and DCF
output semantics. Generate OpenAPI and TS types and enforce regeneration/no-diff
in CI. Cover DCF inputs/results before freezing even though S7 implements its math.
