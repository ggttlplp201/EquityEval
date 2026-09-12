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
| S3 | Planned | EDGAR ingestion | After S2/Source review |
| S4 | Planned | Tiingo and FRED | After S3 |
| S5 | Planned | Ratio engine | After S3/S4 |
| S6 | Planned | API contract review/freeze | After S5 |
| S7 | Planned | Forward DCF | After S6 |
| N1a–d | Requested; continuous discovery and stock assessments specified (D017/D018) | [News and macro agent](../features/N1-news-and-macro-agent.md) | Alongside S2–S8 contracts |
| W1 | Durable Add/Refresh requests implemented; full pipeline/UI follow | [Watchlist and reanalysis](../features/W1-watchlist-analysis.md) | S2 → engines → S8/N1 |
| U1 | Requested; outline captured | [Manual and glossary](../features/U1-user-manual.md) | Required before finished release |
| S8a–d | Planned | P0 company pages and integration | After relevant engine/contracts |

For every milestone use [the template](TEMPLATE.md). Keep its record current,
link decisions and validation evidence, and use a named commit. Future Codex
tasks should be titled `S1 — EquityEval SEC concepts`, etc. Create a new task
only when it has a concrete independent scope or this milestone has a handoff.
Do not duplicate active implementation across tasks. Use `git log --oneline`
for exact commits and `docs/decisions.md` for review status.
