# [20251213_TEST] v1.5.0 - Tests for get_call_graph MCP tool
"""
Comprehensive tests for get_call_graph MCP tool.
Tests the MCP interface, Pydantic models, and async wrapper.
"""

import pytest

from code_scalpel.mcp.server import (
    CallEdgeModel,
    CallGraphResultModel,
    CallNodeModel,
    _get_call_graph_sync,
    get_call_graph,
)

# ============================================================================
# Test Pydantic Models
# ============================================================================


class TestCallNodeModel:
    """Tests for CallNodeModel."""

    def test_node_creation(self):
        """Test basic node creation."""
        node = CallNodeModel(name="func", file="test.py", line=10)
        assert node.name == "func"
        assert node.file == "test.py"
        assert node.line == 10
        assert node.end_line is None
        assert node.is_entry_point is False

    def test_node_with_all_fields(self):
        """Test node with all fields populated."""
        node = CallNodeModel(
            name="main",
            file="app.py",
            line=5,
            end_line=50,
            is_entry_point=True,
        )
        assert node.is_entry_point is True
        assert node.end_line == 50

    def test_node_serialization(self):
        """Test node serializes to dict correctly."""
        node = CallNodeModel(name="test", file="mod.py", line=1)
        data = node.model_dump()
        assert data["name"] == "test"
        assert data["file"] == "mod.py"


class TestCallEdgeModel:
    """Tests for CallEdgeModel."""

    def test_edge_creation(self):
        """Test basic edge creation."""
        edge = CallEdgeModel(caller="a.py:func_a", callee="b.py:func_b")
        assert edge.caller == "a.py:func_a"
        assert edge.callee == "b.py:func_b"

    def test_edge_external_callee(self):
        """Test edge with external callee."""
        edge = CallEdgeModel(caller="main.py:main", callee="print")
        assert edge.callee == "print"

    def test_edge_serialization(self):
        """Test edge serializes correctly."""
        edge = CallEdgeModel(caller="x", callee="y")
        data = edge.model_dump()
        assert data["caller"] == "x"
        assert data["callee"] == "y"


class TestCallGraphResultModel:
    """Tests for CallGraphResultModel."""

    def test_result_creation(self):
        """Test basic result creation."""
        result = CallGraphResultModel(
            nodes=[CallNodeModel(name="f", file="x.py", line=1)],
            edges=[CallEdgeModel(caller="x.py:f", callee="print")],
            mermaid="graph TD\n    N0[f]",
        )
        assert len(result.nodes) == 1
        assert len(result.edges) == 1
        assert "graph TD" in result.mermaid

    def test_result_with_filtering(self):
        """Test result with entry point filtering."""
        result = CallGraphResultModel(
            nodes=[],
            edges=[],
            entry_point="main.py:main",
            depth_limit=5,
            mermaid="",
        )
        assert result.entry_point == "main.py:main"
        assert result.depth_limit == 5

    def test_result_with_circular_imports(self):
        """Test result with circular imports detected."""
        result = CallGraphResultModel(
            nodes=[],
            edges=[],
            mermaid="",
            circular_imports=[["a.py", "b.py", "a.py"]],
        )
        assert len(result.circular_imports) == 1
        assert "a.py" in result.circular_imports[0]

    def test_result_with_error(self):
        """Test result with error message."""
        result = CallGraphResultModel(error="Something went wrong")
        assert result.error == "Something went wrong"
        assert result.nodes == []


# ============================================================================
# Test Synchronous Implementation
# ============================================================================


class TestGetCallGraphSync:
    """Tests for _get_call_graph_sync function."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project for testing."""
        main_py = tmp_path / "main.py"
        main_py.write_text("""
def main():
    helper()
    print("done")

def helper():
    pass

if __name__ == "__main__":
    main()
""")
        return tmp_path

    def test_sync_returns_result(self, sample_project):
        """Test sync function returns CallGraphResultModel."""
        result = _get_call_graph_sync(str(sample_project), None, 10, False)
        assert isinstance(result, CallGraphResultModel)
        assert result.error is None

    def test_sync_finds_functions(self, sample_project):
        """Test sync function finds functions."""
        result = _get_call_graph_sync(str(sample_project), None, 10, False)
        names = {n.name for n in result.nodes}
        assert "main" in names
        assert "helper" in names

    def test_sync_with_entry_point(self, sample_project):
        """Test sync function with entry point filtering."""
        result = _get_call_graph_sync(str(sample_project), "main", 5, False)
        assert result.entry_point is not None
        assert "main" in (result.entry_point or "")

    def test_sync_with_depth_limit(self, sample_project):
        """Test sync function respects depth limit."""
        result = _get_call_graph_sync(str(sample_project), "main", 1, False)
        assert result.depth_limit == 1

    def test_sync_detects_main_block_entry_point(self, tmp_path):
        """Functions called from __main__ block are treated as entry points."""
        (tmp_path / "app.py").write_text("""
def run():
    helper()

def helper():
    pass

if __name__ == \"__main__\":
    run()
""")

        result = _get_call_graph_sync(str(tmp_path), None, 10, False)
        entry_points = {n.name for n in result.nodes if n.is_entry_point}
        assert "run" in entry_points

    def test_sync_generates_mermaid(self, sample_project):
        """Test sync function generates Mermaid diagram."""
        result = _get_call_graph_sync(str(sample_project), None, 10, False)
        assert "graph TD" in result.mermaid
        assert "main" in result.mermaid

    def test_sync_with_circular_import_check(self, tmp_path):
        """Test sync function detects circular imports."""
        # Create circular import
        (tmp_path / "a.py").write_text("import b")
        (tmp_path / "b.py").write_text("import a")

        result = _get_call_graph_sync(str(tmp_path), None, 10, True)
        assert len(result.circular_imports) >= 1

    def test_sync_without_circular_import_check(self, sample_project):
        """Test sync function skips circular import check when disabled."""
        result = _get_call_graph_sync(str(sample_project), None, 10, False)
        assert result.circular_imports == []

    def test_sync_nonexistent_path(self):
        """Test sync function handles nonexistent path."""
        result = _get_call_graph_sync("/nonexistent/path/to/project", None, 10, False)
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_sync_empty_directory(self, tmp_path):
        """Test sync function handles empty directory."""
        result = _get_call_graph_sync(str(tmp_path), None, 10, False)
        assert result.error is None
        assert result.nodes == []
        assert result.edges == []


# ============================================================================
# Test Async Wrapper
# ============================================================================


class TestGetCallGraphAsync:
    """Tests for async get_call_graph function."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project for testing."""
        code = """
def main():
    process()

def process():
    validate()
    compute()

def validate():
    pass

def compute():
    return 42
"""
        (tmp_path / "app.py").write_text(code)
        return tmp_path

    @pytest.mark.asyncio
    async def test_async_returns_result(self, sample_project):
        """Test async function returns result."""
        result = await get_call_graph(project_root=str(sample_project))
        assert isinstance(result, CallGraphResultModel)

    @pytest.mark.asyncio
    async def test_async_finds_functions(self, sample_project):
        """Test async function finds all functions."""
        result = await get_call_graph(project_root=str(sample_project))
        names = {n.name for n in result.nodes}
        assert "main" in names
        assert "process" in names

    @pytest.mark.asyncio
    async def test_async_with_entry_point(self, sample_project):
        """Test async function with entry point."""
        result = await get_call_graph(
            project_root=str(sample_project),
            entry_point="main",
            depth=10,
        )
        # Should filter to reachable functions
        assert result.entry_point is not None

    @pytest.mark.asyncio
    async def test_async_default_depth(self, sample_project):
        """Test async function uses default depth."""
        result = await get_call_graph(project_root=str(sample_project))
        # Default depth should be used
        assert result.error is None

    @pytest.mark.asyncio
    async def test_async_circular_import_check(self, tmp_path):
        """Test async function checks circular imports by default."""
        (tmp_path / "x.py").write_text("import y")
        (tmp_path / "y.py").write_text("import x")

        result = await get_call_graph(project_root=str(tmp_path))
        # Default should include circular import check
        assert isinstance(result.circular_imports, list)


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_syntax_error_in_file(self, tmp_path):
        """Test handling of files with syntax errors."""
        (tmp_path / "good.py").write_text("def good(): pass")
        (tmp_path / "bad.py").write_text("def broken(")  # Syntax error

        result = await get_call_graph(project_root=str(tmp_path))
        # Should still process good files
        assert result.error is None

    @pytest.mark.asyncio
    async def test_large_depth_value(self, tmp_path):
        """Test with large depth value."""
        (tmp_path / "test.py").write_text("def f(): pass")

        result = await get_call_graph(
            project_root=str(tmp_path),
            depth=1000,  # Very large depth
        )
        assert result.error is None

    @pytest.mark.asyncio
    async def test_zero_depth(self, tmp_path):
        """Test with zero depth."""
        code = """
def a():
    b()

def b():
    c()

def c():
    pass
"""
        (tmp_path / "chain.py").write_text(code)

        result = await get_call_graph(
            project_root=str(tmp_path),
            entry_point="a",
            depth=0,
        )
        assert result.error is None
        # Only entry point should be included
        assert len(result.nodes) >= 1

    @pytest.mark.asyncio
    async def test_nonexistent_entry_point(self, tmp_path):
        """Test with entry point that doesn't exist."""
        (tmp_path / "test.py").write_text("def real(): pass")

        result = await get_call_graph(
            project_root=str(tmp_path),
            entry_point="nonexistent",
        )
        # Should not error, just return limited results
        assert isinstance(result, CallGraphResultModel)

    @pytest.mark.asyncio
    async def test_nested_directories(self, tmp_path):
        """Test with nested directory structure."""
        # Create nested structure
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        sub = pkg / "sub"
        sub.mkdir()

        (pkg / "__init__.py").write_text("")
        (pkg / "module.py").write_text("def outer(): pass")
        (sub / "__init__.py").write_text("")
        (sub / "inner.py").write_text("def inner(): pass")

        result = await get_call_graph(project_root=str(tmp_path))

        # Should find functions in nested dirs
        files = {n.file for n in result.nodes}
        assert any("pkg" in f for f in files)


# ============================================================================
# Test Mermaid Output
# ============================================================================


class TestMermaidOutput:
    """Tests for Mermaid diagram output."""

    @pytest.fixture
    def graph_project(self, tmp_path):
        """Create a project with clear call graph."""
        code = """
def entry():
    first()
    second()

def first():
    helper()

def second():
    helper()

def helper():
    pass
"""
        (tmp_path / "graph.py").write_text(code)
        return tmp_path

    @pytest.mark.asyncio
    async def test_mermaid_valid_syntax(self, graph_project):
        """Test Mermaid output has valid syntax."""
        result = await get_call_graph(project_root=str(graph_project))

        assert result.mermaid.startswith("graph TD")
        # Should have node definitions
        assert "N" in result.mermaid  # Node IDs
        # Should have edges
        assert "-->" in result.mermaid

    @pytest.mark.asyncio
    async def test_mermaid_contains_all_nodes(self, graph_project):
        """Test Mermaid includes all functions."""
        result = await get_call_graph(project_root=str(graph_project))

        assert "entry" in result.mermaid
        assert "first" in result.mermaid
        assert "helper" in result.mermaid

    @pytest.mark.asyncio
    async def test_mermaid_line_numbers(self, graph_project):
        """Test Mermaid includes line numbers."""
        result = await get_call_graph(project_root=str(graph_project))

        # Line numbers should appear as :L<num>
        assert ":L" in result.mermaid


# ============================================================================
# JavaScript/TypeScript Support
# ============================================================================


class TestJavaScriptSupport:
    """Basic JS call graph support at Community tier."""

    @pytest.mark.asyncio
    async def test_js_project_generates_nodes_and_edges(self, tmp_path):
        (tmp_path / "util.js").write_text("""
export function foo() {
    return 1;
}
""")
        (tmp_path / "index.js").write_text("""
import { foo } from './util.js';

function main() {
    foo();
}

main();
""")

        result = await get_call_graph(project_root=str(tmp_path), include_circular_import_check=False)
        assert result.error is None
        assert "graph TD" in result.mermaid

        files = {n.file for n in result.nodes}
        assert "index.js" in files
        assert "util.js" in files

        # At minimum we should see a call from main() to foo().
        assert any(e.caller.endswith(":main") for e in result.edges)


class TestTypeScriptSupport:
    """Basic TS call graph support at Community tier."""

    @pytest.mark.asyncio
    async def test_ts_project_generates_nodes_and_edges(self, tmp_path):
        # [20260122_TEST] Ensure TypeScript call mapping works end-to-end
        (tmp_path / "util.ts").write_text("""
export function foo(value: number): number {
    return value + 1;
}
""")

        (tmp_path / "index.ts").write_text("""
import { foo } from './util.ts';

function main(): number {
    return foo(1);
}

main();
""")

        result = await get_call_graph(project_root=str(tmp_path), include_circular_import_check=False)

        assert result.error is None
        assert "graph TD" in result.mermaid

        files = {n.file for n in result.nodes}
        assert "index.ts" in files
        assert "util.ts" in files

        # At minimum we should see a call from main() to foo().
        assert any(e.caller.endswith(":main") for e in result.edges)


# ============================================================================
# Test Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_flask_app(self, tmp_path):
        """Test with Flask-like application."""
        code = """
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return render_page()

@app.route("/api")
def api():
    data = get_data()
    return jsonify(data)

def render_page():
    return "<html>Hello</html>"

def get_data():
    return {"status": "ok"}

def jsonify(data):
    return str(data)
"""
        (tmp_path / "app.py").write_text(code)

        result = await get_call_graph(project_root=str(tmp_path))

        # Should detect routes as entry points
        entry_points = [n for n in result.nodes if n.is_entry_point]
        assert len(entry_points) >= 1

        # Should have edges
        assert len(result.edges) >= 1

    @pytest.mark.asyncio
    async def test_cli_tool(self, tmp_path):
        """Test with CLI tool structure."""
        code = """
import click

@click.group()
def cli():
    pass

@cli.command()
def init():
    setup()

@cli.command()
def run():
    execute()

def setup():
    pass

def execute():
    process()

def process():
    pass
"""
        (tmp_path / "cli.py").write_text(code)

        result = await get_call_graph(project_root=str(tmp_path))

        # Should find CLI commands
        names = {n.name for n in result.nodes}
        assert "cli" in names
        assert "init" in names
        assert "run" in names

    @pytest.mark.asyncio
    async def test_recursive_function(self, tmp_path):
        """Test with recursive function."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""
        (tmp_path / "math.py").write_text(code)

        result = await get_call_graph(project_root=str(tmp_path))

        # Should handle recursion
        assert result.error is None

        # Should have self-referential edges
        recursive_edges = [
            e
            for e in result.edges
            if e.caller == e.callee
            or (e.caller.endswith(":factorial") and e.callee.endswith(":factorial"))
            or (e.caller.endswith(":fibonacci") and e.callee.endswith(":fibonacci"))
        ]
        assert len(recursive_edges) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
