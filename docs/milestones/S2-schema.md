# S2 — Schema and point-in-time layer

Status: Complete for accepted S2a/S2b storage and durable-request scope
Date: 2026-09-12 (Asia/Shanghai)
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: codex/s2-schema-design
Checkpoint tag: milestone/s2
Dependency: S1 evidence commit 5746e7d, review tag milestone/s1-review
User direction: move to S2; add manual/terminology and watchlist-triggered full analysis.

## Acceptance and scope

The user accepted progression from the S1 proposal to S2. Record D007/D011 as
accepted direction; this does not approve an unseen schema. W1 and U1 are added
to the feature list alongside N1. The supplied AGENTS.md requires schema shape
and missing-data representation to be reviewed before implementation.

This checkpoint contains a concrete [S2 proposal](../design/s2/schema-proposal.md)
with five review decisions, table fields, keys, foreign-key/immutability rules,
source version and historical selection policies, durable watchlist requests,
and later engine/news storage requirements. The [test plan](../design/s2/test-plan.md)
pins real KHC expected values and adversarial SQL/concurrency behavior before code.

## Important design choices

- Issuers, traded instruments and quote identity stay distinct.
- Source observations and normalized resolutions are separate, preserving raw
  competing facts and explicit missing/conflicting results.
- Historical filing-date reconstruction and retrieval vintage are independent;
  saved analyses pin exact normalization batches and input evidence.
- Original non-reliable statements remain flagged even after replacement.
- Watchlist membership and queued work commit together. Logical-request fencing
  prevents duplicate publication across retry attempts.
- Completed snapshots/model runs are immutable; latest-result pointers and job
  progress are separate. Manual and glossary use the same domain meanings.

## Earlier design-checkpoint review

Independent reviews challenged PIT and workflow failure cases. The proposal was
refined to address same-day/source-version ambiguity, statement authority,
request-wide retry fencing, atomic state/event changes, parent/membership/quote
consistency, deferred assumption FKs and withdrawn-original eligibility.

At the earlier documentation checkpoint, scaffold lint/typechecks/test harness
checks ran, but no S2 database or financial behavior tests had been executed.
Expected outcomes were documented; migrations, SQL schema, concept enum and
worker were not yet implemented. Docker was absent and the isolated PostgreSQL
runtime had not yet been established. The implemented checkpoint below supersedes
that earlier status.

## N1 refinement — 2026-09-12

D017 records the user's request for per-stock competitor, product, regulatory and
ecosystem monitoring with evidence and conditional verdicts. Their Reap link
resolved Open USD as Open Standard's stablecoin. Added
[stock-topic requirements](../features/N1-stock-topic-monitoring.md), a sourced
[CRCL example](../features/N1-crcl-topic-example.md), later S2 contracts and
acceptance cases. W1 now builds the topic profile/baseline on stock addition;
U1 teaches topic controls and assessment interpretation. The source register and
domain glossary include these requirements.

Independent review checked identities, legislative stages, measurement meaning,
relevance vintages, conflicting/syndicated evidence and alert deduplication. The
review added persistent topic exclusions, send-time relevance checks and a shared
development/revision/purpose notification identity across macro/topic producers.
Open Standard and Circle primary sources support topic identity; the retrieved
Congress page was cached, so the example makes no current legal-status claim.
This is a documentation checkpoint; S2-01–05 remain pending and monitoring is
not running. Required scaffold checks run through the commit hook; no N1
behavior or database tests are claimed by this refinement.

## Continuous discovery clarification — 2026-09-12

D018 records that the CRCL topics are examples. N1 must continuously scan news
sites and announcements for new relevant developments across all active watchlist
stocks. Added broad discovery beyond known aliases/topics, automatic relevance
and assessment updates, collection outside market hours, visible source cadence
and lag, and restart/late-index recovery. Added acceptance cases requiring discovery
of a previously unknown topic without user entry or an open company page. The
feature register, CRCL example and manual requirements reflect this clarification.
Independent review added fair scheduling, discovery/assessment backlog and completed
coverage tracking so successful polling cannot hide stalled assessments.
This is a requirements checkpoint; monitoring is not activated by documenting it.

## Implementation authorization — 2026-09-12

After the S2 proposal and N1 refinements, the user instructed “continue with the
next part.” This is accepted as direction to implement the presented S2-01–05
recommendations. Earlier sections describe the state at their own checkpoints.
The current slice implements S2a then S2b; later source/API/N1 contracts remain
subject to their own milestones. No live monitoring or alerts are activated.

## Implemented checkpoint

See [implementation details](../design/s2/implementation.md) for the actual modules,
frozen migrations, workflow operations, test runtime and remaining boundaries.
The final required commit-hook run passes **124 tests**, Ruff/import policy,
generated-concept drift, ESLint, strict mypy and TypeScript checks. The original
KHC amounts, non-reliance behavior, source vintages, unknown/missing states,
immutable records, concurrent queue behavior and migration round trips run on
PostgreSQL 16. The golden source check also passes separately. The core calculation
suite remains intentionally empty; no valuation test is claimed.

Validation command: `make lint typecheck test test-core test-golden`. All 44 local
links in changed Markdown files resolve; `git diff --check` passes. Resolve the
checkpoint commit with `git show --no-patch milestone/s2`.

Independent reviews found and corrected unverified acceptance ordering, source-role
vintage conflicts, missing pinned event validation, reporting-currency/measurement-unit
conflation, additional blocking quality flags, changed-options duplicate Add, archived
HTTP-error reuse, fixed-snapshot revision-cycle writes, and ticker interval retirement.
A final migration-isolation regression proves explicit test URLs bypass both .env
loading and the application DATABASE_URL, including during a fresh upgrade.

Environment: Homebrew PostgreSQL 16.14 binaries were installed. Homebrew's default
cluster post-install step failed, so the repo helper initializes and manages its own
isolated cluster. A ca-certificates dependency was updated by Homebrew. Existing PG18
services/databases and application .env were not changed. Strict editable installation
and py.typed markers make aliased package imports visible to tests and mypy.

## Handoff

S3 begins with the concrete Source/RawRecord/Fact/archiving contract review (D008),
then the SEC adapter and full-company golden normalization fixtures. S2 storage and
internal operations are in place; no external API or Source contract is silently
frozen by them. Prices/macros, engines, persistent model snapshots, product UI,
continuous news monitoring and the verified user manual follow their recorded
milestones. Use the original archives and S1 evidence; never fill a missing fact
with a guess or a prior period's value.
