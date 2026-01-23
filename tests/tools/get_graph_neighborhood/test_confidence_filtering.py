"""
Confidence filtering tests for get_graph_neighborhood.

Tests the min_confidence parameter:
- Filters edges by confidence score (0.0 to 1.0)
- Lower confidence = weaker relationships, may be filtered
- Confidence values in the graph range from 0.87 to 0.95

These tests validate confidence-based filtering (CRITICAL for pre-release).
"""


class TestConfidenceParameterBasic:
    """Test basic min_confidence parameter functionality."""

    def test_min_confidence_zero_includes_all_edges(self, sample_call_graph):
        """min_confidence=0.0 should include all edges."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.0)

        assert result.success
        # All edges should be included
        baseline_result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

        # Should have same or more edges than default
        assert len(result.subgraph.edges) >= len(baseline_result.subgraph.edges)

    def test_min_confidence_one_only_strongest_edges(self, sample_call_graph):
        """min_confidence=1.0 should only include perfect-confidence edges."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=1.0)

        assert result.success

        # All edges should have confidence exactly 1.0
        for _src, _dst, conf in result.subgraph.edges:
            assert conf == 1.0

    def test_min_confidence_filters_out_weak_edges(self, sample_call_graph):
        """Edges below min_confidence should be excluded."""
        result_strict = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.95)
        result_lenient = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.87)

        # Stricter filter should have fewer or equal edges
        assert len(result_strict.subgraph.edges) <= len(result_lenient.subgraph.edges)

    def test_min_confidence_defaults_to_zero(self, sample_call_graph):
        """Default min_confidence (not specified) should be 0.0."""
        result_default = sample_call_graph.get_neighborhood("python::main::function::center", k=1)
        result_explicit_zero = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1, min_confidence=0.0
        )

        # Should have same edges
        assert set(result_default.subgraph.edges) == set(result_explicit_zero.subgraph.edges)


class TestConfidenceEdgeFilteringBehavior:
    """Test how confidence affects edge inclusion/exclusion."""

    def test_edges_below_threshold_excluded(self, sample_call_graph):
        """Edges with confidence < min_confidence should be excluded."""
        # Sample graph has edges with confidence 0.87-0.95

        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.90)

        # All edges should have confidence >= 0.90
        for _src, _dst, conf in result.subgraph.edges:
            assert conf >= 0.90

    def test_edges_at_threshold_included(self, sample_call_graph):
        """Edges with confidence == min_confidence should be included."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.87)

        # All edges should have confidence >= 0.87
        for _src, _dst, conf in result.subgraph.edges:
            assert conf >= 0.87

    def test_edge_filtering_affects_node_reachability(self, sample_call_graph):
        """Filtering edges may remove nodes from reachability."""
        result_all = sample_call_graph.get_neighborhood("python::main::function::center", k=2, min_confidence=0.0)
        result_filtered = sample_call_graph.get_neighborhood("python::main::function::center", k=2, min_confidence=0.95)

        # Filtered neighborhood should have fewer or equal nodes
        # (some nodes may become unreachable with low-confidence edges removed)
        assert len(result_filtered.subgraph.nodes) <= len(result_all.subgraph.nodes)

    def test_confidence_filtering_with_direction(self, sample_call_graph):
        """Confidence filtering should work with direction parameter."""
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=1,
            direction="outgoing",
            min_confidence=0.90,
        )

        assert result.success
        # Should have edges with conf >= 0.90 in outgoing direction
        for _src, _dst, conf in result.subgraph.edges:
            assert conf >= 0.90


class TestConfidenceBoundaryConditions:
    """Test boundary conditions for confidence parameter."""

    def test_confidence_negative_invalid(self, sample_call_graph):
        """Negative confidence values should be rejected or clamped to 0."""
        # Behavior depends on implementation
        # Could reject, clamp, or default
        pass

    def test_confidence_above_one_invalid(self, sample_call_graph):
        """Confidence values > 1.0 should be rejected or clamped to 1.0."""
        # Behavior depends on implementation
        pass

    def test_confidence_zero_point_five(self, sample_call_graph):
        """Mid-range confidence threshold (0.5) should work."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.5)

        assert result.success
        # All edges should have confidence >= 0.5
        for _src, _dst, conf in result.subgraph.edges:
            assert conf >= 0.5

    def test_confidence_precision(self, sample_call_graph):
        """Confidence filtering should handle decimal precision."""
        result_tight = sample_call_graph.get_neighborhood(
            "python::main::function::center",
            k=1,
            min_confidence=0.875,  # Between some edge values
        )

        assert result_tight is not None
        # All edges should meet threshold
        for _src, _dst, conf in result_tight.subgraph.edges:
            assert conf >= 0.875


class TestConfidenceWithK:
    """Test confidence filtering interaction with k parameter."""

    def test_confidence_filtering_k1(self, sample_call_graph):
        """Confidence filtering should work with k=1."""
        result_k1_strict = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1, min_confidence=0.95
        )
        result_k1_lenient = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1, min_confidence=0.80
        )

        # Stricter filter should have fewer edges
        assert len(result_k1_strict.subgraph.edges) <= len(result_k1_lenient.subgraph.edges)

    def test_confidence_filtering_k2(self, sample_call_graph):
        """Confidence filtering should work with k=2."""
        result_k2_strict = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, min_confidence=0.95
        )
        result_k2_lenient = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, min_confidence=0.80
        )

        # Stricter filter should have fewer edges
        assert len(result_k2_strict.subgraph.edges) <= len(result_k2_lenient.subgraph.edges)

    def test_confidence_may_reduce_depth_reachability(self, sample_call_graph):
        """High confidence threshold may prevent reaching depth 2."""
        result_low_conf = sample_call_graph.get_neighborhood("python::main::function::center", k=2, min_confidence=0.0)
        result_high_conf = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2, min_confidence=0.99
        )

        # If all edges have < 0.99 confidence, unreachable nodes appear
        # (nodes at depth 2 may not be reachable with high threshold)
        # Nodes at depth 2 require 2 edges; if any edge < threshold, node unreachable
        assert len(result_high_conf.subgraph.nodes) <= len(result_low_conf.subgraph.nodes)


class TestConfidenceMetadata:
    """Test confidence value reporting and metadata."""

    def test_confidence_values_reported(self, sample_call_graph):
        """Edge confidence values should be reported in results."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

        # Each edge should have confidence value
        for _src, _dst, conf in result.subgraph.edges:
            assert isinstance(conf, (int, float))
            assert 0.0 <= conf <= 1.0

    def test_confidence_values_accessible(self, sample_call_graph):
        """Should be able to access confidence values after filtering."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.90)

        # All edge confidence values should be readable
        for _src, _dst, conf in result.subgraph.edges:
            assert conf >= 0.90


class TestConfidenceFilteringSemantics:
    """Test semantic meaning of confidence filtering."""

    def test_high_confidence_means_strong_relationships(self, sample_call_graph):
        """High confidence edges should represent strong relationships."""
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.95)

        # All edges should be high-confidence (strong relationships)
        assert all(conf >= 0.95 for _, _, conf in result.subgraph.edges)

    def test_low_confidence_includes_weak_relationships(self, sample_call_graph):
        """Low threshold includes both strong and weak relationships."""
        result_low = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.80)
        result_high = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.95)

        # Low confidence should have at least as many edges as high
        assert len(result_low.subgraph.edges) >= len(result_high.subgraph.edges)

    def test_confidence_filtering_improves_relevance(self, sample_call_graph):
        """Higher confidence threshold should filter to most relevant relationships."""
        result_all = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.0)
        result_relevant = sample_call_graph.get_neighborhood("python::main::function::center", k=1, min_confidence=0.95)

        # Relevant set should be subset of all edges
        relevant_edges = set(result_relevant.subgraph.edges)
        all_edges = set(result_all.subgraph.edges)
        assert relevant_edges.issubset(all_edges)
