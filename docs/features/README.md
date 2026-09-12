# User-requested feature list

These extend the supplied build plan. Original ZIP documents remain unchanged;
implementation status is tracked here and in the milestone index.

| Feature | Requested | Accepted behavior | Build placement | Status |
| --- | --- | --- | --- | --- |
| [N1 — News and macro agent](N1-news-and-macro-agent.md) | 2026-09-11 | US CPI/PPI/Fed events plus per-stock competitor/product/legal/ecosystem topics, supporting data and conditional impact assessments; in-app, desktop and email heads-ups. Refined 2026-09-12; [details](N1-stock-topic-monitoring.md), [CRCL example](N1-crcl-topic-example.md). | S2 design; source/API contracts; N1 workers and delivery alongside S8. | Requirements captured; not running. |
| [W1 — Watchlist and reanalysis](W1-watchlist-analysis.md) | 2026-09-12 | Search/add a resolved stock; run the full applicable analysis automatically; explicit rerun; progress, gaps and preserved history. | S2 membership/request design; pipeline after engines; S8 UI and N1 linkage. | Requirements captured; included in S2 proposal. |
| [U1 — Manual and terminology](U1-user-manual.md) | 2026-09-12 | Teach setup/use, analysis interpretation, financial/economic terms, watchlist and alert workflows; contextual glossary and printable help. | Draft as features land; verify against the finished build before release. | Requirements and outline captured. |

A finished release requires the manual, watchlist workflow and configured alert
channels to pass their acceptance checks. Capturing a feature here is not a claim
that its UI, analysis engine or delivery service is implemented.
