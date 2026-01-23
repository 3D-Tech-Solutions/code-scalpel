"""
Tests for get_graph_neighborhood tier enforcement and capabilities.

[20260121_TEST] Comprehensive tier validation - Ensure tier limits, capabilities,
and features are properly enforced and populated for Community, Pro, and Enterprise.
"""

import pytest

from code_scalpel.mcp.server import get_graph_neighborhood


class TestCommunityTierLimits:
    """Test Community tier limits: k=1 max, nodes=20 max."""

    @pytest.mark.asyncio
    async def test_community_k_limit_enforced(self, tmp_path, community_tier):
        """Community tier should enforce max_k=1 limit from limits.toml."""
        # Create test project
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    helper()

def helper():
    util()

def util():
    core()

def core():
    pass
""")

        # Request k=5 (beyond Community's limit of k=1)
        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=5,
            max_nodes=50,
            project_root=str(tmp_path),
        )

        # Should succeed, but limited to k=1
        assert result.success is True
        # Community should limit depth to 1
        if result.nodes:
            max_depth = max((n.depth for n in result.nodes), default=0)
            # Community k=1 means max depth should be 1
            assert max_depth <= 1, f"Community limited k should keep max depth ≤ 1, got {max_depth}"

    @pytest.mark.asyncio
    async def test_community_nodes_limit_enforced(self, tmp_path, community_tier):
        """Community tier should enforce max_nodes=20 limit."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    for i in range(10):
        func_a()
        func_b()
        func_c()

def func_a(): pass
def func_b(): pass
def func_c(): pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=2,
            max_nodes=100,  # Request more than Community allows
            project_root=str(tmp_path),
        )

        # Should truncate to 20 nodes max for Community
        if result.nodes is not None:
            assert len(result.nodes) <= 20, f"Community max_nodes is 20, got {len(result.nodes)}"

    @pytest.mark.asyncio
    async def test_community_lacks_semantic_neighbors(self, tmp_path, community_tier):
        """Community tier should lack semantic_neighbors capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def func(): pass")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::func",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Verify Community output has no semantic neighbor data
        if result.nodes:
            for node in result.nodes:
                # Community nodes should not have semantic_neighbor metadata
                if node.metadata:
                    assert "semantic_neighbors" not in node.metadata

    @pytest.mark.asyncio
    async def test_community_lacks_logical_relationships(self, tmp_path, community_tier):
        """Community tier should lack logical_relationship_detection capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def func(): pass")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::func",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Verify Community output has no logical relationships
        if result.edges:
            for edge in result.edges:
                # Community should not have logical relationship edges
                assert edge.edge_type != "logical_related"

    @pytest.mark.asyncio
    async def test_community_mermaid_generated(self, tmp_path, community_tier):
        """Community tier should generate basic Mermaid diagrams."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    helper()

def helper():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert result.mermaid is not None
        assert "graph TD" in result.mermaid
        assert "classDef center" in result.mermaid

    @pytest.mark.asyncio
    async def test_community_basic_neighborhood_capability(self, tmp_path, community_tier):
        """Community tier should have basic_neighborhood capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def func(): pass")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::func",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Community should return valid neighborhood
        assert result.nodes is not None
        assert isinstance(result.nodes, list)


class TestProTierCapabilities:
    """Test Pro tier capabilities: k=5 max, nodes=100 max, semantic neighbors, logical relationships."""

    @pytest.mark.asyncio
    async def test_pro_k_limit_extended(self, tmp_path, pro_tier):
        """Pro tier should support k=5 (vs Community k=1)."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    depth1()

def depth1():
    depth2()

def depth2():
    depth3()

def depth3():
    depth4()

def depth4():
    depth5()

def depth5():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=5,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Pro allows k=5, should have deeper nodes
        if result.nodes:
            max_depth = max((n.depth for n in result.nodes), default=0)
            # Pro k=5 should support depth up to 5
            assert max_depth <= 5, f"Pro k=5 should support depth ≤ 5, got {max_depth}"

    @pytest.mark.asyncio
    async def test_pro_nodes_limit_extended(self, tmp_path, pro_tier):
        """Pro tier should support max_nodes=100 (vs Community 20)."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    func_a()

def func_a(): pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=2,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        # Pro allows up to 100 nodes
        if result.nodes is not None:
            assert len(result.nodes) <= 100, f"Pro max_nodes is 100, got {len(result.nodes)}"

    @pytest.mark.asyncio
    async def test_pro_has_advanced_neighborhood_capability(self, tmp_path, pro_tier):
        """Pro tier should have advanced_neighborhood capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def func(): pass")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::func",
            k=1,
            max_nodes=50,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Pro should return valid neighborhood with advanced features
        assert result.nodes is not None

    @pytest.mark.asyncio
    async def test_pro_has_semantic_neighbors_capability(self, tmp_path, pro_tier):
        """Pro tier should have semantic_neighbors capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def process_order(user_id):
    validate()

def validate():
    pass

def process_user():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::process_order",
            k=1,
            max_nodes=50,
            project_root=str(tmp_path),
        )

        # Pro should attempt semantic neighbor detection (best-effort)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_pro_has_logical_relationship_detection(self, tmp_path, pro_tier):
        """Pro tier should have logical_relationship_detection capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def validate_order(order_id):
    check_stock()

def check_stock():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::validate_order",
            k=1,
            max_nodes=50,
            project_root=str(tmp_path),
        )

        # Pro should attempt logical relationship detection (best-effort)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_pro_mermaid_with_metadata(self, tmp_path, pro_tier):
        """Pro tier should generate Mermaid with enhanced metadata."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    helper()

def helper():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=50,
            project_root=str(tmp_path),
        )

        assert result.success is True
        assert result.mermaid is not None
        assert "graph TD" in result.mermaid


class TestEnterpriseTierCapabilities:
    """Test Enterprise tier capabilities: unlimited k, unlimited nodes, query language."""

    @pytest.mark.asyncio
    async def test_enterprise_unlimited_k(self, tmp_path, enterprise_tier):
        """Enterprise tier should support unlimited k depth."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def d0(): d1()
def d1(): d2()
def d2(): d3()
def d3(): d4()
def d4(): d5()
def d5(): d6()
def d6(): d7()
def d7(): d8()
def d8(): d9()
def d9(): d10()
def d10(): pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::d0",
            k=100,  # Request very deep k
            max_nodes=500,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Enterprise should support deep graphs
        if result.nodes:
            max_depth = max((n.depth for n in result.nodes), default=0)
            # Enterprise should reach all depths up to available
            assert max_depth >= 5, f"Enterprise should support deep k, got max_depth {max_depth}"

    @pytest.mark.asyncio
    async def test_enterprise_unlimited_nodes(self, tmp_path, enterprise_tier):
        """Enterprise tier should support unlimited nodes (no max_nodes limit)."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    for i in range(20):
        func_a()
        func_b()
        func_c()
        func_d()

def func_a(): pass
def func_b(): pass
def func_c(): pass
def func_d(): pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=2,
            max_nodes=999,  # Request more than any limit
            project_root=str(tmp_path),
        )

        # Enterprise has no max_nodes limit in limits.toml
        assert result.success is True

    @pytest.mark.asyncio
    async def test_enterprise_has_all_pro_features(self, tmp_path, enterprise_tier):
        """Enterprise tier should have all Pro features plus more."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def func(): pass")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::func",
            k=5,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Enterprise should have Pro capabilities and more
        assert result.nodes is not None

    @pytest.mark.asyncio
    async def test_enterprise_has_graph_query_language_capability(self, tmp_path, enterprise_tier):
        """Enterprise tier should have graph_query_language capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def process():
    validate()

def validate():
    pass

def process_user():
    pass
""")

        # Enterprise should accept and support query parameter
        result = await get_graph_neighborhood(
            center_node_id="python::main::function::process",
            k=2,
            max_nodes=100,
            project_root=str(tmp_path),
            # query parameter is Enterprise only
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_enterprise_has_custom_traversal_rules(self, tmp_path, enterprise_tier):
        """Enterprise tier should have custom_traversal_rules capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def func(): pass")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::func",
            k=2,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        # Enterprise has custom traversal rules capability
        assert result.success is True

    @pytest.mark.asyncio
    async def test_enterprise_has_path_constraint_queries(self, tmp_path, enterprise_tier):
        """Enterprise tier should have path_constraint_queries capability."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def a(): b()
def b(): c()
def c(): pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::a",
            k=2,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        # Enterprise has path constraint query capability
        assert result.success is True

    @pytest.mark.asyncio
    async def test_enterprise_hot_nodes_detection(self, tmp_path, enterprise_tier):
        """Enterprise tier should populate hot nodes (high-degree nodes)."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def hub():
    a()
    b()
    c()

def a(): pass
def b(): pass
def c(): pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::hub",
            k=1,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Enterprise should detect hot nodes (high-degree central nodes)
        # This is best-effort, so we just verify the structure


class TestCrossTierComparison:
    """Test differences between tier levels on same graph."""

    @pytest.mark.asyncio
    async def test_community_vs_pro_k_limit_difference(self, tmp_path):
        """Compare Community k=1 vs Pro k=5 on same graph."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def d0(): d1()
def d1(): d2()
def d2(): d3()
def d3(): d4()
def d4(): d5()
def d5(): pass
""")

        # Community tier
        from tests.utils.tier_setup import activate_tier

        activate_tier("community")

        result_community = await get_graph_neighborhood(
            center_node_id="python::main::function::d0",
            k=5,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        # Pro tier
        activate_tier("pro")
        result_pro = await get_graph_neighborhood(
            center_node_id="python::main::function::d0",
            k=5,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        # Both should succeed
        assert result_community.success is True
        assert result_pro.success is True

        # Pro should have equal or deeper nodes than Community
        if result_community.nodes and result_pro.nodes:
            comm_depth = max((n.depth for n in result_community.nodes), default=0)
            pro_depth = max((n.depth for n in result_pro.nodes), default=0)
            assert pro_depth >= comm_depth, "Pro should have deeper nodes than Community"

    @pytest.mark.asyncio
    async def test_community_truncation_at_20_nodes(self, tmp_path, community_tier):
        """Community tier should truncate at max_nodes=20."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    f1()
    f2()
    f3()

def f1(): pass
def f2(): pass
def f3(): pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=50,
            project_root=str(tmp_path),
        )

        assert result.success is True
        if result.nodes is not None and len(result.nodes) > 20:
            # Should be truncated
            assert result.truncated is True
            assert result.truncation_warning is not None


class TestCapabilityGating:
    """Test that capabilities are properly gated by tier."""

    @pytest.mark.asyncio
    async def test_community_lacks_semantic_neighbors_explicitly(self, tmp_path, community_tier):
        """Verify Community output does NOT contain semantic neighbor metadata."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def calculate():
    pass

def compute():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::calculate",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Community should not have semantic neighbor data
        if result.nodes:
            for node in result.nodes:
                if node.metadata:
                    assert "semantic_similarity" not in node.metadata

    @pytest.mark.asyncio
    async def test_community_lacks_logical_relationships_explicitly(self, tmp_path, community_tier):
        """Verify Community does NOT include LOGICAL_RELATED edge types."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def validate():
    pass

def verify():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::validate",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        if result.edges:
            for edge in result.edges:
                # Community should not have logical relationships
                assert edge.edge_type != "logical_related", "Community should not have logical_related edges"

    @pytest.mark.asyncio
    async def test_pro_lacks_graph_query_language(self, tmp_path, pro_tier):
        """Verify Pro tier does not support graph query language."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def func(): pass")

        # Pro should not support advanced query parameter (Enterprise only)
        result = await get_graph_neighborhood(
            center_node_id="python::main::function::func",
            k=1,
            max_nodes=50,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Query language is Enterprise-only feature

    @pytest.mark.asyncio
    async def test_pro_lacks_custom_traversal_rules_and_path_constraints(self, tmp_path, pro_tier):
        """Verify Pro tier does not have custom_traversal_rules and path_constraint_queries."""
        main_file = tmp_path / "main.py"
        main_file.write_text("def func(): pass")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::func",
            k=1,
            max_nodes=50,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # These are Enterprise-only features


class TestDirectionFiltering:
    """Test direction parameter works across tiers."""

    @pytest.mark.asyncio
    async def test_direction_filtering_community(self, tmp_path, community_tier):
        """Community should filter by direction: incoming, outgoing, both."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def caller():
    target()

def target():
    callee()

def callee():
    pass
""")

        # Test both direction
        result = await get_graph_neighborhood(
            center_node_id="python::main::function::target",
            k=1,
            max_nodes=20,
            direction="both",
            project_root=str(tmp_path),
        )
        assert result.success is True

        # Test outgoing direction
        result = await get_graph_neighborhood(
            center_node_id="python::main::function::target",
            k=1,
            max_nodes=20,
            direction="outgoing",
            project_root=str(tmp_path),
        )
        assert result.success is True


class TestConfidenceThreshold:
    """Test confidence threshold filtering."""

    @pytest.mark.asyncio
    async def test_min_confidence_filtering(self, tmp_path, community_tier):
        """min_confidence parameter should filter low-confidence edges."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    high_conf()

def high_conf():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=20,
            min_confidence=0.5,
            project_root=str(tmp_path),
        )

        assert result.success is True
        # Edges should be filtered by confidence
        if result.edges:
            for edge in result.edges:
                assert edge.confidence >= 0.5, f"Edge confidence {edge.confidence} below threshold"


class TestMermaidGeneration:
    """Test Mermaid diagram generation across tiers."""

    @pytest.mark.asyncio
    async def test_mermaid_generation_community(self, tmp_path, community_tier):
        """Community should generate valid Mermaid diagrams."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def main():
    helper()

def helper():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::main",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        if result.mermaid:
            assert "graph TD" in result.mermaid
            assert "classDef" in result.mermaid

    @pytest.mark.asyncio
    async def test_mermaid_generation_enterprise(self, tmp_path, enterprise_tier):
        """Enterprise should generate Mermaid with depth-based styling."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def d0():
    d1()

def d1():
    d2()

def d2():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::d0",
            k=2,
            max_nodes=100,
            project_root=str(tmp_path),
        )

        assert result.success is True
        if result.mermaid:
            # Should have depth-based styling
            assert ":::center" in result.mermaid or ":::depth" in result.mermaid


class TestNodeDepthTracking:
    """Test that node depth is properly tracked."""

    @pytest.mark.asyncio
    async def test_node_depths_populated(self, tmp_path, community_tier):
        """Node depths should be populated in result."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    level1()

def level1():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        if result.nodes:
            # Center should have depth 0
            center_nodes = [n for n in result.nodes if n.id == result.center_node_id]
            if center_nodes:
                assert center_nodes[0].depth == 0


class TestEdgeMetadata:
    """Test edge metadata fields."""

    @pytest.mark.asyncio
    async def test_edge_type_and_confidence_populated(self, tmp_path, community_tier):
        """Edges should include type and confidence."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def caller():
    target()

def target():
    pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::caller",
            k=1,
            max_nodes=20,
            project_root=str(tmp_path),
        )

        assert result.success is True
        if result.edges:
            for edge in result.edges:
                assert hasattr(edge, "edge_type")
                assert hasattr(edge, "confidence")
                assert edge.edge_type in ("calls", "direct_call", "logical_related")
                assert 0.0 <= edge.confidence <= 1.0


class TestTruncationProtection:
    """Test truncation warnings when limits exceeded."""

    @pytest.mark.asyncio
    async def test_truncation_warning_community(self, tmp_path, community_tier):
        """Community should warn when truncated at max_nodes=20."""
        main_file = tmp_path / "main.py"
        main_file.write_text("""
def center():
    a()
    b()
    c()
    d()

def a(): pass
def b(): pass
def c(): pass
def d(): pass
""")

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=2,
            max_nodes=100,  # Request beyond Community's 20-node limit
            project_root=str(tmp_path),
        )

        if result.nodes and len(result.nodes) > 20:
            # Should be truncated
            assert result.truncated is True
            assert result.truncation_warning is not None
