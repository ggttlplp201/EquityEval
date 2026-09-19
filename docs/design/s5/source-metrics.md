# S5 first calculation slice

Status: first bounded implementation complete; full S5 remains in progress after the user's 2026-09-19 instruction
“implement the next step.” Baseline: `c1f2697`; branch `codex/s5-source-metrics`.

This slice implements pure, internal source-metric calculations and the generic
3/5/10-year comparison math already described in F1. It does not create database
schema, new normalized concepts, HTTP contracts, metric-status storage or saved
snapshots. Missing results remain `Decimal | None` with evidence-bearing flags.
D021's shared-contract and product-policy questions retain their narrower gates.

## Internal boundary

A financial operand wraps an existing selected statement/fact plus its matched
period, unit and semantic-scope records. The pure projection verifies their IDs,
source status, lineage and pinned selection policy before arithmetic. Source
precision is an explicit evidence-bearing input, never guessed from JSON digits.
No database, network or source fetching occurs in core. Existing reported values
and all provenance remain unchanged; calculations retain their exact operands.

Initial functions cover reported revenue growth for exact comparable annual or
quarterly calendar-aligned periods, gross/operating/consolidated-net margins,
CFO-minus-cash-PPE-capex FCF and FCF margin. Source-only amount outputs and
conservative eligibility failures are supported. EPS comparisons require verified
share/split basis and remain outside this first slice; TTM/YTD reconstruction,
ROA/ROE and debt composition require later eligibility work. These limits are
explicit; no supported result is fabricated from a nearby concept.

Numeric divisions require a positive denominator distinguishable from zero at
its reported precision. Exact source zero/negative denominators remain unsuitable;
unknown precision blocks the ratio while preserving the underlying amounts.
Cash-PPE purchases are a positive outflow in the accepted mapping: negative capex
raises a flag, rather than being silently made positive. FCF's distinct CFO and
capex scope IDs are retained, with their compatible consolidation and differing
payment-basis meanings checked explicitly.

Ratios use a local Decimal context with precision 50 and ROUND_HALF_EVEN,
independent of the caller's precision/rounding/traps. Monetary subtraction must
be exact in that context or returns a gap. Historical percentile interpolation
uses sufficient bounded precision to preserve all endpoint digits exactly;
rounding before comparison could otherwise misclassify identical values. Unsupported numeric magnitude
produces an explicit failure rather than infinity or a plausible rounded zero.
Every formula records its revision and exact operands. Fractions stay fractions;
no frontend arithmetic or display status is introduced here.

## Historical calculations

The history module consumes already evaluated, evidence-bearing metric samples.
It does not select old filings, prove trading-calendar coverage, or make live
prices usable. Each call supplies an explicit series/basis key and versioned
policy with a 3-, 5- or 10-year window and minimum eligible sample count. The
12/20/40 counts are tested examples, not an activated application default.

Use completed calendar quarter ends within `(as_of minus years, as_of]`.
Keep sample lineage, exclusions, missing quarter ends and the actual selected
window. Do not pad, interpolate missing financial observations, or silently
shorten a window. Linear interpolation only defines P25/P50/P75 among eligible
observations; equal P25/P75 values stay inside the middle band. No band is
available without the requested sample minimum. Insufficient evidence stays
explicit even when other source metrics can be calculated.

## Verification and next work

Behavior tests precede each numeric addition, using the supplied synthetic
examples and reviewed source fixtures. Check missingness, identity, scope, unit,
period, edition, source precision, capex signs, Decimal context and history-window
boundaries. Independent review focused on plausible but incorrect results; findings and
repairs are recorded in [review.md](review.md).

Later S5 work covers remaining metric definitions, compatible fiscal/TTM/EPS
assemblies, applicability/freshness policy and interpretation. S4b/calendar work
still gates affected price/share metrics. S6 reviews snapshot/public API and W1
publication before these functions become an automatic analysis stage. S8/U1
provide product controls and the verified user walkthrough.
