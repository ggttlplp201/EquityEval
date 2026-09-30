# Company Overview

Open `/development/company`. Choose a fictional company and evaluation date to
view its saved calculations. The page retains Growth, Profitability, Cash,
Balance sheet, valuation multiples, source amounts and comparison history.
No live data or investment conclusion is added in this milestone.

## Research workspace

The four cards show Overview, Financials, Fundamentals and Reverse DCF.

- **Ready · selected snapshot** means this Overview's saved results are present.
  It does not establish compatibility with another workspace.
- **Separate fictional example** means the destination is a different dataset.
  Its link opens that workspace's own default company/edition, without carrying
  the current Company selectors. All three external workspaces currently have
  this status. No financial results are joined.
- **Compatible** requires exact affirmative evidence for issuer, security,
  currency, evaluation/as-of dates, known/retrieved timing, scope and source
  lineage. No checked cross-workspace pair currently qualifies.
- **N/A** means unavailable. A missing destination has no active link.

Click a count, card date or **Inspect linkage evidence** to see the exact saved
identity, snapshot/view IDs, declared source hashes, separately computed local
file/payload hashes, source selectors and reasons. Missing metadata remains N/A
(or null in exact JSON). A capture cutoff is a selection limit, not a retrieval
time. A date-only source declaration is not upgraded to an invented timestamp.

## Values and history

Values display at most four decimal places and retain USD ($), percentages (%)
and multiples (×). Click a financial value for its full saved precision and
calculation/source evidence. No values are calculated in the browser.

Keep **3Y**, **5Y** or **10Y** selected for the desired requested window. Coverage
and date bounds open the exact saved date roster, including missing quarters.
Missing periods remain gaps. Individual unavailable dates open their own
snapshot's evidence. Selecting an earlier evaluation shows only that issuer's
financial snapshots available through that date.

Malformed or repeated URL selectors show N/A. **Choose a saved company** returns
to the default. During a selection change, controls show a loading state. If a
local fixture or checked manifest cannot be read, **Retry** performs a fresh GET
once the underlying file is restored. No analysis job or provider request runs.
