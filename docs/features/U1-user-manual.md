# U1 — User manual and terminology guide

Status: user-authorized deliverable, requested 2026-09-12.
Delivery: alongside the finished product, before release is called complete.

The manual must teach a new user how to operate EquityEval and how to interpret
its financial and economic terminology. It is a product deliverable, not a
substitute for completing the interface. Draft and update it as features land,
then verify every step against the built application.

## Contents

- Installation, first launch, source configuration and a clear first-analysis walkthrough.
- Searching and adding a stock to a watchlist; choosing exchange/share class;
  following progress; removing a stock; rerunning analysis and comparing history.
- Reading the overview, financial statements, ratios, valuation ranges,
  assumptions, sensitivities and provenance; understanding missing/stale data.
- Choosing as-filed-by-date versus latest-reported history; restatements,
  filing dates, reporting periods and retrieval vintages with a worked example.
- Setting/confirming assumptions and understanding why a model may be unavailable.
- Configuring macro/watchlist news coverage, alert lead times, quiet hours,
  in-app/desktop/email delivery, pause/mute controls and delivery failures.
- Inspecting and editing stock topics; distinguishing company, competitor and
  regulatory coverage from macro events; tracing evidence and metric history;
  reading conditional verdicts, counterevidence, confidence and changed assessments.
  Include the CRCL/Open USD/CLARITY/Arc example without presenting it as a forecast.
- Explain circulation versus transaction volume versus revenue, reserve income,
  distribution costs, monetization, testnet versus production, legislative stages,
  materiality and observed price reaction versus claimed causation.
- Continuous background news discovery, source coverage, effective polling cadence,
  last successful checks, collection delays and catch-up after outages; quiet hours
  control delivery while collection continues. Example topics are not a fixed list.
- Local-worker availability, laptop sleep and the requirements for always-on alerts.
- Glossary with plain-English definitions, units, a small worked example where
  useful, and how the term affects interpretation. Cover ticker, exchange, CIK,
  ordinary shares/ADS, annual/quarterly/YTD/TTM, revenue, income, cash flow, capex,
  debt, enterprise/equity value, EPS/dilution, P/E and other implemented ratios,
  DCF/FCFF/WACC/terminal value/growth, sensitivity versus probability, CPI/PPI,
  core/headline inflation, monthly/yearly change, FOMC, yields, basis points,
  consensus/surprise, revisions, source provenance and quality flags.
- Troubleshooting, data-source/model limitations, and supported versus planned features.

## Format and acceptance

Maintain a versioned Markdown manual with a searchable in-app Help view and
contextual glossary links/tooltips for important terms. Provide a printable/exportable
version from the same content; select the export format during UI integration.
Use actual interface labels and screenshots from the finished build. Keep worked
examples explicitly illustrative, dated if real, and consistent with the engine.
Do not invent investment recommendations or describe a sensitivity range as a
probability interval.

A new-user acceptance pass must follow the manual to add a stock, inspect a
source, handle missing assumptions, run analysis again, compare snapshots and
configure all three alert channels. Also follow a stock topic, correct an unrelated
match, inspect an assessment and its counterevidence, and mute its alerts. Broken
links, obsolete screenshots and
unimplemented steps fail the release check. Every implemented financial input
and headline output must have an accessible definition. Verify the numerical
examples against hand-computed cases and the tested engine, and cite primary
sources for economic-release definitions.

The initial [manual outline](../user-manual/README.md) is intentionally labelled
as planned content. The [data and history chapter](../user-manual/data-and-history.md) covers S2/S3 terminology.
The finished product walkthrough and live-alert instructions remain pending.

The [prices and macro chapter](../user-manual/prices-and-macro.md) now documents
S4a field meanings, native units, independent historical controls, coverage gaps
and reruns. Product screen walkthroughs remain pending the interface build.

## F1 fundamentals teaching requirements

The [new fundamentals specification](F1-fundamentals-guide.md) is planned for
S5/S6/S8b/S8d. Add a five-minute company first-pass walkthrough and contextual
“Why this matters” content for growth, profitability, cash generation, balance
sheet, valuation and returns on capital. Reuse one definition/formula/example
source in Help and the company view.

Explain TTM versus fiscal year versus quarter YoY; flow periods versus balance
sheet dates; percentage versus percentage-point changes; reported versus adjusted
or forecast EPS; PPE-capex FCF versus FCFF; dilution versus SBC; gross margin
versus unit economics; net cash versus restricted/reserve cash; common versus
consolidated scope; N/A versus N/M and usable versus covered inputs.

Teach selection of 3-, 5- and 10-year history, sample dates/counts and exclusions,
why a band can be unavailable, and why a historical percentile is not intrinsic
value. Explain loss transitions, extreme ratios, freshness and sector limitations.
Use the six source fixtures as explicitly synthetic examples, checked against the
engine. Test keyboard/mobile access to definitions and provenance, shared snapshot
identity in Overview/Ratios, and the separate previous result after refresh failure.
This is a manual requirement, not a claim these screens exist today.

The [fundamentals calculation chapter](../user-manual/fundamentals.md) now covers
the tested first S5 source formulas, fractions/percentage points, precision and
3/5/10-year history limits. API/UI steps and the complete six-fixture walkthrough
remain pending their implementing slices.

## D1b development guide

`/help` now contains a five-minute walkthrough of the working Sector and Company
demonstrations, 52 searchable definitions, contextual anchors, explicit source
and history limits and a printable full glossary. This does not finish U1:
centralized Markdown/Help content, current primary-source macro citations and
new-user acceptance of real watchlist, analysis and three-channel alert setup
remain required before release. See [D1b](../milestones/D1b-company-news-help.md).
