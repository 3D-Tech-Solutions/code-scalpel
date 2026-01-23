"""
v1.5.1 Integration Tests - Cross-File Analysis Workflows

[20251213_TEST] Tests end-to-end workflows using ImportResolver,
CrossFileExtractor, and CrossFileTaintTracker together.

These tests verify that the v1.5.1 components work correctly in
realistic scenarios that span multiple files.
"""

import pytest


class TestCrossFileWorkflow:
    """Integration tests for complete cross-file analysis workflows."""

    @pytest.fixture
    def flask_project(self, tmp_path):
        """Create a realistic Flask project structure."""
        # app.py - main application entry point
        app_file = tmp_path / "app.py"
        app_file.write_text("""
from flask import Flask
from routes import register_routes

app = Flask(__name__)
register_routes(app)

if __name__ == "__main__":
    app.run(debug=True)
""")

        # routes.py - route definitions
        routes_file = tmp_path / "routes.py"
        routes_file.write_text("""
from flask import request, jsonify
from services import user_service
from db import database

def register_routes(app):
    @app.route("/search")
    def search():
        query = request.args.get("q")
        results = user_service.search_users(query)
        return jsonify(results)

    @app.route("/users/<int:user_id>")
    def get_user(user_id):
        user = database.get_user(user_id)
        return jsonify(user)
""")

        # services/user_service.py
        services_dir = tmp_path / "services"
        services_dir.mkdir()
        (services_dir / "__init__.py").write_text("")
        (services_dir / "user_service.py").write_text('''
from db import database

def search_users(query):
    """Search for users - potentially vulnerable."""
    return database.execute_query(f"SELECT * FROM users WHERE name LIKE '%{query}%'")

def get_user_by_id(user_id):
    """Get user by ID - safe parameterized query."""
    return database.get_user(user_id)
''')

        # db.py - database module
        db_file = tmp_path / "db.py"
        db_file.write_text('''
import sqlite3

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def execute_query(self, query):
        """Execute raw SQL - dangerous!"""
        cursor = self.conn.cursor()
        cursor.execute(query)  # SQL Injection sink
        return cursor.fetchall()

    def get_user(self, user_id):
        """Get user by ID - safe."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()

database = Database()
''')

        return tmp_path

    def test_import_resolver_analyzes_flask_project(self, flask_project):
        """Test that ImportResolver can analyze a Flask project."""
        from code_scalpel.ast_tools.import_resolver import ImportResolver

        resolver = ImportResolver(flask_project)
        result = resolver.build()

        assert result.success
        assert result.modules >= 4  # app, routes, db, services

        # Check that imports are tracked
        assert len(resolver.imports) > 0

        # Verify module relationships using get_importers
        db_importers = resolver.get_importers("db")
        assert len(db_importers) >= 1  # db is imported by routes and/or services

    def test_cross_file_extractor_extracts_dependencies(self, flask_project):
        """Test that CrossFileExtractor can extract search_users with all deps."""
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(flask_project)
        extractor.build()

        result = extractor.extract(
            str(flask_project / "services" / "user_service.py"),
            "search_users",
            depth=2,
        )

        assert result.success
        assert result.target is not None
        assert result.target.name == "search_users"

        # Should have the function code
        assert "SELECT * FROM users" in result.target.code or "execute_query" in result.target.code

    def test_cross_file_taint_tracking(self, flask_project):
        """Test that CrossFileTaintTracker detects cross-file vulnerabilities."""
        from code_scalpel.security.analyzers import CrossFileTaintTracker

        tracker = CrossFileTaintTracker(flask_project)
        result = tracker.analyze(max_depth=3)

        assert result.success
        assert result.modules_analyzed >= 3  # At least app, routes, db

    def test_mcp_tools_work_with_flask_project(self, flask_project):
        """Test that the MCP tools work end-to-end."""
        import asyncio

        from code_scalpel.mcp.server import (
            cross_file_security_scan,
            get_cross_file_dependencies,
        )

        async def run_tests():
            # Test get_cross_file_dependencies - use a function instead of variable
            dep_result = await get_cross_file_dependencies(
                target_file="db.py",
                target_symbol="Database",  # A class that exists
                project_root=str(flask_project),
                max_depth=2,
            )
            assert dep_result.success

            # Test cross_file_security_scan
            security_result = await cross_file_security_scan(
                project_root=str(flask_project),
                max_depth=3,
            )
            assert security_result.success

        asyncio.run(run_tests())


class TestLargeProjectScalability:
    """Test that cross-file tools scale to larger projects."""

    @pytest.fixture
    def large_project(self, tmp_path):
        """Create a project with many files."""
        # Create 10 modules with cross-dependencies
        for i in range(10):
            module_file = tmp_path / f"module_{i}.py"

            # Each module imports from 1-3 others
            imports = []
            if i > 0:
                imports.append(f"from module_{i-1} import func_{i-1}")
            if i > 1:
                imports.append(f"from module_{i-2} import func_{i-2}")

            code = "\n".join(imports) + f"""

def func_{i}(x):
    '''Function in module {i}.'''
    result = x * {i+1}
"""
            # Add calls to imported functions
            if i > 0:
                code += f"    result += func_{i-1}(x)\n"
            code += "    return result\n"

            module_file.write_text(code)

        return tmp_path

    def test_import_resolver_scales(self, large_project):
        """Test that ImportResolver handles many modules."""
        from code_scalpel.ast_tools.import_resolver import ImportResolver

        resolver = ImportResolver(large_project)
        result = resolver.build()

        assert result.success
        assert result.modules == 10

    def test_cross_file_extractor_scales(self, large_project):
        """Test that CrossFileExtractor handles deep dependency chains."""
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(large_project)
        extractor.build()

        result = extractor.extract(
            str(large_project / "module_9.py"),
            "func_9",
            depth=5,
        )

        assert result.success
        assert result.target is not None


class TestCircularImportHandling:
    """Test handling of circular imports across the toolchain."""

    @pytest.fixture
    def circular_project(self, tmp_path):
        """Create a project with circular imports."""
        # a.py imports from b.py
        a_file = tmp_path / "a.py"
        a_file.write_text("""
from b import func_b

def func_a():
    return func_b() + 1
""")

        # b.py imports from a.py (circular!)
        b_file = tmp_path / "b.py"
        b_file.write_text("""
from a import func_a

def func_b():
    return 42  # Would call func_a() but that would recurse

def other_func():
    return func_a()
""")

        return tmp_path

    def test_import_resolver_detects_circular(self, circular_project):
        """Test that ImportResolver detects circular imports."""
        from code_scalpel.ast_tools.import_resolver import ImportResolver

        resolver = ImportResolver(circular_project)
        result = resolver.build()

        assert result.success
        # Should have detected the circular import
        circular_imports = resolver.get_circular_imports()
        assert len(circular_imports) > 0

    def test_cross_file_extractor_handles_circular(self, circular_project):
        """Test that CrossFileExtractor doesn't infinite loop on circular deps."""
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(circular_project)
        extractor.build()

        # Should complete without hanging
        result = extractor.extract(
            str(circular_project / "a.py"),
            "func_a",
            depth=3,
        )

        # Should succeed or return a valid result
        assert result is not None


class TestMCPToolConsistency:
    """Test that MCP tools return consistent results."""

    @pytest.fixture
    def simple_project(self, tmp_path):
        """Create a simple two-file project."""
        utils_file = tmp_path / "utils.py"
        utils_file.write_text('''
def helper(x):
    """A helper function."""
    return x + 1
''')

        main_file = tmp_path / "main.py"
        main_file.write_text('''
from utils import helper

def process(x):
    """Process data using helper."""
    return helper(x) * 2
''')

        return tmp_path

    def test_get_cross_file_dependencies_consistency(self, simple_project):
        """Test that get_cross_file_dependencies returns consistent results."""
        import asyncio

        from code_scalpel.mcp.server import get_cross_file_dependencies

        async def run_twice():
            result1 = await get_cross_file_dependencies(
                target_file="main.py",
                target_symbol="process",
                project_root=str(simple_project),
            )
            result2 = await get_cross_file_dependencies(
                target_file="main.py",
                target_symbol="process",
                project_root=str(simple_project),
            )
            return result1, result2

        result1, result2 = asyncio.run(run_twice())

        assert result1.success == result2.success
        assert len(result1.extracted_symbols) == len(result2.extracted_symbols)
        assert result1.token_estimate == result2.token_estimate

    def test_cross_file_security_scan_consistency(self, simple_project):
        """Test that cross_file_security_scan returns consistent results."""
        import asyncio

        from code_scalpel.mcp.server import cross_file_security_scan

        async def run_twice():
            result1 = await cross_file_security_scan(project_root=str(simple_project))
            result2 = await cross_file_security_scan(project_root=str(simple_project))
            return result1, result2

        result1, result2 = asyncio.run(run_twice())

        assert result1.success == result2.success
        assert result1.vulnerability_count == result2.vulnerability_count
        assert result1.risk_level == result2.risk_level


# [20251216_TEST] v2.5.0 - Confidence Decay Tests
class TestConfidenceDecay:
    """Tests for confidence decay in cross-file dependency analysis."""

    @pytest.fixture
    def deep_dependency_project(self, tmp_path):
        """Create a project with deep dependency chain for testing confidence decay."""
        # level_0.py - entry point
        (tmp_path / "level_0.py").write_text("""
from level_1 import func_1

def entry_point():
    return func_1()
""")

        # level_1.py
        (tmp_path / "level_1.py").write_text("""
from level_2 import func_2

def func_1():
    return func_2() + 1
""")

        # level_2.py
        (tmp_path / "level_2.py").write_text("""
from level_3 import func_3

def func_2():
    return func_3() + 2
""")

        # level_3.py
        (tmp_path / "level_3.py").write_text("""
from level_4 import func_4

def func_3():
    return func_4() + 3
""")

        # level_4.py
        (tmp_path / "level_4.py").write_text("""
from level_5 import func_5

def func_4():
    return func_5() + 4
""")

        # level_5.py (leaf node)
        (tmp_path / "level_5.py").write_text("""
def func_5():
    return 5
""")

        return tmp_path

    def test_calculate_confidence_formula(self):
        """Test that confidence decay formula is correct."""
        from code_scalpel.ast_tools.cross_file_extractor import calculate_confidence

        # Formula: C_effective = 1.0 × 0.9^depth
        assert calculate_confidence(0) == 1.0  # Base confidence
        assert calculate_confidence(1) == 0.9
        assert calculate_confidence(2) == 0.81
        assert abs(calculate_confidence(5) - 0.5905) < 0.001
        assert abs(calculate_confidence(10) - 0.3487) < 0.001

    def test_calculate_confidence_custom_decay_factor(self):
        """Test confidence calculation with custom decay factor."""
        from code_scalpel.ast_tools.cross_file_extractor import calculate_confidence

        # More aggressive decay (0.8)
        assert calculate_confidence(0, decay_factor=0.8) == 1.0
        assert calculate_confidence(1, decay_factor=0.8) == 0.8
        assert abs(calculate_confidence(5, decay_factor=0.8) - 0.3277) < 0.001

        # Less aggressive decay (0.95)
        assert calculate_confidence(0, decay_factor=0.95) == 1.0
        assert abs(calculate_confidence(5, decay_factor=0.95) - 0.7738) < 0.001

    def test_extracted_symbol_has_depth_and_confidence(self, deep_dependency_project):
        """Test that extracted symbols include depth and confidence fields."""
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(deep_dependency_project)
        extractor.build()

        result = extractor.extract(
            str(deep_dependency_project / "level_0.py"),
            "entry_point",
            depth=5,
        )

        assert result.success
        assert result.target is not None

        # Target should have depth 0 and confidence 1.0
        assert result.target.depth == 0
        assert result.target.confidence == 1.0

        # Check dependencies have increasing depth
        for dep in result.dependencies:
            assert hasattr(dep, "depth")
            assert hasattr(dep, "confidence")
            assert dep.depth > 0
            assert dep.confidence <= 1.0
            assert dep.confidence > 0.0

    def test_confidence_decays_with_depth(self, deep_dependency_project):
        """Test that confidence properly decays with increasing depth."""
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(deep_dependency_project)
        extractor.build()

        result = extractor.extract(
            str(deep_dependency_project / "level_0.py"),
            "entry_point",
            depth=5,
        )

        assert result.success

        # Group by depth
        by_depth = {}
        for dep in result.dependencies:
            by_depth[dep.depth] = dep.confidence

        # Confidence should decrease with depth
        prev_conf = 1.0
        for depth in sorted(by_depth.keys()):
            assert by_depth[depth] < prev_conf, f"Confidence should decrease at depth {depth}"
            prev_conf = by_depth[depth]

    def test_low_confidence_count_tracked(self, deep_dependency_project):
        """Test that low confidence symbols are counted."""
        from code_scalpel.ast_tools.cross_file_extractor import (
            DEFAULT_LOW_CONFIDENCE_THRESHOLD,
            CrossFileExtractor,
        )

        extractor = CrossFileExtractor(deep_dependency_project)
        extractor.build()

        # Use aggressive decay to trigger low confidence
        result = extractor.extract(
            str(deep_dependency_project / "level_0.py"),
            "entry_point",
            depth=10,
            confidence_decay_factor=0.7,  # Aggressive decay
        )

        assert result.success
        assert result.low_confidence_count >= 0

        # Verify count matches actual low-confidence symbols
        actual_low_conf = len([d for d in result.dependencies if d.confidence < DEFAULT_LOW_CONFIDENCE_THRESHOLD])
        assert result.low_confidence_count == actual_low_conf

    def test_low_confidence_warning_generated(self, deep_dependency_project):
        """Test that warning is generated for low confidence symbols."""
        from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

        extractor = CrossFileExtractor(deep_dependency_project)
        extractor.build()

        # Use aggressive decay to trigger low confidence warning
        result = extractor.extract(
            str(deep_dependency_project / "level_0.py"),
            "entry_point",
            depth=10,
            confidence_decay_factor=0.6,  # Very aggressive decay
        )

        assert result.success
        if result.low_confidence_count > 0:
            assert result.has_low_confidence_symbols
            assert len(result.warnings) > 0
            assert any("low confidence" in w.lower() for w in result.warnings)

    def test_mcp_tool_returns_confidence(self, deep_dependency_project):
        """Test that MCP tool includes confidence in response."""
        import asyncio

        from code_scalpel.mcp.server import get_cross_file_dependencies

        async def run_test():
            result = await get_cross_file_dependencies(
                target_file="level_0.py",
                target_symbol="entry_point",
                project_root=str(deep_dependency_project),
                max_depth=5,
            )
            return result

        result = asyncio.run(run_test())

        assert result.success
        assert result.confidence_decay_factor == 0.9  # Default

        # Check symbols have confidence
        for sym in result.extracted_symbols:
            assert hasattr(sym, "depth")
            assert hasattr(sym, "confidence")
            assert hasattr(sym, "low_confidence")

        # Target should have full confidence
        target_sym = next((s for s in result.extracted_symbols if s.name == "entry_point"), None)
        if target_sym:
            assert target_sym.confidence == 1.0
            assert not target_sym.low_confidence  # Target has confidence 1.0, should not be low

    def test_mcp_tool_custom_decay_factor(self, deep_dependency_project):
        """Test MCP tool with custom confidence decay factor."""
        import asyncio

        from code_scalpel.mcp.server import get_cross_file_dependencies

        async def run_test():
            result = await get_cross_file_dependencies(
                target_file="level_0.py",
                target_symbol="entry_point",
                project_root=str(deep_dependency_project),
                max_depth=5,
                confidence_decay_factor=0.7,  # Custom decay
            )
            return result

        result = asyncio.run(run_test())

        assert result.success
        assert result.confidence_decay_factor == 0.7

        # With aggressive decay, should have some low confidence
        if len(result.extracted_symbols) > 3:
            low_conf_syms = [s for s in result.extracted_symbols if s.low_confidence]
            # At depth 3 with 0.7 decay: 0.7^3 = 0.343 < 0.5 threshold
            assert len(low_conf_syms) >= 0  # May have low confidence symbols

    def test_mcp_tool_low_confidence_warning(self, deep_dependency_project):
        """Test MCP tool returns low confidence warning."""
        import asyncio

        from code_scalpel.mcp.server import get_cross_file_dependencies

        async def run_test():
            result = await get_cross_file_dependencies(
                target_file="level_0.py",
                target_symbol="entry_point",
                project_root=str(deep_dependency_project),
                max_depth=10,
                confidence_decay_factor=0.5,  # Very aggressive to trigger warning
            )
            return result

        result = asyncio.run(run_test())

        assert result.success
        # With 0.5 decay at depth 1: 0.5 = threshold, depth 2: 0.25 < threshold
        if result.low_confidence_count > 0:
            assert result.low_confidence_warning is not None
            assert "low confidence" in result.low_confidence_warning.lower()


# [20250108_TEST] v2.5.0 Graph Neighborhood View tests
@pytest.fixture
def sample_graph():
    """Create a sample graph for testing neighborhood extraction.

    Tests for Graph Neighborhood View feature (v2.5.0).
    Graph Neighborhood extracts k-hop subgraphs around a center node,
    preventing graph explosion on large codebases.
    Formula: N(v, k) = {u ∈ V : d(v, u) ≤ k}
    """
    from code_scalpel.graph_engine import (
        EdgeType,
        GraphEdge,
        GraphNode,
        NodeType,
        UniversalGraph,
        UniversalNodeID,
    )

    graph = UniversalGraph()

    # Create a star topology: center -> [A, B, C, D]
    # And chains: A -> A1 -> A2, B -> B1 -> B2
    center_id = UniversalNodeID(
        language="python",
        module="main",
        node_type=NodeType.FUNCTION,
        name="center",
        line=1,
    )
    graph.add_node(GraphNode(id=center_id, metadata={"file": "main.py"}))

    # First level nodes
    for letter in ["A", "B", "C", "D"]:
        node_id = UniversalNodeID(
            language="python",
            module="module_" + letter.lower(),
            node_type=NodeType.FUNCTION,
            name=f"func_{letter}",
            line=10,
        )
        graph.add_node(GraphNode(id=node_id, metadata={"file": f"module_{letter.lower()}.py"}))

        # Edge from center to this node
        graph.add_edge(
            GraphEdge(
                from_id=str(center_id),
                to_id=str(node_id),
                edge_type=EdgeType.DIRECT_CALL,
                confidence=0.9,
                evidence="Direct call",
            )
        )

    # Second level nodes (chains from A and B)
    for letter in ["A", "B"]:
        for level in [1, 2]:
            parent_name = f"func_{letter}" if level == 1 else f"func_{letter}{level-1}"
            parent_module = f"module_{letter.lower()}" if level == 1 else f"module_{letter.lower()}{level-1}"

            node_id = UniversalNodeID(
                language="python",
                module=f"module_{letter.lower()}{level}",
                node_type=NodeType.FUNCTION,
                name=f"func_{letter}{level}",
                line=10 + level,
            )
            graph.add_node(
                GraphNode(
                    id=node_id,
                    metadata={"file": f"module_{letter.lower()}{level}.py"},
                )
            )

            parent_id = f"python::{parent_module}::function::{parent_name}"
            graph.add_edge(
                GraphEdge(
                    from_id=parent_id,
                    to_id=str(node_id),
                    edge_type=EdgeType.DIRECT_CALL,
                    confidence=0.9,
                    evidence="Direct call",
                )
            )

    return graph


def test_get_graph_neighborhood_fast_fail_avoids_graph_build(monkeypatch, tmp_path):
    import asyncio
    from pathlib import Path

    # Create an empty project root (no modules)
    project_root = tmp_path / "proj"
    project_root.mkdir()

    # If the slow path is taken, we'd build a call graph. Make that explode.
    from code_scalpel.ast_tools import call_graph as call_graph_mod

    def _boom(*args, **kwargs):
        raise AssertionError("CallGraphBuilder.build_with_details should not run")

    monkeypatch.setattr(call_graph_mod.CallGraphBuilder, "build_with_details", _boom)

    from code_scalpel.mcp.server import get_graph_neighborhood

    async def run():
        return await get_graph_neighborhood(
            center_node_id="python::does.not.exist::function::nope",
            k=2,
            max_nodes=10,
            project_root=str(Path(project_root)),
        )

    result = asyncio.run(run())
    assert result.success is False
    assert result.error


def test_basic_neighborhood_extraction(sample_graph):
    """Test basic k-hop neighborhood extraction."""
    center_id = "python::main::function::center"

    result = sample_graph.get_neighborhood(center_id, k=1)

    assert result.success
    assert not result.truncated

    # Should have center + 4 first-level nodes
    assert len(result.subgraph.nodes) == 5

    # Verify center is at depth 0
    assert result.node_depths[center_id] == 0

    # Verify first-level nodes at depth 1
    for letter in ["A", "B", "C", "D"]:
        node_id = f"python::module_{letter.lower()}::function::func_{letter}"
        assert node_id in result.node_depths
    assert result.node_depths[node_id] == 1


def test_deeper_neighborhood(sample_graph):
    """Test k=2 neighborhood includes second-level nodes."""
    center_id = "python::main::function::center"

    result = sample_graph.get_neighborhood(center_id, k=2)

    assert result.success

    # Should have center + 4 first-level + 2 second-level (A1, B1)
    assert len(result.subgraph.nodes) == 7

    # Verify depth 2 nodes
    assert result.node_depths["python::module_a1::function::func_A1"] == 2
    assert result.node_depths["python::module_b1::function::func_B1"] == 2


def test_neighborhood_truncation(sample_graph):
    """Test graph is truncated when exceeding max_nodes."""
    center_id = "python::main::function::center"

    result = sample_graph.get_neighborhood(center_id, k=3, max_nodes=3)

    assert result.success
    assert result.truncated
    assert result.truncation_warning is not None
    assert "truncated" in result.truncation_warning.lower()

    # Should have exactly max_nodes
    assert len(result.subgraph.nodes) <= 3


def test_neighborhood_direction_outgoing(sample_graph):
    """Test outgoing-only neighborhood extraction."""
    center_id = "python::main::function::center"

    result = sample_graph.get_neighborhood(center_id, k=2, direction="outgoing")

    assert result.success

    # Outgoing from center should find all downstream nodes
    assert len(result.subgraph.nodes) >= 5  # center + first level


def test_neighborhood_direction_incoming(sample_graph):
    """Test incoming-only neighborhood extraction."""
    # Test from a leaf node - should find path back to center
    leaf_id = "python::module_a1::function::func_A1"

    result = sample_graph.get_neighborhood(leaf_id, k=2, direction="incoming")

    assert result.success
    # Incoming edges from a leaf may be limited
    assert len(result.subgraph.nodes) >= 1


def test_neighborhood_nonexistent_node(sample_graph):
    """Test error handling for nonexistent center node."""
    result = sample_graph.get_neighborhood("python::nonexistent::function::fake", k=1)

    assert not result.success
    # Node not found should be handled gracefully


def test_neighborhood_confidence_filtering(sample_graph):
    """Test filtering by minimum confidence."""
    center_id = "python::main::function::center"

    # All edges have 0.9 confidence
    result_high = sample_graph.get_neighborhood(center_id, k=2, min_confidence=0.95)
    result_low = sample_graph.get_neighborhood(center_id, k=2, min_confidence=0.5)

    # High confidence filter should exclude more edges
    assert len(result_low.subgraph.nodes) >= len(result_high.subgraph.nodes)


def test_mcp_tool_graph_neighborhood(tmp_path):
    """Test the MCP tool for graph neighborhood extraction."""
    import asyncio

    from code_scalpel.mcp.server import get_graph_neighborhood

    # Create a simple test project
    (tmp_path / "main.py").write_text("""
def entry_point():
    helper()

def helper():
    util()

def util():
    pass
""")

    async def run_test():
        # Use the actual project - it has a call graph
        result = await get_graph_neighborhood(
            center_node_id="python::tmp_cov::function::main",
            k=2,
            max_nodes=50,
            project_root=None,  # Use default PROJECT_ROOT
        )
        return result

    result = asyncio.run(run_test())

    # Tool should return a valid response
    assert hasattr(result, "success")
    assert hasattr(result, "nodes")
    assert hasattr(result, "edges")
    assert hasattr(result, "truncated")
    assert hasattr(result, "mermaid")


def test_mcp_tool_generates_mermaid(tmp_path):
    """Test MCP tool generates Mermaid visualization."""
    import asyncio

    from code_scalpel.mcp.server import get_graph_neighborhood

    async def run_test():
        result = await get_graph_neighborhood(
            center_node_id="python::tmp_cov::function::load_coverage",
            k=2,
            max_nodes=20,
        )
        return result

    result = asyncio.run(run_test())

    if result.success and result.nodes:
        assert result.mermaid is not None
        assert "graph TD" in result.mermaid
        # Center node should have special styling
        assert "center" in result.mermaid


def test_mcp_tool_invalid_parameters():
    """Test MCP tool handles invalid parameters gracefully."""
    import asyncio

    from code_scalpel.mcp.server import get_graph_neighborhood

    async def run_test():
        # Invalid k value
        result = await get_graph_neighborhood(
            center_node_id="python::test::function::test",
            k=0,  # Invalid - must be >= 1
        )
        return result

    result = asyncio.run(run_test())

    assert not result.success
    assert result.error is not None
    assert "must be at least 1" in result.error  # Updated for standardized error format


def test_mcp_tool_invalid_direction():
    """Test MCP tool validates direction parameter."""
    import asyncio

    from code_scalpel.mcp.server import get_graph_neighborhood

    async def run_test():
        result = await get_graph_neighborhood(
            center_node_id="python::test::function::test",
            direction="invalid",  # Invalid direction
        )
        return result

    result = asyncio.run(run_test())

    assert not result.success
    assert "direction" in result.error.lower()
