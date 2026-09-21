# D3b — First-source bootstrap and CRCL capture

Status: bootstrap implemented; full verification/review and live capture pending.
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
- Lint and strict Python types pass; full suites and independent review pending.

## Live capture and remaining boundary

Not attempted at this implementation checkpoint. Run only after required checks
and review. Preserve actual HTTP outcomes and record the first real capture's
source/attempt/policy identity, body hash/count and original timestamps here.
Do not promote old S1 archives by filling missing completion/request timestamps.

Successful source acquisition is not financial publication. Require genuine quote
validity, filing/non-reliance review, supported scope/period/precision and actual
PIT/core selection before eligible S5 and the minimal S6 result contract.
