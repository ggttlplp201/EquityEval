# S3 acceptance plan

Status: implemented acceptance suite. Numeric expectations and adversarial cases
were specified before their corresponding implementation. `sec_normalized_cohort.json`
contains all 320 reviewed outcomes; the earlier `s3_review_cases.json` remains the
source-evidence review checkpoint. See [implementation](implementation.md) and the
[milestone record](../../milestones/S3-ingestion.md) for validation and limits.

## Transport and storage

Use an injected fake HTTP transport and clock; production coordination tests also
exercise a disposable Redis instance. No CI request goes to SEC.

- Validate CIK/resource identity and every redirect; reject ambiguous tickers,
  credentials, traversal and unsupported hosts. Count all requests against one SEC
  coordinator across hosts/workers; expired grants cannot accumulate into bursts.
- Verify the configured contact header without committing a real address. Enforce
  the rolling hard ceiling, conservative target, shared 403/429 cooldown and
  Retry-After. Coordinator failure prevents dispatch.
- Stream complete JSON/HTML/error bytes before parsing; verify decoded-byte hash
  and count, gzip replay, atomic publication and explicit body limits.
- Cut an HTTP 200 body mid-stream; actual status remains 200 on a failed attempt,
  no complete capture is published and no financial parse begins. Crash before/
  after body publication and DB commit; recovery preserves unknown outcomes.
- Cache reuse and 304 retain old capture identity/time; missing/corrupt cached bytes
  cannot claim success. A later identical 200 has its own retrieval identity.
- Reject cross-source policy/capture links and edits to terminal attempts/policy
  revisions. Verify runtime grants and new migration downgrade/upgrade parity.

## Exact source evidence prepared now

Use the existing eight complete S1 Company Facts archives and their manifest
hashes, with reviewed exact raw rows and locators. The small S3 review packet adds
executable evidence checks across AAPL, MSFT, JPM, CRCL, RBLX, TSM, KHC and COST.
It includes explicit source gaps and scope hazards. No new payloads are fetched.
The five S1 filing-to-API spot checks remain the hand-reviewed comparison basis;
they are not generated from a future production selector.

## Normalized golden acceptance after contract approval

For each cohort anchor, manually specify all 40 requested concept outcomes by
scope/period: exact observed value and selected tag, or explicit gap/status/reason.
Candidate-presence matrices cannot generate the expected answers. Cover:

| Company | Required boundary |
| --- | --- |
| AAPL | Exact fiscal interval, customer-contract revenue, period-end/cover/weighted shares, missing complete current-debt total. |
| MSFT | Cash capex, no SG&A arithmetic patch, no substitution of custom D&A-and-other. |
| JPM | Net-of-interest revenue basis, bank scope, absent/stale generic cash/PP&E and classified working capital. |
| CRCL | Total versus customer-contract revenue, corporate cash versus holder reserves, reported repurchase zero versus absent dividends. |
| RBLX | Parent versus consolidated loss, negative NCI, equal loss-period EPS, stock-class identity and broader cost totals. |
| TSM | FY2025 source gap, explicitly separate FY2024 observations, TWD versus convenience USD, ordinary shares versus ADS, paid dividends versus appropriation. |
| KHC | Original/revised parent and consolidated figures through parser/writer/PIT; public non-reliance dates; distinguish recast from error restatement. |
| COST | Revenue including membership fees, 52/53-week periods, no stale goodwill, cash-flow SBC basis. |

Numeric parser adversaries: numeric zero, nil, absent value, malformed numeric,
booleans, huge integers, decimal/exponent tokens, numeric versus digit-string CIK,
nonfinite values and duplicate
JSON keys. Semantic adversaries: conflicting candidates, unsupported unit/context,
newest missing currency/value, newer unknown-authority coverage with a pinned
blocking flag preventing an older usable result, amendments, equal-day ordering ambiguity, changed
source bytes and nondeterministic output. Preserve missing optional fy/fp/frame. Distinguish missing val, JSON null and
source-declared nil. Test identical semantic duplicates separately from equal
amounts with incompatible scope; only one candidate can be selected. Verify
same-manifest replay reuse and new-capture/identical-body distinct vintages.

Every bundle goes through real S2 constraints and historical queries. Atomic writer
replay must be idempotent while retaining new source vintages/revisions. Incomplete
filing inventory, coverage review or event evidence must remain visible and block
unsupported historical/valuation claims.

## Original filing slice

Test context entity, instant/duration, dimensions, share classes, unit numerator/
denominator, Inline XBRL numeric transforms, sign/scale and nil independently.
Unknown/custom semantics require explicit reviewed rules. Do not silently fill a
Company Facts gap from arbitrary filing text. Accounting identities belong to the
pure financial layer; ingestion does not repair a discrepancy or sum missing facts.
