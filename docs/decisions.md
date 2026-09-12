# Decision register

Original documents are preserved in originals/; this register makes ambiguities
visible without rewriting the source plan. Status **open** means not approved.

| ID | Status | Decision or question | Resolve before |
| --- | --- | --- | --- |
| D001 | Adopted for S0 | Isolated Git repository at the user-authorized iCloud path; no changes to the parent Development repository. | S0 |
| D002 | Adopted for S0 | Python 3.12, Node 22, npm workspaces, pip-tools exact dependency lock, Alembic migration tooling. | S0 |
| D003 | Adopted for S0 | Follow BUILD_GUIDE Part 10: infrastructure only; no financial schema, concepts, API routes, math, ingestion or UI. | S0 |
| D004 | Open | SPEC 0.2 requires reverse DCF default while 11 places it in P1. Define the explicit P0 behavior. | S6 |
| D005 | Open | SPEC 0.1 requires a distribution while Monte Carlo/scenarios are P1. Define the meaning and display of the P0 range; never label a sensitivity range a probability interval. | S6 |
| D006 | Open | S2 says all SPEC 3.1 tables while implementation is P0 only. Propose persistence scope, identifiers, provenance and PIT semantics for review. | S2 |
| D007 | Accepted starting vocabulary — 2026-09-12 | The user directed progression to S2 after the S1 review brief: use its 40 concept names and conservative source rules as the starting design. Production mapping implementations still require evidence/tests. See research/s1/review-brief.md. | S1/S2 |
| D008 | Open | Define Source, RawRecord, Fact, rate-limit and provenance contracts before adapters; S6 API freeze is too late for this dependency. | S3 |
| D009 | Open | Define macro vintage semantics for historical runs and the ERP/beta source or explicit assumption path required by DCF. | S4/S7 |
| D010 | Open | Review numeric test statements: the reverse solve/reprice round trip must have consistent units; a Monte Carlo median need not equal a nonlinear deterministic model at arbitrary base inputs. Specify valid test conditions. | S7/P1 |
| D011 | Accepted direction — 2026-09-12 | Company Facts omits custom-taxonomy and non-whole-entity facts. Use the S1 supported subset with explicit gaps and a separately tested raw-filing extraction slice; overrides alone cannot supply omitted data. See S1 source-boundaries.md. | S1/S2 |
| D012 | Open | Define date-cutoff timezone, inclusivity and treatment of non-reliance events/post-acceptance corrections. A filed-date filter is not exact intraday public availability. | S2 |
| D013 | User authorized — 2026-09-11 | Add US macro/watchlist news monitoring with in-app, desktop and email alerts. See docs/features/N1-news-and-macro-agent.md; introduce N1a–d alongside shared-contract milestones. No live delivery has been activated. | S2/N1 |
| D014 | User authorized — 2026-09-12 | Add stock search/watchlist membership and automatic full applicable reanalysis, explicit reruns and immutable history. See features/W1-watchlist-analysis.md. | S2/W1/S8 |
| D015 | User authorized — 2026-09-12 | Deliver a user manual, terminology explanations and contextual help verified against the finished build. See features/U1-user-manual.md. | U1 / release |
| D016 | Proposed — schema review pending | S2-01–05 specify staged persistence, issuer/security identity, observations/resolutions, filed-date plus retrieval-vintage policy and durable watchlist execution. See design/s2/schema-proposal.md. | S2 |
| D017 | User authorized — 2026-09-12 | Extend N1 with per-stock competitor/product/regulatory/ecosystem topics, supporting metrics and conditional impact assessments. User resolved Open USD as Open Standard's stablecoin via the Reap article. See features/N1-stock-topic-monitoring.md and N1-crcl-topic-example.md. Later schema/API review remains pending; no live monitoring activated. | S2/N1/W1/U1 |

Schema shape, financial vocabulary, API contract and changes to missing-data
representation require a concrete proposal and user review per the supplied
AGENTS.md. No such decisions are made by this scaffold.
