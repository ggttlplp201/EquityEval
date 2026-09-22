# D4c — Simpler real-data pilot presentation

User request: remove coverage/disclaimer paragraphs; leave unavailable data for
later and display N/A without explanations. This supersedes earlier presentation
copy requirements for the real-data pilot.

Implemented the requested N/A presentation for missing prices, metrics, observed
filings, source amounts, history and company coverage cells. Removed the pilot
scope banner and repetitive missing-data/implementation explanations. Renamed the
sections Key metrics, Historical trends and Companies. Archived labels, source
periods, dated links and optional evidence drawers remain available. Fictional
demonstrations remain labelled. Source records, null values and eligibility rules
are unchanged; this is a presentation change with no new source acquisition.

Validation: lint/typecheck, optimized build, local browser inspection across all
seven companies and 3/5/10-year controls, source-drawer access, narrow layout, and
the existing pipeline browser suite. The required pre-commit hook runs the full,
core and golden suites. Checkpoint: milestone/d4c-pilot-ui; exact commit and gate
results are recorded by its annotated tag.

Next work follows the operational roadmap; missing source prerequisites can stay
pending. Use concise N/A placeholders in ordinary views instead of explanatory
warning paragraphs. Technical evidence belongs in source details and the manual.
