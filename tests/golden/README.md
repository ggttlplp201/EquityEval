# Archived source checks

`khc_restatement.json` pins four exact SEC Company Facts observations and their
original JSON locators. `test_khc_source.py` checks the full archived payload hash,
source rows and hand-checked amounts. The PostgreSQL KHC regression is in
`tests/integration/test_pit.py`; its manually reviewed event annotation is labelled
in `tests/khc_seed.py`.

These are S2 storage/retrieval fixtures, not a completed SEC normalizer. S3 will
add full-company golden normalization outputs for the researched cohort. Generic
constraint fixtures are explicitly fictional and cannot masquerade as market data.
