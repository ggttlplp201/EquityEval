# S5 — Ratios and guided fundamentals

Status: planned; F1 incorporated 2026-09-19; no numeric implementation started.
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Planning branch: `codex/fundamentals-plan`
Baseline: S4a `5eeec7e`, tag `milestone/s4a`
Dependencies: S3/S4a evidence; reviewed inputs and policies; S4b and calendar/
coverage work for applicable price/share-adjustment features.
Sources: SPEC 4.1/11/12, BUILD_GUIDE S5, [F1 source and integration](../features/F1-fundamentals-guide.md).

## Scope

Build the existing pure ratio engine with F1's guided fundamentals projections.
Keep all arithmetic in `packages/core`, preserve exact input lineage and NULL
missingness, and expose supported amounts even when another metric is unavailable.
The proposed initial guide covers growth, margins, CFO/PPE-capex FCF, balance
sheet checks, eligible valuation multiples and scoped returns on capital.

Own-history comparisons include selectable **3-, 5- and 10-year windows**.
The user explicitly retained the longer windows on 2026-09-19. Default, exact
sample boundaries and per-window sufficiency are reviewed product policy;
insufficient data never silently changes the selected window.

Existing broader S5 ratio families remain in the backlog with an explicit
coverage/dependency disposition. F1 does not delete them, implement P1 peers,
activate live providers, create automatic stock scores or resolve D004/D005.

## Ordered work

1. **S5a — Review inputs and policies.** Present a concrete packet for
   [F1-01–10](../features/F1-fundamentals-guide.md#conflicts-and-proposed-resolutions):
   metric definitions/applicability, period/TTM/YTD/EPS reconstruction, source
   precision, debt/lease/common-equity/EBIT gaps, history and freshness policies,
   statuses and coverage. Inventory original S5 metrics as supported, blocked or
   explicitly deferred. Any concept/schema/missingness change gets sequential
   review before implementation; do not invent new concept strings.
2. **S5b — Pure calculations and fixtures.** Write hand-calculated expectations
   first. Add metric registry, eligible period assemblies and ratios with exact
   formula/operand provenance. Reuse approved source selection outside core.
   Implement source-only metrics without requiring a new live provider. Return
   explicit gaps for price/calendar/action/estimate or concept dependencies.
3. **S5c — Interpretation and history.** Add neutral observations, deterministic
   top-three deduplication/priority, versioned freshness/trend policy, 3/5/10-year
   percentile bands and coverage. Use per-sample historical facts/quotes and
   show excluded samples. Keep old snapshots and unavailable states honest.
4. **S5d — Verification and S6 handoff.** Independent plausible-wrong-number
   review, required full checks and source spot checks. Supply S6 with tested
   metric definitions and a proposed result projection; S6 still owns public
   routes, snapshot persistence, generated OpenAPI/TS and cache contracts.

These are work slices within S5, not replacements for S6–S8. Their statuses are
all planned. S4b's corporate-action/ADS contract and reviewed session coverage
can proceed as separate prerequisites without delaying source-only formula work.

## Acceptance

- All [F1 requirements and A1–A5](../features/F1-fundamentals-guide.md#requirements-and-acceptance-trace)
  assigned to core pass, including the six supplied synthetic examples.
- Missing, zero, negative, near-zero, stale and unsupported inputs yield defined
  outcomes, never NaN/infinity, fabricated values or favorable rankings.
- Quarter, fiscal year, YTD and TTM remain distinct. No mixed scope, currency,
  accounting/earnings basis, reporting edition or incompatible split history.
- Reported facts stay unchanged; derived outputs carry every operand and rule.
  Runtime accounting mismatches raise evidence-bearing flags without correction.
- Comparison windows 3/5/10 have explicit eligible/excluded counts and dates,
  reviewed minimums and boundary tests. Insufficient history gives no band.
- ROE/EBIT/debt and price-dependent metrics remain unavailable until their
  particular evidence/contract requirements are met. Optional forward estimates
  never become a DCF input.
- `make test-core` contains real numeric tests; full checks and golden/restatement
  regressions pass. Numeric review covers plausible but incorrect results.

API, snapshot storage and cache acceptance finish in S6; keyboard/mobile/shared
snapshot and beginner walkthrough acceptance finish in S8/U1. S5 completion is
not a claim that the full feature or application is released.

## Evidence and handoff

The 2026-09-19 planning audit verified a clean completed S4a checkpoint, read all
79 blocks/five tables/seven rendered pages of the supplied DOCX and compared
contracts against the code. Independent audits covered financial identity/PIT/
source coverage and market/history/W1 dependencies. No feature tests or code
were added during planning. Detailed conflicts and source checksums are linked
from F1. D020 records planning scope; D021 remains open for concrete review.

Planning verification encountered a local runtime issue: the first mandatory
hook run passed 716 tests but its concept-generation subprocess could not import
`equity_schema`. The project's existing editable-install `.pth` was again marked
hidden. Both concept tests passed with `PYTHONPATH` set only to the validated
strict editable tree named by that pointer. The full hook retry uses the same
explicit path inherited by subprocesses; it does not skip a check, alter a
package/dependency, or change feature code. This is a local verification workaround,
not evidence that the launcher permanently fixes hidden-pointer recurrence.
