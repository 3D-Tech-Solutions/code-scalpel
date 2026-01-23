# [20250219_TEST] Increase coverage for integration wrappers (Autogen, CrewAI).
# [20251214_REFACTOR] Drop unused asyncio import flagged by ruff.

import pytest

from code_scalpel.integrations.autogen import AnalysisResult, AutogenScalpel
from code_scalpel.integrations.crewai import CrewAIScalpel


@pytest.mark.asyncio
async def test_autogen_analyze_and_refactor_async():
    code = """\
from math import sqrt

def foo(x):
    return sqrt(x) + 1
"""
    scalpel = AutogenScalpel(cache_enabled=False)

    analysis = await scalpel.analyze_async(code)
    assert analysis.error is None
    assert analysis.ast_analysis.get("parsed") is True

    refactored = await scalpel.refactor_async(code)
    assert refactored.error is None
    assert refactored.refactored_code is not None


@pytest.mark.asyncio
async def test_crewai_analyze_and_refactor_async():
    code = """\
def greet(name: str) -> str:
    return f"Hello {name}"
"""
    scalpel = CrewAIScalpel(cache_enabled=False)

    analysis = await scalpel.analyze_async(code)
    assert analysis.success is True
    assert analysis.analysis.get("parsed") is True

    refactored = await scalpel.refactor_async(code)
    assert refactored.success is True
    assert refactored.refactored_code is not None


def test_crewai_symbolic_and_security_analysis():
    scalpel = CrewAIScalpel(cache_enabled=False)

    symbolic_result = scalpel.analyze_symbolic("""\
import math

def branch(x: int) -> int:
    if x > 0:
        return x + 1
    return -x
""")
    assert symbolic_result["success"] is True
    assert symbolic_result["total_paths"] >= 1

    security_result = scalpel.analyze_security("""\
def safe_path(value: str) -> str:
    return value.replace("..", "")
""")
    assert security_result["success"] is True
    assert security_result.get("risk_level") in {"low", "medium", "high", "critical"}


def test_autogen_generate_suggestions_for_style_and_security():
    scalpel = AutogenScalpel(cache_enabled=False)
    analysis_result = AnalysisResult(
        code="def long_function():\n    pass",
        style_issues={
            "long_functions": ["long_function"],
            "naming_conventions": ["LongFunction"],
        },
        security_issues=[{"type": "dangerous_function", "function": "eval"}],
    )

    suggestions = scalpel._generate_suggestions(analysis_result)
    assert any("long functions" in item for item in suggestions)
    assert any("naming conventions" in item for item in suggestions)
    assert any("dangerous function 'eval'" in item for item in suggestions)


def test_autogen_tool_description_structure():
    scalpel = AutogenScalpel(cache_enabled=False)
    description = scalpel.get_tool_description()

    assert description["name"] == "code_scalpel_analyzer"
    assert "parameters" in description
    assert description["parameters"]["code"].startswith("Python source code")


def test_crewai_risk_calculation_and_recommendations():
    scalpel = CrewAIScalpel(cache_enabled=False)

    critical_risk = scalpel._calculate_risk_from_vulns([{"type": "Command Injection"}])
    high_risk = scalpel._calculate_risk_from_vulns([{"type": "Path Traversal"}])
    low_risk = scalpel._calculate_risk_from_vulns([])

    assert critical_risk == "critical"
    assert high_risk == "high"
    assert low_risk == "low"

    issues = [
        {"type": "dangerous_function", "function": "os.system"},
        {"type": "dangerous_function", "function": "eval"},
        {"type": "sql_injection"},
    ]
    risk_level = scalpel._calculate_risk_level(issues)
    recommendations = scalpel._get_security_recommendations(issues)

    assert risk_level == "critical"
    assert any("os.system" in item for item in recommendations)
    assert any("parameterized queries" in item for item in recommendations)


def test_crewai_suggestions_and_tools_definition():
    scalpel = CrewAIScalpel(cache_enabled=False)
    suggestions = scalpel._generate_suggestions(
        style_issues={
            "long_functions": ["alpha"],
            "deep_nesting": ["beta"],
            "naming_conventions": ["Gamma"],
        },
        security_issues=[
            {"type": "dangerous_function", "function": "subprocess.call"},
            {"type": "sql_injection", "function": "execute"},
        ],
    )

    assert any("long functions" in item for item in suggestions)
    assert any("nesting depth" in item for item in suggestions)
    assert any("PEP 8" in item for item in suggestions)
    assert any("Replace dangerous functions" in item for item in suggestions)
    assert any("parameterized queries" in item for item in suggestions)

    tools = scalpel.get_crewai_tools()
    assert {t["name"] for t in tools} == {
        "analyze_code",
        "refactor_code",
        "security_scan",
    }
