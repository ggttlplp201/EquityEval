# Milestone index

Canonical code location:
`/Users/leon/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval`

The Codex project is currently saved at the older Documents/ChatGPT path. Until
its saved path changes, any new task must explicitly use the canonical path
above. This repository and its commits are the implementation source of truth.

| ID | Status | Record | Task |
| --- | --- | --- | --- |
| S0 | Complete; Docker verification pending | [Scaffold](S0-scaffold.md) | `S0 — EquityEval scaffold and milestones` (ID in record) |
| S1 | Accepted for S2 — 2026-09-12 | [SEC reconnaissance](S1-sec-recon.md) | `EquityEval — milestone build log` (same task, user continued) |
| S2 | Complete for accepted storage/request scope; 124 tests | [Schema and PIT](S2-schema.md) | Same milestone build-log task |
| S3 | Complete for accepted scope; 440 tests; milestone/s3 | [SEC ingestion](S3-ingestion.md) | Same milestone build-log task; D008 accepted |
| S4 | S4a complete; 717 tests; milestone/s4a; S4b/live sources remain open | [Prices and macro sources](S4-prices-macro.md) | Same milestone build-log task |
| S5 | First source-metric/history slice implemented; full S5 in progress | [Ratios and guided fundamentals](S5-ratios.md) | D022 source core; calendar-period prerequisite complete before X1; S4b gates price/share ratios |
| S6 | Planned; include F1 result, snapshot and cache review | [API contract review/freeze](../api-contract.md) | After S5 |
| S7 | Planned | Forward DCF | After S6 |
| N1a–d | Requested; continuous discovery and stock assessments specified (D017/D018) | [News and macro agent](../features/N1-news-and-macro-agent.md) | Alongside S2–S8 contracts |
| W1 | Durable requests and SEC/price/macro source stages implemented; full pipeline/UI follow | [Watchlist and reanalysis](../features/W1-watchlist-analysis.md) | S2 → engines → S8/N1 |
| U1 | Development Help with searchable glossary; complete release manual acceptance pending | [Manual and glossary](../features/U1-user-manual.md) | Required before finished release |
| F1 | Source-metric/history core and bounded fictional Company page implemented; production feature pending | [Guided fundamentals](../features/F1-fundamentals-guide.md) | S5 → S6 → S8b/S8d/U1; preserve 3/5/10-year history options |
| X1 | Core and fictional graphs verified; 950 tests; milestone/x1-core-graphs | [Sector Explorer](X1-sector-explorer.md) | Separate feature; graph-first, source/contract gaps explicit |
| R1 | Design/acceptance and seven-issuer profile evidence packet delivered; application work follows UI/pilot sequence | [Business-aware research](../features/R1-business-aware-research.md) | D026; explanations, small thesis continuity and reviewed profiles |
| D1 | Updated Figma TXT handover with R1; original MCP concept partial | [Design and real-data preparation](D1-design-handover.md) | Original handover preserved; supplied redesign resumes application work in D1a |
| D1a | Dark Sector UI verified: 42 snapshot combinations, 13 flow checks; all 143 IDs reconciled | [Redesign implementation](D1a-redesign-implementation.md) | Existing UI first; remaining company/news/R1 and source-contract work explicit |
| D1b | Reviewed recovery checkpoint: milestone/d1b-redesign; 963 tests, build/browser checks pass | [Connected development workspace](D1b-company-news-help.md) | D029; exact company evidence, 3/5/10-year gaps, unconfigured monitoring and searchable guide |
| D2 | Archived-source slice verified; 970 tests and 54 browser checks; live publication blocked | [Real-data pilot](D2-real-data-pilot.md) | D030; all seven identities/business coverage retained; S5/S6 gates remain |
| D3a | Application storage verified; milestone/d3a-application-runtime | [Application runtime](D3a-application-runtime.md) | Separate PG/Redis; D031 identifies the source-backed identity bootstrap dependency |
| D3b | Capture-only path verified; five genuine CRCL captures; 1,033 tests | [First-source bootstrap](D3b-source-bootstrap.md) | D031; milestone/d3b-crcl-capture; identity/publication review precedes S5/S6 |
| D3c | Pinned intent/readiness and live capture verified; 1,065 tests | [Bootstrap intent](D3c-bootstrap-intent.md) | D031 correction; milestone/d3c-pinned-capture; registration review pending; no automatic quote |
| D3d | Identity review verified; quote currency unsubstantiated | [Quote identity review](D3d-quote-identity-review.md) | Read-only replay/check; no registration or ordinary request; milestone/d3d-identity-review |
| D3e | Interactive saved pipeline state verified; registration remains blocked | [Pipeline preview](D3e-pipeline-preview.md) | Six stages, sanitized real audit fixture, evidence disclosures; milestone/d3e-pipeline-preview |
| D3f | Official-source search remains blocked; saved search disclosure implemented | [Quotation-currency search](D3f-quote-currency-search.md) | D034; primary-source findings, policy/date limits and replayed application invariants; no registration |
| D4a | Real one-shot check and saved UI verified; no new scoped filings | [SEC filing monitor](D4a-filing-monitor.md) | Saved real check, immutable baseline/body lineage; no scheduler or financial dispatch |
| D4b | Bounded real slot and saved UI verified; milestone/d4b-filing-scheduler | [Filing scheduler](D4b-filing-scheduler.md) | Fixed-scope UTC slots, lifecycle/budget/health; rebase gate and no background service |
| D4c | Pilot copy simplified; unavailable values show N/A | [Pilot UI cleanup](D4c-pilot-ui-simplification.md) | User-requested removal of repetitive notices; source details and history controls retained |
| S8a–d | Planned; F1 shares provenance, Ratios and Overview | P0 company pages and integration | After relevant engine/contracts |

For every milestone use [the template](TEMPLATE.md). Keep its record current,
link decisions and validation evidence, and use a named commit. Future Codex
tasks should be titled `S1 — EquityEval SEC concepts`, etc. Create a new task
only when it has a concrete independent scope or this milestone has a handoff.
Do not duplicate active implementation across tasks. Use `git log --oneline`
for exact commits and `docs/decisions.md` for review status.

See the [operational roadmap](../roadmap.md) for dependency order and the distinction between implemented code, research and operating application capabilities. D4a SEC incremental discovery and D4b manual scheduling readiness are complete for their bounded scopes. [D036](../design/s3/filing-scheduler-proposal.md) governs D4b; reviewed rebase and service configuration remain next.
