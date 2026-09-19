# F1 — Guided fundamentals

Status: first S5 source-metric/history slice implemented on 2026-09-19; full feature remains in progress.
User direction: read the supplied spec, check conflicts and reuse, place the work
in existing milestones, and finish current work first. The user also explicitly
requested retaining 5–10-year history as an option.

S4a was completed first at `5eeec7e` / `milestone/s4a`; the working tree was clean
before this planning branch, `codex/fundamentals-plan`. S4b, source activation,
engines, API, UI and monitoring retain their recorded outstanding scope.

## Source and authority

The [original DOCX](../originals/fundamentals/EquityEval_Fundamentals_Implementation_Spec.docx)
is preserved byte for byte, with a [checksum manifest](../originals/fundamentals/manifest.json)
and [searchable transcription](../originals/fundamentals/source-text.md).
References such as B029 identify document-order blocks in that transcription;
A1–A5 are the attachment's release acceptance criteria.

The attachment supplies proposed feature requirements. Its imperative wording,
example route, status names and thresholds do not independently authorize code,
new schemas, new data providers or changed financial policies. This integration
records the user's requested direction and the concrete work still needing review.
The original ZIP specifications remain unchanged. Decisions are tracked as D020,
D021 and D022 in the [decision register](../decisions.md).

## Product scope

Add a beginner-friendly Fundamentals view within the planned S8b Ratios area,
with the same saved result summarized in S8d Overview. Aim for a first pass in
about five minutes. Present Growth, Profitability, Cash generation, Balance sheet
and Valuation in that order, with Returns on capital expandable. Definitions,
formulas, limits and provenance stay reachable from the company page.

Default financial period is proposed as TTM, accompanied by latest-quarter YoY;
fiscal-year and historical views remain available. Balance-sheet dates and quote
dates remain separately visible. For historical comparisons, provide **3-, 5- and
10-year options**. The attachment proposes 3 years as the default; retaining 5
and 10 years is an explicit user requirement, not deferred scope. Do not shorten
a selected window silently when history is insufficient.

Return factual observations and at most three distinct review prompts. No
aggregate stock score, automatic conviction, buy/sell action, price target,
bargain/value-trap verdict or universal quality threshold. F1 labels do not feed
the future human conviction rubric. Specialized issuers get factual rows and
“Sector-specific interpretation needed” until their profile is reviewed.

News monitoring stays in N1, full watchlist reanalysis in W1, and the manual in
U1. F1 does not replace these features, change the DCF default decision D004 or
resolve P0 valuation-range semantics D005. No screenshot ingestion, cash-runway
estimate, new live provider, peer engine or sector valuation model is added here.

## First implementation checkpoint

Following planning commit `c1f2697`, the user requested “implement the next step.”
The [first source-metric slice](../design/s5/source-metrics.md) implements an
internal evidence projection, reported amounts, supported revenue YoY growth,
gross/operating/consolidated-net margins, PPE-capex FCF and FCF margin, plus
3/5/10-year percentile math over already eligible samples. It reuses existing
selection, concept, period, unit and scope records. The [metric inventory](../design/s5/metric-inventory.md)
keeps every original S5 family and its outstanding dependency visible.

No source fetching, stored metric statuses, API, snapshot publication or screen
is added. Explicit history policy arguments are not production defaults. D022
records the bounded implementation; remaining F1-01–10 reviews remain open.

## Reuse and verified gaps at the S4a checkpoint

This table records the planning baseline; the first implementation above adds
the source-only core layer without changing the source contracts below.

| Existing component | Reuse | Work still required |
| --- | --- | --- |
| [Concept enum](../../packages/schema/concepts.py) and S1 reviewed mappings | The 40 concepts and generated TS vocabulary; exact issuer, scope, unit and accession constraints | A concept name does not prove ticker coverage. EBIT, common equity and income available to common are not approved concepts. Review additions or return unavailable. |
| [PIT selection](../../packages/schema/pit.py): `PitQuery`, `read_statement`, `read_statements`, `SelectedFact`, `StatementSelection` | Pinned filing/capture cutoffs, history modes, revisions, source URLs, resolution/observation IDs and input hashes | No TTM/YoY/ratios engine exists. Compose compatible selections outside the pure engine; do not discard blocking flags or invent historical knowledge. |
| [SEC normalization types](../../packages/ingest/financial_types.py), archive and publisher | Raw evidence, reported periods, units, original text, transformations and immutable publication | YTD-to-quarter and TTM bridges are derived calculations. Source precision and derived lineage must reach the core/API; existing selection objects are not the finished metric contract. |
| [Market selection](../../packages/schema/market_selection.py): `select_price`, `MarketSelection` | Exact raw close, quote/security/currency identity, adjustment metadata, dated capture and attempt provenance | No latest-completed-session price lookup or reviewed complete calendar coverage. S4a normalized batches remain unknown/partial/unavailable; archived numeric prices alone do not establish usable market inputs. |
| [W1 workflow](../../packages/schema/workflow.py) and [analysis pipeline](../../packages/ingest/analysis_pipeline.py) | Durable add/rerun requests, lease fencing, retries, independent SEC/price/macro stages and preserved executions | Add the fundamentals stage after contract review. No fundamentals snapshot/result store exists; reuse the analysis input/snapshot design already deferred from S2. One-security source plans do not authorize fetching sibling classes for issuer-wide market cap. |
| [Core package](../../packages/core/AGENTS.md), test harness and golden cohort | Pure calculation boundary, tests before math, reviewed filing fixtures and restatement regression | Core is reserved, not a completed ratio engine. New hand-calculated tests and independent plausible-wrong-number review are required. |
| S8a provenance plan and [U1 manual](U1-user-manual.md) | One evidence drawer, glossary content, shared financial periods and company navigation | UI and public API are not built. F1 must use one result source across Ratios, Overview and Help. |

Selectors and persistence perform I/O outside `packages/core`. Pure functions
receive immutable, fully described inputs. Reuse the existing provenance and
selection contracts through a reviewed projection; do not introduce a parallel
fundamentals ingestion pipeline or perform financial arithmetic in the browser.

Source precision needs particular care: `SelectedFact` has original numeric
text/transform evidence but no precision fields. The [inline filing reader](../../packages/ingest/filing.py)
retains XBRL `decimals` and `precision`; Company Facts JSON digits do not prove
original filing precision. Review how this evidence reaches the calculation
projection and its unavailable state. Do not infer precision from digit count.
This may reuse retained metadata rather than requiring a new SQL column.

## Metric coverage and dependencies

The formulas and eligibility details remain in source B029, B031, B035 and
B053–B057. This table assigns their implementation rather than claiming coverage.

| Metric family | Proposed implementation | Prerequisite or unavailable case |
| --- | --- | --- |
| Revenue and growth | S5: selected amounts, quarter YoY, TTM versus prior TTM | Comparable periods, scope/currency/basis; prior revenue must be positive for a growth percentage. |
| Diluted EPS and growth | S5: reported EPS, amount change and profit/loss/break-even transitions | Both EPS values positive for percentage growth. Verified TTM diluted EPS requires its own reconstruction policy; never blindly sum EPS or substitute net income divided by convenient shares. |
| Gross, operating and net margins | S5: divide eligible amounts by positive revenue; changes in percentage points | Net margin uses matching consolidated income. Derived gross profit is separately labelled core output, not fabricated reported `gross_profit`. |
| CFO, PPE-capex FCF and FCF margin | S5: CFO less reviewed positive cash-PPE outflow | Align YTD/quarter/TTM periods and source signs. Do not apply `abs()` blindly to anomalous amounts. Issuer-adjusted FCF and S7 FCFF are separate concepts. |
| Share count change and SBC context | S5; action-dependent support after S4b | Period-end ownership shares and weighted-average diluted shares stay distinct. Split/class/ADS compatibility needs evidence; SBC is not itself dilution. |
| Cash, net debt and debt/equity | S5 when coverage is proven | Current-debt coverage is incomplete; define debt/lease composition, positive matching equity and unrestricted cash. Exclude reserve/client assets; unknown debt is not zero. |
| Interest coverage | S5 registry with explicit gap until approved | Reviewed EBIT is absent; no silent operating-income substitution. Positive interest denominator; zero interest is N/M. |
| Trailing P/E | S5 with S4b/coverage gates | Raw close and verified diluted TTM EPS on the same instrument, currency and split basis. Nonpositive EPS is N/M; total-return/dividend-adjusted prices are disallowed. |
| P/S and P/FCF | S5 with reviewed equity-value input | Prove complete single-class ownership or review multi-class valuation/composition and W1 source scope. No applying one class's quote silently to all issuer shares. Positive revenue/FCF required. |
| ROA | S5 | Consolidated net income and positive beginning/end assets matching annual/TTM flow dates; both distinguishable from zero at source precision. |
| ROE | S5 registry with explicit gap until approved | Income available to common and common equity are absent as dedicated concepts. Parent income/equity are not automatic substitutes. Nonpositive endpoints/sign changes/near-zero precision make it N/M. |
| Forward P/E and PEG | Define formulas and synthetic tests in S5; production N/A without approved estimates | No estimate source exists. Preserve horizon, EPS basis, provider/known-at dates; no revenue-growth substitution. Review PEG's estimate-use scope against SPEC 2.4 before adding a provider. |
| ROIC/vendor ROI and enterprise cash-flow multiples | Deferred policy work, with S7/P1 dependencies | Reviewed NOPAT/tax/invested capital and compatible EV/FCFF definitions first. Generic EV divided by CFO-minus-capex is not introduced. |

Other original S5 ratio families (P/B, earnings/FCF yields, EV/EBITDA, EV/Sales,
EV/EBIT, DuPont, working capital and composites) remain in the broader ratio
backlog. The S5 review must explicitly disposition each; F1's first-release list
does not silently delete them or approve unsafe substitutes.

## Conflicts and proposed resolutions

These are review items under D021. User-requested 5/10-year choices and preserved
project boundaries are settled direction; the detailed policies below are not
silently frozen by adding this plan.

| ID | Conflict or ambiguity | Planned resolution and gate |
| --- | --- | --- |
| F1-01 | SPEC 4.1 requires 5–10-year history and value/own-history/peer triples; B047 proposes 3 years and B048 defers peers. | Retain selectable 3/5/10-year windows as requested. Propose 3-year default. S5 reviews exact window endpoints, quarter-end sampling, count/coverage minimums and interpolation; S6 includes window and policy version in request/cache identity. Show missing benchmarks explicitly; peers stay P1. No silent fallback to a shorter window. |
| F1-02 | SPEC 4.1 categorical warnings and conviction UI conflict with neutral observations/no stock score (B042–B048). | Use evidence-backed facts, context and deduplicated review prompts in F1. Preserve technical quality flags and source evidence. Neither thresholds nor coverage become return confidence or human conviction. Review message rules in S5. |
| F1-03 | Derived gross profit, TTM/YTD, net debt and ROE may look like filling missing normalized facts. | Derived results live only in core with exact operands/formula lineage. Keep reported facts unchanged. Review period reconstruction, signs, source precision, consolidated/common scope, debt/lease components, restricted cash and unsupported sectors before numeric publication. New concepts/mappings require sequential schema review. |
| F1-04 | B023's proposed `instrumentId`, `inputFactIds`, single `asOf` and six statuses do not directly match existing evidence identities/time semantics. | In S5 preflight/S6, map equity instrument, security and quote identifiers explicitly; carry typed observation/resolution/market IDs, source capture/attempt references and revisions. Separate valuation/evaluation date, inclusive filed-date cutoff, capture timestamp and source-known limits. Preserve existing NULL/flags; N/A and N/M are presentation states over a reviewed metric projection. |
| F1-05 | B020/B060 retain old results after failure and cache identical calculations; W1 requires a new execution/snapshot on explicit rerun, and S4 refuses to revive older usable source values. | Keep the new request/failure visible and show the previous immutable snapshot separately with its own date. Never relabel it as the refreshed result or use its old labels as current. Reuse cached calculation payloads only if exact inputs/policies match; each explicit W1 rerun creates a new request/execution and a new immutable analysis snapshot ID even when values do not change. It may reference identical cached F1 calculation payloads; retries within one logical request still publish at most one analysis snapshot. Review snapshot storage/publication in S6. |
| F1-06 | B035 price/EPS and issuer market cap assume usable prices, compatible shares and complete equity coverage. | S4b reviews action/ADS corrections; a separately reviewed S4 coverage/calendar slice defines completed sessions and eligibility. Single-class evidence or explicit multi-instrument composition is required. Unsupported price-dependent metrics stay unavailable while source-only fundamentals can proceed. |
| F1-07 | Three years with at least 12 quarterly samples leaves little tolerance for missing observations; optional 5/10 years need their own sufficiency rules. Historical captures may not exist. | S5 reviews exact inclusion boundaries and per-window minimums; propose targets of 12/20/40 completed quarter ends, without padding, interpolation of missing financial data, or extending the selected window. Disclose eligible/excluded counts and dates. Distinguish filing-date reconstruction using later archives from strict workspace-as-known history. Insufficient eligible samples mean no band/rank. |
| F1-08 | B045/B054/B056 thresholds (1 pp, extreme margins, 180/450/90 days) are new product policy; no reviewed trading/filing calendar exists. | Version and review freshness, reporter cadence, expected-filing rules, precision and trend sensitivity at S5, exposed by S6. Historical freshness uses the historical evaluation date. Unknown freshness cannot become valid; source age alone is not a trading calendar. |
| F1-09 | B025 coverage counts well-sourced N/M while labels require valid inputs; stale/unsupported applicability is underspecified. | S5/S6 review numerator, denominator, zero-applicable behavior and status precedence. Fix applicability by metric/profile policy, never by source availability. Count fully evidenced N/M as covered but not usable/rankable; expose valid, N/M, stale, missing, invalid and unsupported counts separately. No stock score. |
| F1-10 | Original ROIC/EV-FCF and broad S5 metrics exceed B035's safer first release; later peers need at least 10 in F1 while SPEC 4.4 discusses regression with fewer than 8. | Record explicit per-metric deferred/unsupported status in S5. S7 handles FCFF with a reviewed enterprise definition. F1 benchmark eligibility and a future regression's diagnostic sample policy are separate P1 decisions. Forward estimates remain optional and never enter DCF. |

The historical collection window must include inputs before its first sample:
a 3/5/10-year series of TTM multiples needs approximately 4/6/11 years of flows,
plus filing lag; TTM-YoY may need another year. Select exact compatible fiscal
periods rather than treating these rough lengths as permission to sum any facts.
Every historical sample must apply its own filing/source-known cutoffs, freshness
and compatible price/EPS basis. A later capture is not proof the workspace had
that data then. Unknown publication time cannot be invented from a date.

The session policy must cover venue/time zone, holidays, early closes, daylight
saving, publication delay and suspended/unsupported sessions. Decide whether a
quarter-end sample uses facts known at the selected session close or quarter-end
end-of-day; an after-close filing cannot be silently used in a session-close
sample. Freeze an evaluation timestamp so reopening a saved result does not
recompute age-dependent statuses using the wall clock. New evaluations can
produce new snapshots; saved evaluations remain unchanged.

## Placement in the existing milestones

| Slice | Milestone | Deliverable and dependency |
| --- | --- | --- |
| F1 planning | Historical planning checkpoint `c1f2697`, after S4a completion | Preserved source, conflict/reuse audit, requirements and updated plan; no feature code. |
| F1 source eligibility | S4b plus explicit S4 calendar/coverage review | Corporate-action/ADS and complete-session evidence for price-dependent ratios and history. No reopening accepted S4a schema without a concrete additive review. Core source-only work is not blocked on live-provider activation. |
| F1a core and fixtures | [S5](../milestones/S5-ratios.md) | Metric registry, pure period/growth/margin/cash/leverage/return/multiple calculations, 3/5/10-year comparisons, versioned interpretation/freshness, coverage and hand-computed tests. First review F1-01–10 and input gaps; do not add concepts opportunistically. |
| F1b API and saved results | S6 | Review proposed `GET /companies/{issuerId}/fundamentals`, query and immutable snapshot retrieval, status/provenance projection, snapshot persistence, W1 stage outputs and exact cache keys. Generate OpenAPI/TS with no-diff checks only after approval. |
| Shared valuation boundary | S7 | Reuse eligible facts and definitions, preserve the distinction between CFO-minus-PPE FCF and FCFF. F1 does not require forecast/DCF completion to show supported facts. |
| F1c company view | S8a/S8b | Reuse S8a provenance drawer; build Fundamentals inside Ratios with financial period, 3/5/10-year history choice, explanations, dates, loading/error/N/A/N/M/stale states and accessible charts. |
| Shared result and watchlist | S8d/W1 | Overview and Ratios share snapshot ID/coverage. Add/rerun includes the fundamentals stage, partial outcomes and immutable history; test concurrent/retried/out-of-order completion. |
| Learning and release | U1 with S8b/S8d | Definitions, formulas, limitations, examples and five-minute first pass from the same content; keyboard/mobile walkthrough and complete release acceptance. |

Retain the existing milestone IDs and sequential shared-contract gates. F1 is a
slice through those milestones, not a replacement build sequence. N1 proceeds
under its own reviewed source/API/worker/delivery work; F1 may link to it once it
exists but does not add automatic fundamentals alerts in this request.

## Requirements and acceptance trace

| Requirement | Source blocks | Owner and verification |
| --- | --- | --- |
| Five-section beginner view, TTM/quarter YoY/year/as-of, separate quote/balance dates | B003–B020 | S8b/U1; new user completes first pass, dates/units survive small screens. |
| Decimal values, units, fractions, metric periods, statuses and full lineage | B022–B025, B052, B055 | S5/S6; no NaN/infinity, exact decimal-string round trips, incompatible inputs rejected. |
| Revenue/EPS/margins/CFO/FCF/share/cash/debt/interest formulas | B028–B031 | S5; hand-calculated valid and invalid cases; explicit coverage gaps. |
| Multiples, common-scope returns, estimate/EV/ROIC limitations | B034–B039 | S5/S4b/S7; raw-price/share-basis checks, no invented forecast or EBIT/common-equity substitute. Optional 25% revenue filter remains an optional labelled filter, not a quality boundary. |
| Neutral loss/growth/trend wording and deduplicated top-three review prompts | B042–B048 | S5/S8b; three comparable quarterly YoY rates, 1 pp boundary cases, fixed priority and metric-ID tie-breaks. Data issues precede cash/debt, operating trends, valuation context. |
| History percentile bands and comparisons | B047–B048 plus user 5/10-year request | S5/S6/S8b; choose 3/5/10 years, review per-window minimums, interpolate at `(n−1)p`, P25/P75 equality stays within middle range; show exclusions and no band without sufficient samples. Peers deferred. |
| Period construction and precision | B053–B055 | S5; four nonoverlapping quarters or validated annual-plus-YTD bridge, compatible edition YTD subtraction, no averaging margins or balance-sheet flows, source-precision near-zero guards. |
| Freshness, sector applicability and coverage | B025, B056–B057 | S5/S6; time-relative policy tests, stale labels suppressed, N/M covered but unranked, bank/insurer/REIT/float issuer limitations, reserve cash excluded, no runway. |
| Immutable snapshots, exact cache scope, failed refresh and reruns | B020, B052, B060 | S6/W1; saved results unchanged by new filings/rules; no old-source revival; new immutable analysis snapshot ID for each explicit rerun even on exact payload cache reuse; retries cannot duplicate snapshots. Include history window and all policy/revision/cutoff/evaluation fields. |
| Definitions/provenance and shared UI result | B019–B020, B061, B072 | S8a/b/d/U1; keyboard evidence drawer, accessible charts, metric glossary, one snapshot in Overview/Ratios, reviewed and unmapped ticker flows. |

All source acceptance cases A1–A5 (B068–B072) remain required. Preserve these six
synthetic examples from B065 as test specifications, not claims about any stock:

| Synthetic inputs | Expected result |
| --- | --- |
| Price 60; EPS 2; forecast EPS growth 15% | P/E 30×; PEG 2.0; no investment verdict. This fixture does not authorize a forecast provider. |
| Price 10; EPS −0.50; prior EPS −1.00 | P/E N/M; loss narrowed by 0.50 per share, no positive percentage-growth label. |
| Revenue 1m; operating income −72.7m | Margin −7,270%; show both amounts and review flag; no assumption that the filing is erroneous. |
| CFO 12m; PPE capex 20m; revenue 100m | FCF −8m; margin −8%; P/FCF N/M. |
| P/E 8×; insufficient history; revenue −12% YoY | Show measured values; no below-range/bargain/value-trap claim. |
| Net income −10m; beginning/end equity −20m | ROE N/M, despite arithmetic yielding +50%; explain nonpositive equity. |

Add profit-to-loss, both/one zero EPS endpoints, positive net cash, restricted
cash, split/dilution, absent class coverage, mixed scopes/currencies/earnings
bases, missing/near-zero denominators, stale inputs, failed refresh, unsupported
sectors, restored historical snapshots and cache separation across 3/5/10 years.
Test window edges and insufficient/just-sufficient sample counts for each window,
weekends/holidays/early closes, after-close filings and a two-for-one split with
compatible versus incompatible EPS bases. A multi-class fixture with 10m shares
at 10 and 5m at 20 must yield 200m of equity value, not a one-class shortcut.
Fractions for derived percentage metrics must not change archived macro units.
Verify −4.55K% displays as −4,550%, margins use percentage points, related loss
signals produce one prompt and no unsupported input earns a favorable rank.

Before numeric code is committed, run the repository's required full checks,
real `test-core` cases, golden/restatement regressions and independent numeric
review. Remove the core empty-suite marker only when real tests are added. A
planning update is not evidence that these new acceptance tests already pass.

## Next handoff

Planning was committed at `c1f2697`; the first bounded calculation slice is now
implemented on `codex/s5-source-metrics`. Read the [S5 milestone](../milestones/S5-ratios.md)
and [numeric review](../design/s5/review.md) before continuing. Next work reviews
compatible fiscal/YTD/TTM assemblies, applicability and remaining metric inputs.
S4b/calendar work gates price/share metrics; S6 owns public projections and W1
snapshot publication. Do not seek repeat approval for completed bounded scope.
