# Archived source checks

`khc_restatement.json` pins four exact SEC Company Facts observations and their
original JSON locators. `test_khc_source.py` checks the full archived payload hash,
source rows and hand-checked amounts. The PostgreSQL KHC regression is in
`tests/integration/test_pit.py`; its manually reviewed event annotation is labelled
in `tests/khc_seed.py`.

These are S2 storage/retrieval fixtures, not a completed SEC normalizer. S3 will
add full-company golden normalization outputs for the researched cohort. Generic
constraint fixtures are explicitly fictional and cannot masquerade as market data.

S3 review preparation adds `s3_review_cases.json` and
`test_s3_review_evidence.py`: eight existing archives, 28 audited exact observations
and seven scoped gap cases, with 44 evidence checks. Numeric lexical text, raw CIK
representation and raw-row metadata are preserved. These verify the acceptance
evidence; they do not run a Source adapter or compare normalized statements.
The full normalization acceptance plan is in `docs/design/s3/test-plan.md`.
