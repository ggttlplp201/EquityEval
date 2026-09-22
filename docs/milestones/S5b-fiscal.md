# S5b — Reviewed fiscal periods

Date: 2026-09-22. Baseline `7191276`; branch `codex/source-bootstrap`.
Scope: [fiscal calendar design](../design/s5/fiscal-calendars.md), within the
[remaining S5 plan](../design/s5/completion-plan.md).

Implemented explicit issuer/input-bound fiscal calendar evidence for annual,
four-quarter TTM, YTD subtraction and annual/YTD bridges. Equal-exposure fiscal
YoY and reviewed cross-edition comparisons retain their proof. No normalized
fact, schema, API, source service, application data or UI changed.

Red: new module absent; then three growth/calendar assertions failed before the
extension. Green: 24 new fiscal tests and all **321 core tests** passed.
Independent numeric/spec and standards reviews of staged diff against `7191276`
reported no actionable findings. Full lint/typecheck/test/core/golden gates run
through the mandatory commit hook; the named tag records final counts.

Next: versioned applicability/freshness, neutral observations and available
accounting validation, then S5 acceptance disposition and the S6 proposal.
The broader S5/F1 feature is not declared complete by this checkpoint.
