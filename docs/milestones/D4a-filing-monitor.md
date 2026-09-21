# D4a — Incremental SEC filing discovery

Status: bounded discovery implemented; real check and browser acceptance verified.
Recovery checkpoint: `milestone/d4a-filing-monitor`, created only after required commit gates. Date: 2026-09-21.
Branch: `codex/source-bootstrap`. Baseline: `b4c1e19` / `milestone/d3f-currency-search`.
Decision: D035, approved by delegated coordinator
`01a0bbd2-bd4d-77c2-86f6-2a34fef283f1` after concrete sequential review.

## Scope and reuse

The [operational roadmap](../roadmap.md) reconciles twelve implemented/research/
blocked capabilities and their dependency order. This milestone adds one bounded
SEC filing discovery request without quote registration or financial publication.
It reuses W1 request keys, claims, leases, retry/fencing, the existing application
stores, reviewed SEC policy/contact, Redis budget, raw archive, Submissions parser,
and inventory assembly. No new provider, credentials or scheduler.

The [approved contract](../design/s3/filing-monitor-proposal.md) and
[acceptance matrix](../design/s3/filing-monitor-test-plan.md) specify the boundaries.
Migration 0008 adds exact monitor intent, owner-reviewed initial seed lineage,
fenced typed completion and immutable per-attempt HTTP 200 payload descriptors.
The initial baseline cutoff is no later than its HTTP request start. Later
baselines name a terminal eligible prior result, including its manifest ID/hash.
Scope changes require a reviewed rebase. Acceptance review added migration 0009
with a unique completed-result index per execution; 0008 had already been applied
for the real poll, so it was preserved and the correction applied sequentially.

The pure comparison detects accession additions, amendments, late arrivals,
metadata changes and disappearance. Complete no-change requires complete baseline
and current inventories; missing/invalid metadata stays incomplete. Only advertised
history overlapping the pinned filed window is required. More than ten overlapping
documents is explicitly incomplete, never silently truncated. Every complete 200
body is retained; identical bodies reuse a verified logical capture while keeping
new attempt provenance. Conditional 304 preserves its actual response semantics.

Worker recovery replays successful observations from the same logical request,
recovers interrupted attempts as unknown, and verifies saved manifest bytes before
resuming completion. Old leases cannot finish. The operator requires an explicit
plan/key and uses no clock-derived changes during retries.

## UI and user instructions

The existing dark/mint pipeline design gains a separate SEC filing-monitor panel:
actual outcome/time, cutoff/window/forms, baseline eligibility, scoped filings with
source locators/hashes, history coverage/exclusions, retained response evidence,
current totals and downstream blockers. D3c/D3d/D3f remain pinned historical
artifacts. Earlier acquisition totals are labelled as the pre-monitor checkpoint.
The browser reads a sanitized saved snapshot; no live poll or mutation is implied.

See the [filing-monitor manual](../user-manual/filing-monitor.md) for the verified
view, definitions and one-shot operator commands. The existing 3/5/10-year
fundamentals, fictional sector charts, News and Help routes remain distinct.

## Acceptance record

The [real check audit](../research/crcl-filing-monitor-2026-09-21.json) reports
**no_change** against six existing scoped filings (four 10-Q, one 10-K, one 10-K/A).
Both advertised inventories are complete for 2025-01-01 through 2026-09-21.
The acceptance cutoff is **2026-09-21 20:32:51 UTC**. Actual HTTP request began
20:36:50.211096 UTC and completed **20:36:50.335318 UTC**; these are deliberately
distinct. Seed cutoff is the D3c request start, 17:07:35.880159 UTC.

One real HTTP 200 response retained a new 66,909-byte attempt body with SHA256
`c4f43a9e2582ab88f8cfa1d8f3527bfbf515770e3c33766e21629845c16026a3`.
Its bytes matched verified capture `0e93340d-a10c-40eb-b463-047c23be58bf`.
That logical capture kept its original 17:07:35.957888 UTC retrieval time.
No new filing or amendment was manufactured for the acceptance demonstration.

- Request: `be853bd4-9847-4fc0-beaf-d33de1e8ee86`.
- Execution: `b70b17cc-e7d1-471e-8207-c6bb9f9934ec`.
- Audit SHA256: `ee1074c19265159a08abe95bf8a6795b2c6090bacbccf8875e34b0a6ee577794`.
- App migration: `0009_monitor_result_identity`.
- Current totals: 3 acquisition requests + 1 monitor; 12 logical captures,
  13 attempts, 1 retained monitor body; 0 quotes, memberships, normalization
  batches or ordinary analysis requests.
- Every prior D3f row hash remains present, excluding only the new nullable
  request column from legacy-row hashing. Original D3c identity captures and
  manifest are replayed through the existing verifier; audit exports omit blob
  paths, contacts and credentials.
- Repeating the exact terminal plan/key returns a byte-identical sanitized audit,
  with no new HTTP attempt, capture, request or financial work.

Validation: 1,183 full tests passed before the final UI/audit refinements; 69
focused monitor/contract/snapshot checks cover those refinements, including the
sequential uniqueness correction. The required commit hook reruns the complete
suite (1,194 collected tests), 225 core tests, 110 golden tests, lint, generated vocabulary and strict
Python/TypeScript checks on the exact staged tree. It is not bypassed.

Optimized Next build passes (pipeline 8.03 kB route / 114 kB first load).
Agent-browser renders the saved result without a framework overlay. Nine
Playwright scenarios pass (ten Node results including their parent): monitor
provenance/counts, keyboard disclosures, all six existing stages, safe links,
320/390/768/1440 layouts without overflow, navigation and the 10Y option.
No browser mutations/provider fetches/page errors; the existing narrowly allowed
favicon 404 remains the only known console warning. Screenshots and network audit
are in ignored `var/d4a-browser/`; desktop and narrow layouts were visually reviewed.
React review found static typed data, native disclosures, stable keys and no new
client fetch effects, financial arithmetic or dependencies.

During acceptance, migration allowlist/nullable-column expectations were updated;
a subprocess `.pth` visibility issue was handled with the validated strict-editable
path inherited by the test process. Read-only application audit exposed redundant
idle-connection validation in the capture loader; loading now uses the immutable
DB row directly, while live transport independently verifies reuse. A read-only
transaction regression covers that correction. The final uniqueness test verifies
the database refuses duplicate typed results; its attempted duplicate is rolled
back before normal completion. The first commit attempt also found byte-identical duplicate generated Next type
files (`* 2.ts`) in the iCloud build directory. They were preserved in ignored
`var/d4a-generated-duplicates/` and removed from `.next/types`; typecheck was
rerun without changing application source or bypassing the hook. None of these
corrections rewrote real evidence.

Reproduce the saved projection and full read-only application evidence check:

```sh
.venv/bin/python scripts/project_python.py -m scripts.export_monitor_snapshot --check --verify-application
```

Plain `scripts.export_pipeline_snapshot --check` retains the earlier D3c–f
projection; its old optional current-count equality check intentionally describes
the pre-D4a checkpoint. Use the D4a verifier for current application state.

## Handoff

Next independent dependency is D4b scheduling readiness: application-owned poll
configuration, cadence/budget, health/lag/recovery and reviewed window rebasing.
No OS scheduler is installed in D4a. Automatic financial handoff still requires
reviewed deduplication plus quote, financial coverage, mapping and S5/S6 gates.
CRCL quote currency remains unsubstantiated; no speculative USD substitution.
N1 stock-specific news and CPI/PPI/Fed alerts remain separate planned work.
