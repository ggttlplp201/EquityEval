# N1 — News and macro-event agent

Status: user-requested scope extension; requirements captured, implementation pending shared contracts.
Requested: 2026-09-11, task `EquityEval — milestone build log`.

## User requirement

Monitor news and give advance notice of events such as CPI, PPI and Federal
Reserve decisions, explaining possible effects on stocks. The user selected
**US macro events plus watchlist stocks**, with **in-app, desktop and email**
alerts. This extends the original P0 plan: selected catalyst/news/alert features
are brought forward from SPEC 2.5, 5.5 and P1/P2. Other P1/P2 features remain in
their original phases. The original ZIP documents remain unchanged.

This is an EquityEval product feature. Capturing it does not start a live Codex
monitor, subscribe an email address, or configure an external sending service.

## First useful version

1. A calendar of US CPI, PPI and FOMC decisions, including the separate statement,
   projections when scheduled, press conference and minutes. Include payrolls
   and PCE as the next closely related calendar sources, after adapter checks.
2. Watchlist news from SEC filings and each issuer's official investor-relations
   announcements. Add licensed secondary reporting as an explicitly identified
   source; do not depend on scraping restricted publishers.
3. An advance brief explaining the event, its verified release time, affected
   watchlist companies and conditional outcomes. Proposed defaults: 24 hours
   and 1 hour before a major release, with configurable quiet hours and frequency.
4. A post-release brief that separates the published result, revisions, a
   timestamped consensus if available, observed market reaction if available,
   and the agent's interpretation. Unavailable consensus remains unavailable;
   comparison with the prior release must never be called a market surprise.
5. One alert history with delivery status for each enabled channel, source links,
   publication/retrieval times, changes and the reason each stock was included.
   Users can mute events, pause channels and adjust the watchlist.

## Sources and scheduling

Use the official [BLS CPI calendar](https://www.bls.gov/schedule/news_release/cpi.htm),
[BLS PPI calendar](https://www.bls.gov/schedule/news_release/ppi.htm), and
[FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
as primary schedule sources (checked 2026-09-11). BLS also publishes an updating
[calendar feed](https://www.bls.gov/schedule/news_release/bls.ics). Read the
published schedule; never infer a release date from a recurring weekday rule.
If a source provides only a date, show the time as unconfirmed and withhold
hour-specific alerts until an official time is verified. Preserve the release's
stated timezone, convert using `America/New_York`, store
UTC and show the user's local zone. Handle daylight saving, schedule changes,
postponements, cancellations, revisions and separate release stages.

Use official release pages for actual figures and explanations. FRED/ALFRED
may support history and vintages; the date of a FRED observation is not a release
timestamp. A consensus provider, news provider, redistribution terms, quotas and
costs require verification before integration. No paid service is selected here.

Polling should be configurable and respect source limits. Refresh calendars
regularly; check release sources more frequently around a scheduled publication.
Show source freshness and outages. Deduplicate by source/event identity and
revision; repeated polls, retries or agent restarts must not send duplicate alerts.
A changed release time updates pending alerts; a revised result produces a clearly
labelled correction linked to the original brief.

## How stock effects are explained

The agent produces conditional analysis, not a certain price forecast. For each
relevant company it names the transmission channel, evidence, time horizon,
competing explanation and uncertainty. Separate market-wide exposure from
company-specific news. Examples of hypotheses to assess against current data:

- Inflation above a verified expectation could change the expected policy path,
  bond yields and discount rates; long-duration equity valuations may be sensitive.
- Producer price changes may affect input costs and margins, depending on the
  company's cost mix, contracts and ability to pass costs on.
- A Fed rate change or guidance shift may affect funding costs, lending income,
  currency exposure and demand. A rate cut associated with weaker growth can
  carry different earnings implications from a cut with stable growth.

These are mechanisms, not guaranteed directions or measured causal effects.
The [Federal Reserve's monetary-policy explanation](https://www.federalreserve.gov/aboutthefed/fedexplained/monetary-policy.htm)
provides background on policy transmission; a specific stock claim also needs
issuer evidence and current market context. No invented percent move, probability,
price target or buy/sell signal. No automatic change to a saved valuation or
assumption. A brief may link to a user-created scenario later.

## Product and delivery behavior

A calendar/inbox entry is the durable record. Desktop and email notifications
link back to that brief, with a short headline and why it matters. Store channel
preferences separately from agent prompts. Request browser/OS notification
permission at activation; show denial honestly. Configure and verify an email
recipient and sending service at activation. The SEC contact address stays a
separate setting and is not automatically enrolled for alerts.

Local scheduling runs only while its worker and host are available. For reliable
alerts while the laptop sleeps, deployment needs an always-on worker and delivery
service. The UI must show which operating mode is active and whether monitoring
is healthy. Do not claim guaranteed background delivery from a closed local app.
Failed sends remain visible and can retry with bounded backoff. Keep an audit
trail of enqueue/send/provider acknowledgement; distinguish acknowledgement
from confirmed reading or notification display.

## Implementation slices and dependencies

| Slice | Depends on | Reviewable outcome |
| --- | --- | --- |
| N1a — Contracts and source reconnaissance | S1 review and S2 schema proposal | Propose event identity, schedule/release revisions, watchlist relevance, cited analysis and per-channel delivery state. Resolve schedule/consensus/news terms. Include N1 needs in S2 without silently freezing new schema. |
| N1b — Calendar and watchlist source workers | Reviewed Source/PIT contract (S3/S4) | Archived source payloads; release-time handling; issuer news; no LLM-generated calendar facts. |
| N1c — Analysis and alert orchestration | N1b + reviewed analysis contract | Evidence-grounded briefs; bounded interpretation; idempotent alert jobs and revisions. Missing source/model results remain visible. |
| N1d — Inbox and three delivery channels | N1c + S6 API/shared UI | In-app history, desktop permission flow, verified email configuration; end-to-end delivery checks. Can proceed alongside S8 after shared contracts. |

These slices are authorized as product scope. Their exact schema/API remains
subject to the existing explicit review gates; this document does not implement
a service or claim that alerts are running.

## Acceptance evidence required

- Hand-checked calendar fixtures exercise US daylight-saving changes, local-date
  rollover, reschedules, cancellations and distinct FOMC publication stages.
- Release fixtures retain headline/core, monthly/yearly, seasonally adjusted
  status, units, reference period and revisions without mixing series.
- Missing/stale consensus, missing news and unavailable prices yield explicit
  gaps. Consensus captured after release cannot be used as prior expectations.
- Duplicate sources, retries, restarts and delayed jobs do not duplicate sends;
  material revisions generate corrections. Disabled channels never send.
- Every factual brief claim links to its evidence; uncertain company exposure
  is labelled. Untrusted news content cannot issue instructions or operate tools.
- Fake-clock and mocked-provider checks cover alert lead times, quiet hours,
  delivery failures and recovery. Integration review demonstrates the same alert
  in-app, in a desktop notification and in the configured email inbox.
- No broker action, financial fact substitution, valuation mutation or false
  claim that monitoring continued while the local worker was asleep.
