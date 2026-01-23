"""Tier behavior tests for generate_unit_tests.

These tests validate that tier limits and gated parameters are enforced at the
MCP boundary without relying on symbolic execution internals.

[20251231_TEST] Ensure generate_unit_tests tier gating + limits work.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_generate_unit_tests_community_limits_and_framework(monkeypatch):
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

    monkeypatch.setattr(server, "_generate_tests_sync", _fake_generate_tests_sync)
    monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

    # Community: pytest only
    bad = await server.generate_unit_tests(code="def f():\n    return 1\n", framework="unittest")
    assert bad.success is False
    assert "unsupported framework" in (bad.error or "").lower()

    # Community: data_driven gated
    gated = await server.generate_unit_tests(
        code="def f(x):\n    return x\n",
        framework="pytest",
        data_driven=True,
    )
    assert gated.success is False
    assert "data-driven" in (gated.error or "").lower()

    ok = await server.generate_unit_tests(code="def f():\n    return 1\n", framework="pytest")
    assert ok.success is True
    assert calls, "sync path should be invoked for allowed request"
    assert calls[-1]["max_test_cases"] == 5


@pytest.mark.asyncio
async def test_generate_unit_tests_pro_allows_data_driven_and_unittest(monkeypatch):
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

    monkeypatch.setattr(server, "_generate_tests_sync", _fake_generate_tests_sync)
    # [20250108_BUGFIX] Mock _get_current_tier directly since env var only allows downgrade
    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    ok = await server.generate_unit_tests(
        code="def f(x):\n    return x\n",
        framework="unittest",
        data_driven=True,
    )

    assert ok.success is True
    assert calls
    assert calls[-1]["max_test_cases"] == 20
    assert calls[-1]["framework"] == "unittest"
    assert calls[-1]["data_driven"] is True


@pytest.mark.asyncio
async def test_generate_unit_tests_enterprise_allows_bug_repro(monkeypatch):
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
        calls.append({"max_test_cases": max_test_cases, "crash_log": crash_log})
        return server.GenerationResult(
            success=True,
            function_name=function_name or "divide",
            test_count=0,
            total_test_cases=0,
            test_cases=[],
            pytest_code="",
            unittest_code="",
        )

    monkeypatch.setattr(server, "_generate_tests_sync", _fake_generate_tests_sync)
    # [20250108_BUGFIX] Mock _get_current_tier directly since env var only allows downgrade
    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    ok = await server.generate_unit_tests(
        code="def divide(a, b):\n    return a / b\n",
        framework="pytest",
        crash_log="ZeroDivisionError: division by zero",
    )

    assert ok.success is True
    assert calls
    assert calls[-1]["max_test_cases"] is None
    assert calls[-1]["crash_log"]


@pytest.mark.asyncio
async def test_generate_unit_tests_limits_toml_override(monkeypatch, tmp_path):
    """limits.toml should be the source of truth for numeric limits."""
    from code_scalpel.licensing import clear_cache
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

    monkeypatch.setattr(server, "_generate_tests_sync", _fake_generate_tests_sync)

    # Force a custom limits file for this test.
    custom = tmp_path / "limits.toml"
    custom.write_text(
        """
[community.generate_unit_tests]
max_test_cases = 2
test_frameworks = ["pytest"]
""".lstrip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("CODE_SCALPEL_LIMITS_FILE", str(custom))
    clear_cache()
    monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

    ok = await server.generate_unit_tests(code="def f():\n    return 1\n", framework="pytest")
    assert ok.success is True
    assert calls
    assert calls[-1]["max_test_cases"] == 2

    # Cleanup: avoid leaking config into other tests.
    clear_cache()
