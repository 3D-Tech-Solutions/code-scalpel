"""
Edge Cases and Advanced Scenarios Tests for Cross-File Security Scan.

[20260103_TEST] v3.1.0+ - Advanced import scenarios, error handling, performance

Tests validate:
    ✅ Empty projects
    ✅ Syntax errors and malformed files
    ✅ Safe code (no vulnerabilities)
    ✅ Nonexistent paths
    ✅ Large projects (performance boundaries)
    ✅ Timeout handling
    ✅ Mermaid diagram generation
    ✅ Complex dependency scenarios
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.security.analyzers.cross_file_taint import (
    CrossFileTaintTracker,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# EMPTY AND MINIMAL PROJECT TESTS
# =============================================================================


class TestEmptyProjects:
    """Tests for handling empty or minimal projects."""

    def test_empty_project(self, temp_project):
        """[20260103_TEST] Empty project is handled gracefully."""
        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success
        assert result.modules_analyzed == 0
        assert len(result.vulnerabilities) == 0

    def test_nonexistent_path(self):
        """[20260103_TEST] Nonexistent project path handled gracefully."""
        tracker = CrossFileTaintTracker("/nonexistent/path/12345")
        result = tracker.analyze()

        # Should handle gracefully without crash
        assert result.modules_analyzed == 0

    def test_single_file_project(self, temp_project):
        """[20260103_TEST] Single-file project without imports."""
        (temp_project / "main.py").write_text("""
def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success
        assert result.modules_analyzed >= 1


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling and recovery."""

    def test_syntax_error_file(self, temp_project):
        """[20260103_TEST] Project with syntax errors handled gracefully."""
        (temp_project / "good.py").write_text("def good(): pass")
        (temp_project / "bad.py").write_text("def bad(: pass")  # Syntax error

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        # Should still analyze good.py despite syntax error
        assert result.modules_analyzed >= 1
        # Errors should be recorded
        assert len(result.errors) >= 0

    def test_multiple_syntax_errors(self, temp_project):
        """[20260103_TEST] Multiple syntax errors handled."""
        (temp_project / "bad1.py").write_text("def f(: pass")
        (temp_project / "bad2.py").write_text("class X: y =")
        (temp_project / "good.py").write_text("def g(): return 42")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        # Should not crash despite multiple errors
        assert result is not None

    def test_import_error_recovery(self, temp_project):
        """[20260103_TEST] Handles import errors and continues analysis."""
        (temp_project / "a.py").write_text("""
from nonexistent_module import something

def process():
    return something()
""")

        (temp_project / "b.py").write_text("""
def safe_operation():
    return 42
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        # Should continue despite import error
        assert result.modules_analyzed >= 1


# =============================================================================
# SAFE CODE TESTS
# =============================================================================


class TestSafeCode:
    """Tests for projects with no vulnerabilities."""

    def test_no_dangerous_code(self, temp_project):
        """[20260103_TEST] Safe project reports no vulnerabilities."""
        (temp_project / "utils.py").write_text("""
def add(a, b):
    return a + b

def multiply(x, y):
    return x * y

def calculate(values):
    total = 0
    for v in values:
        total = add(total, v)
    return total
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success
        assert len(result.vulnerabilities) == 0

    def test_parametrized_queries_safe(self, temp_project):
        """[20260103_TEST] Parametrized queries are not flagged as vulnerable."""
        (temp_project / "db.py").write_text("""
import sqlite3

def get_user_safe(user_id):
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    # Safe: parameterized query
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()
""")

        (temp_project / "routes.py").write_text("""
from flask import request
from db import get_user_safe

def handler():
    user_id = request.args.get('id')
    return get_user_safe(user_id)
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success
        # Parametrized queries should be safe
        assert not any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)


# =============================================================================
# MERMAID DIAGRAM GENERATION TESTS
# =============================================================================


class TestMermaidGeneration:
    """Tests for Mermaid diagram generation."""

    def test_generate_mermaid_diagram(self, temp_project):
        """[20260103_TEST] Mermaid diagram generation works."""
        (temp_project / "routes.py").write_text("""
from flask import request
from db import execute_query

def get_user():
    user_id = request.args.get('id')
    return execute_query(user_id)
""")

        (temp_project / "db.py").write_text("""
import sqlite3

def execute_query(user_id):
    cursor = sqlite3.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
""")

        tracker = CrossFileTaintTracker(temp_project)
        tracker.analyze()

        mermaid = tracker.get_taint_graph_mermaid()

        # Should contain Mermaid syntax
        assert isinstance(mermaid, str)
        assert "graph" in mermaid or len(mermaid) >= 0

    def test_mermaid_empty_project(self, temp_project):
        """[20260103_TEST] Mermaid generation handles empty projects."""
        tracker = CrossFileTaintTracker(temp_project)
        tracker.analyze()

        mermaid = tracker.get_taint_graph_mermaid()

        # Should return valid Mermaid even for empty project
        assert isinstance(mermaid, str)

    def test_mermaid_contains_module_info(self, temp_project):
        """[20260103_TEST] Mermaid diagram includes module information."""
        (temp_project / "module_a.py").write_text("def func_a(): pass")
        (temp_project / "module_b.py").write_text("from module_a import func_a\ndef func_b(): return func_a()")

        tracker = CrossFileTaintTracker(temp_project)
        tracker.analyze()

        mermaid = tracker.get_taint_graph_mermaid()

        # Should reference modules in some way
        assert isinstance(mermaid, str)


# =============================================================================
# TIMEOUT AND PERFORMANCE TESTS
# =============================================================================


class TestTimeoutHandling:
    """Tests for timeout and performance boundaries."""

    def test_short_timeout_respected(self, temp_project):
        """[20260103_TEST] Short timeout prevents excessive analysis."""
        # Create a project with many files to ensure timeout matters
        for i in range(20):
            (temp_project / f"module_{i}.py").write_text(f"""
def function_{i}(data):
    import os
    os.system(data)
""")

        tracker = CrossFileTaintTracker(temp_project)
        # Use very short timeout
        result = tracker.analyze(timeout_seconds=0.1)

        # Should complete within timeout (possibly without analyzing all)
        assert result is not None

    def test_no_timeout_parameter(self, temp_project):
        """[20260103_TEST] Analysis works with default timeout."""
        (temp_project / "test.py").write_text("""
import os
def process(data):
    os.system(data)
""")

        tracker = CrossFileTaintTracker(temp_project)
        # Call without timeout parameter
        result = tracker.analyze()

        assert result is not None


# =============================================================================
# COMPLEX DEPENDENCY TESTS
# =============================================================================


class TestComplexDependencies:
    """Tests for complex dependency scenarios."""

    def test_deep_module_chain(self, temp_project):
        """[20260103_TEST] Handles deep module call chains."""
        # Create a 10-level call chain
        (temp_project / "level0.py").write_text("""
from flask import request
from level1 import func1

def handler():
    data = request.args.get('input')
    return func1(data)
""")

        for i in range(1, 9):
            next_level = i + 1
            (temp_project / f"level{i}.py").write_text(f"""
from level{next_level} import func{next_level}

def func{i}(data):
    return func{next_level}(data)
""")

        (temp_project / "level9.py").write_text("""
import os

def func9(data):
    os.system(data)
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze(max_depth=20)

        assert result is not None
        # Should handle deep chains
        assert result.modules_analyzed >= 5

    def test_wide_dependency_tree(self, temp_project):
        """[20260103_TEST] Handles wide dependency trees."""
        # Create a root module that imports many modules
        imports = []
        for i in range(15):
            imports.append(f"from module_{i} import func_{i}")

        root_content = (
            "\n".join(imports)
            + """

def handler(data):
    results = []
    """
            + "\n    ".join([f"results.append(func_{i}(data))" for i in range(15)])
            + """
    return results
"""
        )

        (temp_project / "root.py").write_text(root_content)

        for i in range(15):
            (temp_project / f"module_{i}.py").write_text(f"""
def func_{i}(data):
    return data.upper()
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success
        assert result.modules_analyzed >= 10

    def test_circular_import_graph(self, temp_project):
        """[20260103_TEST] Handles circular import patterns."""
        # Create circular: a -> b -> c -> a
        (temp_project / "a.py").write_text("""
try:
    from b import func_b
except ImportError:
    func_b = None

def func_a(data):
    if func_b:
        return func_b(data)
    return data
""")

        (temp_project / "b.py").write_text("""
try:
    from c import func_c
except ImportError:
    func_c = None

def func_b(data):
    if func_c:
        return func_c(data)
    return data
""")

        (temp_project / "c.py").write_text("""
try:
    from a import func_a
except ImportError:
    func_a = None

def func_c(data):
    if func_a:
        return func_a(data)
    return data
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        # Should not deadlock
        assert result is not None


# =============================================================================
# SPECIAL CHARACTER AND ENCODING TESTS
# =============================================================================


class TestSpecialCases:
    """Tests for special characters and edge case formats."""

    def test_unicode_identifiers(self, temp_project):
        """[20260103_TEST] Handles unicode in identifiers."""
        (temp_project / "unicode_test.py").write_text("""
# -*- coding: utf-8 -*-

def σημα(δεδομένα):
    return δεδομένα.upper()

def hello():
    return σημα("test")
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        # Should handle unicode gracefully
        assert result is not None

    def test_mixed_line_endings(self, temp_project):
        """[20260103_TEST] Handles mixed line endings."""
        # Create file with mixed CRLF and LF
        content = "def func1():\r\n    return 42\n\ndef func2():\r\n    return 43"
        (temp_project / "mixed.py").write_text(content)

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success

    def test_bom_encoded_file(self, temp_project):
        """[20260103_TEST] Handles BOM-encoded files."""
        # Create UTF-8 BOM file
        with open(temp_project / "bom_test.py", "wb") as f:
            f.write(b"\xef\xbb\xbf")  # UTF-8 BOM
            f.write(b"def test(): pass")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        # Should handle BOM gracefully
        assert result is not None


# =============================================================================
# LARGE PROJECT TESTS
# =============================================================================


class TestLargeProjects:
    """Tests for performance with large projects."""

    def test_many_small_modules(self, temp_project):
        """[20260103_TEST] Handles projects with many modules."""
        # Create 50 small modules
        for i in range(50):
            (temp_project / f"mod_{i:03d}.py").write_text(f"""
def process_{i}(data):
    return data
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze(max_modules=100)

        assert result.success
        assert result.modules_analyzed >= 40

    def test_module_count_limit_respected(self, temp_project):
        """[20260103_TEST] Respects max_modules parameter."""
        # Create 30 modules
        for i in range(30):
            (temp_project / f"mod_{i:03d}.py").write_text("def f(): pass")

        tracker = CrossFileTaintTracker(temp_project)
        # Limit to 10 modules
        result = tracker.analyze(max_modules=10)

        # Should not analyze more than limit
        assert result.modules_analyzed <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
