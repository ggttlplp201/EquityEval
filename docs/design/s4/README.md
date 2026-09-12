# S4 — Price and macro data review

Status: source research and a concrete contract review after S3. The user directed
progression with “continue”; new price/macro tables and changed source semantics
still require the review specified by the project instructions.

S3 checkpoint: `b71e308`, tag `milestone/s3`.
S4 branch: `codex/s4-source-contract`.

- [Decision brief and proposed source contract](source-contract.md).
- [Storage review](storage-review.md).
- [Tiingo source research](tiingo-research.md).
- [FRED and direct government source research](fred-research.md).
- [Acceptance cases](test-plan.md).
- [Milestone record](../../milestones/S4-prices-macro.md).

Both configured API-key fields are empty. No provider account, subscription,
authenticated request or production source was activated. One direct-Board H.15
research download was format-verified; its full mixed-content ZIP includes legacy
Moody's series and remains quarantined outside tracked fixtures pending raw
retention review. See the research manifest. Synthetic acceptance fixtures are
explicitly fictional and do not supply market inputs to the application.

The direct Treasury nominal-yield dataset is now the recommended initial yield
source: official CC0 catalog linkage and a complete monthly XML response were
verified. Its source policy and adapter are still proposals, not active services.
