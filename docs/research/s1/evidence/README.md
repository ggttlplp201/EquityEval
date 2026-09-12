# S1 archived evidence

These files are source-research artifacts, not production fixtures or an
implemented ingestion service. No contact email is recorded here.

- `manifest.json`: eight Company Facts responses, source URLs, CIKs, UTC retrieval
  times, empty-query hash, decompressed-body SHA-256, byte counts and taxonomy counts.
- `filing-manifest.json`: eight complete original filing documents (seven annual
  filings and KHC's restatement note). Includes the TSM interrupted attempt and
  successful retry; only complete responses have an archived body.
- `raw/*.gz`: responses archived before parsing. Hashes refer to decompressed
  bytes, so they are independent of gzip timestamps/headers. Source, parameters
  and retrieval identity are recorded in the corresponding manifest record.
- `concept-observations.json`: 320 concept/company groups for the pinned anchors,
  with exact candidate rows, source labels, units, availability and competing
  observations. No financial values are selected or synthesized.
- `filing-spot-checks.json`: five manually specified source comparisons, with
  exact Inline XBRL literals/scales/contexts and expected raw API values.

## Replay an observation

1. Locate the company/filing manifest entry and decompress its raw file. Recompute
   SHA-256 and byte count before trusting an extracted row.
2. Read `facts[namespace][tag].units[unit]` in the Company Facts JSON. Match the
   exact `accn`, `end` and duration `start`; instant facts must not have a start.
   Use the expected unit without currency conversion. Retain every matching row.
3. Compare the full raw row, including nullable `fy`/`fp`, optional `frame`,
   `form` and `filed`. Do not filter by fiscal-focus year or require a frame.
4. For original filings, locate the qualified Inline XBRL tag and context ID,
   inspect entity, dimensions, period and unit, and retain lexical value, sign,
   scale and precision. A matching tag name alone is not equivalent scope.
5. Apply the concept-map's human-reviewed semantics only in the later adapter.
   Candidate presence, spot-check agreement and equal values do not establish
   a universal normalization rule.

The coverage matrix uses O (exact candidate observation), D (anchor observation
at another period/unit), H (tag elsewhere in payload) and A (no listed candidate
in payload). It is a research coverage view, not a success-rate metric.

Downloads were sequential with a declared contact User-Agent and delays,
well below the SEC ceiling of ten requests per second. Subsequent production
workers still need the shared limiter and retry contract specified in S3.
