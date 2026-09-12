# S2 — Tests specified before implementation

Status: proposed acceptance cases. No listed financial/database test has run yet.
Use a disposable PostgreSQL 16 database; mocks cannot establish SQL uniqueness,
transactional enqueue, locks or point-in-time selection behavior.

## First regression: real KHC restatement

Source: [S1 exact raw-row audit](../../research/s1/ifrs-and-restatement-observations.md),
Company Facts body SHA-256
`8fad66c16e535f7749f19126a986a9f43a087ca2472d063fa7742106196d88ac`.
Extract explicit source rows into a small reviewed test fixture, retaining provenance.
Expected amounts are hand-checked against filings, not computed by the production
query being tested.

| Property | Original | Revised comparative |
| --- | --- | --- |
| Issuer CIK | 0001637459 | 0001637459 |
| Tag / concept | us-gaap:NetIncomeLoss / net_income_parent | same |
| Unit / measured interval | USD / 2017-01-01 → 2017-12-30 | same |
| Value | 10999000000 | 10941000000 |
| Accession | 0001637459-18-000015 | 0001637459-19-000049 |
| Filed date | 2018-02-16 | 2019-06-07 |
| Fiscal focus / frame | fy 2017, fp FY; frame absent | fy 2018, fp FY; frame absent |

Write the failing public-query regression before the selector:

1. Ingest fixture evidence/coverage/resolutions under one pinned 2026 retrieval
   vintage and approved mapping revision.
2. `as_filed_by_date` with cutoff 2018-02-17 returns original **10999000000**, its
   original accession and provenance; the revised value is never an eligible input.
3. Same mode at 2019-06-08 returns **10941000000** and the revised accession.
4. `original_as_filed` still returns the first value at the later cutoff, but after
   the public non-reliance announcement it remains flagged and unusable for valuation
   even after the revised edition is available. The revised edition can be eligible.
5. An actual retrieval-vintage cutoff in 2018 returns no captured data, rather
   than pretending the 2026 retrieval existed then.
6. Include the May 6, 2019 non-reliance event. A cutoff inside the interval before
   June's replacement retains original evidence but blocks dependent valuation.
   Compare May 3 with May 7: the May 2 determination must not appear publicly
   known before the May 6 announcement.
7. Test consolidated `ProfitLoss` separately: **10990000000** original and
   **10932000000** revised. Parent/common/consolidated scopes cannot coalesce.
8. Include later repeated rows with nullable fy/fp and optional frame; they do not
   disappear or acquire a false error-restatement classification.

## Plausible-but-wrong selection cases

| Case | Required result |
| --- | --- |
| Duplicate instant period with NULL start | One period identity; ordinary UNIQUE NULL semantics must not permit duplicates. |
| TSM ordinary/ADS EPS same tag, unit and duration | Separate contexts/instruments; no overwrite or accidental fivefold conversion. |
| TWD vs convenience USD | Distinct observations/units and conversion basis. |
| Unknown dimensions vs known empty context | Different states; unknown cannot be silently treated as consolidated. |
| Latest coverage has unknown currency | Explicit unresolved result; do not filter it out to revive an older known-currency edition. |
| Latest covered edition has missing or conflicting concept | Return missing/conflict; do not resurrect an older observed amount. |
| New filing covers a different period | Preserve earlier-period eligibility; do not invalidate unrelated history. |
| TSM FY2025 API gap with FY2024 source rows | FY2025 remains unavailable; FY2024 labelled secondary, not current. |
| Same accession, later changed captured bytes | Both versions remain; pinned old snapshot reads old evidence; a timestamp vintage selects the last complete capture before its cutoff. |
| Same capture/mapping but different normalizer or batch | Exact batch/normalizer version is pinned; conflicting results for identical inputs/revisions are nondeterminism, not newest-wins. |
| Newer preliminary statement conflicts with audited-required input | Preserve disclosure separately; authority policy prevents selection as an audited statement. |
| Same-day conflicting filings with no trustworthy ordering | Ambiguity; never sort accession/UUID/insertion order to get a winner. |
| Same-day filings with verified acceptance order | Later eligible edition selected, still labelled day-based reconstruction. |
| Conflicting equal-priority tags | Preserve candidates and flag; no first/largest/average selection. |
| Reported zero / explicit nil / absent tag / malformed numeric | Four distinct states; only reported zero yields numeric zero. |
| Unrounded decimal, large integer shares, NaN/infinity | Exact finite values round-trip; non-finite inputs rejected with parsing evidence. |
| Cross-issuer filing/observation link | Rejected by relational integrity. |
| Missing explanation/quality flag at batch publication | Transaction rejected; incomplete batch invisible to reads. |
| Restatement link inferred from changed number without evidence | Not accepted as formal error correction. |
| Runtime attempts to update/delete published evidence | Rejected; acknowledgement affects only acknowledgement records. |
| Failed normalization batch | Cannot appear in query candidates or saved analysis inputs. |

## Watchlist/request transaction cases

- Double-click Add and transport retry create one active membership and one logical
  analysis request. Same idempotency key with different parameters fails explicitly.
- Kill the process between membership and queue creation: transaction rollback
  leaves neither half committed; committed membership always has its request.
- Concurrent active Adds are serialized by uniqueness, not only UI disabled buttons.
- Explicit Refresh after completion makes a new request/sequence; retry keeps the
  same request ID with another attempt. Reused capture has its original fetch time.
- Two concurrent retry attempts for one logical request cannot both publish;
  a unique publication and request-wide current-attempt epoch fence the winner.
- Expired/stale worker cannot publish; fencing token and execution state are checked
  in the same transaction as publication.
- Crash during state/event/retry scheduling rolls the complete transition back;
  recovery cannot observe a state with a missing audit event or orphan retry.
- Cross-workspace/security parent, membership or quote links are rejected.
- The S2b schema has no dangling FK to a deferred assumption table.
- Network failures do not hold an open claim transaction. Retry delay/max attempts
  and cancellation are persisted, with an event history.
- Removing/re-adding changes membership generation; old pending stock-specific
  delivery is suppressed. Removing membership does not delete analyses.
- When snapshots arrive in later milestones, an older late result cannot overwrite
  a newer completed result pointer; last successful result retains its old freshness.
- Missing assumptions and unsupported bank/issuer models return explicit stage
  states while independent supported stages can finish. No default forecasts.

## Later N1 contract acceptance

These requirements constrain the shared design but do not add N1 migrations to
S2a/S2b. Implement their behavior tests with N1:

- Open Standard/Open USD stays distinct from an unrelated OpenUSD namesake;
  a relevant competitor story can match without mentioning CRCL.
- A versioned bill amendment is not enactment; a testnet announcement is not
  production revenue. Missing adoption/economics evidence stays unavailable.
- One development maps to multiple issuers through separately evidenced driver
  relationships. Syndication does not multiply corroboration or notifications.
- Pin evidence, topic/profile/relevance revisions and knowledge cutoffs; later
  discovery/corrections cannot appear in an earlier saved assessment.
- Material corrections create linked assessments; model-only rewording and
  baseline backfill cannot generate a new breaking-news alert.
- Removal/re-addition and out-of-order assessment completion cannot revive old
  deliveries or replace a newer valid result. Saved valuations remain unchanged.
- Removing/correcting a topic suppresses obsolete queued components even while
  stock membership remains active; discovery respects persistent exclusions.
- Separate macro/topic producers converge on the same development/revision/purpose
  notification. Distinct lead-time, release and correction purposes remain valid;
  a combined alert pins each included stock-assessment revision.

Full workflow cases are in [N1 stock-topic acceptance](../../features/N1-stock-topic-monitoring.md).

## Migration checks and limits

S2a and S2b upgrades run on empty disposable databases and on the previous tagged
schema. Check constraints, FKs, grants and append-only guards through the actual
runtime role. Exercise downgrade/upgrade only with disposable data. Validate
indexes against the stated query predicates. Run required lint/typecheck/test
commands and the repository commit hook; do not bypass it.

Timescale price/macro constraints, complete upstream normalization fixtures,
calculation invariants and actual email/desktop delivery are later gates, not
successes implied by these S2 tests. Remove each S0 empty-suite marker when its
suite receives real tests; never count an intentionally empty suite as behavior coverage.
