# Sector Explorer — internal boundary and S6 contract proposal

Status: design proposal for X1, 2026-09-19, based on
[original B048–B050](../../originals/sector-explorer/source-text.md).
No public endpoint, persistence schema, normalized concept or new stored status
is approved or implemented by this document. The user already authorized the
feature; remaining reviews concern concrete shared contracts and data rights.

## Minimal pure calculation boundary

Core consumes an immutable roster and **already evaluated** issuer snapshots.
It does not discover companies, query storage, choose sources or assert that
future common-income/capitalization data exists today. This mirrors the current
history module's explicit upstream trust boundary while retaining exact inputs.
The following names/fields describe responsibilities, not a frozen public schema.

| Internal record | Proposed fields / invariants |
| --- | --- |
| Evaluation context | `universe_id`, `universe_version`, `taxonomy_id`, `taxonomy_version`, `membership_snapshot_id`, `membership_mode`, `sector_level`, `as_of`, `captured_before`, `period_basis`, `currency`, `history_mode`, `rules_version`, `policy_version`, `input_manifest_hash`; immutable and identical across one linked graph result. |
| Roster | Explicit complete/partial state, independent membership evidence and tuple of issuer memberships; keep members whose metrics are unavailable. Empty sector definitions also remain in the declared taxonomy list. |
| Membership | `issuer_id`, sector/industry assignment or unclassified, `effective_from`, `effective_to`, `known_at`, source references, membership revision; issuer identity rather than listing/ticker is the aggregation unit. |
| Evaluated company input | `issuer_id`, immutable constituent snapshot ID, profile/applicability policy, financial period/basis/currency, source-evaluation context, current common cap and prior comparison-date common cap, common earnings, current/prior revenue, operating income, FCF, existing corresponding company ratios/growth and their exact input/formula references. Every absent field remains None with reasons. |
| Amount/metric evidence | Decimal value or None, unit, period/as-of, scope/basis, absolute-error evidence where needed, flags, frozen input IDs/hash, source snapshot references and formula revision. Core validates supplied finite values/identity/comparability; it does not independently prove database foreign keys or source truth. |
| Explicit comparison policy | Minimum V, minimum K/N, minimum contributing/full cap, precision/range rules, tie-breaking rule, version; proposed fixture gates are 10, 0.70, 0.80. No ambient defaults or wall-clock aging. |
| Sector result | Exact context, metric/method, Decimal/None, numerator/denominator totals, N/K/V, coverage values, meaningful-company count, eligible and excluded issuer records, cohort ID, period/quote dates, distribution values/percentiles, reasons and gate result. No browser arithmetic. |

Keep scalar amount and company-ratio lineage together: an externally supplied
ratio cannot silently refer to a different cap, earnings period or accounting
basis. Prefer existing fundamental Calculation/period outputs as references where
available. A new internal projection is not permission to add an unchecked
production JSON blob or weaken shared source types.

Deduplicate exact repeated issuer evidence once. Conflicting snapshots or
assignments for one issuer must surface a conflict and exclude its contribution,
not select the first/last row or count two listings. Preserve the issuer in N.
Do not drop a conflict before determining full capitalization: its cap remains
unknown unless a separate unambiguous complete issuer-cap record establishes it.

## Calculation invariants

Use one method-independent eligible-input assessment per metric. K requires
complete, fresh, applicable, comparable metric inputs and required precision;
known losses/zero denominators are complete observations. V derives from that
assessment and the selected method. Keep negative earnings in aggregate P/E but
exclude them from profitable-company medians/means. Keep negative margin values.
Growth excludes nonpositive prior bases from its matched contributing cohort,
while disclosing them separately. Every numerator/denominator uses the same IDs.

N includes unsupported profiles and unavailable company snapshots. Never shrink
the roster to obtain favorable coverage. K/N is None for an empty roster.
Full roster capitalization is a separate completeness determination across all
N issuers, irrespective of metric eligibility. Unknown full cap makes cap coverage
and current concentration unavailable. No division by known-subset cap. Aggregate
losses count in K and V, even if sum earnings makes the final ratio N/M.

Amount precision propagates through sums and period construction; near-zero
aggregate denominators require the same source-supported guard as fundamentals.
Do not confuse a mathematically positive rounded denominator with distinguishable
positive earnings. Return exact totals and failure reasons without NaN/infinity,
zero substitution or a display cap. Division precision must not vary with caller
Decimal context. Median/P25/P75 retain exact eligible company values; simple mean
uses the same eligible ratio set and carries its own sample/outlier label.

Market reference evaluates the full declared issuer roster once with the same
metric/method/applicability. It never averages sector results. Include excluded
profiles and label it Market reference — eligible companies where applicable.
Unclassified issuers belong to this roster and its benchmark.

For growth, current-date membership establishes the candidate cohort; match
current and prior TTM facts before any summation. Record exclusions and both
financial-date ranges. Top-five exclusion uses prior-date cap rankings over that
same declared membership. Unknown required rankings disable the comparison.
Freeze the selected five across both periods; do not select current leaders for
one period and prior leaders for the other. Current-date concentration is a
separate ratio with its own date, full-cap requirement and constituent IDs.

Profiles apply per metric, not by discarding a whole sector: bank P/E may be
supported while generic operating/FCF comparisons are not. A mixed Financials
sector retains unsupported members, reports their exclusion reasons and its true
coverage. An internal caller-supplied profile flag is trusted policy evidence,
not a generalized profile classifier or newly approved production definition.

## History and linked snapshots

Historical-sector mode uses membership effective at each observation and known
by its permitted information cutoff, with company filings and prices selected
under that observation's own date/capture policy. Later delistings, filing
revisions or reclassifications produce new snapshots; old snapshots stay intact.
A date-only publication cannot become a fabricated instant. Filing-date
reconstruction from later archives remains distinguishable from strict
workspace-as-known history.

If that membership evidence is absent, Current members’ history is an explicit
separate mode. It can plot eligible reconstructed company data but cannot make
historical-sector percentile claims. Mode, sector level, metric, aggregation,
taxonomy/universe versions, currency/basis and policies enter series identity.
Coverage or roster comparability failures produce gaps; do not interpolate
missing financial observations. A 3-year historical interpretation needs 12
eligible quarter ends and the source's coverage gates. Equality to P25/P75 remains
inside the middle range, reusing existing exact history math.

Controls select one full result manifest for every graph, table and tooltip.
Selection should atomically switch the result identity rather than leave bars,
benchmarks, history and scatter on different methods. Failure keeps a prior dated
result visible separately, never relabelled as the new selection. Company drilldown
must carry its constituent snapshot ID rather than navigate to mutable latest.

## Proposed S6 records for sequential review

These mirror the document's explicit fields and identify additional identity/time
requirements from current contracts. Keep existing typed source references,
including composite market evidence keys; strings below are descriptive names,
not an instruction to replace typed foreign keys with unchecked references.

| Proposed record | Exact source fields | Review additions / invariants |
| --- | --- | --- |
| `SectorSnapshot` | `id`, `universeId/version`, `taxonomyId/version`, `membershipMode`, `membershipSnapshotId`, `sectorLevel`, `asOf`, `capturedBefore`, `period`, `currency`, `metricMethod`, `rulesVersion`, `policyVersion`, `constituentSnapshotIds[]`, `metrics[]` | Immutable result/execution identity; explicit financial history mode and filing/source-known cutoffs; frozen evaluation time, complete/partial roster state, input manifest/hash, metric/applicability/precision/coverage/selection versions and generated time. Arrays have typed identities, unique issuer membership and canonical ordering. |
| `SectorMetric` | `metricId`, `method`, `value|null`, `numeratorTotal|null`, `denominatorTotal|null`, `status/reasons`, `N/K/V`, `meaningfulCompanyCount`, `issuerCoverage`, `capCoverage|null`, `excludedByReason`, `median/p25/p75`, `financialDateRange`, `quoteDate`, `cohortId`, `benchmarkRef` | Decimal strings and explicit units/fractions; precise K/V definitions and exclusive primary reasons versus overlapping diagnostic flags; selected method and sample counts on distribution summaries; full cap completeness, gate outcome, small-sample/partial-roster labels; quote-date range when no single common date exists; no invented latest quote date. Status projection preserves underlying None/flags. |
| Membership and lineage | `issuerId`, taxonomy code, `effectiveFrom/to`, `knownAt`, `sourceRef`, issuer snapshot ID, included/excluded reason | Source/taxonomy grants, stable provider identity/version, assignment revisions, captured/known limits, effective half-open ranges, unclassified/conflict states and typed evidence keys. No inference from ticker or SIC-to-GICS conversion. |
| Universe / taxonomy definition | Implicit in `universeId/version`, `taxonomyId/version` | Independent dated roster manifest, operating-equity eligibility rule, issuer/security deduplication and capitalization coverage policy; declared sector/industry list, licensed source scope and immutable content hash. No database shape is committed here. |

Proposed endpoint: `GET /sectors/metrics` with pinned universe, taxonomy, date,
period, currency, membership mode and method; a separate immutable snapshot-ID
retrieval is required. Exact path/query/response/error designs remain S6 review,
not an implemented route. Generate OpenAPI and TypeScript together after review.
No API math or frontend ratio reconstruction.

Cache identity must include all selection/context fields above, exact input
manifests, membership/constituent snapshots and methodology/policy versions.
Source or membership revisions produce a new result, not mutation. Distinguish
reusable pure calculation payloads from new explicit W1 executions/snapshots;
retries within one logical request still publish at most once. Freeze evaluated
freshness rather than re-age an old saved snapshot when opening it.

## Development view versus production readiness

A development-only chart view may render precomputed fictional snapshots from
the tested core, including source-shaped fixture references and explicit missing
states. Mark the universe/companies/data as fictional in the visible header and
provenance; never attach real filing links as evidence for invented amounts.
A simulated evidence drawer is not production source integration. Production
starts empty until approved membership/classification, compatible company
snapshots, price/capitalization evidence and the reviewed S6 contract exist.

Do not claim the development view passes source B054 immutable storage or B055
API matching merely because fixtures are frozen. It can verify pure results,
cohort/gate rules, graph values and accessibility. Final acceptance also requires
real-source universe integrity, durable immutable retrieval, exact snapshot
company navigation and failed refresh/loading behavior against the public API.

Major silent-error risks to review independently: loss removal from aggregate
P/E; mismatched aggregate cohorts; double-counted share classes; common-income
substitution; unknown cap denominator replaced by known-subset cap; profile
exclusions removed from N; current membership used as historical membership;
prior/current top-five changes; different methods mixed across linked charts;
and high-precision or near-zero denominators yielding plausible false ratios.
