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
as planned content. S2 includes no completed product walkthrough or live alerts.
