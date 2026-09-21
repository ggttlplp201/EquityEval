# Real-data pilot handoff — 2026-09-20

Canonical repository:
`/Users/leon/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval`.

Reviewed redesign recovery: commit `3342595`, tag `milestone/d1b-redesign`.
Current pilot branch: `codex/seven-company-pilot`.
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

The configured application database currently refuses connections on loopback5433.
Do not replace it with disposable test storage. S3 legacy archive policy links,
registered source/mapping identities and reviewed filing/non-reliance completeness
remain the specific next prerequisites. Use existing S3 transport/archive and PIT
paths when addressing them. Do not build a second ingestion pipeline, reuse test
policy rows or create selection-shaped objects to make core calculations pass.

The source/numeric checkpoint does not activate D027 attribution. Keep S5 then
S6 sequential and review any shared contract changes separately.
