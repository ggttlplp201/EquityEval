# S4a implementation

Status: implemented and verified for accepted S4a scope, 2026-09-19.
Full default suite: 717 passed; native profile: 716 passed/1 Timescale-only skip;
separate golden suite: 110 passed.
Approved scope: D019 / S4-01–04, authorized 2026-09-16. Baseline `014351d`;
branch `codex/s4-market-data`. No application database or live provider is activated.

## Entry points

- `equity_schema.workflow.MarketDataRequestPlan` records explicit price/macro
  source identities, date windows, series keys and independent source-as-of date
  with a watchlist addition or rerun. Omit the plan only for an explicit SEC-only
  legacy request. Existing idempotency semantics remain unchanged.
- `equity_ingest.analysis_pipeline.run_analysis_stages` composes SEC and market
  source work for one claimed lease. Individual source workers can leave the
  execution open with `finalize_execution=False` for this composition.
- `equity_ingest.market_pipeline.run_market_stages` reads the persisted plan and
  accepts configured providers plus `MarketReview`: reviewed quote bindings and
  contexts, macro definitions, and their pinned raw evidence. It never guesses
  listing, units, source permissions or date windows from a ticker.
- `equity_ingest.market_sources.MarketSource` binds concrete `PriceResource`,
  `TreasuryResource` or `FredResource` parameters to verified archived bodies
  before calling pure source normalizers.
- `equity_ingest.market_publisher.publish_market_bundle` verifies evidence and
  interpretation snapshots, writes a deterministic manifest, then invokes the
  narrow fenced SQL publication. Same-input replay is idempotent, including
  timestamps represented in different time zones.
- `equity_schema.market_selection.select_price`, `select_macro`, and
  `select_macro_at_or_before` return typed evidence, field states, quality flags,
  vintages, units, original text, age and manifest references. Backward selection
  requires `max_age_days`; exact-date queries never fill gaps.

These are internal Python interfaces. The public API, stock search/watchlist UI
and complete financial analysis remain S5–S8. Tests exercise watchlist creation,
source work and reruns without upstream traffic.

## Explicit provisioning

Create the source identity and immutable reviewed policy/capability records with
an owner connection. Grants must cover the complete retained raw objects and the
normalized series separately, with indefinite retention compatible with saved
runs. Activation is a guarded owner-only operation; the runtime role cannot
self-approve it. Operational disable blocks new dispatch but does not remove
already authorized retained history. See the [storage contract](storage-review.md).

Provide reviewed metadata captures and their exact interpretation records. For
Tiingo, register a dated provider quote binding before fetching and supply the
matching quote context, including established venue/currency. Unsupported
corporate-action/ADS lifecycle interpretation remains S4b.

Construct a `DatabaseProviderStore` with the exact registered descriptor and a
`ProviderTransport` with a `LocalArchive`, dedicated shared Redis limiter and
HTTP client. Use a common source-specific limiter key across workers, separate
from SEC, with one request per second for the initial market adapters. FRED's
query key and Tiingo's header token are dispatch-only credentials; do not embed
them in descriptors, URLs, fixtures or policy notes. Tiingo also needs all five
explicit `ProviderQuota` bounds. No live source is provisioned by migrations,
examples or tests. Tiingo/FRED retained-content permissions remain unresolved.

Each prepared request conservatively reserves its maximum wire size and counts
against the account budget even if cancelled or interrupted. Reservations cover
rolling hour/day/31-day windows, distinct symbols and monthly bytes, serialized
by source in PostgreSQL. Each immutable W1 request/resource has at most three
prepared attempts across worker retries. This is intentionally conservative:
restarting a worker or Redis cannot erase consumption.

Treasury responses are capped at 8 MiB decoded; other initial market responses
at 32 MiB. Archive wire limits are twice the decoded cap plus 64 KiB. Every
provider has at most three transport attempts per fetch, finite lease/deadline
bounds, and no redirect following. Treasury execution windows are bounded to
120 months and FRED to 20 pages of at most 100,000 observations; exceeding a bound
records a gap rather than silently truncating complete coverage. Two Treasury
series may share an exact captured monthly response within a request.

## Storage and verification

`0004_market_data_contract` adds the eight approved tables, immutable W1 plan
columns, policy/identity guards and atomic publication. `0005` requires actual
PostgreSQL 16 / Timescale 2.28.1 and converts price/macro observations to date
hypertables. No retention, compression or deletion policy is installed.

The default suite requires Timescale and never silently falls back. The explicit
native profile checks relational behavior through 0004. See [runtime setup and
provenance](runtime.md). Source fixtures are fictional except the separately
labelled, permitted Treasury capture. No FRED or Tiingo key is needed for tests.

Use `make check`, and `EQUITY_TEST_DB_PROFILE=native-pg16 make test` for the
additional relational profile. The launcher `scripts/project_python.py` repairs
only this repository's validated strict-editable pointer if macOS marks its
`.pth` file hidden; it does not unhide arbitrary Python startup files. After
adding modules, refresh the strict editable installation before testing.

Final test counts, independent-review fixes, commit and remaining limitations
belong in the [S4 milestone record](../../milestones/S4-prices-macro.md).
