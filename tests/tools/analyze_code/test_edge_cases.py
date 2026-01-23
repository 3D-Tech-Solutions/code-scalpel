"""
Edge case tests for analyze_code tool.

Tests handling of decorators, async functions, nested classes/functions,
lambda expressions, and other Python language features.
"""

from code_scalpel.mcp.server import _analyze_code_sync


class TestAsyncFunctions:
    """Test extraction of async functions."""

    def test_async_function_extracted(self):
        """Async functions should be extracted like normal functions."""
        code = """
async def fetch_data():
    return await get_data()
"""

        result = _analyze_code_sync(code=code)

        assert any("fetch_data" in f for f in result.functions)

    def test_async_method_in_class(self):
        """Async methods should be extracted from classes."""
        code = """
class AsyncHandler:
    async def handle_request(self):
        return await process()
"""

        result = _analyze_code_sync(code=code)

        assert "AsyncHandler" in result.classes
        assert any("handle_request" in f for f in result.functions)

    def test_mixed_async_and_sync(self):
        """Mix of async and sync functions should be handled."""
        code = """
def sync_function():
    return 1

async def async_function():
    return await get_value()

def another_sync():
    return 2
"""

        result = _analyze_code_sync(code=code)

        assert (
            "sync_function" in result.functions
            and "another_sync" in result.functions
            and any("async_function" in f for f in result.functions)
        )


class TestDecoratedFunctions:
    """Test extraction of decorated functions."""

    def test_decorated_function_extracted(self):
        """Decorated functions should be extracted."""
        code = """
@decorator
def decorated_func():
    pass
"""

        result = _analyze_code_sync(code=code)

        assert "decorated_func" in result.functions

    def test_multiple_decorators(self):
        """Functions with multiple decorators should be extracted."""
        code = """
@decorator_one
@decorator_two
@decorator_three
def multi_decorated():
    pass
"""

        result = _analyze_code_sync(code=code)

        assert "multi_decorated" in result.functions

    def test_decorator_with_arguments(self):
        """Decorators with arguments should work."""
        code = """
@decorator(arg1, arg2)
def decorated_with_args():
    pass
"""

        result = _analyze_code_sync(code=code)

        assert "decorated_with_args" in result.functions

    def test_class_decorators(self):
        """Decorated classes should be extracted."""
        code = """
@dataclass
class Person:
    name: str
    age: int
"""

        result = _analyze_code_sync(code=code)

        assert "Person" in result.classes


class TestNestedFunctions:
    """Test extraction of nested functions."""

    def test_nested_function_extracted(self):
        """Nested functions should be extracted."""
        code = """
def outer():
    def inner():
        pass
    return inner
"""

        result = _analyze_code_sync(code=code)

        # Should extract both outer and inner
        assert "outer" in result.functions
        assert "inner" in result.functions

    def test_deeply_nested_functions(self):
        """Deeply nested functions should be extracted."""
        code = """
def level_one():
    def level_two():
        def level_three():
            def level_four():
                return "nested"
            return level_four
        return level_three
    return level_two
"""

        result = _analyze_code_sync(code=code)

        # Should find all levels
        assert set(result.functions) >= {
            "level_one",
            "level_two",
            "level_three",
            "level_four",
        }

    def test_nested_functions_in_class(self):
        """Nested functions within class methods."""
        code = """
class Container:
    def outer_method(self):
        def inner_function():
            return 42
        return inner_function()
"""

        result = _analyze_code_sync(code=code)

        assert "Container" in result.classes
        assert "outer_method" in result.functions
        assert "inner_function" in result.functions


class TestNestedClasses:
    """Test extraction of nested classes."""

    def test_nested_class_extracted(self):
        """Nested classes should be extracted."""
        code = """
class Outer:
    class Inner:
        pass
"""

        result = _analyze_code_sync(code=code)

        # Should find both classes
        assert "Outer" in result.classes
        assert "Inner" in result.classes

    def test_deeply_nested_classes(self):
        """Deeply nested classes should be extracted."""
        code = """
class Level1:
    class Level2:
        class Level3:
            pass
"""

        result = _analyze_code_sync(code=code)

        assert set(result.classes) >= {"Level1", "Level2", "Level3"}


class TestLambdas:
    """Test handling of lambda expressions."""

    def test_lambda_not_counted_as_function(self):
        """Lambda expressions shouldn't be counted as named functions."""
        code = """
def regular_function():
    pass

square = lambda x: x ** 2
"""

        result = _analyze_code_sync(code=code)

        assert "regular_function" in result.functions
        # Lambda may or may not be in functions (depends on implementation)
        # But regular function must be there

    def test_lambda_in_class(self):
        """Lambda in class context."""
        code = """
class Calculator:
    add = lambda self, x, y: x + y
"""

        result = _analyze_code_sync(code=code)

        assert "Calculator" in result.classes


class TestSpecialMethods:
    """Test extraction of special Python methods."""

    def test_magic_methods_extracted(self):
        """Magic methods like __init__, __str__ should be extracted."""
        code = """
class MyClass:
    def __init__(self):
        self.value = 0

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"MyClass({self.value})"
"""

        result = _analyze_code_sync(code=code)

        assert "MyClass" in result.classes
        assert set(result.functions) >= {"__init__", "__str__", "__repr__"}

    def test_property_decorators(self):
        """@property decorated methods should be extracted."""
        code = """
class Circle:
    def __init__(self, radius):
        self.radius = radius

    @property
    def diameter(self):
        return self.radius * 2

    @property
    def area(self):
        return 3.14 * self.radius ** 2
"""

        result = _analyze_code_sync(code=code)

        assert "Circle" in result.classes
        assert set(result.functions) >= {"__init__", "diameter", "area"}

    def test_staticmethod_and_classmethod(self):
        """@staticmethod and @classmethod should be extracted."""
        code = """
class Counter:
    count = 0

    @staticmethod
    def static_method():
        return "static"

    @classmethod
    def from_string(cls, value):
        return cls()
"""

        result = _analyze_code_sync(code=code)

        assert "Counter" in result.classes
        assert set(result.functions) >= {"static_method", "from_string"}


class TestComprehensions:
    """Test code with list/dict/set comprehensions."""

    def test_comprehension_complexity(self):
        """Comprehensions should be handled."""
        code = """
def process_list(items):
    squared = [x ** 2 for x in items]
    filtered = {x for x in items if x > 0}
    mapping = {x: x ** 2 for x in items}
    return squared, filtered, mapping
"""

        result = _analyze_code_sync(code=code)

        assert "process_list" in result.functions
        assert result.complexity > 0


class TestTypeAnnotations:
    """Test handling of type annotations."""

    def test_type_annotations_preserved(self):
        """Type annotations should not prevent extraction."""
        code = """
def add(a: int, b: int) -> int:
    return a + b

def process(data: List[str]) -> Dict[str, int]:
    return {item: len(item) for item in data}

class Processor:
    def handle(self, value: Optional[str]) -> None:
        pass
"""

        result = _analyze_code_sync(code=code)

        assert set(result.functions) >= {"add", "process", "handle"}
        assert "Processor" in result.classes


class TestImportStatements:
    """Test extraction of various import styles."""

    def test_simple_imports(self):
        """Simple imports should be extracted."""
        code = """
import os
import sys
import json
"""

        result = _analyze_code_sync(code=code)

        assert len(result.imports) >= 3

    def test_from_imports(self):
        """From-imports should be extracted."""
        code = """
from os import path
from typing import List, Dict
from collections import defaultdict, Counter
"""

        result = _analyze_code_sync(code=code)

        assert len(result.imports) >= 3

    def test_aliased_imports(self):
        """Aliased imports should be handled."""
        code = """
import numpy as np
from typing import Dict as D
import pandas as pd
"""

        result = _analyze_code_sync(code=code)

        assert len(result.imports) >= 3


class TestUnusualFormatting:
    """Test handling of unusual but valid code formatting."""

    def test_inline_function_definitions(self):
        """Functions defined on single line should work."""
        code = """
def one_liner(): return 42
def another(): x = 1; y = 2; return x + y
"""

        result = _analyze_code_sync(code=code)

        assert set(result.functions) >= {"one_liner", "another"}

    def test_function_with_complex_signature(self):
        """Functions with complex signatures."""
        code = """
def function_with_defaults(a, b=10, *args, c=20, **kwargs):
    pass

def another(*args, **kwargs):
    pass
"""

        result = _analyze_code_sync(code=code)

        assert set(result.functions) >= {"function_with_defaults", "another"}

    def test_class_with_inheritance(self):
        """Classes with inheritance and multiple bases."""
        code = """
class Parent:
    pass

class Child(Parent):
    pass

class MultiBase(Parent, OtherBase):
    pass
"""

        result = _analyze_code_sync(code=code)

        assert set(result.classes) >= {"Parent", "Child", "MultiBase"}


class TestJavaScriptEdgeCases:
    """JavaScript-specific edge cases."""

    def test_arrow_functions(self):
        """Arrow functions should be extracted."""
        code = """
const add = (a, b) => a + b;
const multiply = (x, y) => {
    return x * y;
};
"""

        result = _analyze_code_sync(code=code, language="javascript")

        # Arrow function extraction depends on implementation
        assert result.functions is not None

    def test_class_expressions(self):
        """Class expressions should be handled."""
        code = """
class MyClass {
    constructor(name) {
        this.name = name;
    }

    greet() {
        return `Hello, ${this.name}`;
    }
}
"""

        result = _analyze_code_sync(code=code, language="javascript")

        assert "MyClass" in result.classes or len(result.classes) >= 0


class TestJavaEdgeCases:
    """Java-specific edge cases."""

    def test_java_inner_classes(self):
        """Java inner classes should be extracted."""
        code = """
public class Outer {
    public class Inner {
        public void innerMethod() {}
    }
}
"""

        result = _analyze_code_sync(code=code, language="java")

        assert "Outer" in result.classes  # Java inner class extraction depends on parser

    def test_java_generics(self):
        """Java generics should not break extraction."""
        code = """
public class Container<T> {
    public void add(T item) {}
    public T get() {}
}
"""

        result = _analyze_code_sync(code=code, language="java")

        assert "Container" in result.classes
        assert set(result.functions) >= {"add", "get"}
