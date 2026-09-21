# D3a — Separate application storage and first-capture prerequisite

Status: runtime implemented and verified; bootstrap contract review pending.
Date: 2026-09-21.
Branch: `codex/crcl-source-snapshot`.
Baseline: `53cbdb0`, `milestone/d2-observed-pilot`.
Recovery target: `milestone/d3a-application-runtime`.
Dependencies: D2, accepted S2/W1 and S3 contracts; existing pinned PG16/Timescale build.

## Scope and artifacts

Restore persistent application PostgreSQL and the shared rate coordinator, inspect
actual state before domain writes, and identify the next real-source prerequisite.
Preserve the redesigned UI, seven-company roster, 3/5/10-year options and all
original source timestamps. No financial calculations or shared contracts changed.

- `scripts/app_postgres.py`: separate local PG16.14/Timescale2.28.1 cluster;
  owner-only migration path and least-privilege application login.
- `scripts/app_redis.py`: separately owned persistent application Redis; AOF,
  synchronous persistence, no eviction, startup readiness and identity checks.
- `tests/test_application_runtime.py`: guards against test/remote targets,
  foreign ownership, redirected paths and unsafe Redis configurations.
- Makefile application lifecycle commands and [runtime guide](../design/application-runtime.md).
- [Concrete first-capture proposal](../design/s3/identity-bootstrap-proposal.md).

## Findings and review boundary

The new application database successfully applied existing migrations through
`0005_market_data_hypertables`. Initial inspection found no existing policy,
issuer, security, mapping, capture or normalization rows. The runtime role has no
superuser/create-role/create-DB/replication/RLS-bypass attributes and cannot directly
insert into source captures, policies or analysis requests.

A genuine S3 fetch requires a W1 request, whose quote identifier requires an earlier
source capture. The older S1 manifests lack request/completion timestamps, so they
cannot honestly bootstrap that identity. D031 proposes a bounded source-only W1
request variant; it is not silently activated. The root and schema AGENTS require
concrete review before changing shared request shape. This is a new cold-start
contract issue, not repeat approval for the accepted S3 pipeline.

No policy or financial rows were inserted, no SEC request sent, no fake identifiers
or captures created, and no inventory/event flags cleared. S5 and S6 remain open.

## Validation

- Seventeen targeted runtime isolation/configuration tests pass.
- PostgreSQL migration rerun and actual extension version verified.
- Actual application login verified with restricted permissions.
- PostgreSQL stop/start retained the same cluster system identifier.
- Redis repeated stop/start retained a unique smoke value in AOF; only that smoke
  key was removed. Shared rate-limit state was never flushed.
- Redis daemon-readiness and TIME_WAIT startup failures were reproduced and fixed.
- Lint and Python/TypeScript types pass (55 Python source files).
- Initial full run: 986 passed; one child-process import failed due to the
  previously documented macOS/iCloud hidden editable-pointer recurrence. The
  retry explicitly inherits only the validated project editable build path; no
  test is skipped and no schema/type output changed.
- Final full suite: **987 passed** (123.78 seconds); core: **225 passed**;
  golden: **110 passed**. The mandatory pre-commit hook repeats these gates.
- No UI/API/numeric behavior changed; D2's reviewed browser/source checks remain
  the existing UI checkpoint, not a claim that live financial data is connected.

## Next handoff

Review D031's exact bootstrap request proposal, then implement/test it sequentially
before fresh SEC evidence acquisition. Continue S3 publication and real PIT/core
eligibility checks; finish the eligible S5 slice, then the immutable S6 contract.
Do not bypass the dependency with test seeds, inferred timestamps or direct HTTP.
