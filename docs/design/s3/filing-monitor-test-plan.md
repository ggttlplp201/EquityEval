# D4a filing monitor acceptance cases

Prepared before implementation. [Approved D035 contract](filing-monitor-proposal.md).
Use fictional HTTP and the separate test PostgreSQL/Redis runtimes; never write
fixtures into application evidence. The bounded real check is a separate operator
acceptance after automated checks and migration review.

| Case | Expected result / invariant |
| --- | --- |
| First run against explicit complete baseline | Persist exact baseline/cutoff/plan; no implicit “latest” choice |
| Identical source and metadata | `no_change`; existing capture reused; one honest new check attempt; no downstream request |
| Same terminal idempotency key, concurrent enqueue | Same request and saved result; no extra HTTP, capture or execution |
| Same key with changed cutoff/forms/baseline/policy | Reject parameter conflict |
| Two workers claim one queued poll | One lease; loser performs no HTTP |
| New 10-Q / 10-K before cutoff | `new_filing`; exact accession metadata and source locator retained |
| New 10-Q/A / 10-K/A | `amendment`; separate edition; never infer restatement/non-reliance |
| Original and amendment both added | `mixed_changes`; retain each accession |
| Same accession, changed form/date/report/acceptance/document | Explicit metadata conflict; incomplete; do not overwrite baseline |
| Changed row ordering | Same logical inventory; no false filing change |
| Late-arriving filing dated before the previous maximum | Detected by accession-set difference inside pinned window |
| Acceptance exactly at cutoff / one instant later | Included / excluded; timezone offsets normalized as instants, original metadata retained |
| Missing or naive acceptance in scoped form | Incomplete; no guessed timezone or date-only cutoff substitution |
| Malformed dates, parallel-array mismatch, unsafe document path | Incomplete with capture evidence; no eligible baseline advance |
| Duplicate accession, even identical metadata | Flag ambiguity explicitly rather than silently deduplicate |
| Baseline accession disappears | Incomplete; preserve old observation |
| Newly advertised unplanned history | Incomplete; no fetch outside exact resource intent |
| Root older-history reference inconsistent with history rows | Incomplete; no claim of complete source coverage |
| Other forms added, no scoped changes | `no_change` for form scope; retain changed raw capture as distinct evidence |
| Identical HTTP 200 entity body | Reuse matching verified capture with actual 200/header/check evidence; no false 304 |
| HTTP 304 with missing/corrupt/wrong validator | Refuse reuse; existing S3 recovery behavior preserved |
| 200 same hash but wrong length/resource/policy or unverified archive | Refuse unchanged-body reuse |
| Crash after dispatch, before body completion | Unknown/interrupted attempt retained; retry uses new fenced execution |
| Crash after successful capture, before comparison/result | Recover with verified existing evidence where pinned intent permits; no duplicate result |
| Crash after typed result, before terminal response | Retry returns existing terminal result or resumes finalization safely; no downstream duplicate |
| Stale lease tries completing attempt/result | Fence rejects mutation |
| Generic stage/worker tries completing monitor | Reject missing typed result or wrong trigger/resource |
| Migration over populated 0007 state | Prior rows/results/IDs preserved; new nullable fields remain NULL for old rows |
| Downgrade with monitor/unchanged-attempt history | Refuse destructive history loss |
| UI export of real check | Sanitized, reproducible and dated; counts distinguish bootstrap/monitor; no source secrets/paths |

## Existing CRCL baseline inspection

The archived D3c Submissions capture `0e93340d-a10c-40eb-b463-047c23be58bf`
was verified and parsed without new HTTP. In the 2025-01-01 through 2026-09-21
filed-date window, existing assembly reports complete advertised inventory, no
missing history and six scoped records (four 10-Q, one 10-K, one 10-K/A). All six
carry timezone-bearing acceptance metadata. These are already observed filings,
not newly discovered filings in the upcoming real poll.

Do not assume accession prefix equals the issuer CIK: one existing Circle filing
has accession `0001628280-25-039781`. Identity is bound through the checked SEC
Submissions issuer and resource, not a fabricated accession-prefix restriction.
The annual amendment remains its own record and does not itself establish an
accounting restatement or a non-reliance event.
