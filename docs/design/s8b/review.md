# S8b review record

Fixed baseline: `f46bf529edf4d333df2346045ff7b371b4993388`.
Working diff plus new files reviewed against [pinned acceptance](acceptance.md),
F1, S6a public contracts, root/web AGENTS and the repository specification.

## Specification

Independent review identified that historical percentile drawers incorrectly
showed current-selection sources as if those facts generated the historical
band. History controls now use a separate evidence path: exact PublicHistory,
eligible/excluded IDs and reasons, target selector and snapshot identity, with
historical sample operands N/A. Current facts are not substituted. Metric
controls retain their exact selected-source evidence. Follow-up: no findings.

## Standards

Independent review confirmed the history provenance issue and found overlapping
labels for tied quartile coordinates. Chart labels now combine equal supplied
coordinates; no financial calculations were introduced. Node/browser checks
cover tied labels and history-source separation. Follow-up: no findings.
React review: direct imports, no extra data-fetch waterfall, only one selected
payload crosses the server boundary, derived display state uses no effects,
controls have labels, native drawer/focus behavior is reused. No new dependency.

## Verification repairs

The initial build caught an unscoped CSS module selector; it was scoped to the
local controls. The initial browser run used HTMLElement.innerText on SVG text;
textContent now checks the same expected label correctly. No assertion was
removed. The next full browser suite passed, but visual inspection found a
screenshot captured the inherited Sector loading state during navigation.
The harness now waits for the selected URL, rendered heading, exact snapshot ID and visible metric/status;
a scoped Fundamentals loading page replaces unrelated transient copy. Fresh
browser screenshots and final execution totals are recorded in the milestone.

No core formula, generated type, API or migration changes. Production fixtures
live outside tests and invoke canonical manifest validation and existing S6a
calculation; preserved S8a fixture and checkpoints are unchanged.


Final identity audit: source vintage now binds raw fictional amounts, period
basis, evaluation date and case. Capture/batch/edition/observation identities
include that vintage, capture/source hashes agree, and scope ID binds its exact
descriptor. The new Python regression rejects conflicting observation contents
and verifies changed inputs have distinct capture identities. Independent
standards follow-up found no new issues. Financial formulas remain unchanged.


Coordinator selector audit: unknown query keys previously fell through to the
three-year default, and first-match lookup could mask duplicates. Export now
rejects duplicate example IDs/dates/selection keys. The actual route allowlists
query keys and accepts exactly one matching saved candidate. Red-first Python
and Node/actual-route tests and an unknown-query browser case cover the repair.
Both independent reviewers found no remaining issues on follow-up.
