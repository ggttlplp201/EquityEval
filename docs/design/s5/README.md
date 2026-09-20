# S5 calculation checkpoint

The first bounded implementation follows planning commit `c1f2697` and the user's
“implement the next step” instruction. Branch: `codex/s5-source-metrics`.
The milestone record is [S5 ratios and fundamentals](../../milestones/S5-ratios.md).

- [Source-metric boundary](source-metrics.md): supported inputs/formulas and limits.
- [Period assembly](period-assembly.md): the source-preserving prerequisite completed before X1.
- [Metric inventory](metric-inventory.md): complete original S5 backlog disposition.
- [Numeric review and validation](review.md): findings, repairs and evidence.
- [User manual chapter](../../user-manual/fundamentals.md): terms and worked examples.

Implementation: [inputs](../../../packages/core/inputs.py),
[metrics](../../../packages/core/metrics.py), [history](../../../packages/core/history.py).
Tests: [core suite](../../../tests/core/README.md). The code is pure and internal;
public API, persistence, actual historical collection and UI remain later work.
