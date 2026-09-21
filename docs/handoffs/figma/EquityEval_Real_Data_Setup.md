# EquityEval — obtaining and testing real data

Prepared 2026-09-19. Provider documentation and prices checked on that date.
Implementation baseline: `milestone/x1-core-graphs` (`a9cb080`). This is an
acquisition and test plan, not a claim that a live-data import is already running.

**The user-facing pilot is CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL, in that order.**
Keep all seven; do not treat them as one peer group or a complete sector universe.
Start after UI design review with their identity, current filings and source-coverage
inventory. [Dated profile evidence](../../research/pilot-business-profiles-2026-09-19.md)
and [R1](../../features/R1-business-aware-research.md) give the concrete boundaries.
Mineral mining is in scope; MSTR is treasury/software. Existing MSFT/RBLX annual
archives remain free regression checks, not replacement pilot choices. Qualify
price/capitalization/classification data only as the first complete experience
needs it; broader market coverage follows later.

## 1. What can be tested now

The repository contains real, dated SEC evidence and reviewed mappings, including:

| Regression fixture company | Archived annual period | SEC accession |
| --- | --- | --- |
| Microsoft / MSFT | 2024-07-01 through 2025-06-30 | `0000950170-25-100235` |
| Roblox / RBLX | 2025-01-01 through 2025-12-31 | `0001315098-26-000024` |

These are historical observations, not today's company results. The
[baseline source review](../../research/s1/baseline-observations.md) describes their
accounting contexts and gaps. The [evidence directory](../../research/s1/evidence/README.md)
contains manifests and original filing archives.

The existing no-key regression check is an **annual SEC replay for MSFT and RBLX**:
reopen verified source captures, run the existing extraction/normalization and
fundamentals calculations, and inspect the source trail and every blocked value.
This is narrower than a current TTM valuation or a complete sector dataset.
Unsupported source mappings, incomplete filing/event history and accounting scope
issues must remain visible. An archived fact can be correct yet still be blocked
from a ratio because its surrounding evidence is incomplete.

For an immediate developer check, run the existing archive-backed acceptance tests
from the canonical repository after its normal bootstrap:

```sh
cd '/Users/leon/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval'
.venv/bin/python scripts/project_python.py -m pytest -q tests/golden/test_inline_filing_spot_checks.py tests/core/test_source_metric_golden.py
```

This command verifies archived facts and source-to-calculation boundaries without
an API key or new upstream downloads. It **does not populate the web interface**.
The standalone replay/report workflow and its UI connection still need integration.
Do not replace the checked fictional graph fixture with unreviewed real numbers.

## 2. What account setup does — and does not — unlock

| Capability | Current position |
| --- | --- |
| SEC capture, archive verification, reviewed normalization | Implemented internal Python components; mappings are scoped to reviewed issuers, accessions and periods. |
| Price/macro transport and storage | Implemented internal source interfaces; no live source is provisioned or running. |
| Fundamentals and sector math | Implemented pure calculations for the recorded scope. Missing or incompatible evidence blocks affected results. |
| Sector graph development screen | Works with explicitly fictional snapshots. |
| Real-data company/sector screen and public API | Not connected; S6 immutable result contracts and adapters remain open. |
| News monitoring and alert delivery | Planned N1 feature; account keys do not start a monitor. |

`.env.example` lists `SEC_USER_AGENT`, `TIINGO_API_KEY` and `FRED_API_KEY`.
These are configuration placeholders, **not a finished import command**. Merely
filling `.env` does not wire a worker, grant source permissions, publish result
snapshots or update `/sectors`. There is no verified one-click “load real market”
flow yet. FMP is a candidate source and has no implemented provider adapter here.

Keep credentials in the local ignored environment/secret store, outside Git,
Figma files, screenshots, source manifests and chat. Designers should continue
using the synthetic design fixture.

The implementation handoffs are [S3 ingestion](../../design/s3/implementation.md),
[S4 source setup](../../design/s4/implementation.md) and
[X1 remaining prerequisites](../../milestones/X1-sector-explorer.md).

## 3. SEC fundamentals: free and available without an account

SEC's public read APIs do not require a key. Company submissions identify filings;
Company Facts helps locate standard-tag facts; original XBRL/Inline XBRL filings
preserve the exact reporting contexts. Company Facts does not include every custom
company tag or every dimensional context. Its bulk ZIPs support later scaling.
[Official SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)

For fresh downloads, configure a real contact email in the identifying User-Agent.
The SEC publishes a maximum of ten requests per second. Keep the existing shared,
more conservative limiter, retries and archive-first pipeline. Reading data does
not require an EDGAR Next filing account.
[SEC developer FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)

Developer resources to resolve, rather than paste into browser UI code:

- Submissions: `https://data.sec.gov/submissions/CIK##########.json`
- Company Facts: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`
- Original filing documents: the accession's SEC archive index and its referenced files.

Use the ten-digit CIK, exact accession, period start/end, unit, source context,
precision, filing/acceptance time and retrieval time. Archive the response before
normalizing. A newly downloaded historical observation was not locally captured
last year; preserve those two dates separately.

**Preserve the planned 3, 5 and 10-year fundamentals controls.** Core history
mathematics exists; source-history and company-UI integration remain open. Obtain
actual period coverage where available, and report short history or gaps honestly. A
recent IPO cannot acquire ten years of public-company history through a plan
upgrade. Sector line windows remain the separate 1/3/5-year controls.

## 4. Tiingo prices: use the existing adapter, subject to retention rights

Visit [Tiingo](https://www.tiingo.com/), create or sign into a personal account, and
obtain the API token through its account/documentation interface. The published
personal Power price is **$30/month or $300/year**. Fundamental API data is a
separate add-on; an EOD subscription does not supply the missing sector roster,
sector assignments or common-equity capitalization.
[Current pricing](https://www.tiingo.com/about/pricing)

The EOD API documents raw and adjusted prices, dated dividends and split factors.
Keep raw closes separate from split/dividend-adjusted closes. Its metadata includes
symbol, name, exchange and price availability dates. Its supported-ticker ZIP also
contains reserved symbols, so it is not proof of a complete eligible issuer roster.
[Tiingo EOD documentation](https://www.tiingo.com/documentation/end-of-day)

**Check retention before enabling imports.** Tiingo's terms updated August 5, 2026
prohibit durable storage on Starter/trial plans. Eligible paid plans permit storage
within the plan's terms while active, but require deletion after cancellation,
termination or downgrade unless separately agreed. Different retention can be
negotiated. Derived outputs have additional conditions; a source drawer or a ratio
that reveals an underlying price is not automatically exempt.
[Tiingo terms, section 1.6](https://www.tiingo.com/tos)

The practical consequence for this project: the free plan can support transient
connectivity tests, but not the archive-backed pilot. Even a normal paid plan does
not establish the indefinite raw/normalized retention required by the current
[S4 contract](../../design/s4/implementation.md). Obtain compatible written terms,
or review a changed retention policy before activating persistence. Keep the
account's quotas and permitted resources in the source-policy record.

## 5. Sector reference and capitalization data: qualify FMP before buying

[FMP registration](https://site.financialmodelingprep.com/register) offers a free
API key without a card. Use that account or vendor-supplied samples to establish
whether the exact endpoints and fields meet the project requirements.

Ask for samples/entitlements for the following stable APIs:

| Dataset | Candidate resource | What to validate |
| --- | --- | --- |
| Security directory | `stable/stock-list` | Stable issuer identity, eligible securities, coverage and delistings; not just companies with available statements. |
| Current company profile | `stable/profile?symbol=...` | CIK, exchange, currency, sector/industry and exact taxonomy meaning. |
| Capitalization | `stable/market-capitalization?symbol=...` | Date, common-equity basis and complete issuer/share-class coverage. |
| Historical capitalization | `stable/historical-market-capitalization?symbol=...` | Actual observation dates, depth, revisions and point-in-time share basis. |
| Delistings | `stable/delisted-companies` | Historical eligibility; a delisting list alone does not supply historical classifications. |
| Financial statements | Quarterly/as-reported statement resources | Exact period and original filing provenance for reconciliation; use existing core calculations. |

These resources are documented in the [FMP API directory](https://site.financialmodelingprep.com/developer/docs),
[profile documentation](https://site.financialmodelingprep.com/developer/docs/stable/profile-symbol),
[historical-cap documentation](https://site.financialmodelingprep.com/developer/docs/stable/historical-market-cap)
and [delisting documentation](https://site.financialmodelingprep.com/developer/docs/stable/delisted-companies).
Their existence does not confirm account entitlement, universe completeness or
compatibility with equityEval's definitions.

The checked pricing page advertises Basic at 250 calls/day, Starter with annual
fundamentals and up to five years, Premium with full fundamentals/up to 30 years
at **$49/month billed annually**, and Ultimate with bulk/batch delivery at
**$99/month billed annually**. These are annual-billing equivalents, not a verified
monthly checkout quote. Confirm quarterly statements, per-company 10-year coverage,
required endpoints and call/bandwidth limits before choosing a plan.
[FMP pricing](https://site.financialmodelingprep.com/developer/docs/pricing)

FMP's personal-use terms restrict third-party access and copying/downloading
without written approval; multiuser display requires a specific agreement.
Confirm local raw-response storage, immutable snapshots, backups, derived ratios,
private display and retention after cancellation in writing. API access alone
does not establish those rights.
[FMP terms, sections 2.2–2.8](https://site.financialmodelingprep.com/terms-of-service)

Do not automatically adopt vendor P/E, sector P/E or TTM ratios. Obtain the
underlying inputs, validate them, and calculate with equityEval's existing engine.

## 6. Requirements for meaningful real sector graphs

These are equityEval's acceptance requirements, not claims that any vendor has
already satisfied them.

| Input | Required evidence |
| --- | --- |
| Issuer roster | Dated, independent list of eligible US operating-equity issuers; stable IDs, instruments, currency and inclusion/exclusion reason. |
| Share classes and ADS | Issuer-to-security relationships, class coverage, depositary ratios and corporate-action dates. Count an issuer once. |
| Classification | Taxonomy name/version, sector/industry IDs, effective dates, date known, source and rights; unknown stays Unclassified. |
| Market capitalization | Dated issuer-wide common equity, valuation currency, observation date/time and class methodology. No duplicated full-company cap across class tickers. |
| Earnings | Income available to common shareholders with compatible scope. Generic consolidated/parent net income is not an automatic substitute. |
| Other flows | Revenue, operating income, CFO and cash PPE capex; exact periods, units, precision and accounting basis. |
| Audit trail | Original source, filing accession/acceptance date, retrieval timestamp, transformation and immutable revision/hash. |
| Historical coverage | Membership and financial information known at each historical date, including excluded/delisted companies and revisions. |

Never infer complete issuer market cap from one class price or from weighted-average
EPS shares. Never substitute consolidated or parent income for common earnings
without reviewed accounting evidence. Current calendar-period assembly also does
not establish automatic support for every 52/53-week or transition fiscal year.
Unsupported cases must keep their flags.

Use the confirmed seven-company pilot first. Their share structures, accounting
scopes and business profiles require explicit review; do not assume simple equity
or a generic operating model. Expand only after this experience is verified. Name that universe **Selected-company
pilot**. Full sample coverage does not make it the entire sector. Keep small-sample,
missing-input and coverage gates; real data is allowed to produce unavailable
charts when it does not support a valid comparison.

For production-wide sector history, buy or otherwise obtain dated classifications
and roster history. Today's profile plus old statements produces **current-members
history**, not historical sector membership. The UI must label that mode and disable
historical-sector percentile claims.

If choosing GICS, request licensed current classifications and **GICS History**,
including identifiers, effective/known dates and usage rights. S&P distinguishes
current GICS data from company-level historical classifications. The public GICS
methodology/structure is not a licensed company assignment feed.
[S&P classification products](https://www.spglobal.com/market-intelligence/en/solutions/differentiated-data)

A vendor's own classification can be evaluated for the pilot. Label it with the
actual provider taxonomy and version; do not call it GICS without evidence.

EODHD was also checked. Its specific historical-cap endpoint currently documents
weekly NYSE/NASDAQ equity observations beginning 2021-07-09. That is not a direct
fit for exact-date capitalization or ten-year cap history; it would need additional
data or a reviewed policy. There is no reason to add this subscription first.
[EODHD historical-cap documentation](https://eodhd.com/financial-apis/historical-market-capitalization-api)

## 7. Macro events and company news need their own sources

Use the original publisher for schedule and release evidence:

- **CPI, PPI and employment:** [BLS release schedule](https://www.bls.gov/schedule/)
  and its linked releases. BLS also supplies an updating calendar; its displayed
  release times are Eastern Time.
- **GDP and Personal Income and Outlays/PCE:** [BEA release schedule](https://www.bea.gov/news/schedule).
- **Fed decisions, statements and minutes:** [Federal Reserve FOMC calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).
- **Economic measurements and vintages:** [FRED API](https://fred.stlouisfed.org/docs/api/fred/).
  Treat series observations separately from scheduled announcement events. A FRED
  observation fetch is not a company-news feed or a complete news-monitor setup.

For each watchlist company, the planned N1 monitor needs reviewed company IR,
filings, regulator/legislative and relevant ecosystem sources, plus an appropriately
licensed news feed where useful. Keep announcement facts separate from the model's
stock-specific interpretation. A scheduled CPI release is not yet its actual value;
a legislative proposal is not an enacted law; a relevance match is not a causal
price forecast. The CRCL/OpenUSD/CLARITY/Arc examples define the breadth of relevant
sources to discover, not a fixed list that replaces discovery for other stocks.

N1's scheduler, relevance checks, assessments and in-app/desktop/email delivery
remain implementation work. Buying a financial-data plan does not activate them.
See the [N1 feature contract](../../features/N1-news-and-macro-agent.md).

## 8. Vendor inquiry to copy

> I am building equityEval, a private personal US equity research application.
> I need to persist raw API responses and source-linked immutable calculation
> snapshots in a local database and backups; display prices, company fundamentals
> and calculated sector ratios only to myself; and preserve reproducibility over
> time. Please confirm the plan and written rights required for these uses,
> including raw and derived data retention after cancellation.
>
> Please provide sample data and endpoint entitlements for a complete dated US
> operating-equity roster, issuer/share-class/ADR identifiers, current and historical
> sector/industry assignments, issuer-wide common-equity capitalization on specified
> dates, common-stockholder earnings, quarterly and annual statements with original
> filing/acceptance dates, and delisted companies. Are historical observations revised
> retrospectively, and can I retrieve versions known on earlier dates? What history,
> daily/bulk-call and bandwidth limits apply? Is the classification proprietary or
> separately licensed GICS? Please distinguish private display rights from any future
> sharing or public application rights.

No inquiry has been sent. No account has been created or subscription purchased
for this guide.

## 9. Ready-to-connect checklist

1. Verify the seven selected issuers/instruments and their dated filing/profile coverage; preserve the fictional Figma fixture separately.
2. Retain archived MSFT/RBLX annual evidence as regression checks and inspect blocked values. Do not replace any of the seven user choices with them.
3. Obtain compatible source rights and verified sample coverage before paying for scale.
4. Review common-earnings, capitalization, membership and snapshot/API contracts.
5. Configure source identities, permissions, quotas, dated symbol bindings and credentials.
6. Connect the internal ingest stages to immutable real calculation snapshots and the UI.
7. Reconcile several displayed figures to original sources; test gaps, reruns, revisions,
   failed refreshes and reopening a saved snapshot.
8. Expand only after the selected-company pilot passes; full-sector completeness and
   point-in-time historical claims have separate acceptance criteria.

This sequencing preserves the fundamentals 3/5/10-year options, the four Sector
Explorer graphs and source drilldowns, and the news/watchlist backlog while the
UI is redesigned. It does not relax calculation or coverage rules to make a chart
look populated.
