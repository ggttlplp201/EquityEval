# D5c — CRCL operating-fundamentals safety

Status: complete for the bounded safety review; financial publication remains blocked.
Date: 2026-10-12. Branch: `codex/d5a-crcl-normalization`.
Proposal commit: `eb42a9e`; baseline: `efa92ff`.

## Objective and delivered scope

[D041 proposal](../design/d5c/proposal.md) pins a 19-filing financial/event
roster for 2025-01-01 through 2026-09-21 and a narrow descriptive operating-margin
profile. Four governed bootstrap groups retained 16 missing primary bodies plus
four Company Facts and four Submissions copies: 24 HTTP 200 captures. Existing
BootstrapPlan permits at most five filing resources per group; no cap changed.

The [acquisition audit](../research/crcl-safety-acquisition-2026-10-12.json)
records request/execution/policy/raw lineage. The final report query initially
used incorrect column names after capture succeeded. A read-only recovery joined
durable requests/results/manifests, with no retry or duplicate acquisition.
Application totals are 36 captures, 38 fetch attempts and nine requests; the
existing single normalized batch and its flags remain unchanged.
Every prior database row was compared with the immutable D5a after-audit after
excluding newly owned rows; every table hash matched.

The [safety review](../research/crcl-safety-review-2026-10-12.json) and pinned UI
projection are deterministic. `/development/pilot/analysis` adds separate
historical/retrospective conclusions, eight checks with evidence drawers, a
business profile, exact capture/hash/filing coverage and outstanding source links.
Existing financial amounts retain their D5a provenance. React does no finance math.

## What was and was not proved

- Exact D5a replay reproduces both original annual operands, signed values,
  period, currency, scale and original-filing precision. Unknown Company Facts
  precision stays unknown.
- The annual amendment explicitly adds separate reserve-fund statements without
  restating other annual disclosures. This does not prove no other correction.
- Original and four fresh inventories agree on the historical roster. Thirteen
  event primary bodies were reviewed; no non-reliance/correction was identified
  in those primary texts. Eleven linked exhibits remain unreviewed.
- Five periodic filings disclose prior-period reclassifications and explicitly
  unchanged assets, liabilities and net income. They do not explicitly establish
  unchanged revenue/operating income. Affected-line/edition reconciliation remains
  unresolved; no actual changed operand or restatement is inferred.
- The profile supports descriptive reported operating margin only, accounting for
  reserve yield/circulation, distribution costs and IPO expenses. It does not
  establish recurring cash profit, generic technology comparability, balance-sheet
  liquidity, broader profitability or price/valuation applicability. Holder
  reserves are not corporate excess cash.

September historical knowledge remains blocked: only three of 19 bodies were
retained by the original cutoff, and the October profile was not known then.
October copies cannot repair that historical state. Retrospective review remains
incomplete. Fresh Submissions also identify two later events outside the pinned
window; a genuinely current eligibility judgment needs their review and a new
cutoff/batch. Operating margin remains null; zero real metrics were published.

## Boundaries and next stage

No schema/API/concept/missingness/formula/migration/quote/provider/scheduler
change. Prior audits, normalized batch and flags remain unchanged. S6 real
publication still needs its dedicated typed lineage, policy/precision,
request/intent and contract review; synthetic S6 approval is insufficient.

Next: pin the missing-exhibit/current-history and reclassification reconciliation
scope, retain and review those bodies, then review a current PIT batch and real
publication contract. No valuation or sector conclusion is authorized here.

## Validation

- 15 focused Python tests and four D5a/D5b/D5c artifact/component tests pass;
  strict mypy and ruff pass.
- Archived review replay and read-only acquisition verification pass without
  source retries; the successful immutable report/projection remain unchanged.
- Production build passes. All 27 scoped browser checks pass (four new plus 23
  existing): two decisions, eight evidence drawers, 19 filing disclosures,
  eleven exhibits, two later events, original per-value provenance, keyboard,
  320/390/768/1440px layouts, corrupt-artifact N/A/Retry and local GET-only requests.
- Independent standards review found no issue. Spec review found an unavailable-
  runtime/partial-acquisition recovery gap. The correction saves a sanitized
  blocked outcome, leaves preservation unknown when unverified, and lists exact
  missing primary bodies. A complete synthetic partial-archive replay regression
  proves no metric publication; successful evidence bytes stay unchanged.
- `make check` passes: 1,732 full tests, 505 core and 110 golden cases, generated
  checks, lint and both type systems. Review corrections additionally pass all
  15 focused safety tests. The required commit hook repeats every check against
  the final staged tree, which adds three failure-path cases to the full suite.
- Final independent re-review resolves both P2 findings. The remaining wording
  correction requests fresh inventory without asserting later events when no
  fresh inventory was retained; its red-first partial-review regression passes.

Preview: `http://127.0.0.1:3103/development/pilot/analysis`. Port 3101 belongs to
an unrelated application; the coordinator directed preserving that service.
See the [handoff](../handoffs/d5c-crcl-safety.md).
