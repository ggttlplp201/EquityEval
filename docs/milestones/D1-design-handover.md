# D1 — UI design handover and real-data pilot preparation

Date: 2026-09-19. User requested UI redesign before further feature development,
a handover preserving all functionality, and practical instructions for obtaining
real data. They then asked to use the installed Figma MCP in this conversation.
Application baseline remains `a9cb080`, `milestone/x1-core-graphs`; no application
code, numeric rules, shared contracts or source activation changed in this task.

## Deliverables

- [Portable design brief](../handoffs/figma/EquityEval_Figma_Design_Handover.md).
- [143-item feature/state preservation matrix](../handoffs/figma/EquityEval_Feature_Preservation_Checklist.md),
  with implemented backend, fictional UI, planned and deferred scope distinguished.
- [Real-data acquisition and pilot guide](../handoffs/figma/EquityEval_Real_Data_Setup.md),
  based on the actual adapters and current official provider documentation.
- [Figma design workspace](https://www.figma.com/design/il5MpavMssK1PY5LfGJjHR),
  containing a partial brief and initial editable Sector Explorer concept.
  [Canvas status](../handoffs/figma/FIGMA_STATUS.md) tracks unfinished work precisely.
- Portable ZIP with selected original specs, authoritative plans, manuals and
  existing UI reference images; manifest and checksums allow verification.

## Design boundary and service limit

The Figma Starter plan's MCP tool-call limit stopped canvas work. No upgrade or
purchase was made. The concept is partial, not a completed redesign or working
prototype. Complete local handover files remain available for manual Figma use or
later MCP continuation. Numerical/data rules continue to be owned by the existing
engine and reviewed contracts; the visual design does not approve new contracts.

## Validation and findings

- Compared implementation, original spec, F1/X1/N1/W1/U1 additions and deferred
  P1/P2 scope; assigned 113 unique feature IDs with destinations and states.
- Independently reviewed the brief/data guide for scope and financial semantics;
  corrected monitoring-page wording and scatter per-axis cohort wording.
- Existing SEC archive/source metric acceptance command in the guide passed
  **11 tests**, with no credentials or upstream downloads. This is source
  verification, not a populated real-data application.
- Package link/manifest/secret-exclusion checks are recorded in its generated
  `VALIDATION.json`. No application-code suite was repeated for document changes.

## Next sequence

1. Complete/review the Figma design against the feature matrix, including mobile,
   missing/error/limited states, all linked graphs and source drilldowns.
2. Start the selected-company pilot with all seven user choices, in order: CRCL,
   MSTR, COIN, HOOD, USAR, MP, GOOGL. Complete identity/filing/precision/period
   inventory and the source-to-core boundary; show blocked drivers explicitly.
   Preserve MSFT/RBLX annual archives as regression evidence, not replacement
   user-facing pilot names. Existing tests do not populate the UI.
3. Qualify permitted price/reference/capitalization data, then review S6/X1c's
   common-income, complete cap, roster/membership and immutable snapshot contracts.
4. Connect and verify selected-company real results before claiming any full-sector
   universe/history. Preserve 3/5/10-year company options and the full N1/W1/U1 backlog.

Account keys alone currently activate neither a live import nor news monitoring.
No live-data fetch, external email, subscription or application deployment was
performed by this handover task.

## Standalone Figma AI package — 2026-09-19

The user chose to use Figma AI independently and requested a complete ZIP for
redesign. Added a dedicated prompt, root reading guide, current React/Next UI
source, workspace dependency/configuration files and the compressed fictional
fixture to the handover package. The prior partial MCP canvas is optional
reference; it does not constrain the new visual direction. No application code
changed. Package integrity, feature IDs and supplied reference files were checked.

## Supported Figma AI uploads — 2026-09-19

After the owner reported unsupported ZIP/folder/source attachments, exported a flat
upload set containing only two UTF-8 .txt files and four PNGs. The main brief
embeds the prompt, current handover, all 113 feature IDs, complete original/feature
specification text, current status precedence, terminology/manual and data notes.
The second file preserves current UI source as readable text; binary DOCX and
compressed fixture attachments are not required. Verified all appended spec text,
unique IDs, UTF-8 readability, PNG signatures and file extensions. Project copies
are in var/handoffs/figma-upload; convenient copies are in Downloads.

## Business-aware refinement — D026/D027, 2026-09-19

The user retained the app direction and advanced three specific capabilities:
mathematical versus causal change explanations; small saved-expectation/earnings
continuity from existing thesis scope; and versioned business-model/lifecycle/
instrument profiles. [R1](../features/R1-business-aware-research.md) records reuse,
new behavior and milestone placement. The [primary-source evidence matrix](../research/pilot-business-profiles-2026-09-19.md)
checks all seven requested issuers, including USAR's post-quarter acquisition and
MP's distinct production/ramp stages. None of this research activates a feed.

Delivered the concrete design/acceptance packet and appended E/C/B checklist IDs
without renumbering the original 113. The full checklist now has 143 requirements.
Current bounded work implements the design handoff; no numerical engine, company
UI, specialized valuation or thesis/profile persistence is claimed as complete.
This follows the user's UI-redesign-first sequence, rather than skipping it.

After design review, the next concrete task is the seven-company source/identity/
coverage worksheet and first source-to-core pilot. Proposed first arithmetic
extension: comparable annual operating-margin decomposition; implement tests
before code, using existing operand/precision rules. P/E price/EPS, EPS share-count
bridges and changing-cohort sector explanations retain their prerequisites.

## Supported upload refresh — revision 2, 2026-09-19

The supported set is now in `/Users/leon/Downloads/EquityEval_Figma_Upload_v2`,
with identical project copies in `var/handoffs/figma-upload-v2`. Upload files
01–06 individually: complete UTF-8 design brief, UI source reference as text,
and four PNG references. File 07 is an optional standalone refinement addendum
for an existing Figma AI conversation; it is already included in the main brief.
The application baseline remains unchanged.

Validation: all 143 unique feature IDs are present, including every original
113 ID; all 31 selected source documents are embedded verbatim in the brief;
15 current UI files match the source reference. UTF-8 decoding, PNG signatures,
TXT/PNG-only extensions, recognized credential-marker scan, SHA-256 hashes and
identical Downloads/project copies passed. All 66 checked local Markdown links
resolve. `git diff --check` passed. Independent review corrections distinguish
MSFT/RBLX regression fixtures, supported attachment formats, and Stillwater's
commenced production from its not-yet-started sintered NdFeB magnet revenue.

Six illustrative ratio-attribution cases were checked with exact rational
arithmetic. This validates the document's worked identities only: no numeric
engine was added, and no new application numerical test suite is claimed.
`var/handoffs/FIGMA_UPLOAD_V2_VALIDATION.json` preserves the export manifest.
Actual upload acceptance and the resulting design remain to be checked in the
owner's Figma AI session; the exported formats match the supplied upload screen.

## Design received; build resumed — D028, 2026-09-19

The owner supplied `Sector Explorer redesign demo.zip` and authorized application
work to resume. [D1a](D1a-redesign-implementation.md) tracks the bounded UI port and
verification. The supplied design covers an older 113-ID handover; the complete
143-ID reconciliation retains omitted R1 and other flows. Earlier statements in
this record that application work was paused describe the handover checkpoint.

[D1b](D1b-company-news-help.md) continues the supplied style into Company, News
and Help after the owner authorized filling missing screens. The fictional UI
and real-data/production-service acceptance remain separate.
