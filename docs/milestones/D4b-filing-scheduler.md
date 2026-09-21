# D4b — Application-owned filing scheduling readiness

Status: complete for approved D036 scope; background service not configured.
Task: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de.
Branch: codex/source-bootstrap.
Checkpoint: milestone/d4b-filing-scheduler (resolve with `git show` for exact commit).
Baseline: 9f7c48f / milestone/d4a-filing-monitor; migration 0009.
Application migration: sequential 0010_filing_scheduler, applied 2026-09-21.

## Scope and implementation

Coordinator task 01a0bbd2-bd4d-77c2-86f6-2a34fef283f1 approved the
[D036 proposal](../design/s3/filing-scheduler-proposal.md), its six refinements,
and one bounded real CRCL slot followed by pause. Shared-contract review was
completed before implementation. Fixed scope with typed rebase_required was
chosen; no rebase writer or unattended service was authorized.

0010 adds immutable schedule revisions, deterministic UTC slots, atomic D4a
request materialization, W1 claim/retry fencing, conservative attempt budgets,
final dispatch-time pause/scope/budget checks, missed-run/backoff recovery and
saved health. Full scope equality includes resources, forms, policy and version.
The latest eligible completed baseline advances monotonically. Terminal errors
and incomplete results resolve their slot without replacing the last good
baseline; structural history/scope changes require review. Repeated semantic
observations deduplicate their events. Existing migrations 0008/0009 and old
D4a audit bytes remain unchanged.

The operator CLI reuses the existing monitor worker, source archive and shared
Redis limiter. The saved UI preserves the existing dark/mint design and shows
configuration separately from actual service operation. It includes slot/result
lineage, response evidence, revision history, timing, retries, budget and dated
application totals. It adds no frontend scheduling or financial calculations.
See the [acceptance matrix](../design/s3/filing-scheduler-test-plan.md) and
[operator guide and terminology](../user-manual/filing-scheduler.md).

## Real acceptance evidence

- Schedule: `7a5b20c1-ad07-4f9a-a7bf-3915824364f2`; slot 0:
  `99a45d1a-be3a-42a5-abcd-4d20e6f07abf`.
- Request: `59ca04e0-e3a1-48c3-99b4-9d8238d5dd3c`; execution:
  `9122ba10-9e2e-46f5-86d6-f45cd8ee24e6`.
- Nominal/due/acceptance cutoff: `2026-09-21T22:07:00.000000Z`.
  HTTP requested `22:07:33.107044Z`, completed `22:07:33.362718Z` that day.
- HTTP 200, content_unchanged: 66,909 retained bytes; SHA256
  `c4f43a9e2582ab88f8cfa1d8f3527bfbf515770e3c33766e21629845c16026a3`.
  Original capture `0e93340d-a10c-40eb-b463-047c23be58bf` and its timestamp retained.
- Result: no_change; six scoped filings, complete baseline/current coverage,
  eligible for subsequent discovery comparison. No downstream financial dispatch.
- Four concurrent repeat ticks plus four claims (zero winners), followed by a
  repeated run-slot, added zero requests or HTTP attempts.
- Schedule paused at revision 2. One-hour cadence, zero jitter, one W1 attempt,
  three reserved transport units and one actual dispatch record. No service installed.

The [primary audit](../research/crcl-filing-scheduler-2026-09-21.json) has SHA256
`1b1ddb429521ab8c2593c69b0b6994c61b0c978aa5cfdb96f002bfd92a3859c2`.
The [repeat proof](../research/crcl-filing-scheduler-repeat-2026-09-21.json)
records before/after counts and pause confirmation. Configuration input file SHA256:
`491c0b57fc200cfd3ffe48a2d419eb2f9b61259b4a7a877fbe5d343488934151`.

Current application totals: three source bootstraps, two filing checks (five
requests total), 12 logical captures, 14 fetch attempts and two retained monitor
response bodies. Quote identifiers, memberships and normalization batches remain
zero. Earlier checkpoint totals remain dated rather than rewritten.

## Validation

The mandatory commit gate runs the full suite, 225 core and 110 golden tests,
Ruff/import-policy/generated-concept checks, ESLint, strict mypy and TypeScript.
Acceptance includes 39 focused scheduler/migration checks, 54 combined monitor/
scheduler checks, six real Redis limiter integration tests, UTC arithmetic cases,
and nine saved-snapshot provenance/sanitization tests. The earlier full run
passed 1,225 tests before the final arithmetic/snapshot additions; the checkpoint
hook validates the final tree and records its full count in the commit output.

The optimized Next build passes. Agent-browser verified page content, no error
overlay and home navigation. The pipeline browser suite passes all ten scenarios
(11 Node test results), including real slot IDs, keyboard disclosures, safe source
links, 320/390/768/1440 widths, seven-company navigation and 10Y history control.
Network audit reports no mutations/provider/API requests or new browser errors.
Desktop and narrow scheduler screenshots were visually inspected; evidence and
logs are in ignored `var/d4b-browser/` and `var/d4b-*.log`.

Test setup uses fixed fictional cutoffs and deterministic bootstrap permits to
isolate lifecycle interleavings from wall-clock expiry and unrelated 50 ms permit
contention. The production limiter is unchanged and independently verified with
real Redis. An early draft-migration template mismatch was resolved by rebuilding
the disposable test template before migration 0010 was applied to the application.
No applied migration or real evidence was rewritten.

The [two-axis final review](../design/s3/filing-scheduler-review.md) found no
standards issues and one corrected status issue: pre-dispatch cancellation no
longer advances the last HTTP completion. Two regression scenarios failed before
the correction and pass afterward. Unknown interruption recovery also does not
claim observed HTTP completion.

Reproduce the saved projection and read-only application/history verification:

```sh
.venv/bin/python scripts/project_python.py -m scripts.export_scheduler_snapshot --check --verify-application
```

This verifies the current schedule/results and protected earlier application rows,
including original D4a seed approvals, manifests and retained bodies. Plain D4a
and D3f snapshot `--check` commands still pass; their optional old cumulative-count
comparisons intentionally describe their earlier checkpoints. Use D4b for current
application verification. Saved health is verified at its recorded as-of time;
expired budgets/scope do not silently rewrite a historical snapshot.

## Next handoff

The fixed filed window ends 2026-09-21 UTC. Further polling needs a reviewed
replacement scope/rebase and explicit service configuration; a stored active
schedule alone never proves a worker runs. Keep the acceptance schedule paused.
Review the rebase/service lifecycle separately before unattended operation.

Quote/reference rights and explicit quotation-currency evidence remain blockers
for ordinary analysis. Financial normalization/publication and a deduplicated
filing-to-analysis handoff retain S3/W1/S5/S6 gates. N1 stock-specific news,
CPI/PPI/Fed calendars and in-app/desktop/email delivery remain separate work in
the [operational roadmap](../roadmap.md).
