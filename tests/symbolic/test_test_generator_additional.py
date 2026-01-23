"""
Additional coverage for TestGenerator utility helpers and fallbacks.
"""

# [20251214_TEST] Expand coverage for TestGenerator conversions and fallbacks.

import ast
from fractions import Fraction

from code_scalpel.generators.test_generator import (
    GeneratedTestSuite,
    TestCase,
    TestGenerator,
)


def test_to_pytest_true_and_false_assertions():
    case_true = TestCase(
        path_id=0,
        function_name="foo",
        inputs={},
        expected_behavior="returns True",
        path_conditions=[],
        description="branch returns true",
    )
    case_false = TestCase(
        path_id=1,
        function_name="foo",
        inputs={},
        expected_behavior="returns False",
        path_conditions=[],
        description="branch returns false",
    )

    true_code = case_true.to_pytest(0)
    false_code = case_false.to_pytest(1)

    assert "assert result is True" in true_code
    assert "assert result is False" in false_code


def test_extract_function_code_fallback_on_parse_error():
    suite = GeneratedTestSuite(
        function_name="broken",
        test_cases=[],
        source_code="def broken(:",  # invalid Python to trigger fallback
    )

    fallback = suite._extract_function_code()

    assert "# Function broken" in fallback


def test_detect_main_function_variants():
    generator = TestGenerator()

    # SyntaxError path returns default target
    assert generator._detect_main_function("def broken(:", language="python") == "target_function"

    # JavaScript arrow function detection
    js_code = "const calc = async () => 42;"
    assert generator._detect_main_function(js_code, language="javascript") == "calc"


def test_generate_satisfying_value_defaults():
    generator = TestGenerator()

    assert generator._generate_satisfying_value("y > 0", "x", True) == 1
    assert generator._generate_satisfying_value("y > 0", "x", False) == -1


def test_extract_test_cases_skips_infeasible_and_describes_conditions():
    generator = TestGenerator()

    code = """

def foo(x):
    if x > 0:
        return True
    else:
        return False
"""
    symbolic_result = {
        "paths": [
            {
                "path_id": 0,
                "conditions": ["x > 0", "y > 1", "z > 2"],
                "state": {"x": 1},
            },
            {"path_id": 1, "conditions": ["x <= 0"], "state": {"x": -1}},
            {
                "path_id": 2,
                "conditions": ["x > 10"],
                "state": {"x": 11},
                "status": "infeasible",
            },
        ]
    }

    cases = generator._extract_test_cases(symbolic_result, "foo", code, "python")

    assert len(cases) == 2
    assert "and 1 more conditions" in cases[0].description
    assert cases[1].expected_behavior == "returns False"


def test_extract_parameter_types_constant_annotation():
    generator = TestGenerator()
    typed_code = 'def typed(x: "role"):\n    return x\n'

    param_types = generator._extract_parameter_types(typed_code, "typed", "python")

    assert param_types == {"x": "role"}


def test_to_python_value_conversions_and_coercions():
    generator = TestGenerator()

    class LongMock:
        def __init__(self, value: int):
            self.value = value

        def as_long(self):
            return self.value

    class FractionMock:
        def __init__(self, frac):
            self.frac = frac

        def as_fraction(self):
            return self.frac

    class StringMock:
        def __init__(self, text: str):
            self.text = text

        def as_string(self):
            return self.text

    class BoolMock:
        def __init__(self, flag: bool):
            self.flag = flag

        def is_true(self):
            return self.flag

        def __bool__(self):
            return self.flag

    assert generator._to_python_value(LongMock(3), expected_type="float") == 3.0
    assert generator._to_python_value(FractionMock(Fraction(3, 2)), expected_type="int") == 1
    assert generator._to_python_value(StringMock("hello")) == "hello"
    assert generator._to_python_value(BoolMock(True)) is True
    assert generator._to_python_value(7, expected_type="str") == "7"
    assert generator._to_python_value(0, expected_type="bool") is False
    assert generator._to_python_value(2, expected_type="float") == 2.0
    assert generator._to_python_value("notint", expected_type="int") == 0
    assert generator._to_python_value("notfloat", expected_type="float") == 0.0


def test_analyze_return_paths_and_ast_value_helpers():
    generator = TestGenerator()

    assert generator._analyze_return_paths("function foo() {}", "foo", "javascript") == {}

    assert generator._ast_value_to_python(ast.Constant(value=5)) == 5
    assert generator._ast_value_to_python(ast.Name(id="True")) is True
    assert generator._ast_value_to_python(ast.Name(id="False")) is False


def test_condition_comparisons_and_negations():
    generator = TestGenerator()

    assert generator._is_negation_match("temp > 100", "temp <= 100")
    assert generator._is_equivalent_condition("x > 5", "x > 5")
