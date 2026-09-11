# ADR 0001: S0 workspace and tooling

Date: 2026-09-11. Status: adopted within the user's authorized scaffold scope.

The canonical code directory is
`/Users/leon/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval`.
Its parent Development directory is already a repository, so equityEval has an
independent `.git` directory to keep staging, hooks and commits local.

Keep the SPEC Section 1.1 layout. One Python distribution maps equity_api,
equity_core, equity_ingest and equity_schema onto the specified directories.
npm workspaces connect apps/web and the reserved generated-types package.
Python dependencies use an exact pip-tools lock; JavaScript uses package-lock.
No financial enum, table, route or valuation contract is chosen here.

Use Alembic with no revisions or target metadata until S2. Docker Compose provides
PostgreSQL 16/TimescaleDB and Redis on loopback ports 5433/6380 to avoid common
local defaults. Database data stays in named Docker volumes; raw payloads belong
in ignored var/raw once ingestion exists. A worker is reserved until S3/S4.

Retain Next.js 15 as specified. The locked patch is 15.5.25 (verified in npm), newer than the
15.5.24 maintenance patch named by the official August 2026 release note:
https://nextjs.org/blog/august-2026-security-release
Dependency resolution will be recorded in lockfiles; no app server runs in S0.

Tool references checked during setup:
- https://alembic.sqlalchemy.org/en/latest/tutorial.html
- https://docs.pytest.org/en/stable/reference/exit-codes.html

An empty test suite is labeled explicitly and accepted only for the exact S0
suite targets carrying .allow-empty-s0 and no test files. Genuine failures,
collection errors, mistyped paths and filtered-out tests stay failures. Remove
a suite's marker when its first real tests land.

The Next.js 15 dependency tree pins an older PostCSS release. npm audit found
source-map disclosure advisories; the root override uses PostCSS 8.5.28 within
the same major. Re-audit after installation and verify a real Next build at S8.
This S0 workspace has no UI build to exercise yet.
