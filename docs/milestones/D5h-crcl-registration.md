# D5h — CRCL registration history reconciliation

Baseline `66d34f02`; proposal `01348a5`, D046. Implementation complete; independent standards/spec reviews passed.

Two governed BootstrapPlan groups retained the seven exact D5g registration and
prospectus bodies (five plus two), each with mandatory Company Facts/Submissions.
Eleven HTTP-200 captures were retained once, with all prior rows preserved.
Totals: 74 captures, 76 attempts, 17 requests (15 bootstraps, two monitors), one
historical normalization batch, two facts and zero published metrics.

The immutable acquisition summary incorrectly says incomplete because its wrapper
counted one group. The deterministic review independently validates both typed
completed groups, exact resource/capture identities and preservation; it does not
rewrite the original audit or repeat acquisition. Future wrapper counts are fixed.

All seven full bodies were scanned for accounting/correction passages. Complete
financial statements, accounting bases, reclassifications, auditor changes and
control disclosures were reviewed for the selected income lines. The April S-1
and S-1/A contain an unfilled preliminary Q1 table: it supplies no reported Q1
operand. Three May/June S-1/A editions contain the reported Q1 pair. Two August
bodies contain Q2/H1 statements; Q1 is not derived by subtraction. All seven
annual tables agree on the selected FY2024/FY2023 lines. No FY2025 annual
statement is invented in a 2025 registration document.

Eighteen exact periodic operands from four retained filings reconcile, with
entity/context, duration, reporting USD, thousands scale, sign and edition checks.
All fifteen retained Company Facts vintages agree on the tested Q1 pair, retaining
their later-filing attribution. Prior D5d–g reviews remain pinned and replayed.
No actual selected-line correction or non-reliance notice was identified in the
reviewed accounting passages. Conditional restatement risk, corporate-document
restatements, equity/tax/OCI reclassifications and generic no-impact language are
not treated as independent proof of selected-line consistency. Direct statement
comparisons supply that evidence. Auditor opinions do not prove internal controls;
referenced unretained auditor letters are not represented as reviewed assurance.
This is not certification of every accounting line, SEC form or external report.

**Current eligibility remains blocked.** The last Submissions observation was
2026-10-13T22:27:06.532276+00:00; the final filing body was retained at
2026-10-13T22:27:07.827051+00:00. Same-date comparisons do not prove inventory
coverage of that later instant or the full day. The exact reason is
`inventory_observation_precedes_evidence_cutoff`. Preparation input/output hashes
and new batch ID are null; no database publication occurred. September knowledge
and historical flags remain unchanged. Operating margin stays N/A.

Next, separately pin the mandatory pair `company_facts/0001876042` and
`submissions/0001876042`, both captured after all retained bodies, review any changed
inventory and bind a future preparation to that precise observation. Do not silently
expand acquisition or turn a date-level Completeness field into intraday coverage.
Real S6 remains a separate publication gate even after a future S3 batch qualifies.
No schema/API/provider/quote/valuation/sector/scheduler changes were made.

Evidence: [acquisition](../research/crcl-registration-acquisition-2026-10-13.json),
[review](../research/crcl-registration-review-2026-10-13.json), and
[blocked preparation](../research/crcl-current-preparation-2026-10-13.json).
The checked analysis projection provides seven body disclosures plus periodic/Facts
comparisons, exact source links, accession, capture time, hash and transform lineage.

Validation passed: `make check` (1,784 tests, 505 core, 110 golden), production
build, 47 browser checks, inspected desktop/mobile screenshots, keyboard/provenance,
corrupt-artifact recovery and GET-only local requests. Archive/database preservation
and deterministic replay/export passed. Independent staged standards/spec reviews
passed with no remaining findings. Red-first
adversarial tests cover partial/missing acquisition, changed bodies/inventory,
period/unit/sign, exact resource groups, cross-comparison provenance, same-day
observation gaps and unsupported projection promotion. No publication helper is
included in this milestone.
