# S3 implementation

The user approved D008 and S3-01–04 with “implement” after checkpoint
`df99735` (`milestone/s3-contract-review`). Implementation is on
`codex/s3-ingestion`; the completion checkpoint is `milestone/s3`.

## Implemented boundary

`packages/ingest/contracts.py` defines resolved SEC resources, immutable capture
references, fetch outcomes and the Source protocol. `SecSource` combines the SEC
transport with local archive verification and reviewed Company Facts normalization.
Parsing and normalization perform no database or network operations.

The transport archives complete decoded entity bytes before parsing, hashes and
counts them, and retains real HTTP status separately from body completion. Shared
Redis coordination covers all SEC hosts/workers, with a conservative five-request
per-second target, a rolling ten-request hard ceiling, expiring permits, bounded
retries, validated redirects, Retry-After and shared access cooldowns. Coordination
failure prevents dispatch. Replay and 304 reuse preserve original capture identity
and time. Failed transfers never become complete successful captures.

Migration `0003_source_ingestion` adds the three accepted tables: source policy
revisions, fetch attempts and capture-policy links. Policies and terminal attempts
are immutable; live attempts require the current watchlist worker lease. Runtime
capture insertion uses the narrow fenced functions. Existing S2 financial tables
and migrations remain frozen. Legacy capture policy status stays explicit; new normalization publication requires a
reviewed capture-policy link. Descriptor licence/redistribution claims must match
the pinned database policy.

The reviewed normalizer preserves numeric lexical text, Decimal values, exact
period/unit/accession, semantic scope, candidate decisions and quality flags.
The eight-company golden fixture specifies all 320 requested outcomes, including
missing and unsupported outcomes. Rules bind their approved issuer, accession,
period, scope content, instrument and accounting basis. The writer also verifies
the registered security kind, so an ADS identifier cannot label ordinary shares.
No missing line is synthesized or replaced with zero.

Capture-vintage preparation reads captures and the new attempt log in one database
snapshot. It preserves failed attempt IDs, distinguishes unresolved outcomes at a
historical cutoff, and retains the original body/time on a 304 validation.
`CaptureManifest.attempt_ids` also retains unresolved attempts known at the cutoff;
`NormalizationInput.attempt_ids` accepts finalized attempts only. A future adapter
between these manifests must retain unknown-outcome warnings and references
without blindly copying all attempt IDs into a published normalization input.

Submissions parsing follows only the same issuer's advertised history documents.
Missing chunks, duplicate accessions and conflicting metadata prevent a complete
inventory claim. API inventory completeness is separate from event coverage and
original-filing history. Original-history completeness requires independently
reviewed evidence through the assessment date, starting no later than each
requested period end and relevant filing date.

The separate Inline XBRL reader validates archived bytes, entity/context, explicit
and typed dimensions, unit measures, numeric transformation, sign and scale. It
uses strict XML parsing with no DTD or external access. Selection needs an explicit
qualified tag, context, unit and expected dimensions. Unsupported transformations,
malformed structures or conflicting duplicates stay gaps. KHC's non-XHTML note is
an explicit unsupported extraction case. The reader does not automatically fill
Company Facts gaps or choose custom accounting mappings.

## Watchlist source stages

`run_source_stages` accepts an already claimed W1 request, a resolved `SourcePlan`,
a configured `SecSource`, an archive and a reviewed input-builder callback. It:

1. Checks issuer identity, requested periods, filed cutoff and retrieval vintage.
2. Fetches Company Facts, Submissions, bounded advertised history and planned
   original documents through durable stages.
3. Gives the reviewed builder the exact capture references, inventory and gaps.
   Unknown mappings stop with `waiting_for_input` after preserving source evidence.
4. Verifies every pinned archive, normalizes, and archives a complete manifest of
   inputs, financial evidence, request policy, fetch results and known gaps.
5. Publishes the immutable batch and stage-to-manifest reference in one transaction.
   A crash immediately after commit cannot detach the batch from its manifest.
6. Records valuation as unsupported at this milestone and finishes with
   `completed_with_gaps`. Deferred/transient access retries use W1's durable budget;
   exhaustion returns `failed`. Cancellation and expired leases reject late writes.

Explicit reruns create new requests and capture vintages, leaving earlier batches
and manifests intact. Identical pinned normalization inputs reuse a published
batch. This implements W1's SEC source stages; stock search, UI, prices/macros,
ratios, valuation assumptions, model snapshots and news delivery remain later work.

## Running and inspecting

Use Python 3.12 and the locked dependencies, PostgreSQL 16, and Redis binaries.
`make bootstrap` refreshes strict editable package links. `make check` exercises the
complete local suite with simulated HTTP and archived evidence. No credentials or
upstream network calls are needed for these tests. The helpers own only the
repository's PostgreSQL port 55432 and Redis port 16380:

```sh
make test-db-status test-redis-status
make test-golden
.venv/bin/python -m pytest -q tests/integration/test_source_pipeline.py
make test-db-stop test-redis-stop
```

Application integration imports `SecSource`, `SecTransport`, `LocalArchive`,
`RedisRateLimiter`, `DatabaseAttemptStore` and `run_source_stages`. Callers provide a
reviewed policy revision already stored in PostgreSQL, an explicit contact email,
one shared Redis limiter key for all SEC workers, a resolved issuer/security and a
reviewed mapping plan. A `None` replay argument requests fresh source HTTP; a tuple
requests archive-only replay. A pinned retrieval vintage always requires replay.
This is a typed internal worker interface, not a public API or a background daemon.
No source is activated merely by importing these modules.

Completed normalization stages store batch ID plus manifest blob key/hash/count
in their immutable audit reason. The manifest contains capture, event and external
quality-flag IDs as well as input/output hashes. Read archives only through hash
verification. `PublishedBatch.additional_quality_flag_ids` holds the separately
pinned flags for PIT queries; batch-generated flags are selected through the batch
and period, not indiscriminately applied to every period.

## Verification and limits

Focused tests cover real PostgreSQL constraints and permissions, multiple Redis
processes, interrupted and conditional HTTP, all reviewed cohort outcomes, original
filing spot checks, stale leases, cross-issuer/instrument rejection, idempotent
publication, reruns, retries and crash recovery. Independent reviews added
regressions for plausible wrong scopes, incomplete history, ignored dimension text
and lost manifest associations. The milestone record contains the final check totals.

The historical source fixture is a dated evidence cohort, not current market data.
Mappings apply only to their reviewed accessions and periods. New stocks/filings
can be archived, but need reviewed coverage/mappings before numeric publication.
Event discovery and automatic extraction of non-reliance announcements are not
implemented. Unknown review coverage blocks valuation/history readiness.

S2 observations remain immutable by capture and locator. Replaying a new mapping
or normalizer revision can reuse unchanged intrinsic observations. A parser/scope
correction that changes an existing intrinsic observation raises an explicit
publication conflict; supporting corrected observation versions requires a later
reviewed schema change. Do not overwrite historical rows.

Financial arithmetic and accounting identity checks belong to S5's pure core.
There is no finished interface, continuously running news agent, email delivery,
valuation engine or release-ready manual at this milestone.
