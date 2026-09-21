# Data-source licence register

Scope-specific source reviews are recorded below. A website being reachable or
an API key being valid does not establish retention or redistribution rights.
No research entry automatically provisions an application policy or live worker.
S1 SEC payloads were captured with the configured contact; see its manifests.
Original source recommendations remain preserved in the supplied specification.

| Source | Milestone | Evidence | Retention/use result | Redistribution | Verified |
| --- | --- | --- | --- | --- | --- |
| SEC EDGAR public filings / government-created data | S1/S3 | SEC reuse FAQ and dissemination policy below | Allowed under published policy for the defined scope | Allowed for that scope; attribute SEC and filing | Rechecked 2026-09-12 |
| Tiingo | S4 | [Research](design/s4/tiingo-research.md); [terms](https://app.tiingo.com/tos/) | No verified grant compatible with permanent raw/normalized history; live inactive | Not approved | Terms reviewed 2026-09-12; account entitlement unverified |
| FRED/ALFRED API | S4 | [Research](design/s4/fred-research.md); [terms](https://fred.stlouisfed.org/legal/) | Storage/development restrictions unresolved; per-series rights also required; live inactive | Not approved | Terms reviewed 2026-09-12; no authenticated request |
| Direct Treasury nominal-yield XML | S4 proposed initial yield source | [Research](design/s4/fred-research.md); [official CC0 catalog](https://catalog.data.gov/dataset/interest-rate-statistics-daily-treasury-yield-curve-rates); [capture manifest](research/s4/evidence/treasury-yield-manifest.json) | Official dataset-to-current-feed linkage and one complete monthly response verified; proposed scope is nominal-yield dataset, initial normalization 2y/10y; no production activation | Catalog CC0 scope; preserve attribution/provenance | Reviewed 2026-09-12 |
| Direct Federal Reserve Board H.15 XML ZIP | S4 candidate | [Research and full-body scope finding](design/s4/fred-research.md); [manifest](research/s4/evidence/frb-h15-manifest.json) | Selected government-series format verified; full ZIP includes legacy Moody's material and has unresolved raw retention scope; quarantined research only | Full ZIP not approved | Actual format and scope inspected 2026-09-12 |
| EODHD / Alpha Vantage | S4 alternatives | [Bounded review](design/s4/tiingo-research.md) | Permanent retained-evidence permission unverified; neither selected | Not approved | Public terms reviewed 2026-09-12 |
| NYSE quote page/API and Security Master | D3f identity research | [Search record](milestones/D3f-quote-currency-search.md); [ICE terms](https://www.ice.com/privacy-security-center/terms-of-use) | No compatible retained automated-use grant or account entitlement established; no raw capture/provider activation | Not approved | Primary pages and normal browser responses inspected 2026-09-21 |
| Damodaran datasets | Before S7, if selected | Exact dataset and terms still required | Pending | Unknown | No |
| BLS / Federal Reserve schedules and releases | N1 | Exact calendar/release/feed scope required; N1 source links | Pending; H.15 rate review does not cover news/calendar ingestion | Unknown | Research only |
| Congress.gov legislation | N1 | Bill/text/action APIs; H.R. 3633 in CRCL example | Pending | Unknown | Research only |
| Circle IR / product disclosures and metrics | N1 / D3f | Exact pages/feed and archive scope; [D3f stock-info check](milestones/D3f-quote-currency-search.md) | Pending; linked Circle Mint agreement does not establish IR/Q4 quote-data retention scope; distinct from SEC-hosted filings | Unknown | Research only; stock-info checked 2026-09-21 |
| Open Standard announcements / partner directory | N1 | https://joinopenstandard.com/ and linked announcements | Polling/retention/reuse pending | Unknown | Research only |
| Reap Open USD explainer | N1 discovery reference | User-supplied article in CRCL example | No recurring adapter selected | Unknown | Research only |

For each approved source record terms URL/date, account/tier if applicable,
permitted use, attribution, redistribution decision and evidence hash. Separate
rights to the complete retained raw body from the subset normalized by the app.
A later operational disable does not itself erase an established indefinite
retention grant; changed content rights require explicit review.

The accepted [S3 contract](design/s3/source-contract.md) implements versioned
policy reviews and mandatory capture links. Tests use fictional policy rows.
The [S4 capabilities](design/s4/storage-review.md) are proposed gates, not current
production schema. No provider contact, payment or account changes were made.

SEC scope evidence: [reuse FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)
and [dissemination policy](https://www.sec.gov/about/privacy-information).
This does not grant rights to unrelated artwork, branding or vendor data.
See [S1 source boundaries](research/s1/source-boundaries.md).

The owner-approved D031 operational bootstrap uses the narrowly scoped
[SEC application review](research/sec-application-policy-2026-09-21.md). The
explicit registration command pins its real review timestamp/hash before capture;
it does not activate prices, macro/news feeds or any other provider.
