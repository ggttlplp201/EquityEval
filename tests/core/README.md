# Pure calculation tests

S5 tests use explicit synthetic financial evidence and hand-computed expectations.
`test_inputs.py` validates selected-source projection, precision and provenance.
`test_source_metrics.py` covers growth, margins and CFO-minus-PPE-capex FCF,
including incompatible inputs, numeric limits and preserved missingness.
`test_history.py` covers 3/5/10-year windows, exclusions, exact percentiles and
comparison boundaries. `test_source_metric_golden.py` uses archived normalization
fixtures and preserves their blocking coverage evidence; it is not a database
PIT or live-source eligibility test. Existing schema/PIT tests cover selection.

Run `make test-core`. The mandatory commit hook also runs all repository checks.
See [S5 review](../../docs/design/s5/review.md) for numeric review and limitations.
