# API

Read root AGENTS.md and docs/spec.txt. Keep this layer thin: validate reviewed
request/response types, orchestrate services, delegate valuation to equity_core.
Do not perform financial math here or import yfinance. Preserve provenance,
missing-data flags, point-in-time selection and immutable model-run history.
Prepare API contract changes for review in S6. S0 defines no domain routes.
