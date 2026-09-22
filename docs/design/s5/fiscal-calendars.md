# Reviewed fiscal calendar extension

Extends the calendar-month assembly without changing normalized facts or public
contracts. `FiscalCalendarEvidence` is an internal, caller-reviewed input, just
like the existing `RevisionCompatibility`. It contains exact selection hashes,
issuer, explicit year/quarter boundaries, source availability and capture dates,
evidence references and review revision. Those dates must fit every input's
filed/capture cutoffs. Core validates this proof; it does not discover calendars.

Supported years are twelve calendar months divided into four three-month fiscal
quarters (including non-January starts), or four reported 13/14-week quarters
whose year totals 52/53 weeks. Day counts validate an explicitly reviewed calendar;
they never classify arbitrary facts as fiscal quarters. Transition years, changes
between calendar systems and malformed boundaries return an unavailable amount.
Every original input, coefficient, uncertainty, review and flag is retained.

The existing annual, four-quarter TTM, same-edition YTD subtraction and reviewed
annual + current YTD − prior YTD functions accept this evidence. TTM means four
fiscal quarters with the exact dates attached, not an annualized 365-day estimate.
No weekly amount is scaled. A bridge needs consecutive fiscal years and matching
YTD ordinals; a subtraction needs consecutive cumulative ordinals in one year.

Revenue growth now requires same-edition or explicit cross-edition compatibility
for calendar and fiscal comparisons. Two different editions without review used
to pass the date test; they now return `revision_compatibility_unproven`. Existing
calendar tests now include explicit synthetic review evidence. Fiscal growth
requires adjacent years, matching quarter/year ordinals, and equal week exposure.
52-versus-53-week growth, YTD growth and fiscal assembled-TTM growth remain
unsupported; reported amounts are still available. Different assembly methods
cannot masquerade as like-for-like growth. Review evidence is retained on the
internal `ReviewedGrowthCalculation`; ordinary Calculation projections are intact.

Company evidence projection rebuilds period arithmetic with its retained proof,
rejecting edited outputs. Margin assembly identity includes calendar facts and
review revision, excluding concept-specific hashes so matching concepts can form
a ratio. Annual ROA keeps its existing twelve-calendar-month contract; weekly or
assembled-ROA definitions are not silently broadened.

Validation: fictional hand-computed 100 = 10+20+30+40; 45 = 75−30;
110 = 100+30−20; uncertainty sums 2, 1, 1.5; reviewed growth 120/100−1 = 20%.
Tests cover 52/53 weeks, fiscal offsets, mismatched periods/currency/editions,
unknown precision, changed calendars, PIT/issuer/hash mismatches and forged
projection values. No live source was called and no calendar for CRCL inferred.
