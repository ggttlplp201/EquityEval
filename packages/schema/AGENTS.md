# Shared vocabulary and contracts

Read root AGENTS.md and docs/spec.txt. concept_std must be one checked-in Python
enum at concepts.py with a generated TypeScript union. Its members are decided
through S1/S2 review; S0 does not invent placeholder members or domain fields.
Ask for review of schema shape, concept vocabulary, API contract and missing-data
semantics. Prepare a concrete proposal before asking. Changes happen sequentially.
At S6, generate OpenAPI from Pydantic/FastAPI and commit generated TypeScript.
Add a regeneration/no-diff CI check at that milestone; an empty S0 type module
is only workspace scaffolding and is not a reviewed API contract.
