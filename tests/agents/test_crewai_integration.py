"""
[20251214_TEST] Coverage for CrewAIScalpel analysis and refactor flows.
"""

import asyncio

from code_scalpel.integrations.crewai import CrewAIScalpel


async def _run_coro(coro):
    return await coro


def test_analyze_success_and_suggestions():
    code = """
import math

def square(x: int) -> int:
    return x * x
"""
    scalpel = CrewAIScalpel(cache_enabled=False)
    result = scalpel.analyze(code)
    assert result.success
    assert result.analysis["parsed"] is True
    assert result.analysis["total_issues"] >= 0


def test_analyze_syntax_error_sets_failure():
    scalpel = CrewAIScalpel(cache_enabled=False)
    result = scalpel.analyze("def broken(")
    assert result.success is False
    assert "Syntax error" in result.error


def test_refactor_returns_code():
    code = """

def greet(name):
    return f"hi {name}"
"""
    scalpel = CrewAIScalpel(cache_enabled=False)
    result = scalpel.refactor(code)
    assert result.success
    assert result.refactored_code is not None


def test_analyze_symbolic_async_executes_event_loop():
    code = """

def branch(x):
    if x > 0:
        return 1
    return -1
"""
    scalpel = CrewAIScalpel(cache_enabled=False)
    # [20260118_TEST] Ensure an event loop exists when running under pytest on Python 3.13+.
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    symbolic_result = loop.run_until_complete(_run_coro(scalpel.analyze_symbolic_async(code)))
    assert isinstance(symbolic_result, dict)
    assert "paths" in symbolic_result


# [20251214_TEST] Risk calculation branches for security results.
def test_calculate_risk_from_vulns_levels():
    scalpel = CrewAIScalpel(cache_enabled=False)

    critical = [{"type": "SQL Injection"}]
    high = [{"type": "Cross-Site Scripting (XSS)"}]
    medium = [{"type": "Other"}]

    assert scalpel._calculate_risk_from_vulns(critical) == "critical"
    assert scalpel._calculate_risk_from_vulns(high) == "high"
    assert scalpel._calculate_risk_from_vulns(medium) == "medium"
    assert scalpel._calculate_risk_from_vulns([]) == "low"


# [20251214_TEST] Exception paths for symbolic and security analysis.
def test_analyze_symbolic_handles_runtime_errors(monkeypatch):
    scalpel = CrewAIScalpel(cache_enabled=False)

    class _Boom:
        def analyze(self, code):
            raise RuntimeError("symbolic-fail")

    import sys
    import types

    fake_module = types.SimpleNamespace(SymbolicAnalyzer=_Boom)
    monkeypatch.setitem(sys.modules, "code_scalpel.symbolic_execution_tools", fake_module)

    result = scalpel.analyze_symbolic("x = 1")
    assert result["success"] is False
    assert "symbolic-fail" in result["error"]


def test_analyze_security_fallback_on_import_error(monkeypatch):
    scalpel = CrewAIScalpel(cache_enabled=False)

    def _fake_import(name, *args, **kwargs):
        if name.endswith("symbolic_execution_tools"):
            raise ImportError("missing symbolic tools")
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", _fake_import)

    result = scalpel.analyze_security("value = 1")
    assert result["success"] is True
    assert result.get("analyzer") == "ast-based (fallback)"
