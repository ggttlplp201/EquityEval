# D5c — CRCL operating-fundamentals safety review

Date: 2026-10-12. Baseline: `efa92ff`. D041 records the owner's explicit
continuation and request for Astra 6 to prove whether data is safe for analysis.
Commit this proposal before source/application mutation or implementation.

## Decision and exact boundary

Review the FY2025 consolidated reported revenue/reserve-income and operating-loss
pair already normalized by D5a. The target financial period is 2025-01-01 through
2025-12-31. Review filing/event inventory over 2025-01-01 through 2026-09-21,
using the pinned D3c Submissions body and its actual September retrieval times.
The UI and tests must separate historical application-knowledge coverage from
retrospective content consistency. A genuinely current eligibility judgment needs
fresh Submissions coverage through its new cutoff and a later batch. The profile
is reviewed/known in October; do not backdate it.
This is a retrospective, bounded review, not current October analysis. A new
retrieval retains its actual timestamp and never satisfies the September cutoff.

Replay the accepted SEC parser and D5a normalization/cross-check; enumerate every
10-K, 10-K/A, 10-Q, 10-Q/A, 8-K, 8-K/A, NT 10-K and NT 10-Q in that window.
The saved inventory has no advertised older Submissions files. Its advertised
inventory completeness does not prove complete financial/event coverage.
The roster is 19 filings: 6 periodic filings and 13 event filings. Three periodic
bodies are retained by D3c. The remaining primary-document accessions are:

- 0001876042-26-000267, 0001876042-26-000246, 0001876042-26-000205,
  0001876042-26-000192, 0001876042-26-000159, 0001876042-26-000150,
  0001876042-26-000148, 0001876042-26-000078, 0001876042-26-000032;
- 0001876042-25-000047, 0001876042-25-000045, 0001876042-25-000014,
  0001628280-25-039781, 0001628280-25-039749, 0001876042-25-000004,
  0000950103-25-007107.

Validate the roster and filenames against pinned metadata before dispatch. A
bounded acquisition may reuse existing governed source-bootstrap leases,
transport/archive/policy/limiter and source registration, with groups of at most
five filing documents plus required Company Facts/Submissions. Do not change the
bootstrap contract or infer completeness from a successful HTTP response. Stop
on unavailable runtime, policy, source, lease or network prerequisites; retain an
honest blocked review. Fresh Submissions may reveal additional necessary history;
record that gap rather than silently expanding scope. Exhibits and earlier IPO
registration evidence needed for a conclusion must also remain explicit gaps
unless already retained and actually reviewed. No unattended acquisition.

## Safety and applicability

The two values must agree across Company Facts and the original 10-K in issuer,
consolidated scope, annual duration, USD, sign, scale, decimals and accession.
Review the annual amendment's explanatory note rather than equating amendment
with restatement. Events require substantive non-reliance, auditor/change,
correction/restatement and financial-exhibit review; absence of Item 4.02 in
metadata is not proof of no restatement. Preserve uncertain or missing coverage.

Create an evidence-linked narrow CRCL profile: reserve-interest revenue,
distribution/transaction costs and interest-rate/circulation sensitivity make
reported operating margin descriptive, with explicit comparability limitations.
Do not apply generic technology thresholds, normalize away reported expenses,
claim sustainability, or treat stablecoin reserve assets as corporate excess cash.
Broader metrics need separate reviewed accounting inputs and applicable policies.

## Implementation and acceptance

Add a deterministic, hash-checked safety artifact and interactive extension of
`/development/pilot/analysis`: coverage window, individual filings, source/evidence
links, tests/checks, applicable interpretation and unresolved blockers. Each
financial amount retains its D5a provenance drawer. No frontend financial math.
The immutable D5a/D5b reviews and earlier captures/migrations remain unchanged.
New saved safety evidence may supplement their status without rewriting history.

Write adversarial tests first for changed/missing evidence, incomplete inventory,
wrong cutoff, false completeness, mismatched periods/units/editions and numeric
publication. Keep all real metric values null until source/history, applicability,
accounting and real S6 publication prerequisites pass. The existing S6 approval is
synthetic-only; stop before schema/API/concept/missingness changes and record the
real publication gate. A verified blocked result is a valid milestone outcome.

Run focused checks, full `make check`, production build and local browser checks
for provenance, expanded evidence, keyboard, desktop/mobile, corruption recovery
and GET-only requests. Obtain independent staged standards/spec review. Update
milestone, decision, roadmap, manual and handoff; commit with hooks and leave the
preview on port 3101. No providers, quote inference, price metrics, sector output,
valuation, deployment, migration or scheduler activation.
