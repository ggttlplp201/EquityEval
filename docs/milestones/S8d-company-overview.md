# S8d — Company Overview integration

Status: bounded missing-sentinel correction reviewed; corrected full gate pending.
Branch: `codex/s8d-company-overview`.
Baseline: `ee50c317874dbcc1464d5fdc2fb971411dd31b56`.
Original implementation: `8f04518fdb650d4533a61fa23b3f337a937d9f3d` (preserved, untagged).
Acceptance: [pinned before implementation](../design/s8d/acceptance.md).
Reviews: [two independent axes](../design/s8d/review.md).
Manual: [Company Overview](../user-manual/company-overview.md).

## Delivered scope

`/development/company` keeps existing calculations and saved history while adding
four research-workspace cards. All 168 saved views (84 fictional issuers, two
evaluation dates) have checked metadata linkage. Selected Overview is ready only
for itself; all three other workspaces are separate fictional examples. Their
links open their own defaults; no financial amounts are combined or republished.

The deterministic local exporter stores metadata, actual local file/payload
hashes and distinct declared source hashes. Missing security/known/retrieved/as-of
proof cannot establish compatibility. Existing Company date-only declarations
stay date-only. Per-amount bases remain separate. Server reads verify the exact
four-file roster and byte hashes before projecting the selected view's evidence.
Counts and dates open exact linkage/history/source evidence. GET selectors reject
unknown keys, repeats, unsupported pairs and ambiguous candidates.

Four-decimal display preserves %, × and $ through shared exact-string formatting.
Drawer precision and original saved financial fixture bytes are unchanged.
3/5/10-year history, N/A, responsive layout, keyboard/focus, loading and recovery
remain present. No core/schema/API/migration/provider/scheduler changes.

## Verification

Original implementation gate passed: 1,649 full tests, 505 core, 110 golden,
26 Node, lint/types/exports, in `var/s8d-commit-checks.log`. Corrected gate pending.
Original red-first evidence:
`var/s8d-red-python.log`, `var/s8d-red-node.log`, `var/s8d-units-red.log`.
Focused source tests: 26 (13 new metadata checks plus 13 existing Company checks).
Overview Node tests: 8 (26 across S8a/b/c/d). Production build and lint/types pass.
Seven Overview browser checks pass in `var/s8d-browser-verified.log`;
19 prior browser checks (6 S8a, 6 S8b, 7 S8c) pass in
`var/s8d-prior-browser.log`. All four screenshots in `var/s8d-browser/`
were inspected. Existing wide source/history tables retain horizontal scrolling;
new cards fit 320/390/768/1440. Test flows exercise actual keyboard/focus, supplied
counts/dates, unit markers, full precision, strict selectors, local GET-only
requests, pending controls, missing-manifest fault injection and recovery.

Earlier failing logs are retained: shifted-context assertions, absent explicit
selector names, and a reproducible retained not-found boundary. Recovery now
uses a native GET form; no assertion was replaced by programmatic navigation.
The prior duplicate .next generated declarations were removed by rebuilding
only generated cache output (old cache retained in var). No source type rule was
relaxed. Error fault injection restores the exact manifest bytes.
 Two-axis review
findings were corrected and rereviewed with no remaining findings.

## Stopping point

Stop at S8d. Real sources, financial publication, background monitoring and
additional original Overview features retain their separate reviewed gates.

## Final coordinator correction

An additional independent audit found High: literal matching N/A could establish
compatibility. `complete()` now requires affirmative nonmissing string leaves,
recursively through dictionary/list/tuple metadata. Case/whitespace handling is
limited to missing-marker detection; valid evidence and equality stay exact.
Unsupported scalar proof is unavailable. No UI/fixture/financial value changes.

Corrected focused tests: **46 Python** (33 metadata + 13 existing Company),
**26 Node** (8 Overview), deterministic no-diff export, lint/types/build pass.
Red-first sentinel log: `var/s8d-sentinel-red.log`; corrected focused evidence:
`var/s8d-corrected-python.log`, `var/s8d-corrected-lint-types.log`,
`var/s8d-corrected-build.log`. Both narrow rereviews report no remaining findings.
The original implementation's source fixtures and all 39 prior refs are unchanged;
`var/s8d-preservation-check.json` records the verification. Corrective browser/full
checks and final tag follow before completion. Stop at S8d.
