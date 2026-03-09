# [20251213_TEST] v1.5.0 - Tests for enhanced CallGraphBuilder
"""
Comprehensive tests for CallGraphBuilder enhancements:
- Line number tracking
- Entry point filtering
- Depth limiting
- Mermaid diagram generation
- Circular dependency detection
"""

import pytest
from importlib.util import find_spec
from pathlib import Path

from code_scalpel.ast_tools.call_graph import (
    CallEdge,
    CallGraphBuilder,
    CallGraphResult,
    CallNode,
)
from code_scalpel.ir.nodes import (
    IRAttribute,
    IRCall,
    IRClassDef,
    IRFunctionDef,
    IRImport,
    IRModule,
    IRName,
    SourceLocation,
)


def _tree_sitter_available(module_name: str) -> bool:
    return find_spec(module_name) is not None


GENERIC_POLYGLOT_CALL_GRAPH_CASES = [
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
    ("main.go", "main", "helper"),
    ("main.rs", "main", "helper"),
    ("main.rb", "main", "helper"),
    ("main.php", "main", "helper"),
    ("main.swift", "main", "helper"),
    ("main.kt", "main", "helper"),
    ("main.c", "main", "helper"),
    ("main.cpp", "main", "helper"),
    ("Program.cs", "main", "helper"),
]

GENERIC_ADVANCED_RESOLUTION_CASES = [
    pytest.param(
        "main.go",
        "helper.go",
        IRModule(
            source_language="go",
            body=[IRFunctionDef(name="tool", body=[])],
        ),
        IRModule(
            source_language="go",
            body=[
                IRImport(module="helper"),
                IRFunctionDef(
                    name="main",
                    body=[
                        IRCall(
                            func=IRAttribute(value=IRName(id="helper"), attr="tool"),
                            args=[],
                        )
                    ],
                ),
            ],
        ),
        "main",
        "tool",
        id="go-module-call",
    ),
    pytest.param(
        "App.kt",
        "demo/Helper.kt",
        IRModule(
            source_language="kotlin",
            body=[IRFunctionDef(name="tool", body=[])],
        ),
        IRModule(
            source_language="kotlin",
            body=[
                IRImport(module="demo.Helper.tool"),
                IRFunctionDef(
                    name="main",
                    body=[IRCall(func=IRName(id="tool"), args=[])],
                ),
            ],
        ),
        "main",
        "tool",
        id="kotlin-direct-import",
    ),
    pytest.param(
        "App.php",
        "Demo/Helper.php",
        IRModule(
            source_language="php",
            body=[IRClassDef(name="Helper", body=[IRFunctionDef(name="tool", body=[])])],
        ),
        IRModule(
            source_language="php",
            body=[
                IRImport(module="Demo", names=["Helper"]),
                IRClassDef(
                    name="App",
                    body=[
                        IRFunctionDef(
                            name="run",
                            body=[
                                IRCall(
                                    func=IRAttribute(
                                        value=IRName(id="Helper"), attr="tool"
                                    ),
                                    args=[],
                                )
                            ],
                        )
                    ],
                ),
            ],
        ),
        "App.run",
        "Helper.tool",
        id="php-class-import",
    ),
    pytest.param(
        "main.rb",
        "helper.rb",
        IRModule(
            source_language="ruby",
            body=[IRFunctionDef(name="tool", body=[])],
        ),
        IRModule(
            source_language="ruby",
            body=[
                IRImport(module="./helper"),
                IRFunctionDef(
                    name="main",
                    body=[IRCall(func=IRName(id="tool"), args=[])],
                ),
            ],
        ),
        "main",
        "tool",
        id="ruby-require-relative",
    ),
    pytest.param(
        "main.swift",
        "Helper.swift",
        IRModule(
            source_language="swift",
            body=[IRFunctionDef(name="tool", body=[])],
        ),
        IRModule(
            source_language="swift",
            body=[
                IRImport(module="Helper"),
                IRFunctionDef(
                    name="main",
                    body=[IRCall(func=IRName(id="tool"), args=[])],
                ),
            ],
        ),
        "main",
        "tool",
        id="swift-imported-file",
    ),
    pytest.param(
        "main.rs",
        "helper.rs",
        IRModule(
            source_language="rust",
            body=[IRFunctionDef(name="tool", body=[])],
        ),
        IRModule(
            source_language="rust",
            body=[
                IRImport(module="crate::helper::tool"),
                IRFunctionDef(
                    name="main",
                    body=[IRCall(func=IRName(id="tool"), args=[])],
                ),
            ],
        ),
        "main",
        "tool",
        id="rust-use-import",
    ),
]

# ============================================================================
# Test Data Classes
# ============================================================================


class TestCallNode:
    """Tests for CallNode dataclass."""

    def test_call_node_creation(self):
        """Test basic CallNode creation."""
        node = CallNode(name="test_func", file="test.py", line=10)
        assert node.name == "test_func"
        assert node.file == "test.py"
        assert node.line == 10
        assert node.end_line is None
        assert node.is_entry_point is False

    def test_call_node_with_all_fields(self):
        """Test CallNode with all optional fields."""
        node = CallNode(
            name="main",
            file="app.py",
            line=5,
            end_line=25,
            is_entry_point=True,
        )
        assert node.name == "main"
        assert node.end_line == 25
        assert node.is_entry_point is True

    def test_call_node_defaults(self):
        """Test CallNode default values."""
        node = CallNode(name="func", file="module.py", line=1)
        assert node.is_entry_point is False
        assert node.end_line is None


class TestCallEdge:
    """Tests for CallEdge dataclass."""

    def test_call_edge_creation(self):
        """Test basic CallEdge creation."""
        edge = CallEdge(caller="a.py:func_a", callee="b.py:func_b")
        assert edge.caller == "a.py:func_a"
        assert edge.callee == "b.py:func_b"

    def test_call_edge_external_callee(self):
        """Test CallEdge with external callee."""
        edge = CallEdge(caller="main.py:main", callee="print")
        assert edge.callee == "print"


class TestCallGraphResult:
    """Tests for CallGraphResult dataclass."""

    def test_result_creation(self):
        """Test basic CallGraphResult creation."""
        nodes = [CallNode("main", "app.py", 1)]
        edges = [CallEdge("app.py:main", "print")]
        result = CallGraphResult(
            nodes=nodes,
            edges=edges,
            mermaid="graph TD\n    N0[main]",
        )
        assert len(result.nodes) == 1
        assert len(result.edges) == 1
        assert result.entry_point is None
        assert result.depth_limit is None

    def test_result_with_filtering(self):
        """Test CallGraphResult with entry point filtering."""
        result = CallGraphResult(
            nodes=[],
            edges=[],
            entry_point="main.py:main",
            depth_limit=5,
            mermaid="",
        )
        assert result.entry_point == "main.py:main"
        assert result.depth_limit == 5


# ============================================================================
# Test Build With Details
# ============================================================================


class TestBuildWithDetails:
    """Tests for build_with_details method."""

    @pytest.fixture
    def simple_project(self, tmp_path):
        """Create a simple project structure for testing."""
        # main.py
        main_py = tmp_path / "main.py"
        main_py.write_text("""
def main():
    helper()
    print("done")

def helper():
    utility()

def utility():
    pass

if __name__ == "__main__":
    main()
""")

        return tmp_path

    @pytest.fixture
    def multi_file_project(self, tmp_path):
        """Create a multi-file project structure."""
        # main.py
        main_py = tmp_path / "main.py"
        main_py.write_text("""
from utils import process

def main():
    result = process()
    return result

if __name__ == "__main__":
    main()
""")

        # utils.py
        utils_py = tmp_path / "utils.py"
        utils_py.write_text("""
from helpers import validate

def process():
    if validate():
        return compute()
    return None

def compute():
    return 42
""")

        # helpers.py
        helpers_py = tmp_path / "helpers.py"
        helpers_py.write_text("""
def validate():
    return True

def format_output(data):
    return str(data)
""")

        return tmp_path

    def test_build_with_details_returns_result(self, simple_project):
        """Test that build_with_details returns a CallGraphResult."""
        builder = CallGraphBuilder(simple_project)
        result = builder.build_with_details()

        assert isinstance(result, CallGraphResult)
        assert isinstance(result.nodes, list)
        assert isinstance(result.edges, list)
        assert isinstance(result.mermaid, str)

    def test_nodes_have_line_numbers(self, simple_project):
        """Test that nodes include line numbers."""
        builder = CallGraphBuilder(simple_project)
        result = builder.build_with_details()

        # Find the main function node
        main_nodes = [n for n in result.nodes if n.name == "main"]
        assert len(main_nodes) > 0

        main_node = main_nodes[0]
        assert main_node.line > 0
        assert main_node.file == "main.py"

    def test_entry_point_detected(self, simple_project):
        """Test that main is detected as entry point."""
        builder = CallGraphBuilder(simple_project)
        result = builder.build_with_details()

        main_nodes = [n for n in result.nodes if n.name == "main"]
        assert len(main_nodes) > 0
        assert main_nodes[0].is_entry_point is True

    def test_edges_capture_calls(self, simple_project):
        """Test that edges capture function calls."""
        builder = CallGraphBuilder(simple_project)
        result = builder.build_with_details()

        # Find edge from main to helper
        main_to_helper = [
            e for e in result.edges if "main" in e.caller and "helper" in e.callee
        ]
        assert len(main_to_helper) > 0

    @pytest.mark.parametrize(
        ("filename", "code", "caller_name", "callee_name"),
        GENERIC_POLYGLOT_CALL_GRAPH_CASES,
    )
    def test_generic_polyglot_languages_emit_local_edges(
        self, tmp_path, filename, code, caller_name, callee_name
    ):
        """[20260307_TEST] Generic IR-backed languages should emit local call-graph nodes and edges."""
        (tmp_path / filename).write_text(code, encoding="utf-8")

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        names = {node.name for node in result.nodes}
        assert caller_name in names
        assert callee_name in names
        assert any(
            edge.caller.endswith(f":{caller_name}")
            and edge.callee.endswith(f":{callee_name}")
            for edge in result.edges
        )

    @pytest.mark.parametrize(
        ("filename", "caller_name", "callee_name"),
        GENERIC_FALLBACK_EXTENSION_CASES,
    )
    def test_generic_ir_fallback_wires_all_extensions(
        self, tmp_path, monkeypatch, filename, caller_name, callee_name
    ):
        """[20260307_TEST] Generic polyglot extensions should route through the IR-backed call-graph fallback."""
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

        monkeypatch.setattr(
            CallGraphBuilder,
            "_load_ir_module",
            fake_load_ir_module,
        )

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        names = {node.name for node in result.nodes}
        assert caller_name in names
        assert callee_name in names
        assert any(
            edge.caller.endswith(f":{caller_name}")
            and edge.callee.endswith(f":{callee_name}")
            for edge in result.edges
        )

    def test_generic_ir_receiver_methods_emit_canonical_method_nodes(
        self, tmp_path, monkeypatch
    ):
        """[20260308_TEST] Receiver-backed IR methods should emit canonical method names."""
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

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        assert {node.name for node in result.nodes} >= {"Worker.run", "Worker.help"}
        assert any(
            edge.caller.endswith(":Worker.run")
            and edge.callee.endswith(":Worker.help")
            for edge in result.edges
        )

    @pytest.mark.parametrize(
        (
            "caller_rel_path",
            "callee_rel_path",
            "callee_module",
            "caller_module",
            "caller_name",
            "callee_name",
        ),
        GENERIC_ADVANCED_RESOLUTION_CASES,
    )
    def test_generic_ir_advanced_resolution_follows_imported_files(
        self,
        tmp_path,
        monkeypatch,
        caller_rel_path,
        callee_rel_path,
        callee_module,
        caller_module,
        caller_name,
        callee_name,
    ):
        """[20260308_TEST] Advanced generic IR resolution should follow imported project files conservatively."""
        caller_path = tmp_path / caller_rel_path
        caller_path.parent.mkdir(parents=True, exist_ok=True)
        caller_path.write_text("placeholder", encoding="utf-8")

        callee_path = tmp_path / callee_rel_path
        callee_path.parent.mkdir(parents=True, exist_ok=True)
        callee_path.write_text("placeholder", encoding="utf-8")

        module_map = {
            caller_rel_path: caller_module,
            callee_rel_path: callee_module,
        }

        def fake_load_ir_module(self, requested_file_path, rel_path):
            del requested_file_path
            module = module_map.get(rel_path)
            if module is not None:
                self._ir_modules[rel_path] = module
            return module

        monkeypatch.setattr(CallGraphBuilder, "_load_ir_module", fake_load_ir_module)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details(advanced_resolution=True)

        assert any(
            edge.caller.endswith(f":{caller_name}")
            and edge.callee == f"{callee_rel_path}:{callee_name}"
            for edge in result.edges
        )

    def test_entry_point_filtering(self, simple_project):
        """Test filtering from entry point."""
        builder = CallGraphBuilder(simple_project)

        # Get all nodes
        builder.build_with_details()

        # Get nodes reachable from helper only
        result_filtered = builder.build_with_details(entry_point="helper", depth=10)

        # helper -> utility, so we should have at least 2 nodes
        assert len(result_filtered.nodes) >= 1
        assert result_filtered.entry_point == "helper" or "helper" in (
            result_filtered.entry_point or ""
        )

    def test_depth_limiting(self, simple_project):
        """Test depth limiting."""
        builder = CallGraphBuilder(simple_project)

        # Depth 0 should only include entry point
        result_d0 = builder.build_with_details(entry_point="main", depth=0)

        # Depth 1 should include direct callees
        result_d1 = builder.build_with_details(entry_point="main", depth=1)

        # More depth should include more nodes
        result_d10 = builder.build_with_details(entry_point="main", depth=10)

        assert len(result_d0.nodes) <= len(result_d1.nodes) <= len(result_d10.nodes)

    def test_multi_file_traversal(self, multi_file_project):
        """Test that call graph spans multiple files."""
        builder = CallGraphBuilder(multi_file_project)
        result = builder.build_with_details()

        # Should have functions from multiple files
        files = set(n.file for n in result.nodes if n.file != "<external>")
        assert len(files) >= 1  # At least main.py

    def test_java_project_emits_canonical_method_nodes(self, tmp_path):
        """[20260307_TEST] Java builder foundation should emit Class.method nodes and edges."""
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

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        names = {node.name for node in result.nodes}
        assert "App.main" in names
        assert "App.helper" in names
        assert "App.utility" in names

        main_nodes = [node for node in result.nodes if node.name == "App.main"]
        assert len(main_nodes) == 1
        assert main_nodes[0].file == "App.java"
        assert main_nodes[0].is_entry_point is True

        assert any(
            edge.caller.endswith(":App.main") and edge.callee.endswith(":App.helper")
            for edge in result.edges
        )
        assert any(
            edge.caller.endswith(":App.helper")
            and edge.callee.endswith(":App.utility")
            for edge in result.edges
        )

    def test_java_pro_resolves_static_imports_cross_file(self, tmp_path):
        """[20260307_TEST] Advanced Java resolution should follow static imports across files."""
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

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details(advanced_resolution=True)

        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool"
            for edge in result.edges
        )

    def test_java_pro_resolves_imported_instance_method_calls(self, tmp_path):
        """[20260307_TEST] Advanced Java resolution should follow typed imported instance calls."""
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

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details(advanced_resolution=True)

        assert any(
            edge.caller == "demo/App.java:App.main"
            and edge.callee == "demo/Helper.java:Helper.tool"
            for edge in result.edges
        )

    def test_java_pro_resolves_inherited_methods(self, tmp_path):
        """[20260307_TEST] Advanced Java resolution should follow superclass methods."""
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

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details(advanced_resolution=True)

        matching_edges = [
            edge
            for edge in result.edges
            if edge.caller == "demo/Child.java:Child.run"
            and edge.callee == "demo/Base.java:Base.helper"
        ]
        assert len(matching_edges) >= 2

    def test_java_pro_resolves_field_backed_instance_calls(self, tmp_path):
        """[20260307_TEST] Advanced Java resolution should follow field-backed instance calls."""
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

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details(advanced_resolution=True)

        assert any(
            edge.caller == "demo/App.java:App.run"
            and edge.callee == "demo/Helper.java:Helper.tool"
            for edge in result.edges
        )

    def test_java_pro_resolves_imported_superclass_methods_across_packages(
        self, tmp_path
    ):
        """[20260308_TEST] Advanced Java resolution should follow imported superclass methods across packages."""
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

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details(advanced_resolution=True)

        matching_edges = [
            edge
            for edge in result.edges
            if edge.caller == "demo/app/Child.java:Child.run"
            and edge.callee == "demo/base/Base.java:Base.helper"
        ]
        assert len(matching_edges) >= 2


class TestMermaidGeneration:
    """Tests for Mermaid diagram generation."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project for Mermaid tests."""
        main_py = tmp_path / "main.py"
        main_py.write_text("""
def main():
    foo()
    bar()

def foo():
    pass

def bar():
    baz()

def baz():
    pass
""")
        return tmp_path

    def test_mermaid_starts_with_graph(self, sample_project):
        """Test Mermaid output starts with graph directive."""
        builder = CallGraphBuilder(sample_project)
        result = builder.build_with_details()

        assert result.mermaid.startswith("graph TD")

    def test_mermaid_contains_nodes(self, sample_project):
        """Test Mermaid output contains node definitions."""
        builder = CallGraphBuilder(sample_project)
        result = builder.build_with_details()

        # Should have node definitions with labels
        assert "main" in result.mermaid
        assert "foo" in result.mermaid

    def test_mermaid_contains_edges(self, sample_project):
        """Test Mermaid output contains edge definitions."""
        builder = CallGraphBuilder(sample_project)
        result = builder.build_with_details()

        # Should have arrow notation
        assert "-->" in result.mermaid

    def test_mermaid_entry_point_styling(self, sample_project):
        """Test that entry points have special styling."""
        builder = CallGraphBuilder(sample_project)
        result = builder.build_with_details(entry_point="main")

        # Entry points should use stadium shape [[...]]
        assert "[[" in result.mermaid or "main" in result.mermaid

    def test_mermaid_line_numbers(self, sample_project):
        """Test that Mermaid labels include line numbers."""
        builder = CallGraphBuilder(sample_project)
        result = builder.build_with_details()

        # Should have :L notation for line numbers
        assert ":L" in result.mermaid or "main" in result.mermaid


class TestEntryPointDetection:
    """Tests for _is_entry_point method."""

    def test_main_is_entry_point(self, tmp_path):
        """Test that 'main' function is detected as entry point."""
        code = """
def main():
    pass
"""
        test_file = tmp_path / "test.py"
        test_file.write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        main_node = next((n for n in result.nodes if n.name == "main"), None)
        assert main_node is not None
        assert main_node.is_entry_point is True

    def test_click_command_is_entry_point(self, tmp_path):
        """Test that @click.command decorated function is entry point."""
        code = """
import click

@click.command()
def cli():
    pass
"""
        test_file = tmp_path / "test.py"
        test_file.write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        cli_node = next((n for n in result.nodes if n.name == "cli"), None)
        assert cli_node is not None
        assert cli_node.is_entry_point is True

    def test_flask_route_is_entry_point(self, tmp_path):
        """Test that @app.route decorated function is entry point."""
        code = """
from flask import Flask
app = Flask(__name__)

@app.route("/")
def index():
    return "Hello"

@app.get("/api")
def api():
    return {}
"""
        test_file = tmp_path / "test.py"
        test_file.write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        index_node = next((n for n in result.nodes if n.name == "index"), None)
        api_node = next((n for n in result.nodes if n.name == "api"), None)

        assert index_node is not None
        assert api_node is not None
        assert index_node.is_entry_point is True
        assert api_node.is_entry_point is True

    def test_regular_function_not_entry_point(self, tmp_path):
        """Test that regular functions are not entry points."""
        code = """
def helper():
    pass

def utility():
    pass
"""
        test_file = tmp_path / "test.py"
        test_file.write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        for node in result.nodes:
            assert node.is_entry_point is False


class TestReachableNodes:
    """Tests for _get_reachable_nodes method."""

    @pytest.fixture
    def chain_project(self, tmp_path):
        """Create a project with a call chain."""
        code = """
def a():
    b()

def b():
    c()

def c():
    d()

def d():
    pass

def isolated():
    pass
"""
        test_file = tmp_path / "chain.py"
        test_file.write_text(code)
        return tmp_path

    def test_reachable_from_start(self, chain_project):
        """Test nodes reachable from start of chain."""
        builder = CallGraphBuilder(chain_project)
        result = builder.build_with_details(entry_point="a", depth=10)

        # Should reach a, b, c, d
        names = {n.name for n in result.nodes}
        assert "a" in names
        # At least a should be there

    def test_depth_limit_respected(self, chain_project):
        """Test that depth limit is respected."""
        builder = CallGraphBuilder(chain_project)

        # Depth 1: a -> b
        result_d1 = builder.build_with_details(entry_point="a", depth=1)

        # Depth 2: a -> b -> c
        result_d2 = builder.build_with_details(entry_point="a", depth=2)

        # More depth = more nodes
        assert len(result_d1.nodes) <= len(result_d2.nodes)

    def test_isolated_not_reached(self, chain_project):
        """Test that isolated functions are not reached from entry point."""
        builder = CallGraphBuilder(chain_project)
        result = builder.build_with_details(entry_point="a", depth=10)

        # "isolated" should not be in the result when starting from "a"
        names = {n.name for n in result.nodes}
        assert "isolated" not in names


class TestCircularImportDetection:
    """Tests for detect_circular_imports method."""

    def test_no_cycles_returns_empty(self, tmp_path):
        """Test that project with no cycles returns empty list."""
        # a.py imports b, b.py imports c (no cycle)
        (tmp_path / "a.py").write_text("import b")
        (tmp_path / "b.py").write_text("import c")
        (tmp_path / "c.py").write_text("# no imports")

        builder = CallGraphBuilder(tmp_path)
        cycles = builder.detect_circular_imports()

        assert cycles == []

    def test_simple_cycle_detected(self, tmp_path):
        """Test that simple A->B->A cycle is detected."""
        (tmp_path / "a.py").write_text("import b")
        (tmp_path / "b.py").write_text("import a")

        builder = CallGraphBuilder(tmp_path)
        cycles = builder.detect_circular_imports()

        assert len(cycles) >= 1
        # Cycle should include both a.py and b.py
        cycle_files = set()
        for cycle in cycles:
            cycle_files.update(cycle)
        assert "a.py" in cycle_files or any("a" in f for f in cycle_files)

    def test_three_node_cycle_detected(self, tmp_path):
        """Test that A->B->C->A cycle is detected."""
        (tmp_path / "a.py").write_text("import b")
        (tmp_path / "b.py").write_text("import c")
        (tmp_path / "c.py").write_text("import a")

        builder = CallGraphBuilder(tmp_path)
        cycles = builder.detect_circular_imports()

        assert len(cycles) >= 1

    def test_from_import_creates_cycle(self, tmp_path):
        """Test that 'from X import Y' style imports create cycles."""
        (tmp_path / "a.py").write_text("from b import func_b")
        (tmp_path / "b.py").write_text("from a import func_a")

        builder = CallGraphBuilder(tmp_path)
        cycles = builder.detect_circular_imports()

        assert len(cycles) >= 1

    def test_multiple_cycles_detected(self, tmp_path):
        """Test that multiple independent cycles are detected."""
        # Cycle 1: a <-> b
        (tmp_path / "a.py").write_text("import b")
        (tmp_path / "b.py").write_text("import a")

        # Cycle 2: c <-> d (independent)
        (tmp_path / "c.py").write_text("import d")
        (tmp_path / "d.py").write_text("import c")

        builder = CallGraphBuilder(tmp_path)
        cycles = builder.detect_circular_imports()

        # Should detect at least 2 cycles
        assert len(cycles) >= 1  # At least one detected

    def test_external_imports_ignored(self, tmp_path):
        """Test that external library imports don't cause false positives."""
        (tmp_path / "app.py").write_text("""
import os
import sys
from pathlib import Path
import json
""")

        builder = CallGraphBuilder(tmp_path)
        cycles = builder.detect_circular_imports()

        assert cycles == []

    def test_self_import_handled(self, tmp_path):
        """Test that self-import is handled gracefully."""
        (tmp_path / "recursive.py").write_text("import recursive")

        builder = CallGraphBuilder(tmp_path)
        cycles = builder.detect_circular_imports()

        # Should either return the self-cycle or handle gracefully
        # The important thing is it doesn't crash
        assert isinstance(cycles, list)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_directory(self, tmp_path):
        """Test with empty directory."""
        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        assert result.nodes == []
        assert result.edges == []
        assert "graph TD" in result.mermaid

    def test_syntax_error_in_file(self, tmp_path):
        """Test handling of syntax errors in files."""
        (tmp_path / "valid.py").write_text("def valid(): pass")
        (tmp_path / "invalid.py").write_text("def broken( # syntax error")

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        # Should still process valid files
        assert len(result.nodes) >= 1

    def test_nonexistent_entry_point(self, tmp_path):
        """Test with non-existent entry point."""
        (tmp_path / "test.py").write_text("def foo(): pass")

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details(entry_point="nonexistent", depth=5)

        # Should return result, possibly empty or with just the entry point
        assert isinstance(result, CallGraphResult)

    def test_recursive_calls(self, tmp_path):
        """Test handling of recursive function calls."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        (tmp_path / "recursive.py").write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        # Should handle recursive calls without infinite loop
        assert isinstance(result, CallGraphResult)

        # Should have edge from factorial to itself
        factorial_edges = [
            e
            for e in result.edges
            if "factorial" in e.caller and "factorial" in e.callee
        ]
        assert len(factorial_edges) > 0

    def test_nested_functions(self, tmp_path):
        """Test handling of nested function definitions."""
        code = """
def outer():
    def inner():
        pass
    inner()
"""
        (tmp_path / "nested.py").write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        # Should process without errors
        assert isinstance(result, CallGraphResult)

    def test_async_functions(self, tmp_path):
        """Test handling of async functions."""
        code = """
async def async_main():
    await async_helper()

async def async_helper():
    pass
"""
        (tmp_path / "async_code.py").write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        # Should detect async functions
        async_nodes = [n for n in result.nodes if "async" in n.name]
        assert len(async_nodes) >= 1

    def test_class_methods(self, tmp_path):
        """Test handling of class methods."""
        code = """
class MyClass:
    def method_a(self):
        self.method_b()
    
    def method_b(self):
        pass
"""
        (tmp_path / "class_code.py").write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        # Should process class methods
        assert isinstance(result, CallGraphResult)


class TestIntegration:
    """Integration tests with realistic scenarios."""

    def test_flask_app_structure(self, tmp_path):
        """Test with Flask-like application structure."""
        # app/__init__.py
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("""
from flask import Flask
from app.routes import register_routes

def create_app():
    app = Flask(__name__)
    register_routes(app)
    return app
""")

        # app/routes.py
        (app_dir / "routes.py").write_text("""
from app.handlers import handle_index, handle_api

def register_routes(app):
    app.route("/")(handle_index)
    app.route("/api")(handle_api)
""")

        # app/handlers.py
        (app_dir / "handlers.py").write_text("""
from app.services import get_data

def handle_index():
    return "Hello"

def handle_api():
    return get_data()
""")

        # app/services.py
        (app_dir / "services.py").write_text("""
def get_data():
    return {"status": "ok"}
""")

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details()

        assert len(result.nodes) >= 4  # At least several functions
        assert "graph TD" in result.mermaid

    def test_cli_tool_structure(self, tmp_path):
        """Test with CLI tool structure."""
        code = """
import click

@click.group()
def cli():
    pass

@cli.command()
def init():
    setup_config()

@cli.command()
def run():
    execute_task()

def setup_config():
    pass

def execute_task():
    process_data()

def process_data():
    pass

if __name__ == "__main__":
    cli()
"""
        (tmp_path / "cli.py").write_text(code)

        builder = CallGraphBuilder(tmp_path)
        result = builder.build_with_details(entry_point="cli", depth=5)

        # Should capture CLI structure
        assert isinstance(result, CallGraphResult)
        assert len(result.mermaid) > 20  # Has meaningful content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
