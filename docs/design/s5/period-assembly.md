# S5 period assembly prerequisite

Status: bounded source-period implementation complete after checkpoint `bd437db`.
Validated before X1 feature code began: 167 core tests and independent numeric
review passed. Full S5 remains in progress.
This finishes the next source-only prerequisite before Sector Explorer math.
It does not finish every metric, screen or shared contract in S5/F1.

The pure period module retains original FinancialInput selections, explicit
coefficients, resulting dates, formula revision, source flags and precision.
It produces derived amounts; it does not fabricate a normalized source fact or
replace an original StatementSelection. Existing margin, growth and FCF functions
consume these amounts through the same source/scope/unit guards.

Supported assemblies are an exact twelve-calendar-month source, four contiguous
calendar quarters, same-fiscal-start YTD subtraction into a quarter, and annual
plus current YTD minus prior YTD into TTM. Gaps, overlaps, wrong concepts,
incompatible currencies/scopes/history policies and missing inputs block output.
Instant balances, shares and EPS are never summed. 52/53-week fiscal calendars
remain explicitly unsupported pending their own evidence and alignment policy.

Same-edition evidence is required for YTD subtraction. Cross-edition TTM inputs
need explicit reviewed revision-compatibility evidence pinned to the input hashes;
matching dates or a common query mode is not enough to prove a consistent
restatement basis. Same-period ratio operands must have compatible assemblies.
Unknown precision stays unknown. Known absolute error bounds add across both
addition and subtraction; they are not cancelled when monetary values cancel.

The source-only prerequisite does not supply common-shareholder earnings,
complete capitalization, live quotes, sector memberships or source activation.
Those remain explicit Sector Explorer prerequisites.
