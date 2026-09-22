# Shared vocabulary and contracts

Read root AGENTS.md and docs/spec.txt. concept_std must be one checked-in Python
enum at concepts.py with a generated TypeScript union. Its members are decided
through S1/S2 review; S0 does not invent placeholder members or domain fields.
Ask for review of schema shape, concept vocabulary, API contract and missing-data
semantics. Prepare a concrete proposal before asking. Changes happen sequentially.
At S6, generate OpenAPI from Pydantic/FastAPI and commit generated TypeScript.
Add a regeneration/no-diff CI check at that milestone; an empty S0 type module
is only workspace scaffolding and is not a reviewed API contract.

S6a is approved under D037; its versioned fundamentals contract, migration 0011
and generated OpenAPI/TypeScript are implemented. Canonical Decimal strings,
seven statuses, explicit selectors and immutable W1 result identities are fixed.
`make lint` verifies generation. S6b model contracts retain their separate review.

D038 additionally approves synthetic S6b/S7a assumptions/model/run contracts,
0012 and generated valuation API. See docs/design/s7/implementation.md. New
model or production-source scope still requires its own reviewed contract.
