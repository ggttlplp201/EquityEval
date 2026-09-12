# S1 — SEC concept reconnaissance

Status: accepted for S2 — user directed progression on 2026-09-12
Completed research: 2026-09-12 (Asia/Shanghai)
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: codex/s1-sec-recon
Dependency: S0, tag milestone/s0, commit 33d800d
Review checkpoint: local Git tag milestone/s1-review (created with the final packet)
Interim checkpoint: bfbb000 (before direct payload inspection)
Sources: BUILD_GUIDE Part 5 S1; SPEC 2.1, 3.2, 12.1 and 12.5.

## Outcome

Eight diverse companies inspected; 40 proposed concepts documented with exact
candidate tags, unit/period/accession observations and company-specific exceptions.
Original-filing evidence confirms missing custom/dimensional coverage and scope
collisions. KHC's formal original/revised income pair is verified in raw API rows.
No production ingestion, enum, financial schema, math or API implementation.

## Review artifacts

Start with [the review brief](../research/s1/review-brief.md). The
[packet index](../research/s1/README.md) links the concept map, 40×8 coverage
matrix, company notes, source limits and archived evidence.

The user's additional US macro/watchlist monitoring requirement is recorded in
[N1](../features/N1-news-and-macro-agent.md): in-app, desktop and email alerts.
This authorized extension enters shared-contract planning; alerts are not live.

## Verification

- Eight Company Facts body checksums and sizes match their manifests.
- Eight complete original-document body checksums and sizes match. One TSM
  interrupted response was recorded; the retry completed and is independently hashed.
- Every exact observation in all 320 concept/company groups matches its archived
  source tag/unit/row and pinned accession/period; scope suitability remains reviewed separately.
- Five manually specified filing-to-API checks agree, preserving original literal,
  scale, context, period and unit. Full normalized golden fixtures remain S3 work.
- KHC parent net income, USD, 2017-01-01 through 2017-12-30:
  10,999,000,000 at the 2018 filing; 10,941,000,000 at the 2019 restated filing.
- Contact configuration is local, ignored by Git and excluded from research files.
- Required lint, typecheck and full/core/golden harness checks run at the checkpoint
  through the commit hook. Business suites remain explicitly empty; no financial
  behavior tests, live database tests or hosted CI success are claimed.

## Limits and unresolved decisions

The starting vocabulary and conservative source direction were accepted for S2;
this is not blanket approval of every future mapping or schema decision. TSM FY2025 financial API
coverage is missing; FY2024 examples are labelled secondary. Some reported
subtotals include different expense, lease or share scopes. Complete current-debt
and D&A mappings are not guaranteed by this catalogue. These gaps cannot be
filled with component guesses. See D007, D011 and D012 for review boundaries.

Docker runtime verification remains the S0 environment limitation. Direct data
access was briefly interrupted by account limits, then resumed successfully;
all evidence listed as complete is saved locally.

## Handoff

S1 review direction accepted; continue with the S2 schema/vocabulary design. S2 must present
its own concrete schema and point-in-time policy before implementation, including
N1 event/revision/delivery needs. Write the KHC regression first when numerical
storage/query behavior is implemented. Preserve all raw evidence and originals.
