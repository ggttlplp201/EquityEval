# User-requested feature list

These extend the supplied build plan. Original ZIP documents and the supplied
fundamentals DOCX remain unchanged. Implementation status is tracked here and
in the milestone index.

| Feature | Requested | Accepted behavior | Build placement | Status |
| --- | --- | --- | --- | --- |
| [N1 — News and macro agent](N1-news-and-macro-agent.md) | 2026-09-11 | Continuous news-site discovery of new announcements across watchlist stocks, plus US CPI/PPI/Fed events; evolving competitor/product/legal/ecosystem topics, supporting data and conditional impact assessments; in-app, desktop and email heads-ups. Refined 2026-09-12; [details](N1-stock-topic-monitoring.md), [CRCL example](N1-crcl-topic-example.md). | S2 design; source/API contracts; N1 workers and delivery alongside S8. | Requirements captured; not running. |
| [W1 — Watchlist and reanalysis](W1-watchlist-analysis.md) | 2026-09-12 | Search/add a resolved stock; run the full applicable analysis automatically; explicit rerun; progress, gaps and preserved history. | S2 membership/request design; pipeline after engines; S8 UI and N1 linkage. | S2 durable requests and SEC/price/macro source stages implemented; full engine pipeline and UI follow. |
| [U1 — Manual and terminology](U1-user-manual.md) | 2026-09-12 | Teach setup/use, analysis interpretation, financial/economic terms, watchlist and alert workflows; contextual glossary and printable help. | Draft as features land; verify against the finished build before release. | Source-data, market and fundamentals calculation chapters drafted; final product walkthrough pending. |
| [F1 — Guided fundamentals](F1-fundamentals-guide.md) | 2026-09-19 | Explain growth, profitability, cash, debt and valuation with source-backed metrics, neutral review prompts and accessible definitions; selectable 3/5/10-year history. | S4b/coverage prerequisites where needed; S5 calculations; S6 API/snapshots; S8b Ratios/S8d Overview; W1/U1 integration. | First S5 source-metric/history math slice implemented; full metrics, API, snapshots and UI remain pending. D022 records scope; remaining D021 review stays open. |
| [X1 — Sector Explorer](X1-sector-explorer.md) | 2026-09-19 | Graph-first sector totals versus typical-company ratios, history, distributions and growth/valuation scatter; visible coverage, exclusions and methods. | After current fundamentals prerequisites; separate X1 core/UI slices, shared S6/source review and real-universe acceptance. | S5 period prerequisite complete; core/development graphs verified (950 tests); real-data/source and S6 contract acceptance remain open. |

A finished release requires the manual, watchlist workflow and configured alert
channels to pass their acceptance checks. Capturing a feature here is not a claim
that its UI, analysis engine or delivery service is implemented.
