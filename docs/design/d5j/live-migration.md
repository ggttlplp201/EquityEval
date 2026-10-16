# D5j application migration review packet

Status: staged for independent live-migration and revised numeric review. Nothing
in this packet applies a migration or publishes a metric.

The owned application cluster is PostgreSQL 16.14 / Timescale 2.28.1, local port
5433. `app_postgres.configuration`, `guard` and `verify` passed. Read-only SQL
confirms current head `0010_filing_scheduler`, 53 public tables, and zero existing
v1 fundamentals/valuation functions. Their tables do not yet exist; this is an
observed precondition, not an assumption that their migrations already ran.
Runtime credentials remain scoped; no DSN/password is recorded here.

The exact path is 0010 → immutable 0011_fundamentals_publication → immutable
0012_valuation_publication → reviewed 0013_real_fundamentals. The checked plan
`docs/research/crcl-real-migration-plan-2026-10-15-r3.json` pins all four file hashes,
the offline upgrade SQL hash, all 50 added table names, the 53-table before-row
hash sets, and the revised candidate file hash. Original 0010–0012 bytes match
HEAD. Existing 0011/0012 add their synthetic-only storage/functions and built-in
model/policy definitions; they do not run synthetic or real calculations. 0013
adds real companion storage and the reviewed dedicated W1 routing/constraints.
Expected head is 0013 and expected public table count is 103. No source, quote,
provider, security, scheduler, normalization, or old request data should change.
The only changed pre-existing row is the Alembic version marker.

After independent clearance, take an owner-only local custom-format `pg_dump`
backup in ignored `var/d5j/`, verify its archive listing and record its SHA-256.
Recheck the exact head, migration hashes and every pre-existing row hash before
calling the existing guarded `app_postgres.migrate` command. Alembic executes the
three revisions sequentially with PostgreSQL transactional DDL. Immediately
verify head, exact expected new table set, all prior rows (except version marker),
empty analysis/review/result tables, expected installed function privileges and
successful runtime-role readback. Compare v1 function definitions to a disposable
0013 database's definitions before any real review/publication. Record the before/
after audit and re-run D5i readback, preserving D5a flags and source lineage.

A failed transactional upgrade must leave 0010 and the prior rows intact; inspect
before retrying. Empty new tables can be downgraded through the existing guarded
migration path only if needed and separately reviewed. After a policy review,
request or result exists, downgrade deliberately refuses to discard that history;
recovery is a forward correction or restoration into a separate local cluster
from the backup, never destructive overwrite of retained application history.
No automatic rollback command is part of this packet.

The revised candidate is
`docs/research/crcl-fundamentals-preparation-2026-10-15-r3.json`:
manifest `1fa24dc52392e29aad1db306500db81b76f8ab9e3e6f8282496a02daaebc24e9`,
payload `4042d892477467e07c906091cb30e70aeb264ed9c1adb3df75e351828ffa23db`.
Evaluation is 2026-10-15T23:22:27.030481Z; source knowledge remains exactly
2026-10-15T21:59:05.195192Z. The original candidate is retained as superseded:
its operating-margin arithmetic was correct, but nine intentionally unreviewed
empty-operand entries were incorrectly labelled invalid. Real-v2 now emits those
slots as null/unsupported with metric-specific required-input reasons; coverage
is consistent. Supplied malformed operands, future profiles, unsupported
instrument bases and reviewed-applicability failures still use existing S5
validation. All v1 code remains unchanged.

Revised focused tests: 26 pass including status/coverage consistency, malformed
inputs, signed arithmetic, direct-SQL evidence omission/ownership, leases and
readback. Ruff and mypy pass. Full final checks/build/browser acceptance remain
required. Live numeric publication is separately held for explicit independent
plausible-but-wrong clearance of this exact revised packet after migration checks.

Revision 3 also carries exact missing operands and accounting/applicability review
requirements for every unresolved metric in both policy and public reasons.
Revision 2 is retained as superseded for insufficiently specific blocker wording.

The publication runner now durably writes an immutable intent/baseline before
any review/request mutation. If interrupted after database commit but before the
final audit file is written, rerun finds the committed snapshot by the same
idempotent request, replays its exact stored lease/stage/input identity, verifies
the original baseline and writes the recovered audit atomically. A disposable
commit-before-audit interruption test proves one request, one snapshot and the
same original before-row hashes survive recovery. No new request is substituted.

## Executed reviewed boundary

Explicit independent clearance was received for migration plan r3 and candidate
r3. Backup `var/d5j/pre-0013-2026-10-15.dump` was validated before sequential live
upgrade to 0013. Audit `docs/research/crcl-real-migration-2026-10-15.json` records
53-table preservation, 50 expected new tables, privileges and v1 function parity.
The separately cleared publication is recorded in
`docs/research/crcl-fundamentals-publication-2026-10-15.json`, with durable original
baseline in the adjacent publication-intent artifact. Exact replay/readback and
D5i/D5a preservation passed. Applied migrations and all superseded candidates stay
immutable; recovery is governed forward repair, not destructive rollback of history.
