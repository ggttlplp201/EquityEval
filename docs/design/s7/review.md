# S6b/S7a independent implementation review

Reviewed working implementation against proposal checkpoint `5b85140` on
2026-09-22. Independent read-only reviewers: `s7_numeric_review` (numerical/spec)
and `s7_standards_review` (contracts, persistence and privacy). Numeric tests
preceded the evaluator/solver. Audit regression failures were reproduced before
repairs; logs are local ignored artifacts under `var/`.

| Finding | Repair and retained regression |
| --- | --- |
| Same-day date-only anchor could appear known intraday | Check the actual selected fact's filed date; reject unproved same-day availability. |
| Bridge capture and historical knowledge were underspecified | Explicit capture cutoff and claim/share knowledge basis; unavailable when unproved or outside cutoff. |
| Conditional and reverse sensitivity cells omitted signed PV/equity diagnostics | Both now retain full evaluations and applicable reasons. Reverse repricing preserves changed axes; 2×2 grid regression checks the fixed market target. |
| Margin tax kinks were not explicitly partitioned | Exact boundaries or outward rational bands with preserved unresolved coverage. |
| Boundary/tangency/continuum capability claims needed limits | Tests retain honest inconclusive states; implementation/manual explain the limits. |
| Direct runtime SQL accepted malformed assumption content | Fixed shape and cross-field validator; nested extra/unit/slot regressions. |
| SQL accepted typed strings that changed on reconstruction | Exact UTC microsecond and Decimal canonical spellings; hour-24, missing fraction and exponent spelling regressions. |
| Owner could append invented result children during creation transaction | Exact payload/ordinal/name/state binding and deferred complete-roster checks. |
| Request polling omitted safe stage/failure information | Explicit projection with fixed safe error codes; private details excluded and workspace isolation tested. |
| Worker checked lease only between whole grids | Lease/cancellation checks between each cell; cancellation after first cell publishes no run. |

Final numerical review: all actionable findings resolved; no remaining formula,
bridge-sign, domain-coverage or false-certification issue found within synthetic
scope. Final standards review found no remaining functional issue; its caveat
about nested SQL tests passing for noncanonical timestamps was corrected by
canonicalizing the valid baseline before introducing each nested defect.

S4 adjusted-field metadata was investigated and is not a raw-price bug: the exact
selector is `close`, its complete selection digest is checked, and adjusted close
cannot be substituted. No migration 0001–0011 changes were made. Production
providers, application publication, automatic services and valuation UI remain
outside this review. See the [milestone](../../milestones/S6b-S7a-valuation-contract.md)
for final full-suite, generation, build and checkpoint evidence.

## Coordinator audit correction after 7c86c04

The coordinator identified three missed contract requirements: scenario-specific
value binding in assumption entries, inclusion/exclusion proof for bridge scope,
and N17 share-count unit scaling. The original independent review clearance did
not establish those requirements. They are repaired in the separate
[corrective checkpoint](../../milestones/S7a-corrections.md), preserving the old
commit and tag for audit.

New numerical review independently checked share-scale equivalence, rejected
wrong multipliers/counts, rejected included or unknown debt/lease overlap and
stale scalar/vector/solver bindings. Standards review confirmed SQL shape parity,
complete immutable rows and protected private authorship. It found a generated
TypeScript oneOf omission; a regression failed before the generator was repaired.
The full five-way typed binding union is now preserved. Final evidence and exact
test counts belong to the corrective checkpoint tag and commit-hook log.
