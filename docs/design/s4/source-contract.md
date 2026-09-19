# S4 — Price and macro source contract

Status: **accepted for implementation on 2026-09-16**. The user instructed
“you can implement it” after the concrete S4-01–04 review checkpoint.
Date: 2026-09-12. Baseline: S3 `b71e308` / `milestone/s3`.
Branch: `codex/s4-source-contract`. Proposed decision: D019; macro part of D009.

## Decision brief

Approve the following S4a scope: typed daily prices and native macro observations,
immutable source evidence, explicit missingness and historical selection, using
the eight-table design plus an additive immutable W1 request-plan contract below. Preserve the permanent-history requirement. Build
Tiingo/FRED adapters against fictional fixtures while their live permissions are
unresolved. Use the separately reviewed direct Treasury nominal-yield feed as
the first macro source candidate: its official dataset is listed under CC0 and a
complete monthly research response was verified. Production activation still
requires the proposed policy record and implementation checks. The bulk H.15
alternative contains legacy Moody's series with unresolved raw rights. An API
key does not activate a provider.

This differs from the original two-adapter milestone for concrete reasons.
Current source terms conflict with permanent archival storage, S2 deliberately
deferred market-data tables, and S3's implemented `Source` types require SEC
resources and issuer-bound financial outputs. Reusing those fields for prices or
global macro data would invent a meaning they do not have. The originals remain
unchanged; this packet makes the proposed differences explicit.

| Review item | Proposed decision | Practical effect |
| --- | --- | --- |
| S4-01 — sources and retention | Require compatible raw and normalized retention grants; select direct Treasury for initial yield inputs; leave Tiingo/FRED and bulk H.15 inactive until permitted. | Saved analysis can retain its original inputs. No purchase, account creation or permission request is sent. |
| S4-02 — source boundary | Add a generic typed provider boundary and preserve the existing SEC specialization and behavior. | Price and macro adapters share archive/attempt/fencing rules without pretending a series has an issuer or filing. |
| S4-03 — storage and missingness | Add the eight typed tables and typed W1 request-plan columns in the storage review; use the explicit states and precision rules below. | Raw/adjusted prices, source missing markers and source definitions cannot silently substitute for each other. |
| S4-04 — historical selection and integration | Separate source-as-of DATE from local retrieval cutoff; require real Timescale verification; add independent W1 price/macro stages. | A rerun preserves old evidence and exposes unsupported history instead of filling it from today's data. |

Corporate-action/ADS lifecycle corrections need S4b review. Complete macro-series
coverage, live price readiness and S4b must remain visible unfinished requirements;
S4a is not the whole original S4 or a finished valuation product.

## S4-01: source scope

The [Tiingo research](tiingo-research.md) and [FRED research](fred-research.md)
record the exact documentation, terms, unresolved account scope and alternatives.
Tiingo's reviewed terms restrict durable retention by account tier and subsequent
subscription status. FRED's reviewed service terms contain storage and development
restrictions. Neither has a verified perpetual-retention grant for this app.
Do not turn a paid-plan boolean into that grant. EODHD and Alpha Vantage were
checked as candidates, not approved as substitutes.

The [Board reuse policy](https://www.federalreserve.gov/disclaimer.htm) is a
separate basis for Board-published information, with third-party exceptions.
Permission must cover the **whole retained response**, including unused series,
as well as the normalized output. A three-series normalizer allowlist does not
grant rights to archive unrelated contents of a bulk feed. Record raw-object scope
and normalized-series scope separately in the proposed source capabilities.

### Recommended initial yield source: direct Treasury

The [official nominal-yield dataset catalog](https://catalog.data.gov/dataset/interest-rate-statistics-daily-treasury-yield-curve-rates)
lists Treasury's Office of Debt Management dataset 015-DO-020 as public under
CC0. The official redirect and Developer Notice connect that dataset's legacy
landing page to today's documented nominal-yield XML feed. See the full link
chain and measurement evidence in [the source research](fred-research.md).

One replacement research capture of September 2026 is complete: **13,033 bytes**,
SHA-256 `e655415955c550b13f8ed20868c6cf56578387e82f3babdd39779bd2225b9e17`,
eight entries, safe XML parse. The earlier research attempt reached a semantic
validation error before saving its body; it is explicitly not a replayable
capture. The [Treasury manifest](../../research/s4/evidence/treasury-yield-manifest.json)
and [raw response](../../research/s4/evidence/treasury-yield-202609-e655415955c5.xml)
record the retained response and evidence. Neither attempt created an application
source or normalized batch.

Propose one provider identity for the nominal Treasury yield dataset. Its raw
scope is the documented `daily_treasury_yield_curve` resource, including all
returned maturity fields; its initial normalized allowlist is `BC_2YEAR` and
`BC_10YEAR`. Preserve `BC_30YEARDISPLAY` and other unselected properties in the
original response without treating their numeric meaning as reviewed. This feed
does not supply effective federal funds, CPI, PPI, unemployment or credit spreads.

Request one explicit YYYYMM window per complete bounded capture, with at most
8 MiB response bytes as an application limit. Record the exact nominal-dataset
parameter, month, HTTP result and all entries; do not use an implicit current
default. Reject wrong dataset/namespace, duplicate/conflicting dates, out-of-window
entries, unsafe XML, incomplete responses and malformed selected fields.
Do not fetch schemas or execute source content.

Selected values are in the `http://schemas.microsoft.com/ado/2007/08/dataservices`
namespace. The `m:type=Edm.Double` label is source metadata, not permission to
parse through a binary float: parse the original text using Decimal.
`NEW_DATE` is a measurement-date label, not the instant a market learned the
yield. Preserve the unzoned source spelling. Native percentage and annualized
measurement convention require the separate Treasury definition/FAQ evidence;
they are not specified by a unit attribute in the XML.

Current missing values may omit a maturity element, per the official Developer
Notice. Preserve that source field absence with a typed coverage/quality finding;
do not fabricate a macro observation. An explicit legacy `m:null=true`, when
supported by a reviewed format rule, is separately `source_missing`.
No actual missing example occurred in this eight-row capture, so missing behavior
still needs synthetic tests and permitted real evidence before claiming it verified.
Feed/entry `updated` timestamps do not establish each observation's original
release time or an ALFRED revision interval. The initial series is current
capture-known history; old source vintages cannot be fabricated.

### H.15 alternative and container contract

Direct H.15 candidate definitions, verified in the actual source bytes:

| Exact source series key | Meaning / native unit | Frequency |
| --- | --- | --- |
| `RIFLGFCY10_N.B` | Nominal 10-year constant-maturity Treasury yield; percent per year | Business day |
| `RIFLGFCY02_N.B` | Nominal 2-year constant-maturity Treasury yield; percent per year | Business day |
| `RIFSPFF_N.D` | Effective federal funds rate; percent per year | Daily |

These are new direct-Board source identities, not FRED DGS10/DGS2/DFF records.
The separate business-day federal funds series is not interchangeable with the
daily series. Preserve exact metadata and interpretation evidence.
The source multiplier code `1` means **One**, not ten to the first power.
Any units/seasonality/date convention not established by reviewed evidence remains
unknown and cannot be presented as established comparability.

The [research manifest](../../research/s4/evidence/frb-h15-manifest.json) records
one complete 4,281,072-byte ZIP and five verified member hashes/CRCs. Decoded size
is 71,014,964 bytes. The 70,757,908-byte data member was completely parsed without
DTD/entity/network resolution; two metadata members contain DOCTYPE declarations
and were explicitly refused by the strict XML parser. Literal code-list inspection
of their verified bytes is separately labelled. This is not full XSD validation.

For a future H.15 adapter, propose application bounds of 8 MiB ZIP entity bytes,
128 MiB total decoded member bytes, a reviewed exact member set, and bounded
streaming reads even when declared sizes lie. Reject traversal, absolute paths,
duplicates, symlinks, encrypted members, unsupported compression, CRC failures,
and DTD/entities in the **parsed data member**. Never extract arbitrary paths or
fetch linked schemas. Optional metadata parse refusal stays explicit and cannot
invent a definition; normalization uses a pinned reviewed definition supported
by exact data attributes and separately recorded code-list interpretation.

Archive the original complete ZIP before parsing; its source capture hash/count
describe the ZIP entity, not a reconstructed XML subset. Each observation locator
includes member name, verified member hash, series key and row location. The
manifest pins the container transform revision and member sizes/hashes. Keep
HTTP content decoding separate from ZIP member decoding. The full research ZIP is held in ignored local quarantine, not a tracked/public
fixture or application input, because its unused legacy Moody's series still
need separate retention review. Checked-in evidence consists of hashes, limited
government-series extracts and content-scope metadata. Filtering a saved body
would break complete-capture provenance; it would not cure raw scope.

H.15 `OBS_STATUS=ND` with `OBS_VALUE=-9999` is verified missing data. Never publish
the sentinel as a yield. Reviewed status `A` means observed only with a valid nonsentinel value.
An unsupported status or a contradiction such as A/-9999 blocks usable numeric
publication; a finite-number check alone is insufficient. The XML header's timezone-less
`Prepared` value is not an exact UTC release time. Current H.15 history contains
no demonstrated ALFRED vintage intervals: label it capture-known history.

CPI/PPI release monitoring, Fed announcements, stock-specific topics and impact
assessments remain N1. This rate source does not complete those requirements.
ERP/beta and the selected DCF risk-free input remain S7 decisions; ingestion
stores no guessed discount-rate constant.

## S4-02: compatible typed provider boundary

Introduce an additive generic `ProviderSource[ResourceT, InputT, BundleT]` protocol
with `fetch(ProviderFetchRequest[ResourceT]) -> FetchResult` and
`normalize(InputT) -> BundleT`. A typed provider resource exposes the source
object key, canonical public URL and public parameter hash. The descriptor carries
explicit supported resource kinds, policy and provider-specific quota policy.
No provider accepts an arbitrary user-supplied URL.

Keep existing SEC `Source`, `FetchRequest`, `SourceDescriptor`, `SecResource` and
financial input/output types as the compatible SEC specialization. They retain
CIK validation, the same resource rules and SEC 5/s default with 10/s maximum.
Any internal delegation into common transport must pass the full SEC regression
suite. The new generic interface does not widen SEC resource validation.

Add typed `PriceResource` with quote binding and inclusive session bounds;
`MacroResource` with provider series/object identity, inclusive reference bounds,
native transform settings and source-as-of policy. Provider normalization returns
a typed `MarketDataBundle`, not a financial `Fact`. Preserve shared `RawRecord`,
`FetchResult`, complete archive/attempt evidence, cache modes, replay checks,
source policies and W1 leases. Financial `Concept` remains the reviewed 40-member
vocabulary; macro units and price fields have their own checked types.

Live retrieval uses refresh/reuse/conditional modes only under current policy.
An explicit local retrieval cutoff requires replay of eligible complete captures.
A source-as-of request may fetch a historical provider representation now, but
must be labelled as such and cannot satisfy an earlier local capture cutoff.

Public request identity includes endpoint version, instrument/series identity,
date bounds, native transformation options, ordering and page parameters. It
excludes secret values. Tiingo uses its header token; FRED inserts its query key
only at dispatch. No ambient client cookies, headers or query credentials leak
into requests. Reject authenticated redirects. Safe error codes/reasons replace
raw exception URLs; fake-key tests cover metadata, logs, hashes and failures.
A response reflecting credentials cannot be archived as a safe original: record
an explicit failed/unsafe-to-archive attempt, without silently redacting bytes
and calling them the complete source body.

Check current activation, resource scope and quotas immediately before dispatch.
Do not hold a database transaction across HTTP. A captured response from a
previously authorized dispatch retains its pinned content grant even if the
provider is operationally disabled before finalization. New dispatch is blocked;
replay rights are evaluated separately. A DB guard on shared attempt/capture
entry points prevents bypassing the policy through an older generic function.

Each provider gets independent shared limits; metadata, pages and retries count.
Tiingo needs reviewed account hourly/daily/monthly bounds and durable consumption
across coordinator restart. FRED's proposed initial pacing is 60/minute across
this application; its documented ceiling is not an app entitlement. Treasury uses coordinated bounded monthly-resource fetches, shared only through
explicit capture pins. H.15, if later permitted, uses one bounded common-object
refresh. Cadence and maximum reuse age are recorded configuration.
No persistent polling or alerts are enabled by this contract review.

## S4-03: exact storage and numeric meaning

The [storage review](storage-review.md) is the field-level proposal:

| Table | Purpose |
| --- | --- |
| `source_policy_capabilities` | Immutable reviewed raw/normalized rights and scope; guarded activation/disable |
| `provider_quote_bindings` | Reviewed dated provider-symbol to quote/security evidence |
| `market_data_batches` | Atomic typed publication, scope, revisions, coverage and archived manifest |
| `market_data_batch_inputs` | Typed capture/attempt references and their roles |
| `market_data_quality_flags` | Price/macro gaps and blocking evidence without a dummy issuer |
| `price_daily` | Date-partitioned raw/adjusted OHLC, volumes, dividend and split fields |
| `macro_series_definitions` | Immutable source identity, units, frequency and interpretation |
| `macro_observations` | Date-partitioned native values, source status and vintage evidence |

Use unconstrained-precision PostgreSQL numeric and exact Decimal parsing, finite
dates/timestamps, FK-enforced source/identity scope, immutable sealed publications
and narrow runtime write grants. Source capabilities have at most one active
review per source; activation and permanent operational disable are monotone,
with actors/reasons. Disabled indefinite grants remain attached to authorized
history; provider deactivation alone is not a retroactive deletion requirement.

Price fields distinguish `observed`, `source_null`, `missing` and `unparseable`.
Macro values distinguish `observed`, `source_missing` and `unparseable`, preserving
their literal source status and value text. Missing or malformed values are NULL
with an explicit flag. An absent source row does not cause a fake NULL row on an
invented date. Exact zero remains zero; booleans are not numbers. An inconsistent
but finite OHLC bar retains its values and has a blocking flag, not corrected math.

Raw close and adjusted close never substitute. Keep raw/adjusted OHLC and volume,
cash dividend and split factor separate; do not reconstruct missing fields.
Provider history can change with corrections and subsequent adjustments.
Adjusted history for a request window must use one complete price response
unless the provider establishes a common generation across responses. A batch
wrapper is not proof of that coherence. Unknown adjustment vintage is
`capture_only`, not a fabricated provider revision date.

Pin venue, quote currency and instrument/ADS identity from reviewed evidence.
A historical price is not usable merely because today's ticker matches it.
Missing quote currency blocks usable price publication; no USD guess or
currency conversion. Dividend cash has its own evidenced currency; unknown
dividend currency blocks that field without blocking a separately valid close.
Preserve the provider's session DATE label: midnight UTC does not become the prior
session in New York. Source publication precision is unknown/date/instant and
never inferred from an EOD label or capture time.

Macro native units are separate from financial concepts. A value of 4.25 percent
stays 4.25 percent; the explicitly tested conversion to 0.0425 belongs to core
when that rate is selected as an input. Index levels, percentage-point spreads,
basis points and percent-per-year rates are different definitions. Source unit
multipliers are interpreted using their code list, not a universal exponent rule.

## S4-04: selection, Timescale and W1

Resolve the macro part of D009 with two independent controls:

- `source_as_of_date`: reconstruct the provider's dated vintage only when an
  explicitly requested response establishes it. Preserve original inclusive
  FRED date endpoints, including finite 9999-12-31 without adding a day.
- `retrieval_cutoff`: use only evidence actually completely captured by that
  timestamp. Re-normalizing old bytes today does not change the original capture
  time. Today's download cannot satisfy an earlier capture cutoff.

A clipped one-day response does not establish a revision's full lifetime.
Monthly measurement date, release/vintage date and retrieval time are separate.
Date-level evidence cannot establish availability at an arbitrary hour on the
same day. Current-only H.15 data cannot satisfy source-vintage reconstruction
for an earlier period merely because its observation date is old.

Choose an eligible batch before examining whether it has a usable value. Newer
missing/corrected data must not silently revive older numeric rows. Select an
older date only under an explicit dated/staleness policy with a maximum age and
visible gap status. Never manufacture a carried-forward observation. Verify
pagination as a whole: conflicting duplicates, changing counts or missing pages
block complete coverage. Prior evidence stays inspectable under its own manifest.

Migration proposal is sequential: `0004_market_data_contract` for relational
types/constraints and guards, followed by `0005_market_data_hypertables` with a
required, verified Timescale extension on PostgreSQL 16. The proposed hypertables
partition by session/reference date; all unique keys and future references carry
that date. No retention policy or chunk deletion. Native PG16 tests can verify
0004, but full-head/S4 acceptance requires the real pinned Timescale runtime.
The existing Compose configuration has not yet proved that runtime locally.

W1 adds price and macro source stages beside SEC. An additive typed
`MarketDataRequestPlan` is resolved and saved atomically at enqueue, before work:
versioned plan identity; price source and date bounds; macro source, exact series
keys and date bounds; optional macro source-as-of date. The storage review lists
the new nullable `analysis_requests` columns and strict grouping constraints.
The existing local `retrieval_vintage` remains independent of both macro vintage
and SEC `filed_cutoff`. No plan is hidden in financial requested periods or
unchecked JSON. Legacy SEC-only requests retain NULL plan fields; a worker must
mark S4 unsupported for those requests, never apply today's defaults retroactively.
Retries read the same saved plan; idempotency compares it; a fresh rerun can
explicitly resolve a new plan. Definitions/bindings discovered later must match
this immutable source/key/quote/window scope and their exact revisions are pinned
at publication. A fresh add/rerun request
preserves earlier batches; retries retain their logical request and budget.
A source outage records its own gap. A shared complete macro capture can be
reused only with its exact manifest and freshness policy. Publication, stage
completion and manifest association commit atomically after lease revalidation,
including after lock waits and on idempotent reuse. A stale worker cannot publish.

These are source stages, not complete financial analysis. S5 ratios/accounting,
S6 public API, S7 valuation, S8 watchlist UI, continuous N1 discovery/alerts and the
finished U1 manual remain required. The source manual must eventually explain
raw versus adjusted prices, units, vintage modes, unavailable inputs and reruns.

## Acceptance and handoff

The [test plan](test-plan.md) and explicitly synthetic
[price](../../../tests/fixtures/s4/price-cases.json) /
[macro](../../../tests/fixtures/s4/macro-cases.json) cases precede numeric adapter
code. Their arithmetic was checked directly; no S4 adapter test is claimed passing.
The actual H.15 research evidence is labelled separately from those fictional
inputs. Write the corresponding behavior tests before implementing normalization.

After user review, implement the approved schema in sequence, then parallelize
bounded adapter work against that contract. Review plausible wrong-value paths,
run all SEC regressions and require real Timescale checks. Keep live-provider
readiness separate from adapter test completion. S4b must resolve dated
corporate-action/ADS relationship correction semantics before claiming that full
original requirement complete.

The current review checkpoint creates no production tables, source-policy rows,
live workers, schedules or outbound alerts. User review changes the status of
S4-01–04/D019; it does not itself supply missing provider retention permission.
