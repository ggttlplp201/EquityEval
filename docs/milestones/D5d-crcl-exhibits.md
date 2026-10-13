# D5d — CRCL exhibit accounting-safety review

Proposal `564edfd`, baseline `d4c301e`, D042; authorized continuation to review
all eleven missing D5c exhibits. Completed bounded implementation; commit subject: `feat: review CRCL exhibit accounting safety`.

## Delivered scope and evidence

- Three governed BootstrapPlans (5/5/1 exhibits plus mandatory Facts/Submissions)
  completed once: seventeen retained HTTP 200 captures. Actual retrieval window
  2026-10-13 03:34:00.721088–03:34:04.388371 UTC. No backdating.
- [Acquisition audit](../research/crcl-exhibit-acquisition-2026-10-13.json) records
  request/execution/policy/manifest lineage and before/after row hashes. Every
  original row is preserved. Application totals: 53 captures, 55 attempts,
  12 requests, one normalization batch, two selected facts, zero metrics.
- [Deterministic review](../research/crcl-exhibit-review-2026-10-13.json) retains
  eleven exact accession/form/date/item/exhibit matrices, hashes, quotes,
  source URLs/timestamps, scoped human findings and unresolved reasons.
- Five earnings releases have explicit period/unit/ordered-row assertions and
  22 signed operand comparisons against consolidated, dimensionless USD inline
  periodic contexts at scale three. These are source checks, not a new formula.
- Hash-pinned UI projection adds eleven interactive provenance views to the
  existing analysis page. D5c remains immutable and labeled pre-exhibit.

## What passed and what remains unconfirmed

| Body group | Substantive finding | Limit |
| --- | --- | --- |
| Annual earnings | Selected FY2025 reported pair matches retained 10-K | No independent audit or complete later-history clearance |
| Four quarterly earnings | Explicit tested periods match retained 10-Qs; Q2/H1 FY2025 comparatives match later release | Matching selected periods does not resolve every annual reclassification scope |
| Two director announcements | Appointments/biographies; no reported-line correction identified in reviewed full bodies | Governance news is not financial-history completeness proof |
| Certificate | Governing-document restatement and share-class reclassification | No income-line reconciliation; per-share actions deferred |
| Bylaws | January–December fiscal year corroborated | Governance rules do not certify amounts |
| Tazapay agreement | Target SFRS representations; Circle is Guarantor; contractual seller no-reliance | Scoped accounting review, not full legal diligence; omitted schedules/target statements unavailable |
| Tazapay announcement | Proposed later transaction, expected conditional future closing | No completed consolidation/purchase-accounting proof |

2026 earnings releases change Adjusted EBITDA definitions. That is not a GAAP
operating-income restatement; no adjusted replacement operand is introduced.
Review findings are bounded to the explicitly listed source sections/full bodies,
not inferred from parent item metadata or absence of keywords.

**Eligibility remains blocked.** Historical September knowledge cannot be
retrofitted. Fresh October inventory still identifies two outside-window primary
8-Ks (0001876042-26-000276 and 0001876042-26-000279), not acquired here. Current
coverage and annual affected-line scope need a separate pinned review/batch.
Real S6 remains gated. Metrics remain null; no flags were forced false.

No schema/API/concept/missingness/provider/quote/migration change, no post-window
primary acquisition, and no deployment. Prior audits/projections are untouched.

## Validation and handoff

Red-first missing/changed body, source identity, signed row/header, and partial
acquisition tests; adversarial USD/context/scale/period tests and no-publication
projection checks. Validation: 24 focused checks; full `make check` passes with 1,744 tests,
505 core and 110 golden tests; production build passes; 31 browser checks pass
including desktop/mobile, keyboard, all eleven provenance drawers, local GET-only
requests and corrupt-artifact recovery. Archive replay and live application
preservation verification pass. Independent standards and spec reviews are clear.
A standards P2 concerning unsupported corroboration wording in unavailable/partial
reviews was reproduced red, fixed to depend on completed comparisons, and rechecked.
The hooked implementation commit reruns checks against the exact staged result.
See the [handoff](../handoffs/d5d-crcl-exhibits.md).
Preview: http://127.0.0.1:3103/development/pilot/analysis. Port 3101 is unrelated.
