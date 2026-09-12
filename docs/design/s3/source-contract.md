# S3 accepted source contract

Status: D008 and S3-01–04 accepted for implementation by the user (“implement”),
2026-09-12, after review checkpoint df99735.
Date: 2026-09-12. Base: `milestone/s2` (`dae3e6e`).

This is the dedicated sequential source-contract review required by
[ingestion instructions](../../../packages/ingest/AGENTS.md). The user directed
progression to S3. The existing financial vocabulary, missing-value representation
and S2 migrations stay authoritative. This proposal makes the remaining source
interfaces and additive transport/policy storage concrete before implementation.

## Recommended decisions

| Decision | Recommended behavior | Reason |
| --- | --- | --- |
| S3-01: source interface | Fetch a resolved resource request and return complete archive references plus attempt outcomes. Normalize pinned archives into the existing observation/coverage/resolution structure. | A ticker and a list of values cannot identify ticker reuse, incomplete history or partial failures. |
| S3-02: evidence and coverage | Company Facts first, with pinned filing inventory and reviewed coverage/scope declarations. Original-filing extraction is a separate tested S3 slice. | Company Facts omits custom/dimensional facts; a newer filing with absent API data must remain a visible gap. |
| S3-03: shared transport | One Redis SEC rate coordinator for all app workers, initially 5 requests/second with no burst, never above 10. Archive complete bytes before parsing; fail closed when coordination/archive verification fails. | This follows the supplied Redis architecture and SEC's shared request ceiling. |
| S3-04: additive persistence | Add versioned source-policy reviews, transport attempts and capture-policy links in a new migration after S2. Preserve complete-capture constraints. | Interrupted HTTP 200 responses, conditional cache checks, licence decisions and retry evidence need honest, queryable records. |

Approval accepts these recommendations and the invariants below. It does not
approve new financial concepts, a public HTTP API, later source licences or a
valuation interpretation for banks/stablecoin issuers.

## 1. Source interface

Proposed Python interfaces live in `packages/ingest`; engines continue receiving
reviewed schema inputs. These are internal interfaces, not S6 API routes.

```python
class Source(Protocol):
    descriptor: SourceDescriptor

    def fetch(self, request: FetchRequest) -> FetchResult: ...
    def normalize(self, inputs: NormalizationInput) -> NormalizationBundle: ...
```

This explicitly replaces SPEC 1.5's `fetch(symbol, since) -> list[RawRecord]` and
`normalize(raw) -> list[Fact]`. Company Facts has no server-side `since` filter;
normalization must preserve an explicit requested period range. Identity resolution
occurs before fetch, and ticker search cannot silently choose an issuer/listing.

| Type | Required content |
| --- | --- |
| `SourceDescriptor` | Stable source key/name, immutable policy-review ID, supported resource kinds, shared provider limiter key, rate and freshness policies. Licence and redistribution status come from the pinned policy revision. |
| `FetchRequest` | Logical fetch ID, resolved issuer ID and ten-digit CIK for SEC company resources; resource kind; validated resource identity; optional pinned capture IDs for replay; explicit requested periods/history boundary; cache mode; active W1 execution lease and stage ID for live fetch. No arbitrary URL or unresolved ticker. |
| `RawRecord` | Immutable complete capture reference: capture/source/object IDs, canonical URL and parameter hash, requested/fetched/completed times, actual HTTP status, entity-body SHA-256/count/blob key, content type and policy-review identity. It contains no selected financial amount. |
| `FetchResult` | Complete capture references, attempt IDs/outcomes, reused capture IDs, explicit inventory/history completeness and gaps. Complete HTTP errors remain archive evidence but are not parseable financial success. An empty successful issuer response differs from request failure. |
| `NormalizationInput` | Issuer/security identities; exact capture/attempt/event/quality-flag manifest; filing metadata versions; requested exact periods/concepts/scope groups; reviewed coverage declarations; mapping, parser, normalizer and authority-policy revisions; retrieval cutoff and bounded inventory/event completeness (`complete`, `incomplete`, `unknown`) with evidence. No implicit latest-source lookup. |
| `NormalizationBundle` | Typed observations, statement coverage, fact resolutions, candidate dispositions, quality flags, pinned provenance and deterministic input/output hashes. Matches S2 persistence; no second flattened fact store. |
| `Fact` | A resolution plus its selected observation reference or explicit unavailable status, unit, period, scope and provenance. Amount comes from the selected observation, not a duplicate mutable field. |

`fetch` performs bounded network/archive work; `normalize` only reads verified
archived inputs and returns data. A separate writer validates and atomically
publishes the bundle. It never holds a database transaction across a network call.
The implementation must not hide a DB write, new fetch or retry inside normalization.

Financial-source normalization is the initial capability. Later news/text adapters
may share transport and policy records without pretending text claims are financial
facts; their output types remain in the N1 contract milestone.

## 2. Archive and replay

- Canonical requests use HTTPS, exact approved hosts and endpoint builders.
  SEC company resources are Company Facts and Submissions, including validated
  older Submissions filenames. Original filing resources use a separate validated
  `/Archives/edgar/data/` builder. Reject credentials, unexpected ports/query fields,
  fragments, path traversal and foreign absolute filenames.
- Disable automatic redirects. Follow at most two validated redirects within the
  three-dispatch resource budget; each is its own rate-limited transport attempt. Redirects outside the approved endpoint scope
  fail explicitly. Do not forward the contact header to another host.
- Decode HTTP Content-Encoding exactly once, then hash and count the entity bytes
  before character decoding or JSON parsing.
  Archive those bytes as gzip with deterministic local headers. On replay, decompress
  only the local archive gzip; never apply the saved HTTP Content-Encoding again.
  Never hash reserialized JSON, converted newlines or scaled financial values.
  Reject malformed/unsupported HTTP encodings and enforce limits during decoding.
- Use a unique capture identity and a source/object/parameter-hash/retrieval path.
  Stream to a temporary file, complete and verify it, atomically publish it, then
  publish capture metadata. A crash may leave an unreferenced complete blob, never
  a successful capture pointing to incomplete bytes. No automatic deletion of raw
  evidence is introduced by S3.
- Enforce decoded-body limits: initially 32 MiB for JSON, 64 MiB for a filing
  document. These are explicit operational limits, not universal filing-size claims.
  Incomplete/oversized bodies stay out of `source_captures`; optionally retained
  diagnostic bytes have separate attempt/quarantine hashes and bounded retention.
- Replay verifies both hash and count. Missing/corrupt archives fail reproduction;
  replay must not silently fetch newer data. A new HTTP 200 is a new capture even
  when its body matches an earlier capture; storage may deduplicate identical bytes.
- A cache hit reuses the old capture ID and retrieval time. A 304 records an attempt
  and its reused capture, not a new body or fresh `fetched_at`. Revalidation time
  is distinct from retrieval time. A missing/corrupt cache cannot satisfy a 304;
  any unconditional retry uses the same bounded request budget.

## 3. Rate, retry and freshness policies

The production SEC User-Agent reads the existing local contact configuration;
no contact is embedded in source, fixtures, logs or committed request manifests.
Both `data.sec.gov` and `www.sec.gov`, retries, redirect hops and conditional
requests consume the same SEC budget. The app's workers and hosts must use one
coordinator for the same SEC user identity; independent clients are outside its
control. A process-local sleep is insufficient.

Keep Redis as specified in the original architecture. Grants use Redis's clock,
expire promptly and may not accumulate into delayed bursts. Missing coordination
fails closed. Tests measure actual request starts, including concurrent processes,
expired permits and cooldown recovery; configuration cannot exceed 10 requests
in any one-second window. Initial target is 5/second, burst 1. Live startup requires
a working coordinator. The implementation tests use isolated local Redis and simulated HTTP.

Proposed defaults: connect timeout 10 seconds, read timeout 30 seconds, total
dispatch budget 120 seconds, and a 360-second logical-fetch deadline including
waits and backoff. At most three actual HTTP dispatches per logical
resource fetch: every retry, redirect hop and unconditional recovery request consumes
one. At most two redirects can be followed, within that same budget. Exhaustion
returns an explicit incomplete fetch result; it cannot silently start a fresh budget.
Retry transient network failures, 408, 429, 500, 502, 503 and 504 with jitter; honor
`Retry-After` and shared cooldowns. A 403/access
block stops rapid retries and sets a shared cooldown of at least ten minutes.
A wait beyond the worker or logical-fetch deadline returns a deferred/incomplete
result with its next eligible time; W1 may schedule a recorded new execution under
its existing request-wide retry limit. The fetch function cannot recurse or reset
its own exhausted dispatch budget. Deterministic 4xx and archive-integrity
errors do not cause unbounded retry loops.

Freshness reports last successful retrieval, last validation, latest attempt
outcome, inventory completeness and normalization state separately. A successful
poll cannot conceal a failed parse or unfinished normalization. Today's fetch cannot
satisfy a historical retrieval cutoff. The S2 vintage selector alone cannot see
new attempt-table failures; source preparation must include them when reporting
readiness and producing evidence-bearing quality flags.

## 4. Additive database proposal

Create `0003_source_ingestion` after the accepted frozen S2 migrations. No existing
financial row, enum, observation meaning or capture-completeness constraint changes.

### Source policy revisions

`source_policy_revisions` fields:

- `id uuid` primary key, `source_id uuid` FK, `review_key text`, unique
  `(source_id, review_key)`; nonempty licence label and defined content scope.
- `redistribution_status` constrained to `allowed`, `prohibited`, `unknown`;
  `permitted_use`, `attribution_requirements`, and terms URL list.
- `reviewed_at`, `reviewed_by`, immutable review-artifact path/reference and SHA-256.
  Policy text is a reviewed artifact, not a financial-source observation.
- All rows immutable and owner-approved. Runtime may read but cannot self-approve.
  Changed terms create a new revision. Source descriptor and each transport attempt
  pin the revision; new captures' existing `terms_review_reference` uses its stable
  review key. A linking constraint/trigger verifies that source and pinned review
  match. Unknown permission never permits redistribution.

Add `capture_policy_links(capture_id PK/FK, policy_revision_id FK)` as the third,
narrow immutable table. A deferred constraint requires every newly inserted capture
to get a matching link in its creation transaction; source identity and the existing
terms-review key must match the pinned policy revision. Pre-migration captures
retain an explicit legacy review status and can receive owner-reviewed links without
changing their evidence. Runtime cannot backfill or rewrite policy history.

### Transport attempts

`source_fetch_attempts` fields:

- `id uuid` PK, logical fetch ID, sequence/hop number, source ID, policy-revision FK,
  stable object key, canonical URL and parameter hash; required `stage_attempt_id`
  FK to `analysis_stage_attempts` for every live fetch. Sequence unique per fetch;
  the stage link is immutable.
- `prepared_at`, optional actual `requested_at`, `headers_received_at`, `finished_at`;
  actual HTTP status nullable only when unknown/not received. `requested_at` is
  the locally observed dispatch start, not proof of remote receipt. Timestamp ordering
  checks, valid status range, and no fabricated replacement status.
- State: `prepared`, `in_progress`, then one terminal outcome:
  `complete`, `not_modified`, `redirected`, `http_error`, `transport_error`, `body_limit`,
  `redirect_refused`, `archive_error`, `cancelled`, or `interrupted_unknown`.
- Optional `completed_capture_id` or `reused_capture_id`, both FKs. Complete and
  HTTP-error body captures must match source/object/status; 304 links only to an
  earlier verified successful representation of the same resource. A partial 200
  never gets a completed-capture link. No rewriting capture retrieval time.
- Allowlisted HTTP evidence: content type/encoding, ETag, Last-Modified,
  Retry-After and validated Location; sent If-None-Match/If-Modified-Since validators
  or an immutable validator reference. A 304 link must match the exact source,
  object, parameters and representation that supplied those validators. Bounded
  failure code/detail; optional
  quarantined partial-body hash/count/path explicitly separate from complete bytes.
  No cookies, credentials, User-Agent contact or unrestricted header dump.
- Prepared state commits before network dispatch. Narrow functions allow only
  forward transitions and one finalization, using the attached workflow lease/fence. Terminal rows cannot be changed or deleted. A crashed
  request with an unknown outcome is finalized as `interrupted_unknown` after
  its lease expires; recovery never claims that it was not sent.

For accepted 3xx responses, finalize the hop as `redirected` with its validated
destination before a new hop dispatches. A refused destination is `redirect_refused`.
A lost stage lease/fence prevents further dispatch, attempt finalization and linked
capture publication by that worker; recovery records `interrupted_unknown` and any
late unreferenced blob remains unselected. S3 live fetches always attach to an active
W1 stage/execution lease. A developer
CLI submits/claims a normal request before live fetch; standalone archive replay
needs no live-fetch attempt or lease. A later independent scheduler must define its
durable lease contract before bypassing this requirement.

Revoke S2 runtime direct INSERT on `source_captures`; runtime uses a narrow atomic
capture-plus-policy-link-and-attempt-finalization function. Its transaction checks
the current workflow fence and lease against DB time; all three changes commit
together. Fixed function search paths, revoked PUBLIC execute, and no direct runtime
policy/link mutations enforce the boundary. Downgrade restores S2 capture grants.
Runtime can read records and invoke narrow attempt transitions, not arbitrarily
update tables. New grants, cross-source links, archive-publication
ordering, crash recovery and migration round trips receive database tests.

Approval covers these three named tables and their narrow grants/operations.
Any further shared schema addition requires its own concrete review.

## 5. Conservative financial normalization

Validate the source CIK against the requested canonical identity. The archived CRCL
CIK is a digit string while other cohort CIKs are JSON numbers: accept digit strings
or integer values within SEC CIK bounds, canonicalize separately to ten digits, and
preserve the original value/type. Reject boolean, fractional, signed, overflowing
or mismatched identities. Never treat a different issuer response as empty success.

Parse archived JSON with exact numeric lexical tokens and Decimal. Malformed
JSON or duplicate object keys fail the document. In otherwise parseable rows,
nonfinite/boolean/malformed values produce an unparseable observation and linked
unavailable resolution, while valid independent rows may still publish with gaps.
A missing val field, JSON null and an explicit source nil assertion are distinct:
`source_nil` requires reviewed source semantics; arbitrary JSON null does not prove
XBRL nil. Preserve all unsupported raw content as evidence. Numeric zero remains
numeric zero. No double scaling,
conversion, sign inversion, quarter subtraction or invented subtotals.

Retain namespace/tag, raw unit, actual start/end, accession, filed date, source
labels, optional frame and nullable `fy`/`fp`. The latter fields describe source
metadata, not the measured period's identity. Company Facts context remains
`unknown` with NULL original context/dimensions. A reviewed economic-scope rule
is separate evidence; it must not claim that original XBRL dimensions were read.

Coverage declarations pin their supporting captures/locators, filing version,
exact period/family, accounting basis, economic scope, reporting currency,
authority and assurance. Filing inventory completeness is explicit. Do not infer
audited/complete statements merely from a 10-K form label. Missing current financial
API rows create `source_missing` coverage where supported by the inventory and
reviewed filing declaration; otherwise coverage is unresolved. TSM FY2024 is never
silently substituted for the expected FY2025 statement.

Newer coverage with unknown authority is excluded by S2 authority selection, so
recording an unresolved coverage row alone is insufficient. Source preparation must
also persist and pin a period-specific error/blocking flag for newer unresolved
coverage or incomplete inventory/event review. Older eligible evidence may remain
inspectable under its original filing label but cannot be presented as a usable
current/latest result. Never fabricate authority to force a newer candidate in.

Pin reviewed public non-reliance events and their affected scopes separately from
filing metadata. An 8-K/Item 4.02 label alone does not identify all affected periods.
Unreviewed event scope or incomplete history stays a visible blocker;
`original_history_complete` must remain false unless the necessary inventory and
event coverage are established. An empty event tuple only means none were supplied,
not proof that none occurred. Inclusive filed-date reconstruction remains separate
from exact intraday public knowledge; unknown original completeness retains S2
“earliest available” labeling.

Scope groups remain separate: parent/consolidated ownership, ordinary/ADS/class
shares, payment/addback basis and reporting currency. The selected observation,
resolution and coverage scope IDs must agree with S2 guards. Reporting currency
is distinct from fact units such as USD/shares.

Match exact identity, filing edition, period, unit and reviewed scope before applying
an issuer/era mapping rule. A rule lists exact qualified tags, validity bounds,
scope/unit constraints, evidence references and reviewed preference rationale.
The S1 candidate matrix is not a universal ordered fallback map. An unreviewed
issuer/era can be archived and inspected but yields explicit unresolved mappings
until evidence supports a rule. A new watchlist stock still runs each applicable
stage and exposes these gaps instead of pretending to finish a valuation.

Retain every candidate and disposition. A reviewed equivalence rule may select one reproducible representative (the
lowest original array position only within the same capture/tag/unit and otherwise
identical semantic/provenance rows). Retain all other observations as non-selected
equivalent-duplicate candidate evidence. Equal amounts alone never establish equal
scope. Across captures/tags, ambiguity remains unless a reviewed authority or mapping
rule resolves it. Conflicting values produce `ambiguous`; no arbitrary first/largest/
latest-UUID winner. Every requested concept/period/scope gets a resolution:
`observed`, `source_nil`, `missing`, `ambiguous`, `unsupported_scope` or `stale_source`,
using existing S2 definitions. Unparseable source values retain their observation
with a missing resolution and precise linked flag; no new enum state is invented.

A missing tag creates no synthetic observation. An absent concept cannot inherit
an older amount. Failed parses and incomplete bundles cannot publish. Input/output
hashes exclude newly allocated output row IDs and processing/publication time.
They include pinned capture IDs, retrieval/completion times, body hashes, metadata
versions and every financial/provenance-relevant decision, coverage/event/quality
manifest and pinned revision. A later identical HTTP 200 is a distinct input vintage. Concurrent duplicate publication
reuses an identical existing batch under a short transaction/advisory lock; differing
outputs for the same inputs/revisions fail visibly, not overwrite history.

## 6. Ordered implementation and acceptance

1. S3a transport/archive and policy/attempt persistence, with fake-HTTP, clock,
   Redis coordination and real-PostgreSQL failure tests.
2. S3b SEC Company Facts/Submissions parsing and reviewed normalization for the
   pinned eight-company cohort, through S2 storage and PIT reads.
3. S3c original-filing extraction with separate context/entity/dimension/scale tests;
   support gaps honestly until its reviewed coverage is implemented.
4. Integrate the real source stages with W1 request execution. Source-stage success
   is not completion of valuation engines that do not exist yet.

The [acceptance plan](test-plan.md) distinguishes current evidence verification
from future normalized golden tests. No upstream call is needed to review this
contract. Public API, prices/macros, valuation engines, N1 live monitoring and the
finished user manual remain in their own milestones.

## Primary access references

Rechecked 2026-09-12 against official SEC sources:
[API coverage and Submissions history](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
[access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data),
[developer resources](https://www.sec.gov/about/developer-resources),
[security/dissemination policy](https://www.sec.gov/about/privacy-information),
[time and reuse FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions).
Operational timeout/body/retry defaults above are accepted app policies, not SEC requirements.
