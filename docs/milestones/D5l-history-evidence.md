# D5l — CRCL history evidence checkpoint

Status: implementation and governed acquisition checkpoint complete with gaps;
final validation and independent reviews passed. No new normalization/history/metric publication. The user asked
for the next major CRCL-only step and a stop before multi-company rollout.
Proposal `dd2d4a9`, D050; exact 47-body/11-group scope is immutable.

## Result and limits

Reviewed migration 0014 is applied. All 103 prior public-table row sets except the
Alembic marker, old function privileges, D5a/D5i/D5k selections and three real
snapshot hashes were verified. Two private helpers were added and three functions
changed. The exclusive migration audit and owner-only backup are retained.
An initial readback wrapper incorrectly opened a transaction around PIT reads;
verification was recovered read-only from the original baseline, without applying
the migration again or changing prior financial rows.

Acquisition ran 2026-10-17T08:09:07.949503Z–08:09:25.331164Z. Groups 1–9 completed;
group 10 completed with `body_limit`. Exactly 46 bodies are retained: 39 text/html
and seven application/pdf. Ten mandatory Facts/Submissions pairs add 20 captures.
The ARS `0001876042-26-000116/a2025annualreport0331.pdf` exceeded the exact reviewed
8 MiB wire/entity cap. Attempt `0d9a8154-e428-4c2e-8e24-3f538b9a5750` retained HTTP
200/application/pdf headers but no complete capture or quarantine. Content-Length
and observed byte counters were not persisted, so exact total size and which byte
limit fired are unknown. Temporary streaming bytes are cleaned on failure; this
is not proof that no temporary bytes were written. Its archive directory is empty.
No retry occurred. Group 11 correctly remained undispatched.

All seven retained PDFs return `pdf_limits_unavailable` before parsing: macOS
rejects the required 512 MiB RLIMIT_AS. No uncapped parser/render fallback ran.
Their content and references remain unreviewed. Docker/Podman/Lima/QEMU are
unavailable; successful bounded rendering and real Poppler exhaustion are not
verified on this host. The initial screening artifact remains preserved; r2 adds
specific accounting findings and pins the PDF runtime result.

All retained HTML text and links are indexed with hash-bound text locators. This
is screening and targeted content review, **not complete accounting clearance**
of every edition. Material findings include:

- January 2025 correspondence quotes an SEC objection to Reserve Fund accounting;
  the issuer analysis is redacted. February 2025 DRS/A reports retrospective ASC825
  fair-value-option treatment (otherwise equity method), with additional disclosure
  and no stated consolidated-statement effect.
- The same draft explicitly adopts SAB122 retrospectively for earlier safeguarding
  assets/liabilities and states no operating-income/net-income/equity effect.
  Earlier versus later asset editions therefore cannot be blended into ROA history.
- April correspondence clarifies corporate-held USDC cash-flow/balance presentation
  and adds audited Reserve Fund statements. Fund and Circle scopes remain separate.
- April preliminary Q1 ranges explicitly lack auditor review and finalized closing.
- Earlier S-4 bodies mix Concord restatements, Circle history and proposed combined
  pro-forma figures. Withdrawal says the transaction did not proceed; a Concord
  restatement is not automatically a Circle correction.
- S-3ASR incorporates retained periodic/event filings plus excluded security/legal
  documents. Unretained references are indexed, not presumed irrelevant or fetched.

Ten Facts bodies match the prior retained hash; ten Submissions roots match the
prior inventory (438 recent records, no advertised history). They precede the last
body attempt and do not substitute for the withheld final pair. Filing scope remains
bounded through October 16; actual October 17 retrieval is not September knowledge,
full-day October 16 coverage, or a new eligible observation cutoff.

## Application state and next gate

142 captures, 145 fetch attempts, 31 requests (26 bootstrap, two monitor, three
real fundamentals), three normalization batches, fourteen selected facts, three
real snapshots, six supported D5k definitions, zero provider quote bindings.
No new facts or metrics are published. Gross margin lacks reviewed complete-scope
operands/applicability; growth/ROA/history retain PDF, final-observation and
selected-edition/accounting gates. Annual growth is not a quarterly trend.

[Amendment candidate](../design/d5l/remaining-boundary.md) is a concrete next
review boundary, not authorization to retry, raise limits or substitute a runtime.
Stop before multi-company rollout; this checkpoint does not make it ready.

## Validation

| Check | Result |
| --- | --- |
| Independent pre-live standards/spec reviews | Passed exact migration/acquisition design |
| Pre-live full make check | 1,901 passed; 512 core; 110 golden; two existing warnings |
| Production build before live boundary | Passed |
| SQL/PDF/recovery adversarial tests | Passed; actual host fail-closed limits documented |
| Live migration/acquisition preservation | Passed; exact immutable audits retained |
| New blocked review missing/changed-evidence tests | Three passed; exact artifact replay and corruption recovery passed |
| Final full/build/browser and staged reviews | Passed: 1,904 full tests, 512 core, 110 golden; production build; 67 browser checks; standards/spec/numeric reviews pass for blocked checkpoint |
| Completion synchronization | Mandatory hooks on final implementation commit, non-force branch push and remote verification; exact commit recorded in Git history and final report. Preview: http://127.0.0.1:3103/development/pilot/analysis |
