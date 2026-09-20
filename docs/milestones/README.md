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
| U1 | Draft data/history, price/macro and fundamentals chapters; finished manual pending UI | [Manual and glossary](../features/U1-user-manual.md) | Required before finished release |
| F1 | First source-metric/history slice implemented; remaining guided feature pending | [Guided fundamentals](../features/F1-fundamentals-guide.md) | S5 → S6 → S8b/S8d/U1; preserve 3/5/10-year history options |
| X1 | Core and fictional graphs verified; 950 tests; milestone/x1-core-graphs | [Sector Explorer](X1-sector-explorer.md) | Separate feature; graph-first, source/contract gaps explicit |
| S8a–d | Planned; F1 shares provenance, Ratios and Overview | P0 company pages and integration | After relevant engine/contracts |

For every milestone use [the template](TEMPLATE.md). Keep its record current,
link decisions and validation evidence, and use a named commit. Future Codex
tasks should be titled `S1 — EquityEval SEC concepts`, etc. Create a new task
only when it has a concrete independent scope or this milestone has a handoff.
Do not duplicate active implementation across tasks. Use `git log --oneline`
for exact commits and `docs/decisions.md` for review status.
