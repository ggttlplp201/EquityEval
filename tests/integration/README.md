# PostgreSQL integration tests

Tests use PostgreSQL 16, frozen Alembic migrations and separate runtime-role
connections. Each test clones an isolated migrated template. They cover evidence
integrity, the real KHC historical selection, source vintages, statement ambiguity,
missingness, watchlist/idempotency/lease concurrency and migration round trips.

`tests/conftest.py` never uses application DATABASE_URL/.env. The runtime helper
controls only its owned cluster, and test cleanup drops only newly created
`equity_test_*` databases. No upstream HTTP calls or real notifications occur.
