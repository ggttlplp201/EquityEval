# First genuine CRCL application capture — 2026-09-21

Implementation: `de0aefa`, tag `milestone/d3b-source-bootstrap`.
Live parser correction: `ec7f3f7`, tag `milestone/d3b-inventory-parser`.
Full nonsecret [capture audit](crcl-first-application-capture-2026-09-21.json)
contains exact capture/source/policy IDs, original timestamps, URL, hash/count and
archive references. Raw bodies remain under the application's ignored `var/raw`.

## Result

Request `21669ad8-55c4-4a04-8bbe-ac71ef9d1375`, execution
`bdb43acc-b434-4525-aa4f-16376609b7dc`, completed capture-only with no source gaps.
All five sources returned HTTP 200: Company Facts, Submissions, original FY2025
10-K, July 2026 10-K/A, and Q2 2026 10-Q. Every archive hash/count, database timestamp
and policy/attempt link was rechecked. Manifest SHA-256:
`522dfbb9457d9649b8cf77a525c50ec7f9cf12aeb7a61199f241ab34fe2ed374`.

The manifest retains `financial_result=false`, `event_review=not_performed` and
`quote_identifier_id=null`. Reusing the completed key returned the same request,
state completed and `dispatched=false`; it did not fetch again.

Initial request `954c15d5-d14b-471d-8e87-f1e82978f9a1` remains failed, with its two
successful captures retained. Actual SEC renderer subdirectories exposed an overly
strict inventory metadata validator. The correction was verified by replaying the
saved body without network, then passed 1,033 full, 225 core and 110 golden tests,
lint/types and both independent review axes. The subsequent request added the newly
evidenced amendment and performed a fresh bounded capture with its own timestamps.

## Evidence review

- Submissions contains 421 records; 393 fall within 2025-01-01 through 2026-09-21.
  No older documents are advertised. Inventory coverage is complete within that
  definition, with no inventory flags. This is not an event-coverage certification.
- The July 13 amendment (`0001876042-26-000228`), Explanatory Note, adds separate
  audited Circle Reserve Fund statements for its April 30, 2026 year end and
  related exhibits/certifications. It says it otherwise does not amend, update or
  restate the original report. Review conclusion: this amendment alone should not
  supersede Circle's consolidated FY2025 revenue/operating-income observations.
  It is not evidence of absent subsequent events or complete statement coverage.
- Original 10-K (`0001876042-26-000062`), Item 5, explicitly places the start of
  CRCL Class A trading/listing on NYSE at June 5, 2025. The cover and Q2 cover
  corroborate symbol, exchange and class. This date is actual listing evidence,
  not a filing date substituted for listing validity. Quote currency and the
  intended validity interval still need an explicit reviewed identity record.
- Fresh original-filing extraction reproduces revenue 2,746,642,000 USD and
  operating loss 96,435,000 USD at context c-1, USD unit, empty dimensions.
  These are source observations, not newly published core results. The existing
  extractor still reports 249 whole-document issues; individual agreement does
  not establish complete financial-statement extraction.
- Fresh Company Facts has the same body hash as the legacy S1 payload. The fresh
  annual document differs by a 116-byte script insertion near its closing markup;
  it was only read as source bytes, not executed. Both complete source hashes are
  preserved separately. Old unknown request/completion times remain unknown.

## Remaining work

Application counts: 1 source/policy/issuer/security, 7 captures, 2 requests,
0 quote identifiers, 0 watchlist memberships and 0 normalization batches.
The successful request does not claim financial publication or an S6 snapshot.

Next is a bounded CRCL identity/publication review: substantiate quote currency and
validity, retain the amendment's distinct scope, establish explicit filing/event
coverage, and pin approved mapping/period/scope/precision in S3 publication. Then
use actual PIT selection for eligible S5 metrics and take the minimal S6 contract
through its required sequential review. If a prerequisite fails, retain its gap.

The redesigned UI and all seven pilot companies remain intact. Its D2 view still
uses the original archived observations; this milestone does not silently swap
its source references or claim the new database rows are already displayed.
