"""Determinism and stability tests for generate_unit_tests.

[20260103_TEST] Test that generated tests are deterministic and stable:
- Multiple runs with identical inputs produce identical output
- Test naming is stable (no random UUIDs or timestamps)
- Test ordering is consistent across invocations
- Framework output format is reproducible
- Parametrization is stable
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_deterministic_output_multiple_runs(community_tier):
    """Generated test output should be identical across multiple runs with same input."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    code = """
def classify_number(n):
    if n > 10:
        return "large"
    elif n > 0:
        return "positive"
    elif n == 0:
        return "zero"
    else:
        return "negative"
"""

    # Run 1
    result1 = await server.generate_unit_tests(
        code=code,
        function_name="classify_number",
        framework="pytest",
    )

    # Run 2
    result2 = await server.generate_unit_tests(
        code=code,
        function_name="classify_number",
        framework="pytest",
    )

    # Output should be identical
    assert result1.success is True
    assert result2.success is True
    assert result1.pytest_code == result2.pytest_code
    assert len(result1.test_cases) == len(result2.test_cases)

    # Test case order should be identical
    for tc1, tc2 in zip(result1.test_cases, result2.test_cases, strict=False):
        assert tc1.path_id == tc2.path_id
        assert tc1.inputs == tc2.inputs
        assert tc1.description == tc2.description


@pytest.mark.asyncio
async def test_stable_test_naming_no_random_elements(community_tier):
    """Test names should not contain random elements (UUIDs, timestamps, random IDs)."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    code = """
def is_even(n):
    return n % 2 == 0
"""

    result = await server.generate_unit_tests(
        code=code,
        function_name="is_even",
        framework="pytest",
    )

    assert result.success is True

    # Check test names don't have random elements
    for tc in result.test_cases:
        name = tc.description
        # Should not contain UUID-like patterns (8-4-4-4-12 hex)
        assert "-" not in name or not all(c in "0123456789abcdef-" for c in name.split("-")[0])
        # Should not contain timestamps (too many digits)
        assert not any(len(seg) > 8 and seg.isdigit() for seg in name.split("_"))
        # Should be descriptive
        assert len(name) > 0


@pytest.mark.asyncio
async def test_consistent_test_ordering(community_tier):
    """Test cases should maintain consistent ordering across runs."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    code = """
def get_sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0
"""

    # Multiple runs
    orders = []
    for _ in range(3):
        result = await server.generate_unit_tests(
            code=code,
            function_name="get_sign",
            framework="pytest",
        )
        assert result.success is True
        order = [tc.path_id for tc in result.test_cases]
        orders.append(order)

    # All should have identical ordering
    assert orders[0] == orders[1]
    assert orders[1] == orders[2]


@pytest.mark.asyncio
async def test_framework_output_format_reproducible(community_tier):
    """Framework output (pytest/unittest) should be reproducible."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    code = """
def add(a, b):
    return a + b
"""

    results = []
    for _ in range(2):
        result = await server.generate_unit_tests(
            code=code,
            function_name="add",
            framework="pytest",
        )
        results.append(result)

    # Both should succeed
    assert all(r.success for r in results)

    # Output format should be identical
    assert results[0].pytest_code == results[1].pytest_code
    # Should be valid Python code
    assert "def test_" in results[0].pytest_code
    assert "assert" in results[0].pytest_code


@pytest.mark.asyncio
async def test_parametrized_test_stability_pro_tier(pro_tier):
    """Parametrized tests (Pro tier) should have stable structure."""
    from code_scalpel.mcp import server

    # pro_tier fixture sets up the environment

    code = """
def max_number(a, b):
    if a > b:
        return a
    return b
"""

    results = []
    for _ in range(2):
        result = await server.generate_unit_tests(
            code=code,
            function_name="max_number",
            framework="pytest",
            data_driven=True,
        )
        results.append(result)

    # Both should succeed
    assert all(r.success for r in results)

    # Output should be identical
    assert results[0].pytest_code == results[1].pytest_code

    # Pro tier data_driven is allowed, regardless of whether @pytest.mark.parametrize is used
    # (depends on symbolic execution findings, not data_driven flag)
    assert "import pytest" in results[0].pytest_code
    assert len(results[0].test_cases) > 0


@pytest.mark.asyncio
async def test_determinism_with_complex_control_flow(community_tier):
    """Determinism should hold for complex control flow."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    code = """
def grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
"""

    # Get output multiple times
    outputs = []
    for _ in range(3):
        result = await server.generate_unit_tests(
            code=code,
            function_name="grade",
            framework="pytest",
        )
        assert result.success is True
        outputs.append(result.pytest_code)

    # All outputs should be identical
    assert outputs[0] == outputs[1]
    assert outputs[1] == outputs[2]


@pytest.mark.asyncio
async def test_consistency_across_frameworks(pro_tier):
    """Same test cases should be stable whether pytest or unittest."""
    from code_scalpel.mcp import server

    # pro_tier fixture sets up the environment

    code = """
def double(x):
    return x * 2
"""

    # Generate pytest version twice
    pytest_results = []
    for _ in range(2):
        result = await server.generate_unit_tests(
            code=code,
            function_name="double",
            framework="pytest",
        )
        pytest_results.append(result)

    # Generate unittest version twice
    unittest_results = []
    for _ in range(2):
        result = await server.generate_unit_tests(
            code=code,
            function_name="double",
            framework="unittest",
        )
        unittest_results.append(result)

    # pytest versions should match each other
    assert pytest_results[0].pytest_code == pytest_results[1].pytest_code

    # unittest versions should match each other
    assert unittest_results[0].unittest_code == unittest_results[1].unittest_code

    # Test cases should be stable regardless of framework
    assert len(pytest_results[0].test_cases) == len(unittest_results[0].test_cases)


@pytest.mark.asyncio
async def test_determinism_with_boundary_values(community_tier):
    """Boundary value tests should be generated deterministically."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    code = """
def in_range(x, min_val, max_val):
    if x < min_val:
        return False
    if x > max_val:
        return False
    return True
"""

    # Run multiple times
    results = []
    for _ in range(3):
        result = await server.generate_unit_tests(
            code=code,
            function_name="in_range",
            framework="pytest",
        )
        results.append(result)

    # All should succeed
    assert all(r.success for r in results)

    # Code output should be identical
    assert results[0].pytest_code == results[1].pytest_code
    assert results[1].pytest_code == results[2].pytest_code

    # Test case count should be stable
    assert len(results[0].test_cases) == len(results[1].test_cases)
    assert len(results[1].test_cases) == len(results[2].test_cases)
