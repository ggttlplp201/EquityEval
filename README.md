# Equity Valuation Workbench

## Capabilities

- **Point-in-time SEC fundamentals:** Acquires and archives SEC filings,
  normalizes reviewed XBRL concepts, preserves restatements and reconstructs
  the financial information available on a selected historical date.
- **Auditable financial evidence:** Retains each value's source, filing
  accession, retrieval time, unit, transformation chain and quality state;
  missing or unsupported inputs remain explicitly unavailable.
- **Market and macro data infrastructure:** Provides typed adapters, archival
  storage, exact-date selection, freshness handling and licensing controls for
  price and macroeconomic observations.
- **Fundamental analysis engine:** Calculates fiscal-period and historical
  growth, profitability, cash-generation, liquidity, return-on-assets,
  accounting-reconciliation and coverage metrics in pure Python.
- **Reverse valuation engine:** Uses deterministic Decimal-based reverse FCFF
  models to evaluate the operating assumptions implied by a market value,
  including scenarios, sensitivities and enterprise-to-equity bridges.
- **Immutable research workflows:** Versions assumptions, analysis requests,
  fundamentals snapshots and valuation runs through durable PostgreSQL
  workflows with idempotency, leases, retries and fencing.
- **Filing monitoring and scheduling:** Records bounded SEC filing checks,
  retained responses, detected filing editions, retry budgets, deduplication,
  scheduling state and operational blockers.
- **Research interfaces:** Includes a Next.js company workspace, evidence
  drawer, searchable glossary, pipeline audit, filing controls and graph-based
  Sector Explorer.
- **Correctness verification:** Uses point-in-time and restatement regressions,
  golden SEC fixtures, accounting checks, database constraints, source-policy
  tests, generated-contract checks and valuation invariants.

## TODO

- [ ] Activate a licensed quote and reference-data provider, then register
  authoritative security, exchange and currency identities.
- [ ] Publish governed real-company fundamentals and valuation results through
  the existing snapshot and API contracts.
- [ ] Complete production watchlist search, add, remove, rerun, progress and
  preserved-history workflows.
- [ ] Connect filing discoveries to deduplicated downstream analysis refreshes
  and deploy an operator-controlled recurring monitoring service.
- [ ] Replace fictional Sector Explorer fixtures with reviewed real-company
  universes, historical membership, corporate actions and coverage reporting.
- [ ] Implement the remaining valuation views, including forward DCF, Monte
  Carlo distributions, tornado analysis and comparable-company valuation.
- [ ] Build stock-specific news and macro monitoring for CPI, PPI and Federal
  Reserve events with in-app, desktop and email alerts.
- [ ] Complete the production company workspace, thesis and catalyst tracking,
  prediction logging, calibration analysis and verified user manual.
