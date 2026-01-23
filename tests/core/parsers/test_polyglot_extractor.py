"""
Tests for v2.0.0 Polyglot Extraction - Multi-language support.

[20251214_TEST] v2.0.0 - Test JavaScript, TypeScript, and Java extraction.
"""

# [20251215_TEST] Lint cleanup for polyglot extractor tests (remove unused imports).

from code_scalpel.polyglot import (
    EXTENSION_MAP,
    Language,
    PolyglotExtractor,
    detect_language,
    extract_from_code,
)


class TestLanguageDetection:
    """Test language detection from file extensions and content."""

    def test_python_extensions(self):
        assert detect_language("test.py") == Language.PYTHON
        assert detect_language("script.pyw") == Language.PYTHON

    def test_javascript_extensions(self):
        assert detect_language("app.js") == Language.JAVASCRIPT
        assert detect_language("module.mjs") == Language.JAVASCRIPT
        assert detect_language("common.cjs") == Language.JAVASCRIPT
        assert detect_language("component.jsx") == Language.JAVASCRIPT

    def test_typescript_extensions(self):
        assert detect_language("app.ts") == Language.TYPESCRIPT
        assert detect_language("component.tsx") == Language.TYPESCRIPT
        assert detect_language("module.mts") == Language.TYPESCRIPT

    def test_java_extensions(self):
        assert detect_language("Main.java") == Language.JAVA

    def test_content_detection_python(self):
        code = """
def hello():
    print("Hello")

class Greeter:
    pass
"""
        assert detect_language(None, code) == Language.PYTHON

    def test_content_detection_java(self):
        code = """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
"""
        assert detect_language(None, code) == Language.JAVA

    def test_content_detection_typescript(self):
        code = """
interface User {
    name: string;
    age: number;
}

function greet(user: User): string {
    return `Hello ${user.name}`;
}
"""
        assert detect_language(None, code) == Language.TYPESCRIPT


class TestJavaExtraction:
    """Test Java code extraction."""

    JAVA_CODE = """
public class Calculator {
    private int result;

    public int add(int a, int b) {
        return a + b;
    }

    public int multiply(int x, int y) {
        return x * y;
    }

    public void reset() {
        this.result = 0;
    }
}
"""

    def test_extract_java_class(self):
        extractor = PolyglotExtractor(self.JAVA_CODE, language=Language.JAVA)
        result = extractor.extract("class", "Calculator")

        assert result.success
        assert result.language == "java"
        assert "public class Calculator" in result.code
        assert result.start_line > 0
        assert result.end_line >= result.start_line

    def test_extract_java_method(self):
        extractor = PolyglotExtractor(self.JAVA_CODE, language=Language.JAVA)
        result = extractor.extract("method", "Calculator.add")

        assert result.success
        assert result.language == "java"
        assert "public int add" in result.code
        assert "return a + b" in result.code

    def test_extract_java_method_multiply(self):
        extractor = PolyglotExtractor(self.JAVA_CODE, language=Language.JAVA)
        result = extractor.extract("method", "Calculator.multiply")

        assert result.success
        assert "public int multiply" in result.code

    def test_extract_nonexistent_java_method(self):
        extractor = PolyglotExtractor(self.JAVA_CODE, language=Language.JAVA)
        result = extractor.extract("method", "Calculator.notexists")

        assert not result.success
        assert "not found" in result.error.lower()


class TestJavaScriptExtraction:
    """Test JavaScript code extraction."""

    JS_CODE = """
function add(a, b) {
    return a + b;
}

const multiply = (x, y) => x * y;

async function fetchData(url) {
    const response = await fetch(url);
    return response.json();
}

class Calculator {
    constructor() {
        this.result = 0;
    }

    subtract(a, b) {
        return a - b;
    }
}
"""

    def test_extract_js_function(self):
        extractor = PolyglotExtractor(self.JS_CODE, language=Language.JAVASCRIPT)
        result = extractor.extract("function", "add")

        assert result.success
        assert result.language == "javascript"
        assert "function add" in result.code
        assert "return a + b" in result.code

    def test_extract_js_async_function(self):
        extractor = PolyglotExtractor(self.JS_CODE, language=Language.JAVASCRIPT)
        result = extractor.extract("function", "fetchData")

        assert result.success
        assert "async function fetchData" in result.code

    def test_extract_js_class(self):
        extractor = PolyglotExtractor(self.JS_CODE, language=Language.JAVASCRIPT)
        result = extractor.extract("class", "Calculator")

        assert result.success
        assert "class Calculator" in result.code
        assert "constructor" in result.code

    def test_extract_nonexistent_js_function(self):
        extractor = PolyglotExtractor(self.JS_CODE, language=Language.JAVASCRIPT)
        result = extractor.extract("function", "notexists")

        assert not result.success
        assert "not found" in result.error.lower()


class TestExtractFromCode:
    """Test the convenience function extract_from_code."""

    def test_auto_detect_python(self):
        code = "def hello(): pass"
        result = extract_from_code(code, "function", "hello")

        assert result.success
        assert result.language == "python"

    def test_auto_detect_java(self):
        code = "public class Test { public void test() {} }"
        result = extract_from_code(code, "class", "Test")

        assert result.success
        assert result.language == "java"

    def test_explicit_language(self):
        code = "function test() { return 42; }"
        result = extract_from_code(code, "function", "test", Language.JAVASCRIPT)

        assert result.success
        assert result.language == "javascript"


class TestTokenEstimate:
    """Test token estimation in results."""

    def test_java_token_estimate(self):
        code = "public class Test { public int add(int a, int b) { return a + b; } }"
        extractor = PolyglotExtractor(code, language=Language.JAVA)
        result = extractor.extract("class", "Test")

        assert result.success
        assert result.token_estimate > 0
        # Token estimate is len(code) // 4
        assert result.token_estimate == len(result.code) // 4


class TestExtensionMap:
    """Test the extension mapping completeness."""

    def test_all_common_extensions_mapped(self):
        # Python
        assert ".py" in EXTENSION_MAP
        # JavaScript
        assert ".js" in EXTENSION_MAP
        assert ".jsx" in EXTENSION_MAP
        # TypeScript
        assert ".ts" in EXTENSION_MAP
        assert ".tsx" in EXTENSION_MAP
        # Java
        assert ".java" in EXTENSION_MAP
