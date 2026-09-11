# S1 research packet

Status: work in progress, not an approved vocabulary or mapping.

This milestone inspects the source before freezing normalized concept names.
The candidate cohort is in [cohort.md](cohort.md). Every claimed tag observation
must identify a saved Company Facts payload, taxonomy/tag, unit, period and
filing accession. Candidate tag names without observations stay unverified.

Direct SEC data downloads are pending a real contact User-Agent. Public SEC
API documentation and filing research can proceed independently.

The intended deliverable is a reviewable document covering about 40 concepts,
company exceptions, missing-data behavior, period/share/currency distinctions,
and an original-versus-restated example. Research extraction is not production
normalization and does not create hand-checked golden fixtures automatically.

## Confirmed source boundary

[SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
says the aggregated XBRL APIs cover non-custom taxonomies and whole-entity facts.
A company-specific map cannot recover a custom tag absent from this endpoint.
Original filing/Inline XBRL access would be required for those observations, with
explicit contexts, units and review. Segment coverage must not be inferred from
entity-wide API rows. This corrects the coverage assumption in SPEC 2.1/3.2.

## Current documents

- [40 candidate concepts](concept-candidates.md): definitions and hazards, mapping unverified.
- [Source boundaries](source-boundaries.md): verified API limits and engineering consequences.
- [Kraft Heinz restatement](restatement-khc.md): original/revised filing evidence for S2.
