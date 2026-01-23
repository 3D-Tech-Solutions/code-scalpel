# [20260103_TEST] Language support tests for extract_code
"""
Language support tests for extract_code tool.

These tests verify that the tool correctly handles all declared supported languages:
- Python
- JavaScript
- TypeScript
- Java

Tests verify extraction of functions, classes, and methods across all languages.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from code_scalpel.surgery.unified_extractor import UnifiedExtractor


class TestPythonLanguageSupport:
    """Python language extraction tests."""

    def test_python_function_extraction(self):
        """Test extracting a Python function."""
        python_code = '''def greet(name):
    """Return a greeting."""
    return f"Hello, {name}!"

def farewell(name):
    return f"Goodbye, {name}!"
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "greet")

                assert result.success, f"Extraction failed: {result.error}"
                assert "def greet" in result.code, "Function definition not extracted"
                assert "Hello" in result.code, "Function body not extracted"
                assert "farewell" not in result.code, "Other function incorrectly included"
            finally:
                os.unlink(f.name)

    def test_python_class_extraction(self):
        """Test extracting a Python class."""
        python_code = """class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

class StringUtils:
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("class", "Calculator")

                assert result.success, f"Extraction failed: {result.error}"
                assert "class Calculator" in result.code, "Class definition not extracted"
                assert "def add" in result.code, "Methods not extracted"
                assert "StringUtils" not in result.code, "Other class incorrectly included"
            finally:
                os.unlink(f.name)

    def test_python_method_extraction(self):
        """Test extracting a method from a Python class."""
        python_code = """class DataProcessor:
    def process(self, data):
        return data.strip()

    def validate(self, data):
        return len(data) > 0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "DataProcessor.process")

                assert result.success, f"Extraction failed: {result.error}"
                assert "def process" in result.code, "Method not extracted"
                assert "data.strip()" in result.code, "Method body not extracted"
                # Note: Method extraction may or may not include class context
            finally:
                os.unlink(f.name)


class TestJavaScriptLanguageSupport:
    """JavaScript language extraction tests."""

    def test_javascript_function_extraction(self):
        """Test extracting a JavaScript function."""
        js_code = """function greet(name) {
    return `Hello, ${name}!`;
}

function farewell(name) {
    return `Goodbye, ${name}!`;
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(js_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "greet")

                assert result.success, f"Extraction failed: {result.error}"
                assert "function greet" in result.code, "Function definition not extracted"
                assert "Hello" in result.code, "Function body not extracted"
                assert "farewell" not in result.code, "Other function incorrectly included"
            finally:
                os.unlink(f.name)

    def test_javascript_class_extraction(self):
        """Test extracting a JavaScript class."""
        js_code = """class Calculator {
    add(a, b) {
        return a + b;
    }

    subtract(a, b) {
        return a - b;
    }
}

class StringUtils {
    trim(s) {
        return s.trim();
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(js_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("class", "Calculator")

                assert result.success, f"Extraction failed: {result.error}"
                assert "class Calculator" in result.code, "Class definition not extracted"
                assert "add" in result.code, "Methods not extracted"
                assert "StringUtils" not in result.code, "Other class incorrectly included"
            finally:
                os.unlink(f.name)

    def test_javascript_method_extraction(self):
        """Test extracting a method from a JavaScript class."""
        js_code = """class DataProcessor {
    process(data) {
        return data.trim();
    }

    validate(data) {
        return data.length > 0;
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(js_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "DataProcessor.process")

                assert result.success, f"Extraction failed: {result.error}"
                assert "process" in result.code, "Method not extracted"
                assert "trim()" in result.code, "Method body not extracted"
            finally:
                os.unlink(f.name)


class TestTypeScriptLanguageSupport:
    """TypeScript language extraction tests."""

    def test_typescript_function_extraction(self):
        """Test extracting a TypeScript function with type annotations."""
        ts_code = """function greet(name: string): string {
    return `Hello, ${name}!`;
}

function farewell(name: string): string {
    return `Goodbye, ${name}!`;
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write(ts_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("function", "greet")

                assert result.success, f"Extraction failed: {result.error}"
                assert "function greet" in result.code, "Function definition not extracted"
                assert "string" in result.code, "Type annotations not preserved"
                assert "farewell" not in result.code, "Other function incorrectly included"
            finally:
                os.unlink(f.name)

    def test_typescript_class_extraction(self):
        """Test extracting a TypeScript class."""
        ts_code = """class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }

    subtract(a: number, b: number): number {
        return a - b;
    }
}

class StringUtils {
    trim(s: string): string {
        return s.trim();
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write(ts_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("class", "Calculator")

                assert result.success, f"Extraction failed: {result.error}"
                assert "class Calculator" in result.code, "Class definition not extracted"
                assert "add" in result.code, "Methods not extracted"
                assert "number" in result.code, "Type annotations not preserved"
                assert "StringUtils" not in result.code, "Other class incorrectly included"
            finally:
                os.unlink(f.name)

    def test_typescript_interface_extraction(self):
        """Test extracting a TypeScript interface."""
        ts_code = """interface User {
    name: string;
    age: number;
    email?: string;
}

interface Product {
    id: number;
    name: string;
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write(ts_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                # Note: May need to use "interface" as target_type or "class" depending on implementation
                result = extractor.extract("class", "User")  # Interfaces often treated as classes

                assert result.success, f"Extraction failed: {result.error}"
                assert "User" in result.code, "Interface not extracted"
                assert "Product" not in result.code, "Other interface incorrectly included"
            finally:
                os.unlink(f.name)


class TestJavaLanguageSupport:
    """Java language extraction tests."""

    def test_java_method_extraction(self):
        """Test extracting a Java method."""
        java_code = """public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
            f.write(java_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "Calculator.add")

                assert result.success, f"Extraction failed: {result.error}"
                assert "add" in result.code, "Method not extracted"
                assert "int a" in result.code or "a + b" in result.code, "Method signature/body not extracted"
            finally:
                os.unlink(f.name)

    def test_java_class_extraction(self):
        """Test extracting a Java class."""
        java_code = """public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}

public class StringUtils {
    public String trim(String s) {
        return s.trim();
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
            f.write(java_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("class", "Calculator")

                assert result.success, f"Extraction failed: {result.error}"
                assert "class Calculator" in result.code, "Class definition not extracted"
                assert "add" in result.code, "Methods not extracted"
                assert "StringUtils" not in result.code, "Other class incorrectly included"
            finally:
                os.unlink(f.name)

    def test_java_annotation_preservation(self):
        """Test that Java annotations are preserved during extraction."""
        java_code = """public class Service {
    @Override
    public String toString() {
        return "Service";
    }

    @Deprecated
    public void oldMethod() {
        // Legacy code
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
            f.write(java_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "Service.toString")

                assert result.success, f"Extraction failed: {result.error}"
                assert "@Override" in result.code, "Annotation not preserved"
                assert "toString" in result.code, "Method not extracted"
            finally:
                os.unlink(f.name)

    def test_java_static_method_extraction(self):
        """Test extracting a Java static method."""
        java_code = """public class MathUtils {
    public static int max(int a, int b) {
        return a > b ? a : b;
    }

    public int min(int a, int b) {
        return a < b ? a : b;
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
            f.write(java_code)
            f.flush()

            try:
                extractor = UnifiedExtractor.from_file(f.name)
                result = extractor.extract("method", "MathUtils.max")

                assert result.success, f"Extraction failed: {result.error}"
                assert "static" in result.code, "Static modifier not preserved"
                assert "max" in result.code, "Method not extracted"
                assert "min" not in result.code, "Other method incorrectly included"
            finally:
                os.unlink(f.name)
