# S2 implementation and validation

Date: 2026-09-12. Scope: S2a evidence storage and S2b durable requests.
The user directed implementation after the concrete S2 proposal and N1 scope
refinements. Original ZIP files remain unchanged.

## What is implemented

- The 40 reviewed concepts in `equity_schema.concepts.Concept`, generated
  TypeScript values/union, and a generation-drift check in the commit hook.
- Frozen PostgreSQL SQL migrations: `0001_evidence` and `0002_watchlist`.
  Evidence rows preserve units, scopes, periods, filings, source captures,
  mapping/normalizer revisions, missingness, candidates, flags and event history.
- Exact finite NUMERIC/Decimal values. Actual zero, source nil, absent concepts,
  ambiguous facts and unsupported scope remain distinct.
- Database-enforced publication seals, cross-entity/period/unit/scope checks,
  immutable history, least-privilege runtime grants and reviewed mapping ownership.
- Source-object retrieval-vintage preparation in `equity_schema.vintage`.
  Same-time conflicting payloads block selection; byte-identical duplicates can
  be co-referenced. Later failures remain visible alongside the last success.
- Statement selection in `equity_schema.pit` by exact period, scope, reporting
  currency, fact unit and pinned batch/capture/event/quality evidence. Newest
  missing data never falls back to an older value. Ambiguous filing order returns
  a gap. Multi-statement reads share a read-only snapshot and flag mixed editions,
  bases, scopes and currencies before a downstream calculation.
- Typed internal watchlist/queue operations in `equity_schema.workflow`.
  Adding a stock atomically creates membership, request, current-attempt state,
  execution and audit events. Explicit Refresh is a distinct intent; transport
  retries retain request identity. Workers use database time, leases and request-wide
  fencing for claim, renewal, stage completion, retries, cancellation and finish.

These are internal storage interfaces, not an S6 HTTP API or a runnable product.
The fake-worker tests do not fetch upstream data, calculate valuations or send alerts.

## Small implementation details required by the accepted behavior

- Evidence UUIDs are supplied before insertion. Atomic queue functions generate
  UUIDs inside their transaction; caller idempotency keys preserve retry identity.
  Immutable `analysis_request_keys` records keep aliases when duplicate Add clicks
  with distinct transport keys coalesce. Changed options require explicit Refresh.
- Requests persist their optional retrieval vintage and bounded attempt limit.
  They have no dangling assumption-set FK; that arrives with the actual assumption table.
- Raw observations carry a nullable semantic-scope FK; selecting a value requires
  exact scope/instrument compatibility. Unknown source context is not empty context.
- Batches record input and output hashes. Querying conflicting outputs for identical
  pinned inputs/revisions reports nondeterministic normalization.
- Filing events and their affected scopes commit together. An explicit creation
  transaction identity prevents later additions to an event's scope set.
- Original quote identifiers remain immutable. A guarded current-validity projection
  and source-backed closure record allow a previously open ticker interval to close
  before another issuer uses that symbol. Closure cannot alter the original
  symbol, issuer, currency, start date or capture. Fresh requests use current validity;
  archived requests continue to reference the original quote identity.
- Revision-graph writes require READ COMMITTED because their advisory-lock checks
  need current visibility. PIT reads deliberately use REPEATABLE READ. GiST exclusion
  remains the final interval collision guard for concurrent ticker operations.
- Frozen SQL revisions are authoritative; Alembic does not autogenerate from live
  application metadata. Upgrade/downgrade/re-upgrade is checked against actual
  PostgreSQL catalog signatures, including constraints, indexes, triggers and grants.

## Using and checking this layer

Run from the canonical iCloud repository. Install PostgreSQL 16 binaries first;
`EQUITY_TEST_PG_BIN` can point to their directory. The helper also detects common
Homebrew/Linux locations and refuses another PostgreSQL major version.

```sh
make bootstrap
make test-db-start
make check
make test-db-stop
```

`make test` starts the isolated cluster if needed. Data is under ignored
`var/test-postgres16`; its private socket uses a short path under /tmp because the
iCloud path exceeds the macOS socket-length limit. Port 55432 binds locally.
The helper verifies cluster ownership, server version and data-directory identity.
Each test clones a migrated template into its own random database. Only those
session-created test databases are dropped. Test code never reads the application's
DATABASE_URL or .env, never contacts upstream providers, and does not skip a missing
PostgreSQL runtime. A stopped helper can be started again without touching any
existing PostgreSQL 18 service/database.

Strict editable installation exposes the repository's aliased Python package names
to imports and mypy. Re-run bootstrap after adding modules. The empty-suite exception
now applies only to tests/core; financial arithmetic begins in S5/S7.

Executable examples are the tests: `test_pit.py` seeds exact KHC rows and performs
historical reads; `test_vintage.py` prepares source manifests; `test_workflow.py`
adds a stock, runs fake stages, retries and preserves earlier intent. These avoid
presenting developer helpers as finished user-facing product instructions.

## Validation evidence

The required full check is run before checkpointing and again by the commit hook.
The milestone record reports the final test count and exact checkpoint. Tests include:

- KHC FY2017 parent income: original 10,999,000,000 USD and revised 10,941,000,000
  USD, with exact archived JSON rows, locators and payload hash. Consolidated income
  is checked separately. The May 2019 public non-reliance event blocks the original
  without using the earlier private determination date; replacement does not
  rehabilitate that original. The fixture's event annotation is explicitly hand-reviewed.
- No 2018 captured history from a 2026 retrieval; no capture before completion;
  competing same-day filings, unknown current currency, missing newest concepts,
  source revisions, authority policies, USD/share versus USD and cross-family coherence.
- Finite decimal round-trip, NULL-aware period uniqueness, missingness flags,
  row/child-set immutability, runtime permissions and concurrent revision-cycle prevention.
- Atomic Add rollback, concurrent Add/retry, idempotency option conflicts, lease
  expiry, cancellation, source-error archive rejection, retry limits, stage audit
  atomicity and listing closure/reuse.
- Real PostgreSQL upgrade/base-downgrade/re-upgrade schema parity and concept
  consistency across Python, TypeScript and the database CHECK constraint.

## Remaining milestone boundaries

S3 must freeze the Source/RawRecord/Fact/archiving contract and implement tested SEC
adapters. A database capture record validates metadata integrity; the archive writer
must verify actual bytes before publishing that metadata. The current tests use
archived S1 evidence or explicitly fictional constraint fixtures, not a live parser.

Input preparation must collect and pin the relevant reviewed filing-event and
additional quality-flag IDs; a caller-chosen manifest is not a claim of exhaustive
coverage. Observed source facts are distinct from agent interpretation. S4 adds
prices, macro vintages and ongoing corporate-action/ADS-ratio lifecycle handling;
security active-state management is not yet exposed. Snapshot persistence and
valuation calculations arrive with their engines; an in-memory S2 selection is
not a saved valuation model run.

S6/S8 adds API and UI. W1's real full-analysis pipeline requires those source and
engine stages. N1 continuous news discovery, assessments and three alert channels
remain specified but not running. U1's user manual will be verified against the
finished interface. No email recipient has been enrolled and no source credentials
were changed by this milestone.
