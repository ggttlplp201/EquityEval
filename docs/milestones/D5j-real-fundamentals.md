# D5j — Published real CRCL fundamentals

Status: complete; final hooks and GitHub synchronization follow acceptance
Branch: `codex/d5a-crcl-normalization`; proposal commit `f1a8ee547f289608c9854bacfadd856b020ee08c`.
Dependencies: D5i, S5, W1; approved [D048 proposal](../design/d5j/proposal.md).

## Scope and result

The narrow real-fundamentals chain is complete in the application. Separate real-v2
contracts and companion 0013 storage preserve synthetic v1. The exact reviewed
FY2025 CRCL operating income −96,435,000 USD / revenue including reserve income
2,746,642,000 USD produces −0.035110145406645642206010102517910961821744515666767
(display −3.51%). Both selected original 10-K operands retain full source and
precision lineage. No adjusted-profit, financial-strength or investment label.

Source knowledge ends exactly at 2026-10-15T21:59:05.195192Z. Frozen evaluation
is 23:22:27.030481Z; publication is 23:31:17.174630Z. These later times do not
extend source coverage or retroactively repair historical D5a flags.

Snapshot `1a259fc4-7395-4111-939b-30c58919e230`; request
`7544d95b-6550-495c-a94e-c6a6d7e3dfab`; outcome `completed_with_gaps`.
Manifest `1fa24dc52392e29aad1db306500db81b76f8ab9e3e6f8282496a02daaebc24e9`;
payload `4042d892477467e07c906091cb30e70aeb264ed9c1adb3df75e351828ffa23db`.

## Evidence and preservation

[Implementation](../design/d5j/implementation.md), [migration plan](../design/d5j/live-migration.md),
r3 preparation/plan and immutable migration/publication/intent JSON artifacts in
`docs/research` pin the exact reviewed boundary. All superseded candidates remain.
The application upgrade 0010→0011→0012→0013 preserved all 53 prior table row hashes
(except the version marker), checked 50 expected new tables, privileges and v1
function definitions against a disposable reference. Backup was verified first.
Publication exact replay, readback and prior-row preservation pass; interrupted
commit-before-audit recovery is independently tested without a duplicate request.
D5i current/original/pre-filing readback and historical D5a flags remain unchanged.

## Validation

| Check | Result |
| --- | --- |
| Red-first contract, SQL ownership/omission, status consistency, recovery | Passed focused regressions |
| Independent pre-live standards/spec/numeric reviews | Passed exact r3 |
| Live migration, exact publication/replay/readback/preservation | Passed |
| Full `make check` | Passed: 1,843 tests; 512 core; 110 golden; lint/typechecks |
| Production build | Passed |
| Browser acceptance | 55 passed: 44 analysis/normalization + 11 pipeline |
| Desktop/mobile/keyboard, corrupt-artifact recovery, GET-only | Passed; screenshots inspected |
| Live restricted-runtime API | Exact snapshot/latest 200; other workspace/v1 alias 404 |
| Independent final standards/spec reviews | Passed; no findings |

## Limitations and next stage

Nine roster entries remain null/unsupported with exact missing operands and
business/accounting applicability requirements. Accounting identity, quarterly
trend and comparison history are unavailable. One result does not establish
broader financial safety or later coverage. There are 76 captures, 78 attempts,
19 requests (16 bootstrap, two monitor, one real fundamentals), two normalization
batches/four selected facts and one real snapshot. Zero exchange quote/membership,
valuation or sector publication; no scheduler activation.

Next: [handoff](../handoffs/d5j-real-fundamentals.md) and [operational roadmap](../roadmap.md).

Validation notes: the final stable run restored every intentionally corrupted
display artifact byte-for-byte. Three ignored iCloud-generated ` 2.ts` duplicates
were verified hash-identical before removal; no source change was required.
The earlier D5b copy assertion was updated to identify its historical checkpoint.
Mandatory hooks run again on the final staged content; no hook bypass is allowed.
