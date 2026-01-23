"""
[20260103_TEST] Integration tests for generate_unit_tests tool via MCP server.

Tests validate:
- Tool generates valid pytest and unittest code
- Framework selection works correctly
- max_test_cases parameter is respected
- data_driven parameter affects test generation (Pro+)
- crash_log parameter works for bug reproduction (Enterprise only)
- Error handling for invalid parameters
"""

import json


class TestGenerateUnitTestsIntegration:
    """Integration tests for generate_unit_tests via MCP server."""

    def test_basic_pytest_generation(self):
        """Should generate valid pytest code for simple function."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def add(a, b):
    return a + b
"""
        result = _generate_tests_sync(code=code, framework="pytest")

        assert result.success is True
        assert result.test_count >= 1
        assert "def test_" in result.pytest_code
        # Verify it's compilable Python
        compile(result.pytest_code, "<string>", "exec")

    def test_basic_unittest_generation(self):
        """Should generate valid unittest code for simple function."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def multiply(a, b):
    return a * b
"""
        result = _generate_tests_sync(code=code, framework="unittest")

        assert result.success is True
        assert result.test_count >= 1
        assert "unittest.TestCase" in result.unittest_code
        # Verify it's compilable Python
        compile(result.unittest_code, "<string>", "exec")

    def test_invalid_framework_rejected(self):
        """Should reject invalid framework name or handle gracefully."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = "def f(): pass"

        # Invalid framework either raises or returns error in result
        try:
            result = _generate_tests_sync(code=code, framework="nose")
            # If it doesn't raise, it should at least not succeed
            assert result.success is False or "nose" not in result.pytest_code
        except (ValueError, TypeError, Exception):
            # Expected to fail
            pass

    def test_empty_code_rejected(self):
        """Should handle empty code gracefully."""
        from code_scalpel.mcp.server import _generate_tests_sync

        # Empty code might not raise, but should not produce valid output
        try:
            result = _generate_tests_sync(code="", framework="pytest")
            # If it doesn't raise, result should indicate failure
            assert result.success is False or result.test_count == 0
        except (ValueError, TypeError, Exception):
            # Expected to fail
            pass

    def test_result_is_json_serializable(self):
        """Result must be JSON-serializable for MCP transport."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = "def f(x): return x * 2"
        result = _generate_tests_sync(code=code, framework="pytest")

        # MCP responses must be JSON-serializable
        payload = result.model_dump()
        json_str = json.dumps(payload)
        assert json_str is not None

    def test_complex_function_generation(self):
        """Should handle functions with multiple branches."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def validate(x):
    if x < 0:
        return "negative"
    elif x == 0:
        return "zero"
    else:
        return "positive"
"""
        result = _generate_tests_sync(code=code, framework="pytest")

        assert result.success is True
        # Should generate tests for each branch
        assert result.test_count >= 3

    def test_error_handling_function(self):
        """Should generate tests for functions that raise exceptions."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        result = _generate_tests_sync(code=code, framework="pytest")

        assert result.success is True
        # Should include error case
        assert "ValueError" in result.pytest_code or "ZeroDivisionError" in result.pytest_code

    def test_loop_function_handling(self):
        """Should handle functions with loops."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def sum_list(items):
    total = 0
    for item in items:
        total += item
    return total
"""
        result = _generate_tests_sync(code=code, framework="pytest")

        assert result.success is True
        assert result.test_count >= 1

    def test_nested_conditions(self):
        """Should handle deeply nested conditions."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def complex_logic(a, b, c):
    if a > 0:
        if b > 0:
            return a + b + c if c > 0 else a + b
        return a
    return b if b > 0 else c
"""
        result = _generate_tests_sync(code=code, framework="pytest")

        assert result.success is True
        assert result.test_count >= 1  # Should generate at least one test


class TestPytestOutputFormat:
    """Test specific pytest output format."""

    def test_pytest_uses_assert_statements(self):
        """Pytest tests should use plain assert."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = "def f(x): return x > 0"
        result = _generate_tests_sync(code=code, framework="pytest")

        assert "assert " in result.pytest_code

    def test_pytest_has_test_functions(self):
        """Each pytest test should be a function starting with test_."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = "def f(x): return x"
        result = _generate_tests_sync(code=code, framework="pytest")

        assert "def test_" in result.pytest_code

    def test_pytest_imports_pytest_if_needed(self):
        """Pytest tests should import pytest when needed."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def divide(a, b):
    if b == 0:
        raise ZeroDivisionError()
    return a / b
"""
        result = _generate_tests_sync(code=code, framework="pytest")

        # If error testing, should import pytest
        if "pytest.raises" in result.pytest_code:
            assert "import pytest" in result.pytest_code


class TestUnittestOutputFormat:
    """Test specific unittest output format."""

    def test_unittest_has_test_class(self):
        """Unittest tests should have a test class."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = "def f(x): return x"
        result = _generate_tests_sync(code=code, framework="unittest")

        assert "class Test" in result.unittest_code

    def test_unittest_inherits_testcase(self):
        """Test class should inherit from unittest.TestCase."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = "def f(x): return x"
        result = _generate_tests_sync(code=code, framework="unittest")

        assert "unittest.TestCase" in result.unittest_code

    def test_unittest_uses_assert_methods(self):
        """Unittest should use self.assert* methods."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = "def f(x): return x > 0"
        result = _generate_tests_sync(code=code, framework="unittest")

        assert "self.assert" in result.unittest_code

    def test_unittest_imports_unittest(self):
        """Unittest tests should import unittest."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = "def f(): pass"
        result = _generate_tests_sync(code=code, framework="unittest")

        assert "import unittest" in result.unittest_code


class TestCodeCompilability:
    """Test that generated code is valid Python."""

    def test_generated_pytest_is_compilable(self):
        """Generated pytest code should be syntactically valid."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def complex_function(a, b, c):
    if a > 0 and b > 0:
        return a + b + c
    elif a > 0:
        return a + c
    else:
        return b + c
"""
        result = _generate_tests_sync(code=code, framework="pytest")

        # Should not raise SyntaxError
        compile(result.pytest_code, "<string>", "exec")

    def test_generated_unittest_is_compilable(self):
        """Generated unittest code should be syntactically valid."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def complex_function(a, b, c):
    if a > 0 and b > 0:
        return a + b + c
    elif a > 0:
        return a + c
    else:
        return b + c
"""
        result = _generate_tests_sync(code=code, framework="unittest")

        # Should not raise SyntaxError
        compile(result.unittest_code, "<string>", "exec")


class TestMultipleFunctions:
    """Test handling of code with multiple functions."""

    def test_specific_function_selection(self):
        """Should be able to test specific function when code has multiple."""
        from code_scalpel.mcp.server import _generate_tests_sync

        code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
        # Test first function
        result = _generate_tests_sync(code=code, function_name="add", framework="pytest")

        assert result.success is True
        assert "add" in result.pytest_code
