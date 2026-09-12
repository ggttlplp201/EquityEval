# Verification suites

`make test` runs vocabulary/generation checks, archived KHC evidence checks and
actual PostgreSQL 16 integration tests. Database tests start the repo-owned isolated
cluster and create disposable databases; no upstream calls or application .env.
See [setup](../README.md) and [S2 implementation](../docs/design/s2/implementation.md).

The core financial calculation suite remains explicitly empty until S5/S7.
Only tests/core retains its S0 empty-suite marker. Collection errors and unexpected
empty suites fail; no database test is silently skipped.
