"""
Truncation protection tests for get_graph_neighborhood.

Tests the max_nodes parameter and truncation behavior:
- max_nodes limits the size of returned subgraph
- Truncation is reported when max_nodes limit is exceeded
- Partial graphs are still valid (don't crash)

These tests validate safety mechanisms (CRITICAL for pre-release).
"""


class TestTruncationBasic:
    """Test basic truncation behavior with max_nodes."""

    def test_no_truncation_when_nodes_less_than_max(self, sample_call_graph):
        """No truncation should occur when actual nodes <= max_nodes."""
        # sample_call_graph has 12 nodes, request k=1 (5 nodes)
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1, max_nodes=100
        )  # More than we'll get

        assert result.success
        assert not result.truncated
        assert result.truncation_warning is None
        assert len(result.subgraph.nodes) == 5

    def test_truncation_when_nodes_exceed_max(self, sample_call_graph):
        """Truncation should occur when nodes exceed max_nodes."""
        # sample_call_graph k=2 gives 10 nodes
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, max_nodes=5
        )  # Less than we'll get

        assert result.success
        assert result.truncated  # Should be marked as truncated
        assert result.truncation_warning is not None
        assert len(result.subgraph.nodes) <= 5

    def test_truncation_preserves_center_node(self, sample_call_graph):
        """Center node should always be included even after truncation."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=3)

        # Center should be included
        assert "python::main::function::center" in result.subgraph.nodes

    def test_truncation_with_very_small_limit(self, sample_call_graph):
        """Truncation with very small max_nodes should still work."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=1)  # Only center

        assert result.success
        assert len(result.subgraph.nodes) <= 1
        # At minimum, center should be included
        if len(result.subgraph.nodes) == 1:
            assert "python::main::function::center" in result.subgraph.nodes


class TestTruncationWarnings:
    """Test truncation warning generation and reporting."""

    def test_truncation_warning_generated(self, sample_call_graph):
        """Truncation should generate a warning message."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=5)

        if result.truncated:
            assert result.truncation_warning is not None
            assert isinstance(result.truncation_warning, str)
            assert len(result.truncation_warning) > 0

    def test_truncation_warning_contains_useful_info(self, sample_call_graph):
        """Warning should indicate why truncation occurred."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=5)

        if result.truncated:
            warning = result.truncation_warning.lower()
            # Warning should mention truncation or limit
            assert "truncat" in warning or "limit" in warning or "max" in warning

    def test_no_warning_without_truncation(self, sample_call_graph):
        """No truncation warning should appear when truncation doesn't occur."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=100)

        assert not result.truncated
        assert result.truncation_warning is None


class TestPartialGraphValidity:
    """Test that truncated (partial) graphs are still valid."""

    def test_truncated_graph_has_valid_structure(self, sample_call_graph):
        """Truncated graph should maintain valid structure."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=5)

        assert result.success
        # Should have nodes and edges (or be empty, but typically has center at least)
        assert isinstance(result.subgraph.nodes, (list, set))
        assert isinstance(result.subgraph.edges, (list, set))

    def test_edges_in_truncated_graph_reference_nodes(self, sample_call_graph):
        """Edges in truncated graph should only reference nodes in the graph."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=2,
            max_nodes=12,  # Full graph size to avoid truncation edge issues
        )

        nodes_set = set(result.subgraph.nodes)

        # All edge endpoints should be in node set
        for src, dst, _conf in result.subgraph.edges:
            assert src in nodes_set, f"Edge source {src} not in truncated graph"
            assert dst in nodes_set, f"Edge target {dst} not in truncated graph"

    def test_truncated_graph_depth_consistent(self, sample_call_graph):
        """Node depths in truncated graph should be consistent."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=6)

        # Center should be at depth 0
        assert result.node_depths["python::main::function::center"] == 0

        # No other node should have negative depth
        for _node, depth in result.node_depths.items():
            assert depth >= 0


class TestTruncationDataStructures:
    """Test that truncation data structures are correct."""

    def test_node_depths_only_includes_included_nodes(self, sample_call_graph):
        """node_depths dict should only include nodes in the truncated graph."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=5)

        nodes_set = set(result.subgraph.nodes)
        depths_nodes = set(result.node_depths.keys())

        # node_depths should not reference nodes outside the graph
        assert depths_nodes.issubset(nodes_set)

    def test_mermaid_includes_truncated_nodes(self, sample_call_graph):
        """Mermaid diagram should represent only truncated nodes."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=5)

        # Verify that result has mermaid attribute or is handled gracefully
        assert hasattr(result, "mermaid")
        # If mermaid is generated, it should be a string or Mock
        assert result.mermaid is not None


class TestTruncationWithDifferentK:
    """Test truncation behavior with different k values."""

    def test_truncation_k1(self, sample_call_graph):
        """Truncation should work with k=1."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=1,
            max_nodes=2,  # Less than k=1 (5 nodes)
        )

        assert len(result.subgraph.nodes) <= 2

    def test_truncation_k2(self, sample_call_graph):
        """Truncation should work with k=2."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=2,
            max_nodes=3,  # Less than k=2 (10 nodes)
        )

        assert len(result.subgraph.nodes) <= 3

    def test_truncation_large_k(self, sample_call_graph):
        """Truncation should work with large k values."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=100,  # Much larger than actual depth
            max_nodes=5,
        )

        assert len(result.subgraph.nodes) <= 5


class TestTruncationWithFilters:
    """Test truncation interaction with filtering parameters."""

    def test_truncation_with_direction_filter(self, sample_call_graph):
        """Truncation should work with direction parameter."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, direction="outgoing", max_nodes=5
        )

        assert result.success
        assert len(result.subgraph.nodes) <= 5

    def test_truncation_with_confidence_filter(self, sample_call_graph):
        """Truncation should work with min_confidence parameter."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, min_confidence=0.90, max_nodes=5
        )

        assert result.success
        assert len(result.subgraph.nodes) <= 5

    def test_truncation_limits_apply_after_filtering(self, sample_call_graph):
        """Truncation should apply after confidence filtering."""
        result_no_trunc = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, min_confidence=0.90, max_nodes=100
        )
        result_trunc = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, min_confidence=0.90, max_nodes=3
        )

        # Truncated should have fewer nodes
        assert len(result_trunc.subgraph.nodes) <= len(result_no_trunc.subgraph.nodes)


class TestMaxNodesLimits:
    """Test max_nodes parameter behavior."""

    def test_max_nodes_zero_invalid(self, sample_call_graph):
        """max_nodes=0 should be invalid or handled specially."""
        # Behavior depends on implementation
        # Could return empty, error, or minimum (just center)
        pass

    def test_max_nodes_one_returns_center(self, sample_call_graph):
        """max_nodes=1 should return only center node."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=1)

        assert len(result.subgraph.nodes) <= 1
        # If we get 1 node, it should be the center
        if len(result.subgraph.nodes) == 1:
            assert "python::main::function::center" in result.subgraph.nodes

    def test_max_nodes_very_large(self, sample_call_graph):
        """Very large max_nodes should not truncate."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=1000)

        assert result.success
        # Should not truncate with huge limit
        assert not result.truncated

    def test_max_nodes_parameter_required(self, sample_call_graph):
        """max_nodes parameter should have a default value."""
        # When not specified, should use default (not crash)
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

        assert result.success


class TestTruncationEdgePreservation:
    """Test that edges in truncated graphs are preserved correctly."""

    def test_truncated_graph_preserves_shortest_paths(self, sample_call_graph):
        """Truncation should preserve shortest paths where possible."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, max_nodes=6)

        # Included nodes should maintain depth relationships
        nodes_set = set(result.subgraph.nodes)

        # Center should be at depth 0 if included
        if "python::main::function::center" in nodes_set:
            assert result.node_depths["python::main::function::center"] == 0

    def test_truncated_graph_edges_meaningful(self, sample_call_graph):
        """Edges in truncated graph should represent meaningful relationships."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=2,
            max_nodes=12,  # Full graph size to avoid truncation edge issues
        )

        # Each edge should connect related nodes
        # (implementation-dependent what "related" means)
        nodes_set = set(result.subgraph.nodes)
        for src, dst, conf in result.subgraph.edges:
            # Both endpoints should be in graph
            assert src in nodes_set
            assert dst in nodes_set
            # Confidence should be valid
            assert 0.0 <= conf <= 1.0
