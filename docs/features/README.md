# User-requested feature list

These extend the supplied build plan. Original ZIP documents and the supplied
fundamentals DOCX remain unchanged. Implementation status is tracked here and
in the milestone index.

| Feature | Requested | Accepted behavior | Build placement | Status |
| --- | --- | --- | --- | --- |
| [N1 — News and macro agent](N1-news-and-macro-agent.md) | 2026-09-11 | Continuous news-site discovery of new announcements across watchlist stocks, plus US CPI/PPI/Fed events; evolving competitor/product/legal/ecosystem topics, supporting data and conditional impact assessments; in-app, desktop and email heads-ups. Refined 2026-09-12; [details](N1-stock-topic-monitoring.md), [CRCL example](N1-crcl-topic-example.md). | S2 design; source/API contracts; N1 workers and delivery alongside S8. | Requirements captured; not running. |
| [W1 — Watchlist and reanalysis](W1-watchlist-analysis.md) | 2026-09-12 | Search/add a resolved stock; run the full applicable analysis automatically; explicit rerun; progress, gaps and preserved history. | S2 membership/request design; pipeline after engines; S8 UI and N1 linkage. | S2 durable requests and SEC/price/macro source stages implemented; full engine pipeline and UI follow. |
| [U1 — Manual and terminology](U1-user-manual.md) | 2026-09-12 | Teach setup/use, analysis interpretation, financial/economic terms, watchlist and alert workflows; contextual glossary and printable help. | Draft as features land; verify against the finished build before release. | Requirements, outline and source-data chapters drafted; final product walkthrough pending. |
| [F1 — Guided fundamentals](F1-fundamentals-guide.md) | 2026-09-19 | Explain growth, profitability, cash, debt and valuation with source-backed metrics, neutral review prompts and accessible definitions; selectable 3/5/10-year history. | S4b/coverage prerequisites where needed; S5 calculations; S6 API/snapshots; S8b Ratios/S8d Overview; W1/U1 integration. | Planning incorporated after S4a completion; conflicts/reuse documented, D021 review open; no feature code started. |

A finished release requires the manual, watchlist workflow and configured alert
channels to pass their acceptance checks. Capturing a feature here is not a claim
that its UI, analysis engine or delivery service is implemented.
