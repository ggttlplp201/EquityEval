# Equity Valuation Workbench

A local-first research tool for auditable valuation ranges and explicit
assumptions. **S1 research complete; concept review before S2.** There is no runnable product
or financial implementation yet.

Start with [milestones](docs/milestones/README.md), [P0 tasks](docs/tasks-p0.md)
and [open decisions](docs/decisions.md). Review the [S1 packet](docs/research/s1/review-brief.md)
and the requested [news/macro agent](docs/features/N1-news-and-macro-agent.md). The supplied [spec](docs/spec.txt),
[build guide](docs/build-guide.txt) and originals/ checksums preserve the plan.

## Setup

Requires Python 3.12, Node 22 and npm. Docker with Compose v2 is additionally
required to run the local database/cache. From this repository:

```sh
make bootstrap
cp .env.example .env
make check
```

Bootstrap creates .venv, installs the exact Python dependency lock and npm lock, installs
the local Python distribution and the repository-local pre-commit hook.
No global packages or real API credentials are required. The checked-in example
contains local development database values only. Keep .env out of Git.

## Commands

| Command | Purpose |
| --- | --- |
| `make test` | Full pytest suite; explicitly empty in S0 |
| `make test-core` | Valuation tests; explicitly empty in S0 |
| `make test-golden` | Normalization fixtures; explicitly empty in S0 |
| `make lint typecheck` | Ruff, import policy, ESLint, mypy and TypeScript |
| `make check` | All above checks |
| `make infra-config` | Validate Compose using Docker Compose |
| `make infra-up` | Start Postgres/Timescale and Redis and wait for health |
| `make infra-status` | Show service health |
| `make infra-down` | Stop services; keep named volumes |
| `make migration-history` | Inspect Alembic revisions; none in S0 |
| `make migration-sql` | Render migration SQL without connecting |
| `make migrate` | Apply reviewed migrations; needs DATABASE_URL |
| `make install-hooks` | Install the required local pre-commit hook |

Database binds to localhost:5433; Redis binds to localhost:6380. If you change
ports/credentials, update both Compose variables and connection URLs in .env.
Raw payloads will go in ignored var/raw; source adapters arrive after review.

## Layout

- apps/web: Next.js configuration and dependencies; pages begin at S8.
- apps/api: thin Python API package; reviewed routes begin at S6.
- packages/core: pure financial functions after tested specifications.
- packages/ingest: source adapters after normalization and contract review.
- packages/schema: reviewed shared vocabulary and generated types.
- infra: local services, migration environment and worker reservation.
- tests/core, tests/golden, tests/integration: future verification suites.
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
