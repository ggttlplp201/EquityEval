# Saved fundamentals results

S6a provides a tested storage and read-only API path using fictional integration
fixtures. The accepted application screens are unchanged. Real company results
and a connected Add/Rerun workflow require the next data/integration milestone.

## Reading a result

A **snapshot** is one saved analysis. Its ID identifies the exact inputs,
calculation, source evidence and evaluation time. Opening that ID returns the
original result; it does not update its facts or freshness label.

A **payload** is the calculation's reusable content. Two explicit reruns can use
the same payload while retaining different request, execution and snapshot IDs.
A retry after a network or worker failure retains the same logical request and
cannot publish a second snapshot.

**Latest compatible result** means the saved result for the exact company,
security/quote, reporting period, basis, currency, history mode, capture cutoff,
evaluation time, policies and engine revision. It never means the nearest result
with different assumptions. The response identifies the most recent requested
work separately, so a failed refresh can coexist with the prior saved result.

| Stored status | Meaning |
| --- | --- |
| `valid` | Supported calculation with usable evidence under its explicit policy. |
| `not_meaningful` | Evidence exists, but the ratio is not meaningful, such as a nonpositive denominator. Numeric value is null. |
| `missing` | A required source value or precision input is absent. Numeric value is null. |
| `invalid` | Evidence, scope or calculation checks failed. Numeric value is null. |
| `stale` | A retained number fails the snapshot's dated freshness policy. It does not drive observations. |
| `unsupported` | The formula, input basis or applicability is not supported or reviewed. |
| `inapplicable` | The reviewed company profile says this metric does not apply. |

Unavailable values display as **N/A**. A margin stored as `"0.2"` is a fraction,
equivalent to 20%. Financial values are strings to preserve exact decimal values.
**Coverage** counts the complete applicability roster, including missing entries;
unknown applicability or no applicable metrics yields N/A coverage.

The selected **3-, 5- or 10-year history** keeps its complete window and explicit
minimum sample count. Missing quarters remain missing. P25/P50/P75 mean the 25th,
50th (median) and 75th percentiles of eligible comparable samples. Excluded sample
IDs and reasons are retained. A comparison is unavailable when its evidence or
minimum is insufficient; the window is never shortened automatically.

**Completed with gaps** means publication succeeded but a requested metric,
history comparison, accounting check or trend was unavailable or failed its
checks. It is distinct from a worker failure. Optional absent accounting/trend
work does not create a failure. No result is an investment recommendation.

## Developer/local operator walkthrough

1. Use migration 0011 in an isolated test database; the application DB is unchanged
   by this milestone. Run `scripts/run_tests.py tests/integration/test_fundamentals_publication.py`
   through `scripts/project_python.py` to exercise the governed fictional tracer.
2. Create an explicit typed manifest and call owner-only
   `approve_fixture_manifest`. This verifies retained PIT selections, metadata,
   capture provenance, fixture governance and the exact engine build. It records
   a private immutable review and expected calculation digest.
3. Call `enqueue_fundamentals` with workspace, optional watchlist, review ID,
   idempotency key, optional parent request and explicit maximum attempts. It
   wraps existing W1; it does not acquire new data. Use a new idempotency key for
   an explicit rerun and retain the parent for watchlist membership continuity.
4. Claim the existing W1 request, then call `run_fundamentals_stage`. It resumes
   the existing stage, freezes inputs before calculation and publishes atomically.
   Writer connections must be idle with autocommit enabled. Use W1 retry/cancel
   operations for failures; never edit stored rows.
5. Compose `equity_api.fundamentals.create_app` with the trusted local workspace
   and a connection factory. This creates no listener and reads no default
   credentials. Exposing it beyond trusted local transport requires a separate
   authentication deployment boundary.
6. `GET /analysis-snapshots/{snapshot_id}` reads the saved snapshot. Query
   selectors are rejected. `GET /companies/{issuer_id}/fundamentals` requires
   `security_id`, `compatibility_key` (canonical selector hash) and `scope_id`
   (watchlist membership UUID, or explicit all-zero UUID for independent work).
   No defaults are inferred. Unknown/incompatible requests return typed 404.

The API includes public source URLs, filing/accession dates, actual capture times,
source tags and hashes, normalized input values, scope, formula and coefficient
lineage. Private archives, raw metadata, reviewer contacts and credentials remain
outside the response. Only the reviewed identity-decimal normalization operation
is projected; other transformation metadata is retained privately by its digest.
