# Equity Valuation Workbench

A local-first research tool for auditable valuation ranges and explicit
assumptions. **S2 evidence storage, historical selection and durable watchlist requests are implemented.**
The database/storage layer has real PostgreSQL tests; live ingestion, financial
engines and the product interface remain later milestones.

Start with [milestones](docs/milestones/README.md), [P0 tasks](docs/tasks-p0.md)
and [open decisions](docs/decisions.md). Review the [S2 design](docs/design/s2/README.md)
and the [requested feature list](docs/features/README.md). The supplied [spec](docs/spec.txt),
[build guide](docs/build-guide.txt) and originals/ checksums preserve the plan.

## Setup

Requires Python 3.12, Node 22, npm and PostgreSQL 16 binaries for the integration
tests. Set `EQUITY_TEST_PG_BIN` to the PostgreSQL 16 bin directory if it is not
automatically detected. Docker with Compose v2 is an alternative runtime for the
planned application database/cache, separate from the disposable test cluster.
From this repository:

```sh
make bootstrap
test -f .env || cp .env.example .env
make check
```

Bootstrap creates .venv, installs the exact Python dependency lock and npm lock, installs
the local Python distribution in strict editable mode and the repository-local
pre-commit hook. Rerun bootstrap after adding a Python module so the editable
package links include it.
No real API credentials are required for tests. PostgreSQL 16 must already be installed. The checked-in example
contains local development database values only. Keep .env out of Git.

## Commands

| Command | Purpose |
| --- | --- |
| `make test` | Full suite, including isolated PostgreSQL constraints, PIT and queue tests |
| `make test-core` | Valuation suite; still intentionally empty until S5/S7 |
| `make test-golden` | Exact archived KHC observation/provenance checks; adapters arrive in S3 |
| `make lint typecheck` | Ruff, import policy, generated-concept drift, ESLint, mypy and TypeScript |
| `make check` | All above checks |
| `make infra-config` | Validate Compose using Docker Compose |
| `make infra-up` | Start Postgres/Timescale and Redis and wait for health |
| `make infra-status` | Show service health |
| `make infra-down` | Stop services; keep named volumes |
| `make migration-history` | Inspect frozen evidence and watchlist Alembic revisions |
| `make migration-sql` | Render migration SQL without connecting |
| `make migrate` | Apply reviewed migrations; needs DATABASE_URL |
| `make install-hooks` | Install the required local pre-commit hook |
| `make test-db-start` / `test-db-status` / `test-db-stop` | Control only this repository's isolated PostgreSQL 16 test cluster |

The planned Compose application database binds to localhost:5433; Redis binds to localhost:6380. If you change
ports/credentials, update both Compose variables and connection URLs in .env.
Raw payloads will go in ignored var/raw; source adapters arrive after review.

Tests use a separate cluster at localhost:55432 under ignored `var/test-postgres16`.
They never use the application DATABASE_URL or .env. Each test gets a fresh
randomly named database cloned from a migrated template; cleanup drops only those
test-owned databases. The cluster stays available between test commands; stop it
with `make test-db-stop`. Tests require a real PostgreSQL 16 server and do not
silently skip database checks. See [S2 implementation](docs/design/s2/implementation.md).

## Layout

- apps/web: Next.js configuration and dependencies; pages begin at S8.
- apps/api: thin Python API package; reviewed routes begin at S6.
- packages/core: pure financial functions after tested specifications.
- packages/ingest: source adapters after normalization and contract review.
- packages/schema: reviewed concepts, generated TS, typed PIT/vintage/queue storage operations.
- infra: local services, migration environment and worker reservation.
- tests/golden and tests/integration: source evidence, database and workflow verification.
- tests/core: financial calculation fixtures and invariants from S5/S7.
- docs: originals, decisions, milestone records, licence register and handoffs.

`equity_core`, `equity_ingest`, `equity_schema`, and `equity_api` are the Python
import names, installed from the directories above.

## Correctness and workflow

Follow AGENTS.md. Missing financial values remain NULL with quality flags.
Preserve point-in-time facts and provenance. Valuation lives only in pure Python;
the frontend renders API values. Review schema, concept vocabulary and API
contracts before implementation. Keep one named milestone per task and record
its decisions, checks, limitations and commit. No upstream data is fetched by CI.

An S0 suite can be empty only while it has a .allow-empty-s0 marker and no test
files. Remove the marker with its first tests. Failing tests, collection errors
and accidental deselection always fail. CI's future OpenAPI drift check is
explicitly deferred to S6; see [contract status](docs/api-contract.md).
