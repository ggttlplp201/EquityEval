# N1 — Stock topics, evidence and impact assessments

Status: user-authorized N1 refinement, 2026-09-12; design requirements, not a running service.
Task: EquityEval — milestone build log. Decision: D017.
Parent: [News and macro agent](N1-news-and-macro-agent.md).

## Requested outcome

Every watchlist stock needs its own relevant news coverage beyond issuer filings
and ticker mentions. Track developments in its products, competitors, partners,
customers, suppliers and applicable regulation, gather supporting data, and make
reasoned assessments. Keep macro releases visible separately, then explain each
stock's particular exposure. One development may matter to several stocks in
different ways; stock-specific does not mean exclusive to a single company.

The user's CRCL examples are Open Standard's Open USD stablecoin, the CLARITY
Act and Circle's Arc network. See the [CRCL topic example](N1-crcl-topic-example.md)
for resolved identities, research sources and different economic mechanisms.
This refinement brings forward the relevant portions of SPEC 2.6, 8, 9.5 and 9.8;
it does not activate all deferred sector models or the quantitative event-study engine.

## Coverage and agent responsibilities

Use a shared macro collector and a stock-topic collector, with one assessment
workflow combining the relevant evidence for each stock. They may run as separate
agent jobs; a permanent LLM process for every ticker is unnecessary. Fetch a shared
source once under its source limits, then associate its evidence with each relevant
stock. Keep collection, relevance decisions and assessment generation traceable.

Adding a stock starts an initial monitoring profile as part of W1. Discover topics
from sourced business descriptions, filings and material relationships; accept
user-added topics and source links as well. Each topic has a stable identity,
aliases, a category, why it matters to the issuer, the affected business driver,
evidence for that relationship, and freshness/coverage status. Match the actual
product, organization or law: a similar spelling is not enough. Stocks inherit
issuer topics while preserving their own traded-instrument context.

Automatically include evidence-supported topics. Mark uncertain relationships
as candidates; a user can follow a hypothesis without turning it into a verified
fact. Show discovery gaps instead of claiming exhaustive coverage. The user can
add, correct, mute or remove topics and see why each was included. Explicit user
exclusions persist across discovery refreshes until the user clears them. Profile
changes create revisions. Historical briefs keep the profile/relevance evidence they used.
Periodically revisit coverage so a newly material competitor or regulation can be
found without the user knowing its name in advance. Respect configured polling,
source and model budgets; show delayed or incomplete coverage.

## Evidence the collector must gather

- Preserve each document or permitted extract, source identity, URL, revision/hash,
  publication/event/retrieval times and their precision, and the exact passages
  supporting each claim. Archive content only within the source's permitted scope.
- Distinguish official records, company/competitor announcements, independent
  reporting, analysis and rumors. A primary announcement proves what was announced;
  it does not independently verify a marketing claim or business outcome. Record
  publisher interests, including an author that participates in the project.
- Group coverage of one underlying development, preserving separate sources and
  conflicting claims. Reposts and syndicated articles are not independent
  corroboration. Recycled headlines do not become fresh events.
- Gather dated metrics relevant to the hypothesis: definitions, units, entity,
  measurement interval, point-in-time versus period average, source vintage,
  methodology and limitations. Missing or stale observations stay flagged; no
  invented values. Activity, customers, balances and revenue are separate measures.
- For laws, preserve jurisdiction, legislative session, bill identifier, text and
  amendment versions, action, announced/effective dates and official evidence.
  A proposal, committee action, chamber passage, enactment and implementation are
  distinct developments. Refresh status before a current-status claim; an old
  cached page is not proof that no subsequent action occurred.
- Follow available official schedules for hearings, deadlines, product milestones
  and earnings. Unknown dates remain unknown. Reuse N1's time precision,
  rescheduling and advance-notice rules, rather than inventing a catalyst date.

## What a verdict means

Call the output an **impact assessment** in the product. It evaluates a stated
business driver or research hypothesis at a stated horizon; it is not an overall
stock recommendation. Each published assessment contains:

1. What changed, when it happened, what was learned since the previous assessment,
   and why this stock is affected.
2. Sourced facts and metric observations, separated from the agent's inference.
3. Conditional effects on named drivers such as demand, market share, margins,
   financing, regulatory access or execution costs. Show offsetting channels.
4. A directional judgment per driver: favorable, adverse, mixed or insufficient
   evidence. Keep materiality, source reliability and confidence in the economic
   mechanism separate. Explain confidence in words; do not invent a probability.
5. Near-term versus longer-term implications, counterevidence, missing data and
   observable conditions that would change the conclusion, with a review date or
   explicit unscheduled next check. Do not force a direction when data are weak.
6. Possible valuation implications tied to identified assumptions. If there is
   no tested applicable model and confirmed input set, leave the numerical impact
   unavailable. Any later quantitative result comes from the pure core engine,
   carries a range/assumptions and links to its immutable run.
7. Observed stock-price reaction only when a compatible price source is available,
   with window, market session, currency, delay and freshness. A coincident move
   is not an estimate of how much this event caused, nor proof it was priced in.
8. Evidence links, profile/topic/relevance versions, assessment and retrieval
   cutoffs, model/prompt version, generation time and superseded assessment link.

The stock page shows current assessments by topic and a combined explanation
of reinforcing or offsetting drivers. It must not sum sentiment labels into a
fair value or count the same evidence multiple times as independent support.
Claims about historical information use evidence available at the selected cutoff;
relationships discovered later cannot silently enter an earlier saved assessment.

## Updates, watchlist lifecycle and alerts

Initial discovery/backfill creates a dated baseline dossier. Old articles found
at setup are not sent as new breaking news; genuinely future scheduled events
can receive heads-ups. A material new fact, corrected claim, changed legal stage
or changed driver assessment produces a new linked assessment explaining the
difference. A new model's wording alone does not create a news alert.

The proposed default refreshes the affected topic assessment on material evidence
changes. A fresh full financial analysis uses W1's explicit rerun path and a new
request with confirmed assumptions; news never silently edits saved facts,
assumptions or model runs. Adding a stock still runs every applicable implemented
stage, including its N1 baseline. Assessment failure leaves independent financial
stages available and the monitoring gap visible.

In-app, desktop and email alerts share the same assessment revision. Notify on
material changes and scheduled heads-ups, not every poll. Use explicit topic
relevance and membership generation to select recipients; combine multiple stock
explanations for one development where appropriate. Deduplicate on recipient,
channel, underlying development, material development revision and alert purpose,
shared by macro and stock-topic producers. Distinguish each configured lead-time
heads-up from release, correction and assessment-change purposes. A combined alert
pins all included stock-assessment revisions. Mutes and stock removal suppress
future watchlist-only sends; shared collection may continue for other active stocks.
Before sending, recheck the current topic controls and relevance as well as stock
membership. A corrected/removed topic suppresses its pending obsolete explanations
even while the stock remains watched; exclude it from combined alerts without
suppressing other still-relevant stocks. An unrelated profile edit alone does not
invalidate an otherwise valid alert.
Re-adding creates a new membership generation and baseline without replaying old
pending alerts. Preserve earlier evidence and assessment history.

## Build and acceptance

N1a adds these identities, revisions and evidence requirements to the later S2
contracts for review. N1b implements source adapters and profile discovery after
source terms and contracts are resolved. N1c implements assessment orchestration
and revision checks. N1d adds topic controls, source drill-down and the three
configured delivery channels. U1 teaches this workflow and its terminology.

Required acceptance scenarios, specified now and implemented with those slices:

- Find a relevant competitor article that never mentions the stock ticker; reject
  an unrelated namesake. User correction fixes future matching and retains history.
- A stock addition builds its profile and assessment baseline. Missing metric or
  news access is visible and does not fabricate a complete research result.
- An amendment is not enacted law; a testnet announcement is not production use;
  activity growth with unknown economics leaves monetization unresolved.
- Sources disagree or repeat one announcement: preserve the conflict/origin and
  reduce certainty without inventing corroboration or forcing a directional verdict.
- One development has different implications for two stocks. Explanations remain
  stock-specific, while delivery is deduplicated across topic and macro paths.
- A corrected source, late-arriving article, renamed project or revised relevance
  creates traceable history; saved earlier evidence/assessments remain unchanged.
- Restart, duplicate jobs, removal/re-addition, mute and out-of-order assessment
  completion cannot revive old alerts or replace a newer valid assessment.
- Removing/correcting a topic suppresses its queued alerts while the stock remains
  active; automatic discovery respects the exclusion. Other valid stock coverage
  survives. Distinct lead-time, release and correction alerts remain deliverable
  even though duplicate macro/topic producers converge on one notification.
- Source or model failure, stale data and exhausted source/model budgets remain
  visible. Source text cannot change instructions, operate tools or enroll users.
- A reviewer can trace every factual claim and number, inspect counterevidence,
  explain the verdict's horizon, and locate the observation that would overturn it.
