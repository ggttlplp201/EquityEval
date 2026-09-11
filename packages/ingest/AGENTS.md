# Ingestion

Read root AGENTS.md and docs/spec.txt. Every provider implements the reviewed
Source protocol. Freeze the shared raw-record, fact, provenance and rate-limit
semantics before S3; adding adapters must not alter the engine.
Archive raw payloads before parsing. SEC requests require a real contact in
User-Agent and a maximum 10 requests/second, including parallel requests.
Normalize only approved concept_std values and reviewed company overrides.
Missing values remain NULL and raise a quality flag. Never import yfinance.
Keep unit, period, filing, retrieval and transformation evidence. Record provider
terms before ingestion. Use pinned fixtures and `make test-golden` before commit.
S0 has no source adapters or upstream calls.
