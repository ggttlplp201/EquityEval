# D5a — First governed CRCL normalization and PIT read-back

Status: concrete proposal pinned before implementation or application writes.
Authorization: next-phase continuation relayed by the milestone coordinator on
2026-09-30. Baseline ff4cfa32dffab9505a1c840ed7ac33cb3df2e7a8, corrected S8d.
Branch: codex/d5a-crcl-normalization. No earlier D5a milestone/name exists.
D039 records this bounded reuse of accepted S3 contracts, not a new shared contract.

## Read-only audit

The canonical CloudDocs application runtime is owned PG16.14/Timescale2.28.1 on
loopback 5433, migration 0010_filing_scheduler. Inspection and D3c archive replay
verified one source/policy/issuer/security, 12 captures, 14 attempts, five requests,
zero mapping revisions, normalization batches, quote identifiers and memberships.
Repeatable-read/read-only before/after table hashes match. No source was fetched.
Existing S6/S7 migrations are not needed for S3 normalization and will not be
applied as a side effect. The stale Documents checkout is untouched.

Reuse the exact D3c audit (SHA256
4b1bff12335faf50b67192f92f0f04a5f7d8d1ff8738644f037acf8036836dac) and five governed
captures. Verify body hashes/counts, policy, immutable request/result/manifest,
issuer/security and successful attempt lineage using existing D3d checks:

| Resource | Capture ID | SHA256 |
| --- | --- | --- |
| Company Facts | 923841dc-5a9b-44c4-b59b-ddf7e567fc3b | f7139545b482a7b31520225bc155cb41241b82f004eb8fbca55f4ab66d1426af |
| Submissions | 0e93340d-a10c-40eb-b463-047c23be58bf | c4f43a9e2582ab88f8cfa1d8f3527bfbf515770e3c33766e21629845c16026a3 |
| Annual original | 7cdba2c5-76a0-453d-b8fb-cae4b6e77809 | e535360770ac9230b871b4a4f9ab74336f790aa089f3dd0a078be83e517bbd4c |
| Annual amendment | a091bf37-ac2e-4ba8-8500-77c59e0da24a | 10419022aa21286368e02b193c224af7ad5e059f828ee60c436128c344f51325 |
| Quarterly original | e58aaf2d-ba12-417e-9b2d-872df7a10610 | 81d3190308738e630e9424cc29897d492e943912525ab5f5b03612a160b60cb6 |

All captures completed 2026-09-21; the last completed at
2026-09-21T17:07:36.842185+00:00, the explicit retrieval cutoff. Preserve each
individual requested/fetched/completed time; none becomes today's timestamp.
Submissions supplies genuine acceptance times: original annual 2026-03-09
12:36:51Z, amendment 2026-07-13 20:40:02Z, quarterly 2026-08-05 13:02:57Z.
Date-only filed selection remains distinct from those intraday source times.

The original annual accession 0001876042-26-000062 covers 2025-01-01 through
2025-12-31. Retained Item 8 audit opinion explicitly covers Circle's consolidated
statements under US GAAP. Existing S1/S3 reviewed exact mapping and D2/D3b checks
support only the two selected concepts below for this slice:

- revenue: reported Revenues = 2,746,642,000 USD;
- operating_income: reported OperatingIncomeLoss = -96,435,000 USD.

Cross-check Company Facts with the retained original document's exact c-1
consolidated context, USD unit, empty dimensions, scale 3, decimals -3 and sign.
Preserve original literal text, all equivalent duplicates, scopes and transform
chains. Company Facts lacks original XBRL context/precision; keep those unknown
in its normalized observations and retain separate filing precision evidence.
Do not infer precision from numeric digits or claim complete document extraction
(the established whole-document extractor has 249 issues).

The annual amendment's retained Explanatory Note adds separate Circle Reserve
Fund April-2026 statements and expressly does not otherwise restate the original
report. Keep its own accession/form/acceptance/capture and review evidence. Do
not create a restatement edge merely from 10-K/A. Q2 remains a separate period
without an extrapolated FY2025 mapping. Both are retained review context, not
substituted sources for the two original annual amounts.

## Implementation boundary

1. Add a small local archived-replay/preparation command using LocalArchive,
   parse_submissions/assemble_inventory, reviewed_cohort_rules,
   normalize_verified_bytes and the existing filing extractor. No alternate
   parser, arithmetic, test seed, source fetch or invented source identity.
2. Produce a pinned review artifact and input/output hashes before publication.
   Materialize exactly one idempotent owner-reviewed mapping revision for these
   existing exact rules; record the actual approval time, never backdate it.
   Verify the registered identities and policy again before a write. Mapping
   approval is distinct from publication; it must never imply a batch succeeded.
3. Reuse publish_bundle's supported archived-replay path on an idle runtime
   connection. No new W1 request, quote, lease bypass for live work, migration,
   shared vocabulary/API/status or alternative fact store. One bounded atomic
   normalization publication, followed by exact idempotent replay. Preserve its
   genuine batch ID/publication timestamp and all prior row identities/hashes.
4. Read the resulting rows using existing PitQuery/read_statement. Pin inclusive
   filed cutoff 2026-03-09 and the real September retrieval cutoff; label this a
   filed-date reconstruction, never data available to this app in March. Verify
   the before-filing gap and original/earliest-available semantics separately.
   Inventory and event completeness remain unknown/incomplete for financial
   history, even though advertised Submissions-document coverage is complete.
   Preserve inventory_history_incomplete and event_history_incomplete, any
   mapping/scope/coverage/accounting/applicability flags and usable_for_valuation=false.
5. A compact checked read-only artifact/page, linked from Financial normalization
   in the real pipeline, shows genuine counts, facts, dates, source identity,
   PIT selection, flags and pending S5/S6 gates. Preserve original dated D2–D4
   artifacts and distinguish the new application audit from earlier snapshots.
   No live browser DB/provider access, finance math or fictional value fallback.
   Ordinary missing fields show N/A; technical reasons remain inspectable.

If archive, identity, policy, exact mapping/coverage or owned runtime prerequisites
fail, stop the write and implement verified readiness/blocker evidence instead.
Do not modify shared contracts to force success. No quote registration or currency
inference, price-dependent ratio, valuation, sector comparison, recommendation,
provider activation, source refresh or unattended scheduler. Stop before real S5/S6
analysis publication, even if these two observations are successfully normalized.

## Acceptance and red-first plan

- Pure preparation tests before code: exact two-concept/accession/period/scope/unit
  binding; corrupted/missing bytes and wrong issuer; duplicate/ambiguous metadata;
  source context/dimensions/sign/scale and precision disagreement; genuine zero
  versus missing; no unsupported quarter mapping; amendment not restatement.
- Disposable database tests use clearly labelled isolated test evidence only;
  production commands cannot accept those identities or import test seed code.
  Test one publication plus identical/concurrent reuse, mapping/hash drift,
  wrong issuer/accession/context/unit/period, stale/late/out-of-order evidence,
  transaction failure/rollback and immutable original/amended lineage. Reuse
  existing S3/PIT integration coverage rather than duplicating financial logic.
- Real preflight uses repeatable-read/read-only application snapshots. Record exact
  before/after counts and original-row preservation. On eligible publication,
  verify real read-back, earlier cutoff gap, repeated batch reuse and no new fetch,
  quote, membership, ordinary request, engine result or changed prior capture.
- Deterministic sanitized export with --check; optional current application
  comparison must not mutate. No credentials/contact/local blob paths in UI.
  Inspect every visible amount/count/date through exact evidence; <=4 decimal
  display, unit markers, N/A, keyboard/focus, GET-only network and recoverable states.
  Browser at 320/390/768/1440 plus existing pilot/pipeline and relevant saved UI
  regressions; inspect screenshots and production build.
- Independent spec and plausible-wrong-number/standards reviews; focused Python
  and Node tests, lint/types/exports, full/core/golden through mandatory hooks.
  Update roadmap/manual/milestone with exact genuine counts/blockers. Preserve
  earlier refs/fixtures, annotate only a verified implementation checkpoint, leave
  the tree clean and stop at D5a. Proposal must be committed before implementation
  or application mutation; no hook bypass.
