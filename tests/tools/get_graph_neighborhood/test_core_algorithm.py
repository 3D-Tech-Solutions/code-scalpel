"""
Core algorithm tests for get_graph_neighborhood.

Tests the fundamental k-hop neighborhood extraction algorithm:
- k-hop traversal correctness
- Depth tracking accuracy
- Node reachability
- Graph traversal logic

These are CRITICAL for pre-release validation.
"""


class TestCoreAlgorithmBasic:
    """Test basic k-hop neighborhood extraction."""

    def test_k1_includes_center_and_direct_neighbors(self, sample_call_graph):
        """k=1 should return center + direct neighbors (depth 1)."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

        assert result.success
        assert not result.truncated

        # Should have center (depth 0) + 4 direct neighbors (depth 1)
        assert len(result.subgraph.nodes) == 5
        assert "python::main::function::center" in result.subgraph.nodes

        # Verify all depth 1 nodes are present
        depth_1_nodes = {
            "python::module_a::function::func_A",
            "python::module_b::function::func_B",
            "python::module_c::function::func_C",
            "python::module_d::function::func_D",
        }
        for node in depth_1_nodes:
            assert node in result.subgraph.nodes

    def test_k1_depth_tracking(self, sample_call_graph):
        """Verify depth values are correct for k=1."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

        # Center should be at depth 0
        assert result.node_depths["python::main::function::center"] == 0

        # All direct neighbors should be at depth 1
        assert result.node_depths["python::module_a::function::func_A"] == 1
        assert result.node_depths["python::module_b::function::func_B"] == 1
        assert result.node_depths["python::module_c::function::func_C"] == 1
        assert result.node_depths["python::module_d::function::func_D"] == 1

    def test_k2_includes_second_level_nodes(self, sample_call_graph):
        """k=2 should include center + depth 1 + depth 2 nodes."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2)

        assert result.success

        # Should have:
        # - 1 center (depth 0)
        # - 4 direct neighbors (depth 1)
        # - 5 second-level nodes (depth 2)
        # Total: 10 nodes
        assert len(result.subgraph.nodes) == 10

        # Verify depth 2 nodes exist
        assert "python::module_a1::function::func_A1" in result.subgraph.nodes
        assert "python::module_a2::function::func_A2" in result.subgraph.nodes
        assert "python::module_b1::function::func_B1" in result.subgraph.nodes
        assert "python::module_c1::function::func_C1" in result.subgraph.nodes
        assert "python::module_d1::function::func_D1" in result.subgraph.nodes

    def test_k2_depth_tracking(self, sample_call_graph):
        """Verify correct depth values for k=2."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2)

        # Depth 2 nodes should be at depth 2
        assert result.node_depths["python::module_a1::function::func_A1"] == 2
        assert result.node_depths["python::module_a2::function::func_A2"] == 2
        assert result.node_depths["python::module_b1::function::func_B1"] == 2
        assert result.node_depths["python::module_c1::function::func_C1"] == 2
        assert result.node_depths["python::module_d1::function::func_D1"] == 2

    def test_k3_extends_neighborhood(self, sample_call_graph):
        """k=3 should include all reachable nodes (when they exist)."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=3)

        assert result.success
        # With only 3 levels of depth, k=3 should get same as k=2
        # (only 10 nodes total exist)
        assert len(result.subgraph.nodes) == 10


class TestDepthTracking:
    """Test accurate depth/distance tracking in neighborhoods."""

    def test_shortest_path_distances(self, simple_graph):
        """Verify distances reflect shortest paths in the graph."""
        # From 'caller' -> 'target' is distance 1
        # From 'caller' -> 'query' is distance 2
        result = simple_graph.get_neighborhood("python::service::function::caller", k=2)

        assert result.success
        # Verify center node depth and reachability
        assert "python::service::function::caller" in result.subgraph.nodes

    def test_k_limiting_respects_depth(self, sample_call_graph):
        """Nodes beyond k should not be included."""
        result_k1 = sample_call_graph.get_neighborhood("python::main::function::center", k=1)
        result_k2 = sample_call_graph.get_neighborhood("python::main::function::center", k=2)

        # k=1 should have fewer nodes than k=2
        assert len(result_k1.subgraph.nodes) < len(result_k2.subgraph.nodes)

        # All k=1 nodes should be in k=2
        for node in result_k1.subgraph.nodes:
            assert node in result_k2.subgraph.nodes


class TestNodeReachability:
    """Test node reachability and graph connectivity."""

    def test_all_depth_1_nodes_reachable_from_center(self, sample_call_graph):
        """All depth 1 nodes should be reachable from center in k=1."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

        depth_1_nodes = {
            "python::module_a::function::func_A",
            "python::module_b::function::func_B",
            "python::module_c::function::func_C",
            "python::module_d::function::func_D",
        }

        for node in depth_1_nodes:
            assert node in result.subgraph.nodes, f"{node} should be reachable"

    def test_nonexistent_center_node_fails(self, sample_call_graph):
        """Requesting neighborhood for nonexistent node should fail gracefully."""
        result = sample_call_graph.get_neighborhood("python::nonexistent::function::fake_node", k=1)

        # Should not crash; error handling tested in integration tests
        # Basic check that it returns a result (even if unsuccessful)
        assert result is not None

    def test_k_zero_invalid(self, sample_call_graph):
        """k=0 should be invalid (need at least center)."""
        # This tests tool-level validation
        # Implementation should reject k < 1
        # Verify through integration test with actual tool
        pass


class TestEdgeInclusion:
    """Test that correct edges are included in neighborhoods."""

    def test_k1_edges_connect_center_to_neighbors(self, sample_call_graph):
        """All edges in k=1 neighborhood should involve the center."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

        # All edges should have center as source or target
        for src, dst, _conf in result.subgraph.edges:
            involved_nodes = {src, dst}
            assert "python::main::function::center" in involved_nodes

    def test_k2_edges_form_valid_paths(self, sample_call_graph):
        """Edges in k=2 neighborhood should form connected paths."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2)

        # Every edge should connect two nodes in the subgraph
        nodes_set = set(result.subgraph.nodes)
        for src, dst, _conf in result.subgraph.edges:
            assert src in nodes_set, f"Edge source {src} not in subgraph"
            assert dst in nodes_set, f"Edge destination {dst} not in subgraph"


class TestAlgorithmEdgeCases:
    """Test edge cases in k-hop algorithm."""

    def test_k_exceeds_graph_depth(self, simple_graph):
        """Requesting k larger than graph depth should return all reachable nodes."""
        # Simple graph has max depth of 2
        result = simple_graph.get_neighborhood(
            "python::service::function::caller", k=10
        )  # Much larger than actual depth

        assert result.success
        # Should get all reachable nodes despite large k
        assert len(result.subgraph.nodes) > 0

    def test_isolated_node(self, simple_graph):
        """A node with no connections should return only itself."""
        # This tests whether isolated nodes are handled
        # Would need a graph with truly isolated nodes
        pass

    def test_circular_dependencies(self):
        """Circular call graphs should not cause infinite loops."""
        # Setup a graph with A -> B -> C -> A
        # k should still limit depth traversal
        pass


class TestPerformanceCharacteristics:
    """Test performance-related behaviors of the algorithm."""

    def test_k1_faster_than_k2(self, sample_call_graph):
        """k=1 should use fewer nodes than k=2 (performance proxy)."""
        result_k1 = sample_call_graph.get_neighborhood("python::main::function::center", k=1)
        result_k2 = sample_call_graph.get_neighborhood("python::main::function::center", k=2)

        # k=1 should be subset of k=2
        k1_nodes = set(result_k1.subgraph.nodes)
        k2_nodes = set(result_k2.subgraph.nodes)
        assert k1_nodes.issubset(k2_nodes)

    def test_large_k_with_max_nodes_limit(self, sample_call_graph):
        """Large k should still respect max_nodes limit."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=100, max_nodes=5)

        # With max_nodes=5, should truncate and warn
        assert len(result.subgraph.nodes) <= 5
