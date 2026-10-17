# D5l live boundary review packet

Status: the exact pre-live packet below passed independent review and was applied
on 2026-10-17. Acquisition completed with gaps; no normalization or metric
publication followed. See the D5l milestone and immutable migration/acquisition
audits for actual results. Proposal `dd2d4a9` is pushed.

The read-only preflight confirms application head `0013_real_fundamentals`, 103
public tables and 406 public functions. All D5k rows, three normalization batches,
three real snapshots and historical D5a flags/readback match the completed audit.
Before-row hash is
`a6f622af3595e30315a2761c8a100dac0c7a90fa71aa4d55febaa536de28ddc3`.
The exact complete baseline, function definitions/privileges and frozen migration
file hashes are in `docs/research/crcl-history-migration-plan-2026-10-16.json`.

Apply only sequential `0014_crcl_history_documents` after explicit clearance.
Its SHA-256 is
`1695900039c14e1f29061fd8639fb16fa9cd2b68ef13498db786a2e276c61dc6`;
offline upgrade SQL SHA-256 is
`5c8bd6897462ba33785c2456ff7f8eb990f5b5ce89c7c003d62b4982ed082958`.
There are no new tables/columns/enums/API shapes. Two private helpers preserve
frozen V1 validation; only the existing bootstrap validator, SEC resource validator
and bootstrap-attempt guard change. Existing privileges must remain identical;
new helpers grant no execution to PUBLIC or equity_runtime. All 0001–0013 bytes
remain unchanged. No normalization or metric is part of this migration.

Before applying, recheck every pinned file and baseline row/function hash. Take
an owner-only custom-format pg_dump under ignored `var/d5l/`; verify its archive
listing and retain its SHA-256. Use the existing guarded app_postgres migration
path against the owned application cluster, with transactional DDL. Afterward,
verify exact 0014 head, the same 103 tables, exactly two new helper functions,
three changed definitions, identical old privileges and all old rows except the
Alembic version marker. Re-read all three saved real snapshots and the D5a/D5i/D5k
selections. Persist an exclusive migration audit with before/after rows before
any acquisition.

A failed transaction must leave 0013 and all original rows intact. An empty 0014
can downgrade through its tested guard; once V2 intent exists downgrade refuses
to erase it. Recovery then requires reviewed forward correction or restoring the
backup to a separate owned local cluster. Never overwrite retained history.

After separate acquisition clearance, `capture_crcl_history` consumes only the
proposal's SHA-bound 47-body/11-group roster: 69 logical resources, at most 207
HTTP dispatches, one logical attempt per group and a 45-minute monotonic budget.
Every renewed fetch lease is floored to remaining budget; expired budgets cannot
start a resource. Final pair follows all ten body groups. An exclusive original
intent/baseline precedes mutation; failures retain partial database attempt and
capture identities. Existing attempts are not implicitly retried. Missing-resource
labels mean no verified capture in the audit, not proof that an interrupted process
never retained bytes. Actual retrieval timestamps and the fixed filing-date window
remain distinct.

## Observed PDF runtime gate

The actual macOS host rejects both finite hard/soft and finite-soft/infinite-hard
`RLIMIT_AS` settings at 512 MiB with `ValueError: current limit exceeds maximum
limit`. Docker, Podman, Colima, Lima and QEMU commands are unavailable. Production
inspection returns `pdf_limits_unavailable` before importing the PDF parser or
reading document structure. Rendering also requires the same cap; there is no
uncapped fallback. Synthetic parser-rule unit tests explicitly bypass OS limits
only for tiny generated test fixtures and never establish evidence eligibility.

Consequently, retaining a PDF does not complete its substantive/visual review on
this host. Any unavailable PDF review leaves exact accounting/history gates
unresolved and new metrics null. A different enforcement mechanism would require
a proposal amendment and independent review; it is not silently substituted.
Full-suite/build/browser acceptance and final evidence/UI work follow the live
boundary only if independently cleared. No source or metric publication is cleared
by this packet itself.


## Focused recovery and PDF review fixes

The `recover` acquisition action reads the exclusive original intent, verifies its
migration baseline/hash, exact workspace/issuer/security plans and committed
request parameters, then reconstructs request/attempt/capture and completion
manifest evidence without claiming, renewing, enqueueing or dispatching. An
interrupted in-progress dispatch remains unknown/incomplete; a committed capture
is reused by identity. Missing/corrupt archive evidence cannot clear readiness.
The original before-row baseline is preserved, and final audit publication is
exclusive and repeatable. Disposable tests cover committed capture before audit,
interrupted dispatch, changed intent, repeated readback and zero additional HTTP.

PNG replay verifies and reuses identical existing bytes, rejects mismatches and
retains the completed-page roster. Validation checks CRCs, IEND, bounded zlib
pixel data, dimensions and RGB format. Regressions include truncated/oversized
PNG files, oversized geometry, process failure, parser/render timeout, encrypted
PDFs and page/text limits. A tiny compressed-image fixture with huge declared
image dimensions is blocked by the actual host cap gate before parsing/rendering.
A real bounded subprocess attempting a 768 MiB allocation exits at the unavailable
cap gate without running the payload. This proves fail-closed host behavior; it
does **not** prove Poppler memory exhaustion handling on a compatible enforcing
host. Real compressed-image/Poppler exhaustion and successful bounded rendering
remain unverifiable here until the exact reviewed runtime is available. Synthetic
fault tests exercise those error/result paths without changing that limitation.
