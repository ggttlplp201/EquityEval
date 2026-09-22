"""Explicit finite-difference elasticity; no significance or probability claims."""

from decimal import Decimal, localcontext

from equity_core.valuation import CONTEXT


def elasticity(inputs: tuple[Decimal, ...], outputs: tuple[Decimal | None, ...]) -> Decimal | None:
    if (
        len(inputs) != 3
        or len(outputs) != 3
        or not inputs[0] < inputs[1] < inputs[2]
        or inputs[1] == 0
        or any(v is None for v in outputs)
        or outputs[1] == 0
    ):
        return None
    low, reference, high = outputs
    assert low is not None and reference is not None and high is not None
    with localcontext(CONTEXT):
        return ((high - low) / reference) / ((inputs[2] - inputs[0]) / inputs[1])


def ranks(values: tuple[Decimal | None, ...]) -> tuple[int | None, ...]:
    with localcontext(CONTEXT):
        return tuple(
            None
            if value is None
            else 1 + sum(1 for other in values if other is not None and abs(other) > abs(value))
            for value in values
        )
