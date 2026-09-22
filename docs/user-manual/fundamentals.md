# Understanding fundamentals calculations

Status: draft for the first S5 calculation slice. This chapter explains the
implemented source formulas and their limits. It is not a guide to working product
screens. S6a implements [saved fundamentals and read-only retrieval](saved-fundamentals.md)
for governed synthetic fixtures. Production data and UI integration remain pending. The source
formulas and history math have core tests; the product walkthrough is pending.

The full [fundamentals plan](../features/F1-fundamentals-guide.md) includes more
metrics and a guided company view. This first slice covers supported revenue
growth, margins, cash-flow and liquidity calculations, plus configurable own-history
comparison mathematics.

## Start with the amount and period

Revenue is the amount earned from selling goods or services during a reporting
period. Profit and cash flow describe different parts of the business; revenue
growth alone does not establish either of them.

Check what a figure includes before comparing it. An annual amount and a
quarterly amount cover different lengths of time. A consolidated amount covers
the reporting group; income attributed to the parent or to common shareholders
has a different scope. Currency, reporting basis and the dates must also match.

**Year over year (YoY)** compares a period with its corresponding period a year
earlier. This slice accepts explicitly compatible annual or calendar-quarter
comparisons. A quarter is compared with the corresponding quarter last year,
not with the immediately preceding quarter. A 52/53-week reporting calendar
needs a separate reviewed comparison policy and is not supported by this slice.

**Trailing twelve months (TTM)** means twelve months of financial flows. It is
different from a company's fiscal year and from a balance-sheet date. TTM
assembly, cumulative year-to-date subtraction and diluted-EPS reconstruction
remain later work; this slice does not build them by summing convenient rows.

For source dates, restatements and historical cutoffs, see
[Understanding source data and history](data-and-history.md).

## Growth and profitability

| Term | Calculation and meaning |
| --- | --- |
| Revenue growth | Current revenue ÷ comparable prior revenue − 1. Prior revenue must be positive. A percentage describes the change in sales, not the quality of the business. |
| Gross profit | Revenue left after the matching cost of revenue. A reported gross-profit amount remains distinct from a derived result calculated as revenue − cost of revenue. |
| Gross margin | Gross profit ÷ revenue. This describes the share of revenue left after cost of revenue; it does not establish viable unit economics by itself. |
| Operating margin | Operating income ÷ revenue. Operating income reflects operating expenses as well as cost of revenue. It is not automatically the same as EBIT. |
| Net margin | Matching consolidated net income ÷ revenue. Financing, taxes and other items can affect this measure. Parent-only or common-shareholder income cannot silently replace consolidated income. |

All three margins require positive revenue. Zero or negative revenue does not
produce a meaningful margin, and missing revenue is never replaced with zero.
A derived gross-profit result keeps both source operands and its formula; it
does not overwrite a missing reported gross-profit fact.

For a synthetic growth example, revenue rising from 100 to 120 is growth of
0.20, displayed as **20%**. If the prior revenue is zero or negative, show the
amounts and the reason the percentage is unavailable instead of reporting an
apparently favorable growth rate.

A negative or unusually large margin can be an actual arithmetic result.
For example, synthetic revenue of 1 million and operating income of
−72.7 million give an operating margin of **−7,270%**. That means an operating
loss of 7,270 for every 100 of revenue. Keep both amounts and inspect the
period, scope, units and precision; the size of the ratio alone does not prove
that the filing is wrong. Any display threshold or interpretation rule must
have its own reviewed policy.

## Profit, cash flow and capital spending

**Cash flow from operations (CFO)** is the reported cash generated or used by
operating activities. It can differ from net income because income includes
noncash items and because the timing of cash receipts and payments differs from
the timing of reported revenue and expenses. The difference calls for checking
the source statements; it is not by itself a conclusion about accounting quality.

**Capital expenditure (capex)** in this slice means cash purchases of property,
plant and equipment (PPE). The calculation requires a reviewed nonnegative amount under the
positive-outflow convention. Reported zero capex is valid. An unexpected negative source amount must be investigated;
blindly taking its absolute value could hide a sign or mapping problem.

The chosen **free cash flow (FCF)** convention is:

`FCF = CFO − cash purchases of PPE`

`FCF margin = FCF ÷ positive revenue`

With synthetic CFO of 12 million, PPE capex of 20 million and revenue of
100 million, FCF is **−8 million** and its margin is **−8%**. Operating cash flow
did not cover those capital purchases. Financing proceeds or asset sales could
still increase the company's cash balance, so negative FCF does not by itself
establish imminent failure.

This convention is separate from an issuer's adjusted FCF measure. It is also
separate from **free cash flow to the firm (FCFF)** used in an enterprise
valuation. It does not automatically represent cash distributable to
shareholders. Do not pair an enterprise value with this FCF amount without a
reviewed, compatible valuation definition.

## Working capital and the current ratio

**Current assets** and **current liabilities** are reported balance-sheet totals
at a specific date. Both amounts must describe the same company and date.

**Current ratio** = current assets ÷ current liabilities. For example, 150 of
current assets and 100 of current liabilities gives **1.5x**.

**Net working capital** = current assets − current liabilities. The same example
gives **50** in the reporting currency. Assets of 50 and liabilities of 100 give
**−50**. This is an accounting difference, not cash available to spend or a forecast
of cash flows. Its meaning depends on the business and composition of the balances.

Unavailable results display **N/A**. The calculation preserves its source operands
for inspection and does not assign a good/bad liquidity score.

## Return on assets (ROA)

ROA compares consolidated net income with the average of total assets at the
beginning and end of the reporting year:

`ROA = annual net income ÷ ((opening assets + closing assets) ÷ 2)`

For a synthetic example, net income of 10 and assets of 80 at the beginning and
120 at the end give average assets of 100 and **ROA of 10%**. A net loss produces
negative ROA. This uses two balance-sheet dates, not a daily average. It describes
reported profitability relative to assets; it does not by itself determine
whether a stock is attractive. Unavailable results display **N/A**.

## Percentages, percentage points and units

The calculation layer represents percentages as fractions: 0.25 displays as
25%, and −0.08 as −8%. A margin moving from 10% to 12% rises by **2 percentage
points (pp)**. Calling that a 2% relative increase would describe a different
calculation.

Unit labels and scale matter. A source amount shown in millions must be
interpreted with its scale; a percentage is not a currency amount. As a
formatting example, **−4.55K% means −4,550%**, not −4.55%. This example is a unit
check, not support for extracting financial facts from screenshots.

**Source precision** describes the rounding information attached to the
reported amount. A denominator that cannot be distinguished from zero at that
precision cannot support a stable ratio. Missing precision is itself a gap;
the calculation must not guess a tolerance from the displayed digits.

## Comparing with the company's own history

The planned history choices are **3, 5 and 10 years**. The longer choices remain
part of the requirements. This slice provides comparison mathematics with
explicit window and sample policies; it does not activate a product default or
provide a completed history selector in the interface.

Each sample must represent the same metric on a compatible basis and must be
eligible at its own historical date. Today's revised data cannot silently stand
in for evidence known years ago. Price-dependent samples additionally require
eligible prices, completed-session evidence and compatible share adjustments.
Those prerequisites are not supplied by percentile arithmetic.

A **percentile** locates a value within the selected historical sample.
The **25th percentile (P25)** and **75th percentile (P75)** can describe the
middle half of that sample. The exact sample rules, minimum count and percentile
method must be stated by the comparison policy. Interpolating between ordered
sample values to calculate a percentile is different from inventing missing
financial observations.

A ten-year selection must not silently become a three-year comparison because
data is scarce. Show the selected window, sample dates, eligible and excluded
counts, and the reason a comparison is unavailable. Without the required
eligible samples, there is no band or rank.

Own-history comparisons are not peer comparisons and do not establish
intrinsic value. A low historical multiple, when supported later, will not by
itself mean a stock is a bargain.

## Understanding gaps and what comes later

A source amount can remain available for inspection while a dependent ratio is
unavailable. Missing facts, incompatible periods or scopes, blocking source
flags, insufficient precision and unsupported calculations need distinct reasons.
None of them is permission to substitute zero or choose a convenient fallback.

The current core convention is an absent result (`None`) with explicit flags.
**N/A** for missing or unsupported data and **N/M** for mathematically unsuitable
ratios are proposed interface wording; those product status and coverage rules
are still being reviewed. These labels should explain the gap, not conceal its
source.

EPS and its reconstruction, debt/returns metrics, price-based valuation ratios,
freshness and interpretation policies, complete historical collection and the
guided screen belong to later slices of the [S5 plan](../milestones/S5-ratios.md)
and its S4/S6/S8 prerequisites. This chapter will gain verified screen
instructions and a five-minute company walkthrough when those features exist.

## Fiscal years and comparable periods

A fiscal year is a company's reporting year; it need not start in January. Some
companies report in 52- or 53-week years. The engine can assemble their reported
flows when exact fiscal boundaries have reviewed source evidence. TTM here means
four consecutive fiscal quarters, with their actual dates retained. It does not
scale amounts to a standard number of days.

Growth comparisons need matching quarter/year positions and compatible filing
editions. Unequal 52/53-week exposures and irregular transition years currently
show N/A. The original reported amounts and sources remain available. These are
engine capabilities; they do not indicate a live fiscal calendar or published
financial result for your watchlist.

## Applicability, freshness and coverage

**Applicability** means whether a metric suits the company's reviewed business
model, lifecycle and instrument. It does not mean that the source happens to
supply the data. A specialized business may retain factual rows while its
interpretation is unavailable.

**Freshness** measures age against an explicit policy at the analysis date. A
missing expected filing can also make a metric stale. A stale result may retain
its original number and date, but cannot drive a financial interpretation.
**N/M** means the ratio is mathematically unsuitable, such as division by a
nonpositive or precision-indistinguishable denominator. Missing required inputs
remain **N/A** in the interface.

**Coverage** measures completeness, not investment quality. It counts complete
valid or evidenced N/M metrics against every applicable metric, including those
with missing inputs. Stale, missing, invalid and unsupported counts stay
separate. Unknown applicability or no applicable metrics gives no percentage.

A **growth-rate trend** compares three consecutive quarterly year-over-year
rates. Rising rates can still be negative: −10%, −8%, −6% means revenue is still
falling year over year while the rate of decline narrows. The comparison uses a
versioned sensitivity policy; it is not a healthy/unhealthy or buy/sell boundary.

A **balance-sheet reconciliation** checks whether assets equal liabilities plus
consolidated equity including noncontrolling interests, allowing only the
uncertainty supported by the sources. A mismatch flags the original figures
for review; it does not change them. Negative equity is retained, and parent or
common equity cannot silently replace consolidated equity.

These tested engine functions are ready for the S6 integration review. There is
no new live-data control or published watchlist analysis in this checkpoint;
the saved pilot and existing interface remain unchanged.
