# D3f — CRCL quotation-currency source search

Status: source search concluded blocked; saved UI disclosure implemented and browser verified.
Date: 2026-09-21. Branch: `codex/source-bootstrap`.
Baseline: `34afcf4` / `milestone/d3e-pipeline-preview`.
Recovery checkpoint: `milestone/d3f-currency-search` (created after acceptance checks).

## Outcome and scope

**No quote identifier registered.** No inspected source supplied qualifying,
retainable evidence explicitly binding Circle Class A / CRCL / NYSE to a
quotation currency with effective-date context. `quote_currency` stays missing;
`quote_currency_unsubstantiated` remains the blocker. This is a bounded negative
search result, not a claim that no such evidence exists anywhere.

The user authorized the next implementation step and the coordinator specified
currency evidence/conditional registration after D3e. The blocked outcome is
recorded in D034. The implementation preserves the supplied dark/mint design,
adds inspected-source disclosures to the existing pipeline page, and reuses the
D3d archive/database verification. No schema, vocabulary, missingness, public API,
source policy, identity mutation, watchlist membership, ordinary request,
financial normalization, valuation or S6 publication changes were made.

**Test route:** `http://127.0.0.1:3101/development/pilot/pipeline`.
Select Quote registration (default), then expand each Official-source search row.
The existing Company, Sector, News and Help routes remain intact.

## Primary-source search and policy findings

The [pinned search notes](../research/crcl-quote-currency-search-2026-09-21.json)
are authored research metadata. Their hash protects the reviewed notes against
silent edits; it is **not** a hash of a downloaded source response. Browser/search
observations below are not promoted to application capture/attempt evidence.

| Source | What was inspected | Result |
| --- | --- | --- |
| [SEC annual filing](https://www.sec.gov/Archives/edgar/data/1876042/000187604226000062/crcl-20251231.htm) and existing pinned filings | D3d assertions replayed over immutable D3c captures; targeted primary-source discovery | CIK, issuer, Class A, CRCL, NYSE and 2025-06-05 listing start supported. Reporting currency, offering-price units, par value and public-float amounts do not establish quotation currency. |
| [Official NYSE CRCL page](https://www.nyse.com/quote/XNYS:CRCL) | Static page initially exposed only navigation. A later normal browser load rendered the quote and delivered `/api/quotes/filter` and `/api/nyseservice/v1/quotes` responses (HTTP 200). Identity/currency-related fields were inspected in memory. | Filter fields identify Circle/CRCL/XNYS. Inspected quote fields include a quote time but no explicit quotation-currency field. Rendered prices/word “dollars” were not converted to USD. No payload was persisted to application storage. |
| [Circle stock information](https://investor.circle.com/stock-info/) and linked [FAQ](https://investor.circle.com/resources/investor-faqs/default.aspx) | Public text extraction and normal browser navigation | No populated quote-currency evidence in extracted text. Browser stopped at Cloudflare security check; no bypass. The footer terms link resolves to the [Circle Mint agreement](https://www.circle.com/legal/user-agreement), which is not accepted as a grant for retained IR/Q4 quote data. |
| [NYSE Security Master](https://www.nyse.com/data-products/catalog/nyse-group-security-master), [technical catalog](https://www.nyse.com/market-data/technical-documents), [sample directory](https://ftp.nyse.com/Reference%20Data%20Samples/NYSE%20GROUP%20SECURITY%20MASTER/) | Product description and directory listing only | Product/access entitlement not obtained. Inspected equity sample filenames refer to pre-listing vintages; later directory modification dates do not establish CRCL record validity. No sample import or purchase. |

[ICE terms](https://www.ice.com/privacy-security-center/terms-of-use), reviewed
2026-09-21, describe limited personal access/download and exclude automated
extraction from that license. No compatible retained-ingestion permission was
established. This operational source-policy finding does not activate a provider
or treat a reachable website/API as a licence. See the [licence register](../data-licences.md).

Additional primary discovery results were rejected as out of scope: a Nasdaq
blockchain index factsheet's USD currency describes the index, not the CRCL
constituent; SEC fund holdings/derivative references and general exchange feed
specifications do not establish this exact share-class quotation currency.
Third-party quote displays were not used to resolve the field.

The review date, quote timestamp, filing date and directory modification date
are not currency effective dates. Existing listing-start evidence cannot
backdate a current currency observation to the IPO. No currency validity
interval is asserted.

## Reuse and implementation

- Existing `review_crcl_identity.application_review()` verifies raw archive
  hashes, immutable request/manifest, source policy/capture links and execution
  attempts in a repeatable-read/read-only transaction. Nothing is re-fetched.
- Existing exporter now pins the search-note hash as well as D3c/D3d hashes,
  verifies identity/date binding and blocked-state invariants, then allowlists
  presentation fields. Research links are checked separately from archived SEC
  capture URLs. No contact values, credentials or local archive paths are added.
- New optional `--verify-application` compares the complete replay with the saved
  D3d audit, including table hashes and counts, before claiming a current match.
  Plain export, build and unit tests remain offline. Driver-error messages are
  suppressed to avoid leaking connection details. Run this option **as a module**:

```sh
.venv/bin/python scripts/project_python.py -m scripts.export_pipeline_snapshot --check --verify-application
```

- The UI adds four keyboard-accessible native disclosures: source checked,
  method, finding, effective-date limitation, retention/policy status and public
  links. The provenance section identifies the search-note hash separately from
  captured SEC body hashes. No new browser requests or mutation controls.
- Existing SEC bootstrap resources and S4 provider resources are deliberately
  typed. A new NYSE/IR source cannot be smuggled through a Treasury/price resource
  or inserted directly into evidence tables. No qualifying/approved new source
  was found, so no adapter or registration writer was introduced speculatively.

## Application verification

The optional read-only check matches the pinned D3d evidence and table hashes.
Repeated verification preserves history and creates no duplicate records.

| Record | Count |
| --- | ---: |
| Sources / reviewed policies | 1 / 1 |
| Issuers / securities | 1 / 1 |
| Captures / fetch attempts | 12 / 12 |
| Bootstrap requests / executions | 3 / 3 |
| Stage attempts / execution events | 19 / 64 |
| Quote identifiers / validity projections | 0 / 0 |
| Watchlist memberships / normalization batches | 0 / 0 |

There are no ordinary financial-analysis requests. New research page visits are
not application fetch attempts. The five pinned D3c captures remain distinct
from the twelve cumulative application captures.

## Validation

- 60 focused pipeline/identity tests pass. Added cases cover exact issuer/class/
  exchange/date binding, false capture/policy claims, backdated currency, wrong
  currency meaning, duplicate sources, unsafe related URLs, note hash drift,
  same-count database hash drift, deterministic replay and private error handling.
  Existing D3d integration coverage enforces a read-only database transaction.
- Lint, formatting, import policy, generated concepts and strict Python/TypeScript
  checks pass. Optimized Next build passes; pipeline route is static, 4.87 kB
  route JavaScript / 111 kB first load.
- Agent-browser confirms meaningful rendered content and no framework overlay.
  Eight Playwright scenarios pass (nine Node results including their parent),
  including keyboard disclosure use, all six stages, source links, exact counts,
  navigation/10Y preservation and widths 320/390/768/1440 without horizontal
  overflow. No page errors, API/provider requests or mutations. The existing
  narrowly identified favicon 404 remains the only allowed console warning.
- Desktop/narrow screenshots visually inspected. Ignored verification artifacts:
  `var/d3f-browser/desktop.png`, `narrow.png`, `source-search.png`, `network.json`.
- React/Next review: static typed data, existing state/shell reuse, native
  disclosures, explicit external link handling, stable keys, no new effects,
  dependencies, client fetching or financial arithmetic.
- Real application replay succeeds with exact D3d table/capture/attempt hashes;
  checked-in research and UI additions contain no local blob paths or contacts.
- Commit acceptance requires the repository hook's full, core and golden suites
  plus lint/types to pass before the milestone checkpoint is created. The hook
  is enabled and is not bypassed.

The first optional-check invocation exposed Python's direct-script import scope;
its module invocation is now documented. A module-docstring formatting issue was
also corrected before lint/type/build acceptance. Neither issue changed data.

## Handoff

The next data dependency is an explicit issuer/exchange statement or entitled
reference record with the exact issuer, share class, exchange, currency meaning
and supported effective date. Review retention and capture that evidence through
an approved source path before registration. A new source resource/contract, if
required, needs the concrete sequential review specified in AGENTS.md; no such
contract change is hidden in this milestone. Only then implement/test the
conditional idempotent registration writer. Watchlist, financial coverage,
normalization/PIT/S5 and S6 publication remain later work.

## Later checkpoint

D4a adds a separate governed monitor request and attempt history. D3f's optional
current-database equality check deliberately describes the D3f checkpoint only;
after D4a use the [new monitor verification](D4a-filing-monitor.md), which checks
old row hashes and the new audit separately. Plain D3f snapshot `--check` remains
offline and unchanged. The old JSON audits are not rewritten.
