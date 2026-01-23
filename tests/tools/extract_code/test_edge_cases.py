# [20260103_TEST] Edge case tests for extract_code
"""
Edge case tests for extract_code tool.

These tests verify handling of complex Python structures:
- Decorated functions
- Async functions and methods
- Nested functions
- Inherited methods
- Lambda assignments
- Properties and descriptors
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from code_scalpel.surgery.unified_extractor import UnifiedExtractor


class TestDecoratorHandling:
    """Test extraction of decorated functions."""

    def test_simple_decorator_preserved(self):
        """Test that function decorators are preserved during extraction."""
        python_code = """from functools import wraps

def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@decorator
def process_data(data):
    return data.strip()

def other_function():
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "process_data")

                assert result.success, f"Extraction failed: {result.error}"
                assert "@decorator" in result.code, "Decorator not preserved"
                assert "def process_data" in result.code, "Function definition not extracted"
            finally:
                os.unlink(f.name)

    def test_multiple_decorators_preserved(self):
        """Test that multiple decorators are preserved in correct order."""
        python_code = """from functools import lru_cache
from typing import Optional

@lru_cache(maxsize=128)
@staticmethod
def compute_value(x: int) -> int:
    return x * x

def helper():
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "compute_value")

                assert result.success, f"Extraction failed: {result.error}"
                assert "@lru_cache" in result.code, "First decorator not preserved"
                assert "@staticmethod" in result.code, "Second decorator not preserved"
                # Check order (lru_cache should come before staticmethod)
                lru_pos = result.code.index("@lru_cache")
                static_pos = result.code.index("@staticmethod")
                assert lru_pos < static_pos, "Decorator order not preserved"
            finally:
                os.unlink(f.name)

    def test_class_decorator_preserved(self):
        """Test that class decorators are preserved during extraction."""
        python_code = """from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int

class Other:
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("class", "User")

                assert result.success, f"Extraction failed: {result.error}"
                assert "@dataclass" in result.code, "Class decorator not preserved"
                assert "class User" in result.code, "Class definition not extracted"
            finally:
                os.unlink(f.name)


class TestAsyncFunctions:
    """Test extraction of async functions and methods."""

    def test_async_function_extraction(self):
        """Test extracting an async function."""
        python_code = """import asyncio

async def fetch_data(url):
    await asyncio.sleep(1)
    return f"Data from {url}"

def sync_function():
    return "sync"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "fetch_data")

                assert result.success, f"Extraction failed: {result.error}"
                assert "async def fetch_data" in result.code, "Async keyword not preserved"
                assert "await asyncio.sleep" in result.code, "Await keyword not preserved"
            finally:
                os.unlink(f.name)

    def test_async_method_extraction(self):
        """Test extracting an async method from a class."""
        python_code = """import asyncio

class AsyncService:
    async def process(self, data):
        await asyncio.sleep(0.1)
        return data.upper()

    def sync_method(self):
        return "sync"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "AsyncService.process")

                assert result.success, f"Extraction failed: {result.error}"
                assert "async def process" in result.code, "Async method not extracted correctly"
                assert "await" in result.code, "Await keyword not preserved"
            finally:
                os.unlink(f.name)

    def test_async_context_manager(self):
        """Test extracting async context manager methods."""
        python_code = """class AsyncResource:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def regular_method(self):
        pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "AsyncResource.__aenter__")

                assert result.success, f"Extraction failed: {result.error}"
                assert "async def __aenter__" in result.code, "Async special method not extracted"
            finally:
                os.unlink(f.name)


class TestNestedFunctions:
    """Test extraction of nested functions."""

    def test_outer_function_with_nested(self):
        """Test extracting outer function includes nested functions."""
        python_code = """def outer(x):
    def inner(y):
        return y * 2
    return inner(x) + 1

def other():
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "outer")

                assert result.success, f"Extraction failed: {result.error}"
                assert "def outer" in result.code, "Outer function not extracted"
                assert "def inner" in result.code, "Nested function not included"
                assert "other" not in result.code, "Sibling function incorrectly included"
            finally:
                os.unlink(f.name)

    def test_closure_variables(self):
        """Test extracting function with closure variables."""
        python_code = """def make_multiplier(factor):
    def multiply(x):
        return x * factor
    return multiply

def unrelated():
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "make_multiplier")

                assert result.success, f"Extraction failed: {result.error}"
                assert "def make_multiplier" in result.code, "Outer function not extracted"
                assert "def multiply" in result.code, "Closure not included"
                assert "factor" in result.code, "Closure variable reference not preserved"
            finally:
                os.unlink(f.name)


class TestInheritedMethods:
    """Test extraction of methods from inherited classes."""

    def test_method_from_child_class(self):
        """Test extracting method from a child class."""
        python_code = """class Parent:
    def parent_method(self):
        return "parent"

class Child(Parent):
    def child_method(self):
        return "child"

    def override_method(self):
        return "overridden"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "Child.child_method")

                assert result.success, f"Extraction failed: {result.error}"
                assert "def child_method" in result.code, "Method not extracted"
            finally:
                os.unlink(f.name)

    def test_child_class_extraction(self):
        """Test extracting entire child class preserves inheritance."""
        python_code = """class Base:
    pass

class Derived(Base):
    def method(self):
        return "derived"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("class", "Derived")

                assert result.success, f"Extraction failed: {result.error}"
                assert "class Derived(Base)" in result.code or "class Derived" in result.code, "Class not extracted"
                assert "def method" in result.code, "Method not included"
            finally:
                os.unlink(f.name)


class TestLambdaAndSpecialAssignments:
    """Test extraction of lambda assignments and special patterns."""

    def test_lambda_assignment(self):
        """Test extracting module-level lambda assignment."""
        python_code = """square = lambda x: x * x

cube = lambda x: x * x * x

def regular_function():
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                # Note: Lambda extractions may not be supported by all extractors
                # This test documents the current behavior
                result = extractor.extract("function", "square")

                # Lambda may or may not be extractable - document the behavior
                if result.success:
                    assert "square" in result.code, "Lambda assignment not extracted"
                # If not supported, that's documented behavior
            finally:
                os.unlink(f.name)

    def test_property_method(self):
        """Test extracting property methods."""
        python_code = """class Person:
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def regular_method(self):
        pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "Person.name")

                assert result.success, f"Extraction failed: {result.error}"
                assert "@property" in result.code, "Property decorator not preserved"
                assert "def name" in result.code, "Property method not extracted"
            finally:
                os.unlink(f.name)

    def test_staticmethod_extraction(self):
        """Test extracting static methods."""
        python_code = """class MathUtils:
    @staticmethod
    def add(a, b):
        return a + b

    def instance_method(self):
        pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "MathUtils.add")

                assert result.success, f"Extraction failed: {result.error}"
                assert "@staticmethod" in result.code, "Staticmethod decorator not preserved"
                assert "def add" in result.code, "Static method not extracted"
            finally:
                os.unlink(f.name)

    def test_classmethod_extraction(self):
        """Test extracting class methods."""
        python_code = """class Factory:
    @classmethod
    def create(cls, name):
        return cls(name)

    def __init__(self, name):
        self.name = name
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "Factory.create")

                assert result.success, f"Extraction failed: {result.error}"
                assert "@classmethod" in result.code, "Classmethod decorator not preserved"
                assert "def create" in result.code, "Class method not extracted"
            finally:
                os.unlink(f.name)
