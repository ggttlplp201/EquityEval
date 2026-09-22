# S5 — Ratios and guided fundamentals

Status: first source-metric/history slice implemented 2026-09-19; full S5 in progress.
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Implementation branch: `codex/s5-source-metrics`
Planning checkpoint: `c1f2697` on `codex/fundamentals-plan`
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

These are work slices within S5, not replacements for S6–S8. S5a now has a
bounded source-input review and the complete backlog inventory. S5b source
formulas and S5c generic history mathematics are partially implemented; the
remaining period/metric/interpretation work stays open. S5d review applies only
to this first slice, not the eventual whole-engine acceptance. S4b's corporate-
action/ADS contract and reviewed session coverage
can proceed as separate prerequisites without delaying source-only formula work.

## First implementation checkpoint — D022

User instruction: “implement the next step,” after planning was committed.
Implementation, tests and review are indexed in [S5 design](../design/s5/README.md).

- Pure `FinancialInput` wraps the existing selected fact/statement, period, unit,
  scope and optional explicit source precision; provenance and source flags remain.
- `Calculation` retains exact operands, formula revision, `Decimal`/`None` and
  flags. Supported formulas are selected amounts, compatible calendar-quarter/
  year revenue YoY, gross/operating/consolidated-net margins, explicit derived
  gross margin, CFO-minus-cash-PPE-capex FCF and FCF margin.
- Generic history math supports explicit 3/5/10-year policies, exact percentile
  interpolation, eligible/excluded samples, missing quarter ends and unavailable
  bands when the caller's minimum is not met. No application default is chosen.
- [Manual terminology](../user-manual/fundamentals.md) accompanies these formulas.
  No API, saved fundamental snapshot, W1 metric stage or interface is claimed.

The [metric inventory](../design/s5/metric-inventory.md) preserves all original
S5 families. The [review](../design/s5/review.md) records red/green regressions,
independent numeric checks and the archived-source coverage limitation. The
focused core suite passes 150 tests. Required
full repository checks remain the mandatory, non-bypassed commit gate.

## Period prerequisite completed before X1

On `codex/sector-explorer`, the next bounded source-only prerequisite was finished
before any Sector Explorer math began. [Period assembly](../design/s5/period-assembly.md)
adds annual, contiguous-quarter TTM, same-edition YTD subtraction and explicit
revision-compatible annual/YTD TTM bridges. Existing metric formulas consume
these derived amounts and retain every source operand, precision and coefficient.
Fourteen period tests and three formula-integration regressions brought core
coverage to 167 passing tests. Independent review found no blocking numeric issue.
The 3/5/10-year fundamentals history options are unchanged.

## Next bounded step

[D1b](D1b-company-news-help.md) now renders the existing source calculations in
a guided fictional Company page with exact evidence, missing inputs and
3/5/10-year history controls. It introduces no additional financial formula or
production result/API contract and does not complete S5/F1.

D026/D027 advance [R1](../features/R1-business-aware-research.md) within the
UI-redesign-first/small-pilot sequence. The [change explanation packet](../design/research-refinements/change-explanations.md)
proposes comparable annual operating-margin attribution as the first later
numeric extension, with tests before implementation; profile applicability and
evidence-based neutral rules share the same review. No new calculation is
implemented by that design packet.

The [D2 real-data pilot](D2-real-data-pilot.md) connects archived CRCL observations
to the redesigned source view and keeps all seven requested issuers in a dated
coverage roster. Incomplete history and absent application publication prevent a
real PIT/core result. No synthetic test selection is promoted into application data.

Complete remaining supported metric definitions and neutral interpretation.
EPS, common-equity/debt definitions and applicability need their stated evidence;
new concepts or shared schema/API shapes still require sequential contract review.
Keep S4b/calendar prerequisites explicit for price/share metrics. S6 handles
public result/cache contracts and immutable W1 publication; S8/U1 completes
controls and the verified product walkthrough. Do not mark S5 complete on the
basis of this checkpoint.

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

## Liquidity follow-on — 2026-09-21

After D4c UI acceptance, the user requested continuing functional work.
[S5b liquidity](S5b-liquidity.md) adds current ratio and reported net working
capital using existing selected balance-sheet concepts and Calculation output.
No schema/API or source activation; real publication remains downstream.

## Annual ROA follow-on — 2026-09-21

The user's next continuation adds [annual ROA](S5b-roa.md) to the pure engine,
using exact opening/closing asset dates, same-edition source evidence and
positive endpoints at reported precision. Publication and other returns remain
in their existing later milestones.

## Fiscal-period follow-on — 2026-09-22

[S5b fiscal](S5b-fiscal.md) extends period assembly using exact reviewed fiscal
calendars and tightens cross-edition growth. The [completion plan](../design/s5/completion-plan.md)
continues through remaining unblocked S5 work to the S6 proposal gate.
