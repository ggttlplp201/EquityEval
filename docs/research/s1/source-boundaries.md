# SEC source boundaries and implications

Verified from official SEC documentation on 2026-09-11. Payload field behavior
and cohort-specific coverage remain pending empirical inspection.

## Company Facts

The API aggregates standard-taxonomy facts that apply to the whole filing entity.
Examples include us-gaap, ifrs-full, dei and srt. Units remain separate; multiple
currencies or compound units can occur. Frames use the latest filing nearest a
calendar interval, so they do not establish historical point-in-time values or
identical fiscal periods. APIs require no key; data.sec.gov does not support CORS.
[SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)

Engineering consequence: preserve namespace and unit; use backend ingestion;
never promise segment or custom-tag coverage from Company Facts. Original filing
XBRL/Inline XBRL needs a separate reviewed extraction path. A tag-priority override
cannot retrieve data the endpoint omits. This is a correction to SPEC 2.1/3.2.

## Access and preservation

Declare the client identity/contact. SEC's request ceiling applies per user
across machines, so workers need a shared limiter. Cache targeted downloads and
back off on failures. [Access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data),
[developer resources](https://www.sec.gov/about/developer-resources)

The project additionally requires raw responses to be archived before parsing.
For S1 direct downloads, preserve URL, retrieval timestamp, raw-body checksum and
compressed file location. Do not put the user's contact email into committed
research artifacts; keep client configuration local.

## Time and corrections

Official filing dates, acceptance timestamps and reporting periods are distinct.
SEC does not supply the exact timestamp when content first becomes publicly
available, and post-acceptance corrections can alter filing records.
[Timestamp FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions),
[correction policy](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)

Engineering consequence: call a filed-date cutoff what it is. Do not describe
it as exact intraday knowledge. Document the cutoff timezone/inclusivity and
preserve separately retrieved versions before S2's schema review.

## Alternative source coverage

SEC's Financial Statement and Notes datasets include custom tags and dimensional
information, but monthly extracts and processing corrections are distinct from
the original filings. Use them as explicit additional sources, not a silent
fallback for missing Company Facts observations.
[Dataset documentation](https://www.sec.gov/files/aqfsn_1.pdf),
[dataset overview](https://www.sec.gov/data-research/sec-markets-data/financial-statement-notes-data-sets)

## Reuse

SEC permits access and reuse of government-created content and public EDGAR
filings, with attribution requested by its dissemination policy. Separate site
artwork/logo restrictions do not define the selected financial-data scope.
[Reuse FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions),
[dissemination policy](https://www.sec.gov/about/privacy-information)

## Pending empirical checks

Verify the actual availability and meaning of start/end, accn, fy/fp, filed and
optional frame fields; comparative-period repetitions; restatement rows; units
and scaling; missing concepts; and company-specific tag choices. API landing
pages do not establish those observations for this cohort.
