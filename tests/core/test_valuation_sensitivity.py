from decimal import Decimal as D
from decimal import localcontext

import pytest
from equity_core.valuation_sensitivity import elasticity, ranks


def test_hand_computed_conditional_elasticity():
    result = elasticity((D(".1"), D(".2"), D(".3")), (D("6.421875"), D("17.34375"), D("28.265625")))
    with localcontext() as ctx:
        ctx.prec = 80
        assert abs(result - D(233) / 185) < D("1e-70")
    assert ranks((result, D(-2), result, None)) == (2, 1, 2, None)


@pytest.mark.parametrize(
    "inputs,outputs",
    [
        (("-.1", "0", ".1"), ("1", "2", "3")),
        ((".1", ".2", ".3"), ("-1", "0", "1")),
        ((".1", ".1", ".1"), ("1", "2", "3")),
        ((".3", ".2", ".1"), ("1", "2", "3")),
    ],
)
def test_zero_or_unordered_references_are_unavailable(inputs, outputs):
    assert elasticity(tuple(map(D, inputs)), tuple(map(D, outputs))) is None
