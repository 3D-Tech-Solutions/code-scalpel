"""
[20251214_TEST] Additional coverage for TestGenerator branches and fallbacks.
"""

import re

import pytest

from code_scalpel.generators.test_generator import TestGenerator


def test_invalid_framework_raises():
    with pytest.raises(ValueError):
        TestGenerator(framework="nose")


def test_detect_main_function_non_python():
    gen = TestGenerator()
    js_name = gen._detect_main_function("function run() { return 1; }", language="javascript")
    assert js_name == "run"
    java_name = gen._detect_main_function("public int calc() { return 1; }", language="java")
    assert java_name == "calc"


def test_basic_path_analysis_builds_paths_and_constraints():
    gen = TestGenerator()
    code = """

def classify(x):
    if x > 0:
        return 1
    return -1
"""
    result = gen._basic_path_analysis(code, language="python")
    assert result["paths"]
    constraints = result["constraints"]
    assert any("x > 0" in c for c in constraints)
    values = {p["state"]["x"] for p in result["paths"] if "x" in p["state"]}
    assert any(v > 0 for v in values)
    assert any(v < 0 for v in values)


def test_generate_from_symbolic_result_uses_given_paths():
    gen = TestGenerator()
    symbolic = {
        "paths": [
            {
                "path_id": 1,
                "conditions": ["x > 10"],
                "state": {"x": 11},
                "reachable": True,
            }
        ],
        "symbolic_vars": ["x"],
        "constraints": ["x > 10"],
    }
    code = """

def target(x):
    if x > 10:
        return True
    return False
"""
    suite = gen.generate_from_symbolic_result(symbolic, code, function_name="target")
    assert suite.function_name == "target"
    assert suite.test_cases
    pytest_code = suite.pytest_code
    assert "test_target_path_1" in pytest_code
    # [20260507_TEST] Generator emits equality check rather than identity for booleans.
    assert re.search(r"assert result == True", pytest_code)


def test_generate_unit_tests_infers_distinct_expected_returns_for_branches():
    gen = TestGenerator(framework="pytest")
    code = """

def classify(x: int) -> str:
    if x > 0:
        if x > 10:
            return "danger"
        return "warn"
    return "safe"
"""

    suite = gen.generate(code, function_name="classify", language="python")
    pytest_code = suite.pytest_code

    # Ensure we don't regress to asserting the same return for all paths.
    assert "assert result == 'danger'" in pytest_code
    assert "assert result == 'warn'" in pytest_code
    assert "assert result == 'safe'" in pytest_code
