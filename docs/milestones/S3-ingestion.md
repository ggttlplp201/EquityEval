# S3 — SEC ingestion

Status: complete for the accepted S3 ingestion and W1 source-stage scope
Date: 2026-09-12 (Asia/Shanghai)
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: codex/s3-ingestion
Dependency: S2 `dae3e6e`, tag `milestone/s2`
Review checkpoint: `df99735`, tag `milestone/s3-contract-review`
Completion checkpoint: `milestone/s3`

## Authorization and traceability

The user instructed “implement” after the concrete S3 contract review. D008 and
S3-01–04 were accepted; the three additive tables and the presented source
semantics are within that authorization. The earlier proposal/evidence checkpoint
remains unchanged in Git. Original ZIP documents remain unchanged.

Read the [implementation record](../design/s3/implementation.md) for module
boundaries, internal worker usage, test commands and limits. The
[accepted contract](../design/s3/source-contract.md) and
[acceptance plan](../design/s3/test-plan.md) link the intended behavior to this work.

## Delivered

- Verified immutable gzip archives; bounded SEC transport; shared Redis rate and
  cooldown enforcement; source-policy links and durable fenced attempt storage.
- Company Facts and Submissions parsing; all 320 requested concept outcomes across
  the eight-company S1 cohort; explicit gaps and exact scope/unit/vintage evidence.
- Idempotent normalization publication through real S2 database constraints and
  historical selection, preserving original/revised KHC values and provenance.
- Strict context-aware Inline XBRL extraction, original-filing spot checks,
  separate ordinary/ADS scopes and explicit unsupported/malformed cases.
- W1 source-stage integration: add/rerun requests, bounded retries, cancellation,
  reviewed mapping gaps and durable archived run manifests. Manifest association
  and normalization publication commit atomically.
- Versioned [data/history manual chapter](../user-manual/data-and-history.md),
  updated feature status and CI dependencies for PostgreSQL/Redis tests.

## Verification

`make check` passes: **440 tests**, Ruff/import policy, generated-concept drift,
ESLint, strict mypy and TypeScript. The separate golden run passes **108 tests**,
including the eight-by-40 expected outcomes and original-filing checks. The required
pre-commit hook repeats lint, type checks and all three test commands; it is not bypassed.
Documentation link checks cover 43 local references with no broken links, and
`git diff --check` passes. Tests use
archived SEC evidence or explicitly fictional HTTP/policy/event fixtures. No live
SEC requests were made. The KHC event-selection integration uses a clearly marked
annotation fixture because the actual event document is not in the S1 archive;
it does not claim automatic event extraction or complete original history.

Independent numeric and storage reviews produced regressions for changed scope
labels, period/rule reuse, duplicate inventory rows, incomplete history bounds,
ignored context text, cross-issuer/instrument writes, stale lease reuse, lost
manifest links, retry-budget exhaustion and overstated source licence settings.
Capture-vintage preparation now includes new S3 attempts and unknown outcomes in
the same snapshot as archived captures. Existing S2 partial/304 fixtures now
seed at their actual old migration before upgrade; assertions remain unchanged.

The financial core suite remains intentionally empty until S5/S7. Local checks
do not claim that hosted CI, a production service or an end-user UI was exercised.

## Environment changes

Environment preparation installed Redis 8.8.1 binaries for an isolated local test
coordinator. Homebrew also updated OpenSSL to 3.6.3 and ran its automatic cleanup
of older formula versions and download caches. No launch-at-login service was
enabled; test helpers own only their dedicated local runtimes. Runtime HTTP/Redis/XML
dependencies are pinned in the Python lock. Existing contact configuration is unchanged.

## Remaining boundaries and next handoff

No live worker, schedule, email delivery or news monitor was activated. Mapping
rules apply only to reviewed accessions/periods; newly archived issuers need
reviewed mappings. Event discovery and complete historical event coverage remain
separate work. Parser corrections that alter immutable S2 intrinsic observations
fail explicitly and need a later reviewed versioning change.

Next milestone: S4 Tiingo prices and FRED. Resolve its source/account permissions,
dated observations and macro-vintage policy (D009) before financial inputs are
used. S5 ratios/accounting checks, S6 API, S7 valuation and S8 interface follow.
W1's full pipeline, N1 continuous macro/stock-specific discovery with three alert
channels, and U1's finished manual remain required for the release.
