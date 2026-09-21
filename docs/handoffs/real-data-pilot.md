# Real-data pilot handoff — 2026-09-21

Canonical repository:
`/Users/leon/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval`.

Reviewed redesign recovery: commit `3342595`, tag `milestone/d1b-redesign`.
D2 pilot branch: `codex/seven-company-pilot`.
Runtime continuation was `codex/crcl-source-snapshot`; current branch is
`codex/source-bootstrap` (D3b). Runtime checkpoint D3a,
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
and isolation checks. Application migration is now 0006. D3b contains one reviewed
source/policy/issuer/security, seven genuine captures, and two bootstrap requests;
quote identifiers, watchlist memberships and normalization batches remain empty.

The user approved D031. [D3b](../milestones/D3b-source-bootstrap.md) implements the
source-only request on `codex/source-bootstrap`; see its implementation/operator
instructions for verification and first capture. The bootstrap worker reuses S3
transport and does not publish financial results. S1 completion/request timestamps
remain unknown. After a genuine capture, review identity validity and the actual
filing/event/precision evidence before normal publication/PIT/core work.

The source/numeric checkpoint does not activate D027 attribution. Keep S5 then
S6 sequential and review any shared contract changes separately.


D3b capture is verified at `milestone/d3b-crcl-capture`: 1,033 full / 225 core /
110 golden tests, lint/types and both review axes passed. Read the
[actual capture review](../research/crcl-first-application-capture-2026-09-21.md)
before continuing. The first request's inventory parsing failure is retained;
the corrected request captured all five SEC sources, including the annual
amendment. Actual listing start is evidenced as 2025-06-05. Quote currency/validity,
explicit event/statement coverage and pinned normalization review remain before
financial publication. Do not convert bootstrap completion into an S6 result.
The D2 presentation still deliberately pins its legacy source artifact.


## Current D031 correction checkpoint

[D3c](../milestones/D3c-bootstrap-intent.md) supersedes the initial bootstrap
request/completion contract. `c2b02cf` plus `bba701a` pin the exact versioned
resource/policy/window plan, reject unlisted resources, and persist typed readiness
in result_reference with NULL successful error fields. Both review axes are clear;
1,065 full / 225 core / 110 golden tests and lint/types passed.

Application migration 0007 preserved all historical row hashes. The one new bounded
capture completed five HTTP200 resources; selected Submissions identity capture
`0e93340d-a10c-40eb-b463-047c23be58bf` is ready for registration review, with no
acquisition blockers. Repeating its key returned the identical typed result and
made no dispatch. See the milestone's audit link and recovery tag
`milestone/d3c-pinned-capture`.

Current application counts supersede the earlier D3b counts above: 12 captures,
12 attempts, 3 bootstrap requests, 1 source/policy/issuer/security, no quotes,
watchlist memberships or normalization batches. No acquisition configuration is
missing. Quote currency/validity review and an explicit registration decision
remain; do not auto-register from capture readiness. The actual source/PIT/core
and minimal S6 publication sequence remains open. No UI data artifact was changed.
