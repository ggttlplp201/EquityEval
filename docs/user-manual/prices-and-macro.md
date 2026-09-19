# Understanding prices and macro data

Status: S4a source-layer guide. This chapter explains the implemented storage,
source stages and evidence views. The watchlist screen, valuation models and
news-alert controls are still under construction; there are no verified UI
steps for those features yet.

## What happens when you add a stock or rerun it

The request records the exact stock listing, price source and date range, macro
source and series, and any historical cutoffs. Workers use that saved plan on
retries. They collect SEC, price and macro inputs independently: one unavailable
source does not erase another source's result. Each complete response is archived
before interpretation, and each published result has an immutable manifest.

A fresh rerun creates a new request and preserves earlier results. An explicit
replay reads the selected archives without fetching the latest data. Legacy
requests created before S4 have no market plan and report that stage as
unsupported; they do not acquire today's default source or dates.

This is source collection, not a completed valuation. A result marked
`completed_with_gaps` may still lack prices, source coverage, reviewed mappings,
financial ratios or valuation assumptions. Follow the individual stage reasons.

## Reading price fields

| Term | Meaning and interpretation |
| --- | --- |
| Quote/listing | A specific security traded on a particular venue in a particular currency. A ticker alone is insufficient. |
| Session date | The provider's label for the trading session. A midnight timestamp is not automatically an exact trade or publication time. |
| Open, high, low, close | Unadjusted price fields for that session. Each field retains its original source text and missing-value state. |
| Adjusted prices | Provider-supplied history reflecting its split/dividend adjustment convention. Kept separately from unadjusted prices. |
| Volume / adjusted volume | Separate provider-supplied quantities; neither is substituted for the other. |
| Cash dividend | A provider field with an independently established currency. An unknown dividend currency blocks numeric use. |
| Split factor | A provider-reported adjustment field. It does not by itself establish complete corporate-action history. |
| Adjustment vintage | The version of adjusted history that was captured. Later provider adjustments do not overwrite earlier archived values. |

Illustrative example: a raw close of 100 and an adjusted close of 50 are two
separate values, not conflicting estimates of the same field. The selector
returns the field requested. It never silently replaces a missing raw close
with the adjusted close. An inconsistent high/low/open/close group is flagged
across that group; unrelated volume fields keep their separate evidence.

## Reading macro observations

| Term | Meaning and interpretation |
| --- | --- |
| Series | One source's exact economic measure, with its own units, frequency, geography and definition. |
| Reference date | The date or period the measurement describes. It is not necessarily its release date. |
| Native units | The units the source reports. An observation of 4.25 percent remains 4.25 percent in source storage. A model must explicitly convert it if it needs a decimal rate. |
| Basis point | One hundredth of a percentage point. It is a different unit from percent or an index level. |
| Seasonal adjustment | A source's treatment of recurring seasonal patterns. Unknown adjustment is recorded as unknown. |
| Source vintage | The provider's dated version of an observation, where the response establishes that history. |
| Capture time | When this application finished retaining the complete response. |
| Publication precision | Whether release timing is known to an exact instant, only a date, or not established. Date-only evidence cannot prove availability at a particular hour that day. |

The initial direct Treasury adapter handles nominal two-year and ten-year yield
fields from an explicit monthly XML response. It does not provide CPI, PPI,
unemployment, effective fed funds or news announcements. Treasury measurement
dates do not establish historical release vintages. FRED's synthetic adapter
checks native observations and complete pagination; it retains inclusive source
vintage dates without inventing a full revision lifetime from a one-day response.

## Historical questions and missing values

Two independent controls answer different questions:

- **Source as of date:** which dated version the provider supplied.
- **Local retrieval cutoff:** which complete evidence this application actually
  retained by that instant. Downloading old observations today cannot satisfy a
  cutoff last year.

Selection chooses the relevant response before checking for a usable value.
If a newer response is missing, malformed or failed, that gap remains visible.
An older saved result remains inspectable by its explicit batch ID. Exact-date
selection never fills a missing observation. An optional backward selection
requires a maximum age, returns the actual observation date, and labels the age;
it does not create a carried-forward observation.

`NULL` means no usable source value, not zero. Distinguish an omitted field,
an explicit source missing marker, an unparseable value, and an unavailable
response. A complete HTTP response also does not prove that every expected
trading or release date is present. Until a reviewed calendar establishes that
coverage, the result retains a coverage gap and cannot be treated as a fully
verified model input.

## Source setup and troubleshooting

No live price or macro worker is activated by installing this code. A configured
source needs a reviewed identity, compatible rights to retain both raw responses
and normalized data, exact permitted resources/series, and explicit activation.
An API key alone is insufficient. Tiingo additionally requires reviewed account
quotas; reservations survive worker and rate-coordinator restarts. Provider
credentials are omitted from request identities, archives and HTTP diagnostics.

| Stage reason | What to inspect |
| --- | --- |
| `immutable_market_plan_missing` | Create a fresh request with an explicit market plan. |
| `price_provider_unavailable` / `macro_provider_unavailable` | The requested provider is not configured for this worker. |
| `reviewed_price_binding_required` | The provider symbol must be linked to the exact security/listing with dated evidence. |
| `reviewed_macro_definition_required` | The exact series needs reviewed units and date/frequency interpretation. |
| `credentials_missing` | Configure the provider credential only after the source permission review. |
| `source_policy_unavailable` | Inspect source activation, retained-content rights and permitted scope. |
| `provider_budget_exhausted` | Inspect the durable request/account budget; do not bypass it by restarting the worker. |
| `market_capture_request_mismatch` | The pinned archive does not satisfy the requested resource or cutoff. |
| `unsafe_reflected_secret` | The response reflected a credential; its body was not retained as a safe archive. |
| `market_coverage_unknown` | Complete calendar coverage has not been established. |

Operator entry points and tested setup are documented in the
[S4 implementation guide](../design/s4/implementation.md). The finished manual
will add verified screen instructions, screenshots and contextual glossary links
when S6/S8 and the N1 alert workflow are built.
