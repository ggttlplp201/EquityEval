# S4 storage and provenance review

Status: **approved with D019/S4-01–04 on 2026-09-16**. The original review
checkpoint is preserved at milestone/s4-contract-review; implementation follows
this contract.
Prepared 2026-09-12 against S3 `b71e308` / `milestone/s3`. This document changes no
production schema, source activation, retention rule or financial concept.

## Recommendation and boundary

Add eight tables for source policy capabilities, reviewed provider quote bindings,
market-data publications and their inputs/flags, daily prices, macro definition
revisions and macro observations. Preserve the S2 financial schema and the S3
attempt/archive ledger. The original spec's `macro_series` hypertable becomes a
regular definition table plus a `macro_observations` hypertable; series metadata
must not be repeated as an unversioned string beside numbers.

The recommended S4 acceptance target retains **PostgreSQL 16 plus TimescaleDB**,
as specified. Plain PostgreSQL can run the relational contract tests, but cannot
pass the hypertable acceptance gate. If a usable Timescale runtime is unavailable,
report that gate as blocked or obtain an explicit decision to defer it. Do not
silently call a regular table a hypertable.

Live Tiingo and FRED ingestion stays disabled until the precise content rights
permit this application's durable raw and normalized evidence. Test against
fictional values and fixtures whose retention rights have separately been
established. An API key, a personal account, successful authentication or an
active paid subscription does not settle that question. Tiingo's current conflict
is documented in [the source research](tiingo-research.md); FRED and each underlying
series require the companion source review. This proposal does not make provider
content rights interchangeable.

The narrow initial numeric scope is provider-supplied daily fields for reviewed
quote identity intervals and native, untransformed macro observations. Corporate
split/dividend fields are source claims associated with a session. They are not a
complete action ledger, announcement feed, total-return calculation or proof that
an ADS ratio remained unchanged. Broader action and ADS relationship corrections
need the explicit follow-on described below.

## Existing records to reuse, and limits

| Existing records | S4 use and constraint |
| --- | --- |
| `securities`, `security_identifiers`, identifier closures/validity | Pin the actual instrument and dated venue/currency identity. A provider symbol is not a security ID. Historical selection retains the original identifier plus the known closure evidence. |
| `security_relationships` | Read only evidence-backed, applicable ADS/ordinary relationships. Its positive ratio is not permission to convert a price or share count inside ingestion. |
| `sources`, `source_policy_revisions`, `capture_policy_links` | Keep source and exact terms review attached to every capture. The new capability table makes retention/use gates machine-checkable without rewriting these immutable records. |
| `source_captures`, `source_fetch_attempts` | Reuse complete-body identity, decoded-byte hash/count, original retrieval timestamps, status and attempts. Failed retrieval is not a missing observation. Every paginated request keeps its own attempt and capture. |
| W1 request/execution/stage records | Reuse request identity, current epoch, cancellation and fencing. Macro source work may serve one stock's request, but the stored macro fact is not owned by that issuer. |
| `normalization_batches`, `data_quality_flags` | **Do not reuse for S4 publications.** Both financial families require issuer context; batches also require financial mapping revisions. Inventing a synthetic issuer for macro data or putting price rows inside statement coverage would falsify their meaning. |

S4 data belongs in typed columns and foreign keys. The archived manifest remains
valuable provenance, but is not a substitute for queryable price/macro rows,
retention permissions, typed input references or missingness states.

## Exact proposed additions

The following is the logical schema to approve. Fields marked `?` are nullable;
other fields are required. IDs are UUIDs consistent with existing evidence APIs.
Numeric values are unconstrained-precision `numeric`, parsed through `Decimal`;
no binary float or money type. Every timestamp must be finite and timezone-aware.
Every date must be finite. Names, revisions and evidence locators are nonempty.
Hash fields contain exactly 64 lowercase hexadecimal characters.

### 1. `source_policy_capabilities` — regular table

- `policy_revision_id` primary key; `source_id` FK to `sources`; composite FK
  `(policy_revision_id, source_id)` to `source_policy_revisions(id, source_id)`.
  Add that redundant composite UNIQUE constraint in the forward migration; the
  old migration file and existing policy rows remain unchanged.
- `raw_scope_kind`, `normalized_scope_kind`, each `source`, `source_objects` or
  `macro_series`, with separate `raw_scope_keys` and `normalized_scope_keys` checked
  text arrays. Each array is empty only for its `source` kind; otherwise it has
  distinct nonempty members and no NULLs. Keys match exact objects/series, never
  glob patterns. A source-wide grant is allowed only when the review covers it.
  Raw scope normally names the exact request object whose **entire response** is
  retained; normalized scope may permit only specifically reviewed series.
  H.15's ZIP contains 263 series at this review, while initial normalization
  proposes three: the three-series allowlist does not authorize retaining the
  other 260. Whole-body rights must be established independently, including any
  third-party content and separately from the normalization decision. The subsequent
  full H.15 scan found legacy Moody's series; the ZIP is format-verified research
  evidence, not an approved live raw source. It remains disabled until whole-body
  rights are established or a separately permitted source is selected. Filtering
  later output cannot cure unauthorized raw retention. A multi-series review must
  establish each member's rights; API-level FRED terms do not establish rights for
  every underlying series. A changed archive composition cannot silently broaden
  the reviewed grant.
- `raw_retention` and `normalized_retention`, each one of
  `indefinite_without_required_deletion`, `time_limited`, `forbidden`, `unreviewed`.
- `internal_analysis_allowed` boolean, `review_valid_until?` timestamp,
  `review_basis` text; operational activation fields `activated_at?`,
  `activated_by?`, `activation_reason?`, `disabled_at?`, `disabled_by?`,
  `disable_reason?`.

The pinned policy already contains reviewer, date, terms URLs and review artifact
hash. Reviewed capability fields are immutable and cannot broaden that policy's
content scope. Only the operational fields have guarded, monotone transitions:
activation may be recorded once; disabling may be recorded once after activation
and is permanent for that revision. Each transition requires its date, actor and
reason; `disabled_at >= activated_at`, and no runtime role may enable itself. A fresh reviewed policy revision
is required to reactivate. All providers begin unactivated. The database checks
current activation as well as the historical grant, so an old pinned policy cannot
bypass a subsequent disable. A partial UNIQUE index on `source_id` WHERE
`activated_at IS NOT NULL AND disabled_at IS NULL` permits at most one active
revision per source. Replacing it atomically disables the old revision and
activates the new one; a past review expiry does not silently remove the old row
from this uniqueness guard. An enabled S4 fetch requires both retention fields to be
`indefinite_without_required_deletion`, internal analysis permission, a matching
raw resource scope for the whole response, an unexpired review and an activated,
non-disabled capability. Numeric publication additionally requires the exact
reviewed normalized scope; authorizing the archive does not approve every field
or series for application use.
Operational disable blocks new live dispatch. It does not erase a capture's
indefinite historical retention grant or automatically forbid replay under that
grant. A restriction on retained-content use needs its own explicit rights review,
not an inference from provider deactivation. A later provider activation uses a new
reviewed policy revision. No guessed expiry date or automatic activation on seeing
a key. Time-limited storage needs a separate reviewed redesign covering archives,
backups, logs, facts, snapshots and deletion; it is unsupported here.

The S4 prepare and dispatch entry points enforce current activation and raw
resource scope for the entire response.
Dispatch checks the current database capability immediately before network I/O,
without holding a transaction open over the request. Finalizing a response from
an already authorized dispatch and replay/publication validate the exact pinned
content grant; operational deactivation must not orphan otherwise authorized
retained evidence. Existing request budgets and current W1 fences still apply. Grant runtime callers
only the guarded entry points. Test that directly invoking the existing generic
S3 ingestion functions cannot create a non-SEC market-data capture without the
new checks; a forward migration must add policy guards on the shared attempt and
capture publication paths, while retaining existing SEC behavior. Merely checking
an adapter's constructor is insufficient. Missing capability metadata on new S4
sources fails closed; existing SEC captures remain labelled under their S3 policy
and are not automatically relabelled as S4-approved.

### 2. `provider_quote_bindings` — regular table

- `id` primary key; `source_id` FK; `quote_identifier_id`, `security_id` with a
  composite FK to `security_identifiers(id, security_id)`.
- `provider_symbol`; `provider_instrument_key?` (only when supplied and reviewed);
  `valid_from`, `valid_to?` using `[from, to)` semantics.
- `identity_capture_id` FK; `source_locator`; `identity_review_revision`;
  `reviewed_at`; `reviewed_by`; `content_sha256`.
- Unique `(source_id, quote_identifier_id, content_sha256)` and unique
  `(id, source_id, quote_identifier_id, security_id)` for typed downstream FKs.

An immutable binding is a reviewed interpretation of evidence, not a mutable
lookup row. Publication checks its interval against the selected quote identity,
known closures, session dates, venue, currency and instrument kind. Overlapping
binding revisions are preserved as evidence, not resolved by insertion order;
each batch pins one exact revision and the selection policy rejects an unresolved
conflict. A changed ticker/exchange or provider correction needs another reviewed
binding. Do not extrapolate a current metadata response to an earlier ticker
reuse interval. Metadata lacking currency needs separate identity evidence.

### 3. `market_data_batches` — regular table

- `id` primary key; `data_kind` (`price` or `macro`); `source_id` FK;
  `policy_revision_id` FK to the capability table.
- `quote_identifier_id?` FK, `security_id?` FK, `quote_binding_id?` FK;
  `source_series_key?`; `series_definition_id?` FK to the definition table.
- `requested_start`, `requested_end` (inclusive reference/session dates),
  `source_vintage_mode` (`current_provider_history` or `source_as_of_date`),
  `source_as_of_date?`, `retrieval_cutoff?`.
- `parser_revision`, `normalizer_revision`, `selection_policy_revision`;
  `input_manifest_hash`, `output_manifest_hash`;
  `manifest_blob_key`, `manifest_body_sha256`, `manifest_byte_count`.
- `origin_stage_attempt_id` FK, `created_at`, `published_at?`,
  `state` (`building`, `published`, `failed`),
  `coverage_state` (`complete`, `partial`, `unknown`, `unavailable`).

Price scope requires a security/quote pair and forbids macro scope. Macro scope
requires a provider series key and forbids security/quote scope. A batch with
identity/definition failure may retain a null binding/definition and blocking
flags, but cannot contain numeric observations. Numeric publication requires the
full binding/definition. The selected scope must match the source, the exact W1
quote for price work, and the explicitly requested series list for macro work.
No dummy issuer is needed for the shared macro series.

`source_as_of_date` is required only in its corresponding mode. Retrieval cutoff
is distinct: a source-vintage reconstruction performed today is not evidence
that this application possessed the value years ago. Requested bounds must be
ordered. Publication time is a local database event, never the source release
time. A unique partial index on `(source_id, input_manifest_hash)` for published
batches makes identical pinned normalization inputs idempotent; the hash includes
scope, dates, policies, parser/normalizer revisions and every input, not just bytes.
A reused batch keeps its original origin and timestamps; each new W1 stage points
to it in the stage's immutable completion record.

### 4. `market_data_batch_inputs` — regular table

- `id` primary key; `batch_id` FK; `capture_id?` FK to `source_captures`;
  `attempt_id?` FK to `source_fetch_attempts`; `role` checked enum:
  `observations`, `series_definition`, `quote_identity`, `calendar`,
  `corporate_action_evidence`, `fetch_outcome`.
- Exactly one of capture/attempt is present. Partial unique keys on
  `(batch_id, capture_id, role)` and `(batch_id, attempt_id, role)`.

This preserves pagination, identities, calendar evidence and failure history
without JSON-only IDs. All referenced captures must be complete, policy-reviewed
and allowed for their role and cutoff. Only successful bodies can supply numeric
observations; error bodies may explain a fetch outcome. An interrupted or pending
attempt known at the cutoff is retained as unresolved provenance, not passed off
as a completed fetch. Read attempt/capture state in one preparation snapshot; pin
the observed state and cutoff in the verified manifest. Do not let its later
terminal transition rewrite the meaning of the historical preparation.

### 5. `market_data_quality_flags` — regular table

- `id` primary key; `batch_id` FK; `reference_date?`; `field_key?`;
  `rule_key`; `severity` (`info`, `warning`, `error`, `blocking`); `message`;
  `capture_id?` FK; `attempt_id?` FK; `source_locator?`; `raised_at`.
- At least a capture, attempt or explicit batch-wide rule applies. Locator implies
  a capture. Referenced inputs must belong to this batch. A date must fall inside
  its requested interval. `field_key` is a checked price-field enum or `value` for
  a macro batch; a batch-wide finding has no field key.

These are immutable findings, separate from numeric rows. Missing price sessions,
missing macro dates, unknown historical vintages, failed requests, unsupported
identity and ambiguous duplicate rows are different rules. Do not emit fake
zero/null bars for absent observations. A caller gets a typed unavailable result
plus these flags; source-supplied null/token values do have explicit field states
on their observation rows. Reusing the issuer-bound S2 flag table would require a
larger unrelated migration and make global macro flags falsely stock-specific.

### 6. `price_daily` — hypertable on `session_date`

- `id`, `session_date`: composite primary key `(session_date, id)`.
- `batch_id` FK; `source_capture_id` FK; `source_locator`; `quote_binding_id`,
  `quote_identifier_id`, `security_id`; `quote_currency`; `dividend_currency?`
  (ISO three-letter code); `source_date_text`.
- `session_basis` (`provider_daily_label`, initially); `session_timezone?` only
  with reviewed evidence. `source_published_date?`, `source_published_at?`,
  `publication_precision` (`unknown`, `date`, `instant`). Unknown means both null;
  date means only date set; instant requires the timestamp and its verified basis.
- Twelve independent field triples: `<field> numeric?`, `<field>_state`,
  `<field>_text?` for `open`, `high`, `low`, `close`, `volume`, `adj_open`,
  `adj_high`, `adj_low`, `adj_close`, `adj_volume`, `div_cash`, `split_factor`.
- `adjustment_basis` (`split_and_dividend`, `split_only`, `unadjusted`, `unknown`),
  `adjustment_vintage_basis` (`provider_supplied`, `capture_only`, `unknown`),
  `adjustment_vintage_date?`; `transform_revision`.
- Unique `(batch_id, source_capture_id, source_locator, session_date)`.

Each price field state is `observed`, `source_null`, `missing` or `unparseable`.
`observed` requires finite numeric and original lexical text. Other states require
numeric NULL; `source_null` preserves the explicit JSON null representation;
`missing` preserves absence, not an invented text value. An invalid volume or
split factor is unparseable/invalid under the reviewed field rule, with source
text and a flag. Genuine zero volume or dividend remains zero; a missing split
factor never becomes one. All twelve triples are typed columns, not a numeric
JSON object. No field is silently reconstructed from another.

The batch and binding enforce quote identity and currency. Source capture must be
a successful numeric input of the same batch/source. Session labels are dates;
midnight UTC does not become a previous-day session or a claimed publication time.
Adjusted and raw fields remain distinct. An adjustment vintage not exposed by a
provider stays `capture_only`: the capture ID identifies what was actually seen.
A capture date must never be written into `adjustment_vintage_date` as if supplied
by the provider. A price history batch uses one complete price response for its
requested window unless the provider supplies a verified generation/snapshot
identity across responses. A batch wrapper alone cannot establish coherent
adjustments across independently fetched periods; without that evidence, an
adjusted-return series assembled from those periods is unavailable.
`dividend_currency` requires separately reviewed source evidence and must never
be copied from `quote_currency` by default. Unknown dividend currency stays NULL
and raises a field-level blocking flag for dividend amount use; this does not
block an otherwise valid close. Preserve the source dividend numeric text and
amount, but do not present that amount as monetarily comparable until its unit is
established. The source capture/locator or an explicitly pinned identity input
must support the currency interpretation. No currency conversion is performed here.

Inconsistent high/low/OHLC relationships preserve the source values but block the
bar's relevant use with a flag; no clamping or correction. Conflicting duplicates
are not collapsed by array order. A later capture may create a new row for the
same session with different raw or adjusted values. Historical selection pins a
batch/capture and never takes today's adjusted history as a contemporaneous
trading price. The future typed input FK must carry `(session_date, id)`.

### 7. `macro_series_definitions` — regular table, immutable revisions

- `id` primary key; `source_id` FK; `source_series_key`; `metadata_capture_id` FK;
  `source_locator`; `content_sha256`; `definition_revision`.
- `title`; `units_text`; `unit_code` (reviewed S4 macro-unit enum, separate from
  financial `Concept`: `percent_per_year`, `percent`, `percentage_points`,
  `basis_points`, `index`, `count`); `unit_multiplier` positive finite numeric;
  `frequency` (`daily`, `business_day`, `weekly`, `monthly`, `quarterly`, `annual`);
  `seasonal_adjustment` (`adjusted`, `not_adjusted`, `not_applicable`, `unknown`);
  `geography`; `reference_date_convention`; `source_release_key?`;
  `upstream_source_name`; `upstream_rights_reference`.
- `definition_as_of_date?`; `definition_as_of_basis` (`source_supplied`,
  `capture_only`, `unknown`).
- Unique `(source_id, source_series_key, metadata_capture_id, source_locator,
  definition_revision)` and unique `(id, source_id, source_series_key)`.

A provider series key is stable source identity; an ID above identifies its exact
reviewed metadata revision. Observations pin that revision. Unit, frequency,
seasonal basis and rights cannot float with the latest metadata. Unknown or
unsupported unit/frequency/reference-date definitions prevent numeric publication
instead of inventing conventions. Unknown seasonal adjustment blocks claimed
comparability and any use that requires a reviewed seasonal basis.
Native percent, percent-point spread, basis points, index levels and counts stay
distinct. For example, a native `4.25` Percent yield stays `4.25` Percent in the
fact layer; a later core input transform may explicitly produce `0.0425` with a
traceable operation. `unit_multiplier` records the literal scale established by
the provider codebook, not a guessed exponent. In the reviewed H.15 codebook,
`UNIT_MULT=1` means multiplier One: store `1`, never compute `10 ** 1`. The
definition capture and locator preserve the original code and reviewed meaning.
No ad hoc macro transformation or fallback risk-free assumption is authorized.
Exact initial H.15 definitions, frequency codes and reference-date conventions
are reviewed separately before publication; this enum does not establish them.

This minimum does not invent a separate global canonical series or cross-provider
equivalence table. A provider substitution is a new reviewed definition and
selection policy, not an invisible fallback. Definition history absent from the
upstream service is an explicit limitation, even when observation vintages exist.

### 8. `macro_observations` — hypertable on `reference_date`

- `id`, `reference_date`: composite primary key `(reference_date, id)`.
- `batch_id` FK; `series_definition_id` FK; `source_capture_id` FK;
  `source_locator`; `source_date_text`.
- `value numeric?`, `value_state` (`observed`, `source_missing`, `unparseable`),
  `original_value_text?`, `source_observation_status?`; `transform_revision`.
- `reference_end_date?` only when the reviewed definition determines the interval;
  `source_realtime_start?`, `source_realtime_end?` as original provider DATEs;
  `source_vintage_basis` (`source_interval`, `requested_as_of`, `current_only`,
  `unknown`); `requested_source_as_of?`.
- `source_published_date?`, `source_published_at?`, `publication_precision`
  (`unknown`, `date`, `instant`) with the same null/precision rules as prices.
- Unique `(batch_id, source_capture_id, source_locator, reference_date)`.

Observed values require finite numeric and original lexical text. Source missing
markers such as `.` preserve their marker and NULL value. A provider may instead
express missingness through a status code: retain that exact code in
`source_observation_status` and its original value text separately. H.15
`OBS_STATUS=ND`, `OBS_VALUE=-9999` becomes `value_state=source_missing`, NULL value,
status `ND` and lexical text `-9999`; the sentinel is never published as a numeric
rate. H.15 status `A` permits an observed value only after numeric and
status/value-consistency validation. `A` with the documented `-9999` missing
sentinel is a contradiction: preserve status/text, set value NULL with
`unparseable`, and raise a blocking flag. A finite decimal alone does not make
that combination an observed rate. Unknown status, or a missing status when the
reviewed source contract requires it, blocks
usable numeric publication with `unparseable` and a flag. For a source that has
no status field by design, the status column remains NULL under its explicit
adapter contract. There is no carried-forward rate, interpolation or synthetic
zero. Genuine negative rates/spreads are allowed; status handling is not a blanket
rule that every negative value is missing. Absent dates have no fabricated
observation: the batch records coverage and flags.

Source-vintage interval endpoints retain the provider's inclusive/exclusive
semantics as a checked adapter contract. For FRED's inclusive dates, keep original
start/end DATEs including a finite `9999-12-31` sentinel; do not add a day and
overflow or convert the endpoint into a fabricated timestamp. A vintage date does
not imply release at midnight. A source interval wholly clipped to the requested
as-of date is labelled as such, not a recovered full revision lifetime. Unknown
vintage must not be backfilled from the latest response.

A provider's native monthly `date` labels its reference period; it is neither the
publication day nor a daily measurement. Any derived reference end follows a
reviewed definition rule recorded by the transform revision. Future snapshot FKs
include `(reference_date, id)`. CPI index levels, release surprises and YoY changes
are distinct: S4 stores native levels, while any requested derived calculation
belongs to a separately tested core function.

## Additive W1 request contract in `0004`

The eight new tables also require an explicit forward extension to the existing
immutable `analysis_requests` table. Add these typed, nullable columns without
changing any existing request row or editing migration `0002`:

| Column | Type and meaning |
| --- | --- |
| `market_plan_revision` | TEXT: exact immutable reviewed plan revision, including supported parser/selection versions and source interpretation policy. |
| `price_source_id` | UUID FK to `sources`: requested provider for this request's existing security/quote identity. |
| `price_start`, `price_end` | DATE: inclusive session window. |
| `macro_source_id` | UUID FK to `sources`: one explicit macro provider in S4a. |
| `macro_series_keys` | TEXT[]: exact requested source series keys. Nullable for legacy requests; no inferred series set. |
| `macro_start`, `macro_end` | DATE: inclusive reference-date window. |
| `macro_source_as_of_date` | DATE: optional provider vintage date, independent of local retrieval cutoff and SEC filing cutoff. |

All dates must be finite. `market_plan_revision`, when present, must be nonempty
and resolve to the exact checked-in, immutable reviewed plan; unknown revisions
are rejected by strict enqueue validation. Plan meaning cannot change under the
same revision key. The database enforces these shape constraints:

- `price_source_id` is present if and only if both price dates are present;
  `price_start <= price_end`. With no price source, both dates are NULL.
- A macro source requires both macro dates and a nonempty `macro_series_keys`
  array. Each key is nonempty, distinct and exact; NULL elements are forbidden.
  `macro_start <= macro_end`. Provider-specific key validation occurs before
  enqueue and again before dispatch; SQL validates the common array constraints.
- With no macro source, both macro dates and `macro_source_as_of_date` are NULL,
  and `macro_series_keys` is NULL or empty. An empty list is allowed only in this
  absent-macro case. A provider vintage date is never allowed without a macro
  source. A current-history macro request leaves the vintage date NULL.
- `market_plan_revision` is present if and only if at least one price or macro
  source is present. The two source scopes can independently be absent. A wholly
  absent plan is the legacy SEC-only case; new absent plans are canonically stored
  as all NULL, including the series array. New columns default to NULL, preserving
  existing rows and their request identity.

`MarketDataRequestPlan` is a strict typed enqueue input. It is resolved at request
creation, validated against the existing security/quote and supported provider
resource rules, and written atomically with the request, request key, state and
queued execution. It is not recomputed when a worker claims or retries work.
Do not hide it in `requested_periods`, repurpose SEC `filed_cutoff`, or place
unvalidated instructions in a generic JSON column. The existing `retrieval_vintage`
remains the independent local capture cutoff for these source stages.

An explicit plan does not activate an unapproved provider; a disabled source
records an operational gap under the pinned plan. Source definitions and quote
bindings may be established after permitted retrieval, but must match the pinned
provider/key, request security/quote, date window and plan interpretation revision.
Their exact reviewed row IDs are then included in the batch and manifest.
A worker cannot substitute another provider, series list, date range or current
parser/selection default because retrieval failed or a configuration changed.

Extend strict enqueue validation and canonical request hashing to include every
plan field. Normalize absent macro arrays consistently before hashing. The same
idempotency key plus a different plan is an error; identical requests retain their
identity. Preserve the original hash behavior for legacy requests with no plan,
so deploying S4 does not make existing idempotency keys conflict merely because
new NULL columns exist. Never rewrite saved hashes to achieve that compatibility.

All retries read this same immutable plan. An omitted plan on a legacy request
makes the S4 stages explicitly unsupported, with no inferred current defaults.
If its pinned plan revision is unavailable to the running code, fail/mark that
stage unsupported rather than silently using the latest revision. An explicit
fresh rerun gets a new request and may choose a newly resolved plan; earlier
requests, captures, batches and manifests retain their original versions.

Acceptance tests must cover old-request replay and key compatibility, a plan
resolved before enqueue, changed worker defaults after enqueue, retry stability,
changed-plan idempotency rejection, independent price-only/macro-only requests,
empty/NULL series handling, unknown revisions, finite bounds, source FK mismatch
and source-vintage versus SEC/local-cutoff separation. Actual publication checks
these columns again under the current W1 lease, including on batch reuse.

## Publication, retrieval and identity rules

1. Prepare the complete capture/attempt/identity/definition set in one database
   snapshot. Read and hash-check archives and build normalized rows outside the
   publication transaction. Untrusted payload content never supplies SQL, source
   policy, application instructions or new enum members.
2. Build the full immutable manifest and archive it before the database write.
   It includes requested ranges, effective/retrieval cutoffs, exact definition and
   binding revisions, input row IDs, attempt outcomes as observed, parser versions,
   coverage, flags and hashes. A failed database commit may leave an unreferenced
   archive; it cannot leave a visible partially published batch.
3. In one short transaction, lock the W1 request/execution/stage and verify its
   current owner/epoch/fence and scope. Serialize the source/resource input hash,
   recheck the lease after waiting, validate every FK/source/period/policy and hash,
   insert building batch plus inputs/flags/rows, publish and finish the stage with
   the manifest association. No HTTP, archive reads or retries while holding locks.
4. Runtime roles cannot update/delete sealed rows or write directly into protected
   tables. Narrow publication functions enforce the same checks on new publication
   and idempotent reuse. Cancellation/stale owners fail closed. No partial set of
   rows becomes eligible after a mid-write error.
5. Select published batches with explicit source, quote/definition, request range,
   raw/adjusted field and vintage mode. Rank a newer eligible response at the batch
   level before inspecting its coverage; if it omits an expected date, return the
   documented gap rather than quietly selecting an older row. A deliberately
   chosen older batch remains inspectable with its capture date and warning.
6. Retrieval cutoff filters actual original captures and inputs. Reparse today
   does not change their capture time. Source-as-of reconstruction is separately
   labelled and can use a source's historical vintage captured today. It cannot
   satisfy a claim that the application knew the value before that capture.
7. For intraday historical use, date-only publication/vintage evidence cannot
   establish that a release was available before a chosen hour that day. Exclude
   same-day ambiguous inputs or require a reviewed exact release timestamp. No
   invented release schedule. Scheduled alerts and release actuals are N1 records,
   not these daily series facts.
8. Staleness uses successful coverage, source cadence and known failed attempts,
   not merely the latest attempted refresh time. Complete pagination is not proof
   of complete historic vintages or complete exchange sessions. A weekday formula
   is not an exchange calendar. Unsupported/halted/pre-listing periods stay gaps
   unless reviewed evidence establishes the appropriate coverage classification.

## Corporate actions and ADS relationship follow-on

S4a stores source-supplied `split_factor` and `div_cash` with their capture, ex-date
session label and adjustment basis. That is sufficient to detect that adjusted
history may need a fresh capture, subject to approved access and quotas. It does
not reconstruct adjusted fields, create cash-flow facts, infer future declared
dividends, or convert ADS prices to ordinary-share prices.

S2's immutable `security_relationships` has an exclusion constraint over its
original `[valid_from, valid_to)` interval. An open-ended row cannot simply be
followed by a corrected ratio: a closure row elsewhere would not change that
existing exclusion constraint. **Do not silently update the old ratio or add an
unchecked override JSON field.** For S4b, review a relationship-closure/correction
ledger and a constrained current-validity projection analogous to quote identity,
with historical reads pinning the original relationship and known closure IDs.
That requires a forward change to the old exclusion/projection machinery and is
outside these eight additive S4a tables. Until then, suspected ratio changes or
unreviewed identity intervals block price/share comparability. Pricing a reviewed
ADS directly in its own quote currency remains possible without conversion.

## Timescale migration and tests

Timescale requires all unique keys to include every partition dimension. Its
current documented FK support permits regular-table→hypertable and
hypertable→regular-table references, but not hypertable→hypertable references.
Therefore both observation hypertables reference only regular tables, and future
input snapshots/typed link tables remain regular tables with date-inclusive FKs.
No self-referencing `supersedes_price_id` FK is added to a hypertable; correction
selection follows immutable batches and captures. [Unique-index rules](https://docs.timescale.com/use-timescale/latest/hypertables/hypertables-and-unique-indexes/),
[constraint support](https://github.com/timescale/docs/blob/latest/use-timescale/schema-management/about-constraints.md).

Proposed migration sequence after approval:

- `0004_market_data_contract`: create the eight relational tables, additive typed
  W1 request columns above, explicit constraints/indexes and guarded functions in
  one forward migration. Preserve
  `0001`–`0003` byte-for-byte. Include composite date keys from the first version;
  a UUID-only ID is never promised to later callers.
- `0005_market_data_hypertables`: a mandatory production acceptance migration,
  requiring an explicitly supported, pinned TimescaleDB version on PostgreSQL 16.
  Convert empty `price_daily` by `session_date` and `macro_observations` by
  `reference_date`, each with a one-year initial chunk interval and no space
  partitioning. Use tested API calls for that exact extension version. Do not
  catch extension errors and continue with ordinary tables.
- The existing Compose image is digest-pinned, but its actual extension version
  and incoming-FK behavior must be measured before declaring compatibility. Use
  `SHOW server_version` and `pg_extension.extversion`, then assert both tables in
  Timescale's hypertable catalog. Enable no retention/compression jobs in S4.
- Run the contract suite on native PG16 at revision `0004`; run the **same suite**
  plus hypertable-specific cases against the pinned PG16+Timescale environment at
  `0005`. A full S4 migration command must target `head`, not silently stop at
  `0004`. Keep fixture databases isolated from the user's existing server.
- Initial conversion is performed before production S4 data exists. If a test or
  development database already has rows, fail with a documented migration plan
  rather than relying on incidental `migrate_data` behavior. An explicit migration
  rehearsal can exercise data conversion and locking separately before supporting
  that path. No live worker writes during conversion.

This avoids a same-revision database shape that changes according to whichever
extension happens to be installed. PostgreSQL native partitioning also requires
partition columns in unique keys and has cross-partition exclusion limitations;
it is not an automatic substitute for a tested Timescale target.
[PostgreSQL 16 partitioning constraints](https://www.postgresql.org/docs/16/ddl-partitioning.html#DDL-PARTITIONING-DECLARATIVE-LIMITATIONS).

Index plan: natural uniqueness above; observation lookup on
`price_daily(quote_identifier_id, session_date, batch_id)` and
`macro_observations(series_definition_id, reference_date, batch_id)`; FK-side
indexes on batches, captures, source policies, definitions/bindings and flags.
Published batch lookup indexes include source/scope, requested interval and
publication time. Begin with B-tree indexes; add BRIN only after realistic query
plans justify it. No automatic chunk dropping, copy deletion or destructive
retention lifecycle is introduced under an immutable-history promise.

## Acceptance tests required before implementation

| Test | Required evidence |
| --- | --- |
| Native PG16 upgrade, rollback rehearsal, re-upgrade | Old S2/S3 schema/evidence survives; migration shape and privileges are exact. Downgrade refuses to discard populated S4 evidence unless a separate destructive test explicitly owns it. |
| Pinned Timescale upgrade | Both hypertables exist; absent/incompatible extension fails, never falls back. |
| Dates in different chunks | Duplicate composite IDs in the same date fail; valid date-inclusive identities and future regular-table composite FKs work. UUID-only reference is rejected. |
| Numeric lexical cases | Decimal raw/adjusted values, zero dividends/volume, fractional split, negative macro yield, percentage/index distinctions, explicit price null versus omitted field and macro missing tokens behave as specified. H.15 ND/-9999 is NULL source_missing; A/-9999 contradicts its observed status and is blocked with NULL/unparseable; unknown status is blocked; UNIT_MULT=1 means One. |
| Wrong identity | Cross-issuer, wrong venue/quote currency, recycled ticker, unreviewed historical binding, ADS/ordinary mix and invalid closure interval cannot publish usable price data. Unknown dividend currency blocks dividend amount use while a separately valid close remains usable. |
| Historical corrections | Two captures changing raw close, adjusted close or macro vintage remain independently reproducible. Earlier retrieval/source cutoffs cannot see later evidence. |
| Reparse | Same exact inputs reuse publication; new parser/normalizer revision creates a new batch without mutating source evidence. |
| Precision | Month label, inclusive source vintage date, finite far-future sentinel and date-only release never become guessed instants. Intraday selection excludes ambiguous same-day data. |
| Coverage | New response missing an old date, missing page, empty success, failed refresh, no calendar evidence and unknown vintage return distinct gaps. Older evidence remains inspectable without silently filling them. |
| Source inconsistency | Conflicting duplicate bars/vintages, high below low, unexpected units and invalid numeric types keep evidence and block relevant use; no repair or insertion-order precedence. |
| Rights gate | Missing/expired/wrong-scope policy, time-limited raw or normalized rights, disabled provider and direct generic-ingestion bypass all fail before live dispatch and archive publication. Fictional fixtures never activate a live provider. |
| Atomicity and runtime grants | Partial inserts roll back; runtime direct mutation fails; published children are immutable; stale/cancelled worker and lease expiry after lock wait fail, including the idempotent reuse path. |
| W1 rerun | Fresh request and stage references preserve earlier batches/manifests; a late older request cannot represent a newer completed analysis. Source-only S4 cannot claim completed valuation/news work. |

## Decisions for the root review packet

Approve or revise the eight-table S4a schema and additive typed W1 request
columns, including the new missingness and
precision enums, source-vintage versus retrieval-cutoff semantics, live rights
gate and the two-revision Timescale acceptance plan. Separately label S4b action/
ADS relationship lifecycle as pending review, or expand that proposal explicitly
before implementation. Do not mark complete action history or the full original
S4 requirement as delivered by the narrower EOD marker fields.
