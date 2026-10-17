# D5l — Bounded CRCL correspondence/history acquisition and eligibility

Status: concrete proposal for independent contract review before implementation.
Baseline: pushed `6d751cf78557cdcbd7280984f9abaf849447f027`, clean canonical iCloud
checkout, branch `codex/d5a-crcl-normalization`. D050. The user resumed and asked
for the next major implementation step; stop after D5l, before multi-company work.
No application/source mutation or acquisition precedes this proposal.

## Objective and feasibility

Close the exact 47 retained-inventory candidate body gaps, review accounting editions and
business applicability, and publish only the additional source-only metrics/history
that existing concepts, S3, S5 and real-v2 contracts genuinely support. A blocked
metric is a valid result. Existing six D5k definitions and all old snapshots remain
immutable. No quote/provider/valuation/sector/scheduler/multi-company expansion.

| Candidate | Starting evidence | Gate to resolve |
| --- | --- | --- |
| FY2025 revenue growth | D5k retained FY2024/FY2025 total revenue incl. reserve income | Earlier financial/event history, matching annual scope and edition; distinguish reserve yield/volume from organic growth |
| FY2025 consolidated ROA | Consolidated ProfitLoss plus directly reported opening/closing total assets | Opening balance history, consolidated/NCI scope, holder reserve assets; never substitute parent net income or adjust away reserves |
| Reported gross margin | No selected reported gross-profit operand | Direct reported complete-scope subtotal and meaning; do not rename RLDC or subtract distribution costs |
| Derived gross margin | No selected complete cost-of-revenue operand | Exact existing concept semantics, complete cost classification and period; no unrelated-tag sums |
| History/trends | FY2023/2024 comparative rows and existing S5 history/trend contracts | Full eligible period/edition evidence and immutable compatible historical snapshots; requested 3/5/10 years is not evidence of availability |

## Exact source scope

Full read-only audit of D5k inventory capture
`01551860-7c36-46e5-b31c-9b8fa232ae81`, body SHA-256
`69a7a0884e0e2fda9600481d967b498368da68b21d9a8be1539be59fc37bbaf7`,
finds a finite **47-body candidate roster: 39 HTML and eight PDF resources**.
The exact form/date/accession/resource/retention/MIME/relevance matrix and all
11 request groups are [inventory-scope.json](inventory-scope.json), SHA-256
`754f225b924f52ac9d0bce9761ff2808627bda465aaeb2e59372e9fa93700d22`. This hash and exact roster are part of the proposal.
All 47 are absent from the governed retained-capture lineage. Actual MIME and
substantive relevance are unknown until capture; extensions are only planned
representations. Do not infer irrelevance from form metadata.

The original nine-body D5k gap list covered a narrower 2025 window. Full inventory
adds ten 2023–24 draft/correspondence bodies, eighteen 2021–22 S-4/425/RW bodies,
seven 2025 CORRESP bodies, and S-1MEF/S-3ASR/ARS. Excluding known unreviewed editions
or correspondence would leave history applicability unresolved. This revision
replaces that incomplete nine-body acquisition scope before any commit or dispatch.

### Reviewed form-scope policy

Include DRS, DRS/A, DRSLTR, UPLOAD and CORRESP for draft financial editions and
regulator/issuer accounting correspondence; S-4/S-4A,425 and RW for the earlier
transaction registration, comparative presentations and withdrawal context;
S-1MEF and S-3ASR for registration/incorporation context; ARS for the annual report.
Each is a **candidate relevance class**, not proof of accounting effect. Existing
retained 10-K/10-KA/10-Q/8-K/S-1/S-1A/prospectus bodies and reviewed exhibits remain
in the reconciliation set. No global all-filings completeness claim is permitted.

Ownership/beneficial-owner reports (3/4/144 and amendments, Schedule 13G variants),
Form D offering notices, compensation registration S-8, proxy/solicitation
DEF14A/DEFA14A and administrative EFFECT/CERT/8-A12B are outside this milestone's
selected financial-statement/registration-correspondence scope. Their forms serve
ownership, compensation, governance, offering/registration administration rather
than establishing the selected audited statement editions. This is a bounded
review policy, **not a finding that their unretained bodies have no financial
relevance**. Any included body referencing an affected-line correction, non-reliance
or necessary evidence in an excluded form creates an exact blocker requiring a
new reviewed scope; never ignore such a reference. Multi-company, governance,
compensation and corporate-action completeness remain unproved.

### Governed request groups and budgets

| Groups | Inventory interval | Body count | Mandatory pair per request |
| --- | --- | --- | --- |
|1–4|2021-01-01 through2022-12-31|5+5+5+3 HTML|Facts and Submissions|
|5–6|2023-01-01 through2024-12-31|5+5, mixed exact HTML/PDF roster|Facts and Submissions|
|7–10|2025-01-01 through2026-10-16|5+5+5+4, mixed exact HTML/PDF roster|Facts and Submissions|
|11|2025-01-01 through2026-10-16|zero; fresh post-body pair|Facts and Submissions|

Every interval is at most 730 days; no request exceeds five filing bodies. Exact
canonical grouping/order is in the pinned matrix. Each uses refresh and one
logical attempt; transport remains at most three actual dispatches per resource.
Total 69 logical resources and at most 207 actual HTTP dispatches across the full
planned run; no implicit retry run. A 45-minute acquisition-run wall deadline stops
before the next resource and caps each active lease/fetch to remaining run time.
Unavailable/expired budget leaves an immutable partial artifact with missing keys.
Actual retrieval/completion times are never replaced by proposal/file dates.
If execution crosses the pinned end date, retain the bounded interval and expose
the limitation; do not silently move it. Final pair dispatch follows completion
of all planned bodies. Earlier interval roots are retained and compared against
the final full root; any missing advertised history becomes a blocker.

Diff all newly retained Facts/Submissions against D5i/D5k lineage. New relevant
filings, history documents, changed identities or affected amounts remain explicit
blockers requiring a separately stated scope before any further acquisition.
Even unchanged content is a new observed vintage, not original September knowledge.
The final eligibility cutoff is the exact minimum complete observation supported by
the post-body pair, with capture completion cutoff after both; filing-date coverage
is retrospective and must not imply unobserved intraday/full-day completeness.

## Narrow additive acquisition contract

Add BootstrapPlan version `sec-crcl-history-bootstrap-v2` with unchanged JSON keys.
V1 parsing, canonicalization, limits and accepted resources remain unchanged.
V2 is CRCL CIK 0001876042 only; besides the mandatory pair it allows only the 47
exact keys in the pinned matrix, zero history keys and no more than five bodies. A pair-only V2
plan is valid. Unknown versions, other CIKs/accessions/names, encoded traversal,
query/fragment/absolute URLs, duplicate resources and over-limit sets fail closed.
SecResource's existing filing-document kind gains only the eight exact PDF tuples;
there is no general `.pdf` extension allowance, new resource kind or arbitrary URL.
Ordinary source plans cannot dispatch PDFs: only the persisted V2 bootstrap can.

Add sequential migration `0014_crcl_history_documents` after 0013. No new tables,
columns, enums, public endpoints, numeric concepts or missingness states. Freeze
0013 and every previous migration. Preserve the V1 SQL validator under a versioned
helper and dispatch the existing `workflow_valid_bootstrap_plan` signature to V1
or the exact V2 validator. Preserve existing SQL resource validation in a helper;
`market_sec_resource` additionally permits only canonical URLs for the eight keys
and matching registered SEC source/policy. Extend
`workflow_bootstrap_attempt_guard` to reject PDF attempts unless the request is
V2 source_bootstrap with the exact pinned issuer/resource/policy. Existing enqueue,
lease, fence, result, capture and policy ownership checks remain in force. No
weakened v1 acceptance, privilege widening or direct runtime insert grants.
Downgrade refuses while any V2 request exists; an empty downgrade restores frozen
prior functions and removes only the new helpers. Direct-SQL bypass tests are
required; Python validation alone does not establish the boundary.

## Raw PDF handling and passive review

Keep the existing SEC source/policy: its retained public-filing/government-document
scope already covers these SEC archive correspondence bodies. Record this exact
scope interpretation and current official access references; do not rewrite the
old policy row/artifact or claim rights to other document hosts. Existing actual
contact, shared Redis 5 requests/sec, hard 10/sec cap, retries/cooldowns, W1 fences,
canonical HTTPS hosts and redirect restrictions apply unchanged.

For these PDFs, cap both wire and decoded entity bytes at 8 MiB (or a lower configured
document cap); existing HTML 64 MiB and JSON 32 MiB limits remain unchanged. Stream,
HTTP-decode once, hash/count and gzip-archive the exact entity before interpretation.
Complete malformed/error bodies remain retained evidence, not eligible document
content. Over-limit/partial transfers retain existing failure metadata, never a
successful complete capture. Check normalized content type `application/pdf`,
`%PDF-` signature and terminal EOF before marking the PDF acquisition ready;
wrong MIME, HTML error page, truncation and malformed structure remain explicit
gaps. Reuse/304/replay must revalidate the exact archived bytes and retain original
time; a failed representation cannot satisfy document review by merely returning 200.

PDF review is offline and passive. No JavaScript/actions, attachment extraction,
links/network, embedded files or external references are executed. A separate
bounded subprocess uses the available pinned pypdf 6.10.0 runtime for structural/text
inspection (timeout 30 seconds, address-space 512 MiB, max 100 pages / 2 MiB text for correspondence;
exact ARS max 400 pages / 8 MiB text),
rejects encrypted/active/embedded-file documents for automatic eligibility, and
records parser version, input hash, page count, per-page text hash and exact page
locators. Parser unavailability/error/resource exhaustion is a deterministic blocked
review, never an empty-success document. No PDF values become normalized facts.
Render only with Poppler 26.05.0 (`pdfinfo` and `pdftoppm` version checks), PNG,
100 DPI, RGB 8-bit, MediaBox (no `-cropbox`, resizing or fit-to-page), text/vector
antialiasing enabled, one page per process (`-f N -l N -singlefile -png -r 100`).
Set `LC_ALL=C`, `TZ=UTC`; record exact command/settings, binary SHA-256, version,
input hash and each PNG hash. Validate finite positive MediaBox and CropBox,
CropBox contained within MediaBox, each box dimension at most 1440 points; expected
render width/height at most 2000 pixels and product at most 4 million. Reject oversized
page boxes before rendering; never silently shrink evidence. Pin 512 MiB address
space,8 MiB output-file limit,5 seconds CPU / 15 seconds wall per page. The seven
correspondence PDFs retain at most 100 pages,120 seconds total wall and64 MiB aggregate
PNG bytes. Only exact ARS resource
`filing_document/0001876042/0001876042-26-000116/a2025annualreport0331.pdf`
permits at most 400 pages,300 seconds total wall and256 MiB aggregate PNG bytes;
all per-page/byte/memory limits remain the same. Across all eight PDFs cap rendered
output at 704 MiB and total rendering wall at 1140 seconds. No automatic limit raising. Check
actual PNG dimensions/bytes after each page; stop at the first violated limit and
do not mark the document fully reviewed. Rendering uses only verified local bytes,
no URLs, attachments, scripts or delegated external commands from the document.

Version mismatch/unavailable tool, invalid/oversized page box, encrypted or active
content, text/page/output limit, parser/render timeout or memory exhaustion,
nonzero exit, missing/invalid PNG and incomplete visual coverage each produce a
stable named blocked reason with the exact input hash and completed-page roster.
They never become empty-success or inferred irrelevance. Tests include gigantic
MediaBox/CropBox, nonfinite/reversed boxes, oversized PNG/output, and a small
compressed-image PDF whose decoded image exhausts the resource limit; simulated
worker limit failures are supplemented by a bounded real subprocess regression.
Record rendered-page hashes and review coverage. Image-only or ambiguous passages
remain unconfirmed; no OCR numeric substitution. Preserve the PDF bytes unchanged.
The interactive UI displays escaped text/provenance, not embedded active PDFs.

## Accounting and publication decisions

Review full new HTML/PDF bodies plus all retained relevant periodic, registration,
amendment, earnings and exhibit bodies for corrections, non-reliance, restatements,
reclassifications, auditor/control disclosures and references to other necessary
editions. Record per-body/per-affected-concept dispositions, exact quotes/locators,
period/entity/accounting basis and unresolved references. Keywords alone never
prove absence. Reconcile total revenue, consolidated net income, opening/closing
assets and any candidate gross-profit/cost line with original contexts, units,
scale/sign/precision and all retained Facts vintages. Distinguish public retrospective
content from original application knowledge and confidential draft dates.

Only exact directly reported operands and reviewed mappings use existing Concept
members. Do not sum temporary equity into permanent equity or hide a failed balance
identity; earlier periods with incompatible identity semantics remain blocked for
publication under the current contract. Review separately whether FY2025 ROA can
use a directly supported opening asset operand without making an unsupported
full opening-balance identity assertion. A required contract change becomes a
concrete blocker, not an implicit relaxation.

Prepare an immutable S3 batch only if required inventory/event/edition/accounting
coverage actually passes. Pin hashes and exact readback selections for independent
standards/spec/numeric review before live S3 writes. After source publication,
freeze real-v2 candidates separately for each supported period, with unchanged
formula engine, seven statuses, currency/period checks and exact null reasons.
Historical samples/trend inputs must satisfy existing compatibility and completeness
rules; no partial-window percentile or invented trend. Independent plausible-wrong
review must clear exact pins before live S6. Preserve D5j and both D5k snapshots.
Acquisition-contract code changes legitimately change the installed engine revision;
old snapshots remain readable unchanged and cannot be republished as a new engine
by editing their original manifests. Verify old hashes/rows directly; use new pinned
engine candidates only for new publications.

## Sequential gates and acceptance

1. Commit proposal; independent standards/spec review of this concrete acquisition
   contract before implementation. User's continuation authorizes this dedicated
   contract step; no repeat user permission for the already-scoped work.
2. Red→green contract/transport/parser/adversarial SQL tests on disposable runtimes.
   Stage SQL/Python/policy tests and an exact application 0013→0014 plan with backup,
   row/function hashes, expected objects and recovery. No live migration/acquisition
   until explicit reviewer clearance.
3. Acquire only pinned groups/pair; deterministic unavailable/partial artifacts;
   immutable preservation baseline before writes and crash/replay recovery.
4. Review evidence, then separately clear exact S3 and S6 numeric publication pins.
5. Extend analysis UI with provenance for every number, exact history coverage,
   scope-specific nulls and honest multi-company readiness. No frontend finance math.
6. Focused tests, full make check, production build, browser desktop/mobile/keyboard,
   local GET-only requests and corruption recovery; independent final staged reviews;
   mandatory hooks, non-force branch push, remote HEAD/clean tree/preview verification.
   Stop at the D5l major checkpoint; do not start multi-company rollout.

Adversarial coverage includes unlisted/cross-issuer PDFs and direct-SQL attempts,
V1 PDF rejection, malformed/duplicate/over-limit plans, MIME/signature/truncation,
compressed oversized bodies, redirect/lease/policy failures, corrupt replay/304,
parser timeout/encryption/active content/empty pages, partial acquisitions, changed
Facts/filing editions, NCI vs parent numerator, wrong opening date, reserve scope,
temporary equity, plausible wrong gross-cost substitution and incompatible history.

Official access policy checked 2026-10-16: [SEC access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
and [SEC privacy/security](https://www.sec.gov/about/privacy-information).
These policy reads are not governed financial captures or proof of filing content.
