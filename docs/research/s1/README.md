# S1 review packet

Status: research complete, awaiting concept-map review. No financial enum,
schema, normalization adapter or valuation code has been implemented.

Start with the [review brief](review-brief.md), then the
[40-concept proposal](concept-map.md) and [company coverage](coverage-matrix.md).
The eight Company Facts archives and eight original filing documents were
retrieved on 2026-09-11; source observations and review were completed on
2026-09-12. A filing transport interruption was recorded and successfully retried.

## Contents

- [Review brief](review-brief.md): recommended decisions and limits before S2.
- [Concept definitions](concept-candidates.md): proposed names, scope and units.
- [Concept map](concept-map.md): exact observed tag candidates and conditional rules.
- [Coverage matrix](coverage-matrix.md): 40 concepts × 8 pinned company anchors.
- [Cohort](cohort.md): why each company was selected and primary filing links.
- [Baseline observations](baseline-observations.md): AAPL, MSFT, RBLX and COST.
- [Sector observations](special-sector-observations.md): JPM and CRCL, including original-filing exceptions.
- [IFRS/restatement audit](ifrs-and-restatement-observations.md): TSM source gap and KHC raw history.
- [KHC restatement brief](restatement-khc.md): the hand-checked original/revised pair.
- [Source boundaries](source-boundaries.md): verified API limitations and implications.
- [Evidence guide](evidence/README.md): archives, hashes, exact rows and replay instructions.

## Principal finding

Company Facts covers standard-taxonomy, whole-entity observations; it does not
supply arbitrary issuer extensions or full segment/class contexts. This is both
[documented by the SEC](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
and demonstrated by the archived original filings. An override cannot recover a
missing source observation. TSM's selected 2025 filing has no IFRS financial rows
in the captured API response, even though the original filing reports them.
Missing, stale and incompatible observations must remain distinguishable.

The user's separate [N1 news/macro-agent extension](../../features/N1-news-and-macro-agent.md)
is captured for S2–S8 contract planning. No live alert service is activated.
