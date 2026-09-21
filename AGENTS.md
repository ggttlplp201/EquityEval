# Equity Valuation Workbench — Agent Instructions

Read `docs/spec.txt` before any non-trivial change. This file is the short version
of the rules that must never be violated. Layer-specific rules live in nested
`AGENTS.md` files under `packages/` and `apps/` — the nearest file wins.

Keep this file short. Project docs are subject to a byte cap, so detail belongs
in `docs/spec.txt`, not here.

## What this is

A local-first equity valuation tool. It ingests point-in-time fundamentals and
market data, runs multiple valuation models, forces explicit assumptions, and
outputs a **range plus its assumptions** — never a single fair-value number and
never a buy/sell signal.

## Design principles (non-negotiable)

1. **Output is a range plus assumptions.** Every verdict carries its input set,
   its distribution, and its sensitivity ranking.
2. **Reverse DCF is the primary lens.** "What must I believe at today's price"
   is the default view. Forward DCF is secondary.
3. **Provenance or it doesn't render.** Every number traces to source, filing
   accession, retrieval timestamp, and transform chain.
4. **Point-in-time discipline.** As-reported values are stored alongside
   restatements, keyed by `filed_at`. Reading restated history as if known at
   the time is lookahead bias.
5. **Three layers, strictly separated.** Facts (immutable, ingested) →
   Assumptions (versioned human judgment) → Conclusions (pure functions, never
   hand-editable).
6. **Force falsification.** No thesis saves without a dated "I am wrong if X."

## Absolute rules

**Never fabricate a missing financial value.** No zero-substitution, no
interpolation, no summing unrelated XBRL tags to fill a gap, no estimating a
missing line item. Missing data returns `NULL` and raises a
`data_quality_flag`. A silent wrong number is the worst possible failure of
this tool — worse than a crash, worse than a gap in the UI.

**`concept_std` is a checked-in enum.** It is the only permitted vocabulary for
normalized financial concepts. Inventing a new string must fail to compile, not
fail silently. Location: `packages/schema/concepts.py` (Python enum) and the
generated TS union type.

**Valuation math lives only in `packages/core`.** `core` is pure: no I/O, no
DB, no network. The frontend renders valuations, it never computes them. Any
arithmetic beyond display formatting in `apps/web` is a bug.

**No `yfinance` in `apps/api` or `packages/ingest`.** Unofficial and
ToS-grey. Prototyping only; enforced by lint.

**No hard-coded macro constants.** No `RISK_FREE = 0.042`. It comes from FRED
with a date attached, or it is an `assumption` row with a written rationale.

**Terminal growth < risk-free rate.** Enforced in code, not in a tooltip.

**Model runs are immutable.** Editing an assumption creates a new `model_run`
with `parent_run_id`. Never mutate a saved run.

**Never blend as-reported and restated data in one series.** Pick a mode, label
it in the UI, don't mix.

**Consensus estimates are never a DCF input.** They exist to compute forward
P/E for comparability and to measure expectation gaps. Your own driver
forecasts drive valuation.

**Never emit a buy/sell signal.** The tool produces arguments. The human
decides.

## Point-in-time query idiom

The canonical pattern. Use this, don't reinvent it:

```sql
-- Value as known at date D
SELECT DISTINCT ON (concept_std, period_start, period_end)
       concept_std, value, unit, filed_at, accession_id
FROM   fact_fundamental
WHERE  security_id = :sid
  AND  filed_at <= :as_of_date
ORDER BY concept_std, period_start, period_end, filed_at DESC;
```

Omitting `filed_at <= :as_of_date` gives you the latest restated view, which is
correct for current analysis and **wrong** for anything historical or
calibration-related.

## EDGAR client requirements

- `User-Agent` header must contain a real contact email or requests are blocked.
- Hard cap 10 requests/second.
- Archive every raw payload (gzipped, keyed by source + params hash +
  fetched_at) before parsing, so normalization changes are replayable without
  re-fetching.

## Testing

```
make test          # full suite
make test-core     # valuation invariants only
make test-golden   # XBRL normalization fixtures
make lint typecheck
```

Requirements:
- **Tests before implementation for anything numeric.** Hand-compute the
  expected answer for a small case first.
- Golden-file fixtures for 6–8 diverse companies (clean large-cap, heavy
  custom-tag user, financial, foreign private issuer, recent IPO, company with
  a restatement).
- Accounting identities as runtime assertions: assets = liabilities + equity;
  cash-flow net change ties to balance-sheet cash delta; segment revenue sums
  to consolidated. On violation raise a flag — don't crash, don't auto-correct.
- DCF invariants: `reverse_dcf(base_assumptions) == base_iv`;
  `monte_carlo_median ≈ deterministic_base`; terminal growth constraint holds.
- Point-in-time regression test against a known restatement.

All of the above must pass before commit. `scripts/pre-commit` enforces this —
do not bypass it with `--no-verify`.

After any change to numeric code, run `/review` with an explicit focus on
inputs that would produce a plausible but incorrect number rather than raising.

## Scope discipline

Current scope: **P0 plus user-requested N1, W1, U1, F1 and X1 extensions**.
Read the feature register in docs/features/README.md. F1 fundamentals was added
to the plan on 2026-09-19, including selectable 3/5/10-year comparison history.
After planning at c1f2697, the user requested “implement the next step.”
The first pure source-metric/history slice is implemented on
codex/s5-source-metrics; read docs/design/s5/source-metrics.md and
docs/milestones/S5-ratios.md. D022 records that bounded scope; remaining D021
contract/product-policy review remains open. Other P1/P2
features remain deferred. X1 Sector Explorer was explicitly requested on
2026-09-19 after current fundamentals work; read docs/features/X1-sector-explorer.md
and docs/milestones/X1-sector-explorer.md. Keep fictional graph validation separate
from real sector coverage and retain D024's shared-contract/source review.
If something feels like it needs a contract change (`packages/schema` or the
`concept_std` enum), stop and ask — that happens in a dedicated sequential
session, never inside a feature branch.

## Ask before deciding

These are expensive to reverse. Ask rather than choosing:
- schema shape
- the `concept_std` vocabulary
- the API contract
- anything that changes how missing data is represented

## Milestone traceability

The user-authorized code root is this iCloud equityEval directory. Read
`docs/milestones/README.md` and the active milestone record before continuing.
Keep milestone scope, decisions, validation evidence and the next handoff current.
Preserve originals in `docs/originals`; record interpretations in `docs/decisions.md`.
S0 scaffolding is complete; its environment limits are in the milestone record.
S2 is complete at milestone/s2. S3 is complete at milestone/s3 (440 tests). The user
explicitly approved D008 and S3-01–04 with “implement” on 2026-09-12 after the
concrete review packet. Read docs/design/s3/source-contract.md and
docs/milestones/S3-ingestion.md. S4a is complete for its accepted scope (717 tests), tag milestone/s4a:
docs/design/s4/source-contract.md and docs/milestones/S4-prices-macro.md.
The user approved D019/S4-01–04 with “you can implement it” on 2026-09-16.
S4a is implemented on codex/s4-market-data; follow the implementation and review records.
D031's first-source bootstrap extension was explicitly approved on 2026-09-21.
Read docs/design/s3/bootstrap-intent.md and docs/milestones/D3c-bootstrap-intent.md.
The user authorized the follow-up pinned plan, typed completion and readiness corrections.
It reuses W1 leases and S3 capture with no quote only for source_bootstrap;
ordinary requests and financial-result/S6 boundaries remain unchanged.
Provider rights, S4b lifecycle changes and later financial/API/UI milestones retain
their recorded boundaries; do not seek repeat approval for the accepted S4a scope.
Later API routes, valuation logic and UI remain at their reviewed milestones. Remove each
`tests/**/.allow-empty-s0` marker when that suite gains real tests.

User scope extension (2026-09-11): include the N1 US macro/watchlist news agent
with in-app, desktop and email alerts. Read docs/features/N1-news-and-macro-agent.md;
bring its requirements into the reviewed shared contracts. Other P1/P2 scope stays deferred.

User scope extensions (2026-09-12): W1 stock additions trigger full applicable
analysis and preserve rerun history; U1 provides a verified user manual and
terminology guide before release. The S2 design incorporates these requirements.

D035's bounded filing monitor is implemented in D4a; read
`docs/milestones/D4a-filing-monitor.md` and `docs/roadmap.md`. The exact reviewed
seed/prior-result lineage, retained HTTP bodies and one typed result per execution
are enforced in 0008/0009. This does not authorize automatic financial dispatch
or imply an operating recurring scheduler; those remain the documented next work.

D036/D4b fixed-scope scheduling readiness is complete: sequential 0010, one real
CRCL slot, repeat dedup and a saved paused UI; see docs/milestones/D4b-filing-scheduler.md.
No background service runs. The fixed window ends 2026-09-21 UTC; replacement
scope/rebase and service configuration require their separate reviewed step.
Use export_scheduler_snapshot --check --verify-application for current read-only
verification; older audits and applied migrations remain immutable.
