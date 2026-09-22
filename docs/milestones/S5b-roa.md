# S5b — Annual return-on-assets follow-on

Status: complete for the bounded reported-annual calculation; full S5 remains in progress.
Baseline: 5f02303 / milestone/s5b-liquidity.
Checkpoint: milestone/s5b-roa.

The user requested continuing implementation after the liquidity slice. Added
pure annual return_on_assets using existing selected consolidated net income,
opening/closing total-assets evidence and Calculation output. The
[design boundary](../design/s5/return-on-assets.md) defines exact dates, same-edition
scope and source-precision guards. Neither ending assets alone nor a positive
average can substitute for two eligible endpoints. Loss and zero income remain
valid outcomes. The source-period assembler and existing Decimal helpers are reused.

Tests were written before the implementation; 123 targeted ROA/liquidity/flow/
period cases and all 297 core tests passed. Ruff/strict mypy passed. Independent
numeric and standards reviews found no issues. The mandatory commit gate verifies
the final full/core/golden suites and static checks; counts are recorded in the
annotated tag.
The manual adds the definition and a worked example. No UI, provider, schema,
public API or application-data changes; missing published values remain N/A.

Next: remaining supported S5 definitions and interpretation, then reviewed S6
publication. ROE/common equity, debt composition, EPS/share actions, assembled
TTM ROA and irregular fiscal calendars retain their existing prerequisites.
