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
