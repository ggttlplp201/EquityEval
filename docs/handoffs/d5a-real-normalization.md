# D5a handoff — real CRCL source normalization

Canonical repository:
`/Users/leon/Library/Mobile Documents/com~apple~CloudDocs/Development/equityEval`.
Do not use the stale Documents/ChatGPT checkout.

Branch: `codex/d5a-crcl-normalization`; proposal commit `24bd2ae`.
Recovery tag: `milestone/d5a-crcl-normalization` (created only after final gates).
Use the [milestone](../milestones/D5a-crcl-normalization.md) for exact validation
and the [publication audit](../research/crcl-normalization-2026-09-30.json) for the
real database identity/counts/row-preservation evidence.

The application now contains one approved mapping and one real published S3 batch,
`923458e4-242d-4731-9f57-9fd6779d7e9a`. Two selected annual CRCL facts are available
with retained flags. Source counts remain 12 captures, 14 fetch attempts and five
analysis requests; the batch itself binds only D3c's five governed captures.
No source refresh, quote registration, watchlist addition or downstream financial
analysis was performed. The owned runtime stays at migration 0010. D4b remains
paused; no background service was started.

Read-only verification:

```sh
.venv/bin/python scripts/project_python.py -m scripts.export_crcl_normalization --check --verify-application
```

`publish_crcl_normalization publish` is intentionally limited to the pinned D5a
input/output hashes. Repeating it reuses this batch, without adding a request or
new source attempt. Keep owner mapping approval separate from runtime publication.
Use the existing project-local PYTHONPATH workaround if iCloud re-hides the strict
editable pointer between launcher and interpreter; do not change Python globally.

The new UI is `/development/pilot/normalization`, reached through Financial
normalization in the pipeline. Its server loader checks a deterministic local
artifact; the browser never accesses the DB or providers. The original D2–D4
snapshots and fictional workspaces remain unchanged. Preserve their dated meaning.
The manual is `docs/user-manual/real-normalization.md` and `/help#real-normalization`.

Stop here before real S5/S6 publication. The next review must identify the additional
financial/event-history coverage, exact periods and applicability/accounting/source
prerequisites required for real metrics. Two selected amounts and an audited source
do not make a complete income statement, complete history, price ratio, company
valuation or sector cohort. Preserve unknown Company Facts precision separately
from original-filing scale/decimals and do not turn a 10-K/A into a restatement edge.

Before further work, inspect the milestone status and verify the recovery tag
resolves to its tested implementation. Keep earlier refs and artifacts immutable.


Coordinator correction: the D5a tag is explicitly authorized to move to the verified
corrective commit. Preserve the initial `8ad2fbf` commit in history. Corrected source
chains distinguish numeric observations, independent precision and filing metadata
from non-PIT review context. Before-filing details must never expose later literals
or precision. Mapping approver and scope are mandatory for replay and standalone
verify. See the milestone's corrective section and separate provenance audit.
