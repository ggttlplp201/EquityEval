# Valuation engine

Read the root AGENTS.md and docs/spec.txt. Use pure Python functions only:
no I/O, database, network, or hidden mutable state. All valuation math lives here.
Write meaningful tests with hand-computed answers before numeric implementation.
Do not fabricate missing values; preserve missingness and return quality evidence.
Review units, currency, period alignment, signs and near-zero denominators.
Run `make test-core` plus the full required checks before committing.
S0 reserves this package only. Do not implement formulas until its milestone.
