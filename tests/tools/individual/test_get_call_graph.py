# [20251213_TEST] v1.5.0 - Tests for get_call_graph MCP tool
"""
Comprehensive tests for get_call_graph MCP tool.
Tests the MCP interface, Pydantic models, and async wrapper.
"""

from importlib.util import find_spec
from pathlib import Path

import pytest
from unittest.mock import patch

from code_scalpel.mcp.server import (
    CallEdgeModel,
    CallGraphResultModel,
    CallNodeModel,
    _get_call_graph_sync,
    get_call_graph,
)
from code_scalpel.ir.nodes import (
    IRAttribute,
    IRCall,
    IRFunctionDef,
    IRImport,
    IRModule,
    IRName,
    SourceLocation,
)


def _tree_sitter_available(module_name: str) -> bool:
    return find_spec(module_name) is not None


GENERIC_POLYGLOT_GET_CALL_GRAPH_CASES = [
    pytest.param(
        "main.go",
        "package main\n\nfunc helper() {}\n\nfunc main() {\n    helper()\n}\n",
        "main",
        "helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_go"),
            reason="tree_sitter_go not installed",
        ),
        id="go",
    ),
    pytest.param(
        "main.rs",
        "fn helper() {}\n\nfn main() {\n    helper();\n}\n",
        "main",
        "helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_rust"),
            reason="tree_sitter_rust not installed",
        ),
        id="rust",
    ),
    pytest.param(
        "main.rb",
        "def helper\nend\n\ndef main\n  helper\nend\n",
        "main",
        "helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_ruby"),
            reason="tree_sitter_ruby not installed",
        ),
        id="ruby",
    ),
    pytest.param(
        "main.php",
        "<?php\nfunction helper() {}\nfunction main() { helper(); }\n",
        "main",
        "helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_php"),
            reason="tree_sitter_php not installed",
        ),
        id="php",
    ),
    pytest.param(
        "main.swift",
        "func helper() {}\n\nfunc main() {\n    helper()\n}\n",
        "main",
        "helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_swift"),
            reason="tree_sitter_swift not installed",
        ),
        id="swift",
    ),
    pytest.param(
        "main.kt",
        "fun helper() {}\n\nfun main() {\n    helper()\n}\n",
        "main",
        "helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_kotlin"),
            reason="tree_sitter_kotlin not installed",
        ),
        id="kotlin",
    ),
    pytest.param(
        "main.c",
        "void helper(void) {}\n\nint main(void) {\n    helper();\n    return 0;\n}\n",
        "main",
        "helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_c"),
            reason="tree_sitter_c not installed",
        ),
        id="c",
    ),
    pytest.param(
        "main.cpp",
        "void helper() {}\n\nint main() {\n    helper();\n    return 0;\n}\n",
        "main",
        "helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_cpp"),
            reason="tree_sitter_cpp not installed",
        ),
        id="cpp",
    ),
    pytest.param(
        "Program.cs",
        "public class Program {\n    public static void Helper() { }\n\n    public static void Main(string[] args) {\n        Helper();\n    }\n}\n",
        "Program.Main",
        "Program.Helper",
        marks=pytest.mark.skipif(
            not _tree_sitter_available("tree_sitter_c_sharp"),
            reason="tree_sitter_c_sharp not installed",
        ),
        id="csharp",
    ),
]

GENERIC_FALLBACK_EXTENSION_CASES = [
    "main.go",
    "main.rs",
    "main.rb",
    "main.php",
    "main.swift",
    "main.kt",
    "main.c",
    "main.cpp",
    "Program.cs",
]

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

    def test_result_with_polyglot_parity_metadata(self):
        """[20260308_TEST] Call graph result exposes explicit polyglot parity metadata."""
        result = CallGraphResultModel(
            language_parity={"python": "advanced", "go": "method_local_slice"},
            parity_legend={"advanced": "deep", "method_local_slice": "local"},
            runtime_scope_summary="summary",
        )

        assert result.language_parity["python"] == "advanced"
        assert result.language_parity["go"] == "method_local_slice"
        assert result.parity_legend["method_local_slice"] == "local"
        assert result.runtime_scope_summary == "summary"


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

    def test_sync_exposes_polyglot_foundation_metadata(self, sample_project):
        """[20260308_TEST] Sync get_call_graph exposes current polyglot parity levels."""
        result = _get_call_graph_sync(str(sample_project), None, 10, False)

        assert result.error is None
        assert result.language_parity["python"] == "advanced"
        assert result.language_parity["javascript"] == "runtime_slice"
        assert result.language_parity["typescript"] == "runtime_slice"
        assert result.language_parity["java"] == "runtime_slice"
        assert result.language_parity["go"] == "method_local_slice"
        assert result.language_parity["rust"] == "method_local_slice"
        assert "advanced" in result.parity_legend
        assert "method_local_slice" in result.parity_legend
        assert result.runtime_scope_summary is not None
        assert "conservative import-aware edges" in result.runtime_scope_summary


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

        with patch(
            "code_scalpel.mcp.tools.graph._get_current_tier", return_value="community"
        ):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )
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

        with patch(
            "code_scalpel.mcp.tools.graph._get_current_tier", return_value="community"
        ):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert "graph TD" in result.mermaid
        assert result.tier_applied == "community"
        assert result.max_depth_applied == 10
        assert result.max_nodes_applied == 200
        assert result.advanced_resolution_enabled is False
        assert result.language_parity["javascript"] == "runtime_slice"
        assert result.language_parity["typescript"] == "runtime_slice"
        assert result.language_parity["java"] == "runtime_slice"
        assert result.language_parity["go"] == "method_local_slice"

        files = {n.file for n in result.nodes}
        assert "index.ts" in files
        assert "util.ts" in files

        # At minimum we should see a call from main() to foo().
        assert any(e.caller.endswith(":main") for e in result.edges)

    @pytest.mark.asyncio
    async def test_ts_project_preserves_pro_metadata(self, tmp_path):
        """[20260307_TEST] TypeScript call graph slices should preserve Pro tier metadata."""
        (tmp_path / "util.ts").write_text(
            """
export function foo(value: number): number {
    return value + 1;
}
"""
        )

        (tmp_path / "index.ts").write_text(
            """
import { foo } from './util.ts';

function main(): number {
    return foo(1);
}

main();
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.tier_applied == "pro"
        assert result.max_depth_applied is None
        assert result.max_nodes_applied is None
        assert result.advanced_resolution_enabled is True


class TestJavaSupport:
    """Basic Java call graph foundation coverage."""

    @pytest.mark.asyncio
    async def test_java_project_generates_canonical_method_nodes(self, tmp_path):
        """[20260307_TEST] get_call_graph should surface Java Class.method nodes once builder support exists."""
        (tmp_path / "App.java").write_text(
            """
public class App {
    public static void main(String[] args) {
        helper();
    }

    private static void helper() {
        utility();
    }

    private static void utility() {
    }
}
"""
        )

        with patch(
            "code_scalpel.mcp.tools.graph._get_current_tier", return_value="community"
        ):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.tier_applied == "community"
        assert result.max_depth_applied == 10
        assert result.max_nodes_applied == 200
        assert result.advanced_resolution_enabled is False

        names = {node.name for node in result.nodes}
        assert "App.main" in names
        assert "App.helper" in names
        assert "App.utility" in names

        files = {node.file for node in result.nodes}
        assert "App.java" in files

        assert any(
            edge.caller.endswith(":App.main") and edge.callee.endswith(":App.helper")
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_java_project_preserves_pro_cross_file_resolution(self, tmp_path):
        """[20260307_TEST] Pro Java get_call_graph should resolve static imports across files."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public static void tool() {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import static demo.Helper.tool;

public class App {
    public static void main(String[] args) {
        tool();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.tier_applied == "pro"
        assert result.advanced_resolution_enabled is True
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool"
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_java_project_mermaid_and_paths_stay_relative(self, tmp_path):
        """[20260308_TEST] Java call graph slices should preserve relative file paths and canonical method labels in Mermaid output."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public static void tool() {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import static demo.Helper.tool;

public class App {
    public static void main(String[] args) {
        tool();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert {node.file for node in result.nodes} >= {"demo/App.java", "demo/Helper.java"}
        assert result.mermaid.startswith("graph TD")
        assert "App.main" in result.mermaid
        assert "Helper.tool" in result.mermaid
        assert ":L" in result.mermaid

    @pytest.mark.asyncio
    async def test_java_project_path_query_returns_canonical_method_path(self, tmp_path):
        """[20260308_TEST] Java call graph path queries should return canonical file-backed method paths."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public static void tool() {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import static demo.Helper.tool;

public class App {
    public static void main(String[] args) {
        tool();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path),
                include_circular_import_check=False,
                paths_from="demo/App.java:App.main",
                paths_to="demo/Helper.java:Helper.tool",
            )

        assert result.error is None
        assert result.paths == [["demo/App.java:App.main", "demo/Helper.java:Helper.tool"]]

    @pytest.mark.asyncio
    async def test_java_project_resolves_overloaded_static_import_to_signature_node(
        self, tmp_path
    ):
        """[20260308_TEST] Java call graph should route overloaded static imports to signature-qualified nodes."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public static void tool(int value) {
    }

    public static void tool(String value) {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import static demo.Helper.tool;

public class App {
    public static void main(String[] args) {
        tool(1);
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path),
                include_circular_import_check=False,
                paths_from="demo/App.java:App.main",
                paths_to="demo/Helper.java:Helper.tool(int)",
            )

        assert result.error is None
        names = {node.name for node in result.nodes}
        assert "Helper.tool(int)" in names
        assert "Helper.tool(String)" in names
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool(int)"
            for edge in result.edges
        )
        assert not any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool(String)"
            for edge in result.edges
        )
        assert result.paths == [["demo/App.java:App.main", "demo/Helper.java:Helper.tool(int)"]]

    @pytest.mark.asyncio
    async def test_java_project_infers_method_return_types_for_overloaded_calls(
        self, tmp_path
    ):
        """[20260308_TEST] Java call graph should use method return types when resolving overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Factory.java").write_text(
            """
package demo;

public class Factory {
    public static String make() {
        return "ok";
    }
}
"""
        )

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public static void tool(int value) {
    }

    public static void tool(String value) {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import static demo.Factory.make;
import static demo.Helper.tool;

public class App {
    public static void main(String[] args) {
        tool(make());
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path),
                include_circular_import_check=False,
                paths_from="demo/App.java:App.main",
                paths_to="demo/Helper.java:Helper.tool(String)",
            )

        assert result.error is None
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Factory.java:Factory.make"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool(String)"
            for edge in result.edges
        )
        assert not any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool(int)"
            for edge in result.edges
        )
        assert result.paths == [["demo/App.java:App.main", "demo/Helper.java:Helper.tool(String)"]]

    @pytest.mark.asyncio
    async def test_java_project_infers_method_return_types_for_overloaded_constructors(
        self, tmp_path
    ):
        """[20260308_TEST] Java call graph should use method return types when resolving overloaded constructors."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Factory.java").write_text(
            """
package demo;

public class Factory {
    public static String make() {
        return "ok";
    }
}
"""
        )

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public Helper(int value) {
    }

    public Helper(String value) {
    }

    public void run() {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import static demo.Factory.make;

public class App {
    public static void main(String[] args) {
        Helper helper = new Helper(make());
        helper.run();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path),
                include_circular_import_check=False,
                paths_from="demo/App.java:App.main",
                paths_to="demo/Helper.java:Helper.Helper(String)",
            )

        assert result.error is None
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Factory.java:Factory.make"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.Helper(String)"
            for edge in result.edges
        )
        assert not any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.Helper(int)"
            for edge in result.edges
        )
        assert result.paths == [["demo/App.java:App.main", "demo/Helper.java:Helper.Helper(String)"]]

    @pytest.mark.asyncio
    async def test_java_project_infers_chained_builder_return_types_for_overloaded_calls(
        self, tmp_path
    ):
        """[20260308_TEST] Java call graph should follow chained builder-style method returns into overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Builder.java").write_text(
            """
package demo;

public class Builder {
    public String make() {
        return "ok";
    }
}
"""
        )

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public static void tool(int value) {
    }

    public static void tool(String value) {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import static demo.Helper.tool;

public class App {
    public static void main(String[] args) {
        tool(new Builder().make());
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path),
                include_circular_import_check=False,
                paths_from="demo/App.java:App.main",
                paths_to="demo/Helper.java:Helper.tool(String)",
            )

        assert result.error is None
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Builder.java:Builder.make"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool(String)"
            for edge in result.edges
        )
        assert not any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool(int)"
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_java_project_infers_cast_types_for_overloaded_constructors(
        self, tmp_path
    ):
        """[20260308_TEST] Java call graph should use explicit casts when resolving overloaded constructors."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public Helper(int value) {
    }

    public Helper(String value) {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

public class App {
    public static void main(String[] args) {
        Object raw = "ok";
        new Helper((String) raw);
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path),
                include_circular_import_check=False,
                paths_from="demo/App.java:App.main",
                paths_to="demo/Helper.java:Helper.Helper(String)",
            )

        assert result.error is None
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.Helper(String)"
            for edge in result.edges
        )
        assert not any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.Helper(int)"
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_java_project_infers_static_fluent_builder_return_types_for_overloaded_calls(
        self, tmp_path
    ):
        """[20260308_TEST] Java call graph should use static builder entrypoints and longer fluent chains when selecting overloaded call targets."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Builder.java").write_text(
            """
package demo;

public class Builder {
    public static Builder start() {
        return new Builder();
    }

    public Builder step() {
        return this;
    }

    public String make() {
        return "ok";
    }
}
"""
        )

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public static void tool(int value) {
    }

    public static void tool(String value) {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import static demo.Helper.tool;

public class App {
    public static void main(String[] args) {
        tool(Builder.start().step().make());
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path),
                include_circular_import_check=False,
                paths_from="demo/App.java:App.main",
                paths_to="demo/Helper.java:Helper.tool(String)",
            )

        assert result.error is None
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Builder.java:Builder.start"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Builder.java:Builder.step"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Builder.java:Builder.make"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool(String)"
            for edge in result.edges
        )
        assert not any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool(int)"
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_java_project_infers_static_fluent_builder_return_types_for_overloaded_constructors(
        self, tmp_path
    ):
        """[20260308_TEST] Java call graph should use static builder entrypoints and longer fluent chains when selecting overloaded constructors."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Builder.java").write_text(
            """
package demo;

public class Builder {
    public static Builder start() {
        return new Builder();
    }

    public Builder step() {
        return this;
    }

    public String make() {
        return "ok";
    }
}
"""
        )

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public Helper(int value) {
    }

    public Helper(String value) {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

public class App {
    public static void main(String[] args) {
        new Helper(Builder.start().step().make());
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path),
                include_circular_import_check=False,
                paths_from="demo/App.java:App.main",
                paths_to="demo/Helper.java:Helper.Helper(String)",
            )

        assert result.error is None
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Builder.java:Builder.start"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Builder.java:Builder.step"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Builder.java:Builder.make"
            for edge in result.edges
        )
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.Helper(String)"
            for edge in result.edges
        )
        assert not any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.Helper(int)"
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_java_project_preserves_pro_imported_instance_resolution(self, tmp_path):
        """[20260307_TEST] Pro Java get_call_graph should resolve typed imported instance calls."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public void tool() {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

import demo.Helper;

public class App {
    public static void main(String[] args) {
        Helper helper = new Helper();
        helper.tool();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.advanced_resolution_enabled is True
        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool"
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_java_project_preserves_pro_inherited_method_resolution(self, tmp_path):
        """[20260307_TEST] Pro Java get_call_graph should resolve inherited superclass methods."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Base.java").write_text(
            """
package demo;

public class Base {
    protected void helper() {
    }
}
"""
        )

        (package_dir / "Child.java").write_text(
            """
package demo;

public class Child extends Base {
    public void run() {
        helper();
        this.helper();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.advanced_resolution_enabled is True
        matching_edges = [
            edge
            for edge in result.edges
            if edge.caller == "demo/Child.java:Child.run"
            and edge.callee == "demo/Base.java:Base.helper"
        ]
        assert len(matching_edges) >= 2

    @pytest.mark.asyncio
    async def test_java_project_preserves_pro_field_backed_instance_resolution(self, tmp_path):
        """[20260307_TEST] Pro Java get_call_graph should resolve field-backed instance calls."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Helper.java").write_text(
            """
package demo;

public class Helper {
    public void tool() {
    }
}
"""
        )

        (package_dir / "App.java").write_text(
            """
package demo;

public class App {
    private final Helper helper = new Helper();

    public void run() {
        this.helper.tool();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.advanced_resolution_enabled is True
        assert any(
            edge.caller == "demo/App.java:App.run"
            and edge.callee == "demo/Helper.java:Helper.tool"
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_java_project_preserves_pro_imported_superclass_resolution(
        self, tmp_path
    ):
        """[20260308_TEST] Pro Java get_call_graph should resolve imported superclass methods across packages."""
        base_dir = tmp_path / "demo" / "base"
        app_dir = tmp_path / "demo" / "app"
        base_dir.mkdir(parents=True)
        app_dir.mkdir(parents=True)

        (base_dir / "Base.java").write_text(
            """
package demo.base;

public class Base {
    protected void helper() {
    }
}
"""
        )

        (app_dir / "Child.java").write_text(
            """
package demo.app;

import demo.base.Base;

public class Child extends Base {
    public void run() {
        helper();
        this.helper();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        matches = [
            edge
            for edge in result.edges
            if edge.caller == "demo/app/Child.java:Child.run"
            and edge.callee == "demo/base/Base.java:Base.helper"
        ]
        assert len(matches) >= 2

    @pytest.mark.asyncio
    async def test_java_project_prefers_overridden_child_method_resolution(self, tmp_path):
        """[20260308_TEST] Pro Java get_call_graph should prefer overridden child methods over superclass fallbacks."""
        package_dir = tmp_path / "demo"
        package_dir.mkdir()

        (package_dir / "Base.java").write_text(
            """
package demo;

public class Base {
    protected void helper() {
    }
}
"""
        )

        (package_dir / "Child.java").write_text(
            """
package demo;

public class Child extends Base {
    @Override
    protected void helper() {
    }

    public void run() {
        helper();
        this.helper();
    }
}
"""
        )

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        child_matches = [
            edge
            for edge in result.edges
            if edge.caller == "demo/Child.java:Child.run"
            and edge.callee == "demo/Child.java:Child.helper"
        ]
        base_matches = [
            edge
            for edge in result.edges
            if edge.caller == "demo/Child.java:Child.run"
            and edge.callee == "demo/Base.java:Base.helper"
        ]
        assert len(child_matches) >= 2
        assert not base_matches


class TestGenericPolyglotSupport:
    """Generic IR-backed call graph coverage for the broader polyglot set."""

    @pytest.mark.parametrize(
        ("filename", "code", "caller_name", "callee_name"),
        GENERIC_POLYGLOT_GET_CALL_GRAPH_CASES,
    )
    @pytest.mark.asyncio
    async def test_get_call_graph_generic_languages_emit_local_edges(
        self, tmp_path, filename, code, caller_name, callee_name
    ):
        """[20260307_TEST] get_call_graph should emit local nodes and edges for generic polyglot languages."""
        (tmp_path / filename).write_text(code, encoding="utf-8")

        with patch(
            "code_scalpel.mcp.tools.graph._get_current_tier", return_value="community"
        ):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.tier_applied == "community"
        assert result.max_depth_applied == 10
        assert result.max_nodes_applied == 200
        assert result.language_parity["csharp"] == "method_local_slice"
        assert result.language_parity["swift"] == "method_local_slice"

        names = {node.name for node in result.nodes}
        assert caller_name in names
        assert callee_name in names
        assert any(
            edge.caller.endswith(f":{caller_name}")
            and edge.callee.endswith(f":{callee_name}")
            for edge in result.edges
        )

    @pytest.mark.parametrize("filename", GENERIC_FALLBACK_EXTENSION_CASES)
    @pytest.mark.asyncio
    async def test_get_call_graph_generic_ir_fallback_supports_extension_matrix(
        self, tmp_path, monkeypatch, filename
    ):
        """[20260307_TEST] get_call_graph should use the generic IR fallback for every mapped extension."""
        from code_scalpel.ast_tools.call_graph import CallGraphBuilder

        file_path = tmp_path / filename
        file_path.write_text("placeholder", encoding="utf-8")

        module = IRModule(
            body=[
                IRFunctionDef(
                    name="helper",
                    body=[],
                    loc=SourceLocation(line=1, column=0, end_line=1, end_column=1),
                ),
                IRFunctionDef(
                    name="main",
                    body=[
                        IRCall(
                            func=IRName(id="helper"),
                            args=[],
                            loc=SourceLocation(
                                line=3, column=4, end_line=3, end_column=10
                            ),
                        )
                    ],
                    loc=SourceLocation(line=2, column=0, end_line=4, end_column=1),
                ),
            ]
        )

        def fake_load_ir_module(self, requested_file_path, rel_path):
            if Path(requested_file_path) == file_path:
                self._ir_modules[rel_path] = module
                return module
            return None

        monkeypatch.setattr(CallGraphBuilder, "_load_ir_module", fake_load_ir_module)

        with patch(
            "code_scalpel.mcp.tools.graph._get_current_tier", return_value="community"
        ):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert {node.name for node in result.nodes} >= {"main", "helper"}
        assert any(
            edge.caller.endswith(":main") and edge.callee.endswith(":helper")
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_get_call_graph_receiver_methods_emit_method_local_nodes(
        self, tmp_path, monkeypatch
    ):
        """[20260308_TEST] get_call_graph should expose receiver-qualified generic method nodes."""
        from code_scalpel.ast_tools.call_graph import CallGraphBuilder

        file_path = tmp_path / "main.go"
        file_path.write_text("placeholder", encoding="utf-8")

        help_fn = IRFunctionDef(name="help", body=[], source_language="go")
        help_fn._metadata["receiver"] = "(worker Worker)"

        run_fn = IRFunctionDef(
            name="run",
            body=[
                IRCall(
                    func=IRAttribute(value=IRName(id="worker"), attr="help"),
                    args=[],
                )
            ],
            source_language="go",
        )
        run_fn._metadata["receiver"] = "(worker Worker)"

        module = IRModule(source_language="go", body=[help_fn, run_fn])

        def fake_load_ir_module(self, requested_file_path, rel_path):
            if Path(requested_file_path) == file_path:
                self._ir_modules[rel_path] = module
                return module
            return None

        monkeypatch.setattr(CallGraphBuilder, "_load_ir_module", fake_load_ir_module)

        with patch(
            "code_scalpel.mcp.tools.graph._get_current_tier", return_value="community"
        ):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.language_parity["go"] == "method_local_slice"
        assert {node.name for node in result.nodes} >= {"Worker.run", "Worker.help"}
        assert any(
            edge.caller.endswith(":Worker.run")
            and edge.callee.endswith(":Worker.help")
            for edge in result.edges
        )

    @pytest.mark.asyncio
    async def test_get_call_graph_generic_ir_advanced_resolution_follows_imported_files(
        self, tmp_path, monkeypatch
    ):
        """[20260308_TEST] Pro get_call_graph should surface conservative imported-file generic edges."""
        from code_scalpel.ast_tools.call_graph import CallGraphBuilder

        caller_path = tmp_path / "App.kt"
        caller_path.write_text("placeholder", encoding="utf-8")
        callee_path = tmp_path / "demo" / "Helper.kt"
        callee_path.parent.mkdir(parents=True, exist_ok=True)
        callee_path.write_text("placeholder", encoding="utf-8")

        module_map = {
            "App.kt": IRModule(
                source_language="kotlin",
                body=[
                    IRImport(module="demo.Helper.tool"),
                    IRFunctionDef(name="main", body=[IRCall(func=IRName(id="tool"), args=[])]),
                ],
            ),
            "demo/Helper.kt": IRModule(
                source_language="kotlin",
                body=[IRFunctionDef(name="tool", body=[])],
            ),
        }

        def fake_load_ir_module(self, requested_file_path, rel_path):
            del requested_file_path
            module = module_map.get(rel_path)
            if module is not None:
                self._ir_modules[rel_path] = module
            return module

        monkeypatch.setattr(CallGraphBuilder, "_load_ir_module", fake_load_ir_module)

        with patch("code_scalpel.mcp.tools.graph._get_current_tier", return_value="pro"):
            result = await get_call_graph(
                project_root=str(tmp_path), include_circular_import_check=False
            )

        assert result.error is None
        assert result.advanced_resolution_enabled is True
        assert any(
            edge.caller == "App.kt:main" and edge.callee == "demo/Helper.kt:tool"
            for edge in result.edges
        )


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
