# D3d — CRCL quote identity evidence review

Status: review implemented and verified; registration blocked by missing evidence.
Date: 2026-09-21. Branch: `codex/source-bootstrap`.
Baseline: `a2780a6` / `milestone/d3c-pinned-capture`.
Recovery checkpoint: `milestone/d3d-identity-review`.

## Scope and findings

The authorized continuation reviews only already captured application bytes and
recorded D3b/D3c research. No new retrieval or provider was used. The current
Company/News/Help/Sector design and 3/5/10-year history options remain intact.

| Required field | Reviewed result | Evidence |
| --- | --- | --- |
| Symbol | CRCL | Submissions ticker and three filing covers |
| Exchange code | NYSE | Exact SEC Submissions exchange code; covers say New York Stock Exchange |
| Share class | Class A common stock | Three covers, including exact par-value description |
| Listing valid_from | 2025-06-05 | Original annual report explicitly says listed since June 5, 2025 |
| Quote currency | NULL / unsubstantiated | No explicit exchange quote-currency declaration established in this bounded review |

`NYSE` is the source's exchange code. No unverified MIC mapping to `XNYS` is
introduced. The June 5 listing start is neither the annual period end
(2025-12-31), original filing date (2026-03-09), March 3 holder observation,
amendment filing date (2026-07-13), Q2 filing date (2026-08-05), nor September 21
capture date. It is a supported candidate, not an inserted identifier.

Reporting currency is explicitly the U.S. dollar. Inline XBRL offering-price
facts use USD/share (IPO 31.00, follow-on 130.00); par value and public-float
amounts also use dollar notation. These establish their own denominations;
they do not explicitly substantiate the exchange quote currency. No currency
is inferred from NYSE, reporting currency, an offering price or a dollar sign.

This is a bounded manual evidence finding, not a claim that no possible source
could establish the field. The replay command deliberately cannot discover or
approve a currency from arbitrary new documents.

## Implementation and artifacts

- [Command](../../scripts/review_crcl_identity.py): fixed-vintage read-only review
  and `check-registration` action (exit 2 when blocked, 1 on verification failure).
  The command pins the prior D3c audit hash, verifies stored request/plan,
  execution/result, policy/attempt linkage and the archived manifest, then reads
  all five bodies through the existing SHA/size-verifying `LocalArchive`.
- Namespace-aware cover checks and exact reviewed listing/reporting statements
  retain inspectable locators and capture IDs. DTDs, ambiguous/conflicting
  identities, altered source bytes and changed audit packets are refused.
- [Audit](../research/crcl-quote-identity-review-2026-09-21.json): source hashes,
  locators, field results, explicit currency exclusion rationale and database
  table counts/hashes. This is a review artifact, not a financial result or a
  new stored/public contract.
- [Tests](../../tests/test_crcl_identity_review.py): offline fictional evidence
  plus an isolated PostgreSQL test enforcing a read-only transaction.

Reproduce without SEC calls or application writes:

```sh
.venv/bin/python scripts/project_python.py -m scripts.review_crcl_identity review
.venv/bin/python scripts/project_python.py -m scripts.review_crcl_identity check-registration
```

A quote-registration writer is not added: its required evidence is incomplete.
There is no placeholder currency, CLI currency override, quote insertion,
ordinary request, membership, normalization or publication side effect. The
existing source-bootstrap owner registration command retains its original scope.

## Validation and state

18 focused tests pass: reporting/offer currency cannot unblock registration,
no date fallback, namespace/identity conflicts, archive corruption/missing body,
changed audit refusal, stable replay, timestamp-offset equivalence, blocked CLI
exit status, and PostgreSQL rejection of writes within the review transaction.

Actual application review repeated identically. The registration check returned
exit 2 with `quote_currency_unsubstantiated`. Both run over a repeatable-read,
read-only database transaction with UTC serialization. The saved table hashes
are identical before/after within that snapshot and across separate command
invocations; they are not a claim about concurrent writes by other processes.
The original D3c audit SHA and all five source body hashes remain unchanged.

Counts: 1 source/policy/issuer/security; 12 captures and 12 attempts; 3 bootstrap
requests; 0 quote identifiers, memberships and normalization batches. Existing
workflow history is preserved. Test fixtures stay in the separate test runtime.

Commit acceptance requires the mandatory hook: full suite (1,083 tests), core
(225), golden (110), lint/format/import policy/generated enum and Python/TS types.
No valuation math, schema, API or missing-financial-data representation changed.

## Handoff

The exact next blocker is `quote_currency_unsubstantiated`. Obtain and archive
authoritative evidence explicitly connecting CRCL's NYSE Class A listing to its
quote currency, including sufficient effective-date context, under a reviewed
source policy. That acquisition is outside this captured-evidence-only turn.
Then review the new evidence, implement the narrow idempotent owner registration,
and enqueue an ordinary request only after its prerequisites are met. Identity
success alone must not create membership or publish financial statements.
Financial event/statement review, normalization/PIT/S5 and S6 boundaries still apply.
