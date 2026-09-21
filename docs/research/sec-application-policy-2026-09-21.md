# SEC application source policy — 2026-09-21

Scope: SEC government-created Company Facts, submissions and advertised same-CIK
submission history on data.sec.gov, and SEC-hosted public filing documents under
www.sec.gov/Archives/edgar/data. This review does not cover unrelated artwork,
third-party market feeds, Circle's own website, news, or other providers.

The source register already accepts SEC public filings/government data under S1/S3.
The owner explicitly authorized D031 implementation and first genuine CRCL capture
using existing project settings. This record documents the scoped application
policy provisioning; it does not fabricate a historical provider approval.

Official pages reviewed on 2026-09-21:

- https://www.sec.gov/about/webmaster-frequently-asked-questions
- https://www.sec.gov/about/privacy-information
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces

The SEC FAQ permits access and reuse of government-created content and EDGAR
public filings, with exceptions for unrelated material such as stock artwork.
For this exact scope, retained raw bodies and derived observations are permitted
for local analysis and reuse. Preserve SEC/issuer attribution, canonical source
URL, accession when present, capture times, hashes and transformation references.
The FAQ does not grant a licence to unrelated vendor data hosted elsewhere.

Operational limits: use the actual configured identifying contact; one shared
Redis budget at five requests/second, with the existing hard cap of ten, including
redirects/retries. Archive complete entity bodies before parsing. Retain failures
and partial-attempt metadata; only successful, complete captures can supply facts.
A blocked request never justifies changing the contact or bypassing the limiter.

Review identity: `sec-public-filings-2026-09-21`.
Licence label: `SEC public filings and government-created data reuse`.
Redistribution: allowed within the defined scope, with the provenance above.
Reviewed by: Codex source review under owner-authorized D031.
The database records the actual provisioning/review timestamp and SHA-256 of this
immutable review artifact, not the dates of the SEC pages or old S1 archives.

CRCL bootstrap identity comes from the separate dated seven-company research
packet: CIK 0001876042, Circle Internet Group, Inc., Class A common stock. A
bootstrap security is not a registered stock-exchange quote. The first capture
must not invent a listing start date or claim a completed analysis.
