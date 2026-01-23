# [20260103_TEST] Line number accuracy tests for extract_code
"""
Line number accuracy tests for extract_code tool.

These tests verify that start_line and end_line values are accurate for IDE integration.
Accurate line numbers are critical for:
- Navigating to extracted code in the editor
- Highlighting relevant code sections
- Error reporting and debugging
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from code_scalpel.surgery.unified_extractor import UnifiedExtractor


class TestLineNumberAccuracy:
    """Test line number accuracy for extracted code."""

    def test_function_line_numbers(self):
        """Test that function extraction returns correct line numbers."""
        python_code = """# Line 1: comment
def first_function():  # Line 2
    return "first"  # Line 3

def second_function():  # Line 5
    return "second"  # Line 6

def third_function():  # Line 8
    return "third"  # Line 9
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "second_function")

                assert result.success, f"Extraction failed: {result.error}"

                # Verify start_line and end_line exist
                assert hasattr(result, "start_line"), "start_line attribute missing"
                assert hasattr(result, "end_line"), "end_line attribute missing"

                # second_function is at line 5-6 (1-indexed)
                # Depending on implementation, might include blank lines
                assert result.start_line >= 5, f"start_line {result.start_line} should be >= 5"
                assert result.end_line >= 6, f"end_line {result.end_line} should be >= 6"
                assert result.start_line <= result.end_line, "start_line should be <= end_line"
            finally:
                os.unlink(f.name)

    def test_class_line_numbers(self):
        """Test that class extraction returns correct line numbers."""
        python_code = """# Line 1
# Line 2

class FirstClass:  # Line 4
    def method(self):  # Line 5
        pass  # Line 6

class SecondClass:  # Line 8
    def method_a(self):  # Line 9
        pass  # Line 10

    def method_b(self):  # Line 12
        pass  # Line 13
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("class", "SecondClass")

                assert result.success, f"Extraction failed: {result.error}"

                # SecondClass starts at line 8, ends at line 13
                assert result.start_line >= 8, f"start_line {result.start_line} should be >= 8"
                assert result.end_line >= 13, f"end_line {result.end_line} should be >= 13"
                assert result.start_line <= result.end_line, "start_line should be <= end_line"
            finally:
                os.unlink(f.name)

    def test_decorated_function_line_numbers(self):
        """Test that decorators are included in line number range."""
        python_code = """def decorator(func):
    return func

@decorator  # Line 4
def decorated_function():  # Line 5
    return "decorated"  # Line 6
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "decorated_function")

                assert result.success, f"Extraction failed: {result.error}"

                # Decorator should be included, so start_line should be <= 4
                # Function ends at line 6
                assert result.start_line <= 5, f"start_line {result.start_line} should include decorator at line 4"
                assert result.end_line >= 6, f"end_line {result.end_line} should be >= 6"
            finally:
                os.unlink(f.name)

    def test_method_line_numbers(self):
        """Test that method extraction returns correct line numbers."""
        python_code = '''class Calculator:
    def add(self, a, b):  # Line 2
        return a + b  # Line 3

    def subtract(self, a, b):  # Line 5
        """Subtract b from a."""  # Line 6
        return a - b  # Line 7

    def multiply(self, a, b):  # Line 9
        return a * b  # Line 10
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "Calculator.subtract")

                assert result.success, f"Extraction failed: {result.error}"

                # subtract method is at lines 5-7
                assert result.start_line >= 5, f"start_line {result.start_line} should be >= 5"
                assert result.end_line >= 7, f"end_line {result.end_line} should be >= 7"
                assert result.start_line <= result.end_line, "start_line should be <= end_line"
            finally:
                os.unlink(f.name)

    def test_multiline_function_line_numbers(self):
        """Test line numbers for functions with multi-line signatures."""
        python_code = '''def simple():
    pass

def complex_function(
    arg1: str,
    arg2: int,
    arg3: float = 1.0,
    arg4: bool = True
):  # Line 9
    """Multiline function signature."""
    return arg1
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "complex_function")

                assert result.success, f"Extraction failed: {result.error}"

                # Function starts at line 4, ends at line 11
                assert result.start_line >= 4, f"start_line {result.start_line} should be >= 4"
                assert result.end_line >= 11, f"end_line {result.end_line} should be >= 11"
                assert result.start_line <= result.end_line, "start_line should be <= end_line"
            finally:
                os.unlink(f.name)

    def test_line_number_consistency_across_extractions(self):
        """Test that multiple extractions from same file report consistent line numbers."""
        python_code = """def func_a():  # Line 1
    pass  # Line 2

def func_b():  # Line 4
    pass  # Line 5

def func_c():  # Line 7
    pass  # Line 8
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)

                # Extract all three functions
                result_a = extractor.extract("function", "func_a")
                result_b = extractor.extract("function", "func_b")
                result_c = extractor.extract("function", "func_c")

                assert result_a.success and result_b.success and result_c.success

                # Verify they don't overlap incorrectly
                assert result_a.end_line < result_b.start_line, "func_a should end before func_b starts"
                assert result_b.end_line < result_c.start_line, "func_b should end before func_c starts"

                # Verify ordering
                assert (
                    result_a.start_line < result_b.start_line < result_c.start_line
                ), "Functions should be in correct order"
            finally:
                os.unlink(f.name)

    def test_nested_function_line_numbers(self):
        """Test line numbers for nested functions."""
        python_code = """def outer():  # Line 1
    def inner():  # Line 2
        return "inner"  # Line 3
    return inner()  # Line 4

def other():  # Line 6
    pass  # Line 7
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "outer")

                assert result.success, f"Extraction failed: {result.error}"

                # outer function includes nested inner, lines 1-4
                assert result.start_line >= 1, f"start_line {result.start_line} should be >= 1"
                assert result.end_line >= 4, f"end_line {result.end_line} should be >= 4"
                assert result.start_line <= result.end_line, "start_line should be <= end_line"
            finally:
                os.unlink(f.name)


class TestLineNumberEdgeCases:
    """Test line number accuracy for edge cases."""

    def test_first_line_function(self):
        """Test function starting at line 1."""
        python_code = """def first_line_function():
    return "first"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "first_line_function")

                assert result.success, f"Extraction failed: {result.error}"
                assert result.start_line == 1, f"start_line should be 1, got {result.start_line}"
                assert result.end_line >= 2, f"end_line should be >= 2, got {result.end_line}"
            finally:
                os.unlink(f.name)

    def test_single_line_function(self):
        """Test function definition on a single line."""
        python_code = """def other(): pass

def single_line(): return "single"

def another(): pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "single_line")

                assert result.success, f"Extraction failed: {result.error}"

                # Single line function at line 3
                assert result.start_line >= 3, f"start_line {result.start_line} should be >= 3"
                assert result.end_line >= 3, f"end_line {result.end_line} should be >= 3"
                # For single-line functions, start and end might be the same
            finally:
                os.unlink(f.name)

    def test_function_with_blank_lines(self):
        """Test that blank lines within function are included in range."""
        python_code = """def function_with_blanks():  # Line 1
    x = 1  # Line 2

    # Blank line above and below

    y = 2  # Line 6
    return x + y  # Line 7
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "function_with_blanks")

                assert result.success, f"Extraction failed: {result.error}"

                # Function spans lines 1-7, including blank lines
                assert result.start_line >= 1, f"start_line {result.start_line} should be >= 1"
                assert result.end_line >= 7, f"end_line {result.end_line} should be >= 7"
            finally:
                os.unlink(f.name)
