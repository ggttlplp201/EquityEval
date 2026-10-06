# D5b — CRCL analysis readiness

Status: complete

Date: 2026-10-05

Branch: `codex/d5a-crcl-normalization`

Proposal commit: `bb30206`

## Objective

Project the reviewed D5a CRCL normalization result into a checked, read-only
application view that distinguishes exact normalized facts from inputs that are
eligible for financial analysis.

## Delivered scope

The [proposal](../design/d5b/proposal.md) permits a deterministic artifact and
development UI with exactly two source inputs and zero published metrics. Both
facts remain blocked by incomplete inventory and event history. Operating
margin stays unavailable.

- `scripts/export_crcl_analysis_readiness.py` validates the fixed D5a snapshot
  and provenance hashes, fact roster, signed values, source chains, retained
  flags and false eligibility before emitting the D5b snapshot and manifest.
- `/development/pilot/analysis` shows the two normalized amounts, the withheld
  operating-margin candidate and five publication gates.
- Each abbreviated amount opens its exact D5a source, accession, retrieval and
  transform evidence; retrieval and publication dates remain visible.
- Pipeline, normalization, Help and the user guide link to the new page.
- Display abbreviations come from the offline exporter. React performs no
  financial calculation.

## Decisions and review

D040 authorizes only this read-only projection. The implementation introduces
no migration, database write, provider/source activity, quote registration,
schema/API concept, missingness change or real S5/S6 publication. Visual review
confirmed the desktop and 390px layouts keep the status and N/A result clear.

## Validation evidence

| Command/check | Result | Date | Notes |
| --- | --- | --- | --- |
| `make check` | Pass | 2026-10-05 | 1,720 full, 505 core and 110 golden tests; lint, generated contracts, mypy and TypeScript pass |
| `npm run build --workspace @equity/web` | Pass | 2026-10-05 | Production route `/development/pilot/analysis` compiled |
| D5b + pipeline + D5a browser suites | Pass | 2026-10-05 | 23 checks; per-value provenance, keyboard, direct load, corrupt-snapshot recovery, GET-only application requests and 320–1440px widths |
| Generated artifact mutation tests | Pass | 2026-10-05 | Value, roster, eligibility, history flag, source chain and batch changes fail closed |

## Limitations and blockers

Stop before real S5/S6 publication, new source acquisition, identity or quote
registration, schema/API changes, or any change to finance formulas and
missing-data semantics. Those require their existing reviews and evidence.

## Handoff

See the [D5b handoff](../handoffs/d5b-analysis-readiness.md). The next main stage
is a reviewed, sector-aware CRCL metric/profile and source-coverage proposal,
followed by evidence acquisition. D5b itself does not unblock calculation.
