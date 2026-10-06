# D5b handoff — CRCL analysis readiness

Date: 2026-10-05

Baseline: `bb30206`

## Delivered boundary

The D5b exporter reads only the checked D5a normalization snapshot and its
provenance record. It validates their fixed hashes, batch identity, exact two-fact
roster and signed values, source chains, false eligibility and both retained
history flags. The generated readiness artifact contains two normalized inputs,
zero published metrics and a null operating-margin result.

`/development/pilot/analysis` presents that decision and links back to exact D5a
source evidence. Each displayed amount opens its original D5a evidence detail,
and retrieval/publication dates remain visible. Pipeline and normalization pages
link to it. Display values are generated offline; the React component performs
no financial arithmetic.

## What remains blocked

- Complete reviewed inventory and event history for the required period.
- A reviewed CRCL business profile and applicable metric roster.
- The financial/accounting inputs required beyond the two D5a facts.
- Explicit quotation-currency identity before price-dependent ratios.
- A reviewed real S6 publication contract and real source-backed payload.

Do not turn the two exact numbers into a real operating-margin publication until
those gates pass. D5b adds no migration, application write, source acquisition,
provider, quote identifier, schema/API concept, formula or missingness change.

## Next review

The next main stage is evidence expansion for a real CRCL fundamentals packet:
define the sector-aware metric profile and exact source roster, then acquire and
review the missing history and accounting inputs. That work needs its own
proposal before source or publication changes.
