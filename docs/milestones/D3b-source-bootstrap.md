# D3b — First-source bootstrap and CRCL capture

Status: capture-only implementation and genuine CRCL capture verified; financial publication remains open.
Date: 2026-09-21.
Branch: `codex/source-bootstrap`.
Baseline: `c314df9` / `milestone/d3a-application-runtime`.
Recovery target: `milestone/d3b-source-bootstrap`.
Dependencies: accepted D031, S2/W1/S3 invariants, separate application PG/Redis.

## Authorized scope

The user explicitly approved the concrete first-capture extension, followed by
actual CRCL capture if identifying contact and approved source settings are
available. Preserve ordinary requests, source provenance, financial missingness,
the redesigned screens and all seven companies. No DCF or other live provider.

## Artifacts

- New migration 0006, narrow bootstrap enqueue and explicit/specific claim helper.
- Existing shared SEC fetch/inventory path with a capture-only bootstrap branch.
- Database stage/resource guards; ordinary, combined and market worker exclusions.
- Immutable source manifest with NULL quote and no claimed financial result.
- Explicit CRCL registration/capture CLI using existing application configuration.
- [Implementation and operator guide](../design/s3/identity-bootstrap.md),
  [approved proposal](../design/s3/identity-bootstrap-proposal.md),
  [scoped source review](../research/sec-application-policy-2026-09-21.md).

## Validation and review

- Focused bootstrap/workflow/migration/source/market regression pass: 70 tests.
- Expanded tests include specific claiming, HTTP failure, cancelled finalization,
  retry exhaustion, source-policy hash mismatch and genuine empty-database setup.
- Application readiness inspection: configured SEC contact is valid; separate PG
  and persistent Redis verified. No secret printed; no application registration
  or live request at this preflight checkpoint.
- Checkpoint `de0aefa` / `milestone/d3b-source-bootstrap`: lint, Python/TypeScript
  types, 1,017 full tests, 225 core and 110 golden passed in the mandatory hook.
- Standards and Spec reviews both found no actionable findings; see
  [review record](../design/s3/bootstrap-review.md).
- Live SEC inventory revealed renderer subdirectories in primaryDocument. The
  bounded metadata parser correction passes 25 inventory tests and both review
  axes; transport filename permissions remain unchanged.

## Live capture and remaining boundary

Application migration 0006 and reviewed owner registration succeeded. Request
`954c15d5-d14b-471d-8e87-f1e82978f9a1` captured genuine Company Facts and Submissions
(HTTP 200) through S3, then failed at inventory parsing. The request and its two
captures remain immutable. Replaying the saved inventory after the parser fix
produces 421 records (393 within the requested window), complete advertised
coverage, and no inventory flags. No network was used for this parsing replay.

The inventory identifies annual amendment `0001876042-26-000228`, filed 2026-07-13,
primary document `crcl-20251231.htm`. Its metadata comes from capture
`e51439cd-a222-4dd8-9861-b21406eb7693`. The next bounded capture plan includes that
SEC-hosted amendment for substantive review alongside the original and Q2 filing.
An amendment alone does not establish financial restatement or non-reliance.
No quote, normalization batch or financial result has been created.

Successful source acquisition is not financial publication. Require genuine quote
validity, filing/non-reliance review, supported scope/period/precision and actual
PIT/core selection before eligible S5 and the minimal S6 result contract.


## Completed capture checkpoint

Parser recovery `ec7f3f7` / `milestone/d3b-inventory-parser` passed 1,033 full,
225 core and 110 golden tests plus lint/types. The subsequent bounded request
completed all five HTTP200 captures, including the discovered amendment.
[Capture audit and evidence review](../research/crcl-first-application-capture-2026-09-21.md)
records source identities, hashes, original timestamps, metadata replay, amendment
scope, genuine listing-date evidence, remaining statement issues and next gates.
No secret or old timestamp placeholder was published. Terminal-key reuse produced
no new dispatch. Source-only recovery is tagged `milestone/d3b-crcl-capture`.

D3b acquisition is complete. Normal quote registration and financial publication
remain pending their explicit evidence review; then continue PIT → eligible S5 →
reviewed minimal S6. The fresh capture does not itself update the D2 UI artifact.
