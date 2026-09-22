# S6b / S7a — Proposed acceptance plan

Status: **proposed; implementation and tests await coordinator review**.
Date: 2026-09-22. Baseline: `3909572`, `milestone/s6a-fundamentals`.
This is a test specification, not a report of implemented valuation behavior.
The [contract proposal](../s6/valuation-contract-proposal.md) defines all formulas,
domains, units, states and approval choices. Numeric tests must precede code.

## 1. Hand-computed oracle

All examples below are fictional, in one declared currency, with annual end-period
cash flows. Numbers are literal Decimal inputs, never binary floats. Use exact
rational identities for expected repeating results; do not generate an expected
answer by calling the implementation being tested. Public model horizons are
5–10 years. The three-period example tests the lower-level evaluator solely to
satisfy SPEC 12.3; it does not authorize a three-year public model.

Shared assumptions unless a case overrides them:

| Input | Value |
| --- | --- |
| Annual revenue anchor | 100 |
| Annual and terminal operating margin | 0.20 |
| Annual and terminal tax rate | 0.25 |
| Forecast net reinvestment / revenue | 0.05 |
| WACC; dated risk-free input | 0.10; 0.04 |
| Terminal growth; terminal ROIC | 0.02; 0.08 |
| Bridge C, A, D, L, P, M, O | 20, 5, 30, 10, 2, 3, 0 |
| Common-equity bridge adjustment | -20 |
| Eligible shares | 10, basic equals diluted with explicit evidence |

The synthetic claim coverage establishes each amount's identity, date and valuation
basis, including explicit absence for O. Financial debt excludes leases. Preferred
and noncontrolling claims do not belong in common shares. The chosen operating
cash flows have the same lease treatment as the bridge. Quote/action/session and
no-dilution evidence are part of the fixture, not deductions from these numbers.

### H01 — Three periods, no growth

R = 100 each year. EBIT = 20, cash tax = 5, NOPAT = 15, reinvestment = 5,
FCFF = 10 each year. Terminal revenue = 102, NOPAT = 15.3, reinvestment = 3.825,
FCFF = 11.475 and terminal value = 143.4375.

Operating EV = `(10 * 1.1^2 + 10 * 1.1 + 10 + 143.4375) / 1.1^3`
= `176.5375 / 1.331` = approximately 132.635236664162284.
Common equity = EV - 20; per-share value = `(EV - 20) / 10`.
Terminal PV = `143.4375 / 1.331`; terminal contribution exceeds 75%.
Assert every forecast row and both explicit/terminal PV components independently.

### H02 — Three periods, 10% growth

Revenue = 110, 121, 133.1; FCFF = 11, 12.1, 13.31. Each discounted FCFF = 10.
Terminal revenue = 135.762; NOPAT = 20.3643; reinvestment = 5.091075;
FCFF = 15.273225; terminal value = 190.9153125; terminal PV = 143.4375.
Operating EV = **173.4375**; equity = **153.4375**; per share = **15.34375**.
Terminal contribution = `153 / 185`, greater than 75%.

### H03 — Five periods, 10% growth, valid public horizon

Revenue = 110, 121, 133.1, 146.41, 161.051.
FCFF = 11, 12.1, 13.31, 14.641, 16.1051. Each discounted FCFF = 10.
Terminal revenue = 164.27202; NOPAT = 24.640803; reinvestment = 6.16020075;
FCFF = 18.48060225; terminal value = 231.007528125; terminal PV = 143.4375.
Operating EV = **193.4375**; equity = **173.4375**; per share = **17.34375**.
Terminal contribution = `143.4375 / 193.4375`, below 75%.

Use the selected synthetic raw quote 17.34375 and 10 eligible shares. The market
EV target is `17.34375 * 10 + 20 = 193.4375`. Reversing growth over [0,0.20]
recovers 0.10 within declared parameter and residual tolerances, with a uniqueness
certificate. Repricing uses the same assumptions, schedule, bridge and shares.

### H04 — Each supported unknown, and deterministic range

For H03's fixed 10% growth, constant annual/terminal margin m, and forecast
reinvestment intensity k, independently simplify:

`operating_EV(m,k) = 1092.1875 * m - 500 * k`.

At the same market target 193.4375:

- Fixed m = 0.20, solve k on [0,0.10]: **0.05**; derivative is exactly -500.
- Fixed k = 0.05, solve terminal margin on [0.10,0.30] with all fade weights 1:
  **0.20**. Test a second nontrivial fade vector independently; all-one weights
  alone do not validate the fade implementation.
- Named margin scenarios with k = 0.025, 0.05, 0.075 imply respectively
  **659/3495**, **0.20**, **739/3495**. Complete deterministic range is
  [659/3495,739/3495], approximately [0.188555078684,0.211444921316]. Retain each
  finite numerical root interval separately. These endpoints have no probability.
- Conditional repricing at margins 0.10, 0.20, 0.30 with k = 0.05 gives EV
  **84.21875, 193.4375, 302.65625**, equity **64.21875, 173.4375, 282.65625**,
  and per-share values **6.421875, 17.34375, 28.265625**. This diagnostic span is
  a different unit/output kind from the reverse margin range.

The fixture's target is chosen for exact arithmetic, not as a real quote or an
investment conclusion. Expected repeating numbers use declared Decimal tolerances.
All exact terminating identities must agree before display rounding.

### H05 — Valid model with two growth solutions

Use N=5, anchor=100, WACC=0.10, all tax rates=0, all forecast reinvestment=0,
annual margins [-1.10,0,0,0,0], terminal margin=0.161051, terminal growth=0,
risk-free=0.04 and terminal ROIC=0.08. The explicit terminal margin jump remains
visible. Let z=1+growth. Independently, operating EV is `100*z^5 - 100*z`.
With quote=1, shares=10, cash=30 and every other bridge component evidenced zero,
the market EV target is -20; residual is `100*z^5 - 100*z + 20`.

Over growth [-0.99,0] (z in [0.01,1]), the residual is positive at both endpoints
but negative at z=0.5 (-26.875). Its derivative has one positive turning point,
so there are two distinct roots in the domain. Certified isolation must return
non_unique; an intentionally limited proof budget may return inconclusive. It
must never report no solution from endpoint signs or select one implied CAGR.
This also tests a negative operating-value target with positive common equity.

## 2. Numeric and solver cases

| ID | Case | Required assertion |
| --- | --- | --- |
| N01 | R=100, margin=-0.10, tax=0.25, k=0.05 | EBIT=-10, tax=0, NOPAT=-10, reinvestment=5, FCFF=-15. No invented refund or clamping. Zero EBIT likewise has zero tax. |
| N02 | Forecast margin crosses zero under a fade vector | Piecewise tax policy is continuous at zero; derivative certificates split at the kink and do not assume differentiability there. |
| N03 | Zero/negative anchor, price, shares, ROIC; growth <= -1; invalid tax/margin/weights | Validation/domain failure with exact operand references. No zero substitution, absolute-value repair or unit coercion. |
| N04 | Terminal growth equals/exceeds WACC, risk-free or ROIC; negative terminal growth/risk-free regime | Correct strict domain rejection; no division by zero, rate repair or silent alternative model. Terminal tax=1 is invalid. |
| N05 | Terminal growth zero with positive other inputs | Terminal reinvestment=0 by formula, not missingness; nonzero terminal FCFF and valid finite value. |
| N06 | Terminal PV 150, EV 200; explicit PV then reduced from 50 to 49.999 | Exactly 75% has no dominance flag; strict greater-than does. Policy is recorded and cannot change the cash flows. |
| N07 | Negative explicit PV with positive terminal PV; total EV positive/zero/negative | Keep signed components; ratio may exceed 100%; EV <= 0 yields null ratio plus not-meaningful reason. Never use abs(EV). Negative equity stays signed. |
| N08 | Deliberately large/small admissible values, precision limits and caller Decimal contexts | Context-independent canonical results; no float/nonfinite input; bounded coefficients/exponents; precision/overflow/budget failure is typed, never a plausible rounded zero. |
| N09 | Two unknowns, solved slot also fixed, absent fixed vector, wrong vector length | Reject underdetermined/ambiguous requests before solve. No fitted hidden variable/default fade/tax assumption. |
| N10 | Constant nonzero residual; root outside requested bounds | Certified no_solution_in_domain only after full domain exclusion; never expand bounds or claim no possible economic solution. |
| N11 | f(x)=(x-1)(x-2) over [0,3] | Same-sign endpoints do not prove absence. Certified disjoint roots yield non_unique; unresolved work may be inconclusive, never converged to one preferred root. |
| N12 | f(x)=(x-1)^2 over [0,2]; endpoint root; identically zero residual | Tangency must be certified or inconclusive; exact endpoint needs existence proof; continuum is non_unique/unidentifiable. A rounded near-zero residual is not proof. |
| N13 | Too few iterations/subdivisions/evaluations; midpoint ceases moving | Inconclusive with retained candidate intervals and actual counts; no headline scalar or completed convergence flag. Enforce global as well as per-bracket caps. |
| N14 | Width tolerance passes but residual fails, and vice versa; zero/negative EV target | Both tolerances required; residual uses abs_tol + rel_tol * abs(target). Zero target uses absolute term only. |
| N15 | Multiple eligible domain pieces or excluded/invalid interval | Certificate accounts for every eligible piece; exclusions stay explicit. Any unresolved possible-root region prevents a uniqueness/no-root assertion. |
| N16 | Reverse/reprice round trip for growth, margin and reinvestment | Same inputs/basis; solution bracket includes the known parameter for certified unique fixtures; repriced residual meets currency tolerance. No comparison of currency to a rate. |
| N17 | Rate/share/currency scaling and equivalent Decimal representations | Explicit supported unit transformations preserve expected economics; wrong units rejected. Semantically equivalent lexical Decimals follow canonicalization v1 exactly. No automatic 10-to-0.10 conversion. |

N10–N15 include independent scalar-kernel fixtures and valid model-level cases.
Artificial polynomials are solver tests, not new valuation models. A valid model
with mixed-sign forecast cash flows must also demonstrate that a global growth
monotonicity claim is unsafe. Assert safe inconclusive behavior where certification
is intentionally outside the first solver's capabilities; do not weaken a domain
proof requirement merely to make an example converge.

Conditional invariants: positive fixed revenues make value decrease with the
forecast reinvestment intensity. Margin is monotone under the reviewed fade/tax/
terminal policy. WACC decrease/value increase only has its usual guarantee when
all discounted amounts are nonnegative and all other relevant inputs stay fixed.
Terminal growth also changes reinvestment: test ROIC above, equal to and below WACC
within the allowed domain. Never assert unconditional terminal-growth monotonicity.

## 3. Evidence, assumptions, bridge and scenarios

| ID | Case | Required assertion |
| --- | --- | --- |
| E01 | Reuse exact S6a historical source and private selections | Exact source IDs/hashes/typed operands/periods and transformations retained; public display values alone cannot create inputs. Saved S6 status never changes with the new valuation date. |
| E02 | Filed/public-known dates after historical cutoff; later retrieval; date-only filing | No lookahead; later capture accepted only with existing PIT proof. Date-only disclosure is not promoted to intraday certainty. Test timezone boundaries. |
| E03 | Today's authorship with a historical valuation date | Explicit retrospective scenario; never fabricate historical authorship or count it as ex-ante skill evidence. Future effective assumptions are explicitly forecasts. |
| E04 | Old annual/TTM fact carried into revenue anchor; 52/53-week/transition/stub cases | Rationale, source lag, calendar and rebase method retained; unsupported calendar conversion gives unavailable, not silent annualization. Leap-day schedule and discount exponents explicit. |
| E05 | Missing versus reported/evidenced zero in every bridge component | Missing blocks required solve/per-share; evidenced zero passes. No missing debt/leases/NCI/options treated as zero. Each claim's economic valuation basis is reviewed. |
| E06 | Debt includes leases, duplicate asset/claim, client/reserve cash, cross-holding earnings | Reject/flag incomplete or overlapping coverage; no double addition/subtraction or assumed book-to-market proxy. Cash-flow lease policy and bridge agree. |
| E07 | Multiple share classes, ADS, dynamic dilution, weighted-average EPS shares, option proceeds | Typed unsupported basis; a quoted class is never total issuer capitalization. First model needs positive current shares and proven basic=diluted/no dilutive claims. |
| E08 | Reporting USD only; adjusted quote/raw shares; split, stale session or incomplete action history | Unavailable with typed identity/action/currency/freshness reasons. No quote inference or corporate-action repair. |
| E09 | Bank/reserve/customer-asset profile, or otherwise unreviewed applicability | No FCFF result based only on a label. Changing profile/policy cannot silently select different formulas or thresholds. |
| E10 | Assumption edit, model revision or policy revision | New immutable identity and parent link; all former bytes remain retrievable. Facts, judgments and deterministic conclusions stay distinct. |
| E11 | H04 scenario roster; one missing/no-root/non-unique/inconclusive scenario | Complete eligible roster yields deterministic range; any ineligible requested row withholds headline range and retains all individual outcomes/coverage. No survivor-only min/max. |
| E12 | One named scenario; two distinct scenarios with identical solved endpoints | Single scenario has no primary range; identical endpoints allowed as a labelled degenerate multi-scenario span. Duplicate names rejected. |
| E13 | Scenarios vary price/solved variable/units/source basis | Reject as one primary reverse range. Source/solver/scenario uncertainty cannot be combined or labelled as probability. |
| E14 | WACC × terminal-growth and growth × margin grids; solved variable also an axis | Explicit output kind and held-fixed assumptions; illegal reverse axis rejected; every requested invalid cell retained, never interpolated. |
| E15 | Sensitivity reference/step/output is zero, ranks tie or some rows unavailable | Null ineligible elasticity, declared units/perturbations and comparable-only ranking; preserve sign, ties and exclusions. No mutation of assumption rows. |
| E16 | Missing peer/historical comparison, or absent news evidence | N/A; do not manufacture a base rate, likelihood, business cause or event effect. |

## 4. S6b persistence, W1 and API integration

| ID | Case | Required assertion |
| --- | --- | --- |
| I01 | Next additive migration from current head | Applied 0001–0011 untouched; next revision follows actual head. Fresh upgrade plus upgrade from S6a pass. Existing S6a behavior and privileges remain intact. |
| I02 | Cross-workspace/security/source/hash/parent/quote/membership link; orphan or nullable bypass | Typed composite FKs/checks reject mismatches, including NULL writer arguments. No unchecked generic ID or polymorphic mutation of S6a inputs. |
| I03 | Direct runtime mutation, late child append, reassigning content address, destructive downgrade | Denied; owner-reviewed definitions/fixture digests, sealed immutable children, hash verification and retained-history downgrade guard tested. |
| I04 | Assumption creation/revision and idempotent enqueue | New set on edit, one logical request on repeat; same idempotency key/different payload is conflict. Full intent and latest requested sequence exist before claim. |
| I05 | Crash after enqueue/before freeze; concurrent claim; new evidence after freeze | W1 recovery with one frozen manifest per logical request; retry cannot silently choose newer facts/assumptions. Parent/source request is explicit. |
| I06 | Numerical model outcome vs exception/transport failure | No-root/non-unique/inconclusive/unavailable publish typed completed_with_gaps; malformed intent fails validation. Exceptions/cancelled/expired workers publish no partial run. |
| I07 | Lease expiry, token/epoch mismatch, heartbeat, cancel or remove/re-add during calculation | Old worker cannot publish; pure core does no I/O; worker checks between bounded batches. New membership generation never revives old work. |
| I08 | Failure midway through publication or simultaneous duplicate publication | Run, children, stage/execution, events and pointer commit together or not at all. One logical publication; no child/payload mismatch. |
| I09 | A then B requested; B fails before freeze; A finishes late | Older A cannot promote over declared B; prior compatible saved run remains separately readable beside B's request state. Ordering uses requests, not finish time. |
| I10 | Exact replay after commit under changed current engine | Saved canonical bytes/envelope returned and verified without recalculation. A new explicit rerun gets a new run ID even when payload is reused. |
| I11 | Change each semantic dependency one at a time | Assumptions, policy contents, model/engine, bounds/tolerances, source/claim exclusions, cutoffs, price/actions/shares or roster change cache identity, even when the value is numerically unchanged. |
| I12 | Equal dependency content, different envelope IDs/times; other workspace | Eligible same-workspace reuse; workspace-qualified cache and authorization prevent cross-workspace reuse/equality leakage. Envelope identity is never reused. |
| I13 | Proposed API happy paths, wrong workspace and conflicting selectors | Explicit trusted workspace; exact GET only; 404 for absent/cross-workspace; structured 422 for malformed/conflicting selectors; POST request 202; idempotency-content conflict 409. No source acquisition on read. |
| I14 | Canonical/generated contract roundtrip | Decimal strings, scale policy, UTC instants, nulls, solve discriminators, units and ordered full rosters survive Python/JSON/TypeScript. Unknown enum/extra fields fail; generated OpenAPI/TS no diff. |
| I15 | Public projection and errors | Traceable public evidence without private email/contact/worker details; authorship protected by workspace. Missing data reasons retained without inventing zeros. |
| I16 | Synthetic end-to-end tracer | Owner-reviewed fictional inputs and expected digest → W1 intent/freeze → pure solve → atomic run → API read → rerun/cancel/retry. No provider/real source/scheduler activation. |

Test actual PostgreSQL writers/constraints/privileges and concurrent independent
connections, not just mock Python interfaces. Reuse existing W1/S6 integration
fixtures and API app-factory boundaries. S6b contract fixtures may use explicitly
reviewed expected payloads before the S7a evaluator exists; they must not claim a
numeric implementation passed. The full S7a tracer verifies recomputation later.

## 5. UI/manual follow-on and checkpoint gates

UI work follows the approved contract and kernel. Preserve the accepted design,
F1 3/5/10-year history and X1 chart distinctions. Verify selected price/date,
solved parameter/units, assumption editing/new-run history, full scenario roster,
explicit conditional chart labels and evidence links. Unavailable values show
N/A; detail belongs in the evidence drawer. No fair-value/target/probability or
buy/sell headline. Verify keyboard navigation and chart/table consistency using
saved fixture outputs; the frontend must not calculate valuation arithmetic.

The manual must distinguish facts/assumptions/conclusions; forecast vs history
horizon; EBIT/NOPAT/FCFF/net reinvestment/WACC/ROIC; operating EV vs common equity;
reverse implied assumption vs conditional repricing; deterministic span vs numeric
root interval; coverage, terminal dominance and no-solution/ambiguity. Explain
how to change assumptions and rerun without overwriting earlier results. These
are later acceptance requirements, not a claim that new UI/manual already exists.

Before an implementation checkpoint:

1. Coordinator approves or revises D004/D005 plus model/bridge/numeric/time/storage/
   API proposals and D010's valid P0 round-trip interpretation.
2. Numeric fixtures/tests fail meaningfully before their implementation; retain
   independent hand-calculated expected outputs and source-reference rationale.
3. Focused tests above, migration/privilege/concurrency acceptance, generated
   contract no-diff, and S6a regressions pass. Numeric/spec and standards review
   explicitly target plausible-but-wrong values and global-solver overclaims.
4. `make lint typecheck test test-core test-golden` and production web build pass;
   record actual counts, audit corrections and commit/tag. Do not use old S6a
   counts as evidence for S7a. No hook bypass.
5. A later real-data publication gate independently reviews quote/actions/claims/
   dilution/financial normalization/profile/calendar/precision and provider rights.
   Passing synthetic tests alone does not meet it.

## Proposal validation only — 2026-09-22

H01–H05 arithmetic was independently checked using Decimal precision 80 and the
explicit formulas, including exact bridge and scenario rational identities.
This planning step adds no evaluator, solver, migration, API or live data. Document
links/status/diff checks are recorded in the [proposal milestone](../../milestones/S6b-S7a-valuation-contract.md).
