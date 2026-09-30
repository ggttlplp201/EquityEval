# S8d pinned acceptance — Company Overview

Baseline: ee50c317874dbcc1464d5fdc2fb971411dd31b56.
Branch: codex/s8d-company-overview. Scope pinned before implementation.

The existing Company source-copy fixture contains 84 fictional issuers and 168
saved views. Fundamentals, Financials and Reverse DCF each use a different
fictional issuer. USD agreement does not establish compatibility. Company has
no security ID, source known-at or exact retrieval timestamp; Financials has no
security/as-of selector. Preserve missing metadata as null/N/A, date precision,
per-amount bases, and distinguish capture cutoffs from retrieval timestamps.

1. Keep Company calculations, source drawers, historical snapshots and 3/5/10
   history intact. Name the entry point Company Overview. No combined financial
   conclusion, score, recommendation, AI narrative or browser financial math.
2. Generate a deterministic local metadata-only manifest from the four checked
   fixtures. Classify selected Overview as ready for its own saved view only.
   Cross-workspace compatibility requires affirmative exact issuer, security,
   currency, as-of/evaluation, known/retrieval, scope and source-lineage matches;
   missing proof cannot equal a match. Different or incomplete fictional
   identities stay separately fictional/unlinked; absent destinations are N/A.
   This is an internal presentation contract, not a schema/API/core change.
3. Bind entries to exact Company view IDs and verify source file SHA256 hashes
   on the server. Retain actual local payload hashes separately from declared
   synthetic hashes. Evidence includes all identity/date/scope decisions,
   source file paths/digests, snapshot/selection identities, reasons and counts.
   No financial values copied between workspaces. Status is supplied, never
   inferred from a label in React. Show linkage before navigation. Incompatible
   links open their own default; compatible links use only destination-supported
   exact selectors. Missing links are disabled.
4. Company GET query rejects unknown keys, arrays/repeated parameters, unknown
   or unsupported company/date combinations and ambiguous saved candidates.
   Malformed URLs never fall back. Send only selected issuer history up to date.
5. Financial displays max four decimals via existing exact-string formatter;
   drawers preserve full precision. Missing displays N/A. Exposed coverage counts
   and dates must open source/context evidence. Preserve read-only GET behavior,
   keyboard/focus, 320/390/768/1440 layouts and loading/not-found/error recovery.
6. Red-first tests cover strict selectors, missing/mismatched compatibility,
   evidence and navigation, formatting and pass-through (no browser math).
   Run deterministic no-diff export, Python/Node focused tests, S8a/b/c Node and
   browser regressions, S8d browser checks, build, lint/types/full/core/golden.
   Independent spec and standards review against baseline, fixes, milestone
   log/manual/roadmap, named commit and immutable annotated S8d tag. Stop at S8d.

Real publication, providers, new shared contracts, automated monitoring and
other original Overview wish-list features retain their separate gates.
