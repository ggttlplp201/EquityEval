# D3e — Interactive CRCL application pipeline preview

Status: implemented and browser verified; source/financial blockers remain unchanged.
Date: 2026-09-21. Branch: `codex/source-bootstrap`.
Baseline: `61524a7` / `milestone/d3d-identity-review`.
Recovery checkpoint: `milestone/d3e-pipeline-preview`.

## Scope

Expose the completed D3c acquisition and D3d identity review for UI testing in a
separate, tightly linked development page. Preserve the current dark/mint design,
responsive shell, archived observations and fictional Company/Sector examples.
This adds no source acquisition, database operation, schema, public API or
financial calculation. D033 records the authorized presentation-only scope.

**Test route:** `http://127.0.0.1:3101/development/pilot/pipeline`.
The existing project preview on 3101 was an older production server. It was
rebuilt and restarted on the same loopback port with the new route. A normal
`npm run dev --workspace @equity/web` also serves the route on its chosen port.

## Interactions and state

The pilot and Data readiness pages link to **Inspect CRCL’s application pipeline**.
The new page defaults to Quote registration, making the current blocker visible.
Select any of six stage buttons:

1. Pinned acquisition plan: inventory dates, source policy and five fixed resources.
2. Source captures: five current-request captures, public SEC links, UTC timestamps,
   exact capture IDs/body hashes and byte counts in expandable disclosures.
3. Identity review: CIK, issuer name, symbol, NYSE, Class A and listing start;
   expand source evidence and the reason reporting currency cannot establish
   quotation currency. Quote currency stays missing.
4. Quote registration: blocked, with `quote_currency_unsubstantiated` explanation.
5. Financial normalization: not started; zero application normalization batches.
6. Analysis/publication: not started; no financial-analysis result.

Cumulative counters are explicitly distinct from the five displayed captures:
12 captures, 12 fetch attempts, 3 bootstrap requests, 1 issuer, 1 security,
0 quote identifiers, 0 watchlist memberships, 0 normalization batches.
The snapshot is dated 2026-09-21 and labels acquisition readiness separately
from financial-analysis readiness. Nothing is presented as a valuation, ratio,
score, recommendation or completed financial analysis.

Buttons expose selection through `aria-pressed`, control a labelled stage region
and retain keyboard focus. Native details/summary elements provide disclosures;
a concise live status announces stage changes. The shared skip link works.
Source locators/hashes wrap inside narrow layouts. A persistent next-step panel
explains the missing evidence; there are no fetch, retry or registration actions.

## Data boundary and artifacts

- [Exporter](../../scripts/export_pipeline_snapshot.py) verifies the exact D3c
  and D3d audit hashes and projects an explicit allowlist. It reads checked-in
  audit files only, never the application database, `.env` or raw archive.
- [Typed fixture](../../apps/web/src/features/pipeline/snapshot.ts) uses
  `satisfies PipelineSnapshot`. It contains public source references and reviewed
  identity/status metadata; no blob keys/paths, contact values or credentials.
  CIK is in the acquisition plan; the issuer-name literal is the assertion
  verified by the pinned D3d replay against Submissions, not a new source claim.
- [UI](../../apps/web/src/features/pipeline/PipelineWorkspace.tsx) renders the
  sanitized fixture, with no backend mutation or valuation computation.
- [Mapping tests](../../tests/test_pipeline_snapshot.py) reject audit drift,
  inferred quote currency, mismatched completion states, orphan evidence and
  nonpublic source URLs, and verify exact fields/counters and sanitization.
- [Browser tests](../../tests/web/pipeline.test.cjs) exercise navigation, selection,
  keyboard focus, disclosures, source links, scope, responsive layout and
  mutation-free network behavior against the actual built application.

Reproduce/check the fixture:

```sh
.venv/bin/python scripts/project_python.py scripts/export_pipeline_snapshot.py --check
.venv/bin/python scripts/project_python.py scripts/run_tests.py tests/test_pipeline_snapshot.py -q
```

Frontend tests require a running local preview (3101 by default), Playwright and
Chromium. Use an installed Playwright package or set `EQUITY_PLAYWRIGHT_MODULE` to
its module directory; `EQUITY_CHROMIUM_EXECUTABLE` can select an installed Chrome
binary. This run used the Codex bundled Playwright and installed Chrome; no new
npm dependency or browser download was introduced. Override `EQUITY_PREVIEW_URL`
only with a localhost/127.0.0.1 URL.

```sh
npm run test:pipeline --workspace @equity/web
```

## Verification

- 16 focused mapping tests pass; generated fixture exactly reproduces both audits.
- ESLint, Python/TS types and optimized Next build pass. The new route is static,
  4.52 kB route JavaScript / 110 kB first load in the verified build.
- Agent-browser verifies the refreshed server renders meaningful content and has
  no framework error overlay. Seven Playwright scenarios pass (eight Node test
  results including the parent): pilot/readiness navigation, six stages by keyboard,
  native disclosures, exact missing currency/listing evidence, skip link, return to
  CRCL observations/10Y control, widths 320/390/768/1440 and no horizontal overflow.
- No application JavaScript errors, API requests, provider fetches or non-GET
  requests during interaction. The independently reproduced pre-existing
  `/favicon.ico` 404 is recorded as a known warning; all other console errors fail.
  The first test run also exposed a navigation-timing assertion, corrected to wait
  for the route's main content rather than just its URL.
- Desktop and narrow screenshots visually inspected. Ignored local artifacts:
  `var/d3e-first-view.png`, `var/d3e-browser/desktop.png`, `narrow.png`, `network.json`.
- React/Next review: small static server-to-client fixture, no raw audit imports,
  direct component imports, one local selection state, native disclosures,
  stable evidence keys and no effect-driven state or browser arithmetic.
- Commit acceptance: mandatory full suite (1,099), core (225), golden (110),
  lint/format/import policy/generated enum and strict Python/TypeScript checks.

## Handoff

This is a saved development snapshot, not ongoing polling or a live readiness API.
A changed audit requires substantive review before the exporter accepts it.
The next data blocker remains explicit quote-currency evidence. Registration,
ordinary source-backed requests, event/financial coverage, normalization/PIT/S5
and reviewed S6 publication remain separate work. Continue from D3d's handoff;
this preview does not change its application counts or unblock financial analysis.
