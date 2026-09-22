# S6a — Immutable fundamentals publication

Status: complete for the approved synthetic S6a boundary at
`milestone/s6a-fundamentals`; the commit hook enforces the final full gates.
Task: equityEval milestone build log, continued on 2026-09-22.
Branch: `codex/source-bootstrap`; baseline `bd40e6a` / `milestone/s5c-engine-handoff`.
Approval: D037, narrow synthetic-only S6a. S6b/S7 and real publication remain separate.

## Scope and artifacts

- Migration **0011 only**: immutable owner-reviewed input manifests and typed
  source links; W1 request intent; request-owned frozen inputs; content-addressed
  payloads; immutable snapshots; guarded exact latest pointers.
- Existing S5 calculations assemble source metrics, evidence, coverage, accounting,
  trends and explicit 3/5/10-year history. Decimal strings and all seven statuses
  survive serialization. Source selections and metadata are reproduced from DB.
- Owner review pins the engine artifact and expected output digest. The worker
  freezes the approved inputs, calculates outside a transaction, then atomically
  publishes under W1 lease/epoch/token/stage and membership controls. A forged
  worker output cannot pass the approved digest. Fixture review is not publication.
- The narrow `enqueue_fundamentals` W1 wrapper binds the complete selection at
  creation, so queued/failed/cancelled refreshes are visible before calculation.
  Explicit reruns receive new snapshot IDs; exact retries return the same one.
- Workspace-bound read-only API, generated OpenAPI and TypeScript, no-diff gate.
  No UI wiring or new runtime listener. Existing UI remains accepted.

## Reviews and corrections

Independent spec/numeric and standards audits compared the working tree with
`bd40e6a`. Corrections include fiscal Q4 versus Q3 annual classification, rejection
of segment/instrument amounts as consolidated issuer amounts, auxiliary period
alignment, queued-request ordering, explicit autocommit ownership, public capture
and coefficient lineage, uniform 422 errors and exact NULL-safe replay checks. Exact committed replay
uses stored canonical bytes even after an engine update; UTC envelope timestamps
are stable across reader timezones. Changed policy contents isolate payload and
latest-selection keys while leaving old snapshots unchanged.
Regression tests cover these cases. No prior migrations or audits were edited.

## Validation evidence

| Check | Result (2026-09-22) |
| --- | --- |
| Full integration/unit run | 1,458 passed before the final three recovery/cache regressions; no failures |
| Core engine suite | 409 passed |
| Golden retained-source suite | 110 passed |
| Final API/publication regression run | 26 passed, including the three added cases |
| Lint, Python/TypeScript types, generated no-diff | Passed after final code changes |
| Accepted web UI production build | Passed; no UI changes |
| Independent standards and spec/numeric audits | Findings repaired and regression-tested |
| Commit hook | Repeats full/core/golden/lint/type checks on the exact staged tree; final counts recorded in the milestone tag |

Two upstream FastAPI/Starlette test-client deprecation warnings are present;
they do not affect results. Build/test logs are retained locally under `var/s6-*`.

Focused tests cover canonical SQL/Python agreement, numeric/status roundtrips,
3/5/10-year history, workspace isolation, exact selector 404/422 behavior, immutable
history, owner/runtime privileges, source tampering, request mismatches, crash
rollback/replay, concurrent publishers, lease expiry, retry epoch, cancellation,
remove/re-add, failed/queued refresh ordering, migration roundtrip and downgrade
refusal when history exists. All data is explicitly fictional and disposable.

## Handoff

No production source, scheduler, normalization or published company result was
activated. The real CRCL quote/currency and reviewed financial normalization,
profile/calendar/precision/retention gates remain. Next work is a separately
reviewed real-data tracer or S6b assumptions/model contract, as prioritized by the
user. D004/D005 still gate valuation semantics. No DCF or buy/sell signal exists
in this result contract.
