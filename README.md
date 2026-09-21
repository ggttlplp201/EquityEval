# Equity Valuation Workbench

A local-first research tool for auditable valuation ranges and explicit
assumptions. **S3 SEC ingestion is implemented**, alongside S2 evidence storage,
historical selection and durable watchlist requests. It includes verified archives,
reviewed normalization, original-filing extraction and watchlist source stages.
See the [S3 implementation](docs/design/s3/implementation.md). The approved
S4a price/macro source layer is implemented and verified (717 tests); see its
[implementation guide](docs/design/s4/implementation.md). S5 source formulas, calendar-period assembly and history math now support the
separate X1 Sector Explorer calculation layer. A graph interface runs with clearly
fictional verification data; live sector data, durable result APIs, the full
company product and news monitoring remain later work.

Start with [milestones](docs/milestones/README.md), [P0 tasks](docs/tasks-p0.md)
and [open decisions](docs/decisions.md). Review the [S2 design](docs/design/s2/README.md)
and the [requested feature list](docs/features/README.md). The supplied [spec](docs/spec.txt),
[build guide](docs/build-guide.txt) and originals/ checksums preserve the plan.

## Setup

Requires Python 3.12, Node 22, npm, Redis binaries and PostgreSQL 16 binaries for the integration
tests. Set `EQUITY_TEST_PG_BIN` to the PostgreSQL 16 bin directory if it is not
automatically detected. Set `EQUITY_TEST_REDIS_BIN` for Redis binaries if needed. Docker with Compose v2 is an alternative runtime for the
application database/cache, separate from the disposable test cluster.
The [native application runtime guide](docs/design/application-runtime.md) describes
the separate persistent local services now available without Docker.
From this repository:

```sh
make bootstrap
test -f .env || cp .env.example .env
make test-db-setup-timescale
make check
```

Bootstrap creates .venv, installs the exact Python dependency lock and npm lock, installs
the local Python distribution in strict editable mode and the repository-local
pre-commit hook. Rerun bootstrap after adding a Python module so the editable
package links include it.
No real API credentials are required for tests. PostgreSQL 16 and Redis must already be installed. The checked-in example
contains local development database values only. Keep .env out of Git.

## Commands

| Command | Purpose |
| --- | --- |
| `make test-db-setup-timescale` | Build the pinned private PG16/Timescale test runtime |
| `make test` | Full suite, including isolated PostgreSQL constraints, PIT and queue tests |
| `make test-core` | Pure fundamentals, period, company and sector calculation regressions |
| `make test-golden` | Reviewed eight-company normalization and original-filing provenance checks |
| `make lint typecheck` | Ruff, import policy, generated-concept drift, ESLint, mypy and TypeScript |
| `make check` | All above checks |
| `make infra-config` | Validate Compose using Docker Compose |
| `make infra-up` | Start Postgres/Timescale and Redis and wait for health |
| `make infra-status` | Show service health |
| `make infra-down` | Stop services; keep named volumes |
| `make migration-history` | Inspect frozen evidence and watchlist Alembic revisions |
| `make migration-sql` | Render migration SQL without connecting |
| `make migrate` | Apply reviewed migrations; needs DATABASE_URL |
| `make app-db-start` / `app-db-migrate` / `app-db-inspect` | Start, migrate and inspect the separate native application database |
| `make app-redis-start` / `app-redis-status` | Start and inspect the persistent application rate coordinator |
| `make app-db-stop` / `app-redis-stop` | Stop owned application services while retaining data |
| `make install-hooks` | Install the required local pre-commit hook |
| `make test-db-start` / `test-db-status` / `test-db-stop` | Control only this repository's isolated PostgreSQL 16 test cluster |
| `make test-redis-start` / `test-redis-status` / `test-redis-stop` | Control only this repository's Redis test coordinator |

The planned Compose application database binds to localhost:5433; Redis binds to localhost:6380. If you change
ports/credentials, update both Compose variables and connection URLs in .env.
Application archives belong in ignored `var/raw`. Source workers require explicit configuration; no live ingestion is active.

Tests default to a separate real Timescale cluster at localhost:55433 under ignored
`var/test-postgres16-timescale`. The explicit `native-pg16` profile uses localhost:55432
under `var/test-postgres16`. See [S4 runtime setup](docs/design/s4/runtime.md).
Redis tests use localhost:16380 under ignored `var/test-redis`. Tests never use the application DATABASE_URL or .env. Each test gets a fresh
randomly named database cloned from a migrated template; cleanup drops only those
test-owned databases. The cluster stays available between test commands; stop it
with `make test-db-stop`. Tests require a real PostgreSQL 16 server and do not
silently skip database checks. See [S2 implementation](docs/design/s2/implementation.md).

## Sector Explorer development view

```sh
npm run dev --workspace @equity/web
```

Open `http://127.0.0.1:3000/development/sectors`. All values and companies are
explicitly fictional. The normal `/sectors` page lists the missing real-data
prerequisites. The [manual](docs/user-manual/sector-explorer.md) explains controls,
methods and terminology; the [milestone](docs/milestones/X1-sector-explorer.md)
records exact scope, checks and outstanding acceptance.

The checked artifact is generated by the actual pure Python calculations:

```sh
.venv/bin/python scripts/project_python.py scripts/build_sector_fixture.py
.venv/bin/python scripts/project_python.py scripts/export_sector_explorer.py var/sector-explorer-raw.json apps/web/src/features/sectors/fixture.json.gz
npm run build --workspace @equity/web
```

The deterministic gzip keeps the repository fixture small. The development page
still preloads all dated calculation/provenance views and has a large initial
payload. This verifies chart behavior without claiming production performance;
reviewed S6 snapshot retrieval will load the relevant results and evidence.
No live provider or production database is activated by these commands.

## CRCL application pipeline preview

Open `http://127.0.0.1:3101/development/pilot/pipeline` on the existing local
preview, or use `/development/pilot/pipeline` on your development server.
Links also appear in the real-data pilot and Data readiness pages.

Select a stage to inspect the pinned plan, source captures, identity review,
blocked quote registration and unstarted financial stages. Expand evidence for
public SEC links, exact capture times, source locators and hashes. The saved
September 21 application snapshot is separate from archived financial observations
and fictional demos. It contains no financial-analysis result or live actions.

See [D3e](docs/milestones/D3e-pipeline-preview.md) for verification and the
`test:pipeline` browser-test prerequisites. Check the sanitized typed fixture with:

```sh
.venv/bin/python scripts/project_python.py scripts/export_pipeline_snapshot.py --check
```

## Layout

- apps/web: Sector Explorer development graphs and real-data readiness page; full company pages remain S8.
- apps/api: thin Python API package; reviewed routes begin at S6.
- packages/core: pure financial functions after tested specifications.
- packages/ingest: SEC transport, archive verification, reviewed normalization and source stages.
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

D3f adds an **Official-source search** disclosure under Quote registration.
It explains the issuer/exchange sources checked, their date/policy limitations,
and why currency remains missing. These authored research notes are separate
from archived application captures. See [D3f](docs/milestones/D3f-quote-currency-search.md).
D4b adds a saved **Filing schedule** panel using the same design, with immutable
revision/slot evidence, UTC timing, retries and attempt budgets. One real CRCL slot
found no new filings among six scoped reports; the schedule is paused and no
background service is configured. See [D4b](docs/milestones/D4b-filing-scheduler.md)
and the [operator guide](docs/user-manual/filing-scheduler.md). Earlier checkpoint
totals remain separately labelled. Verify the current application and protected
earlier evidence (read-only, no fetch):

```sh
.venv/bin/python scripts/project_python.py -m scripts.export_scheduler_snapshot --check --verify-application
```

The canonical [operational roadmap](docs/roadmap.md) lists every non-operating capability, its dependencies and acceptance gate.
