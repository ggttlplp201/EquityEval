# S6b/S7a synthetic valuation implementation

D038 approves the contract checkpoint `5b85140` after S6a `3909572`.
Implementation uses migration **0012** only. Applied 0001–0011, S6a, the accepted
UI and production application data remain unchanged. This chapter describes
implemented synthetic behavior; the [milestone](../../milestones/S6b-S7a-valuation-contract.md)
records final verification and the [review](review.md) records audit corrections.

## Model and numerical proof

`packages/core/valuation.py` evaluates nominal annual FCFF using exact Decimal
inputs and an 80-digit local context. Forecast EBIT is revenue times margin;
cash tax applies to positive EBIT only, with no NOL credit. Net reinvestment is
revenue times the explicit intensity. Terminal reinvestment is terminal NOPAT
times growth divided by ROIC. Annual cash flows and the terminal value use the
same WACC and end-period discounting. Public horizons are 5–10 years; internal
three-period primitives support the independent H01/H02 arithmetic oracles.

Each scenario solves exactly one revenue CAGR, terminal operating margin with
an explicit monotone annual fade, or reinvestment/revenue ratio. Domain validation
requires positive revenue/WACC/ROIC, growth greater than -1, nonnegative
reinvestment, and `0 <= terminal growth < min(risk-free, WACC, ROIC)`. Terminal
margin is positive and at most one; terminal tax is below one. These restrictions
belong to `reverse_fcff_operating_v1`, not every business or valuation model.

Outward-rounded interval arithmetic and automatic derivatives enclose residuals
and slopes. Domain regions are excluded by interval range or proved monotonicity;
a unique root requires certified opposite endpoint signs and both bracket-width
and whole-bracket residual tolerances. The entire requested domain must be
accounted for before a unique/no-solution claim. Margin tax kinks are explicit
partition boundaries; nonterminating kink locations retain an outward band.
Every proof, isolated root, unresolved interval and budget counter is retained.
No grid sampling or local convergence substitutes for a global certificate.

Endpoint roots, tangencies, flat continua, tight precision limits and exhausted
budgets can return `inconclusive`. This implementation does not promise to solve
every mathematically soluble input. Such outcomes have no representative value;
proved multiple roots are `non_unique`. No-root means only the declared domain.

Named scenarios preserve the full requested roster. At least two eligible,
converged scenarios are needed for a deterministic span; incomplete rosters
withhold that span. Numerical root intervals, scenario dispersion and source
measurement uncertainty are separate fields. No probabilities are assigned.
Sensitivity cells explicitly distinguish reverse implied parameters from
conditional repricing. Both kinds retain signed EV/equity, forecast/terminal PV,
terminal contribution and reasons. Terminal contribution is N/M for nonpositive
EV and dominance is flagged strictly above 75%. Three-point elasticity ranks
only eligible comparable axes within a grid, preserving ties and missing rows.

## Evidence and immutable records

The owner review reproduces the exact S6a snapshot/input/selector and S4 raw
`close` selection, including source, observation, batch, cutoffs and selection
hash. S4 adjustment metadata describes adjusted fields in the same record and
cannot replace the explicitly selected raw close. Full-year revenue carries
S5 source/precision checks; a same-day date-only filing cannot establish
intraday availability. Carry-forward revenue is an explicit dated assumption.

Bridge terms are cash + nonoperating assets - debt - leases - preferred - NCI -
other claims. All seven have economic-value evidence or explicit evidence of
absence, dates, capture vintage, knowledge basis and nonoverlapping economic
claim IDs. Unknown claims never become zero. Shares require one homogeneous
common pool with current basic=diluted, no dilutive claims, matching action and
lease bases, cash restrictions and crossholding coverage. Unsupported evidence
produces a saved gapped result. Later capture is distinguishable from historical
knowledge by the explicit bridge capture cutoff and reviewed knowledge basis.

Immutable assumptions retain author, authorship time, retrospective classification,
dated rationales, schedule and model inputs. Edits create a parent-linked version.
The trusted-local runtime creation path rejects backdating; only the owner fixture
path can seed historical fictional assumptions. SQL validates the full fixed
shape/cross-field rules and canonical typed spelling. Canonical Decimal strings
preserve scale and signed zero; timestamps are UTC with six fractional digits.
The public run projection omits private authorship/rationale; exact assumption
reads are restricted to the app's configured trusted workspace.

The cache hashes the complete immutable manifest: S6/S4/source selection, quote,
actions/shares/claims, all dates, exclusions, assumptions, model/policy contents
and engine fingerprint. Request/execution envelope IDs do not substitute for
semantic compatibility. Payload rows are workspace-qualified; explicit reruns get
new run/input IDs and parent links even when calculation content is identical.

## W1 and API

An owner-approved synthetic review pins the expected result digest without
publishing it. A narrow W1 enqueue wrapper declares immutable intent and advances
latest-request ordering before any worker claim. The worker freezes those inputs,
verifies the engine, calculates outside transactions, and renews/checks its lease
between scenarios and individual sensitivity cells. Publication checks the exact
lease/epoch, stage, membership generation, frozen review and expected digest.

Run, payload, ordered children, conclusions, stage/execution completion, event and
latest pointer commit atomically. Children must match their canonical payload,
including inside the creation transaction; deferred checks require full rosters.
Failed newer work prevents an older completion from becoming latest. Retries
retain frozen inputs; exact saved replay verifies bytes without invoking today's
engine. Destructive downgrade with retained valuation history is refused.

`apps/api/valuation.py` is an explicit workspace-bound app factory, separate from
S6a's read-only app. Mutations create immutable assumptions or enqueue reviewed
work; no HTTP handler calculates or acquires source data. Exact reads and latest
compatible reads use read-only transactions. Poll responses expose stage/state
and a fixed safe error vocabulary, never private worker text. OpenAPI and TS are
generated and `make lint` rejects drift. The [API record](../../api-contract.md)
and [manual](../../user-manual/saved-valuations.md) describe each route.

Real company publication still requires reviewed quote rights/identity, action and
share/claim coverage, normalized financial/PIT evidence and applicable policies.
Automated WACC, Monte Carlo, valuation UI and operating providers/schedulers are
outside this checkpoint. Existing F1 history and X1 graph work is preserved.

## Corrective contract after 7c86c04

The coordinator's final audit required explicit scenario-value provenance,
economic-scope exclusion proofs and source share scaling. The
[corrective checkpoint](../../milestones/S7a-corrections.md) records that scope.
Each scenario has all 13 judgment entries, keyed by scenario and parameter.
`binding.kind` is scalar, vector, solved, schedule or solver; its value must match
the scenario or shared schedule byte-for-byte under canonical serialization.
Each entry retains unit, effective period, user_judgment origin, author and equal
set/entry authored-known times, rationale and supporting evidence hashes. An edit
must change both the scenario and its binding in a new set. SQL binds the same
values and requires the complete entry roster at transaction commit.

Every claim's coverage is a seven-component proof roster. Included/excluded/unknown
states carry explanations and evidence hashes. Only a proved own inclusion (or
proved absence) plus exclusion of all separately counted components is eligible.
Thus debt marked as including leases cannot pass merely by using different IDs.
Unknown, incomplete or unproved coverage produces a gapped saved run.

SharePool retains source_basic, source_diluted, source_unit and source_multiplier
alongside current_basic/current_diluted in canonical shares. The core verifies
exact Decimal normalization with supported multipliers 1, 1000 and 1000000; the
model consumes only matching canonical counts. Unsupported units are rejected;
missing or inconsistent evidence produces an unavailable bridge. All source
scaling and claim coverage survives in saved evidence and dependency hashes.
