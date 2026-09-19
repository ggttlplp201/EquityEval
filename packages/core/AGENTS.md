# Valuation engine

Read the root AGENTS.md and docs/spec.txt. Use pure Python functions only:
no I/O, database, network, or hidden mutable state. All valuation math lives here.
Write meaningful tests with hand-computed answers before numeric implementation.
Do not fabricate missing values; preserve missingness and return quality evidence.
Review units, currency, period alignment, signs and near-zero denominators.
Run `make test-core` plus the full required checks before committing.
S5 source metrics and generic 3/5/10-year history math are implemented. Read
docs/design/s5/source-metrics.md for exact supported inputs and deferred work.
Keep projection records internal; S6 owns the public API and persistence contract.
