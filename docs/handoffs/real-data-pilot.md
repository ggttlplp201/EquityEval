# Real-data pilot handoff — 2026-09-20

Canonical repository:
`/Users/leon/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval`.

Reviewed redesign recovery: commit `3342595`, tag `milestone/d1b-redesign`.
D2 pilot branch: `codex/seven-company-pilot`.
Current continuation: `codex/crcl-source-snapshot`; runtime checkpoint D3a,
recovery tag `milestone/d3a-application-runtime` (987 full / 225 core / 110 golden).
Pilot recovery tag: `milestone/d2-observed-pilot`.
Validation: 970 full, 225 core, 110 golden tests; lint/types/build; 54 browser checks.
The live publication/core prerequisite remains open.
Read [D2](../milestones/D2-real-data-pilot.md) and
[the dated seven-company review](../research/seven-company-pilot-2026-09-20.md).

Open the app at `/development/pilot?company=CRCL`. The pilot uses real archived
SEC observations; Company/Sector demo routes retain their fictional labels.
Select any of the seven companies to inspect dated identity/business evidence
and explicit data prerequisites. The selector does not add a watchlist item or
start an analysis request.

Reproduce the display artifact without network or database access:

```sh
.venv/bin/python scripts/project_python.py -m scripts.export_real_pilot
.venv/bin/python scripts/project_python.py -m scripts.export_real_pilot --check
```

CRCL's actual observed period is FY2025, not the separate Q2 2026 research filing.
Its two observed values match original filing and Company Facts evidence. Open
a value's drawer for exact accession, source hashes, capture timestamps, context,
unit, scale/sign, original decimals, transformations, repetitions and flags.

All calculated metrics are unavailable until real publication/PIT and
history/applicability prerequisites pass. Unknown is not zero. A reported loss is
retained as a negative observation; it is not silently excluded. There are no
eligible quarter-end snapshots, so 3/5/10-year history windows do not plot a line,
compute a percentile or invent annual-to-quarter observations.

The application database now runs separately on loopback5433 at existing migration
head; persistent application Redis runs on6380. [D3a](../milestones/D3a-application-runtime.md)
and the [runtime guide](../design/application-runtime.md) record control commands
and isolation checks. All six inspected domain/evidence tables remain empty.

The next specific prerequisite is the [D031 first-capture contract review](../design/s3/identity-bootstrap-proposal.md):
W1 requires an evidenced quote, whose first capture itself requires W1. S1 has
no authentic completion/request timestamps and cannot substitute for that capture.
Do not use disposable test storage, policies, synthetic timestamps or
selection-shaped objects to bypass this dependency. After review, reuse S3's
existing transport/archive/publication and PIT paths.

The source/numeric checkpoint does not activate D027 attribution. Keep S5 then
S6 sequential and review any shared contract changes separately.
