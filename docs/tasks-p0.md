# P0 task breakdown

Status and evidence live in [milestones](milestones/README.md). Read the original
SPEC Section 11 and BUILD_GUIDE Part 5 for scope. Dependencies are sequential
through shared contracts; independent leaves can run in parallel afterward.

| Milestone | Dependency | Deliverable and acceptance criteria |
| --- | --- | --- |
| S0 — Scaffold | None | Isolated repo; source docs + root/nested instructions; dependency locks; Postgres/Timescale + Redis Compose; Alembic environment; harness; CI; hook; make checks execute and label zero tests honestly. |
| S1 — EDGAR reconnaissance | S0 | Document ~40 proposed concepts across 6–8 diverse companies with exact tags, units, periods, filing evidence, missing mappings and explicit custom-tag limits. Present concrete concept map for human review; no financial implementation. |
| S2 — Schema and point-in-time layer | Reviewed S1 | Present schema/vocabulary/missingness proposal; obtain review; implement migrations. Write real-restatement regression first: pre-restatement query returns original values, later query returns revised values. Preserve filing/retrieval/transform provenance. |
| S3 — EDGAR ingestion | S2 + reviewed Source contract | Archive before parsing; real contact User-Agent; shared rate limits; idempotent storage; approved normalization; missing-data flags. Golden fixtures across S1 cohort and 3–5 checks against filings. Licence record complete. Review plausible-but-wrong output cases. |
| S4 — Prices and macro sources | S3; accepted [D019 contract](design/s4/source-contract.md) | Tiingo/FRED adapters; archived responses; dated prices/macros; truthful staleness; flag missing observations. Verify terms, configuration and vintage semantics. |
| [S5 — Ratios and guided fundamentals](milestones/S5-ratios.md) | S3/S4a; reviewed F1 inputs/policies; S4b/coverage for dependent metrics | Pure functions and hand-computed tests first; F1 metric registry, period assembly, neutral observations, coverage and selectable 3/5/10-year own-history comparisons. Review concept/precision/debt/EPS gaps and versioned policies before math. Test missingness, signs, units, scope, currency, period alignment and near-zero denominators. Accounting mismatches raise evidence-bearing flags. |
| S6 — API contract | S5 + resolved D004/D005 and relevant D021 items | Reviewed Pydantic models including forthcoming DCF inputs/results and F1 fundamentals projection; immutable snapshot/W1 publication and complete cache identity, including history window/evaluation date/policies. Generated OpenAPI and TS; no-diff CI. Consistent provenance, errors, flags, missingness and PIT controls. |
| S7 — Forward DCF | S6 | Hand-computed three-period fixture first; FCFF/WACC/terminal/sensitivity implementation; dated or justified discount inputs; enforced constraints; independent numeric review. |
| S8a — Financials + provenance | S6 | API-backed statements, quarterly/annual/TTM and explicit historical modes; every number opens its source and transform evidence. |
| S8b — Ratios/Fundamentals | S5/S6; S8a provenance | Five-section guided fundamentals, definitions and evidence, period and 3/5/10-year comparison controls; neutral review prompts, N/A/N/M/stale states and accessible charts. API ratios and own-history percentiles; gaps remain visible. |
| S8c — Forward DCF | S7 | Assumption controls, sensitivity grid, terminal share and approved P0 range semantics; no client valuation math. |
| S8d — Overview/integration | S8a–c | Company navigation, overview, price staleness and cross-tab evidence; Overview/Ratios share one F1 snapshot and coverage. W1 add/rerun includes applicable fundamentals; verify full flow and U1 beginner walkthrough. |

P1/P2 features remain deferred. S2 may reserve approved future persistence only
if the schema review explicitly chooses it; this does not authorize later UI or
valuation features. Review gates: S1 concept map, S2 schema, S3 Source contract,
S6 API. Each milestone ends with evidence, a commit and a handoff note.

## User-requested extension — N1

The user added US macro/watchlist news monitoring on 2026-09-11, with in-app,
desktop and email delivery. Track requirements, dependencies and acceptance in
[N1 news and macro agent](features/N1-news-and-macro-agent.md). Bring its contract
requirements into S2; N1b–d follow the shared source and API contracts. This is
an explicit scope extension, not activation of all P1/P2 work.

## Additional user requirements — W1 and U1

On 2026-09-12 the user requested [watchlist additions with full reanalysis](features/W1-watchlist-analysis.md)
and a [user manual with terminology explanations](features/U1-user-manual.md).
W1 storage and execution semantics enter S2 now; its real pipeline follows the
source/engine contracts and its UI follows S6/S8. U1 is drafted alongside the
build and verified against the finished app before release is complete. Track
all accepted additions in the [feature list](features/README.md).

## Fundamentals planning addition — F1

On 2026-09-19 the user supplied a [fundamentals guide specification](features/F1-fundamentals-guide.md)
and requested incorporation after finishing current work. S4a was complete at
`5eeec7e` before planning began. F1 is now assigned to the existing milestones;
the planning checkpoint is `c1f2697`. The user also explicitly retained 5–10-year
history, so 3/5/10-year comparisons remain required options.

The subsequent “implement the next step” instruction authorized the first S5
[source-metric/history calculation slice](design/s5/source-metrics.md), now
implemented with its [review record](design/s5/review.md). D022 records that scope;
full S5 and public integration remain in progress.

Review unresolved F1-01–10 items under D021 before their implementing slices. S4b covers required
corporate-action/ADS semantics; a reviewed calendar/coverage slice is also needed
for usable historical prices and freshness. These gaps do not require a new live
provider or prevent supported source-only S5 metrics. [S5's handoff](milestones/S5-ratios.md)
records the ordered work and acceptance. N1/W1/U1 and other P0 work remain in scope.
