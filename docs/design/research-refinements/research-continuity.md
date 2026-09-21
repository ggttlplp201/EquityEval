# Research continuity — first-watchlist design

Date: 2026-09-19. Status: **design only; implementation and shared contracts pending**.
This advances a small part of the existing assumptions/thesis/prediction scope;
it does not create a second journal, activate a provider or send an alert.
The user wants the present product preserved, with more specific explanations
and a small watchlist experience before broad market coverage.

## Sequence and reuse

Complete the UI refinement and its state/interaction design first. The initial
user-facing pilot uses all seven supplied tickers, in their supplied order:
**CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL**. This is a pilot selection, not a
claim about positions held or suitability as peers. Mining means mineral mining;
MSTR is a treasury exposure with an operating business, not a Bitcoin miner.
Verify current company/segment/lifecycle profiles with dated evidence rather
than infer them from those themes. Existing MSFT/RBLX archives remain regression
evidence; they do not replace the seven requested names.

The [original specification](../../spec.txt), especially sections 3, 6, 7 and 10,
already defines assumptions, immutable model runs, falsifiable theses,
predictions and version comparisons. [W1](../../features/W1-watchlist-analysis.md)
already requires exact inputs, confirmed assumption versions, durable requests,
new snapshots on explicit reruns and preserved prior results. Reuse that design.

These objects are **planned, not existing database tables**. The
[S2 later-contract boundary](../s2/schema-proposal.md#required-later-contracts)
and [S2 implementation](../s2/implementation.md) distinguish implemented
source/workflow storage from future assumption sets, input/result snapshots,
model runs and theses. Do not hide a new production journal in an unchecked
JSON field or browser storage while their typed contracts remain unreviewed.

The first complete experience belongs in the small-watchlist S8/W1 workflow,
after the relevant S5 calculations and S6 storage/publication/API review.
[F1](../../features/F1-fundamentals-guide.md) and
[D021/D024](../../decisions.md) retain their shared-contract boundaries.
Full conviction scoring, position-size heuristics, probability calibration and
specialist valuation models are not advanced automatically by this slice.
Preserve valuation, sector graphs, company 3/5/10-year history and N1 macro/news
requirements in the wider roadmap.

## Entry points and fields

Offer **Save expectation** from the company overview, Fundamentals/history and
an evidence-backed “Why did this change?” detail. Open the same research/thesis
workspace from each entry point; do not maintain separate copies per screen.
No source number, decomposition or AI explanation becomes the user's expectation
without an explicit save/confirmation action.

| Field label | Design requirement |
| --- | --- |
| What I expect | The user's claim in their own words. An optional numerical target must name a reviewed metric, unit, period, scope and explicit comparison/threshold; never extract a binding target silently from prose. |
| Why I expect this | User rationale, separate from source facts and computed observations. Do not force a price target or universal valuation judgment. |
| Supporting evidence | Exact figures, passages and source references with dates; pin the source capture and analysis snapshot used. A link alone must not imply its changing current content is the saved evidence. |
| What would strengthen this | Optional confirming observations or milestones, with applicable period/scope. Meeting a condition is evidence for review, not proof of the thesis. |
| What would weaken or invalidate this | Required weakening/falsification conditions; retain disconfirming evidence. If a condition is not machine-evaluable, label it for human review. |
| Alternative explanations | Competing explanations and evidence for/against each, or an explicit “not yet researched” gap. A business cause is not established by ratio correlation. |
| Review date / review event | User-entered date and/or stable event reference, its known date precision and current schedule status. Show the original saved review intention separately from later event rescheduling. |
| Analysis context | Read-only resolved issuer/security/instrument, financial periods, evaluation/capture/filing cutoffs, accounting mode, exact input/result snapshot identities and calculation versions. |
| Business profile | Read-only profile identity/version, effective/known dates and company/segment overlays used for this analysis, with a route to inspect evidence and propose a correction. |
| Related assumptions | Exact confirmed assumption-set/revision references where available. Show inherited age and origin; no invented default assumptions. |
| Author and version | User authorship, saved time, revision and parent; distinguish human text, sourced evidence, calculated observations and proposed AI explanation. |

These are proposed UI labels and semantic requirements, **not an approved table,
API payload or status enum**. A research entry need not have a DCF run or a
numerical forecast to be useful. Where a planned object is not available, show
that limitation; do not manufacture a model run or evidence reference.

## Draft versus active thesis

An incomplete entry can be a draft within the same thesis/version design.
Clearly label its missing evidence, unconfirmed event date or unfinished
falsification. Draft is not an active confirmed thesis, and a local Figma demo
must not claim it has persisted real research.

Activation requires the user's expectation and rationale, evidence references
or explicit evidence gaps, and a written **“I am wrong if X by Y”** condition.
The dated falsification requirement comes from the original specification and
must not become optional helper text. If the only review trigger is an earnings
event with no known date, preserve that unknown date and leave activation
incomplete until the user supplies a dated review deadline. Do not guess a
release date. A user-chosen review deadline is distinct from an official event
schedule.

The small workflow does not silently waive the full thesis feature's
why-mispriced, external-bear-case and bias-checklist requirements. Keep those
future validation requirements in the existing thesis design. The S6 proposal
must explicitly define the draft/active research subset and full-thesis
validation boundary before persistence is implemented. It must not create a
second entity solely to bypass validation or demand an invented conviction
score to save a simple expectation.

Editing saved reasoning creates a new revision. Profile corrections, new facts
and later model explanations never rewrite prior research or the prior analysis
against which it was saved.

## Earnings update and comparison journey

1. The user saves/activates their expectation against the exact available company
   context. The workspace displays its review timing and evidence coverage.
2. A later eligible earnings update or explicit W1 rerun produces a new immutable
   analysis snapshot. A failed refresh retains the previous successful result
   separately dated; it does not become new earnings evidence.
3. **Review new evidence** opens the original expectation beside the updated
   figures, passages, dates and sources. Pin both snapshot/profile versions.
   Show what is new, corrected, unchanged, missing or no longer comparable.
4. Mathematical differences and decompositions come from tested core code and
   retain their formulas, operands and validity reasons. Compare like periods,
   scopes, units and accounting/instrument bases. Show compatible numerical
   observations even when a narrative explanation is unavailable.
5. Show the saved strengthening/weakening conditions alongside the relevant
   evidence. Deterministic checks may report a specific condition met/not met
   only when its reviewed definition and all valid inputs exist. Otherwise show
   “Needs review” or an explicit unavailable reason. No condition automatically
   establishes that the complete thesis is right or wrong.
6. The user selects **Retain**, **Revise** or **Retire** and records why. Retain
   appends a dated review; revise creates a linked version; retire preserves
   history and its reason. None edits the earlier evidence, assumptions or result.
7. Reopen either version and its original sources later. The current company
   page may show newer data, but archived research must retain its saved context.

The comparison must distinguish operating-period change from a source correction,
restatement, new classification/profile or calculation-policy revision. An
as-known-then baseline cannot be silently replaced with today's restated values.
A separately labelled restated comparison may be offered when supported.

## Required states and safeguards

| State | Required presentation and behavior |
| --- | --- |
| No saved expectation | Explain the short workflow; do not populate a presumed investment thesis. |
| Draft / incomplete | Name unresolved fields, evidence gaps and unconfirmed dates; preserve the user's work without calling it active. |
| Awaiting event / review due | Display user deadline and sourced event schedule separately; date-only or unknown schedules cannot imply precise alert times. |
| Comparable update | Show old/new periods, figures, numerical changes, provenance and review conditions together. |
| Partial new evidence | Present supported comparisons and missing/unsupported parts independently; unavailable data is not a failed business outcome. |
| Corrected or restated source | Identify the revision and knowledge date. Preserve the original capture and comparison; do not call every correction an earnings surprise. |
| Profile or instrument changed | Expose both versions and changed applicability; block incompatible comparisons and retain losses, cash/debt and dilution facts where supported. |
| Different policy or calculation version | Label the change and its effect; recomputation under a new policy is a new result, not a rewrite of the past. |
| Stale / failed refresh | Show the failed attempt separately from the prior successful snapshot and its age. Never relabel the old result as newly checked. |
| Unchanged evidence | Show that available evidence is unchanged without inventing an explanation or duplicating review/completion alerts. |
| Retired / superseded research | Preserve read-only history, successor links and the user's reason. Watchlist removal does not delete research. |

These presentation states must map onto reviewed existing missing-value and
workflow meanings at S6, rather than invent storage statuses during UI work.
Unknown data remains unknown; no zero substitution, synthesized probabilities or
implied completed analysis. A seven-company selection is not a sector universe,
and X1's comparison gates must not be weakened to make the pilot rankable.

## Explanations with or without AI

The first workflow works without AI. Tested calculations and explicit
rule-based observations explain numerical changes; user-authored reasoning and
linked filing evidence provide the research context.

If AI is added later, label its explanation as a proposal. It must cite the
relevant filing/news evidence, distinguish business inference from arithmetic,
show alternatives/counterevidence and express uncertainty. It cannot overwrite
source facts, calculation outputs, a saved expectation or user assumptions.
Accepting an AI suggestion is a user action that creates a new user-confirmed
revision with its origin retained. AI cannot resolve a prediction or select a
retirement decision silently.

Qualitative confidence is not a probability. Future
[prediction/calibration scope](../../spec.txt) requires explicitly saved prior
probabilities, defined outcomes and resolution horizons; do not compute Brier
scores for vague prose or retrospective probabilities. Price movement alone
cannot prove a business explanation or validate a thesis.

## Concrete next slice and acceptance

For the current refinement, deliver annotated Figma-ready field/state layouts
and this reuse/contract proposal. This document implements design scope only:
no application form, storage, comparison worker, public endpoint, provider
activation or external delivery is claimed.

After design review, implement the applicable tested deterministic explanation
and profile boundaries, qualify source evidence for the seven-company pilot,
then review S6 typed persistence/publication/API contracts before connecting the
complete save-and-review experience. Preserve [W1's](../../features/W1-watchlist-analysis.md)
idempotency, retries, request fencing and out-of-order completion guarantees.
The [manual](../../features/U1-user-manual.md) must teach the shipped workflow.

Design acceptance requires a walkthrough of save → new earnings evidence →
compare → retain/revise/retire; a missing/incomparable update; an event with an
unconfirmed date; a source restatement; a changed profile; a failed refresh;
and reopening old reasoning unchanged. Test calculations before implementation,
and later verify that retries cannot duplicate published comparisons, late work
cannot replace a newer result, a profile change cannot rewrite old analyses and
AI-disabled use retains the entire basic research workflow.
