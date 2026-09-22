"""The public TypeScript contract must retain discriminated assumption values."""

from scripts.generate_valuation_api import outputs


def test_bound_judgments_generate_a_typed_union():
    ts = next(text for path, text in outputs().items() if path.suffix == ".ts")
    binding = next(line for line in ts.splitlines() if 'readonly "binding"' in line)
    assert "unknown" not in binding
    for name in (
        "ScalarBinding",
        "VectorBinding",
        "SolvedBinding",
        "ScheduleBinding",
        "SolverBinding",
    ):
        assert name in binding
