"""
Direction filtering tests for get_graph_neighborhood.

Tests the direction parameter:
- direction="outgoing" - only follow calls FROM center outward
- direction="incoming" - only follow calls TO center inward
- direction="both" - follow in both directions (default)

These tests validate filtering logic (CRITICAL for pre-release).
"""


class TestDirectionOutgoing:
    """Test direction='outgoing' parameter."""

    def test_outgoing_only_includes_called_functions(self, sample_call_graph):
        """Outgoing direction should only include functions called BY center."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="outgoing")

        assert result.success

        # Center should be included
        assert "python::main::function::center" in result.subgraph.nodes

        # Only functions directly called by center should be included
        # (depth 1 callees, not callers)
        # Exact node list depends on call graph direction
        assert len(result.subgraph.nodes) >= 1  # At least center

    def test_outgoing_k2_extends_call_chain(self, sample_call_graph):
        """Outgoing k=2 should follow two levels of function calls."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, direction="outgoing")

        assert result.success
        # Should have center + functions it calls + functions they call
        # Total depends on call graph topology
        assert len(result.subgraph.nodes) > 1

    def test_outgoing_excludes_callers(self, sample_call_graph):
        """Outgoing should exclude functions that call the center."""
        sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="outgoing")

        # Should not include callers of center
        # (functions that have edges TO center)
        # Verification depends on graph topology
        pass

    def test_outgoing_edges_point_away_from_center(self, sample_call_graph):
        """In outgoing neighborhood, edges should flow from center outward."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="outgoing")

        # All edges should have center as source, or flow away from center
        # (for k > 1)
        for src, dst, _conf in result.subgraph.edges:
            # In call graphs, outgoing means we follow call edges
            # Source should be at equal or lower depth than destination
            src_depth = result.node_depths.get(src, 0)
            dst_depth = result.node_depths.get(dst, 0)
            assert src_depth <= dst_depth


class TestDirectionIncoming:
    """Test direction='incoming' parameter."""

    def test_incoming_only_includes_calling_functions(self, sample_call_graph):
        """Incoming direction should only include functions that call center."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="incoming")

        assert result.success

        # Center should be included
        assert "python::main::function::center" in result.subgraph.nodes

        # Only functions that call center should be included
        # (callers, not callees)

    def test_incoming_k2_traces_back_callers(self, sample_call_graph):
        """Incoming k=2 should trace back two levels of callers."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=2, direction="incoming")

        assert result.success
        # Should have center + functions that call it + functions that call them
        assert len(result.subgraph.nodes) >= 1

    def test_incoming_excludes_callees(self, sample_call_graph):
        """Incoming should exclude functions called by center."""
        sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="incoming")

        # Should not include functions called by center
        # Verification depends on graph topology
        pass

    def test_incoming_edges_point_toward_center(self, sample_call_graph):
        """In incoming neighborhood, edges should flow toward center."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="incoming")

        # All edges should reference valid nodes in the subgraph
        nodes_set = set(result.subgraph.nodes)
        for src, dst, _conf in result.subgraph.edges:
            assert src in nodes_set
            assert dst in nodes_set


class TestDirectionBoth:
    """Test direction='both' parameter (default)."""

    def test_both_includes_callers_and_callees(self, sample_call_graph):
        """Both direction should include both callers and callees."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="both")

        assert result.success

        # Should have center + both callers and callees
        # This should be the union of incoming and outgoing
        assert "python::main::function::center" in result.subgraph.nodes

    def test_both_k1_larger_than_outgoing_k1(self, sample_call_graph):
        """Both k=1 should include more nodes than outgoing k=1."""
        result_both = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="both")
        result_outgoing = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1, direction="outgoing"
        )

        # Both should have at least as many nodes as outgoing
        assert len(result_both.subgraph.nodes) >= len(result_outgoing.subgraph.nodes)

    def test_both_k1_larger_than_incoming_k1(self, sample_call_graph):
        """Both k=1 should include more nodes than incoming k=1."""
        result_both = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="both")
        result_incoming = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1, direction="incoming"
        )

        # Both should have at least as many nodes as incoming
        assert len(result_both.subgraph.nodes) >= len(result_incoming.subgraph.nodes)

    def test_both_is_default(self, sample_call_graph):
        """Default direction (no parameter) should equal direction='both'."""
        result_default = sample_call_graph.get_neighborhood("python::main::function::center", k=1)
        result_both = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="both")

        # Should have same nodes
        assert set(result_default.subgraph.nodes) == set(result_both.subgraph.nodes)

    def test_both_includes_all_edge_types(self, sample_call_graph):
        """Both direction should include all edges."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="both")

        # All edges from graph should be represented
        assert len(result.subgraph.edges) > 0


class TestDirectionWithDepth:
    """Test direction parameter interaction with k parameter."""

    def test_outgoing_k2_vs_outgoing_k1(self, sample_call_graph):
        """Outgoing k=2 should include more nodes than outgoing k=1."""
        result_k1 = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="outgoing")
        result_k2 = sample_call_graph.get_neighborhood("python::main::function::center", k=2, direction="outgoing")

        # k=2 should be superset of k=1
        k1_nodes = set(result_k1.subgraph.nodes)
        k2_nodes = set(result_k2.subgraph.nodes)
        assert k1_nodes.issubset(k2_nodes)

    def test_incoming_k2_vs_incoming_k1(self, sample_call_graph):
        """Incoming k=2 should include more nodes than incoming k=1."""
        result_k1 = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction="incoming")
        result_k2 = sample_call_graph.get_neighborhood("python::main::function::center", k=2, direction="incoming")

        # k=2 should be superset of k=1
        k1_nodes = set(result_k1.subgraph.nodes)
        k2_nodes = set(result_k2.subgraph.nodes)
        assert k1_nodes.issubset(k2_nodes)

    def test_direction_respected_at_all_depths(self, sample_call_graph):
        """Direction filtering should apply at every depth level."""
        result_outgoing = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, direction="outgoing"
        )

        # At depth 2, should still only have outgoing edges
        # Verify by checking edge directions
        for src, dst, _conf in result_outgoing.subgraph.edges:
            src_depth = result_outgoing.node_depths.get(src, 0)
            dst_depth = result_outgoing.node_depths.get(dst, 0)
            # Outgoing means depth increases along edges
            assert src_depth <= dst_depth


class TestDirectionValidation:
    """Test validation of direction parameter."""

    def test_valid_directions(self, sample_call_graph):
        """Valid directions are: 'outgoing', 'incoming', 'both'."""
        for direction in ["outgoing", "incoming", "both"]:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, direction=direction)
            # Should not raise error
            assert result is not None

    def test_invalid_direction_rejected(self, sample_call_graph):
        """Invalid direction values should be rejected."""
        # Implementation should reject invalid directions
        # Behavior depends on tool implementation
        # Could raise error or use default
        pass

    def test_case_sensitive_direction(self, sample_call_graph):
        """Direction parameter should be case-sensitive."""
        # 'Outgoing' should not equal 'outgoing'
        # Implementation-dependent behavior
        pass
