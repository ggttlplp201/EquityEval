# API

Read root AGENTS.md and docs/spec.txt. Keep this layer thin: validate reviewed
request/response types, orchestrate services, delegate valuation to equity_core.
Do not perform financial math here or import yfinance. Preserve provenance,
missing-data flags, point-in-time selection and immutable model-run history.
Prepare API contract changes for review in S6. S0 defines no domain routes.

D037 approves the S6a read-only fundamentals endpoints and generated contract.
Use the explicit workspace-bound app factory; no implicit database/listener/auth
configuration. No mutation route, real publication or valuation model is included.
See docs/api-contract.md and docs/design/s6/implementation.md.

D038 adds a separate trusted-local synthetic valuation app: immutable assumption
creation, enqueue-only requests, safe polling and exact saved runs. It does not
calculate inside HTTP handlers or activate providers. Generated contract checks
cover both app factories; see docs/design/s7/implementation.md.
