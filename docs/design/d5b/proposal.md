# D5b — CRCL analysis-readiness projection

Date: 2026-10-05

Baseline: `28107eb`

Status: authorized by the owner's continuation request

## Problem

D5a publishes two exact FY2025 CRCL normalized facts, but both point-in-time
selections retain `inventory_history_incomplete` and
`event_history_incomplete`. The existing fundamentals boundary therefore
returns no usable values. A normalized amount must not be presented as an
analysis-ready input or turned into a ratio while those blockers remain.

The next application step is a read-only readiness projection that makes this
boundary visible. It lets the owner inspect what is present, what is blocked,
and what evidence is still needed before real S5/S6 publication.

## Bounded implementation

1. Export a deterministic checked artifact from the reviewed D5a snapshot and
   provenance record. Validate the exact batch and snapshot hashes, the two
   expected concepts and signed values, their source chains, the retained PIT
   flags, and `eligible_for_valuation = false`.
2. Represent the two normalized source inputs and zero published financial
   metrics. The projection may describe the operating-margin formula, but it
   must not calculate or display a result.
3. Add `/development/pilot/analysis` and link it from the pipeline Analysis
   stage and the normalization workspace.
4. Explain the remaining financial-history, applicability/profile,
   accounting-coverage, quote-identity, and real-publication-contract gates.
5. Record the generated-artifact check, UI behavior, recovery path, and manual
   verification in milestone and user documentation.

## Boundaries

- No database or application-state writes.
- No migration, schema, API, concept, status, missingness, or formula changes.
- No source fetch, provider activation, quote registration, scheduler dispatch,
  real S5/S6 snapshot, price-dependent ratio, valuation, or sector result.
- No financial arithmetic in React.
- Checked D5a artifacts remain the source of truth; the readiness view is a
  projection over them, not a second normalization or publication path.

## Acceptance criteria

- The exporter fails closed if the snapshot/provenance hash, fact roster,
  signed values, eligibility, source lineage, or retained blocking flags change.
- The checked artifact contains exactly two normalized inputs and zero
  published metrics.
- Revenue, operating income, and operating margin are shown as unavailable for
  analysis. The UI exposes the relevant blockers and never shows a numeric
  operating-margin result.
- Pipeline and normalization navigation reach the readiness view; direct load,
  refresh, keyboard use, desktop/mobile layout, and the error recovery path work.
- Reads remain GET-only and the browser performs no finance calculation.
- Focused exporter, contract, component, and browser checks pass, followed by
  the full repository gates and review.
