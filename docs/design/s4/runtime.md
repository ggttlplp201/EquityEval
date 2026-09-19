# S4 database test runtime

Verified locally 2026-09-16. This is test infrastructure, not an application
migration or a production deployment.

## Explicit profiles

| Profile | Port | Test migration target | Runtime |
| --- | --- | --- | --- |
| `native-pg16` | 55432 | `0004_market_data_contract` | Existing isolated PostgreSQL 16 helper |
| `timescale-pg16` (default) | 55433 | `head` / required `0005` | Private PostgreSQL 16.14 + TimescaleDB 2.28.1 |

`EQUITY_TEST_DB_PROFILE` selects the profile. Invalid values fail. The full suite
never falls back from Timescale to native PostgreSQL. Pytest reports the selected
profile and target. Native relational checks are useful but do not satisfy the
S4 hypertable acceptance gate. The same contract tests run in both CI jobs;
only the explicit Timescale-specific smoke test is skipped in the native job.

The helper reads no application `.env` or `DATABASE_URL`. Each test database has
an unpredictable `equity_test_` name, is created by that test session and is
removed afterward. Runtime start/stop checks the data directory, owner record,
server major version and dedicated loopback port before controlling the server.
The Timescale profile additionally verifies its exact available extension version
and required preload. A failed full-head migration remains a test failure.

## Local setup and commands

Docker, Podman and Colima were unavailable on the development host. No container
engine or global Timescale installation was added. Instead, the explicit setup
command builds pinned official source archives in a repository-keyed directory
under `~/.cache/equityeval/` and writes a private installation reference under the
ignored `var/test-postgres16-timescale/` runtime directory.

```sh
.venv/bin/python scripts/project_python.py scripts/setup_test_timescale.py
.venv/bin/python scripts/project_python.py scripts/test_postgres.py start --profile timescale-pg16
.venv/bin/python scripts/project_python.py -m pytest tests/integration/test_database_runtime.py
make check

# Separate, narrower relational verification:
EQUITY_TEST_DB_PROFILE=native-pg16 make test

.venv/bin/python scripts/project_python.py scripts/test_postgres.py stop --profile timescale-pg16
.venv/bin/python scripts/project_python.py scripts/test_postgres.py stop --profile native-pg16
```

Setup requires a C compiler, Make and Python with venv/pip. It installs CMake
3.31.10 into its private build-tools venv; the project's runtime dependency lock
is unchanged. `--jobs` defaults to at most four compilation processes. Repeated
successful setup reuses the recorded installation, and no package purchase,
application database, shell profile or login service is involved. Build logs are
kept in the private cache. An explicitly provided
`EQUITY_TEST_TIMESCALE_PG_BIN` may select another PG16 installation, but the exact
Timescale version and isolated runtime checks still apply.

This private build disables TLS, ICU, readline and zlib to minimize test-only
system dependencies, and compiles Timescale telemetry out. The server also sets
`timescaledb.telemetry_level=off`. It binds only loopback and uses a dedicated
owner-only data directory with local trust authentication. It is **not a
production database distribution**. PostgreSQL's `btree_gist` extension is built
for the existing evidence constraints. Source and build paths avoid spaces
because the upstream build tools do not reliably support them; the user-visible
repository and test data retain their canonical iCloud paths.

## Pinned evidence and checks

| Artifact | Version / SHA-256 |
| --- | --- |
| PostgreSQL source | 16.14 / `f6d077142737920858ce958ccdb75c6ee137a63b5b0853c70693d401ac7e3471` |
| Timescale source | 2.28.1 / `ae582d545b1364d7df0deeba862161c021d9df82e9bb281f7f57ddaa686a6a44` |
| Compose image | `timescale/timescaledb:2.28.1-pg16@sha256:fdce0a44280da4168ed8e2251f91f813c1e5df9c1c117e16ab7e3bbdbedfca11` |

The PostgreSQL archive digest matched its official adjacent checksum file.
The Timescale release archive is pinned by its observed digest; its release is
[2.28.1](https://github.com/timescale/timescaledb/releases/tag/2.28.1).
The release's source version checks explicitly support PostgreSQL 16. Official
[source-build guidance](https://docs.timescale.com/self-hosted/latest/install/installation-source/)
describes a PostgreSQL development installation, C compiler and CMake, and warns
about the reverted PostgreSQL 16.5 ABI; this build uses 16.14.

The Compose digest was read from the official
[Docker Hub tag metadata](https://hub.docker.com/v2/repositories/timescale/timescaledb/tags/2.28.1-pg16).
Its manifest includes Linux amd64 and arm64. Compose now pins the same extension
release. The image was not pulled or executed locally; local acceptance uses the
actual source-built PostgreSQL/Timescale runtime. Hosted CI results remain
unobserved until the workflow runs.

Local runtime smoke verification passed actual `CREATE EXTENSION`, exact
`pg_extension.extversion`, one-year date hypertable creation, catalog presence,
incoming regular-table-to-hypertable FKs, outgoing hypertable-to-regular-table
FKs, unique date-inclusive keys, and absence of retention/compression policies.
Three independent helper regressions cover profile isolation, unowned data
rejection and symlink rejection. These establish runtime capability; the S4
migration and market-data contract suites separately establish application
behavior.
