# S7a corrective checkpoint — assumption bindings, claim scope and share units

Status: implementation and independent corrective reviews complete; the final
checkpoint is created only after the required commit hook succeeds. Coordinator audit of `7c86c04` requested these three corrections before
milestone approval. Preserve that commit and `milestone/s7a-synthetic-valuation`;
this correction receives a new commit and `milestone/s7a-synthetic-valuation-corrected`.
Scope remains synthetic-only. No UI, provider, application-store or service change.

## Corrections

1. **P1 assumption value/provenance binding.** One immutable entry per scenario
   and each of the 13 parameter groups. Discriminated bindings carry the exact
   scalar, annual vector, solved-variable marker, schedule or full solver policy.
   Each entry includes unit, effective period, explicit user-judgment origin,
   author/authored/known times, rationale and supporting hashes. Values must match
   their named scenario exactly; immutable entry authorship/known time matches
   the current-authored set. SQL validates the same binding and complete roster;
   child primary keys include scenario and parameter. Private entry content is
   omitted from public run projections.
2. **P1 bridge overlap proof.** Each claim carries all seven economic components,
   explicit included/excluded/unknown disposition, explanation and evidence hash.
   An eligible amount includes its own component and excludes the other six;
   evidenced absence excludes all seven. Missing/duplicate components, unknown
   scope, missing evidence or an included separately counted component make the
   entire bridge unavailable. Distinct arbitrary claim IDs are not exclusion proof.
3. **P2 N17 source share scaling.** Source basic/diluted counts and source unit are
   separate from canonical share counts. Supported multipliers are exactly 1 for
   shares, 1,000 for thousand_shares and 1,000,000 for million_shares. Pure Decimal
   core normalization must agree with both canonical counts before any market
   target. Wrong or missing units/multipliers and inconsistent normalization are
   rejected or unavailable. Fraction rates and currency checks remain explicit;
   no percentage or FX conversion is added.

## Storage and compatibility

The corrective commit updates synthetic migration 0012, which has not been
applied to the application store. Migrations 0001–0011 remain byte-identical.
Earlier code and synthetic contract remain reproducible from the original commit
and tag. No existing application financial records are rewritten. Disposable
migration round-trip tests cover the corrected 0012 schema and complete-entry
constraints. This is not an upgrade path for a deployed old 0012 database.

Pydantic, fixed SQL schemas/cross-field validation, canonical serialization and
generated OpenAPI/TypeScript change together. Review caught the new OpenAPI
`oneOf` becoming `unknown` in TypeScript; a red regression preceded the generator
fix. All five binding alternatives now retain their discriminant and typed value.

## Review and verification

Three targeted acceptance regressions failed before implementation, proving the
original stale-value, unproved claim scope and unproved share-scale gaps.
Independent numerical review found no remaining arithmetic, overlap or scaling
issue; standards review identified the generated-union gap above, now repaired.

Evidence files under ignored `var/`: `s7-correction-red.log`,
`s7-correction-types-red.log`, `s7-correction-verification.log`,
`s7-correction-static.log`, `s7-correction-build.log` and
`s7-correction-commit-checks.log`. The final tag annotation records actual required
full/core/golden counts and clean checkpoint identity after the commit hook passes.

Tests cover equivalent share economics (10 shares = .01 thousand = .00001 million),
wrong raw/canonical counts and multipliers, debt already including leases,
unknown/missing/duplicate scope proofs, stale scalar/vector/fade/scenario binding,
wrong authorship/origin, private projection, SQL bypass attempts, incomplete
creation transactions, immutable entries, gapped publication and migration gates.

[Manual](../user-manual/saved-valuations.md) ·
[Original milestone](S6b-S7a-valuation-contract.md) ·
[Spec review](../design/s7/review.md)

## Verification before checkpoint

- Focused valuation/API/persistence/migration/generation checks: **160 passed**.
- Lint and generated no-diff: passed. Python types: 89 source files passed;
  schema/web TypeScript checks passed.
- Production web build: passed.
- Independent numerical and standards corrective reviews: no outstanding
  actionable finding after the typed-union regression and fix.
- Full/core/golden gate: required unbypassed commit hook; final actual counts are
  retained in the corrective tag annotation and `var/s7-correction-commit-checks.log`.
  The validated strict editable package path is used for subprocess imports.

Coordinator milestone approval remains distinct from this implementation checkpoint.
The original `7c86c04` commit and tag remain unchanged and auditable.

The first full corrective hook run had 1,602 passes and one existing SEC transport
failure: its short-lived rate-limit permit expired before dispatch, so the request
was correctly declined. The unchanged eight-test transport suite then passed in
isolation. No transport behavior, permit safeguard or test was weakened. The first
report is retained as `var/s7-correction-commit-first.log`; the final required hook
reruns all suites and records completion in the checkpoint annotation.
