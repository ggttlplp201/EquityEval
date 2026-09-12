# S4 FRED / ALFRED research

Research date: 2026-09-12. Status: evidence and proposed decisions for D009;
not an approved source policy or schema. The later full H.15 ZIP scope check
found third-party Moody's series; its complete payload is unapproved for
production retention or redistribution, despite the selected Treasury inputs. This document interprets the adopted
specification, sections 2.3 and 3.1, alongside the implemented S3 archive contract.
The initial review used official documentation, terms and series-information
pages. No authenticated API request was made, no key was read, and no FRED
financial payload was saved. A subsequent authorized direct-Board research
capture is documented in the appendix. Contract-test numbers are invented;
the appendix explicitly identifies its actual source observations.

## Permission finding

The current [FRED terms](https://fred.stlouisfed.org/legal/) permit some personal
uses but separately prohibit API use connected with archiving/caching/database
incorporation (API Prohibitions l) and software/AI development or training (k).
The general Services prohibitions contain parallel restrictions. The API section
does not state an archive exception. Third-party series retain their own rights.
Applications must attribute the data, display the prescribed non-endorsement
notice, and, for other users, link and bind users to the API terms. Limits can
change. **App decision proposed:** retain the archive requirement and keep live
FRED ingestion unapproved until the provider supplies permission covering this
app's actual storage and use. An API key alone does not resolve that conflict.

This finding is specific to the reviewed FRED service. It is not a claim that the
underlying government's independently published data is unavailable. Research and
synthetic contract tests can proceed. No provider contact or subscription change
is authorized by this document.

## Verified API semantics

[FRED v1 observations](https://fred.stlouisfed.org/docs/api/fred/series_observations.html)
uses `series_id`, `file_type=json`, observation-date bounds and real-time-date
bounds. Real-time bounds default to today. `units=lin` preserves native levels;
`frequency` can aggregate to a lower frequency. Results expose `count`, `offset`
and `limit`; the observation-page limit is 1–100,000. Ascending observation-date
sort is available. `output_type=1` returns real-time periods, 2 all observations
by vintage, 3 only new/revised observations by vintage, and 4 initial releases.
Explicit `vintage_dates` is an alternative to real-time bounds.

[Real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)
are inclusive at both boundaries and describe when information was known before
changing. They differ from the date the economic observation measures. Today's
historical series is therefore a current view, not automatically a historical
knowledge view. The documented full range is 1776-07-04 through 9999-12-31.

[ALFRED download semantics](https://alfred.stlouisfed.org/help/downloaddata)
define a row's real-time start/end as the first/last vintage where that revision
was current. An unended revision's end is unknown; text downloads represent it
with a dot. That text-file rule must not be copied blindly to JSON date fields.
Initial-release output and new/revised-only output have different meanings from
an all-observation snapshot.

[ALFRED help](https://alfred.stlouisfed.org/help) says releases are generally
added within one business day. Release dates use the source's date when known,
otherwise a provider date, otherwise first FRED availability. Consequently a
vintage date does not establish an exact intraday public-release timestamp, and
provider metadata need not prove the original source's publication time.

[Series vintage dates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html)
list new/revised data dates and exclude releases where the series did not change.
They are not a complete event calendar. The
[series metadata endpoint](https://fred.stlouisfed.org/docs/api/fred/series.html)
provides series identity, native units, frequency, seasonal adjustment, notes,
real-time bounds and a series-level `last_updated`. App interpretation: the latter
is not an observation's first-publication timestamp.

The [v2 release endpoint](https://fred.stlouisfed.org/docs/api/fred/v2/release_observations.html)
explicitly defines numeric values as strings and `"."` as missing. It uses cursor
pagination, unlike v1, and warns that a release request can mix updated and
not-yet-updated series. The inspected v1 example contains no missing observation;
acceptance should still verify the intended v1 missing marker against a permitted
pinned response before enabling live data. Do not substitute v2 bulk current
release output for a v1 historical-vintage request.

## Native definitions that must survive normalization

| Series | Definition relevant to S4 | Native metadata / source |
| --- | --- | --- |
| DGS10 | Nominal 10-year constant-maturity market yield, investment basis | Percent, daily, not seasonally adjusted; Board H.15. [Series](https://fred.stlouisfed.org/series/DGS10) |
| DGS2 | Nominal 2-year constant-maturity market yield, investment basis | Percent, daily, not seasonally adjusted; Board H.15. [Series](https://fred.stlouisfed.org/series/DGS2) |
| DFF | Effective federal funds rate | Percent, daily (7-day), not seasonally adjusted. [Series](https://fred.stlouisfed.org/series/DFF) |
| T10Y2Y | Treasury 10-year less 2-year spread | Percent, daily, not seasonally adjusted; since 2019 its inputs come directly from Treasury. [Series](https://fred.stlouisfed.org/series/T10Y2Y) |
| CPIAUCSL | All-items urban CPI level | Index 1982–1984=100, monthly, seasonally adjusted; BLS. It is not already a percent inflation rate. [Series](https://fred.stlouisfed.org/series/CPIAUCSL) |
| UNRATE | U-3 unemployment rate | Percent, monthly, seasonally adjusted; BLS household survey. [Series](https://fred.stlouisfed.org/series/UNRATE) |
| BAMLH0A0HYM2 | ICE high-yield option-adjusted spread | Percent, daily close, not seasonally adjusted. Notes limit available observations to three years from April 2026 and restrict reproduction/distribution. [Series](https://fred.stlouisfed.org/series/BAMLH0A0HYM2) |

Proposed application treatment: begin the numerical contract with DGS10 and one
revised monthly synthetic series; keep other identities explicit and separately
reviewed. Preserve native percent as percent. A later core adapter may convert a
synthetic 4.25 percent to 0.0425 once, recording that transform. Never write 4.25 as
a fractional discount rate, nor re-scale 0.0425 a second time. Keep nominal/real,
maturity, index base and seasonal basis separate. A negative spread is a valid
possible amount. Do not replace T10Y2Y with subtraction of asynchronously updated
DGS observations or derive inflation inside ingestion.

## Authentication and operational constraints

The [v1 key documentation](https://fred.stlouisfed.org/docs/api/api_key.html)
requires a key on every request, a distinct key for each application, and each
application user to use their own key. V1 transmits it as `api_key` in the query.

Proposed secret handling: inject the key only at dispatch; keep a redacted
canonical request and hash only public, meaning-bearing parameters. Do not store
the key in URLs, failure strings, logs, fixtures, archived manifests, Redis keys
or user-facing provenance. Use a non-secret account/limiter identity. HTTP-client
exception text can contain the full request URL and must not pass through to the
attempt record unchanged. A redirected request must never carry the key to an
unapproved host.

The [official error documentation](https://fred.stlouisfed.org/docs/api/fred/errors.html)
states up to 120 requests per minute before HTTP 429 and warns that ignoring
throttling can cause a temporary block. It lists 400, 404, 423, 429 and 500 errors.
It does not specify a guaranteed per-key versus per-IP partition in that statement.

Proposed app policy: one shared FRED coordinator across its workers, initially
60 requests/minute with no accumulated burst; count metadata, pages and retries.
Retain S3's bounded dispatch/lease/archive discipline with provider-specific
cooldowns. Missing credentials, permission or coordinator fails before dispatch.
Treat 400/404 and access/locked responses as explicit gaps; honor Retry-After on
throttling; never rotate keys or reset a request budget to escape a block.

## Proposed request, selection and replay contract

These are app design choices for sequential contract review, not provider claims.
They do not create new tables or change the financial concept enum.

1. Pin endpoint version, allowlisted series identity, native metadata capture,
   exact observation interval, real-time policy, ordering, page boundaries and
   parser/normalizer revision. Request untransformed native-frequency values.
2. A historical source-vintage query at date D explicitly sets both real-time
   bounds to D. A current query also resolves and records its chosen date rather
   than relying on an implicit moving default. Preserve row bounds exactly;
   a one-day response window alone does not establish a revision's full lifetime.
3. Keep three clocks distinct: measured period, provider vintage, local complete
   capture time. A later capture can support labeled source-vintage reconstruction
   when its explicit vintage covers D; it cannot satisfy a strict local
   captured-before-D query. Missing historic vintage remains unavailable.
4. Date-only vintage eligibility is labeled as a date-based reconstruction. An
   intraday cutoff cannot infer availability at midnight or at the market open.
   Exact source release evidence is a separate capability; a scheduled CPI/Fed
   event is not evidence that actual values have been published.
5. Read every bounded page and archive it before parsing. Verify count/offset,
   sort, response filters and metadata coherence. Repeated page, missing page,
   count drift, premature empty page or conflicting duplicate remains incomplete.
   Never call a truncated prefix the entire history. Each page has its own capture.
6. Parse numeric strings exactly with Decimal; retain raw spelling and locator.
   A supported explicit missing marker becomes unavailable plus a quality issue.
   Absent row, missing field, JSON null and malformed numeric string remain
   distinguishable. Reject booleans/nonfinite values/duplicate JSON keys; never
   interpolate, zero-fill, forward-fill or invent a publication timestamp.
7. Select the latest *eligible observation date*, then its eligible revision.
   Missing/retracted latest evidence must not silently revive an older numeric
   value. A policy to use the last available earlier date must be explicit and
   show its original date and age; it never creates a value on a missing date.
8. All pages, native metadata, source policy and quality/completeness outcomes
   form a pinned input manifest. New capture is new evidence even if bytes match.
   Replay verifies archive hash/count and never fetches newer data after failure.
   Conflicting overlapping revisions are unavailable until resolved, not ordered
   by arbitrary UUID or insertion time.

Proposed hand-computed acceptance cases, all synthetic:

| Case | Expected behavior |
| --- | --- |
| Native percent `"4.25"`, zero `"0.00"`, negative spread `"-0.25"` | Exact Decimal values and native units survive; no implicit engine scaling. |
| `"."` versus absent row, null, `"NaN"`, boolean | Missing reasons remain distinct; no zero or prior-value substitution. |
| Revision A 100.0 valid 2024-02-01…2024-02-14; B 101.0 from 2024-02-15 | Feb 14 selects A, Feb 15 selects B under inclusive date semantics. |
| Both revisions claim Feb 15 with different values | Flag conflict; do not choose a plausible number. |
| January measurement first available in February | January historical cutoff cannot select it. |
| Vintage Feb 15 captured March 1 | Source-date reconstruction may use it when requested explicitly; February local retrieval cutoff rejects it. |
| Metadata says index, response requested as percent change | Refuse native-level publication; no silent unit switch. |
| Two pages, second missing or count changes | Explicit incomplete dataset; prior evidence retained under its own manifest. |
| Current and initial-only payloads mixed | Reject incompatible view; no partial faux as-reported series. |
| Key appears in fake HTTP exception or redirect location | No secret persists or reaches another host; failure remains inspectable. |
| Corrupted archive on replay | Fail reproduction without any HTTP request. |
| Date-only release versus an intraday model cutoff | No invented release hour or timestamp certainty. |

## Separately reviewed direct-source alternative

The [Board's copyright policy](https://www.federalreserve.gov/disclaimer.htm)
permits copying and distributing Board-site information unless otherwise marked,
asks for attribution, excludes third-party material from that blanket permission,
and protects seals/logos. This is independent of FRED's service terms.

The [H.15 release page](https://www.federalreserve.gov/releases/h15/) publishes
nominal constant-maturity Treasury rates in percent per annum and links to
[its XML ZIP](https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip).
The ZIP URL was initially read from the release-page hyperlink. A subsequent
authorized research download, its verified members and its limits are recorded
in the appendix; this is separate from provisioning a production adapter.

The [Board's July 16, 2026 transition notice](https://www.federalreserve.gov/data/data-download-fred-information.htm)
says the DDP custom-package builder will be removed the week of November 9, 2026,
while historical XML will remain on release pages. Additional package/DDP
retirement follows. Proposed choice: review the release-page XML capability,
not a new dependency on DDP's retiring custom query interface. Its full ZIP may
require a separate bounded archive/container contract and safe member validation.

[Treasury's documented XML feed](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed)
is another option: HTTPS GET at
`/resource-center/data-chart-center/interest-rates/pages/xml` on
`home.treasury.gov`, with `data=daily_treasury_yield_curve` and either
`field_tdr_date_value=YYYY` or `field_tdr_date_value_month=YYYYMM`.
All-years mode starts at page 0, returns 300 rows by default, and continues until
there are no entries. The documented par-yield history starts in 1990. The feed
uses OData data types, including null. The later bounded request outcome is
recorded below; no production adapter was provisioned.

Treasury's [interest-rate description](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics)
identifies these as par yields derived from indicative market prices; 3:30 p.m.
input collection is not evidence of API publication at that instant. The reviewed
[Treasury site-policy index](https://home.treasury.gov/subfooter/site-policies-and-notices)
and [privacy policy](https://home.treasury.gov/subfooter/privacy-policy) did not
supply an explicit data-copy/reuse statement comparable to the Board's. Do not
substitute TreasuryDirect/Fiscal Service terms for this host's own policy.

**Initial recommendation, narrowed by the full-payload check below:** direct
Board H.15 provides suitable Treasury definitions, but its complete ZIP also
contains third-party series. No production policy can be approved for that ZIP
until its entire raw retention scope is resolved. Selecting three normalized
series does not remove the other data from the retained response.
Historical rates downloaded today prove their values in today's capture, not
what every past user knew. Label that limitation and preserve future captures;
never manufacture ALFRED-style vintage intervals. This source change does not
provide CPI, PPI or Fed-event notifications, which remain N1 capabilities, nor
ERP/beta defaults, which remain a separate D009/S7 decision.


### Final bounded alternative-source check, 2026-09-12

The official [Treasury nominal-yield dataset catalog record](https://catalog.data.gov/dataset/interest-rate-statistics-daily-treasury-yield-curve-rates)
identifies Office of Debt Management as publisher, dataset `015-DO-020`, public
access and a CC0 license. Its metadata was modified 2025-02-11 and checked by the
catalog 2026-09-10. This is concrete dataset-specific reuse evidence, unlike the
policy index above. Its distribution points to the legacy
`treasury.gov/.../TextView.aspx?data=yield` page. The HTTPS equivalent was observed
redirecting to the current [Treasury interest-rate page](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics?data=yield),
which links the [official XML migration notice](https://home.treasury.gov/developer-notice-xml-changes).
That notice explicitly names `daily_treasury_yield_curve` as the replacement
nominal par-yield feed and documents table redirects. Together these establish
the dataset-to-current-feed linkage for this research scope; they do not license
other Treasury datasets or FRED service use.


One September 2026 XML request was then authorized with an 8 MiB complete-body
cap and no credentials. It returned HTTP 200, passed complete-body size/encoding
checks and safe XML parsing, but the temporary research scope validator refused
an additional `BC_30YEARDISPLAY` field before saving the response. The process
exited with its bytes only in memory. Consequently this attempt has **no retained
body, byte hash, exact byte count or usable replay fixture**. The [attempt record](../../research/s4/evidence/treasury-yield-research-attempt.json)
preserves this failure without presenting it as a verified capture. A separately
authorized single replacement request then saved the complete body before field
review; its successful evidence is recorded below. No further retries were made.

The migration notice separately establishes a critical missing-data convention:
the current feed omits a property element when unavailable; the old feed used
`m:null=true`. A future adapter must distinguish absence from numeric zero and
check both element existence and content. No actual current-month missing row
or selected numeric spot check was retained from the failed first attempt.

The Board also publishes a [preformatted Treasury constant-maturities package review](https://www.federalreserve.gov/datadownload/Review.aspx?filetype=csv&from=&label=include&lastObs=&layout=seriescolumn&rel=H15&series=bf17364827e38702b42a58cf8eaa3f78&to=&type=package).
Its displayed eleven series are all Treasury maturities: `RIFLGFCM01_N.B`,
`RIFLGFCM03_N.B`, `RIFLGFCM06_N.B`, and `RIFLGFCY01_N.B`, `02`, `03`, `05`, `07`,
`10`, `20`, `30` with the same `RIFLGFCY` prefix and `_N.B` suffix. It includes the
2-year and 10-year inputs and does not list Moody's. This is a narrower candidate
than the complete H.15 ZIP. Only its official package metadata was inspected;
no download response was captured, so full-body scope and format are unverified.
The [announced DDP transition](https://www.federalreserve.gov/data/data-download-fred-information.htm)
also makes its service horizon a review condition. It supplies no calendar-daily
federal-funds series. Neither candidate activates a source or changes S4 scope.


## Appendix: direct H.15 capture verified 2026-09-12

The authorized research download of the exact published XML ZIP completed at
2026-09-12 09:55:49.444355 UTC with HTTP 200, identity HTTP encoding and
4,281,072 complete entity bytes. SHA-256:
`cd55cf4eb2f90147a418cd4e9b7fb6529d6f8c7f48135a87ead2c79221681b13`.
See [request and verification manifest](../../research/s4/evidence/frb-h15-manifest.json),
and [selected metadata/row evidence](../../research/s4/evidence/frb-h15-series-review.json).
The selected JSON is explicitly an extract, never a replacement full capture.
The full ZIP is restricted local research evidence in ignored
`var/research-quarantine/s4/`; it is not tracked, public or a test fixture.
No production replay is permitted from it while raw retention rights remain
unresolved. The manifest retains its original complete byte count/hash and
records the quarantine location; the downloaded bytes were not modified.

The initial 32 MiB compressed / 64 MiB decoded research cap accepted the ZIP but
refused the declared XML expansion. Before decoding the large member, the parent
review approved a 128 MiB decoded cap using the same capture. No second request
was made. All five member sizes, SHA-256 hashes and ZIP CRCs were then verified.
Declared and actual total decoded bytes both equal 71,014,964. No paths were
extracted to the filesystem and no 70 MB duplicate XML is checked in.

| Member | Decoded bytes | Verification result |
| --- | ---: | --- |
| H15_discontinued.xsd | 10,237 | CRC/hash and complete well-formed XML; no schema imports loaded. |
| H15_H15.xsd | 10,219 | CRC/hash and complete well-formed XML; no schema imports loaded. |
| H15_data.xml | 70,757,908 | CRC/hash and complete streaming XML parse. |
| H15_struct.xml | 96,648 | CRC/hash; bare DOCTYPE causes strict XML parse refusal. |
| frb_common.xsd | 139,952 | CRC/hash; bare DOCTYPE causes strict XML parse refusal. |

Archive names were checked for traversal, absolute paths, duplicate names,
symlinks and encryption. XML parsing disabled DTD loading, entity resolution,
network access and recovery. The data member contains no DTD/entity declaration.
External `schemaLocation` references were retained as text and never followed.
The two refused metadata members were retained unchanged; selected code-list
labels were inspected as literal text in those verified bytes. This is not a
claim of full XSD validation or successful parsing of the refused members.

The data XML uses SDMX 1.0's `message:MessageGroup`; active H.15 `Series` elements
use `http://www.federalreserve.gov/structure/compact/H15_H15`; `Obs` elements
use `http://www.federalreserve.gov/structure/compact/common` and carry `TIME_PERIOD`, `OBS_VALUE` and `OBS_STATUS`. The full document contained
263 series and 923,533 observations. This is a format/evidence check, not a
published normalization batch or acceptance of every series for app use.

The subsequent complete series-description scan identified eight Moody's
corporate-yield series in `H15_discontinued`: `RIMLPAAAR_N` and `RIMLPBAAR_N`,
each with `.B`, `.WF`, `.M`, and `.A` frequencies. See the
[scope metadata](../../research/s4/evidence/frb-h15-content-scope-review.json).
The Board policy does not confer blanket rights on indicated third-party
material. Complete-payload retention/reuse is therefore **unresolved**, and the
ZIP must not become a production capture or distributable golden fixture.
Filtering at normalization cannot repair that raw-payload issue.

Exact proposed identities, all with `UNIT="Percent:_Per_Year"`, `UNIT_MULT="1"`
and `CURRENCY="NA"`:

| Intended input | SERIES_NAME | FREQ | INSTRUMENT / MATURITY |
| --- | --- | --- | --- |
| Nominal 10-year Treasury | RIFLGFCY10_N.B | 9 | TCMNOM / Y10 |
| Nominal 2-year Treasury | RIFLGFCY02_N.B | 9 | TCMNOM / Y2 |
| Effective federal funds, calendar-daily | RIFSPFF_N.D | 8 | FF / O |
| Distinct business-day federal funds variant | RIFSPFF_N.B | 9 | FF / O |

The pinned structure's literal code list labels `8` as daily and `9` as business
day; unit multiplier `1` means one, not an exponent of ten. Status `A` is normal;
`NA`, `ND`, `NC` mean not available, no data and not calculable. Selected daily
rows use ISO `YYYY-MM-DD` measurement dates. Do not map monthly/weekly siblings
or the `RIFLGFCY10_XII_N.B` inflation-indexed series into the nominal daily input.
`CURRENCY="NA"` is source metadata and must not become an invented quote currency.
The complete Series-attribute inventory contains only these seven fields; no
seasonal-adjustment attribute is present. Preserve that absence. Native annualized
percent, investment basis, and nominal instrument codes do not prove a seasonal
adjustment flag. These measurement conventions are supported by the actual data
attributes and descriptive annotations, while the frequency/status/multiplier
labels above come from separately marked literal code-list inspection.

Actual source spot checks, preserving native percent with no conversion:

- `RIFLGFCY10_N.B`, 2026-09-10: `OBS_VALUE="4.95"`, `OBS_STATUS="A"`.
  The same measurement date is `4.56` for `RIFLGFCY02_N.B` and `3.63` for
  `RIFSPFF_N.D`, each status A.
- `RIFLGFCY10_N.B`, 1962-02-12: `OBS_VALUE="-9999"`, `OBS_STATUS="ND"`.
  This is an unavailable datum, not a negative yield. Missing-status handling
  must precede numeric publication, with a separate guard for sentinel/status
  contradictions.

These locators identify the unique selected series by `SERIES_NAME` and its
`Obs` by `TIME_PERIOD` in the member pinned above. All source numeric spellings
remain in the selected JSON. The header's `Prepared` value is
`2026-09-11T15:40:02`, which has no timezone. HTTP Last-Modified and local capture
completion are separate fields. None proves an individual observation's original
release instant or an ALFRED-style revision interval.

Proposed production limits, still a contract choice: 8 MiB complete ZIP body,
128 MiB total decoded members, a small allowlisted member inventory, and strict
parsing of only the reviewed data member. Additional schema members can be
preserved and integrity-checked without being interpreted. Unexpected growth,
changed format, unreviewed codes or a required unsafe declaration yields an
explicit source gap. A future growth allowance must be reviewed; no unbounded
extraction, automatic DTD relaxation, or external schema fetch is implied.


## Appendix: direct Treasury replacement capture verified 2026-09-12

The separately authorized replacement request returned HTTP 200 and 13,033
complete, unmodified entity bytes within the 8 MiB cap. See the
[full XML response](../../research/s4/evidence/treasury-yield-202609-e655415955c5.xml)
and [request, hash and scope manifest](../../research/s4/evidence/treasury-yield-manifest.json).
SHA-256: `e655415955c550b13f8ed20868c6cf56578387e82f3babdd39779bd2225b9e17`.
The manifest records exact UTC request/header/completion times and HTTP metadata.
The response was saved before semantic review. XML is fully well formed with
no DTD/entity declaration; parsing disabled entities, DTD loading and network.
No schema imports or linked entry URLs were followed, and no XSD validation is
claimed. These files are research evidence; no production batch was published.

All eight entries identify `TreasuryDataWarehouseModel.DailyTreasuryYieldCurveRateDatum`.
The complete body contains nominal Treasury maturity properties, the Treasury
30-year display property, IDs/dates and Atom feed metadata. No third-party series
or other interest-rate dataset was identified. This narrowly matches the linked
nominal-yield dataset's CC0 scope. Complete raw retention and selected numeric
normalization remain separate decisions.

The complete property inventory is `Id`, `NEW_DATE`, `BC_1MONTH`, `BC_1_5MONTH`,
`BC_2MONTH`, `BC_3MONTH`, `BC_4MONTH`, `BC_6MONTH`, `BC_1YEAR`, `BC_2YEAR`,
`BC_3YEAR`, `BC_5YEAR`, `BC_7YEAR`, `BC_10YEAR`, `BC_20YEAR`, `BC_30YEAR` and
`BC_30YEARDISPLAY`. The last field is preserved but remains an unsupported
optional property; its numeric purpose is not inferred from this sample.
Only `BC_2YEAR` and `BC_10YEAR` are reviewed normalized candidates.

The Atom namespace is `http://www.w3.org/2005/Atom`; property namespace `d` is
`http://schemas.microsoft.com/ado/2007/08/dataservices`; metadata namespace `m`
adds `/metadata` to that URI. Within each `entry/content/m:properties`, the two
selected fields have `m:type="Edm.Double"`; `NEW_DATE` has
`m:type="Edm.DateTime"`. Selected values are present, unique and finite in all
eight entries. Measurement dates range from `2026-09-01T00:00:00` through
`2026-09-11T00:00:00` and carry no timezone. Preserve their date meaning without
manufacturing a midnight publication instant. All inventoried fields are
present and nonempty here; no actual missing-value example was captured.

[Treasury's CMT FAQ](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions)
supports native percent and a simple annualized bond-equivalent basis for
semiannual coupon securities. This differs from compounded APY. The XML type
alone supplies neither that unit nor a seasonal-adjustment flag; preserve the
latter as unknown. Source spot check: for `NEW_DATE="2026-09-11T00:00:00"`,
`BC_2YEAR="4.63"` and `BC_10YEAR="4.96"`, unchanged native percent.

The feed and every entry have `updated="2026-09-12T02:01:04Z"`. That common value
is recorded as source metadata, not proof of each observation's original release
instant. No source-vintage intervals are provided. A future adapter can preserve
capture-based history from activation onward; it cannot claim retrospective
ALFRED-style reconstruction. This candidate covers nominal 2-year and 10-year
rates only in the proposed first normalization scope. It supplies neither
federal-funds observations nor macro-event alerts.
