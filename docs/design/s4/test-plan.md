# S4 acceptance plan

Status: numeric and lifecycle cases specified before adapter implementation.
Fixtures under `tests/fixtures/s4` are synthetic; their JSON and hand-computed
expectations were checked during review. They are not yet executable adapter tests. S3 remains the latest implemented
milestone. Fixture `status` labels an acceptance outcome; field-specific keys
such as `close_state` and `value_state` specify the proposed storage state.

## Price selection and normalization

- Keep security, dated quote identifier, provider symbol/mapping, exchange and
  currency explicit. Never infer currency or ordinary/ADS identity from a ticker.
- Preserve provider session labels and original date text. An EOD timestamp at
  midnight UTC labels the provider's session date; converting it to New York and
  taking the previous date is not acceptable.
- Decode JSON numeric tokens exactly. Booleans, nonfinite numbers, invalid prices,
  negative volumes and malformed numbers produce explicit problems, not zeros.
- Keep unadjusted OHLC, adjusted OHLC, raw/adjusted volumes, dividend amount and
  split factor separate. Check OHLC consistency without repairing it.
- A two-for-one adjustment revises the historical adjusted representation; it
  does not replace the recorded unadjusted close or create a current share count.
- Later provider corrections create new capture/batch versions. Historical reads
  pin capture vintages and one coherent adjusted-history generation; no mixtures
  assembled from separately fetched periods or adjustments.
- A newly missing/invalid close in a complete newer capture cannot silently fall
  back to an older close. Preserve the old fact as inspectable evidence and block
  a usable current result. Empty response, holiday, delisting, suspension and
  missing data are different states; no rows are fabricated for calendar dates.
- S4a verifies dated identity evidence and blocks unsupported ADS comparability.
  Correction/closure of action and ADS-ratio history is deferred to S4b review.
  No automatic split, currency conversion or ADS arithmetic in ingestion.

## Macro selection and normalization

- Bind the exact series definition, unit, frequency, seasonal basis and source.
  Rate percentages, percentage-point spreads, index levels and currencies differ.
- Preserve a published percent value as percent. Unit conversion is explicit and
  tested later in the pure financial layer; a value of 4.25 percent is not 4.25
  as a dimensionless rate. No hard-coded discount input.
- Preserve reference date, source-vintage interval, retrieval/completion times
  and publication precision separately. A monthly reference date is not a
  release date. Date-level ALFRED information does not establish intraday timing.
- FRED/ALFRED source-vintage intervals are inclusive on both ends. Select a date
  only from a response explicitly requested for that vintage. Never infer an
  infinite valid interval from a single-date snapshot or a response envelope.
- Keep a source missing marker as an explicit missing observation; it is not
  zero. H.15 ND/-9999 becomes NULL with source status and text retained; reject
  unknown status and sentinel/status contradictions. UNIT_MULT=1 means One.
  A latest missing value must not pick an earlier numeric revision.
- A current direct H.15 capture has no ALFRED-style vintage guarantee. Historical
  reads cannot use a later downloaded value as though it had already been
  captured. Retain capture-known-only status when source vintage is unavailable.
- Follow complete bounded pagination with invariant series/filter/vintage/count.
  Missing pages, duplicates, changed counts and inconsistent overlaps block a
  complete result; never publish only the convenient first page as complete.
- For dated rate selection, state an explicit backward-selection policy with
  reference-date age, retrieval age, gap status and maximum permitted age.
  Do not carry forward missing values to manufacture observations.

## Direct Treasury feed cases

- Pin the nominal-yield dataset and exact monthly request; verify the complete
  response before interpretation. A semantic failure must not discard otherwise
  permitted complete raw evidence.
- Parse selected BC_2YEAR/BC_10YEAR values from their exact namespaces using
  Decimal despite the source Edm.Double label. Pin units from separately reviewed
  Treasury definition evidence, since the XML contains no unit attribute.
- Preserve NEW_DATE as a date label and updated metadata as update metadata;
  neither proves original publication time or an older source vintage.
- Distinguish current omitted maturity elements, explicitly supported legacy
  m:null, empty/malformed text and genuine zero. Unknown unselected properties
  remain in the raw response without silently gaining normalized meaning.
- Verify wrong dataset, unsafe XML, conflicting duplicate dates, out-of-window
  rows, namespace drift and incomplete bodies. The one complete eight-row
  research capture does not demonstrate missing-date/calendar completeness.

## Archive, policy and secrets

- Tests with deliberately fake API keys prove they appear only on the wire;
  omit them from logs, request metadata, hash inputs, manifests and exception text.
  Do not archive reflected credentials in upstream error bodies.
- Missing key or incompatible storage permission prevents dispatch before any
  network call. A paid-plan flag is not permanent-retention authorization.
  Review the entire retained body independently of normalized series scope; a
  normalizer allowlist cannot approve unused third-party content in a bulk ZIP.
- Retain S3's complete-body verification, interrupted-response behavior, immutable
  policy links and attempt evidence. New providers have independent shared quotas;
  SEC's budget is unaffected. Reject redirects for authenticated provider requests.
- Verify full HTTP responses against source identity and request boundaries.
  A 200 API error is not an empty successful time series. Unknown outcome after
  a crash remains unknown. One worker's lease loss prevents late publication.

## Persistence and workflow

- Exercise all new types, finite numeric checks, composite identity links,
  immutable rows, replay idempotency, manifest association and stale-worker
  rejection with real PostgreSQL and the required Timescale profile.
- Future references to time-partitioned facts include the date partition key.
  Test runtime grants, migration downgrade/upgrade and both captured-before and
  source-vintage selection on the same consistent snapshot.
- Persist the strict typed market plan at enqueue; retries cannot change its
  source, series, date bounds or revision. Preserve legacy request hashes and
  all-null SEC-only plans; reject changed-plan idempotency reuse.
- Add/rerun considers SEC, price and macro stages and preserves their independent
  gaps. One provider outage cannot replace or erase another stage's evidence.
- Reuse only explicitly pinned complete archives. A historical request never
  falls back to today's provider endpoint. A new user rerun preserves the prior
  capture/batch history, while a retry stays on its original logical request.
- Display-only staleness and source availability are not assertions that a
  valuation is supported. S5–S7 remain responsible for calculations and assumptions.

## Required review before completion

Run an independent review focused on plausible wrong values: split-adjusted close
used with unadjusted shares, stale quote mappings, missing currency, percentage
versus fraction, revision lookahead, empty/latest-missing fallback and inconsistent
pagination. Then run the full project checks and original SEC regressions. A
Timescale feature cannot be reported tested using only plain PostgreSQL.
