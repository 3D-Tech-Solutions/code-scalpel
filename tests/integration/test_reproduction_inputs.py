"""Tests for concrete reproduction inputs from symbolic execution.

This covers the Z3 model marshaling path to ensure `reproduction_input`
is populated with usable concrete assignments for reachable paths.
"""

from code_scalpel.mcp.server import _symbolic_execute_sync


def _path_by_condition(paths, text):
    """Helper to pick a path containing a condition snippet."""
    return next(p for p in paths if any(text in c for c in p.conditions))


def test_symbolic_execute_returns_concrete_inputs():
    """[20251214_TEST] Ensure reachable paths carry concrete input models."""

    code = """
from code_scalpel.symbolic_execution_tools import symbolic

x = symbolic("x", int)
if x > 0:
    y = x + 1
else:
    y = x - 1
"""

    result = _symbolic_execute_sync(code)

    assert result.success
    assert result.paths_explored == 2

    # All reachable paths should expose concrete reproduction inputs.
    reachable = [p for p in result.paths if p.is_reachable]
    assert all(p.reproduction_input for p in reachable)

    positive = _path_by_condition(reachable, "0 < x")
    negative = _path_by_condition(reachable, "Not(0 < x)")

    # Positive branch: x > 0 → y = x + 1
    x_pos = positive.reproduction_input["x"]
    assert x_pos > 0
    assert positive.final_state["y"] == x_pos + 1

    # Negative branch: x <= 0 → y = x - 1
    x_neg = negative.reproduction_input["x"]
    assert x_neg <= 0
    assert negative.final_state["y"] == x_neg - 1
