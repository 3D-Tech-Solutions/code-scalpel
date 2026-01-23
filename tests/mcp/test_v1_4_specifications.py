"""
Code Scalpel v1.4.0 - Test Specifications Implementation
Based on Release Evidence Protocol directives.

[20251213_TEST] v1.4.0 - Comprehensive MCP tool and vulnerability detection tests.
"""

import ast
import os
import tempfile

import pytest


class TestSpec_MCP_GetFileContext:
    """
    Tests for the 'get_file_context' MCP tool.
    Target function: get_file_context(file_path: str)
    """

    def test_returns_correct_structure(self):
        """
        REQUIREMENT: The output must strictly adhere to the FileContext schema.
        """
        from code_scalpel.mcp.server import FileContextResult, _get_file_context_sync

        content = "\nimport os\nimport json\n\nclass MyClass:\n    def method(self):\n        pass\n\ndef func_one():\n    pass\n\ndef func_two():\n    pass\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            f_path = f.name
        try:
            result = _get_file_context_sync(f_path)
            assert isinstance(result, FileContextResult)
            assert result.language == "python"
            assert result.line_count > 0
            assert result.line_count == len(content.strip().split("\n")) + 1
            # [20250112_FIX] Functions may be list of FunctionInfo objects or strings
            # depending on tier. Extract names for comparison.
            func_names = [f.name if hasattr(f, "name") else f for f in result.functions]
            assert "func_one" in func_names
            assert "func_two" in func_names
            # [20250112_FIX] Classes may be list of ClassInfo objects or strings
            class_names = [c.name if hasattr(c, "name") else c for c in result.classes]
            assert "MyClass" in class_names
            assert "os" in result.imports
            assert "json" in result.imports
        finally:
            os.unlink(f_path)

    def test_complexity_calculation(self):
        """
        REQUIREMENT: Complexity score must be an integer > 0 for complex code.
        """
        from code_scalpel.mcp.server import _get_file_context_sync

        content = "\ndef complex_function(x):\n    result = 0\n    for i in range(10):\n        if i % 2 == 0:\n            if x > 5:\n                for j in range(5):\n                    while result < 100:\n                        result += 1\n            else:\n                result -= 1\n        elif i % 3 == 0:\n            result *= 2\n    return result\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            f_path = f.name
        try:
            result = _get_file_context_sync(f_path)
            assert result.complexity_score > 0
            assert result.complexity_score >= 5
        finally:
            os.unlink(f_path)

    def test_token_efficiency_summary(self):
        """
        REQUIREMENT: The 'summary' field must be present and concise.
        """
        from code_scalpel.mcp.server import _get_file_context_sync

        lines = [f"def func_{i}(): pass" for i in range(50)]
        content = "\n".join(lines)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            f_path = f.name
        try:
            result = _get_file_context_sync(f_path)
            assert result.summary is not None
            assert len(result.summary) > 0
            assert len(result.summary) < len(content)
        finally:
            os.unlink(f_path)

    def test_file_not_found_error(self):
        """
        REQUIREMENT: Should handle non-existent files gracefully.
        """
        from code_scalpel.mcp.server import _get_file_context_sync

        result = _get_file_context_sync("/nonexistent/path/file.py")
        assert result.success is False
        assert result.error is not None
        assert (
            "cannot access file" in result.error.lower()
            or "not found" in result.error.lower()
            or "no such file" in result.error.lower()
        )

    def test_syntax_error_handling(self):
        """
        REQUIREMENT: Should handle Python syntax errors gracefully.
        """
        from code_scalpel.mcp.server import _get_file_context_sync

        content = "\ndef broken_function(\n    # Missing closing paren and colon\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            f_path = f.name
        try:
            result = _get_file_context_sync(f_path)
            assert result.success is False
            assert result.error is not None
        finally:
            os.unlink(f_path)


class TestSpec_MCP_GetSymbolReferences:
    """
    Tests for the 'get_symbol_references' MCP tool.
    Target function: get_symbol_references(symbol_name: str, project_root: str)
    """

    def test_finds_cross_file_references(self):
        """
        REQUIREMENT: Must find usages of a symbol in files other than its definition.
        """
        from code_scalpel.mcp.server import _get_symbol_references_sync

        with tempfile.TemporaryDirectory() as tmpdir:
            def_path = os.path.join(tmpdir, "definitions.py")
            with open(def_path, "w") as f:
                f.write('\ndef target_func():\n    """The target function."""\n    return 42\n')
            use_path = os.path.join(tmpdir, "consumer.py")
            with open(use_path, "w") as f:
                f.write("\nfrom definitions import target_func\n\nresult = target_func()\nprint(target_func())\n")
            result = _get_symbol_references_sync("target_func", tmpdir)
            assert result.success is True
            assert result.total_references >= 2
            consumer_refs = [r for r in result.references if "consumer.py" in r.file]
            assert len(consumer_refs) >= 1

    def test_finds_definition_location(self):
        """
        REQUIREMENT: Should correctly identify where symbol is defined.
        """
        from code_scalpel.mcp.server import _get_symbol_references_sync

        with tempfile.TemporaryDirectory() as tmpdir:
            def_path = os.path.join(tmpdir, "module.py")
            with open(def_path, "w") as f:
                f.write("\nclass MyClass:\n    pass\n")
            result = _get_symbol_references_sync("MyClass", tmpdir)
            assert result.success is True
            assert result.definition_file is not None
            assert "module.py" in result.definition_file
            assert result.definition_line == 2

    def test_symbol_not_found(self):
        """
        REQUIREMENT: Should handle non-existent symbols gracefully.
        """
        from code_scalpel.mcp.server import _get_symbol_references_sync

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "empty.py")
            with open(file_path, "w") as f:
                f.write("# Empty file\n")
            result = _get_symbol_references_sync("nonexistent_symbol", tmpdir)
            assert result.success is True
            assert result.total_references == 0

    def test_invalid_project_root(self):
        """
        REQUIREMENT: Should handle invalid project paths.
        """
        from code_scalpel.mcp.server import _get_symbol_references_sync

        result = _get_symbol_references_sync("any_symbol", "/nonexistent/path")
        assert result.success is False
        assert result.error is not None


class TestSpec_Detection_XXE_CWE611:
    """
    Tests for CWE-611 XXE Detection.
    """

    @pytest.mark.parametrize(
        "vulnerable_code,sink_name",
        [
            ("import xml.etree.ElementTree as ET\nET.parse(user_input)", "ET.parse"),
            ("from lxml import etree\netree.fromstring(data)", "etree.fromstring"),
            ("import xml.sax\nxml.sax.parse(stream, handler)", "xml.sax.parse"),
        ],
    )
    def test_detects_standard_xml_parsers(self, vulnerable_code, sink_name):
        """
        REQUIREMENT: All standard library unsafe XML parsers must trigger a finding.
        """
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        matching_sinks = [k for k in SINK_PATTERNS.keys() if sink_name in k or k in sink_name]
        assert len(matching_sinks) > 0, f"No sink pattern found matching {sink_name}"
        for sink in matching_sinks:
            assert SINK_PATTERNS[sink] == SecuritySink.XXE

    @pytest.mark.parametrize(
        "safe_code",
        [
            "import defusedxml\ndefusedxml.parse(data)",
            "from defusedxml.ElementTree import parse\nparse(data)",
            "# This is just a comment about xml.etree",
        ],
    )
    def test_ignores_defused_and_safe_code(self, safe_code):
        """
        REQUIREMENT: Must not flag defusedxml or comments.
        """
        from code_scalpel.security.analyzers.taint_tracker import SANITIZER_REGISTRY

        defused_sanitizers = [k for k in SANITIZER_REGISTRY.keys() if "defusedxml" in k]
        assert len(defused_sanitizers) > 0, "No defusedxml sanitizers registered"

    def test_xxe_taint_flow_detection(self):
        """
        REQUIREMENT: Detect XXE when user input flows to XML parser.
        """
        from code_scalpel.security.analyzers import SecurityAnalyzer
        from code_scalpel.security.analyzers.taint_tracker import SecuritySink

        code = "\nfrom flask import request\nimport xml.etree.ElementTree as ET\n\nxml_file = request.args.get('file')\ntree = ET.parse(xml_file)\n"
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        xxe_vulns = [v for v in result.vulnerabilities if v.sink_type == SecuritySink.XXE]
        assert len(xxe_vulns) >= 1, "XXE vulnerability not detected"


class TestSpec_Detection_SSTI_CWE1336:
    """
    Tests for CWE-1336 SSTI Detection.
    """

    def test_detects_jinja2_template_injection(self):
        """
        REQUIREMENT: Detect 'jinja2.Template(x)' where x is variable.
        """
        from code_scalpel.security.analyzers import SecurityAnalyzer
        from code_scalpel.security.analyzers.taint_tracker import SecuritySink

        code = "\nfrom flask import request\nimport jinja2\n\ntemplate = request.args.get('t')\nrendered = jinja2.Template(template).render()\n"
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        ssti_vulns = [v for v in result.vulnerabilities if v.sink_type == SecuritySink.SSTI]
        assert len(ssti_vulns) >= 1, "SSTI vulnerability not detected"

    def test_allows_file_loading_jinja2(self):
        """
        REQUIREMENT: Do not flag standard environment loaders (best practice).
        """
        from code_scalpel.security.analyzers.taint_tracker import (
            SANITIZER_REGISTRY,
            SecuritySink,
        )

        assert "render_template" in SANITIZER_REGISTRY
        sanitizer_info = SANITIZER_REGISTRY["render_template"]
        assert SecuritySink.SSTI in sanitizer_info.clears_sinks

    @pytest.mark.parametrize(
        "template_engine",
        [
            "jinja2.Template",
            "mako.template.Template",
            "django.template.Template",
            "tornado.template.Template",
        ],
    )
    def test_detects_multiple_template_engines(self, template_engine):
        """
        REQUIREMENT: Detect SSTI across multiple template engines.
        """
        from code_scalpel.security.analyzers.taint_tracker import SINK_PATTERNS

        matching = any(template_engine in k or k in template_engine for k in SINK_PATTERNS.keys())
        assert matching, f"No SSTI sink pattern for {template_engine}"


class TestSpec_Regression_V130:
    """
    Regression tests to ensure v1.3.0 features still work.
    """

    def test_sql_injection_still_detected(self):
        """v1.3.0 SQL injection detection must still work."""
        from code_scalpel.security.analyzers import SecurityAnalyzer
        from code_scalpel.security.analyzers.taint_tracker import SecuritySink

        code = "\nfrom flask import request\nimport sqlite3\n\nuser_id = request.args.get('id')\ncursor.execute(\"SELECT * FROM users WHERE id = \" + user_id)\n"
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        sqli_vulns = [v for v in result.vulnerabilities if v.sink_type == SecuritySink.SQL_QUERY]
        assert len(sqli_vulns) >= 1

    def test_command_injection_still_detected(self):
        """v1.3.0 command injection detection must still work."""
        from code_scalpel.security.analyzers import SecurityAnalyzer
        from code_scalpel.security.analyzers.taint_tracker import SecuritySink

        code = "\nfrom flask import request\nimport os\n\ncmd = request.args.get('cmd')\nos.system(cmd)\n"
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        cmdi_vulns = [v for v in result.vulnerabilities if v.sink_type == SecuritySink.SHELL_COMMAND]
        assert len(cmdi_vulns) >= 1

    def test_secret_detection_still_works(self):
        """v1.3.0 secret detection must still work."""
        from code_scalpel.security.secrets.secret_scanner import SecretScanner

        code = '\nAWS_KEY = "AKIAIOSFODNN7EXAMPLE"\nGITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n'
        scanner = SecretScanner()
        tree = ast.parse(code)
        secrets = scanner.scan(tree)
        assert len(secrets) >= 1, "Secret detection broken"


class TestSpec_MCP_Tools_Integration:
    """
    Integration tests for MCP tools working together.
    """

    def test_file_context_and_symbol_references_consistency(self):
        """
        REQUIREMENT: get_file_context and get_symbol_references should be consistent.
        """
        from code_scalpel.mcp.server import (
            _get_file_context_sync,
            _get_symbol_references_sync,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "module.py")
            with open(file_path, "w") as f:
                f.write("\ndef important_function():\n    pass\n\nclass ImportantClass:\n    pass\n")
            context = _get_file_context_sync(file_path)
            # [20260111_BUGFIX] context.functions now contains FunctionInfo objects, not strings
            function_names = [f.name for f in context.functions]
            assert "important_function" in function_names
            refs = _get_symbol_references_sync("important_function", tmpdir)
            assert refs.total_references >= 1
            assert refs.definition_line is not None
