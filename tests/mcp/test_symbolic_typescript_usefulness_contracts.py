"""Public usefulness-contract tests for TypeScript symbolic and test-generation boundaries.

[20260315_TEST] Keep the documented TypeScript slice honest at the MCP boundary:
- symbolic_execute: Bounded Useful (IR-backed control-flow paths, not full TS semantics)
- generate_unit_tests: Bounded Useful (concrete TS path cases plus scaffold output)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_symbolic_execute_typescript_is_bounded_useful() -> None:
    from code_scalpel.mcp.server import symbolic_execute

    ts_code = """
export function classify(x: number): number {
    if (x > 0) {
        return x;
    }
    return 0;
}
"""

    result = await symbolic_execute(ts_code, language="typescript")

    assert result.success is True
    assert result.error is None
    assert result.paths_explored >= 2
    assert "x" in result.symbolic_variables
    assert any(
        "x" in constraint and ("<" in constraint or ">" in constraint)
        for constraint in result.constraints
    )
    assert any(
        "x" in condition for path in result.paths for condition in path.conditions
    )


async def test_generate_unit_tests_typescript_is_bounded_useful() -> None:
    from code_scalpel.mcp.server import generate_unit_tests

    ts_code = """
export function classify(x: number): number {
    if (x > 0) {
        return 1;
    }
    return 0;
}
"""

    result = await generate_unit_tests(
        code=ts_code,
        language="typescript",
        framework="pytest",
    )

    assert result.success is True
    assert result.function_name == "classify"
    assert result.framework_used == "pytest"
    assert result.test_count >= 2
    assert result.total_test_cases >= 2
    assert any("x" in case.inputs for case in result.test_cases)
    assert any(
        "x" in condition
        for case in result.test_cases
        for condition in case.path_conditions
    )
    assert "scaffold" in result.pytest_code.lower()
    assert "invoke_typescript_case" in result.pytest_code
    compile(result.pytest_code, "<typescript-contract-pytest>", "exec")
