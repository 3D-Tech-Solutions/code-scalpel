# [20260103_TEST] Language support tests for surgical patching
"""
Language support tests for update_symbol tool.

These tests verify that the tool correctly handles all declared supported languages:
- Python
- JavaScript
- TypeScript
- Java

Tests use UnifiedPatcher which auto-detects language from file extension and routes
to the appropriate parser (SurgicalPatcher for Python, PolyglotPatcher for others).
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from code_scalpel.surgery.surgical_patcher import UnifiedPatcher


class TestPythonLanguageSupport:
    """Python language support tests."""

    def test_python_function_replacement(self):
        """Test replacing a Python function with new implementation."""
        python_code = '''def greet(name):
    """Return a greeting."""
    return f"Hello, {name}!"

def farewell(name):
    return f"Goodbye, {name}!"
'''
        new_function = '''def greet(name):
    """Return an enhanced greeting."""
    return f"Hello, {name}! Welcome back!"'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_function("greet", new_function)

                assert result.success, f"Function replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "Welcome back" in patched, "New code not inserted"
                assert "farewell" in patched, "Other function removed"
                assert patched.count("def ") == 2, "Incorrect function count"
            finally:
                os.unlink(f.name)

    def test_python_class_replacement(self):
        """Test replacing a Python class with new implementation."""
        python_code = """class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

class StringUtils:
    pass
"""
        new_class = '''class Calculator:
    """Enhanced calculator with logging."""
    def add(self, a, b):
        result = a + b
        print(f"Added {a} + {b} = {result}")
        return result

    def subtract(self, a, b):
        result = a - b
        print(f"Subtracted {a} - {b} = {result}")
        return result'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_class("Calculator", new_class)

                assert result.success, f"Class replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "Enhanced calculator" in patched, "Docstring not added"
                assert "print" in patched, "Logging not added"
                assert "StringUtils" in patched, "Other class removed"
            finally:
                os.unlink(f.name)

    def test_python_method_replacement(self):
        """Test replacing a method in a Python class."""
        python_code = """class DataProcessor:
    def process(self, data):
        return data.upper()

    def validate(self, data):
        return len(data) > 0
"""
        new_method = '''def process(self, data):
    """Process data with validation."""
    if not data:
        return ""
    return data.upper().strip()'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_method("DataProcessor", "process", new_method)

                assert result.success, f"Method replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "strip()" in patched, "New logic not added"
                assert "validate" in patched, "Other method removed"
            finally:
                os.unlink(f.name)


class TestJavaScriptLanguageSupport:
    """JavaScript language support tests."""

    def test_javascript_function_replacement(self):
        """Test replacing a JavaScript function with new implementation."""
        js_code = """function greet(name) {
    return `Hello, ${name}!`;
}

const farewell = (name) => {
    return `Goodbye, ${name}!`;
};
"""
        new_function = """function greet(name) {
    if (!name) return "Hello, stranger!";
    return `Hello, ${name}! Welcome back!`;
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(js_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_function("greet", new_function)

                assert result.success, f"Function replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "Welcome back" in patched, "New code not inserted"
                assert "farewell" in patched, "Other function removed"
            finally:
                os.unlink(f.name)

    def test_javascript_class_replacement(self):
        """Test replacing a JavaScript class with new implementation."""
        js_code = """class Calculator {
    add(a, b) {
        return a + b;
    }

    subtract(a, b) {
        return a - b;
    }
}

class Logger {
    log(msg) {
        console.log(msg);
    }
}
"""
        new_class = """class Calculator {
    constructor() {
        this.operations = 0;
    }

    add(a, b) {
        this.operations++;
        console.log(`Operation #${this.operations}`);
        return a + b;
    }

    subtract(a, b) {
        this.operations++;
        return a - b;
    }
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(js_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_class("Calculator", new_class)

                assert result.success, f"Class replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "constructor" in patched, "Constructor not added"
                assert "Logger" in patched, "Other class removed"
            finally:
                os.unlink(f.name)

    def test_javascript_method_replacement(self):
        """Test replacing a method in a JavaScript class."""
        js_code = """class DataProcessor {
    process(data) {
        return data.toUpperCase();
    }

    validate(data) {
        return data.length > 0;
    }
}
"""
        new_method = """process(data) {
    if (!data) return "";
    return data.trim().toUpperCase();
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(js_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_method("DataProcessor", "process", new_method)

                assert result.success, f"Method replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "trim()" in patched, "New logic not added"
                assert "validate" in patched, "Other method removed"
            finally:
                os.unlink(f.name)


class TestTypeScriptLanguageSupport:
    """TypeScript language support tests."""

    def test_typescript_function_replacement(self):
        """Test replacing a TypeScript function with type annotations."""
        ts_code = """function greet(name: string): string {
    return `Hello, ${name}!`;
}

function farewell(name: string): string {
    return `Goodbye, ${name}!`;
}
"""
        new_function = """function greet(name: string): string {
    if (!name || name.length === 0) {
        return "Hello, stranger!";
    }
    return `Hello, ${name}! Welcome back!`;
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write(ts_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_function("greet", new_function)

                assert result.success, f"Function replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert ": string" in patched, "Type annotation removed"
                assert "Welcome back" in patched, "New code not inserted"
                assert "farewell" in patched, "Other function removed"
            finally:
                os.unlink(f.name)

    def test_typescript_class_replacement(self):
        """Test replacing a TypeScript class with generics/interfaces."""
        ts_code = """interface Operation {
    execute(): number;
}

class Calculator implements Operation {
    add(a: number, b: number): number {
        return a + b;
    }

    execute(): number {
        return this.add(1, 1);
    }
}
"""
        new_class = """class Calculator implements Operation {
    private operationCount: number = 0;

    add(a: number, b: number): number {
        this.operationCount++;
        console.log(`Operation #${this.operationCount}`);
        return a + b;
    }

    execute(): number {
        return this.add(1, 1);
    }
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write(ts_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_class("Calculator", new_class)

                assert result.success, f"Class replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "private operationCount" in patched, "Private field not added"
                assert "interface Operation" in patched, "Interface removed"
            finally:
                os.unlink(f.name)

    def test_typescript_method_replacement(self):
        """Test replacing a method in a TypeScript class."""
        ts_code = """class DataProcessor {
    process(data: string): string {
        return data.toUpperCase();
    }

    validate(data: string): boolean {
        return data.length > 0;
    }
}
"""
        new_method = """process(data: string): string {
    if (!data || data.length === 0) {
        return "";
    }
    return data.trim().toUpperCase();
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write(ts_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_method("DataProcessor", "process", new_method)

                assert result.success, f"Method replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "trim()" in patched, "New logic not added"
                assert ": string" in patched, "Type annotation removed"
                assert "validate" in patched, "Other method removed"
            finally:
                os.unlink(f.name)


class TestJavaLanguageSupport:
    """Java language support tests."""

    def test_java_method_replacement(self):
        """Test replacing a method in a Java class."""
        java_code = """public class DataProcessor {
    public String process(String data) {
        return data.toUpperCase();
    }

    public boolean validate(String data) {
        return data.length() > 0;
    }
}
"""
        new_method = """public String process(String data) {
    if (data == null || data.isEmpty()) {
        return "";
    }
    return data.trim().toUpperCase();
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
            f.write(java_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_method("DataProcessor", "process", new_method)

                assert result.success, f"Method replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "trim()" in patched, "New logic not added"
                assert "public String" in patched, "Return type removed"
                assert "validate" in patched, "Other method removed"
            finally:
                os.unlink(f.name)

    def test_java_class_replacement(self):
        """Test replacing a Java class with constructor/fields."""
        java_code = """public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }
}

public class Logger {
    public void log(String msg) {
        System.out.println(msg);
    }
}
"""
        new_class = """public class Calculator {
    private int operationCount = 0;

    public Calculator() {
        this.operationCount = 0;
    }

    public int add(int a, int b) {
        this.operationCount++;
        System.out.println("Operation #" + this.operationCount);
        return a + b;
    }

    public int subtract(int a, int b) {
        this.operationCount++;
        return a - b;
    }
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
            f.write(java_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_class("Calculator", new_class)

                assert result.success, f"Class replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "operationCount" in patched, "Field not added"
                assert "public Calculator()" in patched, "Constructor not added"
                assert "Logger" in patched, "Other class removed"
            finally:
                os.unlink(f.name)

    def test_java_annotation_preservation(self):
        """Test replacing a method with annotations preserved."""
        java_code = """public class DataService {
    @Override
    public String toString() {
        return "DataService";
    }

    @Deprecated
    public void oldMethod() {
        System.out.println("Old");
    }

    @SuppressWarnings("unchecked")
    public void process() {
        System.out.println("Processing");
    }
}
"""
        new_method = """@Override
public String toString() {
    return "DataService [version=2.0]";
}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".java", delete=False) as f:
            f.write(java_code)
            f.flush()

            try:
                patcher = UnifiedPatcher.from_file(f.name)
                result = patcher.update_method("DataService", "toString", new_method)

                assert result.success, f"Method replacement failed: {result.error}"
                patched = patcher.get_modified_code()
                assert "@Override" in patched, "Override annotation removed"
                assert "@Deprecated" in patched, "Deprecated annotation removed"
                assert "version=2.0" in patched, "New implementation not added"
            finally:
                os.unlink(f.name)
