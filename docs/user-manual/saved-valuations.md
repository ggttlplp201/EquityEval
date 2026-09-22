# Saved valuations and assumptions

S6b/S7a adds a tested synthetic valuation engine, saved history and a trusted-local
API. The accepted screens are unchanged. The operator workflow below is available
in code; a connected valuation screen and real-company publication come later.

## What the result answers

Reverse DCF asks what growth, operating margin or reinvestment assumption is
required to support a selected dated price. Choose one unknown and give every
other input explicitly. Several named scenarios show how that answer changes
under different assumptions. Their range is deterministic, not a probability or
price target. Conditional repricing instead fixes those assumptions and asks what
per-share value the model produces under them.

A fictional example starts with annual revenue 100, growth 10%, margin 20%, tax
25%, reinvestment/revenue 5%, WACC 10%, terminal growth 2%, terminal ROIC 8%,
five forecast years and explicit bridge adjustment -20. With ten shares, the
model's conditional per-share value is 17.34375. Reversing the same case recovers
10% growth within the declared numerical tolerance. This is an arithmetic
example, not a stock estimate.

## Operator workflow available now

1. Configure `equity_api.valuation.create_app` with a trusted workspace ID and
   idle-autocommit connection factory. It creates no listener or credentials.
   The integration examples in `tests/api/test_valuation_api.py` show the tested
   local setup using a disposable test database.
2. Save assumptions with `POST /assumption-sets`: `parent_id` (null for a new
   set), a unique `idempotency_key`, and the full `content` from the generated
   OpenAPI contract. Provide current authorship time, dated rationales, 5–10
   annual forecast dates, named scenarios and optional explicit sensitivity grids.
   Fractions and financial amounts are Decimal strings: `"0.10"` means 10%.
3. Have the owner fixture path validate the exact saved S6a financial snapshot,
   S4 raw quote and full claims/share evidence using `approve_fixture_manifest`.
   It returns a synthetic review ID. Saving assumptions alone does not approve
   missing source evidence or create an eligible valuation review.
4. `POST /valuation-requests` with that `review_id`, the source or prior valuation
   `parent_request_id`, a fresh `idempotency_key` and `max_attempts`. A 202 response
   means queued. Repeating identical content/key returns the same logical request;
   reusing the key for changed content returns 409.
5. The explicitly invoked W1 worker claims work and calls `run_valuation_stage`.
   Poll `GET /valuation-requests/{request_id}` for execution/stage status and the
   eventual `run_id`. No automatic worker service is installed by this feature.
6. Open `GET /model-runs/{run_id}` to read the exact saved run. The company route
   additionally requires security, quote, scope and compatibility key. It keeps
   the latest requested work separate from the latest compatible saved result.
7. To change assumptions, create a new set with the old `parent_id`, obtain its
   reviewed synthetic inputs, and enqueue with a new key. Earlier assumptions
   and runs remain available. A retry recovers the same request; a rerun records
   a new analysis with its own run ID.

To reproduce the synthetic flow without configuring the application, run
`.venv/bin/python scripts/project_python.py scripts/run_tests.py tests/integration/test_valuation_publication.py tests/api/test_valuation_api.py`
from the repository. The test harness targets disposable test stores, not the
application database. It requires the project's documented test runtime setup.

## Reading outcomes

| Outcome | Meaning |
| --- | --- |
| Converged | One root certified across the requested domain, within stated tolerances. |
| No solution in domain | The model proves there is no root inside the declared bounds. |
| Non-unique | More than one root is certified; no single implied assumption is shown. |
| Inconclusive | The solver cannot certify the whole domain within its limits. |
| Unavailable | A required input, model basis or source proof is unavailable. |

Unavailable values display as **N/A**. Individual scenario outcomes remain even
when the complete scenario range cannot be shown. Negative modeled equity is
retained with its diagnostic; it is not silently clipped to zero. Terminal
contribution is N/M when EV is nonpositive. A terminal share above 75% is flagged.

Keep three forms of uncertainty separate: the **numerical interval** brackets a
root to computational tolerance; the **scenario span** compares chosen
assumptions; **source measurement uncertainty** records precision of source facts.
None of these is a statistical confidence interval.

## Terms

| Term | Meaning |
| --- | --- |
| Fact / assumption / conclusion | Retained evidence / explicit dated judgment / calculated output. |
| CAGR | Compound annual growth rate, expressed here as a fraction. |
| EBIT | Operating earnings before interest and tax. |
| NOPAT | Operating earnings after the model's cash tax. |
| Net reinvestment | Net capital spending plus change in noncash operating working capital. |
| FCFF | Free cash flow available to all capital providers: NOPAT minus net reinvestment. |
| WACC | Weighted average cost of capital used to discount operating cash flows. Supplied explicitly here. |
| ROIC | Return on invested capital; terminal ROIC links growth to required reinvestment. |
| Terminal value | Value of cash flows beyond the explicit forecast period under terminal assumptions. |
| Operating EV | Present value of modeled operating cash flows. |
| Common equity | Operating EV adjusted for cash/nonoperating assets and senior/other claims. |
| Margin fade | Explicit path from anchor margin to the solved terminal margin. |
| Sensitivity / elasticity | Change in modeled output as a declared input changes / proportional response under the specified three-point method. |
| Retrospective | Assumptions authored after the valuation date; they were not known at that date. |
| Forecast horizon / history window | Future model years / past comparison years. Existing 3/5/10-year history options remain separate from the 5–10-year forecast. |

Every saved result includes model/policy, source identity and dates, bridge claims,
assumptions and numerical evidence. Exact ID reads do not refresh or recalculate.
