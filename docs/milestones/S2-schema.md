# S2 — Schema and point-in-time layer

Status: design prepared — schema review pending; implementation not started
Date: 2026-09-12 (Asia/Shanghai)
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: codex/s2-schema-design
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

## Review performed

Independent reviews challenged PIT and workflow failure cases. The proposal was
refined to address same-day/source-version ambiguity, statement authority,
request-wide retry fencing, atomic state/event changes, parent/membership/quote
consistency, deferred assumption FKs and withdrawn-original eligibility.

Required scaffold lint/typechecks/test harness run at the documentation checkpoint.
No database or financial behavior tests have been executed for S2 yet; their
expected outcomes are documented. No migration, SQL schema, concept enum or
worker was implemented. Docker remains absent; a psql executable alone does not
prove a compatible isolated database is available.

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

## Handoff

Review decisions S2-01 through S2-05. After approval, implement S2a evidence
storage and the KHC regression first, then S2b durable watchlist/request storage.
Resolve an isolated PostgreSQL runtime before claiming database validation.
Later W1/N1/U1 implementation follows the dependencies in the feature register.
