# S1 — SEC concept reconnaissance

Status: in progress — SEC contact configuration pending
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: codex/s1-sec-recon
Dependency: S0, tag milestone/s0, commit 33d800d
Sources: BUILD_GUIDE Part 5 S1; SPEC 2.1, 3.2, 12.1 and 12.5.

## Scope

Documentation and source reconnaissance only. Propose approximately 40 core
financial concepts, inspect eight diverse companies, identify exceptions and
prepare a formal restatement example for S2. No production ingestion, enum,
financial calculations, schema definitions or API contracts are implemented.

## Artifacts

- docs/research/s1/README.md — scope and evidence status
- docs/research/s1/cohort.md — selected companies and anchor filings
- docs/research/s1/concept-candidates.md — 40 preliminary concept definitions
- docs/research/s1/source-boundaries.md — verified API limits and data-access implications
- docs/research/s1/restatement-khc.md — verified original/revised filing evidence
- Exact tag mappings and company coverage remain pending payload inspection.

## Decisions and review

The concept vocabulary and overrides remain proposals until user review. A real
contact User-Agent is required before direct SEC data access. No contact has
been inferred from unrelated account or Git configuration.

## Findings so far

Official SEC documentation limits Company Facts to standard-taxonomy facts
applying to the entire filing entity. The original spec overstates extension
and segment coverage. Record raw-filing requirements explicitly at the S1 gate.

## Validation evidence

Public SEC documentation and original/revised KHC filing evidence have been
reviewed. The catalogue contains 40 numbered proposals and the cohort contains
eight companies with primary filing locators. Company Facts payloads have not
yet been fetched; no observed-tag coverage matrix or golden fixture is claimed.
This is an interim documentation checkpoint, not S1 completion.

## Handoff

Complete the evidence-backed concept proposal and present the S1 review packet
before creating the concept enum or schema in S2.
