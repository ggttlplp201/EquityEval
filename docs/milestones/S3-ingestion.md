# S3 — SEC ingestion

Status: Source-contract review and evidence checkpoint; adapter implementation pending
Date: 2026-09-12 (Asia/Shanghai)
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: codex/s3-source-contract
Dependency: S2 `dae3e6e`, tag `milestone/s2`
Checkpoint tag: `milestone/s3-contract-review`

## User direction and current boundary

After S2 was completed, the user instructed “continue.” Progression to S3 is
accepted. D008 remains a source-contract review gate, as required by
[ingestion instructions](../../packages/ingest/AGENTS.md): “Every provider implements
the reviewed Source protocol. Freeze the shared raw-record, fact, provenance and
rate-limit semantics before S3.” The concrete contract was not previously presented.

This checkpoint completes the reviewable proposal and source-evidence preparation.
It does not treat progression as approval of an unseen protocol or new tables.
Production adapters and proposed migration `0003_source_ingestion` are not implemented.

## Concrete review packet

[Source contract S3-01–04](../design/s3/source-contract.md) specifies:

- Resolved resource requests, complete raw archive references, explicit outcomes
  and a typed normalization bundle matching the existing S2 evidence model.
- Pinned filing inventory, scope, authority and public-event evidence. Newer
  unresolved coverage gets blocking flags; old eligible facts cannot pose as a
  usable current statement.
- One shared SEC rate coordinator, complete archive verification before parse,
  bounded dispatch/retry policies, honest 304 reuse and incomplete-download handling.
- Three additive tables: source-policy revisions, transport attempts and immutable
  capture-policy links. Existing complete-capture/financial constraints remain intact.

[Acceptance plan](../design/s3/test-plan.md) specifies transport/concurrency,
publication, full normalized golden tests and original-filing extraction boundaries.

## Evidence prepared

`tests/golden/s3_review_cases.json` pins eight existing S1 Company Facts archives,
28 exact audited observations and seven scoped gap cases. Each observation retains
its exact raw row, JSON pointer, numeric lexical text and Decimal expectation;
capture references retain the full archived-body hash. No archive is duplicated.

The cases cover total/component revenue, corporate cash versus reserves, reported
zero versus missing data, parent/consolidated losses, share dates/classes, banking
basis, stale/absent API facts, IFRS units and the KHC restatement. The evidence
checks discovered CRCL's raw CIK is a padded string; other cohort captures use
numbers. The contract now preserves either representation and validates canonical
identity without accepting booleans, fractional values or another issuer.

These are executable acceptance-evidence checks, not full normalized statements.
The eight-by-40 concept outcomes still require specific reviewed mapping/coverage
fixtures before production numeric normalization. Existing S1 filing spot checks
and S2 PIT regressions remain the reference evidence.

## Review and validation

Two independent reviews examined transport/storage and financial selection.
Corrections cover shared budgets, completed versus interrupted 200s, policy links,
stale leases, request validators, exact hash bytes, event/inventory completeness,
unknown authority, duplicate-candidate representation and retrieval-vintage identity.

The focused evidence suite passes 44 tests. The combined run passes **168 tests**,
plus Ruff/import policy, generated-concept drift, ESLint, strict mypy and TypeScript.
The golden suite also passes separately with 45 tests. The mandatory commit hook
repeats `make lint typecheck test test-core test-golden`. Financial engine core tests
remain intentionally empty. Tests make no upstream requests. All 36 local Markdown
links resolve and `git diff --check` passes.

Official SEC API/access/security/time/reuse references were rechecked for the
proposal. Local timeout/body-size/retry limits are labeled app choices. No new
provider account, paid service, credential, monitoring schedule or email delivery
was configured. The existing contact configuration was not changed or printed.

## Next handoff

Obtain review of S3-01–04, then implement in order:

1. S3a archive/transport, policy/attempt persistence and rate coordination tests.
2. S3b Company Facts/Submissions normalization through S2 persistence and PIT,
   with complete reviewed cohort golden fixtures and explicit unsupported gaps.
3. S3c context-aware original-filing extraction and its own numeric/context tests.
4. W1 integration of live source stages, preserving queue/retry/history semantics.

N1 continuous discovery and three alert channels, valuation engines, UI and U1's
verified manual remain in the recorded later milestones. S3 success must not be
reported as a finished valuation or an active news monitor.
