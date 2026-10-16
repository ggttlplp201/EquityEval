# D5k handoff — pause after broader reported fundamentals

Canonical repository is the iCloud equityEval checkout; ambient Documents checkout
is unrelated. Branch `codex/d5a-crcl-normalization`, origin
`https://github.com/ggttlplp201/EquityEval.git`. Preview uses port 3103; do not touch
unrelated port 3101. User asked to pause after this milestone. No next milestone
or acquisition should start until the user resumes.

D049 proposal and expanded evidence/candidate hashes are in
`docs/design/d5k/implementation.md`. Retain every prior audit and timestamp.
The same D5i source observation supports the new ten-concept S3 batch; two real-v2
results keep annual and instant periods separate. No contract or engine change
was needed. Existing SQL ownership checks, W1 fences, idempotency and durable
commit-before-audit recovery remain active. D5j remains immutable.

After final synchronization, read-only verification commands are:

- `python -m scripts.verify_crcl_broader_completion --check`
- `python -m scripts.publish_crcl_broader_fundamentals verify annual`
- `python -m scripts.publish_crcl_broader_fundamentals verify instant`
- `python -m scripts.export_crcl_broader --check`

Use the configured editable PYTHONPATH/venv as recorded by Makefile. The older
D5i application verifier expected exactly two batches and is superseded for total
counts; D5k's audit verifies old D5i/D5a selections and row preservation directly.
The source-stage-only verifier also predates the subsequent W1 publications;
use the completion verifier for the exact S3→annual→instant audit chain.
Do not modify prior immutable audits to make old total-count assertions pass.

Next work, only after resume: a separately reviewed earlier-history acquisition
boundary, including the four PDF resources that existing BootstrapPlan cannot
represent, followed by affected-line/edition reconciliation before growth/ROA or
longer-history publication. Gross-profit/cost-of-revenue definitions need their
own source/applicability review. Broader product phases remain quote/reference
entitlement and S4b actions, real valuation assumptions/ranges, company/watchlist
and sector coverage, reviewed automatic refresh/service operation, then release
and manual acceptance. A working source-only CRCL subset does not complete those
phases. No buy/sell conclusion, provider activation or scheduler is implied.

Final acceptance: full `make check` passed (1,857 tests, 512 core, 110 golden;
two existing dependency deprecation warnings), production build passed and all
62 analysis/normalization/pipeline browser checks passed. Desktop/mobile screenshots
were inspected. Final independent standards/spec reviews passed; scoped CSS wraps
expanded unsupported labels and exact SEC tag headings. Mandatory hooks run again
at the implementation commit. Stop after non-force synchronization and verification.
