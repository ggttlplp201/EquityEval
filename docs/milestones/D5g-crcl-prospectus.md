# D5g — CRCL IPO prospectus reconciliation

Baseline `a56c3f26`; proposal `4866b16`, D045. Implementation complete; independent standards/spec reviews passed.

One governed group retained IPO 424B4 accession `0001193125-25-135795`,
`d737521d424b4.htm`, plus mandatory Facts/Submissions. Actual capture times:
2026-10-13 21:37:24.653658–21:37:25.661952 UTC; inventory observed
21:37:25.001058 UTC. All prior rows preserved. Totals: 63 captures, 65 attempts,
15 requests (13 bootstraps, two monitors), one batch, two facts, zero metrics.

The complete reported condensed Q1 statement (F-4, exact archived table locator)
provides revenue/reserve income and operating income. Entity/consolidation,
period/column, reporting USD, thousands scale and positive sign were checked.
Both selected Q1 2025 operands match the retained 2026 Q1 comparative and all
thirteen retained Facts vintages. The full annual statement's FY2024/FY2023
selected lines match the later FY2025 annual filing comparatives. Six later inline
operands are checked through the existing extractor (entity, empty dimensions,
unit, duration, scale/sign); no synthetic quarter or financial ratio is calculated.
Summary, pro-forma EPS and adjusted EBITDA are not substitutes for these operands.

The scoped accounting review covers financial statements/basis, reclassification,
restatement/non-reliance, control-risk and auditor-change passages and edition
references. No actual FY2025 correction was identified in those reviewed passages.
Prospective risk language is not a correction. The 2023 auditor change and source
assertions do not make its unretained referenced letter reviewed assurance. Exact
quotes, offsets, table/context locators and lineage are retained in the artifact.
This is a selected-line comparison, not assurance over every accounting line.

The current inventory exposes a coverage boundary: the prior 21 K/Q/8-K roster
omitted eight financial registration/prospectus records. One is now reviewed;
seven exact bodies are not. They are enumerated in the artifact and UI. No content
or irrelevance is inferred from metadata. Candidate decision remains blocked on
`registration_history_unreviewed`; metric and new batch ID remain null. Next:
separately pin the seven-body review (two governed groups of five and two, each
with mandatory inventories), then reassess all gates and current cutoff.

Prior audits and September application knowledge remain immutable. No schema/API,
real S6, provider, quote, valuation, sector or scheduler expansion occurred.
[Acquisition](../research/crcl-prospectus-acquisition-2026-10-13.json) and
[review](../research/crcl-prospectus-review-2026-10-13.json) are deterministic and
lineage-bound; the analysis UI is a checked projection with provenance drawers.

Validation passed: `make check` (1,771 tests, 505 core, 110 golden), production
build, 43 browser checks, desktop/mobile screenshots inspected, keyboard/provenance,
corrupt-artifact recovery and GET-only local requests. Archive/database preservation
and deterministic review/export replay passed. Independent staged standards/spec
reviews found no issues. Red tests preceded numeric comparison and export work;
adversarial coverage includes period/unit/sign, changed scope/hash/time, partial
acquisition, altered inventory and unsupported projection clearance.
