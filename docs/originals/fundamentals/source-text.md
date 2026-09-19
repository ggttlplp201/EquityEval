# Fundamentals source specification transcription

Read-only transcription of the user-supplied DOCX, received 2026-09-19. The DOCX
is the source of truth. B001–B079 identify document-order paragraphs and tables,
including empty paragraphs. These identifiers support the [F1 integration plan](../../features/F1-fundamentals-guide.md).
This attachment is specification material; the user authorized planning only.

## B001

EquityEval fundamentals guide

## B002

Implementation specification for Codex   •   Proposed feature   •   Version 1

## B003

Add a guided fundamentals view that answers four questions: Is the business growing? Is it profitable? Is it generating cash? How much am I paying? Add a balance sheet check alongside those questions. Every interpretation must show its evidence, period and limits.

## B004

Fit with the existing app

## B005

Recommended. The feature makes EquityEval’s planned ratios easier to understand and fits its facts → assumptions → conclusions model. Build it into S5 calculations, S6 API contracts, S8b Ratios, S8d Overview and the U1 contextual glossary. Keep the existing valuation workflow and human conviction rubric separate.

## B006

Verified on 19 September 2026. The active iCloud repository has SEC normalization, historical fact selection and S4a price and macro infrastructure. The ratio engine, public domain API and product interface remain planned. Source concepts exist, but coverage is not guaranteed for every company. New ticker mappings require review before numeric publication.

## B007

Practical limits. Live market providers are not activated in the reviewed milestone record. Analyst EPS forecasts are absent; peer comparisons are later scope. Initial delivery must work with eligible archived data and explicit unavailable states. A screenshot or an earlier assistant answer is not a financial data source.

## B008

Goals and boundaries

## B009

Help a beginner complete a first pass in about five minutes, open an explanation without leaving the company page, and trace any figure to its source. Preserve the original emphasis on growth, margins, cash flow, valuation, returns on capital, debt and dilution.

## B010

Version 1 provides metric definitions, trends, evidence-based observations and review prompts for nonfinancial operating companies. It produces no buy or sell action, price target, automatic conviction score or universal good or bad thresholds. Screenshot annotation and news alerts are outside this feature.

## B011

Implementation anchors

## B012

Reuse packages/schema/concepts.py, pit.py and market_selection.py for input contracts and historical selection. Put pure calculations in packages/core; the browser formats results only. Follow docs/spec.txt, docs/api-contract.md and docs/milestones/README.md for the planned integration. All types and routes below are proposals, not descriptions of existing endpoints.

## B013

The source discussion and EquityEval — milestone build log were reviewed, together with the active repository at ~/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval. The saved Documents/ChatGPT checkout was empty.

## B014

(Empty paragraph)

## B015

User experience and result contract

## B016

Company page flow

## B017

Open Fundamentals from the company page. Default to trailing twelve months (TTM), with the latest quarter shown as year over year (YoY). Offer fiscal year and historical as of views; display the selected financial period and quote date above the results. TTM means twelve months of flows, not the date of a balance sheet.

## B018

Show five sections in order: Growth, Profitability, Cash generation, Balance sheet and Valuation. Put gross margin and net margin under Profitability, dilution under Growth, and ROE or ROA in an expandable Returns on capital section. Keep raw amounts beside ratios when the denominator is small or the ratio is extreme.

## B019

Each metric displays value, units, period, trend and a short observation. “Why this matters” opens its plain-language definition, formula, interpretation limits and evidence drawer. “Review these items” lists at most three distinct issues and links to the relevant rows. The Overview reuses this same result, including its coverage and as of date.

## B020

States and accessibility. Use loading placeholders, retry on source error, and retain the dated previous result if refresh fails. Show N/A for missing or unsupported data and N/M for a mathematically unsuitable ratio. A stale value remains visible with its age but cannot drive labels. Text and icons carry meaning independently of color; drawers and charts support keyboard navigation.

## B021

Proposed typed projection

## B022

Extend existing source and selection types rather than creating a second ingestion model. Monetary and ratio calculations use Decimal; serialize finite values as decimal strings. Store percentages as fractions: 0.25 displays as 25%.

## B023

| Record | Required fields |
| --- | --- |
| FundamentalsSnapshot | issuerId, instrumentId, snapshotId, financialPeriod, basis, asOf, capturedBefore, historyMode, inputManifestId, rulesVersion, policyVersion, metrics[], observations[], coverage |
| MetricResult | metricId, value\|null, unit, currency, start/end or instant, basis, status, reasonCodes[], inputFactIds[], formulaVersion, comparison\|null |
| Source metadata | Reuse accession, filing date, source URL and locator, observation/resolution IDs, transforms and quality flags. Retain price timestamp, retrieval time, scope and restatement revision. |
| Observation | ruleId, dimension, kind, messageKey, parameters, evidenceMetricIds[], priority, benchmarkRef\|null. Kind: fact, context or review. |
| Optional estimate or benchmark | Provider, knownAt, horizon, EPS basis, sample members and dates, sample count, method and version. Absent in v1 unless an approved source exists. |

## B024

(Empty paragraph)

## B025

Status is valid, missing, not_meaningful, invalid, stale or unsupported. Only valid inputs drive financial interpretations; data-quality prompts may explain any status. Keep raw values in provenance; never coerce missing to zero. Coverage = metrics with complete valid-source inputs / applicable metrics; well-sourced N/M counts as covered. Show usable, stale, missing and unsupported counts separately. Source availability must not change applicability.

## B026

(Empty paragraph)

## B027

Metric definitions for the first release

## B028

Use consistent currency, entity scope, accounting basis and periods. These formulas are app conventions; reconcile them to the approved concept mappings. Amounts are flows for the selected period unless marked as a balance sheet date. [1, 2]

## B029

| Metric | Calculation and interpretation |
| --- | --- |
| Revenue growth | current revenue / comparable prior revenue − 1; require prior revenue > 0. Use quarter versus the same fiscal quarter last year, or TTM versus prior TTM. Sales growth does not establish profit growth. |
| EPS and EPS growth | Use reported diluted EPS with its basis. Growth = current / prior − 1 only when both are positive. Otherwise show the EPS change and loss or profit transition. Buybacks and dilution can change EPS independently of operating performance. |
| Gross margin | gross profit / revenue. If needed, derive gross profit as revenue − matching cost of revenue. Positive gross margin shows profit after cost of sales; it does not prove viable unit economics. |
| Operating margin | operating income / revenue. Shows profit or loss after operating expenses; compare trends and similar business models. |
| Net profit margin | net income / revenue using the same consolidated scope. Includes financing, tax and other effects; retain parent versus consolidated income distinctions. |
| Operating cash flow | Reported cash from operating activities (CFO). Show alongside net income; persistent divergence prompts a working-capital or noncash-item review, not a fraud conclusion. |
| Free cash flow and margin | FCF = CFO − cash purchases of PPE (v1 capex), normalized to a positive outflow. FCF margin = FCF / revenue. Label the capex definition; keep adjusted issuer FCF separate. Negative FCF means CFO did not cover that capex. |
| Share count change | matching split-adjusted share count / prior count − 1. Use period-end shares for ownership change; label weighted-average diluted shares separately. Show stock-based compensation as context, not as identical to dilution. |
| Cash and net debt | At one eligible balance sheet date, net debt = interest-bearing debt − unrestricted cash and equivalents. Negative net debt means net cash. Exclude restricted cash and customer or reserve assets unavailable to the company. |
| Debt to equity | interest-bearing debt / matching equity at the same date. Require equity > 0; specify lease treatment. Never interpret a negative ratio as low leverage. |
| Interest coverage | period EBIT / positive interest expense, if the EBIT mapping is supported. EBIT ≤ 0 means operating earnings do not cover interest. Zero interest is N/M, not infinity; do not silently substitute operating income for EBIT. |

## B030

(Empty paragraph)

## B031

Margin denominators must be positive. Compute TTM margins from summed eligible amounts, never by averaging quarterly percentages. Margin changes are percentage points (pp): 10% to 12% is +2 pp.

## B032

(Empty paragraph)

## B033

Valuation and returns on capital

## B034

Valuation multiples describe price relative to a financial measure. They do not independently establish fair value. Reported, adjusted, normalized and forecast earnings must remain separately named series. [3, 4]

## B035

| Metric | Definition and eligibility |
| --- | --- |
| Trailing P/E | Raw close / diluted TTM EPS for the same instrument, currency and split basis; never use dividend-adjusted or total-return prices. EPS ≤ 0 → N/M with loss or zero-earnings reason. P/E 20× means $20 of share price per $1 of annual EPS, not revenue or a promised return. |
| Forward P/E | price / positive forecast diluted EPS. Show exact fiscal year or next-twelve-month horizon, provider and estimate date. No dated approved estimate → N/A; never invent a forecast from revenue growth. |
| PEG | positive P/E / (positive expected annual EPS growth fraction × 100). Thus 30× / 15 = 2.0. Record P/E basis, EPS growth horizon and forecast date. Missing growth → N/A; zero, negative or loss-base growth → N/M. Never substitute revenue growth. |
| Price to sales | market capitalization / positive TTM revenue. Market cap must cover the issuer’s equity classes on a consistent currency basis; a single-class quote must not silently value all classes. Compare margins and capital intensity. |
| Price to FCF | market capitalization / positive TTM CFO-minus-capex FCF. Nonpositive FCF → N/M. This cash-flow convention is not automatically cash distributable to shareholders. |
| ROE and ROA | ROE = income available to common / average common equity; ROA = consolidated net income / average total assets. Average means beginning and end of the flow period. Require matching scope and annual or TTM flows. ROA requires positive beginning and ending assets, distinguishable from zero at source precision. |
| ROIC and vendor ROI | Defer until a reviewed NOPAT, tax and invested-capital policy exists. Undefined vendor ROI is not ROIC. Do not estimate missing preferred distributions or common equity just to fill ROE. |
| EV to cash flow | Defer generic EV/FCF. Enterprise value requires a compatible enterprise cash-flow definition; do not pair EV silently with CFO-minus-capex. Later EV/FCFF needs separately defined FCFF, debt, cash, preferred equity and noncontrolling interests. |

## B036

(Empty paragraph)

## B037

What the original shortcuts should become

## B038

High P/E can reflect expected growth, business quality, risk, temporarily depressed earnings or a high price. Low P/E can reflect weak expectations, cyclical peak earnings or a lower price. Low PEG indicates a lower P/E relative to the chosen EPS forecast; it does not prove fast growth or a bargain.

## B039

Revenue growth above 25% may remain an optional user filter labeled “Revenue YoY above 25%.” It must not become a universal quality threshold or a PEG input. EPS growth above revenue growth is a prompt to check margins, taxes and shares, not proof of operating leverage.

## B040

(Empty paragraph)

## B041

Interpretation and labeling rules

## B042

No aggregate stock score. Return independent observations for each dimension. Coverage is data completeness, not confidence that a stock will rise. Do not feed these labels into the planned human conviction rubric. Deduplicate related signals: negative earnings, net margin and P/E should not count as three separate investment risks.

## B043

| Condition | Required wording or behavior |
| --- | --- |
| Positive or negative growth | “Revenue grew X% YoY” or “Revenue fell X% YoY.” Use the exact comparison period. Zero change: “Revenue unchanged.” With a nonpositive prior base, show amounts and “Growth percentage unavailable.” |
| Loss transitions | Both EPS values negative: “Loss narrowed” if current EPS is higher, otherwise “Loss widened” or “Loss unchanged.” Negative to positive: “Turned profitable”; positive to negative: “Turned loss-making.” One zero endpoint: “Break-even transition”; both zero: “Remained break-even.” |
| Trend across quarters | Use the latest three consecutive comparable quarterly YoY rates. All successive increases >1 pp: “Growth rate rising”; all decreases <−1 pp: “Growth rate falling”; all absolute changes ≤1 pp: “Growth broadly stable”; otherwise “Mixed trend.” |
| Negative FCF | “Operating cash flow did not cover capital spending.” Link CFO, capex, cash and debt. Financing or asset sales can still raise total cash; do not infer imminent failure. |
| Lower multiple plus decline | P/E or P/FCF below its historical 25th percentile plus negative revenue YoY in the latest two quarters → “Lower multiple; review revenue decline.” Stable or recovering revenue still needs margin, cash and debt review. No bargain or value-trap verdict. |
| Higher multiple plus growth | Show the multiple comparison and the measured growth separately. Revenue growth does not establish whether earnings will justify the price. |
| Broken or high PEG | Broken inputs receive the specific unavailable reason. A valid high PEG reports price relative to the chosen EPS forecast. Never output “value trap” or “overvalued” from PEG alone. |

## B044

(Empty paragraph)

## B045

The 1 pp trend tolerance is a proposed display sensitivity, not an investment boundary. Keep it in versioned configuration and test boundaries. Fewer than three valid rates → “Trend unavailable”; show the individual rates that are available.

## B046

Comparison and attention policy

## B047

Use a trailing three-year window with at least 12 eligible calendar quarter-end samples of the same metric. Use the last completed session on or before quarter end and facts known then. Compute percentiles by linear interpolation at zero-based position (n−1)p. Below P25 is “Below own-history middle range”; above P75 is “Above own-history middle range”; equality is “Within middle range.” Show dates, sample size and excluded N/M or missing quarters. This band is not intrinsic value.

## B048

Defer peer labels to the planned comparables work. Later require at least 10 eligible comparable companies, a disclosed peer list, matching basis and period rules. Without an eligible benchmark, never say high or low. Sort review prompts by data problems, then cash and debt, then operating trends, then valuation context; use fixed rule priority and metric ID to resolve ties.

## B049

(Empty paragraph)

## B050

Safeguards and implementation sequence

## B051

Financial and data safeguards

## B052

Historical selection must pin the existing filing and capture cutoffs, history mode and revisions. A restatement or rule update creates a new result; it must not rewrite an earlier snapshot. Preserve the source URL and calculation lineage through the API and interface.

## B053

Build TTM flows from four nonoverlapping eligible fiscal quarters, or an equivalent validated annual-plus-YTD bridge. Derive standalone cash-flow quarters from cumulative YTD facts within one compatible reporting edition. Do not sum overlapping annual and quarterly data or average balance sheet amounts into TTM flows. Use verified TTM diluted EPS; unsupported reconstruction stays unavailable.

## B054

No NaN or infinity in responses. Zero or negative revenue makes margins N/M. Nonpositive beginning or ending equity, equity sign changes, or equity indistinguishable from zero at source precision make ROE N/M even when two negatives yield a positive ratio. Treat large ROE cautiously after buybacks or leverage changes. Add a data-review flag for |margin| > 100%; display the true result and absolute amounts without assuming a reporting error.

## B055

Normalize raw units before calculation. Display −4.55K% as −4,550%, never −4.55%; percentages are not currency units. In v1 this is a formatting test, not screenshot ingestion. Validate extreme inputs against period, currency, scale and source precision. For denominators indistinguishable from zero at reported precision, return N/M rather than an unstable ranked ratio.

## B056

Use a versioned freshness policy. Proposed defaults: financial period end older than 180 days for quarterly reporters or 450 days for annual reporters; price older than the latest completed trading session; estimates older than 90 days. Missing expected new filings also trigger review. Historical runs apply dates relative to their as of cutoff. Stale inputs disable dependent financial labels and comparisons; data-quality explanations remain visible.

## B057

Banks, insurers, REITs and other specialized issuers receive “Sector-specific interpretation needed” and factual rows only until a reviewed profile exists. Early-stage or tiny-revenue businesses emphasize absolute cash use and available cash. Exclude client deposits and reserve backing assets from spendable cash. Do not publish a cash-runway estimate in v1. [2, 4, 5]

## B058

Build in three slices

## B059

1  Core and fixtures. Add the metric registry and pure calculations in packages/core; reuse existing approved concepts and selectors. Add hand-calculated fixtures for valid and invalid bases, scope, periods and units. Report unavailable concepts explicitly. No new live provider is required.

## B060

2  API and provenance. Propose GET /companies/{issuerId}/fundamentals with instrumentId, period, basis, asOf, capturedBefore and historyMode. A snapshotId request returns its immutable saved result. Cache by all selection fields, input manifest and rule and policy versions, including freshness and display sensitivity. Refresh resolves inputs again and creates a new snapshot when inputs or evaluation dates change. Return coverage explicitly.

## B061

3  Interface and regression checks. Integrate Ratios, Overview, glossary and provenance drawer using one result source. Rephrase categorical legacy quality flags as evidence-backed review prompts. Link valuation and news features only when they exist. Run the repository’s required checks plus the acceptance cases on the next page.

## B062

(Empty paragraph)

## B063

Examples and acceptance criteria

## B064

All amounts below are synthetic test fixtures, not claims about CRCL or the company in the earlier screenshots.

## B065

| Fixture | Expected result |
| --- | --- |
| Price $60; EPS $2; forecast EPS growth 15% | P/E 30×; PEG 2.0. Explain both bases. No buy, overvalued or growth-stock verdict. |
| Price $10; EPS −$0.50; prior EPS −$1.00 | P/E N/M; “Loss narrowed by $0.50 per share.” No positive percentage-growth or cheap-stock label. |
| Revenue $1m; operating income −$72.7m | Operating margin −7,270%; “For every $100 of revenue, operating loss was $7,270.” Show both amounts and data-review flag. |
| CFO $12m; capex $20m; revenue $100m | FCF −$8m; margin −8%; P/FCF N/M. Financing proceeds could still increase cash. |
| P/E 8×; no eligible comparison history; revenue −12% YoY | “P/E 8×” and “Revenue fell 12% YoY.” No below-range, bargain or value-trap label. |
| Net income −$10m; beginning/end equity −$20m | ROE N/M despite raw arithmetic yielding +50%. Explain nonpositive equity. |

## B066

(Empty paragraph)

## B067

Release acceptance

## B068

A1  Formula fixtures match hand calculations, including PEG 30 / 15 = 2 and capex sign normalization. Negative, zero and missing denominators never emit NaN, infinity or a favorable rank.

## B069

A2  Quarter YoY, TTM and fiscal-year selections stay distinct. Tests reject mixed currencies, scopes, earnings bases, overlapping periods, total-return prices and incompatible share adjustments. A later restatement cannot change a saved historical result.

## B070

A3  Each label resolves to rule ID, version, dates and source-backed metrics. Stale or unavailable inputs permit data-quality prompts only. N/M with complete inputs counts as covered. Test history sample limits, percentile equality, trend boundaries and cache isolation across cutoffs and policy versions.

## B071

A4  All fixtures above pass. Add cases for profit-to-loss, zero bases, positive net cash, dilution, restricted cash, failed refresh and unsupported sectors. Related negative earnings signals produce one review item.

## B072

A5  Every metric’s meaning and provenance are reachable by keyboard in the company view. Small screens retain units, dates and unavailable reasons. Overview and Ratios show the same snapshot; a reviewed ticker works end to end and an unmapped ticker shows explicit coverage gaps.

## B073

Evidence and source notes

## B074

Project basis: docs/spec.txt; docs/api-contract.md; docs/design/s3/implementation.md; docs/milestones/S4-prices-macro.md; packages/schema/{concepts,pit,market_selection}.py. Current implementation and planned work are distinguished on page 1. Numerical thresholds and labels here are proposed product policy, not validated predictors of returns.

## B075

[1] SEC  Beginners Guide to Financial Statements

## B076

[2] SEC  Non GAAP Financial Measures  Question 102 07

## B077

[3] CFA Institute  Market Based Valuation  Price and Enterprise Value Multiples

## B078

[4] NYU Stern  Damodaran  Valuation Project Questions

## B079

[5] Nareit  Funds From Operations

## Embedded source links

Retained from the DOCX; not newly verified by this planning update.

- <https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide>
- <https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/non-gaap-financial-measures>
- <https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples>
- <https://pages.stern.nyu.edu/adamodar/New_Home_Page/project/prques.htm>
- <https://www.reit.com/glossary/funds-operation-ffo>
