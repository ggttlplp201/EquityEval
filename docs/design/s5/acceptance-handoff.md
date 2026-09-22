# S5 acceptance disposition and S6 handoff — 2026-09-22

**Remaining unblocked source-only engine work is complete at this boundary.**
This does not claim full SPEC 4.1, F1 release, live watchlist analysis or S7
valuation completion. The accepted UI, 3/5/10-year controls, archived evidence,
fictional/real distinctions and all applied migrations are preserved.
Baseline for this continuation: `7191276` / `milestone/s5b-roa`.
Fiscal checkpoint: `ac81370` / `milestone/s5b-fiscal`.

## Implemented and verified boundary

| S5 requirement | Evidence / disposition |
| --- | --- |
| Source amounts, growth/margins/cash, liquidity, annual ROA | Existing calculators reused; ten metric IDs plus checked-concept reported amounts route through calculation reconstruction in `assessment.py`. No separate financial engine. |
| Quarter/year/YTD/TTM compatibility | Existing calendar paths plus exact reviewed month/52/53-week calendars, source/hash/issuer/PIT proof and edition review. Transition calendars, unequal weekly growth exposure and unsupported reconstruction return gaps. |
| Precision, scope, lineage and missingness | Every source operand, signed period coefficient, uncertainty, policy and flag retained. Decimal-only bounded arithmetic; no parent/common, instrument, cash/debt or currency substitution. |
| Applicability and freshness | Explicit versioned issuer/business/lifecycle/instrument policy, independent per-metric applicability roster and frozen age/expected-filing evaluation. No production profile or default age limit inferred. |
| Neutral interpretation | Evidence-linked facts and deterministic at-most-three distinct review topics; stale/unavailable inputs cannot drive financial labels. No score, bargain/value-trap or buy/sell output. |
| Quarterly growth trends | Exactly three consecutive compatible direct-quarter YoY rates; caller's versioned tolerance, strict/inclusive boundaries, source/edition/profile/context safeguards and no universal threshold. |
| Coverage | Complete valid or evidenced N/M / all applicable metrics; explicit per-status/unresolved counts. Omitted inputs cannot shrink denominator. Mixed company selection contexts rejected. |
| 3/5/10-year own history | Existing exact percentile, equality, minimum/sample/exclusion and boundary tests remain unchanged. Actual historical collection and product defaults stay gated. |
| Runtime accounting check | Assets − liabilities − equity including NCI, within summed evidenced absolute error. Negative equity retained; mismatch flagged without correction. Other identities remain unsupported for missing scoped inputs. |
| Real-source regression | Existing selected-source/golden and restatement tests remain required by the full hook. New profiles/calendars are fictional test inputs; no synthetic selection is published as CRCL evidence. |

## F1's six supplied examples, individually reconciled

| Original B065 example | Acceptance at this boundary |
| --- | --- |
| Price60 / EPS2 and growth15% → PE30 / PEG2 | **Blocked for source-backed execution:** verified quote, share/action EPS basis and dated estimate/growth definition. X1's evaluated common-cap/common-income P/E helper is a different basis and cannot be relabelled price/diluted-EPS. No fake estimate input added. |
| Price10, EPS−.50 from−1 → N/M and loss narrowed .50 | **Blocked for EPS interpretation:** exact instrument/split/earnings basis and approved EPS transition convention. Source facts can remain separate; no positive EPS growth percentage or cheap-stock label. |
| Revenue1m, operating loss−72.7m → margin−7,270% | **Pass, source-calculator and assessment fixtures:** fraction−72.7 retained, explicit extreme-margin data review, no clamping or inference of reporting error/valuation. UI formatting remains existing S8 responsibility. |
| CFO12m, PPE purchases20m, revenue100m → FCF−8m, margin−8% | **Pass for cash-PPE FCF/margin and deduplicated neutral review.** P/FCF/source capitalization remains gated. No inference that financing cash or total cash declined. |
| PE8, no eligible history, revenue−12% | **Pass for −12% revenue observation and existing insufficient-history behavior.** No below-range or bargain label. Real P/E source eligibility remains blocked; the synthetic multiple helper is not new source evidence. |
| Net loss−10m and equity−20m → ROE N/M | **Blocked for ROE:** reviewed common-income/common-equity definitions. Do not substitute consolidated ROA or parent equity to make this test green. Generic denominator/precision guards and negative-equity accounting checks do not claim implemented ROE. |

A1/A2 pass for supported formulas and periods, with their explicit unsupported
outcomes. A3's core rule lineage, freshness, N/M coverage and history/trend
boundaries pass; immutable storage/cache isolation is S6 acceptance. A4 is partial
by the table above; EPS, net cash, dilution, restricted-cash scope and failed
refresh are blocked or owned by later source/S6/S8 work. A5's real ticker, shared
snapshot, keyboard/mobile/manual release acceptance remains S6/S8/U1. Do not mark
all six examples or full F1 complete because the available subset passes.

## Remaining blockers, with owners

- **Production policy/evidence (D021/R1):** reviewed company/segment assignments,
  effective/known dates, permitted instrument basis, metric applicability and
  actual fiscal/precision/revision evidence. Proposed age, history minimum and
  trend sensitivity values remain configurable test inputs, not defaults.
- **Period/metric definitions:** irregular/transition calendars, unequal-week
  comparability, assembled/fiscal ROA and assembled-quarter trend extension need
  reviewed definitions. EPS reconstruction/action identity, common earnings/
  equity, debt/leases, EBIT/EBITDA, invested capital/tax/WACC, day counts and
  composite-score conventions remain inventory items; no new concepts invented.
- **Additional accounting:** cash-flow net change with matching restricted-cash/
  currency/scope bridge and segment-to-consolidated coverage are absent. An
  arbitrary sum of existing tags is not an acceptable substitute.
- **S4/S4b and data rights:** quote currency/identity, retained-use entitlement,
  session coverage, actions/ADS and optional estimate vintages are still required
  for their price/share metrics. No provider or account activation in S5.
- **D027 attribution:** symmetric operating-margin decomposition remains a
  proposed numerical convention, not an activated rule. No price/EPS/sector
  attribution inferred from existing margin calculations.
- **S6/W1:** typed immutable input/result storage, exact cache and rerun identity,
  atomic/fenced publication, failed refresh and public/generated contracts remain
  at [the concrete review packet](../s6/publication-contract-proposal.md).
- **Real-data tracer:** governed normalization/PIT selection and proof-backed
  source inputs do not yet exist as an application financial batch/result.
  Source acquisition/filing detection is not financial analysis publication.
- **Full P0:** D004/D005, S7 assumption/DCF/range behavior, X1 real universes,
  N1 ongoing news/event monitoring and S8/U1 release flows retain their milestones.

## Verification and reviews

Fiscal slice: **1,333 full / 321 core / 110 golden**, lint/typecheck pass; required
hook at `ac81370`. Next slice adds **65 tests**, bringing core to **386** before
its full mandatory hook. Red runs showed absent modules and subsequently six
review regressions failing before repair. Exact final full-suite counts and the
checkpoint commit are recorded in the annotated milestone tag.

Numeric/spec review initially found no numeric defect within the documented
boundary but highlighted cross-metric aggregation coherence. Standards review
found an annual-wrapper classification defect. Both were reproduced and repaired:
missing/unsupported stays missing/unsupported, edited assemblies stay invalid,
and summaries reject incompatible selection contexts. Follow-up reviews report
no actionable findings; standards reviewer independently invoked eight focused
cases. No UI changes were made, so no new browser verification was needed.
