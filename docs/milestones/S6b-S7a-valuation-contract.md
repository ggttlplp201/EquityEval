# S6b / S7a — Assumptions and reverse valuation review packet

Status: **original synthetic checkpoint retained; coordinator audit requires the [corrective checkpoint](S7a-corrections.md) before milestone approval**.
Task: continuing equityEval milestone build log; proposal requested by coordinator
`01a0bbd2-bd4d-77c2-86f6-2a34fef283f1` on 2026-09-22.
Branch: `codex/source-bootstrap`. Approved baseline: `3909572`,
`milestone/s6a-fundamentals`; documentation checkpoint recorded in Git history.
Dependencies: S6a, S5 source evidence/calculations, S4 retained selections, W1;
D004/D005/D009/D010 bounded resolutions and D038 approval of `5b85140`.
Sources: SPEC 0.1/0.2, 4.2, 11, 12.3; S2 deferred assumptions/model records;
F1/R1/W1/U1 requirements and existing real-data/source gates.

## Scope

The coordinator approved `5b85140` through synthetic S6b/S7a implementation:
immutable assumptions, Decimal reverse FCFF, full economic-claim bridge, sequential
0012, W1 worker/publication and trusted-local generated API. Preserve approved
S6a, applied migrations and the accepted UI. Real financial publication, provider
activation, automated WACC, Monte Carlo and valuation UI remain separate work.

## Artifacts

- [Contract proposal](../design/s6/valuation-contract-proposal.md): exact model
  formulas/domains, single unknown, bridge/share identity, immutable records,
  Decimal solver proof/failure semantics, deterministic ranges, proposed generated
  API, source lineage, W1 freeze/cache/retry/fencing and later UI behavior.
- [Acceptance plan](../design/s7/acceptance-plan.md): independent small hand cases,
  valid non-unique model fixture, solver/numeric/source/bridge/scenario checks,
  PostgreSQL and API acceptance, synthetic tracer and later manual/UI verification.
- [Implementation](../design/s7/implementation.md), [independent review](../design/s7/review.md)
  and [manual](../user-manual/saved-valuations.md).
- [Decision register](../decisions.md): D004/D005/D038 approved for synthetic scope;
  D009/D010 accept the explicit-input and valid deterministic round-trip portions.

## Reviewed decisions adopted for this checkpoint

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

These model, numeric and storage choices were approved together with D004/D005. Real-source prerequisites remain
separate and explicit. No named watchlist company is presumed model-eligible.

## Proposal validation evidence — historical `5b85140`

| Check | Result | Date | Notes |
| --- | --- | --- | --- |
| H01–H05 hand arithmetic | Independently checked | 2026-09-22 | Decimal 80 plus exact algebra/rational identities; fictional data only, no engine created |
| Relative document links and proposal status | Pass | 2026-09-22 | All local Markdown targets in seven packet/status files resolve; decisions and routes explicitly proposed |
| Scope diff | Pass | 2026-09-22 | Seven documentation files only; no code or applied migration changes; whitespace check passes |
| Documentation checkpoint hook | Required existing-suite gate; see commit output | 2026-09-22 | `var/s6b-proposal-commit-checks.log`; no S7a tests/code exist yet. Acceptance cases above are requirements, not passing implementation claims |

## Implementation and audit progress — 2026-09-22

Implemented pure evaluator/interval solver, explicit scenario/grid diagnostics,
complete bridge and PIT checks, immutable assumption/model/input/run records,
canonical SQL mutation validation, W1 freeze/retry/cancel/publication, safe polling
and exact saved reads. Generated OpenAPI/TypeScript and lint drift checks included.

Independent numerical and standards reviews are complete. Findings and regression
repairs are recorded in the review document. H01–H05 and adversarial numeric
cases were written before math; audit regressions also failed before repairs.
Expanded core evidence: 70 tests passed before the final reverse-cell diagnostic
regression. Focused final audit evidence: 53 tests passed. Checkpoint counts and the final hook evidence below supersede these intermediate runs.

## Limitations and next handoff

UI is unchanged. Solver endpoint/tangency/continuum cases can be inconclusive,
with intervals retained and no scalar claim. New models, production valuation and
real source eligibility need their own reviewed inputs and policy work. The
manual describes the available trusted-local fixture workflow, not a deployed
valuation screen. No provider, automatic WACC, Monte Carlo, alert or scheduler
service is activated. The next handoff is the audited synthetic checkpoint with
full test/build results and immutable Git tag.

## Checkpoint verification

Checkpoint tag: **`milestone/s7a-synthetic-valuation`**, created only after the
required commit hook succeeds. The tag annotation records final actual results;
`git show milestone/s7a-synthetic-valuation` traces the exact implementation commit.

| Check | Evidence |
| --- | --- |
| Lint / Python and TS types / generated no-diff | Passed; 89 typed Python source files; both API generators match. |
| Core numerical/source suite | 480 passed. |
| Golden normalization suite | 110 passed. |
| Production web build | Passed; existing accepted routes unchanged. |
| Full suite | 1,569 collected. The required commit hook reruns all tests and is the final completion gate; see `var/s7-commit-checks.log` and the checkpoint tag. |
| Migration / transactions | Full pre-check passed migration upgrade/downgrade, runtime privileges, concurrency/rollback, immutability and retained-history guards. Only 0012 is new. |
| Docs / diff | 14 changed/new Markdown documents have valid local links; whitespace check passes. |
| Independent audits | Both numerical and standards reviews cleared functional findings after regressions; see review record. |

The initial full pre-check had 1,568 passes and one existing subprocess import
failure: iCloud hid the editable package pointer from a child interpreter.
The isolated concept-generation rerun passed (2 tests) with the validated strict
editable build path supplied through `PYTHONPATH`. The final hook uses that same
validated environment; no source or test bypass was introduced. Both existing
FastAPI/AnyIO deprecation warnings remain unchanged.
