# Fictional presentation inputs

`valuation-presentation.json` contains deterministic, separately saved S8a
manifests accepted by the existing S7a `ValuationManifest` contract. The baseline
uses S7a's hand-oracle inputs (revenue 100, five annual periods, 17.34375 raw price,
10 common shares, −20 equity adjustment). Its UUIDs and hashes are fictional
identities, not retained application evidence. Author/rationale fields stay in
this development input and are excluded by the public payload projection.

The reference example adds two grids without changing audited test fixtures:
WACC × terminal growth reverse solves, and terminal margin × reinvestment
conditional repricing. Along the latter grid's reinvestment .05 row, the exact
per-share hand oracle is 6.421875, 17.34375, 28.265625 at margins .1/.2/.3.
The multiple-solution case uses EV = 100z^5 − 100z, z = 1 + growth, target −20.
Other examples restrict the domain, cap evaluation budget or mark the quote
unavailable. Every solver state is calculated by core, never hand-authored output.

Regenerate with `.venv/bin/python scripts/project_python.py scripts/export_valuation.py`.
Verify with the same command plus `--check`; lint includes this no-diff gate.
Neither command accesses the application database or any provider.
