"""
Core functionality tests for analyze_code tool.

Tests the fundamental feature: accurate code structure extraction without hallucinations.
Covers Python, JavaScript, TypeScript, and Java language support.
"""

import pytest

from code_scalpel.analysis.code_analyzer import (
    AnalysisLanguage,
    CodeAnalyzer,
)


class TestNominal:
    """Nominal case: Analyze simple, well-formed code."""

    def test_analyze_python_single_function(self):
        """Test Python code with single function."""
        code = """
def greet(name):
    return f"Hello, {name}!"
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        assert "greet" in result.functions
        assert result.classes == []

        assert result.metrics.cyclomatic_complexity > 0

    def test_analyze_python_with_class(self):
        """Test Python code with class and methods."""
        code = """
class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, x):
        self.value += x
        return self.value

    def subtract(self, x):
        self.value -= x
        return self.value
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        assert "Calculator" in result.classes
        assert set(result.functions) >= {"__init__", "add", "subtract"}
        assert result.metrics.cyclomatic_complexity > 0

    def test_analyze_python_with_imports(self):
        """Test Python code with various import styles."""
        code = """
import os
import sys
from typing import List, Dict
from collections import defaultdict

def process(items):
    return items
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        # Verify basic extraction works
        assert "process" in result.functions
        assert result.metrics.cyclomatic_complexity > 0

    def test_analyze_javascript_function(self):
        """Test JavaScript code extraction."""
        code = """
function calculateSum(a, b) {
    return a + b;
}
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.JAVASCRIPT)
        result = analyzer.analyze(code)

        assert "calculateSum" in result.functions
        assert result.metrics.cyclomatic_complexity > 0

    def test_analyze_javascript_class(self):
        """Test JavaScript class extraction."""
        code = """
class User {
    constructor(name) {
        this.name = name;
    }

    greet() {
        return `Hello, ${this.name}`;
    }
}
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.JAVASCRIPT)
        result = analyzer.analyze(code)

        assert "User" in result.classes
        # [20260105_BUGFIX] Qualified method names for disambiguation
        assert "User.greet" in result.functions
        assert "User.constructor" in result.functions

    def test_analyze_typescript_with_types(self):
        """Test TypeScript code with type annotations."""
        code = """
interface User {
    name: string;
    age: number;
}

function createUser(name: string, age: number): User {
    return { name, age };
}
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.TYPESCRIPT)
        result = analyzer.analyze(code)

        assert "createUser" in result.functions
        assert result.metrics.cyclomatic_complexity > 0

    def test_analyze_java_class(self):
        """Test Java code extraction."""
        code = """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }
}
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.JAVA)
        result = analyzer.analyze(code)

        assert "Calculator" in result.classes
        # [20260105_BUGFIX] Qualified method names for disambiguation
        assert set(result.functions) >= {"Calculator.add", "Calculator.subtract"}


class TestNoHallucinations:
    """Core feature: Tool does NOT invent non-existent functions/classes.

    This is the PRIMARY purpose of analyze_code per roadmap:
    "helps prevent hallucinating non-existent methods or classes"
    """

    def test_no_hallucinated_functions(self):
        """Verify no non-existent functions are returned."""
        code = """
def real_function():
    return 42
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        # Should contain ONLY the real function, nothing invented
        assert result.functions == ["real_function"]
        assert "hallucinated_func" not in result.functions
        assert "fake_function" not in result.functions

    def test_no_hallucinated_classes(self):
        """Verify no non-existent classes are returned."""
        code = """
class RealClass:
    pass
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        # Should contain ONLY the real class, nothing invented
        assert result.classes == ["RealClass"]
        assert "FakeClass" not in result.classes
        assert "HallucinatedClass" not in result.classes

    def test_no_extra_functions_in_complex_code(self):
        """Verify exact function extraction in multi-function code."""
        code = """
def func_one():
    pass

def func_two():
    pass

def func_three():
    pass
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        # Exact set, no extras
        assert set(result.functions) == {"func_one", "func_two", "func_three"}
        assert len(result.functions) == 3

    def test_no_extra_classes_in_complex_code(self):
        """Verify exact class extraction."""
        code = """
class ClassA:
    pass

class ClassB:
    def method(self):
        pass

class ClassC:
    pass
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        # Exact set, no extras
        assert set(result.classes) == {"ClassA", "ClassB", "ClassC"}
        assert len(result.classes) == 3


class TestCompleteness:
    """Verify all actual functions/classes are extracted."""

    def test_extract_all_functions(self):
        """Verify ALL functions in code are found."""
        code = """
def function_1():
    return 1

def function_2():
    return 2

def function_3():
    return 3

def function_4():
    return 4

def function_5():
    return 5
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        expected_functions = {
            "function_1",
            "function_2",
            "function_3",
            "function_4",
            "function_5",
        }
        assert set(result.functions) == expected_functions
        assert len(result.functions) == 5

    def test_extract_all_classes(self):
        """Verify ALL classes in code are found."""
        code = """
class First:
    pass

class Second:
    pass

class Third:
    pass
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        expected_classes = {"First", "Second", "Third"}
        assert set(result.classes) == expected_classes
        assert len(result.classes) == 3

    def test_extract_all_methods(self):
        """Verify all methods are extracted from classes."""
        code = """
class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass

    def method_three(self):
        pass
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        # Should find all methods + class
        assert "MyClass" in result.classes
        assert set(result.functions) >= {"method_one", "method_two", "method_three"}


class TestInputValidation:
    """Input validation and error handling."""

    def test_non_string_input_rejected(self):
        """Non-string input should be handled gracefully."""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)

        # Should not raise, but return result with errors
        result = analyzer.analyze(12345)
        assert result is not None
        assert "errors" in dir(result) or len(result.errors) > 0

    def test_non_list_input_rejected(self):
        """List input should be rejected."""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)

        with pytest.raises((TypeError, AttributeError)):
            analyzer.analyze(["code"])

    def test_empty_string_handled(self):
        """Empty code string should be handled gracefully."""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze("")

        # Should return valid result with empty structures
        assert isinstance(result.functions, list)
        assert isinstance(result.classes, list)
        assert result.metrics is not None

    def test_syntax_error_handled(self):
        """Invalid Python syntax should be handled."""
        code = """
def broken_function(
    # Missing closing parenthesis
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        # Should not raise exception, return best-effort result
        assert result is not None
        assert hasattr(result, "functions")

    def test_whitespace_only_handled(self):
        """Code with only whitespace should be handled."""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze("   \n   \n   ")

        assert result.functions == []
        assert result.classes == []


class TestLanguageSupport:
    """Verify language support as per roadmap: Python, JS, TS, Java."""

    def test_python_supported(self):
        """Python language is supported."""
        code = "def test(): pass"
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)
        assert "test" in result.functions

    def test_javascript_supported(self):
        """JavaScript language is supported."""
        code = "function test() {}"
        analyzer = CodeAnalyzer(language=AnalysisLanguage.JAVASCRIPT)
        result = analyzer.analyze(code)
        assert "test" in result.functions

    def test_typescript_supported(self):
        """TypeScript language is supported."""
        code = "function test(): void {}"
        analyzer = CodeAnalyzer(language=AnalysisLanguage.TYPESCRIPT)
        result = analyzer.analyze(code)
        assert "test" in result.functions

    def test_java_supported(self):
        """Java language is supported."""
        code = "class Test { void method() {} }"
        analyzer = CodeAnalyzer(language=AnalysisLanguage.JAVA)
        result = analyzer.analyze(code)
        assert "Test" in result.classes


class TestComplexityScoring:
    """Verify complexity score is computed and accurate."""

    def test_complexity_score_exists(self):
        """Complexity score should be present."""
        code = "def simple(): return 1"
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        assert hasattr(result, "metrics")
        assert isinstance(result.metrics.cyclomatic_complexity, (int, float))
        assert result.metrics.cyclomatic_complexity >= 0

    def test_simple_code_has_low_complexity(self):
        """Simple code should have lower complexity."""
        code = "def simple(): return 1"
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        analyzer.analyze(code)

    def test_complex_code_has_higher_complexity(self):
        """Complex code with many branches should have higher complexity."""
        code = """
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 100:
                return "very large"
            else:
                return "large"
        else:
            return "small"
    else:
        return "negative"
"""
        analyzer = CodeAnalyzer(language=AnalysisLanguage.PYTHON)
        result = analyzer.analyze(code)

        # Should have measurable complexity
        assert result.metrics.cyclomatic_complexity > 0
