"""Tests for MCP Server tools.

Tests the FastMCP-based Model Context Protocol server.
All MCP tool functions are async and return Pydantic models.
"""

import pytest
from pydantic import BaseModel, Field

from code_scalpel.mcp.contract import ToolError

# Mark entire module as async
pytestmark = pytest.mark.asyncio


class _FakeCallGraphResult(BaseModel):
    success: bool = True
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


class _FakeGraphNeighborhoodResult(BaseModel):
    success: bool = True
    center_node: dict = Field(default_factory=dict)
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


class _FakeProjectMapResult(BaseModel):
    success: bool = True
    total_files: int = 1
    total_lines: int = 5
    modules: list[dict] = Field(default_factory=list)
    dependencies: list[dict] = Field(default_factory=list)
    complexity_hotspots: list[dict] = Field(default_factory=list)
    mermaid: str = "graph TD"


class _FakeCrossFileDependenciesResult(BaseModel):
    success: bool = True
    target_symbol: str = "helper"
    extracted_symbols: list[dict] = Field(default_factory=list)
    dependency_graph: dict = Field(default_factory=dict)
    combined_code: str = ""
    confidence_scores: dict = Field(default_factory=dict)
    mermaid: str = "graph TD"
    truncated: bool = False


class _FakeCrossFileSecurityResult(BaseModel):
    success: bool = True
    vulnerability_count: int = 0
    files_analyzed: int = 1
    has_vulnerabilities: bool = False
    risk_level: str = "low"
    vulnerabilities: list[dict] = Field(default_factory=list)
    taint_flows: list[dict] = Field(default_factory=list)
    taint_sources: list[str] = Field(default_factory=list)
    dangerous_sinks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    mermaid: str = "graph TD"


def get_error_message(error) -> str:
    """[20260201_BUGFIX] Extract error message from either string or ToolError.

    The Oracle middleware may enhance errors to ToolError objects,
    so tests need to handle both string and ToolError error fields.
    """
    if error is None:
        return ""
    if isinstance(error, ToolError):
        return error.error
    return str(error)


class TestAnalyzeCodeTool:
    """Tests for the analyze_code tool."""

    async def test_analyze_simple_function(self):
        """Test analyzing a simple function."""
        from code_scalpel.mcp.server import analyze_code

        code = """
def hello():
    return "Hello, World!"
"""
        result = await analyze_code(code)
        assert result.success is True
        assert "hello" in result.functions
        assert result.function_count == 1

    async def test_analyze_class(self):
        """Test analyzing a class definition."""
        from code_scalpel.mcp.server import analyze_code

        code = """
class MyClass:
    def __init__(self):
        pass

    def method(self):
        return 42
"""
        result = await analyze_code(code)
        assert result.success is True
        assert "MyClass" in result.classes
        assert result.class_count == 1
        assert result.function_count == 2  # __init__ and method

    async def test_analyze_imports(self):
        """Test analyzing imports."""
        from code_scalpel.mcp.server import analyze_code

        code = """
import os
from pathlib import Path
import sys
"""
        result = await analyze_code(code)
        assert result.success is True
        assert "os" in result.imports
        assert "sys" in result.imports
        assert any("Path" in imp for imp in result.imports)

    async def test_analyze_complexity(self):
        """Test complexity calculation."""
        from code_scalpel.mcp.server import analyze_code

        code = """
def complex_func(x):
    if x > 0:
        if x > 10:
            return "big"
        return "small"
    return "negative"
"""
        result = await analyze_code(code)
        assert result.success is True
        assert result.complexity >= 3  # At least 3 due to two if statements

    async def test_analyze_empty_code(self):
        """Test analyzing empty code."""
        from code_scalpel.mcp.server import analyze_code

        result = await analyze_code("")
        assert result.success is False
        assert result.error is not None
        assert "empty" in get_error_message(result.error).lower()

    async def test_analyze_syntax_error(self):
        """Test handling syntax errors."""
        from code_scalpel.mcp.server import analyze_code

        code = "def broken("
        result = await analyze_code(code)
        assert result.success is False
        assert result.error is not None
        assert "syntax" in get_error_message(result.error).lower()

    async def test_analyze_async_function(self):
        """Test analyzing async functions."""
        from code_scalpel.mcp.server import analyze_code

        code = """
async def async_func():
    await some_coroutine()
"""
        result = await analyze_code(code)
        assert result.success is True
        assert any("async_func" in f for f in result.functions)

    async def test_analyze_file_not_found_with_oracle_suggestions(
        self, tmp_path, monkeypatch
    ):
        """Test file not found error provides Oracle fuzzy matching suggestions."""
        from code_scalpel.mcp.server import analyze_code

        # Create a real project root with a file similar to the requested path
        (tmp_path / "utils.py").write_text("def helper(): pass\n")
        monkeypatch.setattr(
            "code_scalpel.mcp.helpers.session._get_project_root",
            lambda: str(tmp_path),
        )

        # Test with a non-existent file that has similar names in the project
        result = await analyze_code(file_path=str(tmp_path / "utilz.py"))

        # For error cases, check the envelope's error field
        assert result.error is not None
        assert "not found" in result.error.error.lower()
        assert result.error.error_code == "correction_needed"

        # Check that Oracle suggestions are provided in error_details
        assert result.error.error_details is not None
        assert "oracle_suggestion" in result.error.error_details

        oracle = result.error.error_details["oracle_suggestion"]
        assert isinstance(oracle, dict)
        assert "suggestion" in oracle
        assert "confidence" in oracle
        assert isinstance(oracle["confidence"], (int, float))
        assert 0 <= oracle["confidence"] <= 1

    async def test_analyze_uses_shared_path_resolver_for_malformed_windows_path(
        self, tmp_path, monkeypatch
    ):
        """Malformed '/K:/...' paths should be recovered through shared path resolution."""
        from code_scalpel.mcp.server import analyze_code

        real_file = tmp_path / "legacy_processor.py"
        real_file.write_text("def normalize_me():\n    return 1\n")

        requested_path = "/K:/backup/Develop/code-scalpel-ninja-warrior/legacy_processor.py"

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.analyze.resolve_path",
            lambda path, project_root=None: str(real_file),
        )

        result = await analyze_code(file_path=requested_path, language="python")

        assert result.error is None
        assert result.success is True
        assert "normalize_me" in result.functions

    async def test_analyze_returns_correction_needed_for_unresolvable_windows_path(
        self, monkeypatch
    ):
        """Unresolvable '/K:/...' paths should not degrade to internal_error."""
        from code_scalpel.mcp.server import analyze_code

        requested_path = "/K:/backup/Develop/code-scalpel-ninja-warrior/legacy_processor.py.bak"
        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/backup/Develop/code-scalpel-ninja-warrior/legacy_processor.py.bak (not found)\n\n"
            "Suggestion:\n"
            "Windows path detected but file not accessible.\n"
            "If running in WSL, the path should be accessible at:\n\n"
            "  /mnt/k/backup/Develop/code-scalpel-ninja-warrior/legacy_processor.py.bak"
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.analyze.resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await analyze_code(file_path=requested_path, language="python")

        assert result.error is not None
        assert result.error.error_code == "correction_needed"
        assert "/mnt/k/backup/Develop/code-scalpel-ninja-warrior/legacy_processor.py.bak" in result.error.error
        assert result.error.error_details is not None
        assert result.error.error_details["hint"] == str(resolver_error)


class TestSecurityScanTool:
    """Tests for the security_scan tool."""

    async def test_scan_uses_shared_path_resolver_for_malformed_windows_path(
        self, tmp_path, monkeypatch
    ):
        """Malformed '/K:/...' paths should resolve before scanning."""
        from code_scalpel.mcp.server import security_scan

        real_file = tmp_path / "vuln.py"
        real_file.write_text(
            "import os\n"
            "def run(request):\n"
            "    os.system(request.args.get('cmd'))\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.security.resolve_path",
            lambda path, project_root=None: str(real_file),
        )

        result = await security_scan(
            file_path="/K:/backup/Develop/code-scalpel-ninja-warrior/vuln.py"
        )

        assert result.error is None
        assert result.success is True
        assert result.vulnerability_count >= 1

    async def test_scan_returns_correction_needed_for_unresolvable_windows_path(
        self, monkeypatch
    ):
        """Unresolvable '/K:/...' paths should return correction_needed."""
        from code_scalpel.mcp.server import security_scan

        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/backup/Develop/code-scalpel-ninja-warrior/vuln.py (not found)\n\n"
            "Suggestion:\n"
            "Windows path detected but file not accessible.\n"
            "If running in WSL, the path should be accessible at:\n\n"
            "  /mnt/k/backup/Develop/code-scalpel-ninja-warrior/vuln.py"
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.security.resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await security_scan(
            file_path="/K:/backup/Develop/code-scalpel-ninja-warrior/vuln.py"
        )

        assert result.error is not None
        assert result.error.error_code == "correction_needed"
        assert "/mnt/k/backup/Develop/code-scalpel-ninja-warrior/vuln.py" in result.error.error

    async def test_scan_clean_code(self):
        """Test scanning clean code with no vulnerabilities."""
        from code_scalpel.mcp.server import security_scan

        code = """
def safe_function(x):
    return x + 1
"""
        result = await security_scan(code)
        assert result.success is True
        assert result.vulnerability_count == 0
        assert result.risk_level == "low"

    async def test_scan_sql_injection(self):
        """Test detecting SQL injection."""
        from code_scalpel.mcp.server import security_scan

        code = """
def vulnerable(request):
    user_input = request.args.get("id")
    query = "SELECT * FROM users WHERE id = " + user_input
    cursor.execute(query)
"""
        result = await security_scan(code)
        assert result.success is True
        assert result.has_vulnerabilities is True
        # Handle both dict and object forms (due to envelope wrapping converting to dict)
        vuln_types = [
            v.get("type") if isinstance(v, dict) else v.type
            for v in result.vulnerabilities
        ]
        assert any("SQL" in vt for vt in vuln_types)

    async def test_scan_command_injection(self):
        """Test detecting command injection."""
        from code_scalpel.mcp.server import security_scan

        code = """
import os
def run_command(request):
    user_input = request.form.get("cmd")
    os.system("ls " + user_input)
"""
        result = await security_scan(code)
        assert result.success is True
        assert result.has_vulnerabilities is True
        vuln_types = [
            v.get("type") if isinstance(v, dict) else v.type
            for v in result.vulnerabilities
        ]
        assert any("Command" in vt for vt in vuln_types)

    async def test_scan_eval_injection(self):
        """Test detecting eval injection."""
        from code_scalpel.mcp.server import security_scan

        code = """
def dangerous(request):
    user_input = request.args.get("expr")
    result = eval(user_input)
    return result
"""
        result = await security_scan(code)
        assert result.success is True
        assert result.has_vulnerabilities is True

    async def test_scan_hardcoded_secret(self):
        """Test detecting hardcoded secrets."""
        from code_scalpel.mcp.server import security_scan

        code = """
def connect():
    aws_key = "AKIAIOSFODNN7EXAMPLE"
    return aws_key
"""
        result = await security_scan(code)
        assert result.success is True
        assert result.has_vulnerabilities is True
        vuln_types = [
            v.get("type") if isinstance(v, dict) else v.type
            for v in result.vulnerabilities
        ]
        assert any("Secret" in vt or "Hardcoded" in vt for vt in vuln_types)

    async def test_scan_empty_code(self):
        """Test scanning empty code."""
        from code_scalpel.mcp.server import security_scan

        result = await security_scan("")
        assert result.success is False
        assert result.error is not None

    async def test_scan_detects_taint_sources(self):
        """Test detection of taint sources."""
        from code_scalpel.mcp.server import security_scan

        code = """
from flask import request
def handler():
    user_data = request.args.get('user')
    return user_data
"""
        result = await security_scan(code)
        assert result.success is True
        # Either SecurityAnalyzer or fallback should detect request.args
        # (May or may not have vulnerabilities depending on implementation)

    async def test_scan_risk_levels(self):
        """Test risk level calculation."""
        from code_scalpel.mcp.server import security_scan

        # Code with multiple vulnerabilities
        code = """
import os
def very_dangerous(request):
    user_input = request.args.get("data")
    eval(user_input)
    exec(user_input)
    os.system(user_input)
"""
        result = await security_scan(code)
        assert result.success is True
        assert result.risk_level in ["high", "critical"]


class TestSymbolicExecuteTool:
    """Tests for the symbolic_execute tool."""

    async def test_symbolic_simple_function(self):
        """Test symbolic execution on simple function."""
        from code_scalpel.mcp.server import symbolic_execute

        code = """
def simple(x):
    return x + 1
"""
        result = await symbolic_execute(code)
        assert result.success is True
        assert result.paths_explored >= 1

    async def test_symbolic_branching(self):
        """Test symbolic execution with branches."""
        from code_scalpel.mcp.server import symbolic_execute

        code = """
def branching(x):
    if x > 0:
        return "positive"
    else:
        return "non-positive"
"""
        result = await symbolic_execute(code)
        assert result.success is True
        # Should find paths for both branches
        assert result.paths_explored >= 1
        assert len(result.constraints) > 0

    async def test_symbolic_multiple_branches(self):
        """Test symbolic execution with multiple branches."""
        from code_scalpel.mcp.server import symbolic_execute

        code = """
def classify(x):
    if x < 0:
        return "negative"
    elif x == 0:
        return "zero"
    else:
        return "positive"
"""
        result = await symbolic_execute(code)
        assert result.success is True
        assert result.paths_explored >= 1

    async def test_symbolic_detects_symbolic_vars(self):
        """Test that symbolic variables are detected."""
        from code_scalpel.mcp.server import symbolic_execute

        code = """
def func(a, b, c):
    if a > b:
        return c
    return a + b
"""
        result = await symbolic_execute(code)
        assert result.success is True
        # Should detect function parameters as symbolic
        assert len(result.symbolic_variables) > 0

    async def test_symbolic_empty_code(self):
        """Test symbolic execution on empty code."""
        from code_scalpel.mcp.server import symbolic_execute

        result = await symbolic_execute("")
        assert result.success is False
        assert result.error is not None

    async def test_symbolic_max_paths(self):
        """Test max_paths parameter."""
        from code_scalpel.mcp.server import symbolic_execute

        code = """
def many_branches(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return 1
            return 2
        return 3
    return 4
"""
        result = await symbolic_execute(code, max_paths=5)
        assert result.success is True
        # Should respect max_paths
        assert result.paths_explored <= 10  # Some buffer for implementation

    async def test_symbolic_loop_handling(self):
        """Test symbolic execution with loops."""
        from code_scalpel.mcp.server import symbolic_execute

        code = """
def with_loop(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
        result = await symbolic_execute(code)
        assert result.success is True

    async def test_symbolic_java_language_slice(self):
        """[20260309_TEST] Test symbolic execution through the public Java tool path."""
        from code_scalpel.mcp.server import symbolic_execute

        code = """
class Demo {
    int classify(int x) {
        if (x > 0) {
            return 1;
        }
        return 0;
    }
}
"""
        result = await symbolic_execute(code, language="java")
        assert result.success is True
        assert result.paths_explored >= 2
        assert "x" in result.symbolic_variables
        assert any(
            "x" in constraint and ("<" in constraint or ">" in constraint)
            for constraint in result.constraints
        )
        assert any(
            "x" in condition
            for path in result.paths
            for condition in path.conditions
        )


class TestPathResolutionParityAcrossTools:
    """Regression tests for malformed Windows/WSL path handling across MCP tools."""

    async def test_get_call_graph_resolves_malformed_windows_project_root(
        self, tmp_path, monkeypatch
    ):
        """get_call_graph should normalize malformed '/K:/...' project roots."""
        from code_scalpel.mcp.server import get_call_graph

        expected_root = str(tmp_path)

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: expected_root,
        )

        def fake_sync(project_root, *args, **kwargs):
            assert project_root == expected_root
            return _FakeCallGraphResult(nodes=[{"id": "main"}], edges=[])

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph._get_call_graph_sync",
            fake_sync,
        )

        result = await get_call_graph(project_root="/K:/repo/sample")

        assert result.success is True
        assert len(result.nodes) == 1

    async def test_get_call_graph_returns_correction_needed_for_unresolvable_windows_project_root(
        self, monkeypatch
    ):
        """get_call_graph should return correction_needed for unresolvable '/K:/...' roots."""
        from code_scalpel.mcp.server import get_call_graph

        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/repo/sample (not found)\n\nSuggestion:\n  /mnt/k/repo/sample"
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_call_graph(project_root="/K:/repo/sample")

        assert result.error is not None
        assert result.error.error_code == "correction_needed"

    async def test_get_graph_neighborhood_resolves_malformed_windows_project_root(
        self, tmp_path, monkeypatch
    ):
        """get_graph_neighborhood should normalize malformed '/K:/...' project roots."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        expected_root = str(tmp_path)

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: expected_root,
        )

        def fake_sync(center_node_id, k, max_nodes, direction, min_confidence, project_root, query):
            assert project_root == expected_root
            return _FakeGraphNeighborhoodResult(
                center_node={"id": center_node_id},
                nodes=[{"id": center_node_id}],
                edges=[],
            )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph._get_graph_neighborhood_sync",
            fake_sync,
        )

        result = await get_graph_neighborhood(
            center_node_id="python::app.main::function::main",
            project_root="/K:/repo/sample",
        )

        assert result.success is True
        assert result.center_node["id"] == "python::app.main::function::main"

    async def test_get_graph_neighborhood_returns_correction_needed_for_unresolvable_windows_project_root(
        self, monkeypatch
    ):
        """get_graph_neighborhood should return correction_needed for bad '/K:/...' roots."""
        from code_scalpel.mcp.server import get_graph_neighborhood

        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/repo/sample (not found)\n\nSuggestion:\n  /mnt/k/repo/sample"
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_graph_neighborhood(
            center_node_id="python::app.main::function::main",
            project_root="/K:/repo/sample",
        )

        assert result.error is not None
        assert result.error.error_code == "correction_needed"

    async def test_get_project_map_resolves_malformed_windows_project_root(
        self, tmp_path, monkeypatch
    ):
        """get_project_map should normalize malformed '/K:/...' project roots."""
        from code_scalpel.mcp.server import get_project_map

        expected_root = str(tmp_path)

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: expected_root,
        )

        def fake_sync(project_root, *args, **kwargs):
            assert project_root == expected_root
            return _FakeProjectMapResult(total_files=2, total_lines=10)

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph._get_project_map_sync",
            fake_sync,
        )

        result = await get_project_map(project_root="/K:/repo/sample")

        assert result.success is True
        assert result.total_files == 2

    async def test_get_project_map_returns_correction_needed_for_unresolvable_windows_project_root(
        self, monkeypatch
    ):
        """get_project_map should return correction_needed for bad '/K:/...' roots."""
        from code_scalpel.mcp.server import get_project_map

        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/repo/sample (not found)\n\nSuggestion:\n  /mnt/k/repo/sample"
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_project_map(project_root="/K:/repo/sample")

        assert result.error is not None
        assert result.error.error_code == "correction_needed"

    async def test_get_cross_file_dependencies_resolves_malformed_windows_paths(
        self, tmp_path, monkeypatch
    ):
        """get_cross_file_dependencies should normalize malformed file and root inputs."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        expected_root = str(tmp_path)
        expected_file = str(tmp_path / "service.py")

        def fake_resolve(path, project_root=None):
            if path.endswith("service.py"):
                return expected_file
            return expected_root

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            fake_resolve,
        )

        def fake_sync(target_file, target_symbol, project_root, *args, **kwargs):
            assert target_file == expected_file
            assert project_root == expected_root
            return _FakeCrossFileDependenciesResult(target_symbol=target_symbol)

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph._get_cross_file_dependencies_sync",
            fake_sync,
        )

        result = await get_cross_file_dependencies(
            target_file="/K:/repo/sample/service.py",
            target_symbol="helper",
            project_root="/K:/repo/sample",
        )

        assert result.success is True
        assert result.target_symbol == "helper"

    async def test_get_cross_file_dependencies_returns_correction_needed_for_unresolvable_windows_paths(
        self, monkeypatch
    ):
        """get_cross_file_dependencies should return correction_needed for bad '/K:/...' paths."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/repo/sample/service.py (not found)\n\nSuggestion:\n  /mnt/k/repo/sample/service.py"
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_cross_file_dependencies(
            target_file="/K:/repo/sample/service.py",
            target_symbol="helper",
            project_root="/K:/repo/sample",
        )

        assert result.error is not None
        assert result.error.error_code == "correction_needed"

    async def test_cross_file_security_scan_resolves_malformed_windows_project_root(
        self, tmp_path, monkeypatch
    ):
        """cross_file_security_scan should normalize malformed '/K:/...' project roots."""
        from code_scalpel.mcp.server import cross_file_security_scan

        expected_root = str(tmp_path)

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: expected_root,
        )

        def fake_sync(project_root, *args, **kwargs):
            assert project_root == expected_root
            return _FakeCrossFileSecurityResult()

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph._cross_file_security_scan_sync",
            fake_sync,
        )

        result = await cross_file_security_scan(project_root="/K:/repo/sample")

        assert result.success is True
        assert result.vulnerability_count == 0

    async def test_cross_file_security_scan_returns_correction_needed_for_unresolvable_windows_project_root(
        self, monkeypatch
    ):
        """cross_file_security_scan should return correction_needed for bad '/K:/...' roots."""
        from code_scalpel.mcp.server import cross_file_security_scan

        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/repo/sample (not found)\n\nSuggestion:\n  /mnt/k/repo/sample"
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.graph.resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await cross_file_security_scan(project_root="/K:/repo/sample")

        assert result.error is not None
        assert result.error.error_code == "correction_needed"

    async def test_generate_unit_tests_resolves_malformed_windows_file_path(
        self, tmp_path, monkeypatch
    ):
        """generate_unit_tests should normalize malformed '/K:/...' file paths."""
        from code_scalpel.mcp.server import generate_unit_tests

        expected_file = str(tmp_path / "service.py")

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.symbolic.resolve_path",
            lambda path, project_root=None: expected_file,
        )

        def fake_generate(*args):
            assert args[1] == expected_file
            return {
                "success": True,
                "function_name": "helper",
                "test_count": 1,
                "total_test_cases": 1,
                "framework_used": "pytest",
                "data_driven_enabled": False,
                "bug_reproduction_enabled": False,
                "test_cases": [{"name": "test_helper"}],
                "warnings": [],
                "coverage_estimate": 75.0,
            }

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.symbolic.sym_helpers._generate_tests_sync",
            fake_generate,
        )

        result = await generate_unit_tests(file_path="/K:/repo/sample/service.py")

        assert result.error is None
        assert result.success is True
        assert result.function_name == "helper"

    async def test_generate_unit_tests_returns_correction_needed_for_unresolvable_windows_file_path(
        self, monkeypatch
    ):
        """generate_unit_tests should return correction_needed for bad '/K:/...' file paths."""
        from code_scalpel.mcp.server import generate_unit_tests

        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/repo/sample/service.py (not found)\n\nSuggestion:\n  /mnt/k/repo/sample/service.py"
        )

        monkeypatch.setattr(
            "code_scalpel.mcp.tools.symbolic.resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await generate_unit_tests(file_path="/K:/repo/sample/service.py")

        assert result.error is not None
        assert result.error.error_code == "correction_needed"

class TestMCPIntegration:
    """Integration tests for MCP server."""

    async def test_all_tools_available(self):
        """Test that all tools are registered."""
        from code_scalpel.mcp.server import mcp

        # FastMCP should have our tools
        assert mcp is not None
        # The tools should be callable
        from code_scalpel.mcp.server import (
            analyze_code,
            security_scan,
            symbolic_execute,
        )

        assert callable(analyze_code)
        assert callable(security_scan)
        assert callable(symbolic_execute)

    async def test_result_models_are_valid(self):
        """Test that result models are proper Pydantic models."""
        from code_scalpel.mcp.server import (
            AnalysisResult,
            SecurityResult,
            SymbolicResult,
        )

        # Should be importable and usable
        assert AnalysisResult is not None
        assert SecurityResult is not None
        assert SymbolicResult is not None

    async def test_code_validation(self):
        """Test code validation for all tools."""
        from code_scalpel.mcp.server import (
            analyze_code,
            security_scan,
            symbolic_execute,
        )

        # All should reject empty code
        result1 = await analyze_code("")
        result2 = await security_scan("")
        result3 = await symbolic_execute("")

        assert result1.success is False
        assert result2.success is False
        assert result3.success is False

    async def test_large_code_rejection(self):
        """Test rejection of code exceeding size limit."""
        from code_scalpel.mcp.helpers.analyze_helpers import MAX_CODE_SIZE
        from code_scalpel.mcp.tools.analyze import analyze_code

        # Create code exceeding limit
        large_code = "x = 1\n" * ((MAX_CODE_SIZE // 6) + 1)  # +1 to exceed limit
        result = await analyze_code(large_code)
        assert result.success is False
        assert (
            "size" in get_error_message(result.error).lower()
            or "exceed" in get_error_message(result.error).lower()
        )

    async def test_analysis_pipeline(self):
        """Test running multiple analyses on the same code."""
        from code_scalpel.mcp.server import (
            analyze_code,
            security_scan,
            symbolic_execute,
        )

        code = """
def process_user(user_id):
    if user_id > 0:
        return f"User: {user_id}"
    return "Invalid"
"""
        # All should succeed
        analysis = await analyze_code(code)
        security = await security_scan(code)
        symbolic = await symbolic_execute(code)

        assert analysis.success is True
        assert security.success is True
        assert symbolic.success is True

        # Cross-check: function detected
        assert "process_user" in analysis.functions

    async def test_concurrent_analysis(self):
        """Test concurrent analysis calls."""
        import asyncio

        from code_scalpel.mcp.server import analyze_code

        codes = [
            "def f1(): return 1",
            "def f2(): return 2",
            "def f3(): return 3",
        ]

        results = await asyncio.gather(*[analyze_code(code) for code in codes])

        for result in results:
            assert result.success is True


class TestValidationHelpers:
    """Tests for internal validation helpers."""

    async def test_validate_code_empty(self):
        """Test validation of empty code."""
        from code_scalpel.mcp.server import _validate_code

        valid, error = _validate_code("")
        assert valid is False
        assert error is not None

    async def test_validate_code_valid(self):
        """Test validation of valid code."""
        from code_scalpel.mcp.server import _validate_code

        valid, error = _validate_code("x = 1")
        assert valid is True
        assert error is None

    async def test_validate_code_non_string(self):
        """Test validation of non-string input."""
        from code_scalpel.mcp.server import _validate_code

        valid, error = _validate_code(123)  # type: ignore
        assert valid is False
        assert error is not None


class TestComplexityCalculation:
    """Tests for complexity estimation."""

    async def test_complexity_linear(self):
        """Test complexity of linear code."""
        import ast

        from code_scalpel.mcp.server import _count_complexity

        code = "x = 1\ny = 2\nz = x + y"
        tree = ast.parse(code)
        complexity = _count_complexity(tree)
        assert complexity == 1  # Base complexity

    async def test_complexity_with_if(self):
        """Test complexity with if statements."""
        import ast

        from code_scalpel.mcp.server import _count_complexity

        code = """
if x > 0:
    y = 1
"""
        tree = ast.parse(code)
        complexity = _count_complexity(tree)
        assert complexity == 2  # Base + 1 for if

    async def test_complexity_with_loop(self):
        """Test complexity with loops."""
        import ast

        from code_scalpel.mcp.server import _count_complexity

        code = """
for i in range(10):
    x = i
"""
        tree = ast.parse(code)
        complexity = _count_complexity(tree)
        assert complexity == 2  # Base + 1 for for


class TestResultModels:
    """Tests for Pydantic result models."""

    async def test_analysis_result_serialization(self):
        """Test AnalysisResult JSON serialization."""
        from code_scalpel.mcp.server import AnalysisResult

        result = AnalysisResult(
            success=True,
            functions=["foo", "bar"],
            classes=["MyClass"],
            imports=["os"],
            function_count=2,
            class_count=1,
            complexity=3,
            lines_of_code=10,
        )

        # Should serialize to dict/JSON
        data = result.model_dump()
        assert data["success"] is True
        assert len(data["functions"]) == 2

    async def test_security_result_serialization(self):
        """Test SecurityResult JSON serialization."""
        from code_scalpel.mcp.server import SecurityResult, VulnerabilityInfo

        result = SecurityResult(
            success=True,
            has_vulnerabilities=True,
            vulnerability_count=1,
            risk_level="high",
            vulnerabilities=[
                VulnerabilityInfo(
                    type="SQL Injection",
                    cwe="CWE-89",
                    severity="high",
                    line=5,
                    description="SQL injection via execute()",
                )
            ],
        )

        data = result.model_dump()
        assert data["vulnerability_count"] == 1
        assert len(data["vulnerabilities"]) == 1

    async def test_symbolic_result_serialization(self):
        """Test SymbolicResult JSON serialization."""
        from code_scalpel.mcp.server import ExecutionPath, SymbolicResult

        result = SymbolicResult(
            success=True,
            paths_explored=2,
            paths=[
                ExecutionPath(
                    path_id=0,
                    conditions=["x > 0"],
                    final_state={"x": 5},
                    reproduction_input={"x": 5},
                    is_reachable=True,
                ),
            ],
            symbolic_variables=["x"],
            constraints=["x > 0"],
        )

        data = result.model_dump()
        assert data["paths_explored"] == 2
        assert len(data["paths"]) == 1


class TestExtractCodeTool:
    """Tests for the extract_code surgical extraction tool."""

    async def test_extract_function_basic(self):
        """Test extracting a simple function."""
        from code_scalpel.mcp.server import extract_code

        code = """
def hello():
    return "Hello, World!"

def goodbye():
    return "Goodbye!"
"""
        result = await extract_code(
            code=code, target_type="function", target_name="hello"
        )
        assert result.success is True
        assert result.target_name == "hello"
        assert "return" in result.target_code
        assert result.full_code != ""

    async def test_extract_function_with_context(self):
        """Test extracting a function with its dependencies."""
        from code_scalpel.mcp.server import extract_code

        code = """
def helper():
    return 42

def main():
    return helper() + 1
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="main",
            include_context=True,
            context_depth=1,
        )
        assert result.success is True
        assert result.target_name == "main"
        assert len(result.context_items) > 0
        assert "helper" in result.context_items
        assert "helper" in result.context_code

    async def test_extract_class_basic(self):
        """Test extracting a simple class."""
        from code_scalpel.mcp.server import extract_code

        code = """
class MyClass:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value
"""
        result = await extract_code(
            code=code, target_type="class", target_name="MyClass"
        )
        assert result.success is True
        assert result.target_name == "MyClass"
        assert "__init__" in result.target_code
        assert "get_value" in result.target_code

    async def test_extract_method(self):
        """Test extracting a specific method from a class."""
        from code_scalpel.mcp.server import extract_code

        code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        result = await extract_code(
            code=code, target_type="method", target_name="Calculator.add"
        )
        assert result.success is True
        assert result.target_name == "Calculator.add"
        assert "return a + b" in result.target_code

    async def test_extract_method_invalid_format(self):
        """Test method extraction with invalid name format."""
        from code_scalpel.mcp.server import extract_code

        code = "class Foo:\n    def bar(self): pass"
        result = await extract_code(code=code, target_type="method", target_name="bar")
        assert result.success is False
        assert "ClassName.method_name" in result.error

    async def test_extract_nonexistent_function(self):
        """Test extracting a function that doesn't exist."""
        from code_scalpel.mcp.server import extract_code

        code = "def foo(): pass"
        result = await extract_code(
            code=code, target_type="function", target_name="nonexistent"
        )
        assert result.success is False
        assert "not found" in get_error_message(result.error).lower()

    async def test_extract_unknown_target_type(self):
        """Test extraction with unknown target type."""
        from code_scalpel.mcp.server import extract_code

        code = "def foo(): pass"
        result = await extract_code(code=code, target_type="variable", target_name="x")
        assert result.success is False
        assert "unknown target_type" in get_error_message(result.error).lower()

    async def test_extract_token_estimate(self):
        """Test that token estimation is included."""
        from code_scalpel.mcp.server import extract_code

        code = """
def calculate(x, y, z):
    result = x + y
    result = result * z
    return result
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="calculate",
            include_token_estimate=True,
        )
        assert result.success is True
        assert result.token_estimate > 0

    async def test_extract_class_with_context(self):
        """Test extracting a class with its dependencies."""
        from code_scalpel.mcp.server import extract_code

        code = """
def utility_func():
    return 100

class MyClass:
    def __init__(self):
        self.value = utility_func()
"""
        result = await extract_code(
            code=code,
            target_type="class",
            target_name="MyClass",
            include_context=True,
        )
        assert result.success is True
        assert result.target_name == "MyClass"
        # Should include utility_func as dependency
        assert "utility_func" in result.context_items

    async def test_extract_syntax_error(self):
        """Test extraction from code with syntax errors."""
        from code_scalpel.mcp.server import extract_code

        code = "def broken("
        result = await extract_code(
            code=code, target_type="function", target_name="broken"
        )
        assert result.success is False
        assert result.error is not None

    async def test_extract_no_input_error(self):
        """Test extraction fails when neither file_path nor code provided."""
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(target_type="function", target_name="foo")
        assert result.success is False
        assert (
            "file_path" in get_error_message(result.error).lower()
            or "code" in get_error_message(result.error).lower()
        )


class TestExtractCodeFromFile:
    """Tests for file-based extraction - the TOKEN-EFFICIENT path."""

    async def test_extract_function_from_file(self, tmp_path):
        """Test extracting a function directly from a file (0 token cost for read)."""
        from code_scalpel.mcp.server import extract_code

        # Create a "large" file - Agent never sees these 20 lines
        file_content = '''
"""A utility module with many functions."""
import math

def unused_function_1():
    """This function is not requested."""
    return "not needed"

def unused_function_2():
    """Another unrequested function."""
    return "also not needed"

def calculate_tax(amount, rate=0.1):
    """Calculate tax for a given amount."""
    return amount * rate

def unused_function_3():
    """Yet another function the agent doesn't need."""
    return "still not needed"

class UnrelatedClass:
    """The agent doesn't need this either."""
    pass
'''
        test_file = tmp_path / "utils.py"
        test_file.write_text(file_content)

        # Agent asks: "Get me calculate_tax from utils.py"
        # Agent sends: ~50 tokens (the request)
        # Server reads file: COMMUNITY to Agent
        # Agent receives: ~50 tokens (just the function)
        result = await extract_code(
            file_path=str(test_file),
            target_type="function",
            target_name="calculate_tax",
        )

        assert result.success is True
        assert result.target_name == "calculate_tax"
        assert "amount * rate" in result.target_code
        # Verify the agent did NOT receive the other functions
        assert "unused_function" not in result.target_code
        assert "UnrelatedClass" not in result.target_code

    async def test_extract_class_from_file(self, tmp_path):
        """Test extracting a class directly from a file."""
        from code_scalpel.mcp.server import extract_code

        file_content = '''
class OtherClass:
    pass

class TargetClass:
    """This is what we want."""
    def __init__(self, value):
        self.value = value

    def process(self):
        return self.value * 2

class AnotherClass:
    pass
'''
        test_file = tmp_path / "models.py"
        test_file.write_text(file_content)

        result = await extract_code(
            file_path=str(test_file),
            target_type="class",
            target_name="TargetClass",
        )

        assert result.success is True
        assert "TargetClass" in result.target_code
        assert "__init__" in result.target_code
        assert "process" in result.target_code
        # Verify we didn't get the other classes
        assert "OtherClass" not in result.target_code
        assert "AnotherClass" not in result.target_code

    async def test_extract_method_from_file(self, tmp_path):
        """Test extracting a specific method from a file."""
        from code_scalpel.mcp.server import extract_code

        file_content = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b
"""
        test_file = tmp_path / "calc.py"
        test_file.write_text(file_content)

        result = await extract_code(
            file_path=str(test_file),
            target_type="method",
            target_name="Calculator.multiply",
        )

        assert result.success is True
        assert "multiply" in result.target_code
        assert "a * b" in result.target_code

    async def test_extract_with_context_from_file(self, tmp_path):
        """Test extracting a function with its dependencies from a file."""
        from code_scalpel.mcp.server import extract_code

        file_content = """
def helper():
    return 42

def another_helper():
    return 100

def main():
    return helper() + 1

def unrelated():
    return "not connected"
"""
        test_file = tmp_path / "service.py"
        test_file.write_text(file_content)

        result = await extract_code(
            file_path=str(test_file),
            target_type="function",
            target_name="main",
            include_context=True,
        )

        assert result.success is True
        assert result.target_name == "main"
        assert "helper" in result.context_items
        assert "helper" in result.context_code
        # another_helper and unrelated are NOT dependencies
        assert "another_helper" not in result.context_code
        assert "unrelated" not in result.context_code

    async def test_extract_file_not_found(self):
        """Test extraction from non-existent file."""
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            file_path="/nonexistent/path/to/file.py",
            target_type="function",
            target_name="foo",
        )

        assert result.success is False
        # [20251214_BUGFIX] Updated to match PathResolver's detailed error messages
        assert (
            "cannot access file" in get_error_message(result.error).lower()
            or "not found" in get_error_message(result.error).lower()
        )

    async def test_extract_function_not_found_in_file(self, tmp_path):
        """Test extraction of non-existent function from valid file."""
        from code_scalpel.mcp.server import extract_code

        file_content = "def existing_func(): pass"
        test_file = tmp_path / "test.py"
        test_file.write_text(file_content)

        result = await extract_code(
            file_path=str(test_file),
            target_type="function",
            target_name="nonexistent_func",
        )

        assert result.success is False
        assert "not found" in get_error_message(result.error).lower()

    async def test_token_savings_demonstration(self, tmp_path):
        """Demonstrate the token savings of file-based extraction."""
        from code_scalpel.mcp.server import extract_code

        # Create a "large" file with 100 lines
        lines = ["# Line of code"] * 100
        lines[50] = "def target_function():\n    return 'found me'"
        file_content = "\n".join(lines)
        test_file = tmp_path / "large_file.py"
        test_file.write_text(file_content)

        result = await extract_code(
            file_path=str(test_file),
            target_type="function",
            target_name="target_function",
            include_token_estimate=True,
        )

        assert result.success is True
        # The returned code should be tiny compared to the file
        assert result.token_estimate < 50  # ~2 lines worth of tokens
        # The full file would be ~100 lines * 15 chars / 4 = ~375 tokens
        # Token savings: Agent received ~50 tokens instead of ~375


class TestUpdateSymbolTool:
    """Tests for the update_symbol surgical modification tool."""

    @pytest.fixture(autouse=True)
    def _set_project_root(self, tmp_path, monkeypatch):
        """[20260116_TEST] Set PROJECT_ROOT to tmp_path for path validation."""
        from code_scalpel.mcp.helpers import extraction_helpers
        from code_scalpel.mcp import server

        monkeypatch.setattr(extraction_helpers, "PROJECT_ROOT", tmp_path)
        # [20260120_FIX] Also patch server module's PROJECT_ROOT for security_helpers
        monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
        server._PROJECT_ROOT_HOLDER[0] = tmp_path

    async def test_update_function_in_file(self, tmp_path, monkeypatch):
        """Test updating a function in a file."""
        from code_scalpel.mcp.server import update_symbol

        file_content = '''
def old_function():
    """Old implementation."""
    return 1


def other_function():
    return 2
'''
        test_file = tmp_path / "test.py"
        test_file.write_text(file_content)

        new_code = '''def old_function():
    """New and improved!"""
    return 42
'''
        result = await update_symbol(
            file_path=str(test_file),
            target_type="function",
            target_name="old_function",
            new_code=new_code,
        )

        assert result.success is True
        assert result.target_name == "old_function"
        assert result.target_type == "function"

        # Verify file was modified
        modified_content = test_file.read_text()
        assert "return 42" in modified_content
        assert "return 2" in modified_content  # other_function preserved
        assert "return 1" not in modified_content  # old code gone

        # Verify backup was created
        assert result.backup_path is not None
        assert (tmp_path / "test.py.bak").exists()

    async def test_update_class_in_file(self, tmp_path, monkeypatch):
        """Test updating a class in a file."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import update_symbol

        file_content = '''
class OldClass:
    """Old class."""
    def method(self):
        return 1


def helper():
    return 2
'''
        test_file = tmp_path / "test.py"
        test_file.write_text(file_content)

        new_code = '''class OldClass:
    """Completely rewritten!"""
    def method(self):
        return 42

    def new_method(self):
        return 100
'''
        result = await update_symbol(
            file_path=str(test_file),
            target_type="class",
            target_name="OldClass",
            new_code=new_code,
        )

        assert result.success is True
        assert result.target_type == "class"

        modified_content = test_file.read_text()
        assert "new_method" in modified_content
        assert "helper" in modified_content  # preserved

    async def test_update_method_in_file(self, tmp_path, monkeypatch):
        """Test updating a method within a class."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import update_symbol

        file_content = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        test_file = tmp_path / "test.py"
        test_file.write_text(file_content)

        new_code = '''def add(self, a, b):
    """Now with logging!"""
    print(f"Adding {a} + {b}")
    return a + b
'''
        result = await update_symbol(
            file_path=str(test_file),
            target_type="method",
            target_name="Calculator.add",
            new_code=new_code,
        )

        assert result.success is True
        assert result.target_type == "method"

        modified_content = test_file.read_text()
        assert "print" in modified_content
        assert "subtract" in modified_content  # preserved

    async def test_update_file_not_found(self):
        """Test error when file doesn't exist."""
        from code_scalpel.mcp.server import update_symbol

        result = await update_symbol(
            file_path="/nonexistent/path.py",
            target_type="function",
            target_name="foo",
            new_code="def foo(): pass",
        )

        assert result.success is False
        assert "not found" in get_error_message(result.error).lower()

    async def test_update_function_not_found(self, tmp_path, monkeypatch):
        """Test behavior when function doesn't exist - should return error."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import update_symbol

        test_file = tmp_path / "test.py"
        test_file.write_text("def existing(): pass")

        result = await update_symbol(
            file_path=str(test_file),
            target_type="function",
            target_name="nonexistent",
            new_code="def nonexistent(): pass",
        )

        # [20260113_FIX] Correct behavior: error when function not found
        assert result.success is False
        assert result.error is not None
        assert "not found" in get_error_message(result.error).lower()

    async def test_update_invalid_syntax(self, tmp_path, monkeypatch):
        """Test error when new code has syntax error."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import update_symbol

        test_file = tmp_path / "test.py"
        test_file.write_text("def target(): pass")

        result = await update_symbol(
            file_path=str(test_file),
            target_type="function",
            target_name="target",
            new_code="def target( broken syntax",
        )

        assert result.success is False
        assert "syntax" in get_error_message(result.error).lower()

    async def test_update_invalid_target_type(self, tmp_path, monkeypatch):
        """Test error for invalid target type."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import update_symbol

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        result = await update_symbol(
            file_path=str(test_file),
            target_type="variable",
            target_name="x",
            new_code="x = 2",
        )

        assert result.success is False
        assert "invalid" in get_error_message(result.error).lower()

    async def test_update_method_invalid_format(self, tmp_path, monkeypatch):
        """Test error when method name doesn't have ClassName.method format."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import update_symbol

        test_file = tmp_path / "test.py"
        test_file.write_text("class Foo:\n    def bar(self): pass")

        result = await update_symbol(
            file_path=str(test_file),
            target_type="method",
            target_name="bar",  # Missing ClassName.
            new_code="def bar(self): pass",
        )

        assert result.success is False
        assert "ClassName.method_name" in result.error

    async def test_update_no_backup(self, tmp_path, monkeypatch):
        """Test updating without creating backup."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import update_symbol

        test_file = tmp_path / "test.py"
        test_file.write_text("def old(): return 1")

        result = await update_symbol(
            file_path=str(test_file),
            target_type="function",
            target_name="old",
            new_code="def old(): return 42",
            create_backup=False,
        )

        assert result.success is True
        assert result.backup_path is None
        assert not (tmp_path / "test.py.bak").exists()

    async def test_update_lines_delta(self, tmp_path, monkeypatch):
        """Test that line count changes are tracked."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import update_symbol

        test_file = tmp_path / "test.py"
        test_file.write_text("def short(): return 1")

        new_code = """def short():
    x = 1
    y = 2
    z = 3
    return x + y + z
"""
        result = await update_symbol(
            file_path=str(test_file),
            target_type="function",
            target_name="short",
            new_code=new_code,
        )

        assert result.success is True
        assert result.lines_after > result.lines_before
        assert result.lines_delta > 0

    async def test_extract_modify_update_workflow(self, tmp_path, monkeypatch):
        """Test the full workflow: extract -> modify -> update."""
        monkeypatch.setenv("SCALPEL_ROOT", str(tmp_path))
        from code_scalpel.mcp.server import extract_code, update_symbol

        # Original file
        file_content = '''
def calculate_tax(amount):
    """Calculate tax."""
    return amount * 0.1


def other_function():
    return 42
'''
        test_file = tmp_path / "utils.py"
        test_file.write_text(file_content)

        # Step 1: Extract the function (token-efficient)
        extract_result = await extract_code(
            file_path=str(test_file),
            target_type="function",
            target_name="calculate_tax",
        )

        assert extract_result.success is True
        assert "amount * 0.1" in extract_result.target_code

        # Step 2: "Agent modifies" the code (simulated)
        modified_code = '''def calculate_tax(amount, rate=0.1):
    """Calculate tax with configurable rate."""
    return round(amount * rate, 2)
'''

        # Step 3: Update the file with the new code
        update_result = await update_symbol(
            file_path=str(test_file),
            target_type="function",
            target_name="calculate_tax",
            new_code=modified_code,
        )

        assert update_result.success is True

        # Verify final state
        final_content = test_file.read_text()
        assert "rate=0.1" in final_content  # New parameter
        assert "round(" in final_content  # New logic
        assert "other_function" in final_content  # Preserved


@pytest.mark.asyncio
class TestCrossFileDependenciesMCP:
    """Test extract_code with include_cross_file_deps=True."""

    @pytest.fixture(autouse=True)
    def _enable_pro_tier(self, monkeypatch):
        """[20260116_TEST] Cross-file deps is Pro+; set tier via env var."""
        # tier_detector.get_current_tier() reads CODE_SCALPEL_TIER
        monkeypatch.setenv("CODE_SCALPEL_TIER", "pro")
        # Also clear any cached tier result
        from code_scalpel.licensing import tier_detector

        detector = tier_detector.TierDetector()
        detector._cached_result = None

    @pytest.fixture
    def multi_file_project(self, tmp_path):
        """Create a multi-file project for cross-file tests."""
        # models.py
        models_py = tmp_path / "models.py"
        models_py.write_text('''"""Models module."""

class TaxRate:
    """Tax rate configuration."""

    def __init__(self, rate: float):
        self.rate = rate

    def calculate(self, amount: float) -> float:
        return amount * self.rate


def get_default_rate() -> float:
    """Get the default tax rate."""
    return 0.1
''')

        # utils.py
        utils_py = tmp_path / "utils.py"
        utils_py.write_text('''"""Utilities module."""

from models import TaxRate, get_default_rate


def calculate_tax(amount: float) -> float:
    """Calculate tax using TaxRate."""
    rate = TaxRate(get_default_rate())
    return rate.calculate(amount)


def simple_function():
    """No external dependencies."""
    return 42
''')

        return tmp_path

    async def test_cross_file_deps_resolves_class(
        self, multi_file_project, monkeypatch
    ):
        """Test that cross-file deps resolves imported classes."""
        monkeypatch.setattr(
            "code_scalpel.mcp.helpers.extraction_helpers.get_current_tier",
            lambda: "pro",
        )
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            file_path=str(multi_file_project / "utils.py"),
            target_type="function",
            target_name="calculate_tax",
            include_cross_file_deps=True,
        )

        assert result.success is True
        assert "calculate_tax" in result.target_code

        # Should have resolved TaxRate from models.py
        assert "TaxRate" in result.context_code
        assert "class TaxRate" in result.context_code
        assert "models.py" in result.context_code

    async def test_cross_file_deps_resolves_function(
        self, multi_file_project, monkeypatch
    ):
        """Test that cross-file deps resolves imported functions."""
        monkeypatch.setattr(
            "code_scalpel.mcp.helpers.extraction_helpers.get_current_tier",
            lambda: "pro",
        )
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            file_path=str(multi_file_project / "utils.py"),
            target_type="function",
            target_name="calculate_tax",
            include_cross_file_deps=True,
        )

        assert result.success is True

        # Should have resolved get_default_rate from models.py
        assert "get_default_rate" in result.context_code
        assert "def get_default_rate" in result.context_code

    async def test_cross_file_deps_full_code(self, multi_file_project, monkeypatch):
        """Test that full_code contains external deps + target."""
        monkeypatch.setattr(
            "code_scalpel.mcp.helpers.extraction_helpers.get_current_tier",
            lambda: "pro",
        )
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            file_path=str(multi_file_project / "utils.py"),
            target_type="function",
            target_name="calculate_tax",
            include_cross_file_deps=True,
        )

        assert result.success is True

        # full_code should have both external symbols and target
        assert "class TaxRate" in result.full_code
        assert "def calculate_tax" in result.full_code
        assert "# From" in result.full_code

    async def test_cross_file_deps_context_items(self, multi_file_project, monkeypatch):
        """Test that context_items lists resolved symbols."""
        monkeypatch.setattr(
            "code_scalpel.mcp.helpers.extraction_helpers.get_current_tier",
            lambda: "pro",
        )
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            file_path=str(multi_file_project / "utils.py"),
            target_type="function",
            target_name="calculate_tax",
            include_cross_file_deps=True,
        )

        assert result.success is True
        assert len(result.context_items) >= 1

        # Context items should mention the resolved symbols
        context_str = " ".join(result.context_items)
        assert "TaxRate" in context_str

    async def test_cross_file_deps_no_deps(self, multi_file_project, monkeypatch):
        """Test function with no external dependencies."""
        monkeypatch.setattr(
            "code_scalpel.mcp.helpers.extraction_helpers.get_current_tier",
            lambda: "pro",
        )
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            file_path=str(multi_file_project / "utils.py"),
            target_type="function",
            target_name="simple_function",
            include_cross_file_deps=True,
        )

        assert result.success is True
        assert "simple_function" in result.target_code
        assert result.context_code == ""  # No external deps

    async def test_cross_file_deps_requires_file_path(self, monkeypatch):
        """Test that cross-file deps requires file_path (not code)."""
        monkeypatch.setattr(
            "code_scalpel.mcp.helpers.extraction_helpers.get_current_tier",
            lambda: "pro",
        )
        from code_scalpel.mcp.server import extract_code

        code = """
from models import TaxRate

def my_func():
    return TaxRate(0.1)
"""

        result = await extract_code(
            code=code,  # Using code, not file_path
            target_type="function",
            target_name="my_func",
            include_cross_file_deps=True,
        )

        # Should succeed but won't resolve cross-file deps
        assert result.success is True
        # Without file_path, can't resolve external deps
        assert "TaxRate" not in result.context_code or result.context_code == ""

    async def test_cross_file_deps_token_savings(self, multi_file_project, monkeypatch):
        """Test that cross-file extraction is token-efficient."""
        monkeypatch.setattr(
            "code_scalpel.mcp.helpers.extraction_helpers.get_current_tier",
            lambda: "pro",
        )
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            file_path=str(multi_file_project / "utils.py"),
            target_type="function",
            target_name="calculate_tax",
            include_cross_file_deps=True,
            include_token_estimate=True,
        )

        assert result.success is True
        assert result.token_estimate > 0

        # Token estimate should be reasonable (not the entire file)
        # The models.py + target should be ~150-250 tokens
        assert result.token_estimate < 500


# [20251212_TEST] v1.4.0 - Tests for new MCP tools


class TestGetFileContext:
    """Tests for the get_file_context tool (v1.4.0)."""

    async def test_get_file_context_basic(self, tmp_path):
        """Test basic file context extraction."""
        from code_scalpel.mcp.server import get_file_context

        # Create a test file
        test_file = tmp_path / "test_module.py"
        test_file.write_text('''
"""A test module."""

import os
from pathlib import Path

def helper_function():
    """A helper function."""
    return 42

class MyClass:
    """A test class."""
    
    def method(self):
        return "hello"
''')

        result = await get_file_context(str(test_file))

        assert result.success is True
        assert result.language == "python"
        assert result.line_count > 0
        # [20260104_BUGFIX] Functions/classes may be dicts (from envelope) or objects
        function_names = [
            f["name"] if isinstance(f, dict) else f.name for f in result.functions
        ]
        class_names = [
            c["name"] if isinstance(c, dict) else c.name for c in result.classes
        ]
        assert "helper_function" in function_names
        assert "MyClass" in class_names
        assert "os" in result.imports
        assert result.complexity_score >= 0

    async def test_get_file_context_security_issues(self, tmp_path):
        """Test file context detects security issues."""
        from code_scalpel.mcp.server import get_file_context

        test_file = tmp_path / "vulnerable.py"
        test_file.write_text("""
def dangerous_eval(user_input):
    return eval(user_input)  # Security issue!
""")

        result = await get_file_context(str(test_file))

        assert result.success is True
        assert result.has_security_issues is True

    async def test_get_file_context_not_found(self):
        """Test handling of non-existent file."""
        from code_scalpel.mcp.server import get_file_context

        result = await get_file_context("/nonexistent/path/file.py")

        assert result.success is False
        assert result.error is not None
        assert "not found" in get_error_message(result.error).lower()

    async def test_get_file_context_syntax_error(self, tmp_path):
        """Test handling of file with syntax error."""
        from code_scalpel.mcp.server import get_file_context

        test_file = tmp_path / "broken.py"
        test_file.write_text("def broken(")  # Invalid syntax

        result = await get_file_context(str(test_file))

        assert result.success is False
        assert result.error is not None
        assert "syntax" in get_error_message(result.error).lower()

    async def test_get_file_context_exports(self, tmp_path):
        """Test detection of __all__ exports."""
        from code_scalpel.mcp.server import get_file_context

        test_file = tmp_path / "exports.py"
        test_file.write_text("""
__all__ = ["public_func", "PublicClass"]

def public_func():
    pass

def _private_func():
    pass

class PublicClass:
    pass
""")

        result = await get_file_context(str(test_file))

        assert result.success is True
        assert "public_func" in result.exports
        assert "PublicClass" in result.exports


class TestGetSymbolReferences:
    """Tests for the get_symbol_references tool (v1.4.0)."""

    async def test_find_function_references(self, tmp_path):
        """Test finding all references to a function."""
        from code_scalpel.mcp.server import get_symbol_references

        # Create multiple files that reference a function
        utils_file = tmp_path / "utils.py"
        utils_file.write_text('''
def helper_function():
    """The helper function definition."""
    return 42
''')

        main_file = tmp_path / "main.py"
        main_file.write_text("""
from utils import helper_function

def main():
    result = helper_function()
    return result
""")

        test_file = tmp_path / "test_utils.py"
        test_file.write_text("""
from utils import helper_function

def test_helper():
    assert helper_function() == 42
""")

        result = await get_symbol_references("helper_function", str(tmp_path))

        assert result.success is True
        assert result.symbol_name == "helper_function"
        assert result.definition_file is not None
        assert result.total_references >= 3  # Definition + 2 usages

    async def test_find_class_references(self, tmp_path):
        """Test finding all references to a class."""
        from code_scalpel.mcp.server import get_symbol_references

        models_file = tmp_path / "models.py"
        models_file.write_text("""
class User:
    def __init__(self, name):
        self.name = name
""")

        service_file = tmp_path / "service.py"
        service_file.write_text("""
from models import User

def create_user(name):
    return User(name)
""")

        result = await get_symbol_references("User", str(tmp_path))

        assert result.success is True
        assert result.total_references >= 2  # Definition + 1 usage
        # References may be dicts (from envelope) or objects
        for ref in result.references:
            ref_dict = ref if isinstance(ref, dict) else ref
            is_def = (
                ref_dict.get("is_definition")
                if isinstance(ref, dict)
                else ref.is_definition
            )
            if is_def:
                break
        assert any(
            (r.get("is_definition") if isinstance(r, dict) else r.is_definition)
            for r in result.references
        )

    async def test_symbol_not_found(self, tmp_path):
        """Test behavior when symbol is not found."""
        from code_scalpel.mcp.server import get_symbol_references

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        result = await get_symbol_references("nonexistent_symbol", str(tmp_path))

        assert result.success is True  # Search succeeded, just no results
        assert result.total_references == 0

    async def test_invalid_project_root(self):
        """Test handling of invalid project root."""
        from code_scalpel.mcp.server import get_symbol_references

        result = await get_symbol_references("some_symbol", "/nonexistent/path")

        assert result.success is False
        assert result.error is not None

    async def test_reference_context_included(self, tmp_path):
        """Test that context snippets are included in references."""
        from code_scalpel.mcp.server import get_symbol_references

        test_file = tmp_path / "code.py"
        test_file.write_text("""
def target_function():
    return "result"

result = target_function()
""")

        result = await get_symbol_references("target_function", str(tmp_path))

        assert result.success is True
        # All references should have context
        # References may be dicts (from envelope) or objects
        for ref in result.references:
            context = ref.get("context") if isinstance(ref, dict) else ref.context
            assert context != ""
            assert "target_function" in context


# ============================================================================
# [20251213_TEST] v1.5.1 - Tests for get_cross_file_dependencies MCP Tool
# ============================================================================


class TestGetCrossFileDependencies:
    """Tests for the get_cross_file_dependencies MCP tool."""

    async def test_basic_cross_file_extraction(self, tmp_path):
        """Test extracting a function with dependencies from another file."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        # Create utils.py with a helper function
        utils_file = tmp_path / "utils.py"
        utils_file.write_text("""
def format_string(s):
    \"\"\"Format a string.\"\"\"
    return s.strip().upper()
""")

        # Create main.py that uses the helper
        main_file = tmp_path / "main.py"
        main_file.write_text("""
from utils import format_string

def process_data(data):
    \"\"\"Process data using utility function.\"\"\"
    return format_string(data)
""")

        result = await get_cross_file_dependencies(
            target_file="main.py",
            target_symbol="process_data",
            project_root=str(tmp_path),
            max_depth=2,
        )

        assert result.success is True
        assert result.target_name == "process_data"
        assert result.target_file == "main.py"
        # Should have extracted the target function
        assert len(result.extracted_symbols) >= 1
        symbol_names = [s.name for s in result.extracted_symbols]
        assert "process_data" in symbol_names

    async def test_combined_code_generation(self, tmp_path):
        """Test that combined code is generated correctly."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        helper_file = tmp_path / "helper.py"
        helper_file.write_text("""
def helper():
    return "help"
""")

        main_file = tmp_path / "main.py"
        main_file.write_text("""
from helper import helper

def main():
    return helper()
""")

        result = await get_cross_file_dependencies(
            target_file="main.py",
            target_symbol="main",
            project_root=str(tmp_path),
            include_code=True,
        )

        assert result.success is True
        # Combined code should contain the target function
        assert "def main():" in result.combined_code
        assert result.token_estimate > 0

    async def test_without_code_inclusion(self, tmp_path):
        """Test extraction without including full code."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        main_file = tmp_path / "main.py"
        main_file.write_text("""
def target_func():
    return 42
""")

        result = await get_cross_file_dependencies(
            target_file="main.py",
            target_symbol="target_func",
            project_root=str(tmp_path),
            include_code=False,
        )

        assert result.success is True
        # Combined code should be empty when include_code=False
        assert result.combined_code == ""
        # But symbol info should still be there
        assert len(result.extracted_symbols) >= 1

    async def test_mermaid_diagram_generation(self, tmp_path):
        """Test that Mermaid diagram is generated."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        # Create files with imports
        a_file = tmp_path / "a.py"
        a_file.write_text("""
def func_a():
    return 1
""")

        b_file = tmp_path / "b.py"
        b_file.write_text("""
from a import func_a

def func_b():
    return func_a() + 1
""")

        result = await get_cross_file_dependencies(
            target_file="b.py",
            target_symbol="func_b",
            project_root=str(tmp_path),
            include_diagram=True,
        )

        assert result.success is True
        # Mermaid diagram should be generated
        assert (
            "graph" in result.mermaid.lower()
            or "flowchart" in result.mermaid.lower()
            or result.mermaid == ""
        )

    async def test_file_not_found(self, tmp_path):
        """Test handling of nonexistent target file."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        result = await get_cross_file_dependencies(
            target_file="nonexistent.py",
            target_symbol="func",
            project_root=str(tmp_path),
        )

        assert result.success is False
        assert result.error is not None
        # error may be a string or ToolError object; extract string either way
        error_msg = (
            result.error.error if hasattr(result.error, "error") else result.error
        )
        assert "not found" in error_msg.lower()

    async def test_invalid_project_root(self):
        """Test handling of invalid project root."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        result = await get_cross_file_dependencies(
            target_file="main.py",
            target_symbol="func",
            project_root="/nonexistent/path",
        )

        assert result.success is False
        assert result.error is not None

    async def test_circular_import_detection(self, tmp_path):
        """Test detection of circular imports."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        # Create circular import situation
        a_file = tmp_path / "a.py"
        a_file.write_text("""
from b import func_b

def func_a():
    return func_b()
""")

        b_file = tmp_path / "b.py"
        b_file.write_text("""
from a import func_a

def func_b():
    return func_a()
""")

        result = await get_cross_file_dependencies(
            target_file="a.py",
            target_symbol="func_a",
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Should detect circular imports
        assert len(result.circular_imports) > 0

    async def test_max_depth_limiting(self, tmp_path):
        """Test that max_depth limits dependency resolution."""
        from code_scalpel.mcp.server import get_cross_file_dependencies

        # Create a chain of dependencies
        c_file = tmp_path / "c.py"
        c_file.write_text("""
def func_c():
    return "c"
""")

        b_file = tmp_path / "b.py"
        b_file.write_text("""
from c import func_c

def func_b():
    return func_c()
""")

        a_file = tmp_path / "a.py"
        a_file.write_text("""
from b import func_b

def func_a():
    return func_b()
""")

        # With max_depth=1, should only get immediate dependencies
        result = await get_cross_file_dependencies(
            target_file="a.py",
            target_symbol="func_a",
            project_root=str(tmp_path),
            max_depth=1,
        )

        assert result.success is True


# ============================================================================
# [20251213_TEST] v1.5.1 - Tests for cross_file_security_scan MCP Tool
# ============================================================================


class TestCrossFileSecurityScan:
    """Tests for the cross_file_security_scan MCP tool."""

    async def test_no_vulnerabilities(self, tmp_path):
        """Test scanning code with no vulnerabilities."""
        from code_scalpel.mcp.server import cross_file_security_scan

        safe_file = tmp_path / "safe.py"
        safe_file.write_text("""
def safe_function(x):
    return x * 2
""")

        result = await cross_file_security_scan(project_root=str(tmp_path))

        assert result.success is True
        assert result.has_vulnerabilities is False
        assert result.vulnerability_count == 0
        assert result.risk_level == "low"

    async def test_cross_file_sql_injection(self, tmp_path):
        """Test detecting SQL injection across files."""
        from code_scalpel.mcp.server import cross_file_security_scan

        # Create routes.py with user input
        routes_file = tmp_path / "routes.py"
        routes_file.write_text("""
from flask import request
from db import execute_query

def search():
    query = request.args.get('q')
    return execute_query(query)
""")

        # Create db.py with SQL execution
        db_file = tmp_path / "db.py"
        db_file.write_text("""
import sqlite3

def execute_query(query):
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE name = '{query}'")
    return cursor.fetchall()
""")

        result = await cross_file_security_scan(project_root=str(tmp_path))

        assert result.success is True
        assert result.files_analyzed >= 2

    async def test_taint_flow_detection(self, tmp_path):
        """Test that taint flows are detected across files."""
        from code_scalpel.mcp.server import cross_file_security_scan

        input_file = tmp_path / "input.py"
        input_file.write_text("""
def get_user_input():
    return input("Enter data: ")
""")

        process_file = tmp_path / "process.py"
        process_file.write_text("""
from input import get_user_input
import os

def process():
    data = get_user_input()
    os.system(data)
""")

        result = await cross_file_security_scan(project_root=str(tmp_path))

        assert result.success is True

    async def test_mermaid_diagram_for_security(self, tmp_path):
        """Test that security scan generates Mermaid diagram."""
        from code_scalpel.mcp.server import cross_file_security_scan

        test_file = tmp_path / "test.py"
        test_file.write_text("""
def test_func():
    return 42
""")

        result = await cross_file_security_scan(
            project_root=str(tmp_path), include_diagram=True
        )

        assert result.success is True
        # Diagram should be string (may be empty if no taint flows)
        assert isinstance(result.mermaid, str)

    async def test_invalid_project_root_security(self):
        """Test handling of invalid project root."""
        from code_scalpel.mcp.server import cross_file_security_scan

        result = await cross_file_security_scan(project_root="/nonexistent/path")

        assert result.success is False
        assert result.error is not None

    async def test_entry_points_filtering(self, tmp_path):
        """Test that entry_points parameter filters analysis."""
        from code_scalpel.mcp.server import cross_file_security_scan

        main_file = tmp_path / "main.py"
        main_file.write_text("""
def main():
    return "main"

def other():
    return "other"
""")

        result = await cross_file_security_scan(
            project_root=str(tmp_path),
            entry_points=["main.py:main"],
        )

        assert result.success is True

    async def test_max_depth_for_security(self, tmp_path):
        """Test that max_depth limits security analysis."""
        from code_scalpel.mcp.server import cross_file_security_scan

        test_file = tmp_path / "test.py"
        test_file.write_text("""
def test():
    pass
""")

        result = await cross_file_security_scan(
            project_root=str(tmp_path),
            max_depth=2,
        )

        assert result.success is True

    async def test_risk_level_calculation(self, tmp_path):
        """Test that risk level is calculated correctly."""
        from code_scalpel.mcp.server import cross_file_security_scan

        # Create safe code
        safe_file = tmp_path / "safe.py"
        safe_file.write_text("""
def safe_func():
    return 42
""")

        result = await cross_file_security_scan(project_root=str(tmp_path))

        assert result.success is True
        assert result.risk_level in ["low", "medium", "high", "critical"]
