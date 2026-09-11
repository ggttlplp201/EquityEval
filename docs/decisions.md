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
| D007 | Open | Propose ~40 concept_std members, tag priorities, shares definitions, currency/unit/period handling and company overrides from actual filing evidence. | S1/S2 |
| D008 | Open | Define Source, RawRecord, Fact, rate-limit and provenance contracts before adapters; S6 API freeze is too late for this dependency. | S3 |
| D009 | Open | Define macro vintage semantics for historical runs and the ERP/beta source or explicit assumption path required by DCF. | S4/S7 |
| D010 | Open | Review numeric test statements: the reverse solve/reprice round trip must have consistent units; a Monte Carlo median need not equal a nonlinear deterministic model at arbitrary base inputs. Specify valid test conditions. | S7/P1 |
| D011 | Open — source limitation verified | Company Facts omits custom-taxonomy and non-whole-entity facts. Define the supported P0 subset and a separately reviewed raw-filing extraction path; overrides alone cannot supply omitted data. See S1 source-boundaries.md. | S1/S2 |
| D012 | Open | Define date-cutoff timezone, inclusivity and treatment of non-reliance events/post-acceptance corrections. A filed-date filter is not exact intraday public availability. | S2 |

Schema shape, financial vocabulary, API contract and changes to missing-data
representation require a concrete proposal and user review per the supplied
AGENTS.md. No such decisions are made by this scaffold.
