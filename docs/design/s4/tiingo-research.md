# S4 Tiingo EOD source research

Status: reviewed public evidence and proposed acceptance cases; no live adapter
activation, account entitlement approval or schema decision.
Reviewed: 2026-09-12 (Asia/Shanghai). Baseline: S3 `b71e308` / `milestone/s3`.

## Finding that changes the original plan

The original spec's free-tier recommendation predates the current retention
restriction. The [official terms](https://app.tiingo.com/tos/), last updated
2026-08-05, §1.6 prohibit Starter/trial durable storage; eligible paid plans allow
storage while active, followed by deletion on cancellation/downgrade unless a
separate written agreement applies. The provisions cover archives, backups, logs
and normalized substitutes, not just downloaded files. Qualified irrecoverable
Derived Products have separate conditions; renamed, compressed or reconstructable
prices do not become exempt merely by transformation. §1.4 also restricts website
scraping and preserves proprietary notices.

**Application consequence:** Tiingo live ingestion stays disabled pending a
reviewed retention arrangement compatible with the project's immutable evidence
requirement, or a separately reviewed retention redesign. A personal email, API
key, successful response or paid subscription alone does not establish perpetual
archive permission. This research neither changes account subscriptions nor
sends a request to Tiingo. Pure fictional fixtures can support development.

The old licence-register URL `/about/terms` did not resolve through the research
browser. The current pricing footer links `/tos`, which redirects to
`https://app.tiingo.com/tos/`; use that canonical terms link in the policy review.

## Verified provider behavior

Each paragraph below is a concise record of official evidence. Proposed app
behavior is separated in the following section.

**Authentication.** Tiingo documents both query-token and header authentication.
The header syntax is `Authorization: Token <token>`. REST supports JSON or CSV.
[Connection documentation](https://www.tiingo.com/documentation/general/connecting).

**EOD payload and metadata.** Endpoint paths are `/tiingo/daily/<ticker>` for
metadata and `/tiingo/daily/<ticker>/prices` for prices, on `api.tiingo.com`.
`startDate` and `endDate` bound historical requests. The response fields are
`date`, `open`, `high`, `low`, `close`, `volume`, `adjOpen`, `adjHigh`, `adjLow`,
`adjClose`, `adjVolume`, `divCash`, `splitFactor`. Raw and adjusted prices are
separate; adjustments include splits and dividends. `date` identifies the day
the data concerns; `divCash` uses the dividend ex-date. The documented metadata
fields are `ticker`, `name`, `exchangeCode`, `description`, `startDate`, `endDate`.
Null coverage boundaries mean no available price data. The supported-ticker ZIP
includes reserved symbols; only its presence does not prove API availability.
The published EOD response tables do not establish quote currency, stable
instrument identity, source-publication timestamps or historical adjustment
vintage fields. [EOD documentation](https://www.tiingo.com/documentation/end-of-day).

**Corrections and timing.** The product page describes EOD prices as a composite
of multiple feeds with automated checks and manual corrections. It advertises
most equity/ETF updates at 5:30 pm EST and evening corrections through 8 pm EST;
mutual fund NAV timing differs. This is provider guidance, not proof of a
particular response's publication time or immutable finality.
[Product description](https://www.tiingo.com/products/end-of-day-stock-price-data).

**Historical adjustments.** Tiingo's update guide recommends initial history
loading, then refreshing entire history when `splitFactor != 1` or
`divCash > 0` to obtain updated adjusted prices. That guide was updated
2023-05-23. Its old caching workflow does not override the newer terms.
[Official ingestion guide](https://www.tiingo.com/kb/article/the-fastest-method-to-ingest-tiingo-end-of-day-stock-api-data/).

**Provider audit trail.** Tiingo describes internal timestamped correction
history and corrections to corporate-action dates. This confirms that provider
values can change; it does not document an EOD API parameter for retrieving
all historical versions available at an earlier instant.
[Data-quality article, 2026-08-24](https://www.tiingo.com/blog/tiingo-data-quality-how-we-find-and-fix-market-data-errors/).

**Identity.** Tiingo uses `BRK-A` for `BRK.A`, and a separate preferred-share
format. Its symbology guide describes limits on recycled/delisted coverage.
[Symbology](https://www.tiingo.com/documentation/appendix/symbology).
The changelog separately documents EOD permaTicker queries for accounts with
that capability enabled, international-equity prices in local currency, and
ADR-dividend currency handling improvements. It does not make an issuer's
reporting currency a safe quote-currency default.
[Changelog](https://www.tiingo.com/documentation/general/changelog).

**Corporate actions.** The split endpoint defines `splitFactor` as
`splitTo / splitFrom` and associates it with the ex-date. Its page combines
beta/customer-access language with EOD-entitlement language, so access should
be verified for the actual account before depending on the separate endpoint.
[Split documentation](https://www.tiingo.com/documentation/corporate-actions/splits).
The dividend endpoint distinguishes ex-date, payment date, record date and
declaration date. It similarly has account-access qualifications. An EOD
`divCash` row alone is not advance announcement evidence.
[Dividend documentation](https://www.tiingo.com/documentation/corporate-actions/dividends).

**Published individual-plan limits.** Pricing currently lists Starter at
50 requests/hour, 1,000/day, 500 unique symbols/month and 1 GB/month; Power at
10,000/hour, 100,000/day and 40 GB/month. The displayed Power subscription is
$30/month or $300/year. Both are labelled internal use; redistribution has
separate products. These are dated advertised tiers, not this user's confirmed
account limits, retention approval, permission to display data to others, or
promised future pricing. [Pricing](https://www.tiingo.com/about/pricing).

## Proposed application choices for the shared S4 review

These are engineering recommendations, not additional provider guarantees.

1. Permit only resolved, evidence-backed quote identities. Pin the security,
   listing, quote currency, share class and provider symbol mapping with its
   validity interval. Current metadata cannot prove that all historical uses
   of a ticker denote the same instrument. Restrict the first implementation
   to reviewed US quote identities; leave unsupported identity ranges as gaps.
2. Use bounded daily JSON requests with explicit start/end dates. Disallow
   resampling and column filtering in this first version, avoiding unseen
   transformation defaults. Preserve source date text and use its date label;
   do not timezone-convert midnight into the preceding market session. Reject
   unexpected timestamp forms pending a reviewed parsing rule.
3. Parse numeric lexical tokens into Decimal, preserve raw evidence and each
   field separately, and never reconstruct adjusted prices from unadjusted
   values or invent a missing dividend/split factor. Do not treat an adjusted
   value as the price paid in the historical session. `adjVolume` remains a
   distinct provider field, not locally inferred from price factors.
4. Preserve every captured representation and normalization revision if the
   approved licence permits it. A later response for the same session creates
   another vintage. Label current historical data as provider history retrieved
   on that date. A retrieval cutoff can select only evidence actually archived
   by then; unavailable older vintages remain unavailable. Do not claim the
   provider's unexposed internal audit history is locally reconstructed.
5. Keep the source date, retrieval/completion timestamp, normalization timestamp,
   and a genuinely supplied publication time distinct. No fabricated 4 pm or
   8 pm publication time. Scheduling can use an explicit application timezone
   and margin, but freshness should inspect returned session coverage and
   failures, not just the clock.
6. Build requests with the header token only. Never place credentials in URLs,
   parameter hashes, blob paths, recorded request headers, logs or errors.
   Reject redirects for the initial authenticated adapter. A configured HTTP
   client's ambient headers/cookies/query arguments cannot enter the request.
7. Use one shared budget per Tiingo account across workers, symbols, retries
   and endpoints. Enforce configured hourly/day quotas as well as pacing;
   per-second pacing alone cannot respect hourly limits. Bound symbol/month
   and byte/month consumption before activation. Redis restart must not reset
   consumed quotas into fresh allowance. Document that external clients on the
   same account are outside this app's accounting.
8. Carry S3 archive verification, finite request budgets, cooldowns, lease fences
   and attempt provenance into the provider-independent transport contract.
   Exact quota reset boundaries and rate-limit response conventions were not
   established by the public pages reviewed here; do not invent them. Fail
   closed on missing coordination and defer on an exhausted local budget.

## Conservative acceptance cases to write before numeric code

| Case | Expected result |
| --- | --- |
| Fictional raw close `100.25`, adjusted close `49.875` | Preserve both exact amounts and their distinct field names; neither replaces the other. |
| Fractional split factor `0.1`, cash dividend `0`, volume `0` | Preserve genuine finite zeros and factor; do not convert zeros to missing or recompute prices. |
| Omitted `divCash` or `splitFactor` | Explicit missing field with no synthetic zero/one. |
| JSON null, boolean, NaN, duplicate object key, negative volume, zero/negative split factor | Preserve diagnostic evidence; return a gap or document failure according to reviewed granularity, never a usable fabricated bar. |
| High below low; close outside high/low | Flag source inconsistency; do not clamp or silently repair. |
| Two different rows for one session | Ambiguous until a reviewed precedence rule resolves them; array order is not authority. |
| A later capture changes adjusted history or corrects raw OHLC | Earlier capture stays reproducible; explicit selection cutoffs cannot see the new capture prematurely. |
| A new capture omits a formerly present requested session | Report the gap; no unlabelled carry-forward from the older response. |
| Weekend, holiday, halted stock, pre-IPO range or empty success | No invented bars; completeness depends on reviewed calendar/identity evidence, not a Monday-to-Friday guess. |
| Midnight UTC date label | Preserve the calendar label; no prior-day shift or fabricated publication instant. |
| Same ticker on another exchange/share class, recycled ticker, ordinary share versus ADS | Reject mismatched identity or mark unsupported; never attach by ticker string alone. |
| Metadata lacks currency or has null start/end | Require independent reviewed quote identity; do not assume USD or infer available history. |
| Auth error, quota exhaustion or missing account entitlement | Distinct operational failure; no missing-market-data success and no fallback source substitution. |
| Missing/corrupt archive, stale workflow fence, cancelled request | No normalization/publication from that capture or worker. |
| Free/trial or unresolved durable-retention policy | No upstream dispatch or archive write; a fictional test fixture can exercise the adapter without account data. |

No actual market observations, credentials or whole provider documents were
captured for this note. Only this research document was added by the research
subtask. Shared schema, source-interface generalization, source choice and
retention decisions belong in the root S4 review packet.

## Bounded alternative-provider check

Reviewed 2026-09-12; only EODHD and Alpha Vantage, without accounts, payments,
market-data requests or contact messages.

**EODHD is a candidate for clarification, not an approved replacement.** Its
[terms](https://eodhd.com/financial-apis/terms-conditions) expressly allow qualifying
non-professional users to store and analyze data privately, with sharing and
redistribution restrictions. The cancellation/termination sections do not expressly
confirm that this storage right survives the end of the subscription. The
[personal/commercial guidance](https://eodhd.com/financial-apis/commercial-vs-personal-license-use)
adds user-status qualifications. Its
[EOD API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes)
offers daily OHLC, adjusted close and volume. These pages establish a plausible
functional candidate and an express personal-storage grant; they do not establish
permanent post-subscription retention. Require written clarification covering raw
archives, normalized history, backups and private model-run reproduction before
selecting it for this project's retained-evidence contract.

**Alpha Vantage is also unverified for permanent retention.** Its
[terms, §§2–7](https://www.alphavantage.co/terms_of_service/)
provide a revocable personal/non-commercial platform licence, define commercial
usage more broadly than payment alone, and deactivate access on termination.
They do not expressly grant surviving archival rights to downloaded market data.
The [cancellation page](https://www.alphavantage.co/cancellation/)
describes loss of premium access and market-data entitlements, without resolving
archive retention. The
[API documentation](https://www.alphavantage.co/documentation/)
describes historical daily data, but endpoint availability is not a retention
licence. Obtain a source-specific written answer before treating it as compatible.

No fully verified replacement emerged from this bounded review. Silence about
post-subscription storage is recorded as uncertainty, not inferred permission or
an invented prohibition. This does not block fictional-fixture engineering or
independent FRED work, and does not authorize a provider switch.
