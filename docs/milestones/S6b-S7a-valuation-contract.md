# S6b / S7a — Assumptions and reverse valuation review packet

Status: **ready for coordinator review; implementation not started**.
Task: continuing equityEval milestone build log; proposal requested by coordinator
`01a0bbd2-bd4d-77c2-86f6-2a34fef283f1` on 2026-09-22.
Branch: `codex/source-bootstrap`. Approved baseline: `3909572`,
`milestone/s6a-fundamentals`; documentation checkpoint recorded in Git history.
Dependencies: S6a, S5 source evidence/calculations, S4 retained selections, W1;
D004/D005/D009/D010 proposed resolutions and D038 review.
Sources: SPEC 0.1/0.2, 4.2, 11, 12.3; S2 deferred assumptions/model records;
F1/R1/W1/U1 requirements and existing real-data/source gates.

## Scope

Prepare a concrete contract and acceptance plan only. Preserve approved S6a,
applied migrations and the accepted UI. No new schema, API, math implementation,
real valuation, provider activation, quote inference, scheduler or alert delivery.

## Artifacts

- [Contract proposal](../design/s6/valuation-contract-proposal.md): exact model
  formulas/domains, single unknown, bridge/share identity, immutable records,
  Decimal solver proof/failure semantics, deterministic ranges, proposed generated
  API, source lineage, W1 freeze/cache/retry/fencing and later UI behavior.
- [Acceptance plan](../design/s7/acceptance-plan.md): independent small hand cases,
  valid non-unique model fixture, solver/numeric/source/bridge/scenario checks,
  PostgreSQL and API acceptance, synthetic tracer and later manual/UI verification.
- [Decision register](../decisions.md): D004/D005 are proposed, not accepted;
  D009/D010 retain unresolved portions; D038 records planning-only scope.

## Decisions requested and recommended conservative resolutions

1. D004: reverse DCF is P0 primary; exactly one solved assumption. Forward
   comparison later, using the same evaluator.
2. D005: complete named deterministic range, no probability/price-target claim.
   Incomplete scenario roster means N/A for the range, while retaining each result.
3. D009/D010: explicit dated WACC/risk-free inputs; unit-consistent reverse/reprice
   test under certified uniqueness. No automated rate defaults or Monte Carlo claim.
4. Model applicability and bridge: first operating-company model requires eligible
   economic claim values, complete cash/debt/lease/nonoperating/NCI/preferred scope,
   one homogeneous common pool and evidenced basic=diluted/no dilution. Broader
   class/ADS/options/proxy models stay unsupported rather than silently estimated.
5. Time and formula choices: explicit annual run-rate anchor/rebase, annual schedule,
   no-NOL cash-tax assumption, terminal ROIC reinvestment, reviewed lease basis and
   bounded positive terminal regime. These are model restrictions, not universal
   truths or automatic business-profile defaults.
6. Solver/numeric policy: Decimal point/interval math, explicit tolerances/budgets,
   global domain proof for unique/no-root claims; inconclusive where proof fails.
7. Storage/API: additive valuation records compose S6a evidence and existing W1;
   they do not change S6a's fundamentals-specific snapshot/publisher. Workspace-
   bound exact routes and immutable assumptions/results require approval together.

These choices are concrete review items beyond D004/D005, not blockers that need
more research before the coordinator can review. Real-source prerequisites remain
separate and explicit. No named watchlist company is presumed model-eligible.

## Validation evidence

| Check | Result | Date | Notes |
| --- | --- | --- | --- |
| H01–H05 hand arithmetic | Independently checked | 2026-09-22 | Decimal 80 plus exact algebra/rational identities; fictional data only, no engine created |
| Relative document links and proposal status | Pass | 2026-09-22 | All local Markdown targets in seven packet/status files resolve; decisions and routes explicitly proposed |
| Scope diff | Pass | 2026-09-22 | Seven documentation files only; no code or applied migration changes; whitespace check passes |
| Documentation checkpoint hook | Required existing-suite gate; see commit output | 2026-09-22 | `var/s6b-proposal-commit-checks.log`; no S7a tests/code exist yet. Acceptance cases above are requirements, not passing implementation claims |

## Limitations and next handoff

Send both documents and this decision list to the coordinator for audit, then
pause. Approval must identify accepted/revised model, numeric, schema/API and
synthetic-publication scope before implementation. After approval, S6b implements
reviewed contracts; S7a implements tests-first pure math and the synthetic W1/API
tracer; UI/manual follow in their verified slice. Production valuation requires
its own real quote/action/claim/dilution/normalization and source-policy gate.
