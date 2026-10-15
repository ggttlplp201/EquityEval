# D5i — Current CRCL inventory observation and conditional normalization

Baseline `07c53d69`; proposal `c55c2cf`, D047. Independent standards, specification and numeric reviews passed.

One governed exact-pair BootstrapPlan retained Company Facts at
2026-10-15T21:59:05.128575+00:00 and Submissions at
2026-10-15T21:59:05.195192+00:00. Both postdate all reviewed bodies. Their hashes
match the last reviewed October captures. Scoped periodic/current-event and
registration metadata, advertised history completeness, annual/Q1 editions and
acceptance bounds match the preceding review. The fresh observation closes the
D5h timing gap; it asserts no event coverage beyond that exact instant or whole day.
All prior application rows and historical artifacts are preserved.

Disposable PIT readback caught old filing-version metadata being superseded by
the fresh inventory. New immutable versions bind to the fresh Submissions capture.
The September-to-October metadata delta is explicitly pinned: acceptanceDateTime
alone differs for 000062, 000228 and 000248 (prefix 0001876042-26-). Exact old/new
values and both source hashes/capture IDs are in the review and proposal addendum.
No cause or timezone conversion is inferred. New versions use the fresh reported
timestamps/hash; the old versions and D5a query results remain unchanged.

The current preparation retains 71 evidence captures and the unchanged two-concept
mapping. Exact original FY2025 annual source operands reconcile with original
inline filing context, USD unit, thousands scale/sign and precision. Inventory and
event completeness are bounded by the exact fresh observation. No quality flags
are manually cleared. Disposable tests prove a distinct current batch, exact
publication replay, eligible readback, pre-filing missingness, original-as-filed
selection and preservation of historical blockers.

No real S6 metric is published in D5i. The existing S6 InputManifest and
FundamentalsPayload only permit synthetic evidence with a fixed synthetic label;
SelectionKey and migration 0011 require a quote identifier. Real descriptive
source-only operating margin needs a separate reviewed schema/API publication
boundary. Reporting USD does not establish quote currency. No quote/provider,
valuation, sector, scheduler, API, concept or migration changes are included.

Validation: full `make check` passed (1,799 tests, 505 core and 110 golden);
14 focused observation tests include the subsequently added publication regression.
Production build and all 51 browser checks pass (47 prior checks plus four new
checks; one case-sensitive presentation-label assertion corrected and rerun).
Desktop/mobile screenshots inspected. Independent final standards/spec reviews
pass, as did the separate pre-publication numeric review. Red-first tests
cover changed sign/unit/edition/metadata, future acceptance, stale/partial/duplicate
captures, unavailable runtime, forged publication hashes and exact metadata
provenance. Preview 3103; unrelated 3101 untouched.

Live S3 batch `b49859b5-9f27-455a-87a4-e6fe776f5314` published successfully.
Exact replay reused it; current and original selection are usable, pre-filing
selection remains missing, old D5a blockers and every prior row are preserved.
Input hash `a179286890c64c55a8f6afb855506bf4732324bc74d5ef944e037695d67b72a4`;
output hash `5a0f7405d7d939a9fdae7732ab2bd1b2d368c0f277ba948f47f156a4a33c8240`.
Totals: 76 captures, 78 attempts, 18 requests (16 bootstrap, two monitor), two
normalization batches/four selected facts, zero published real metrics.
