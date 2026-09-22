# S6b / S7a — Assumptions and reverse valuation contract proposal

Implementation status update — 2026-09-22: coordinator approved `5b85140`
for synthetic S6b/S7a. The original proposal/acceptance text below is retained as
review history. See [the milestone](../../milestones/S6b-S7a-valuation-contract.md)
for implementation, audits and actual verification results.

**Status: proposed, awaiting coordinator review. No implementation authorized.**
Prepared 2026-09-22 after coordinator acceptance of `3909572`,
`milestone/s6a-fundamentals`. That checkpoint, migrations 0001–0011 and retained
S6a evidence remain unchanged. This packet is a design and acceptance proposal,
not an API/schema/model already available in the application.

Read alongside the [numeric and integration acceptance plan](../s7/acceptance-plan.md),
[S6a contract](implementation.md), [S5 boundary](../s5/acceptance-handoff.md),
[S2 deferred records](../s2/schema-proposal.md) and [decision register](../../decisions.md).

## 1. Decisions submitted for approval

| Decision | Proposed resolution | Consequence |
| --- | --- | --- |
| D004 | P0's primary workflow is **reverse DCF**: hold the dated market value fixed and solve one declared revenue-growth, operating-margin or reinvestment assumption at a time. | Other assumptions are explicit and frozen. Solving several unknowns from one price is underdetermined and rejected. A forward valuation screen remains a later comparison. The internal cash-flow evaluator is necessary for reverse solving and sensitivity, not a hidden forward workflow. |
| D005 | P0 range means a **deterministic span across named scenarios or explicit sensitivity cells**. | No probabilities, weights, confidence interval, price target, fair-value certification, recommendation or Monte Carlo. The primary reverse range is in the solved assumption's units; optional repricing cells use currency or currency/share and are labelled separately. |
| D010, P0 portion | Generate a target with the same evaluator/bridge, reverse-solve one parameter, then reprice the solution. | Compare compatible units and declared Decimal tolerances. Recover the original parameter only when uniqueness is certified. The nonlinear Monte Carlo median assertion remains outside P0. |
| D009, S7a portion | Require a dated, explicitly supplied WACC assumption and dated risk-free evidence or a separately labelled risk-free assumption. | No default ERP, beta, debt spread or live rate. Automated WACC construction and its source eligibility remain later reviewed work. |
| D038 | Approve the concrete bounded model, ownership, failure semantics and gates below before implementation. | A planning request does not approve the proposed tables, routes, formulas, domains, solver policy or real publication. |

The proposed resolutions reconcile SPEC 0.1/0.2 with its conflicting P0/P1 list;
they do not rewrite the original specification. P1 retains probability models,
correlations, Monte Carlo and any probabilistic calibration claims.

## 2. First supported model and explicit limits

Proposed definition: `reverse_fcff_operating_v1`, one currency, nominal annual
end-of-period cash flows, constant WACC, Gordon terminal value, 5–10 forecast
years selected explicitly. Forecast horizon is distinct from F1's 3/5/10-year
historical comparison window. No exit-multiple terminal method in S7a.

The profile must explicitly approve an operating-company FCFF interpretation.
Banks, insurers, reserve-backed/customer-asset businesses, REIT-specific models,
asset liquidation, mixed currencies and unreviewed segment/class allocations
remain `unsupported` until an appropriate reviewed model exists. A business
label alone does not establish applicability. This is not an assertion that any
named watchlist company is eligible. Profiles may suggest questions; they cannot
change formulas, tax policy, domains or thresholds invisibly.

S7a supports three **separate**, single-unknown runs:

1. `revenue_cagr`: constant forecast revenue CAGR; annual margins and reinvestment
   intensities are fixed explicit vectors.
2. `terminal_operating_margin`: one terminal margin; annual margins follow
   `m_t = (1 - weight_t) * anchor_margin + weight_t * terminal_margin` using
   explicit ordered weights in [0,1], nondecreasing, final weight 1. No automatic
   fade schedule. Growth and reinvestment stay fixed.
3. `reinvestment_to_revenue`: one constant forecast net-reinvestment/revenue
   intensity; growth and annual/terminal margins stay fixed. It does not change
   the independently declared terminal ROIC policy.

All constant values, annual vectors, terminal values and solver bounds are
required. The solved slot is an explicit `solve_parameter` marker, not null
meaning missing or a secretly supplied default. An input cannot be both fixed
and solved. Variable ROIC, multiple-variable fitting, endogenous WACC and
forecast dilution/funding models are deferred, not approximated.

## 3. Facts, assumptions and time

A base S6a snapshot supplies eligible historical evidence, not forecasts. Reuse
its private typed selections and source hashes; its public display projection
alone cannot reconstruct an eligible model input. Preserve the source snapshot's
saved statuses. Evaluate a separate, frozen **valuation eligibility assessment**
under the new valuation date and explicit freshness policy; do not age or edit
that snapshot. Stale/inapplicable/ambiguous required facts block numerical output.

A model has an explicit `valuation_at` UTC instant, financial filed cutoff,
capture vintage, source-known boundary, selected quote/session, reporting basis,
currency, forecast schedule and history mode. Evidence known after the historical
valuation cutoff cannot enter a historical run. A later local capture can only
support a reconstruction when the existing PIT contract proves what was publicly
known by that cutoff; it does not upgrade date-only publication to intraday proof.

The revenue anchor at model time zero is an **annual run-rate assumption** with
its own rationale. It links to a selected historical annual/TTM revenue fact and
its period, filed date and retrieval time. Explicitly choosing to carry that value
forward does not turn an old period into current revenue. Source lag, calendar
basis and the chosen carry-forward/rebase method remain visible and hashed.
S7a accepts calendar-year-equivalent anchors; weekly/transition annualization,
fractional stub periods or unreviewed rebase methods return typed unavailable.

Forecast dates are explicit anniversaries of valuation date, with discount
exponents 1 through N under `annual_end_period_v1`. Calendar-anniversary and leap-
day treatment must be pinned in the model schedule, not taken from server locale.
No historical year-to-date cash flow is counted again as a future full year.
Cash flows/discount rates must share nominal currency and compounding basis;
there is no implicit FX, inflation, annualization or percent/fraction conversion.

Each assumption entry carries: stable parameter key, typed value/vector, unit,
period or effective dates, author, authored/known dates, rationale, optional typed
supporting evidence and an explicit user-judgment origin. A source reference is
support for an assumption, not proof that its forecast is a company fact.
A retrospective assumption cannot be labelled as an ex-ante historical record;
backdated authorship is forbidden. A historical scenario authored today must be
labelled retrospective and excluded from any future forecasting-skill score.

## 4. Proposed formulas and numeric policy

The structural FCFF definition is after-tax operating income less net investment
in operating assets. It is different from the existing S5 CFO-minus-PPE cash-flow
metric. Do not relabel or reuse the latter as FCFF. [Damodaran, cash flows to the firm](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/cashflows.htm)

For t = 1..N, all rates below are fractions:

```text
R_t         = revenue_anchor * product(1 + growth_j, j=1..t)
EBIT_t      = R_t * operating_margin_t
cash_tax_t  = max(EBIT_t, 0) * tax_rate_t
NOPAT_t     = EBIT_t - cash_tax_t
I_t         = R_t * reinvestment_to_revenue_t
FCFF_t      = NOPAT_t - I_t
PV_t        = FCFF_t / (1 + wacc)^t
```

`I_t` means **net capex (capex minus D&A) plus change in non-cash operating working
capital**, under the declared lease policy. It is a forecast composite assumption,
not a reconstructed missing source fact. S7a requires `I_t/R_t >= 0`; divestment/
capital-release forecasts need a later model. It retains negative EBIT and FCFF
without clamping. `tax_on_positive_ebit_no_nol_v1` is an explicit simplifying tax
assumption: no immediate tax refunds, NOL balances or loss-carryforward benefits
are invented. Users requiring those mechanisms get an unsupported-model reason.
Tax rates lie in [0,1]; terminal tax must be below 1. Forecast margins may be
negative; terminal margin must lie in (0,1] for this limited operating model.

Terminal growth and reinvestment are linked through a declared stable return on
invested capital, rather than assuming growth requires no investment.
[Damodaran, terminal reinvestment and return on capital](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/termvalueexreturns.htm)

```text
R_(N+1)         = R_N * (1 + terminal_growth)
NOPAT_(N+1)     = R_(N+1) * terminal_margin * (1 - terminal_tax_rate)
terminal_I     = NOPAT_(N+1) * terminal_growth / terminal_ROIC
terminal_FCFF  = NOPAT_(N+1) - terminal_I
TV_N           = terminal_FCFF / (wacc - terminal_growth)
PV_TV          = TV_N / (1 + wacc)^N
operating_EV   = sum(PV_t) + PV_TV
```

Domains: revenue anchor > 0; every growth rate > -1; WACC > 0;
`0 <= terminal_growth < min(risk_free_rate, wacc, terminal_ROIC)`; terminal_ROIC > 0.
These are proposed model-domain restrictions, not universal economic truths.
They preserve the repository's hard `terminal_growth < risk_free_rate` rule and
also prevent a nonpositive Gordon denominator or unsustainable terminal cash flow.
Negative-risk-free/negative-terminal-growth regimes require a different reviewed
model rather than relaxing the rule or substituting a rate. Terminal FCFF must
be positive. A jump to terminal margin/reinvestment is disclosed in the final
forecast row; it is never silently smoothed.

Numeric policy proposal `decimal_dcf_v1`: isolated Decimal contexts, precision 80,
ROUND_HALF_EVEN point evaluation; finite inputs limited to 40 coefficient digits
and absolute stored/adjusted exponent 100. Reject floats/nonfinite values before
computation. No money rounding between steps. Overflow, invalid operations,
precision exhaustion or values outside bounds produce typed numeric failure,
not infinity or zero. Directed ROUND_FLOOR/ROUND_CEILING interval evaluation
supports proof of solver signs and uniqueness; it uses Decimal too. The complete
policy and operation order are versioned and included in cache identity.

Every run explicitly specifies absolute residual tolerance in valuation currency,
relative residual tolerance, solved-variable interval-width tolerance, maximum
iterations, interval subdivisions and evaluation budget. Proposed hard caps are
256 iterations per bracket, 4096 subdivisions and 10000 function evaluations;
caller limits may be lower, never silently raised. Display rounding cannot
satisfy a convergence test. Required acceptance proves caller Decimal contexts do
not alter results. These numeric choices are proposed, not deployed defaults.

## 5. Enterprise-to-equity and market target

Separate the value of operating assets from common equity and its claims. A
market-capitalization calculation must identify the complete issuer equity basis;
a quote for one class is not automatically that capitalization.
[Damodaran, enterprise-value definitions](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/definitions.html)

A `BridgeInput` contains individually eligible, dated amounts and complete scoped
claim coverage for unrestricted non-operating cash C, separately valued non-
operating assets A, financial debt D, operating lease claims L, preferred claims P,
noncontrolling interests M, and other senior/dilutive claims O. Each has unit,
currency, source and valuation basis. Actual source zero or a reviewed evidenced
absence can supply zero; missing, unsupported or unreviewed cannot. Reserve/client
cash is not added. Cross-holdings cannot be in both operating earnings and A.
Debt containing lease liabilities cannot also be subtracted as L. Each economic
claim has an identity and an explicit inclusion/exclusion explanation to prevent
double counting. In S7a, debt/claims require an eligible economic valuation;
automatic book-to-market proxies are deferred.

```text
common_equity = operating_EV + C + A - D - L - P - M - O
market_EV_target = eligible_total_common_market_value - C - A + D + L + P + M + O
reverse_residual(x) = operating_EV(x) - market_EV_target
```

The first supported per-share bridge is deliberately narrow: one economically
homogeneous common-equity claim pool, complete current share/quote coverage and a
reviewed **fixed** fully diluted common-equivalent basis. S7a requires evidence
that basic and diluted counts coincide and that options, warrants, convertibles
and contingent share claims are absent; it does not infer that from missing EPS
or option disclosures. Outstanding shares are a dated stock, not weighted-average
EPS shares. Multiple classes, ADS conversion, option exercise proceeds/treasury
stock, non-equivalent class rights and dynamic dilution return explicit reasons
until their allocation/dilution models and S4b action evidence are reviewed.
This limitation is a proposed acceptance boundary, not a claim that typical
watchlist companies meet it.

For this supported pool only, market common value is selected raw price times
eligible shares; conditional per-share value is common equity divided by the
same eligible shares. Quantity > 0, price > 0, explicit quote currency equals
valuation currency, and quote/session/freshness/action identity must pass. Raw
price and shares share one action basis. Adjusted total-return price, reporting-
currency inference, partial class capitalization or incomplete action coverage
cannot pass. A computed common-equity value <= 0 is retained as a model conclusion with
a nonpositive-equity reason; it is never clamped to a zero share value. Required
bridge ineligibility withholds both the market-target reverse solve and per-share
output; the component evidence remains inspectable.

Forecast EBIT/reinvestment must use the same lease treatment as the bridge.
Unknown lease adjustment does not become an assumed zero expense or claim.
Existing normalized debt/cash concepts alone do not prove these scope gates.
Missing reviewed source mappings/claim coverage are explicit prerequisites for
real use; synthetic economic-claim fixtures can test the contract without new
live normalization or changing `concept_std` in this planning step.

## 6. Solver result, domain proof and failure semantics

Solving uses one continuous scalar residual within a declared eligible domain.
Evaluate domain boundaries, preserve every excluded/invalid interval and retain
proof of continuity and derivative bounds under the fixed model. Bisection is the
initial bracket solver; no unreviewed Newton fallback or global optimizer.
Tax kinks in margin solves split the domain into explicit continuous pieces.

For growth, the residual is a polynomial in `1+g` for fixed annual coefficients;
negative cash-flow coefficients can defeat monotonicity. For the constant
reinvestment solve, with positive revenues and fixed other inputs, its derivative
is `-sum(R_t/(1+wacc)^t) < 0`. Margin solves have nonnegative fade weights and a
positive terminal contribution under this model's fixed tax/ROIC constraints.
These are model-specific certificates, not assertions for arbitrary plugins.

Use Decimal interval subdivision/derivative bounds to exclude root-free regions,
certify uniqueness in brackets and detect unresolved regions. A coarse scan or
same-sign endpoints alone cannot prove no solution. Sign-changing brackets can
miss tangential roots; unresolved derivative-zero regions must remain unresolved.
If the implementation cannot certify the declared domain within its limits,
return `inconclusive` rather than guessing uniqueness. This permits a small safe
solver first without pretending to solve every mathematically valid case.

Proposed discriminated `SolveResult` (does **not** alter S6a's seven metric statuses):

| State | Required content |
| --- | --- |
| `converged` | Exactly one certified solution over the eligible declared domain, original/final brackets, residual interval, solved-value interval, reproducible representative, actual budget/iteration counts and proof revision. Both width and residual tolerances pass. |
| `no_solution_in_domain` | Full root-exclusion proof over every eligible domain piece; tested domain and constraints retained. No solved scalar. No claim about values outside the bounds. |
| `non_unique` | Multiple distinct certified root intervals, or a proven continuum (`unidentifiable` reason); no preferred scalar/root and no implied-point headline. |
| `inconclusive` | Remaining possible-root regions, numeric/budget/precision reasons, candidate brackets and partial proof; no headline implied scalar. |
| `unavailable` | Required source, scope, bridge, applicability or input-policy reasons with operand references; no solver started. |

A root exactly on a boundary is accepted only when existence is certified, not
because a rounded residual looks small. Domain changes create new assumptions
and a new run; never expand a bracket, repair inputs or switch variables silently.
Residual tolerance is `abs_tol + rel_tol * abs(target_EV)`; target zero therefore
uses the supplied absolute tolerance. A solution also needs interval width <=
its parameter-unit tolerance. Precision-limited intervals do not converge merely
because Decimal midpoint rounding stopped moving.

No-solution/non-unique/inconclusive are **model outcomes**, not transport failures.
Publish the auditable outcome with W1 `completed_with_gaps`; required unavailable
inputs also retain a typed gapped result when the reviewed manifest is well formed.
Malformed requests are validation failures; cancellation/lease expiry/worker
exceptions publish no new model run. Their request state remains visible beside
the prior compatible run. A previous successful scalar is never inserted into
a newer unsuccessful conclusion.

## 7. Named scenarios, sensitivity and conclusions

A scenario set freezes an ordered roster of names and complete resolved assumption
sets. No implicit pessimistic/base/optimistic assignments, weights or probabilities.
All primary reverse scenarios use the **same market target**, solved parameter,
units and source/time basis; they change only named fixed assumptions. Each
scenario is a reproducible solve with its own result and lineage.

A primary range needs at least two distinct named scenarios and complete eligible
converged results across the requested roster. Its bounds are min/max of the
representatives, and it separately retains every solver interval. If any requested
scenario is excluded/unavailable/non-unique/inconclusive, headline range is null;
show per-scenario results and full coverage. Identical endpoints produce a labelled
degenerate range, never invented width. Scenario span is distinct from numerical
solver uncertainty and source measurement uncertainty.

Sensitivity requests contain explicit axes, ordered values, reference scenario,
held-fixed assumptions and output kind: either `reverse_implied_parameter` or
`conditional_reprice`. Reject an axis that is also the solved variable for a reverse
cell. WACC × terminal-growth and growth × terminal-margin grids use the declared
output kind; never silently change a reverse solve into a forward price chart.
Every invalid cell remains in coverage. Do not interpolate across invalid cells.
Repricing is a kernel diagnostic with conditional labels, not a new P0 target-price
workflow. No monotonicity is assumed when cash flows change sign, terminal
reinvestment changes, taxes cross a kink, or a coupled assumption changes.

Finite-difference sensitivity retains exact low/reference/high perturbations,
outputs and units. Elasticity is optional and null when its input/output reference
or step denominator is zero or otherwise ineligible. Rank only comparable
available rows under an explicit versioned ranking policy; preserve signs, ties
and excluded rows. Store ranks with the run's sensitivity results, **not by editing
assumption rows**. No universal top-three thresholds or significance tests.

Always retain PV explicit cash flows, PV terminal value, signed operating EV and
terminal contribution ratio `PV_TV / operating_EV` when EV > 0. For EV <= 0 that
ratio is not meaningful; show components and a typed reason. Do not clamp ratios
over 100%. Proposed dominance policy adopts SPEC 4.2(c)'s strict `> 0.75` flag as
an explicit revisioned policy input, not a formula-changing default. Exactly 75%
does not trigger. A flag changes neither cash flows nor the range.

Conclusions are deterministic evidence-linked statements such as “At the selected
price and these named assumptions, the model implies X revenue CAGR over N years.”
Historical/peer/base-rate comparisons require their own eligible dated S5/X1
results; otherwise N/A. No invented peer distribution, likelihood or event impact.

## 8. Immutable records, source ownership and proposed API

S6a is source-fundamentals-specific: its input table references fundamentals
reviews and its publisher completes that W1 execution. Do not make those records
polymorphic or call its publisher midway through a longer valuation transaction.
Start S7a from a saved S6a snapshot and retained S4 selections. Add typed valuation
composition records in a **new reviewed migration after 0011** (expected 0012 if
head is unchanged), with no changes to the existing snapshot bytes or writers.

| Proposed record | Identity, contents and constraints |
| --- | --- |
| `model_definitions` | Immutable model ID/revision, formula/domain/tax/lease/terminal/schedule definitions, numeric/solver algorithms, supported solve variables, semantic hash and engine artifact digest. Owner reviewed; no user-editable formula strings. |
| `assumption_sets` / `assumption_entries` | Immutable UUID, workspace, parent set, explicit parameter schema/version, values/units/dates, authorship and rationale; typed optional evidence links. New edit creates a new set. Unique parameter key; no generic unchecked JSON inputs or mutable source facts. |
| `valuation_policy_revisions` | Reviewed applicability, freshness/action/claim eligibility, dominance and sensitivity policy contents; scope/effective/known dates and retained evidence links. Full content hashes, not names alone. |
| `valuation_request_intents` | Unique W1 request; assumption set, complete scenario/grid roster, model definition, source snapshot, market selectors, bridge/claim policy, valuation time and membership generation. Created atomically with W1 enqueue, before claim. |
| `valuation_input_snapshots` and typed links | One immutable composite frozen manifest per logical valuation request, creating execution, exact S6a snapshot/hash and retained source selections, S4 composite observation keys/captures/known dates, claims/shares/action proofs, full assumptions/policies and eligibility assessment. No copied mutable fact store or generic-ID escape hatch. |
| `valuation_payloads` | Canonical, content-addressed forecast rows, bridge, all solve/cell/coverage/proof outputs, sensitivities and conclusions; dependency digest and verified typed projection. Not a model-run identity. |
| `model_runs` | New immutable UUID per explicit W1 request, execution/input/payload, parent run, generated time, outcome and evidence mode. Unique logical publication; intentional reruns may share a payload but never a run ID. |
| `scenario_results` / `sensitivity_results` / `model_conclusions` | Immutable typed children sealed atomically with their run/payload; no post-publication append or mutable sensitivity rank. Request roster and exclusions remain auditable. |
| `latest_valuation` | Exact compatible scope/model/source/assumption/scenario/policy/time key, latest requested sequence and separate latest eligible published run. Monotonic W1 ordering and membership generation, never completion time. |

Reusing patterns is not copying migration functions into a parallel queue. Reuse
W1 workspace, membership, requests, executions, stages, lease/epoch/token, events,
retry/cancellation and existing source selectors. The new typed input envelope
composes those records because S6a's existing table cannot represent valuation
without changing its approved contract. Extract shared non-domain helper code
only when it preserves all S6a behavior and regression tests.

Proposed routes and generated models, all workspace-bound through the existing
trusted-local composition boundary:

| Route | Typed behavior |
| --- | --- |
| `POST /assumption-sets` | Explicit new set or parent-linked revision, complete entries and idempotency key. Return immutable set ID/hash. User judgment only; cannot update facts, formulas or profiles. |
| `GET /assumption-sets/{id}` | Exact authorized saved set; private authorship/rationale protected from cross-workspace access. |
| `POST /valuation-requests` | Narrow W1 wrapper with full typed intent, explicit parent/membership and idempotency key; 202 with request identity. No synchronous calculation/provider acquisition. Same key/different contents is 409. |
| `GET /valuation-requests/{id}` | Request/execution/stage state and typed public error codes; no private worker/contact details. |
| `GET /model-runs/{id}` | Exact saved run and immutable evidence/assumption projection, without re-solving or aging labels. Unknown/cross-workspace 404. Reject conflicting selector queries with structured 422. |
| `GET /companies/{issuer_id}/valuation` | Explicit security/quote, scope and complete compatibility key; latest request state separate from saved run. No compatible result gives typed 404, not nearest assumptions or latest stale price. |

No S6a route/metric-status change. Model-specific discriminated results and Decimal
string fields generate OpenAPI/TypeScript with no-diff enforcement. Decimal scale,
nulls, units and scenario order survive roundtrip. Extra fields and unknown enum
values fail validation. Mutation routes require explicit local-user action and
workspace binding; remote/multi-user authentication, provider activation and alert
sending are outside this approval proposal. No default credential/network setup.

## 9. Publication, cache and recovery

1. Validate and atomically enqueue the complete intent using W1; bind the latest
   requested sequence before worker claim. An initial valuation references the
   source fundamentals request; a rerun references its prior compatible valuation
   request/run. Parent workspace/security/quote/membership generation must match.
2. Select existing retained evidence under consistent PIT reads and freeze all
   typed inputs before calculation. A retry reuses those frozen inputs; new facts,
   assumption edits or revised bounds require a new logical request.
3. Calculate in pure `packages/core` outside the DB transaction, with bounded
   solver work and between-batch lease/cancellation checks in the worker. Never
   call the DB/network from the numerical evaluator. Renew leases outside math.
4. Reproduce and verify payload/dependency digests, domain certificates and exact
   engine/model revisions. For the first synthetic tracer retain S6a-style owner
   fixture review/expected-output digests; no weakened production writer is implied.
5. Under the existing locked lease, recheck epoch/token/current execution,
   membership, stage and pinned review. Atomically insert/reuse payload, insert run
   and all children, finish stage/execution, record events and conditionally update
   the exact latest pointer. Runtime role has no direct mutation grants.
6. Same logical request/execution publishes at most once. Crash before commit
   leaves no partial result; exact replay after commit validates stored canonical
   bytes and envelope identity without requiring the current engine to re-solve.
   Wrong token/epoch/stage/input or payload is rejected, including NULL arguments.
7. A newer declared request prevents older promotion even if it fails before
   freeze. Failed/cancelled/expired work leaves the prior run reachable separately.
   Removed/re-added membership cannot revive an earlier generation's result.

Canonicalization uses S6a v1 sorted UTF-8 JSON, ordered arrays, exact Decimal strings
and UTC instants. Dependency identity includes full resolved assumptions, source
snapshots/observations/claims/exclusions, source-known/filing/capture cutoffs,
valuation time, price/action/share basis, every model/solver/tolerance/policy
content, scenario/grid roster and engine build. Exclude request/execution/run IDs
and generation clock only. Use a workspace-qualified cache boundary; no cross-
workspace reuse or equality leakage through public APIs. A semantic change misses
the cache even if its output happens to equal an old number. Reuse never promotes
an old run ID or recalculates a saved run on retrieval.

Immutable children, strict typed/composite FKs, owner-only definition/fixture
review, narrow SECURITY DEFINER writers, sealed creation transactions and retained-
history downgrade guards are required. Proposed compatibility includes assumption
set content hash and source snapshot hash; edited assumptions deliberately create
a separate exact pointer. Prior runs are compared by explicit IDs, not fallback.

## 10. UI and delivery gates

The accepted UI is unchanged by this proposal. Later integration should make
reverse DCF the primary valuation panel, with named scenarios as the main comparison
and graphs for explicit sensitivity cells. Always identify price/source date,
solved variable and units, held-fixed assumptions, horizon, bridge basis, source
snapshot, scenario coverage and numerical interval separately. Unavailable cells
show N/A; detailed reasons/proofs live in the evidence drawer rather than repetitive
page notices. Source facts, user assumptions and model conclusions remain visually
distinct. Editing creates a new assumption set/request/run and preserves history.

No user gets a bare single “fair value” headline. A single scenario can show its
conditional solved assumption with its inputs; the primary range stays N/A until
its requested multi-scenario roster qualifies. Terminal dominance and action/scope
failures remain concise, actionable disclosures. No probabilistic wording, trade
signal, automated recommendation, news alert or scheduler change.

Implementation sequence **after approval**: S6b typed records/API/migration and
synthetic W1 publication contract; S7a tested pure evaluator/bridge/solver/scenario
kernel and synthetic end-to-end tracer; then a distinct UI/manual verification
slice. Numeric tests precede numeric code. Full/core/golden/lint/type/build,
generated-client, migration, concurrency and independent numeric/spec/standards
reviews gate the checkpoint. Real valuation publication is a separate decision
requiring the currently missing quote/action/claims/dilution/normalization/policy
prerequisites. Stop here for coordinator review of this packet and its test plan.
