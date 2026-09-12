# Equity Valuation Workbench

A research workspace that connects reported company facts, explicit human
assumptions and reproducible valuation conclusions.

## Company and data

**Issuer**: The legal reporting entity that publishes financial statements.
An issuer may have several share classes or traded instruments.

**Security**: A particular equity instrument, such as an ordinary share class or
an American depositary share. A ticker is a market label for that instrument,
not its permanent identity.
_Avoid_: Company when instrument identity matters

**Reporting period**: The exact interval or point date measured by a reported
fact. It can differ from the fiscal year named on the filing containing it.

**Filing**: A company's submitted report with its own accession and filing date.
A later filing can contain revised facts about an earlier reporting period.

**Source capture**: A saved version of a source response, identified by when it
was retrieved and the exact content obtained.
_Avoid_: Filing date when referring to retrieval time

**Reported fact**: A numerical observation with its original entity, tag, unit,
reporting period and source context. It is distinct from a calculated subtotal.

**Normalized fact**: A reported observation assigned an approved concept while
retaining its meaning and provenance. Similar amounts or labels do not prove
that two observations represent the same concept.

**Provenance**: The evidence connecting a displayed result to its original
sources and any transformations applied.

**As-filed-by-date view**: A reconstruction using filing versions dated on or
before a chosen date. It does not claim exact intraday public availability.

**Retrieval vintage**: The saved source versions available to this workspace by
a chosen retrieval time. It is distinct from the reporting period and filing date.

**Latest-reported view**: A view using the newest eligible filing versions in a
chosen source capture, with older-period comparatives labelled as such.

**Restatement**: A later reported revision of an earlier period. A change of
presentation or a repeated comparative must not automatically be called an error
correction.

**Quality flag**: An explanation of a missing, stale, conflicting, incompatible
or otherwise questionable input or result. Acknowledging a flag does not fix it.

## Analysis and monitoring

**Watchlist**: The user's collection of securities to follow. It identifies
research interest, not portfolio ownership or a trading instruction.

**Analysis request**: A request to run the available research workflow for one
security at a stated analysis date, with stated data and assumption policies.
_Avoid_: Model run for the entire workflow

**Analysis execution**: One attempt to fulfil an analysis request, including
source refresh, quality checks, calculations and a final research summary.

**Analysis snapshot**: A completed, preserved set of inputs, outcomes, gaps and
provenance from an analysis execution. A newer snapshot does not rewrite it.

**Model run**: One valuation calculation using a fixed set of inputs and
assumptions. An analysis execution may produce several model runs or none when
required inputs are unavailable.

**Assumption set**: A versioned collection of explicit judgments or dated inputs
used by a valuation. Unconfirmed assumptions cannot be invented to finish a run.

**Reanalysis**: A new analysis execution that refreshes eligible sources and
recomputes available outputs, preserving the earlier snapshots.
_Avoid_: Overwrite, train the model

**Macro event**: A scheduled or newly published economic or monetary-policy
release with its own date, time precision, source and revision history.

**Event brief**: An evidence-backed explanation of an event and its possible
relevance to the market and watchlist securities. Interpretation is separate
from published facts and observed price reactions.

**Alert**: A user-facing heads-up tied to an event, news item or analysis outcome.
One alert can be presented through several delivery channels.

**Delivery attempt**: One attempt to send or display an alert through a particular
channel. Provider acknowledgement does not mean the user read it.
