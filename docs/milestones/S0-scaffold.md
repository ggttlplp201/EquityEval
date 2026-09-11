# S0 — Scaffold

Status: complete — scaffold verified; Docker runtime validation pending
Date: 2026-09-11 (Asia/Shanghai)
Task: S0 — EquityEval scaffold and milestones
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: codex/s0-scaffold
Commit checkpoint: local Git tag `milestone/s0` on the S0 completion commit
Sources: SPEC 1.1/11/12; BUILD_GUIDE 4.2/5 S0/7.2/10.

## Scope

Repository, original documents, instructions, dependency management, local
infrastructure, migration environment, verification harness, CI and milestone
records. Financial implementation begins in later reviewed milestones.

## Artifacts

Root README/AGENTS, nested guidelines, apps/web + apps/api, packages/core +
ingest + schema, infra/compose.yaml, Alembic environment, scripts, Makefile,
CI workflow, docs/tasks-p0.md, docs/decisions.md and source checksums.

## Validation evidence

Verified 2026-09-11 16:51 CST. No business tests exist in S0.

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Original document integrity | Passed | SHA-256 manifest matches all three originals; working spec and guide are byte-identical. |
| `make bootstrap` | Passed | Exact Python lock, npm ci, editable Python package, local hook installation. |
| `make check` | Passed | Ruff lint/format, import policy, ESLint, strict mypy (8 Python files), both TypeScript workspaces, full/core/golden harness targets. |
| S0 test targets | Passed with zero tests | Every target explicitly reports that no behavioral tests ran. |
| Test-runner behavior probes | 7 passed | Empty marked suite with pytest addopts; real failure; deselection; collection error; missing path; real success; empty unmarked suite. |
| Import-policy probes | 8 passed | Direct/from imports, dynamic imports, aliases and a safe control. |
| `npm audit` | Passed | Zero reported vulnerabilities after PostCSS override; npm ci also reports zero. |
| `pip check` | Passed | No broken requirements. |
| Python package imports | Passed | equity_api, equity_core, equity_ingest and equity_schema. |
| `make migration-history` | Passed | Empty migration history, intentionally. |
| `make migration-sql` | Passed | PostgreSQL dialect renders BEGIN/COMMIT offline with configured DATABASE_URL. |
| Compose static inspection | Passed | YAML loads; service names, digest pins, loopback bindings and init-script path checked. |
| `make infra-config` | Not verified | Docker executable absent; command fails with `docker: No such file or directory`. |
| Live services / DB migration execution | Not run | Requires Docker; static parsing and offline SQL do not establish runtime correctness. |
| Hosted CI | Not run | Workflow is checked in; repository has no remote and has not been pushed. |

Independent scaffold review found an import-module alias gap, now fixed.
Runtime verification found that pytest mutates its argument list; the wrapper
now passes a copy, and its failure/empty-suite behaviors were rechecked.

Python locking uses exact versions including SQLAlchemy's platform-dependent
greenlet dependency. Hash generation was dropped because the resolver downloaded
wheels for unrelated platforms. Docker images and npm packages retain content
hashes through the Compose digest pins and npm lockfile.

## Limitations

Docker CLI/engine were not found on this machine at initial inspection. Live
Postgres/Timescale/Redis startup and database migrations are therefore unverified.
There are no migration revisions, API contracts, numerical functions or UI yet.
No upstream financial data has been fetched and no API credentials are needed.

## Handoff

Next milestone is S1: prepare an evidence-backed concept-map proposal across
6–8 companies. A real SEC contact User-Agent is required before upstream access.
Read docs/decisions.md, especially vocabulary review and P0 scope conflicts.
