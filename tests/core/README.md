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


The X1 prerequisite adds `test_periods.py` (annual/YTD/TTM evidence), with
integration cases in `test_source_metrics.py`. `test_company.py` verifies shared
company multiples and source-preserving adapters. `test_sectors.py` covers
aggregate/median/mean cohorts, N/K/V, coverage, breadth, precision, concentration
and histogram membership. `test_sector_history.py` checks effective/known-date
membership, conflicts, immutable input identities, explicit gaps and the separate
three-year/twelve-quarter historical-sector policy. These tests use fictional
inputs; they do not establish a licensed universe or production API/storage.
