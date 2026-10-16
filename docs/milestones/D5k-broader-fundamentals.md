# D5k — Broader real CRCL reported fundamentals

Status: complete; paused after D5k at the user’s request.
Proposal commit: `e1edd54655082d3c54e892e0d78f7a015c9a3dd9`.
Branch: `codex/d5a-crcl-normalization`. Decision D049; [proposal](../design/d5k/proposal.md)
and [review/implementation packet](../design/d5k/implementation.md).

## Completed scope

The expanded review uses the same 71 retained lineage captures, including 41
filing/exhibit bodies, at source observation `2026-10-15T21:59:05.195192Z`.
Hash-bound dispositions cover all ten concepts. 101 matching-period comparisons
check registration net/CFO/PPE editions, later current components and earnings
releases. Annual CFO/PPE are directly reported in the audited annual filing;
later interim cash flows are not summed or represented as full-year corroboration.
Independent standards/specification/plausible-but-wrong reviews cleared source
publication and then the separate frozen real-v2 candidates.

New immutable S3 batch `cc2f6241-b43e-40af-8e76-07e249819cbb` contains ten directly
reported FY2025 annual/closing concepts with zero quality flags. Existing S3
replay, current/original/pre-filing readback and prior-row preservation pass.
Historical D5a flags and eligible D5i selections are preserved.

Existing S5 formulas and real-v2 contracts produce two separate results:

| Result scope | Supported definitions | Explicit gaps |
| --- | --- | --- |
| FY2025 annual | Operating margin, consolidated net margin, CFO minus cash PPE purchases, its revenue margin | Six slots: two other-period metrics and four global unsupported definitions |
| 2025-12-31 instant | Reported current ratio and net working capital | Eight slots: four other-period metrics and four global unsupported definitions |

The source includes reserve income, holder reserves and deposit obligations.
Consolidated net income includes NCI. PPE cash payments exclude capitalized
software, acquisitions and other investing; FCF is not discretionary cash.
Current totals are gross reported classifications, not available corporate
liquidity. Both results retain the passing closing consolidated balance identity.
No schema/API/concept/engine/provider/quote/valuation/sector/scheduler change.
D5j's original immutable operating-margin snapshot remains inspectable.

## Validation

| Check | Result |
| --- | --- |
| Expanded body/hash/missing/changed-line red-first regressions | Passed |
| Existing S3 disposable and live replay/readback/preservation | Passed |
| Separate selector/status coverage and wrong-period regressions | Passed |
| Paired SQL/W1 publication, prior snapshot preservation | Passed disposable test |
| Commit-before-audit recovery | Passed: one request and snapshot on retry |
| Independent source and candidate standards/spec/numeric review | Passed exact pinned boundaries |
| Full make check | Passed: 1,857 tests, 512 core, 110 golden; two existing dependency deprecation warnings |
| Production build and browser acceptance | Passed; 62 browser checks, 320/390/768/1440px, keyboard, all metric provenance, local GET-only requests and corruption recovery; screenshots inspected |
| Final staged standards/spec review | Passed after header/historical-label corrections |
| Completion synchronization | Mandatory commit hooks and non-force branch push; final commit/remote identity recorded in Git history and completion handoff |

## Remaining boundary and pause

Reported/derived gross margins lack reviewed complete-scope operands. Revenue
growth and ROA have comparative numeric rows but incomplete earlier-period
history. Nine exact unretained draft/correspondence resources are listed in the
review artifact; four PDF UPLOAD bodies are outside current BootstrapPlan resource
shape. Their accounting relevance is not inferred from metadata. No complete
3/5/10-year analysis history or quarterly trend is claimed.

The user requested a pause after this task. Finish D5k validation and GitHub sync,
then stop. Do not start a new milestone or acquire the earlier missing bodies.
The [handoff](../handoffs/d5k-broader-fundamentals.md) records the resume boundary.

Preview: `http://127.0.0.1:3103/development/pilot/analysis`. The strict completion
artifact reproduces the full live audit chain and all prior selection preservation.
Final browser regression wraps expanded status labels and SEC tag headings on
narrow screens. No financial values or publication pins changed during acceptance.
