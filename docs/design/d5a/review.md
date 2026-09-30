# D5a implementation review

Fixed baseline: `24bd2ae` (proposal); implementation diff includes the new files.
Spec: `docs/design/d5a/proposal.md`; standards: root/frontend AGENTS and existing
S3/PIT contracts. The local pinned spec replaces an absent issue-tracker setup.

## Standards

Initial finding: PIT aggregate flags were confused with underlying quality rules.
Resolved before application writes by selecting and validating the exact quality
rows and retaining both representations. Final implementation review: no remaining
documented-standard violations or actionable heuristic smells. Minor checkpoint
stamp suggestion implemented: pipeline now lists D5a and its publication date.

## Spec

Initial findings: public PIT reader requires an idle connection; original-history
checks needed values/status/accession/observation lineage and earliest-available
semantics, while the earlier cutoff needed an explicit unavailable-coverage flag.
All resolved before application writes. A disposable integration test exercises
the complete publication/readback/verify orchestration. Correction rereview passed.
Final whole-feature review found no remaining actionable spec findings. The saved
audit/export/UI preserve exact signed values, missingness, history flags and
source precision; no schema/API/provider or S5/S6 scope expansion was found.

## Numerical and runtime evidence

The focused 33-test suite includes exact source transforms, signed values, zero
versus missing, ambiguous/wrong inventory/context/units/precision, late evidence,
idempotency/concurrency and injected late rollback. No app rows changed until the
pre-publication reviews and disposable orchestration test passed. Real read-back
and replay succeeded; exact current-application verification matches the saved
audit. UI formatting reuses the Decimal-string formatter; no browser valuation math.

Final gates passed: 1,702 full / 505 core / 110 golden Python tests; 27 Node tests;
44 browser checks across all relevant workspaces; lint, types, deterministic
exports and production build. The mandatory commit hook repeats the full gates.


## Coordinator correction — reviewed against 8ad2fbf

A subsequent independent review found three defects in the first checkpoint:
(1) every source was shown as if mapped/PIT-selected; (2) before-filing drawers
leaked later original-filing precision/literals; (3) mapping replay/standalone
verification omitted the approver and reviewed scope from identity validation.

The correction gives observed facts three role-specific source-chain entries:
selected Company Facts observation, original 10-K precision cross-check and
Submissions metadata. The amendment and Q2 filing remain separate non-PIT review
context. Unavailable before-filing drawers contain no source/precision/context
material from the later filing; the separate publication detail retains it only
as non-PIT review context. The shared drawer's optional context section is an
internal presentation addition, with no schema or API changes.

Mapping registration/replay and standalone verification now use one exact validator
for all six reviewed identity/approval fields. Tests seed altered approval/scope
only in the disposable runtime and prove both paths fail without row changes.

The original publication audit remains byte-identical. A separate deterministic
provenance audit binds the corrected snapshot hash to source-chain and review-context
capture IDs. A minor follow-up naming issue was resolved by using
`source_chain_capture_ids`, since Submissions is metadata rather than a numeric
value source. Final independent spec and standards rereviews report no remaining
findings. Red regressions demonstrated all defects before their fixes; 40 focused
Python tests pass. Full browser and mandatory commit-gate results are in the milestone.

Corrective browser run: 44/44 passing, including negative future-evidence assertions
for both concepts at all four widths and explicit source-chain/context membership.
Production build and read-only application check pass. The final hook records all
1,709 Python / 28 Node checks plus core/golden/lint/types before the authorized tag move.
