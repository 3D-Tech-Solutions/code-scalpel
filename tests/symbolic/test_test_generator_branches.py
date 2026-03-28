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
    js_name = gen._detect_main_function(
        "function run() { return 1; }", language="javascript"
    )
    assert js_name == "run"
    java_name = gen._detect_main_function(
        "public int calc() { return 1; }", language="java"
    )
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


def test_generate_unit_tests_infers_distinct_java_returns_for_branches():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    String classify(int x) {
        if (x > 10) {
            return "danger";
        }
        if (x > 0) {
            return "warn";
        }
        return "safe";
    }
}
"""

    suite = gen.generate(code, function_name="classify", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 3
    assert all(tc.path_conditions != ["x > 10", "!(x > 0)"] for tc in suite.test_cases)
    assert "assert result == 'danger'" in pytest_code
    assert "assert result == 'warn'" in pytest_code
    assert "assert result == 'safe'" in pytest_code


def test_generate_unit_tests_infers_java_expression_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int bump(int x) {
        if (x > 0) {
            return x + 1;
        }
        return x - 1;
    }
}
"""

    suite = gen.generate(code, function_name="bump", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 2
    assert "assert result == 2" in pytest_code
    assert "assert result == -1" in pytest_code


def test_generate_unit_tests_infers_java_ternary_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    String classify(boolean flag) {
        return flag ? "yes" : "no";
    }
}
"""

    suite = gen.generate(code, function_name="classify", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 2
    assert any(tc.inputs == {"flag": True} for tc in suite.test_cases)
    assert any(tc.inputs == {"flag": False} for tc in suite.test_cases)
    assert "assert result == 'yes'" in pytest_code
    assert "assert result == 'no'" in pytest_code


def test_generate_unit_tests_infers_java_local_and_field_values():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int delta = 2;

    int add(int x) {
        int y = x + 1;
        return y + delta;
    }
}
"""

    suite = gen.generate(code, function_name="add", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 1
    assert any(
        tc.inputs == {"x": 0} and tc.expected_result == 3 for tc in suite.test_cases
    )
    assert "assert result == 3" in pytest_code


def test_generate_unit_tests_uses_requested_java_method():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int first() {
        return 1;
    }

    int second() {
        return 2;
    }
}
"""

    suite = gen.generate(code, function_name="second", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 1
    assert any(tc.expected_result == 2 for tc in suite.test_cases)
    assert "assert result == 2" in pytest_code


def test_generate_unit_tests_infers_java_this_field_value():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int delta = 2;

    int add() {
        return this.delta;
    }
}
"""

    suite = gen.generate(code, function_name="add", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 1
    assert any(tc.expected_result == 2 for tc in suite.test_cases)
    assert "assert result == 2" in pytest_code


def test_generate_unit_tests_infers_java_branch_assignment_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int adjust(int x) {
        int y = 0;
        if (x > 0) {
            y = 2;
        }
        return y;
    }
}
"""

    suite = gen.generate(code, function_name="adjust", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 2
    assert any(
        tc.inputs == {"x": 1} and tc.expected_result == 2 for tc in suite.test_cases
    )
    assert any(
        tc.inputs == {"x": 0} and tc.expected_result == 0 for tc in suite.test_cases
    )
    assert "assert result == 2" in pytest_code
    assert "assert result == 0" in pytest_code


def test_generate_unit_tests_infers_java_if_else_assignment_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int adjust(int x) {
        int y = 0;
        if (x > 0) {
            y = 2;
        } else {
            y = -2;
        }
        return y;
    }
}
"""

    suite = gen.generate(code, function_name="adjust", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 2
    assert any(
        tc.inputs == {"x": 1} and tc.expected_result == 2 for tc in suite.test_cases
    )
    assert any(
        tc.inputs == {"x": 0} and tc.expected_result == -2 for tc in suite.test_cases
    )
    assert "assert result == 2" in pytest_code
    assert "assert result == -2" in pytest_code


def test_generate_unit_tests_infers_java_augmented_assignment_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int adjust() {
        int y = 1;
        y += 2;
        return y;
    }
}
"""

    suite = gen.generate(code, function_name="adjust", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 1
    assert any(tc.expected_result == 3 for tc in suite.test_cases)
    assert "assert result == 3" in pytest_code


def test_generate_unit_tests_infers_java_branch_augmented_assignment_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int adjust(int x) {
        int y = 1;
        if (x > 0) {
            y += 2;
        }
        return y;
    }
}
"""

    suite = gen.generate(code, function_name="adjust", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 2
    assert any(
        tc.inputs == {"x": 1} and tc.expected_result == 3 for tc in suite.test_cases
    )
    assert any(
        tc.inputs == {"x": 0} and tc.expected_result == 1 for tc in suite.test_cases
    )
    assert "assert result == 3" in pytest_code
    assert "assert result == 1" in pytest_code


def test_generate_unit_tests_infers_java_this_field_augmented_assignment_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int delta = 1;

    int adjust() {
        this.delta += 2;
        return this.delta;
    }
}
"""

    suite = gen.generate(code, function_name="adjust", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 1
    assert any(tc.expected_result == 3 for tc in suite.test_cases)
    assert "assert result == 3" in pytest_code


def test_generate_unit_tests_infers_java_branch_this_field_augmented_assignment_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int delta = 1;

    int adjust(int x) {
        if (x > 0) {
            this.delta += x;
        }
        return this.delta;
    }
}
"""

    suite = gen.generate(code, function_name="adjust", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 2
    assert any(
        tc.inputs == {"x": 1} and tc.expected_result == 2 for tc in suite.test_cases
    )
    assert any(
        tc.inputs == {"x": 0} and tc.expected_result == 1 for tc in suite.test_cases
    )
    assert "assert result == 2" in pytest_code
    assert "assert result == 1" in pytest_code


def test_generate_unit_tests_infers_java_this_field_assignment_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int delta = 1;

    int adjust() {
        this.delta = this.delta + 2;
        return this.delta;
    }
}
"""

    suite = gen.generate(code, function_name="adjust", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 1
    assert any(tc.expected_result == 3 for tc in suite.test_cases)
    assert "assert result == 3" in pytest_code


def test_generate_unit_tests_infers_java_branch_this_field_assignment_returns():
    gen = TestGenerator(framework="pytest")
    code = """
class Demo {
    int delta = 1;

    int adjust(int x) {
        if (x > 0) {
            this.delta = this.delta + x;
        }
        return this.delta;
    }
}
"""

    suite = gen.generate(code, function_name="adjust", language="java")
    pytest_code = suite.pytest_code

    assert len(suite.test_cases) == 2
    assert any(
        tc.inputs == {"x": 1} and tc.expected_result == 2 for tc in suite.test_cases
    )
    assert any(
        tc.inputs == {"x": 0} and tc.expected_result == 1 for tc in suite.test_cases
    )
    assert "assert result == 2" in pytest_code
    assert "assert result == 1" in pytest_code
