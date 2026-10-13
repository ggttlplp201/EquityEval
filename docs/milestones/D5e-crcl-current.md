# D5e — CRCL current-window and affected-line review

Baseline `cad64c2`, proposal `373c358`, D043. Implementation complete; independent standards/spec reviews passed.

## Evidence and actual outcome

One governed group retained two later primary 8-Ks plus required Facts/Submissions:
four HTTP captures, all prior rows preserved. Application totals: 57 captures,
59 attempts, 13 requests, one normalization batch, two selected facts, zero metrics.
[Acquisition audit](../research/crcl-current-acquisition-2026-10-13.json) retains
request/execution/policy/manifest and before/after row hashes. Actual retrieval
window: 2026-10-13 05:01:15.043952–05:01:15.734230 UTC.

[Review artifact](../research/crcl-current-review-2026-10-13.json) and interactive
analysis UI show exact body/quote evidence and the blocked candidate decision.

| Filing | Full primary-body finding | Remaining limit |
| --- | --- | --- |
| 0001876042-26-000276, 2026-09-22 | New Binance commercial arrangements and concurrent private placement; only embedded Exhibit 104 | Prospective distribution/share economics are not FY2025 correction or future-margin proof |
| 0001876042-26-000279, 2026-09-25 | Director/CFO departures, transition and compensation terms; no-disagreement wording | Referenced Exhibit 99.1 `final_leadershiptransiti.htm` is unretained/unreviewed; parent wording is not assurance |

The exact outstanding key is
`filing_document/0001876042/0001876042-26-000279/final_leadershiptransiti.htm`.
It was not acquired beyond the committed group. No financial non-reliance
statement was identified in either reviewed primary; this is not a blanket event
history clearance.

Fresh Submissions matches the 21 scoped financial/event primary identities.
Inventory observation is 05:01:15.264075 UTC; application retrieval cutoff is
05:01:15.734230 UTC. The latter does not extend inventory/public-event knowledge.
No claim is made about the rest of that calendar day or every SEC form.

Fresh Company Facts retains the same original FY2025 annual edition and selected
values. D5d annual source corroboration is preserved. New deterministic comparisons
confirm matching selected revenue/op-income literals across retained Q2/H1 2025
periodic editions, with exact period/unit/scale/capture provenance. The retained Q1
source is a later comparative, without an earlier primary edition in this set.
Generic reclassification wording identifies no selected-line effect. These gaps
remain unconfirmed; neither a restatement nor unchanged universal scope is inferred.

**Candidate PIT batch blocked; no new batch or metric published.** Historical
D5a flags remain intact. Real S6 remains outside scope. No schema/API/concept,
missingness, provider/quote, valuation, sector, migration or scheduler change.
Target transaction schedules were not used as proof of Circle FY2025 accounting.

## Validation and handoff

Red-first tests cover changed/missing prior roster, unavailable acquisition,
annual edition identity/value, duplicated or mismatched comparison editions,
current inventory identity/extra events, false eligibility and partial-review copy.
Validation passed: full `make check` (1,754 tests; 505 core; 110 golden),
production build, 35 browser checks, deterministic archive/report/export replay,
and independent staged standards/spec reviews with no findings. Browser checks
cover 320/390/768/1440 widths, keyboard provenance, corrupt-artifact Retry, and
local GET-only requests; desktop/mobile screenshots were inspected.
See [handoff](../handoffs/d5e-crcl-current.md). Preview uses port 3103; unrelated
3101 is untouched. Push the completed branch without force and verify remote HEAD.
