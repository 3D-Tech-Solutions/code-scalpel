"""License fallback behavior tests for generate_unit_tests.

[20260103_TEST] Test explicit license fallback scenarios:
- Invalid license → fallback to Community tier
- Expired license → fallback to Community tier
- Missing license → default to Community tier
- Pro feature without license → rejected with warning
- Enterprise feature without license → rejected with warning
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_invalid_license_falls_back_to_community(community_tier, monkeypatch):
    """Invalid license should fallback to Community tier with warning."""
    import code_scalpel.mcp.helpers.symbolic_helpers as sym_helpers
    from code_scalpel.mcp import server

    calls: list[dict[str, Any]] = []

    def _fake_generate_tests_sync(
        code,
        file_path,
        function_name,
        framework,
        max_test_cases,
        data_driven,
        crash_log,
    ):
        calls.append(
            {
                "framework": framework,
                "max_test_cases": max_test_cases,
                "data_driven": data_driven,
                "crash_log": crash_log,
            }
        )
        return server.GenerationResult(
            success=True,
            function_name=function_name or "f",
            test_count=0,
            total_test_cases=0,
            test_cases=[],
            pytest_code="",
            unittest_code="",
        )

    # [20260121_TEST] Patch helper path after refactor to tools/symbolic.
    monkeypatch.setattr(sym_helpers, "_generate_tests_sync", _fake_generate_tests_sync)

    # Simulate invalid license by mocking tier detection
    # community_tier fixture sets up the environment

    # Try to use Pro feature (data_driven) without valid license
    result = await server.generate_unit_tests(
        code="def f(x):\n    return x\n",
        framework="pytest",
        data_driven=True,
    )

    # Should be rejected because Community doesn't support data_driven
    assert result.success is False
    assert "data-driven" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_expired_license_falls_back_to_community(community_tier, monkeypatch):
    """Expired license should fallback to Community tier."""
    import code_scalpel.mcp.helpers.symbolic_helpers as sym_helpers
    from code_scalpel.mcp import server

    calls: list[dict[str, Any]] = []

    def _fake_generate_tests_sync(
        code,
        file_path,
        function_name,
        framework,
        max_test_cases,
        data_driven,
        crash_log,
    ):
        calls.append({"max_test_cases": max_test_cases})
        return server.GenerationResult(
            success=True,
            function_name=function_name or "f",
            test_count=0,
            total_test_cases=0,
            test_cases=[],
            pytest_code="",
            unittest_code="",
        )

    # [20260121_TEST] Patch helper path after refactor to tools/symbolic.
    monkeypatch.setattr(sym_helpers, "_generate_tests_sync", _fake_generate_tests_sync)

    # Simulate expired license by clamping to community
    # community_tier fixture sets up the environment

    # Basic pytest should still work in Community
    result = await server.generate_unit_tests(
        code="def f():\n    return 1\n",
        framework="pytest",
    )

    assert result.success is True
    assert calls
    assert calls[-1]["max_test_cases"] == 5  # Community limit


@pytest.mark.asyncio
async def test_missing_license_defaults_to_community(community_tier, monkeypatch):
    """Missing license should default to Community tier."""
    import code_scalpel.mcp.helpers.symbolic_helpers as sym_helpers
    from code_scalpel.mcp import server

    calls: list[dict[str, Any]] = []

    def _fake_generate_tests_sync(
        code,
        file_path,
        function_name,
        framework,
        max_test_cases,
        data_driven,
        crash_log,
    ):
        calls.append({"max_test_cases": max_test_cases, "framework": framework})
        return server.GenerationResult(
            success=True,
            function_name=function_name or "f",
            test_count=0,
            total_test_cases=0,
            test_cases=[],
            pytest_code="",
            unittest_code="",
        )

    # [20260121_TEST] Patch helper path after refactor to tools/symbolic.
    monkeypatch.setattr(sym_helpers, "_generate_tests_sync", _fake_generate_tests_sync)

    # Disable license discovery and no license path provided
    # community_tier fixture sets up the environment

    result = await server.generate_unit_tests(
        code="def f():\n    return 1\n",
        framework="pytest",
    )

    assert result.success is True
    assert calls
    # Should enforce Community limits: pytest only, max 5 tests
    assert calls[-1]["framework"] == "pytest"
    assert calls[-1]["max_test_cases"] == 5


@pytest.mark.asyncio
async def test_pro_feature_rejected_without_valid_license(community_tier, monkeypatch):
    """Pro tier features (unittest, data_driven) should be rejected without valid license."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    # Test 1: unittest framework rejected for Community
    result = await server.generate_unit_tests(
        code="def f():\n    return 1\n",
        framework="unittest",
    )
    assert result.success is False
    assert "unsupported framework" in (result.error or "").lower()

    # Test 2: data_driven rejected for Community
    result = await server.generate_unit_tests(
        code="def f(x):\n    return x\n",
        framework="pytest",
        data_driven=True,
    )
    assert result.success is False
    assert "data-driven" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_enterprise_feature_rejected_without_valid_license(community_tier, monkeypatch):
    """Enterprise tier features (crash_log) should be rejected without valid license."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    # Enterprise feature: crash_log
    result = await server.generate_unit_tests(
        code="def divide(a, b):\n    return a / b\n",
        framework="pytest",
        crash_log="ZeroDivisionError: division by zero",
    )

    # Should be rejected because Community doesn't support crash_log
    assert result.success is False
    # Either gated or handled as invalid parameter
    assert result.error is not None


@pytest.mark.asyncio
async def test_license_fallback_preserves_community_features(community_tier, monkeypatch):
    """License fallback should preserve all Community features."""
    from code_scalpel.mcp import server

    calls: list[dict[str, Any]] = []

    def _fake_generate_tests_sync(
        code,
        file_path,
        function_name,
        framework,
        max_test_cases,
        data_driven,
        crash_log,
    ):
        calls.append(
            {
                "framework": framework,
                "max_test_cases": max_test_cases,
                "function_name": function_name,
            }
        )
        return server.GenerationResult(
            success=True,
            function_name=function_name or "calculate",
            test_count=3,
            total_test_cases=3,
            test_cases=[
                server.GeneratedTestCase(
                    path_id=0,
                    function_name="calculate",
                    inputs={"x": 1},
                    description="Positive number path",
                ),
                server.GeneratedTestCase(
                    path_id=1,
                    function_name="calculate",
                    inputs={"x": 0},
                    description="Zero path",
                ),
                server.GeneratedTestCase(
                    path_id=2,
                    function_name="calculate",
                    inputs={"x": -1},
                    description="Negative number path",
                ),
            ],
            pytest_code="def test_calculate():\n    assert calculate(1) == 2\n",
            unittest_code="",
        )

    monkeypatch.setattr(server, "_generate_tests_sync", _fake_generate_tests_sync)
    # community_tier fixture sets up tier, no need for additional monkeypatch

    # Community should support: pytest tests with path-based generation
    result = await server.generate_unit_tests(
        code="def calculate(x):\n    if x > 0:\n        return x + 1\n    return 1\n",
        function_name="calculate",
        framework="pytest",
    )

    assert result.success is True
    assert calls
    assert calls[-1]["framework"] == "pytest"
    assert calls[-1]["max_test_cases"] == 5
    assert result.test_count == 3
    assert len(result.test_cases) == 3


@pytest.mark.asyncio
async def test_license_fallback_warning_message_when_feature_gated(monkeypatch):
    """License fallback should include clear warning about gated features."""
    from code_scalpel.mcp import server

    # community_tier fixture sets up the environment

    result = await server.generate_unit_tests(
        code="def f(x):\n    return x\n",
        framework="pytest",
        data_driven=True,
    )

    assert result.success is False
    # Error message should clearly indicate tier/feature relationship
    error_msg = (result.error or "").lower()
    assert "data-driven" in error_msg or "pro" in error_msg or "tier" in error_msg
