# Remaining S5 execution plan — 2026-09-22

Baseline: `7191276`, `milestone/s5b-roa`. Continue through the unblocked pure
engine, then stop at a concrete S6 contract proposal. No schema/API migrations,
new vocabulary, provider activation, application publication or UI redesign.

1. **Fiscal periods.** Extend existing period assembly with caller-reviewed fiscal
   boundaries bound to exact input hashes, issuer and filed/capture cutoffs.
   Support month-based and 52/53-week years; retain explicit transition-calendar
   exclusions. Require review across filing editions. Compare equal fiscal
   exposures; do not annualize a short year or silently normalize 53 to 52 weeks.
2. **Evaluation and interpretation.** Recompute existing formulas before evaluating
   them. Caller supplies versioned applicability and freshness policies with
   evidence; no default company profile, filing cadence or age limit is invented.
   Retain raw Calculation and its operands; statuses and observations are internal
   projections, not a new storage missingness model. Separate coverage from
   interpretability. Stable top-three review items must not duplicate earnings
   signals or interpret stale/unsupported inputs.
3. **Available validation.** Check the consolidated balance-sheet identity with
   existing total assets/liabilities/equity including NCI and source uncertainty.
   Cash reconciliation and segments lack complete concepts/coverage and remain
   blocked. New ratios requiring reviewed definitions remain blocked.
4. **Acceptance and S6 gate.** Reconcile F1 examples individually, record true
   blockers, preserve 3/5/10-year history, and propose immutable results, exact
   cache identity, W1 reruns/retries and fenced publication with acceptance tests.
   R1 attribution, new price/EPS/EV/debt/return conventions and product defaults
   require their separate definition/evidence gates; do not invent them to claim
   whole-product completion.

Each implementation slice receives tests before numeric changes, independent
numeric/spec and standards review, the full mandatory hook and a named checkpoint.
No synthetic evidence is promoted into a real issuer's application records.
