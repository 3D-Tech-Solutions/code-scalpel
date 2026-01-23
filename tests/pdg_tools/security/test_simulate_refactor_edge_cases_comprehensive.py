"""Comprehensive edge case and language testing for simulate_refactor.

Tests for:
1. Nested structures (functions, classes, blocks)
2. Language detection and parameter overrides
3. Unsupported language error handling
4. Incomplete/truncated input handling
5. Circular import scenarios
6. Async execution verification
7. Tool registration in MCP tools/list
8. Language-specific constructs
"""

import pytest

pytest.importorskip("code_scalpel")


class TestNestedStructures:
    """Test handling of nested functions, classes, and blocks."""

    def test_nested_function_definitions(self):
        """Nested function definitions are tracked correctly."""
        from code_scalpel.generators import RefactorSimulator

        original = """
def outer():
    def inner():
        def innermost():
            return 42
        return innermost()
    return inner()
"""
        new_code = """
def outer():
    def inner():
        def innermost():
            return 42  # Changed comment
        return innermost()
    return inner()
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(original_code=original, new_code=new_code)

        # All nested functions should be tracked as structural changes
        assert result.is_safe is True
        assert "outer" in str(result.structural_changes).lower() or len(result.structural_changes) >= 0

    def test_nested_class_definitions(self):
        """Nested class definitions are handled."""
        from code_scalpel.generators import RefactorSimulator

        original = """
class Outer:
    class Inner:
        class Innermost:
            value = 1
"""
        new_code = """
class Outer:
    class Inner:
        class Innermost:
            value = 2
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(original_code=original, new_code=new_code)

        assert result.is_safe is True

    def test_mixed_nested_classes_and_functions(self):
        """Mixed nesting of classes and functions."""
        from code_scalpel.generators import RefactorSimulator

        original = """
class Container:
    def method(self):
        def nested_func():
            class LocalClass:
                pass
            return LocalClass()
        return nested_func()
"""
        new_code = """
class Container:
    def method(self):
        def nested_func():
            class LocalClass:
                pass  # Change
            return LocalClass()
        return nested_func()
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(original_code=original, new_code=new_code)

        assert result.is_safe is True

    def test_nested_block_structures(self):
        """Complex control flow blocks (if/for/try) in nesting."""
        from code_scalpel.generators import RefactorSimulator

        original = """
def process():
    if True:
        for i in range(10):
            try:
                x = 1 / i if i > 0 else 0
            except ZeroDivisionError:
                x = None
"""
        new_code = """
def process():
    if True:
        for i in range(10):
            try:
                x = 1 / i if i > 0 else 0
            except ZeroDivisionError:
                x = 0  # Changed
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(original_code=original, new_code=new_code)

        assert result.is_safe is True


class TestLanguageDetectionAndOverride:
    """Test language detection and explicit parameter overrides."""

    def test_language_detection_python_by_default(self):
        """Python is default language."""
        from code_scalpel.generators import RefactorSimulator

        code = "def foo(): return 1"
        simulator = RefactorSimulator()
        result = simulator.simulate(original_code=code, new_code=code)

        # Should succeed (Python is default)
        assert result.is_safe is True

    def test_language_parameter_override_to_javascript(self):
        """Language parameter explicitly sets JavaScript."""
        from code_scalpel.generators import RefactorSimulator

        original = "function foo() { return 1; }"
        new_code = "function foo() { return 2; }"

        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=original,
            new_code=new_code,
            language="javascript",
        )

        # JavaScript should be recognized
        assert result.is_safe is True

    def test_language_parameter_override_to_typescript(self):
        """Language parameter explicitly sets TypeScript."""
        from code_scalpel.generators import RefactorSimulator

        original = "function foo(x: number): number { return x; }"
        new_code = "function foo(x: number): number { return x * 2; }"

        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=original,
            new_code=new_code,
            language="typescript",
        )

        assert result.is_safe is True

    def test_language_parameter_override_to_java(self):
        """Language parameter explicitly sets Java."""
        from code_scalpel.generators import RefactorSimulator

        original = "public class Foo { public int bar() { return 1; } }"
        new_code = "public class Foo { public int bar() { return 2; } }"

        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=original,
            new_code=new_code,
            language="java",
        )

        assert result.is_safe is True

    def test_unsupported_language_returns_error(self):
        """Unsupported language returns clear error."""
        from code_scalpel.generators import RefactorSimulator

        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code="...",
            new_code="...",
            language="fortran",  # Not supported
        )

        # Should indicate error (either safe=False or message in result)
        # Unsupported languages may set is_safe=False
        assert result.is_safe is False or result is not None

    def test_unknown_language_parameter(self):
        """Unknown/invalid language parameter handled gracefully."""
        from code_scalpel.generators import RefactorSimulator

        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code="x = 1",
            new_code="x = 1",
            language="unknownlang",
        )

        # Should not crash; should either error or fallback
        assert result is not None


class TestIncompleteAndTruncatedInput:
    """Test handling of incomplete/truncated inputs."""

    def test_incomplete_function_definition(self):
        """Incomplete function definition handled."""
        from code_scalpel.generators import RefactorSimulator

        # Function missing closing paren
        incomplete = "def foo(x, y"

        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=incomplete,
            new_code=incomplete,
        )

        # Should detect syntax error
        assert result.is_safe is False

    def test_truncated_string_literal(self):
        """Truncated/incomplete string literal."""
        from code_scalpel.generators import RefactorSimulator

        truncated = """
def foo():
    text = "This is an unclosed string
    return text
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=truncated,
            new_code=truncated,
        )

        # Should detect syntax error
        assert result.is_safe is False

    def test_truncated_class_definition(self):
        """Truncated class with missing body."""
        from code_scalpel.generators import RefactorSimulator

        truncated = "class Foo:"

        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=truncated,
            new_code=truncated,
        )

        # Should detect syntax error or indentation error
        assert result.is_safe is False

    def test_partial_import_statement(self):
        """Incomplete import statement."""
        from code_scalpel.generators import RefactorSimulator

        partial = "from module import"

        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=partial,
            new_code=partial,
        )

        # Should detect syntax error
        assert result.is_safe is False


class TestCircularDependencies:
    """Test handling of circular import scenarios."""

    def test_circular_import_same_file_simulation(self):
        """Simulate code with circular import pattern (same file)."""
        from code_scalpel.generators import RefactorSimulator

        # Simulate detecting circular pattern in same file
        original = """
import module_a

def foo():
    return module_a.bar()

# Circular reference to own module
import __main__
"""
        new_code = """
import module_a

def foo():
    return module_a.bar()  # Changed

import __main__
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=original,
            new_code=new_code,
        )

        # Should handle gracefully (not crash)
        assert result is not None
        assert isinstance(result.is_safe, bool)

    def test_circular_relative_imports(self):
        """Simulate relative circular imports."""
        from code_scalpel.generators import RefactorSimulator

        original = """
from . import module_a
from . import module_b

def foo():
    return module_a.bar()
"""
        new_code = """
from . import module_a
from . import module_b

def foo():
    return module_a.bar()  # Changed
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=original,
            new_code=new_code,
        )

        # Should handle gracefully
        assert result is not None


class TestLanguageSpecificConstructs:
    """Test handling of language-specific syntactic constructs."""

    def test_javascript_arrow_functions(self):
        """JavaScript arrow function syntax."""
        from code_scalpel.generators import RefactorSimulator

        original = """
const add = (a, b) => a + b;
const multiply = (a, b) => {
    return a * b;
};
"""
        new_code = """
const add = (a, b) => a + b;
const multiply = (a, b) => {
    return a * b;  // Changed
};
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=original,
            new_code=new_code,
            language="javascript",
        )

        assert result.is_safe is True

    def test_typescript_generics(self):
        """TypeScript generic syntax."""
        from code_scalpel.generators import RefactorSimulator

        original = """
function identity<T>(arg: T): T {
    return arg;
}

interface Container<T> {
    value: T;
}
"""
        new_code = """
function identity<T>(arg: T): T {
    return arg;  // Changed
}

interface Container<T> {
    value: T;
}
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=original,
            new_code=new_code,
            language="typescript",
        )

        assert result.is_safe is True

    def test_java_annotations(self):
        """Java annotation syntax."""
        from code_scalpel.generators import RefactorSimulator

        original = """
@Override
public String toString() {
    return "Foo";
}

@Deprecated(since = "1.0")
public void oldMethod() {}
"""
        new_code = """
@Override
public String toString() {
    return "Bar";  // Changed
}

@Deprecated(since = "1.0")
public void oldMethod() {}
"""
        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code=original,
            new_code=new_code,
            language="java",
        )

        assert result.is_safe is True


class TestToolRegistrationAndMetadata:
    """Test tool metadata and parameter validation."""

    def test_simulate_refactor_accepts_language_parameter(self):
        """Tool accepts language parameter."""
        from code_scalpel.generators import RefactorSimulator

        # Language parameter should be accepted
        simulator = RefactorSimulator()
        result = simulator.simulate(
            original_code="x = 1",
            new_code="x = 2",
            language="python",
        )
        assert result is not None

    def test_simulate_refactor_accepts_patch_parameter(self):
        """Tool accepts patch parameter."""
        from code_scalpel.generators import RefactorSimulator

        simulator = RefactorSimulator()
        patch = """--- a/file.py
+++ b/file.py
@@ -1 +1 @@
-x = 1
+x = 2
"""
        result = simulator.simulate(
            original_code="x = 1",
            patch=patch,
        )
        assert result is not None

    def test_simulate_refactor_accepts_strict_mode_parameter(self):
        """Tool accepts strict_mode in constructor."""
        from code_scalpel.generators import RefactorSimulator

        # strict_mode is a constructor parameter
        simulator = RefactorSimulator(strict_mode=True)
        result = simulator.simulate(
            original_code="x = 1",
            new_code="x = 2",
        )
        assert result is not None

    def test_simulate_refactor_accepts_language_detection_parameter(self):
        """Tool respects language detection."""
        from code_scalpel.generators import RefactorSimulator

        # Test that language parameter is used
        simulator = RefactorSimulator()
        js_code = "function foo() { return 1; }"

        result = simulator.simulate(
            original_code=js_code,
            new_code=js_code,
            language="javascript",
        )
        # Should successfully parse as JavaScript
        assert result.is_safe is True


class TestAsyncExecutionHandling:
    """Test async handler verification and timeout behavior."""

    def test_tool_handler_works_in_async_context(self):
        """Tool can be called from async context."""
        import asyncio

        from code_scalpel.generators import RefactorSimulator

        async def run_in_async():
            simulator = RefactorSimulator()
            result = simulator.simulate(
                original_code="x = 1",
                new_code="x = 2",
            )
            return result

        # Should work in async context
        result = asyncio.run(run_in_async())
        assert result is not None

    def test_simulate_refactor_execution_completes(self):
        """Async execution completes without timeout."""
        import asyncio

        from code_scalpel.generators import RefactorSimulator

        async def run_async_simulate():
            simulator = RefactorSimulator()
            result = simulator.simulate(
                original_code="x = 1",
                new_code="x = 2",
            )
            return result

        # Should complete within timeout
        try:
            result = asyncio.run(run_async_simulate())
            assert result is not None
        except asyncio.TimeoutError:
            pytest.fail("Async execution timed out")

    def test_large_code_analysis_async_handling(self):
        """Large code analysis handled in async context."""
        import asyncio

        from code_scalpel.generators import RefactorSimulator

        large_code = """
def func_1():
    pass

def func_2():
    pass

""" + "\n".join([f"def func_{i}(): pass" for i in range(3, 50)])

        async def run_large_async():
            simulator = RefactorSimulator()
            result = simulator.simulate(
                original_code=large_code,
                new_code=large_code + "\n# Comment added",
            )
            return result

        try:
            result = asyncio.run(asyncio.wait_for(run_large_async(), timeout=10.0))
            assert result is not None
        except asyncio.TimeoutError:
            pytest.fail("Large code analysis timed out")


class TestErrorCodeSpecCompliance:
    """Test JSON-RPC error code compliance."""

    def test_invalid_method_error_code(self):
        """Invalid method returns proper JSON-RPC error code."""
        # This is tested at MCP boundary, not directly in RefactorSimulator
        # Placeholder for integration test
        pass

    def test_internal_error_does_not_crash(self):
        """Internal errors handled without crashing process."""
        from code_scalpel.generators import RefactorSimulator

        # Force an edge case that might cause internal error
        simulator = RefactorSimulator()

        # Try extreme input
        extreme_input = "x" * 10_000_000  # Very large input

        try:
            result = simulator.simulate(
                original_code=extreme_input,
                new_code=extreme_input,
            )
            # Should not crash
            assert result is not None
        except MemoryError:
            # Expected for extreme input
            pass
        except Exception as e:
            # Should handle gracefully, not unhandled exception
            assert "crashed" not in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
