# S4 — Prices and macro sources

Status: concrete source/schema review prepared; implementation pending D019
Date: 2026-09-12 (Asia/Shanghai)
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: codex/s4-source-contract
Dependency: S3 `b71e308`, tag `milestone/s3`
Review checkpoint: `milestone/s4-contract-review` (created after verification)

## Scope and authorization

The user directed progression with “continue” after S3. This work prepares the
next concrete review, source research and preimplementation acceptance cases.
The adopted project instructions require sequential review before new schema
shape or missingness semantics are decided; the earlier “implement” approved the
presented S3 contract, not these subsequently proposed S4 tables. Original ZIP
documents remain unchanged.

The proposed S4a scope is daily price fields, native macro observations, typed
provenance, independent source/capture vintages and W1 price/macro stages.
S4b must separately resolve corporate-action/ADS relationship correction history.
No S4 tables, production adapters or policy activations have been implemented.

## Artifacts and findings

- [Decision brief and S4-01–04 contract](../design/s4/source-contract.md).
- [Eight-table storage proposal](../design/s4/storage-review.md), including
  explicit rights gates, units, missingness, atomic publication and Timescale.
- [Tiingo research](../design/s4/tiingo-research.md) and
  [FRED/direct-source research](../design/s4/fred-research.md).
- [Test plan](../design/s4/test-plan.md) and fictional
  [price](../../tests/fixtures/s4/price-cases.json) /
  [macro](../../tests/fixtures/s4/macro-cases.json) acceptance cases.
- [Actual H.15 research manifest](../research/s4/evidence/frb-h15-manifest.json):
  one complete ZIP response, all five CRC/hash-verified members, full safe parse
  of the data XML, separately refused DOCTYPE metadata parsing. The initial
  64 MiB decoded cap was exceeded; the reviewed 128 MiB cap verified the same ZIP
  without another download. No application normalization or W1 run was created.

Current Tiingo and FRED terms do not establish compatible permanent storage for
this application. No key is configured for either provider, and neither was called.
The direct H.15 format was validated for exact Treasury/fed-funds identities,
native percent-per-year units, literal multiplier semantics and explicit missing
status/sentinel. It does not expose historical release vintages or a verified
seasonal flag. The full ZIP also contains legacy Moody's data outside the blanket
Board reuse grant: raw scope remains unresolved. The complete ZIP is quarantined
in ignored local research storage, not committed or offered as a public fixture.
Filtering normalized output is insufficient to approve its raw retention.

The subsequent direct Treasury review established official CC0 catalog linkage
to the current nominal-yield feed. The first bounded research response was not
saved because the research validator rejected an unreviewed optional property;
its attempt record makes that limitation explicit. A separately authorized
replacement request preserved the complete 13,033-byte response before semantic
checks. Its hash and safe parse were verified, with eight entries and exact
two-/ten-year field identities. This is the recommended initial yield source,
still requiring policy provisioning and production adapter tests after review.
Current absent-field missingness is documented but not present in this capture;
no historical release-vintage or full-yield-field normalization is claimed.
See the [Treasury manifest](../research/s4/evidence/treasury-yield-manifest.json).

D019/S4-01–04 are **proposed**. D009's macro selection policy is proposed; ERP/beta
remains open for S7. No API, vocabulary or new table is silently approved.

## Validation evidence

The review checks synthetic JSON syntax, explicit fictional labels, split
arithmetic (100 to 50; volume 1000 to 2000), percentage conversion (4.25 to 0.0425),
inclusive vintage boundaries and capture-cutoff expectations. These are review
calculations, not passing production S4 adapter tests.

The independent storage review checks for plausible wrong values and policy
bypasses: adjusted-history coherence, provider-symbol reuse, explicit missing
status, dividend currency, full raw-body versus normalized scope, source
activation/replay, date precision and real Timescale acceptance. `make check` passes: **440 tests**, Ruff/import policy, concept generation,
ESLint, strict mypy and TypeScript. The separate golden run passes **108 tests**.
The core suite remains intentionally empty until S5/S7; no S4 executable adapter
tests or Timescale acceptance are claimed. The mandatory pre-commit hook repeats
these checks before the checkpoint is recorded and is not bypassed.

Review-time validation confirms fictional JSON labels, the hand calculations and
vintage/capture selections, all current local review links, the quarantined H.15
body hash/count and member-size totals. The Treasury body hash/count, eight
selected-date rows and exact field values agree with its manifest.
The raw Treasury XML retains its original trailing whitespace; a capture-specific
Git attribute prevents line-ending rewriting and excludes that source whitespace
from the code-style check. `git diff --check` passes.

## Limitations and next handoff

After review, implement the accepted additive schema sequentially and write
numeric behavior tests before normalization. Provider code can be exercised with
fictional fixtures while live rights remain unresolved. A real pinned Timescale
runtime is required for full S4 acceptance; existing plain PG16 tests cannot
establish hypertable correctness. No new machine package was installed here.

No account, subscription, provider contact, live worker, recurring monitor, email
or desktop delivery was activated. S5–S8, W1's full analysis/UI, N1's continuous
US macro and stock-specific discovery/assessments across all three alert channels,
and U1's finished manual/glossary remain required for release.
