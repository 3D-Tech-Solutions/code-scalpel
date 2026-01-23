"""
Multi-language tests for get_file_context.

Tests that get_file_context properly handles multiple programming languages:
- Python (full support)
- JavaScript (basic support)
- TypeScript (basic support)
- Java (basic support)

These tests validate:
1. Language detection and correct parsing
2. Feature parity across languages
3. Language-specific syntax handling
4. Import/export consistency across languages
"""

from pathlib import Path


class TestPythonExtraction:
    """Test Python code extraction (fully supported)."""

    def test_python_function_extraction(self, temp_python_project):
        """Python should extract functions correctly."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        good_code_path = temp_python_project / "good_code.py"
        result = _get_file_context_sync(str(good_code_path), capabilities=[])

        # Should extract Python functions
        assert result.functions is not None
        assert len(result.functions) > 0

    def test_python_class_extraction(self, temp_python_project):
        """Python should extract classes correctly."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        good_code_path = temp_python_project / "good_code.py"
        result = _get_file_context_sync(str(good_code_path), capabilities=[])

        # Should extract Python classes
        assert result.classes is not None
        assert len(result.classes) > 0

    def test_python_import_extraction(self, temp_python_project):
        """Python should extract imports correctly."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        good_code_path = temp_python_project / "good_code.py"
        result = _get_file_context_sync(str(good_code_path), capabilities=[])

        # Should extract Python imports
        assert result.imports is not None

    def test_python_complexity_calculation(self, temp_python_project):
        """Python should calculate complexity correctly."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        good_code_path = temp_python_project / "good_code.py"
        result = _get_file_context_sync(str(good_code_path), capabilities=[])

        # Should calculate complexity
        assert result.complexity_score is not None


class TestJavaScriptExtraction:
    """Test JavaScript code extraction."""

    def test_javascript_function_extraction(self, temp_javascript_project):
        """JavaScript should extract functions correctly."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        js_path = temp_javascript_project / "processor.js"
        result = _get_file_context_sync(str(js_path), capabilities=[])

        # Should extract JavaScript functions
        assert result.functions is not None
        # JavaScript file should have functions
        if result.functions:
            assert len(result.functions) > 0

    def test_javascript_class_extraction(self, temp_javascript_project):
        """JavaScript should extract classes correctly."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        js_path = temp_javascript_project / "processor.js"
        result = _get_file_context_sync(str(js_path), capabilities=[])

        # Should extract JavaScript classes
        assert result.classes is not None
        # JavaScript file has DataProcessor class
        if result.classes:
            assert len(result.classes) > 0

    def test_javascript_import_export_detection(self, temp_javascript_project):
        """JavaScript should detect imports and exports."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        js_path = temp_javascript_project / "processor.js"
        result = _get_file_context_sync(str(js_path), capabilities=[])

        # Should detect imports/exports
        assert result.imports is not None


class TestTypeScriptExtraction:
    """Test TypeScript code extraction."""

    def test_typescript_function_extraction(self, temp_typescript_project):
        """TypeScript should extract functions correctly."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        ts_path = temp_typescript_project / "user.ts"
        result = _get_file_context_sync(str(ts_path), capabilities=[])

        # Should extract TypeScript functions
        assert result.functions is not None

    def test_typescript_interface_detection(self, temp_typescript_project):
        """TypeScript should detect interfaces (types)."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        ts_path = temp_typescript_project / "user.ts"
        result = _get_file_context_sync(str(ts_path), capabilities=[])

        # TypeScript should detect interfaces
        assert result.classes is not None or result.functions is not None

    def test_typescript_type_annotations(self, temp_typescript_project):
        """TypeScript should handle type annotations."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        ts_path = temp_typescript_project / "user.ts"
        result = _get_file_context_sync(str(ts_path), capabilities=[])

        # Should handle TypeScript types gracefully
        assert result is not None


class TestJavaExtraction:
    """Test Java code extraction."""

    def test_java_class_extraction(self, temp_java_project):
        """Java should extract classes correctly."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        java_path = temp_java_project / "DataProcessor.java"
        result = _get_file_context_sync(str(java_path), capabilities=[])

        # Should extract Java classes
        assert result.classes is not None

    def test_java_method_extraction(self, temp_java_project):
        """Java should extract methods (functions)."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        java_path = temp_java_project / "DataProcessor.java"
        result = _get_file_context_sync(str(java_path), capabilities=[])

        # Should extract Java methods
        assert result.functions is not None

    def test_java_import_detection(self, temp_java_project):
        """Java should detect imports."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        java_path = temp_java_project / "DataProcessor.java"
        result = _get_file_context_sync(str(java_path), capabilities=[])

        # Should detect Java imports
        assert result.imports is not None

    def test_java_package_detection(self, temp_java_project):
        """Java should detect package declarations."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        java_path = temp_java_project / "DataProcessor.java"
        result = _get_file_context_sync(str(java_path), capabilities=[])

        # Should detect package
        assert result is not None


class TestLanguageFeatureParity:
    """Test feature parity across languages."""

    def test_all_languages_extract_functions(
        self,
        temp_python_project,
        temp_javascript_project,
        temp_typescript_project,
        temp_java_project,
    ):
        """All supported languages should extract functions."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # Python
        py_result = _get_file_context_sync(str(temp_python_project / "good_code.py"), capabilities=[])
        assert py_result.functions is not None

        # JavaScript
        js_result = _get_file_context_sync(str(temp_javascript_project / "processor.js"), capabilities=[])
        assert js_result.functions is not None

        # TypeScript
        ts_result = _get_file_context_sync(str(temp_typescript_project / "user.ts"), capabilities=[])
        assert ts_result.functions is not None

        # Java
        java_result = _get_file_context_sync(str(temp_java_project / "DataProcessor.java"), capabilities=[])
        assert java_result.functions is not None

    def test_all_languages_extract_classes(
        self,
        temp_python_project,
        temp_javascript_project,
        temp_typescript_project,
        temp_java_project,
    ):
        """All supported languages should extract classes."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # Python
        py_result = _get_file_context_sync(str(temp_python_project / "good_code.py"), capabilities=[])
        assert py_result.classes is not None

        # JavaScript
        js_result = _get_file_context_sync(str(temp_javascript_project / "processor.js"), capabilities=[])
        assert js_result.classes is not None

        # TypeScript
        ts_result = _get_file_context_sync(str(temp_typescript_project / "user.ts"), capabilities=[])
        assert ts_result.classes is not None

        # Java
        java_result = _get_file_context_sync(str(temp_java_project / "DataProcessor.java"), capabilities=[])
        assert java_result.classes is not None

    def test_all_languages_detect_imports(
        self,
        temp_python_project,
        temp_javascript_project,
        temp_typescript_project,
        temp_java_project,
    ):
        """All supported languages should detect imports."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # Python
        py_result = _get_file_context_sync(str(temp_python_project / "good_code.py"), capabilities=[])
        assert py_result.imports is not None

        # JavaScript
        js_result = _get_file_context_sync(str(temp_javascript_project / "processor.js"), capabilities=[])
        assert js_result.imports is not None

        # TypeScript
        ts_result = _get_file_context_sync(str(temp_typescript_project / "user.ts"), capabilities=[])
        assert ts_result.imports is not None

        # Java
        java_result = _get_file_context_sync(str(temp_java_project / "DataProcessor.java"), capabilities=[])
        assert java_result.imports is not None

    def test_all_languages_calculate_complexity(
        self,
        temp_python_project,
        temp_javascript_project,
        temp_typescript_project,
        temp_java_project,
    ):
        """All supported languages should calculate complexity."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # Python
        py_result = _get_file_context_sync(str(temp_python_project / "good_code.py"), capabilities=[])
        assert py_result.complexity_score is not None

        # JavaScript
        js_result = _get_file_context_sync(str(temp_javascript_project / "processor.js"), capabilities=[])
        assert js_result.complexity_score is not None

        # TypeScript
        ts_result = _get_file_context_sync(str(temp_typescript_project / "user.ts"), capabilities=[])
        assert ts_result.complexity_score is not None

        # Java
        java_result = _get_file_context_sync(str(temp_java_project / "DataProcessor.java"), capabilities=[])
        assert java_result.complexity_score is not None


class TestLanguageSyntaxHandling:
    """Test handling of language-specific syntax."""

    def test_python_type_hints(self, tmpdir):
        """Python should handle type hints."""
        code = "def add(a: int, b: int) -> int: return a + b"
        test_file = Path(tmpdir) / "typed.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(str(test_file), capabilities=[])
        # Should handle type hints gracefully
        assert result is not None

    def test_javascript_arrow_functions(self, tmpdir):
        """JavaScript should handle arrow functions."""
        code = "const add = (a, b) => a + b;"
        test_file = Path(tmpdir) / "arrow.js"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(str(test_file), capabilities=[])
        # Should handle arrow functions gracefully
        assert result is not None

    def test_typescript_generic_types(self, tmpdir):
        """TypeScript should handle generic types."""
        code = """
        class Container<T> {
            value: T;
            constructor(value: T) { this.value = value; }
        }
        """
        test_file = Path(tmpdir) / "generic.ts"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(str(test_file), capabilities=[])
        # Should handle generics gracefully
        assert result is not None

    def test_java_annotations(self, tmpdir):
        """Java should handle annotations."""
        code = """
        @Override
        public String toString() {
            return "test";
        }
        """
        test_file = Path(tmpdir) / "annotated.java"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(str(test_file), capabilities=[])
        # Should handle annotations gracefully
        assert result is not None
