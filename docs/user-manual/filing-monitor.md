# SEC filing monitor (development preview)

Open the local **Real-data pilot → Inspect CRCL’s application pipeline** link.
The **SEC filing monitor** section shows a saved, real filing check. It does not
poll while the page is open. Recurring monitoring and automatic analysis refresh
are later milestones; the News view's stock-news/macro monitoring remains separate.

Read the outcome and check-completion time first. Expand **scoped filings at the
cutoff** for each accession, form, reporting period, acceptance time and archived
source evidence. Expand the baseline/response disclosure to trace the comparison
back to its request, original captures, new HTTP attempt and manifest hashes.
The current saved totals include acquisition requests and filing checks separately.
The earlier acquisition checkpoint totals remain visible and dated.

| Term / result | Meaning |
| --- | --- |
| Baseline | The exact reviewed earlier inventory used for comparison. It is an approved acquisition seed or a completed, eligible prior monitor result. |
| Filed-date window | Inclusive filing dates considered in this comparison. It is not financial-history coverage. |
| Acceptance cutoff | Only scoped filings with verified acceptance timestamps at or before this instant can enter the comparison. It does not establish when a subsequently retrieved payload was publicly known. |
| Checked at | Completion of the actual recorded fetch attempt, separate from the acceptance cutoff. |
| Capture time | When an immutable source representation was retrieved. An unchanged-body response can reuse that representation without changing its old timestamp. |
| No change | Both advertised inventories are complete for the pinned scope, and their scoped accession/metadata sets match. It does not mean the company's business or all its news is unchanged. |
| New filing | A previously absent accession for a supported 10-Q or 10-K is present before the cutoff. A late or backdated filing can still be detected. |
| Amendment | A separate 10-Q/A or 10-K/A edition. This alone does not establish an accounting restatement or a non-reliance event. |
| Incomplete | Missing history, unverified acceptance, duplicate/disappearing accessions, changed existing metadata or malformed source data prevents an eligible comparison. |
| Error | Acquisition or archive verification failed. It is not a no-change result. |
| Eligible baseline | This complete discovery result may be used in a later comparison with the same reviewed scope. It is not financial-analysis readiness. |
| HTTP 200 / 304 | A 200 response contains a body, which is retained even if identical. A valid conditional 304 confirms reuse of a verified earlier representation without supplying another body. |

The downstream section explains why a detected filing has not started analysis.
D4a does not register a quote, add watchlist membership, normalize financials or
publish ratios/valuations. Missing inputs stay missing.

## Operator: one explicit check

Use the canonical repository and its separate application PostgreSQL/Redis stores.
The commands below use existing configured SEC contact/policy settings. They do
not acquire credentials, enable a provider or install an OS scheduler.

1. Preserve the pre-migration checkpoint with `history --output var/d4a-before.json`.
2. After the approved migration, `seed-plan --cutoff <explicit UTC instant>
   --output var/d4a-plan.json` registers only the exact approved D3c seed lineage.
   The seed cutoff is the original HTTP request start, not capture completion.
3. Run `poll --plan var/d4a-plan.json --key <stable logical check key>
   --before var/d4a-before.json --output <audit.json>`.
4. Use `inspect --request <request UUID> --before var/d4a-before.json
   --output <audit.json>` to verify the existing result without fetching.

Prefix each action with:

```sh
.venv/bin/python scripts/project_python.py -m scripts.monitor_crcl_filings
```

Reusing a terminal poll's exact plan/key returns its saved result without network
work. Changing a cutoff or baseline requires a new key. After a lease expires,
reclaiming the same request uses W1 fencing/recovery and replays already successful
observations. Terminal incomplete/error results cannot become the next baseline.

A prior-result plan pins its exact request/execution, manifest ID/hash, version and
cutoff; retain the same issuer, policy, forms and filed window. The initial D4a
window ends on 2026-09-21. Do not silently roll it forward: an expanded window or
changed scope requires separately reviewed rebasing. D4b implements the fixed-scope
rebase_required gate, not a rebase writer. This tracer
is deliberately a bounded acceptance check, not an operating daily service.

Saved UI snapshots are regenerated only from reviewed/pinned audits, then verified
with `python -m scripts.export_monitor_snapshot --check --verify-application` via
the project Python launcher. The application check is read-only. Builds and normal
snapshot regeneration do not open the application database.

After D4b, use the [scheduler guide](filing-scheduler.md) and its read-only
`export_scheduler_snapshot --check --verify-application` command to compare the
current application and preserve D4a history. This page's D4a checkpoint remains
unchanged; its older optional cumulative-count equality check is no longer the
current application total. Plain `export_monitor_snapshot --check` still verifies
the original saved projection.
