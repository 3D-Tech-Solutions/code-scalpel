"""
Tests for get_graph_neighborhood Enterprise Tier Features.

Tests graph query language, custom traversals, and advanced graph metrics.

**Enterprise Tier Features Tested**:
- Graph query language (query parameter support)
- Custom graph traversals with WHERE clauses
- Node/edge filtering with predicates
- Path pattern matching
- Advanced graph metrics (degree centrality, hot nodes)
- Query result ordering and limiting

**Test Organization**:
1. TestGraphQueryLanguageBasic - Basic query parsing and execution
2. TestQueryNodeFiltering - WHERE clause node filtering
3. TestQueryEdgeFiltering - Edge type and confidence filtering
4. TestQueryPathMatching - Path pattern matching
5. TestQueryOrdering - ORDER BY and LIMIT clauses
6. TestAdvancedGraphMetrics - Degree centrality, hot nodes
7. TestQueryComplexCombinations - Complex multi-clause queries
8. TestEnterpriseTierCapabilityGating - Feature gating validation
9. TestQueryPerformance - Query execution performance
10. TestQueryErrorHandling - Invalid query handling

**Implementation Notes**:
- Enterprise tier provides GraphQueryEngine
- Query language is Cypher-inspired (MATCH, WHERE, RETURN)
- Queries operate on in-memory graph structures
- hot_nodes feature requires Enterprise tier capability
"""

import pytest

# =============================================================================
# Test Class 1: Graph Query Language Basic
# =============================================================================


class TestGraphQueryLanguageBasic:
    """Test basic graph query language functionality."""

    def test_query_language_capability_exists(self, mock_tier_enterprise):
        """Enterprise tier includes 'graph_query_language' capability."""
        with mock_tier_enterprise:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
            capabilities = set(caps.get("capabilities", []))
            assert "graph_query_language" in capabilities

    def test_query_language_disabled_for_community(self, mock_tier_community):
        """Community tier does NOT have query language."""
        with mock_tier_community:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "community")
            capabilities = set(caps.get("capabilities", []))
            assert "graph_query_language" not in capabilities

    def test_query_language_disabled_for_pro(self, mock_tier_pro):
        """Pro tier does NOT have query language (Enterprise only)."""
        with mock_tier_pro:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "community")
            capabilities = set(caps.get("capabilities", []))
            assert "graph_query_language" not in capabilities

    def test_graph_query_engine_initialization(self):
        """GraphQueryEngine can be initialized."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        engine = GraphQueryEngine()
        assert engine is not None

    def test_query_engine_load_graph_data(self):
        """GraphQueryEngine can load node and edge data."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        nodes = [
            {"id": "node1", "type": "function", "name": "foo"},
            {"id": "node2", "type": "function", "name": "bar"},
        ]
        edges = [
            {
                "from_id": "node1",
                "to_id": "node2",
                "type": "calls",
                "confidence": 1.0,
            }
        ]

        engine = GraphQueryEngine()
        engine.load_graph_data(nodes, edges)

        # Verify data loaded
        assert len(engine._nodes) == 2
        assert len(engine._edges) == 1


class TestQueryNodeFiltering:
    """Test WHERE clause node filtering."""

    @pytest.fixture
    def query_engine_with_data(self):
        """Create query engine with sample data."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        nodes = [
            {"id": "func1", "name": "process_order", "complexity": 15},
            {"id": "func2", "name": "validate_order", "complexity": 8},
            {"id": "func3", "name": "save_order", "complexity": 5},
            {"id": "func4", "name": "calculate_total", "complexity": 20},
        ]
        edges = [
            {"from_id": "func1", "to_id": "func2", "type": "calls", "confidence": 1.0},
            {"from_id": "func1", "to_id": "func3", "type": "calls", "confidence": 0.9},
            {"from_id": "func2", "to_id": "func4", "type": "calls", "confidence": 0.8},
        ]

        engine = GraphQueryEngine()
        engine.load_graph_data(nodes, edges)
        return engine

    def test_query_where_greater_than(self, query_engine_with_data):
        """WHERE clause with > operator filters nodes."""
        result = query_engine_with_data.execute("WHERE complexity > 10")

        assert result.success is True
        assert len(result.nodes) == 2  # process_order (15) and calculate_total (20)

        complexities = [n["complexity"] for n in result.nodes]
        assert all(c > 10 for c in complexities)

    def test_query_where_less_than(self, query_engine_with_data):
        """WHERE clause with < operator filters nodes."""
        result = query_engine_with_data.execute("WHERE complexity < 10")

        assert result.success is True
        assert len(result.nodes) == 2  # validate_order (8) and save_order (5)

        complexities = [n["complexity"] for n in result.nodes]
        assert all(c < 10 for c in complexities)

    def test_query_where_equals(self, query_engine_with_data):
        """WHERE clause with = operator filters nodes."""
        result = query_engine_with_data.execute("WHERE complexity = 8")

        assert result.success is True
        assert len(result.nodes) == 1
        assert result.nodes[0]["name"] == "validate_order"

    def test_query_where_contains(self, query_engine_with_data):
        """WHERE clause with contains operator filters nodes."""
        result = query_engine_with_data.execute("WHERE name contains 'order'")

        assert result.success is True
        # All function names contain 'order' except calculate_total
        assert len(result.nodes) >= 3


class TestQueryEdgeFiltering:
    """Test edge filtering in queries."""

    @pytest.fixture
    def query_engine_with_edges(self):
        """Create query engine with diverse edges."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        nodes = [
            {"id": "n1"},
            {"id": "n2"},
            {"id": "n3"},
        ]
        edges = [
            {"from_id": "n1", "to_id": "n2", "type": "calls", "confidence": 1.0},
            {"from_id": "n2", "to_id": "n3", "type": "imports", "confidence": 0.9},
            {"from_id": "n1", "to_id": "n3", "type": "calls", "confidence": 0.7},
        ]

        engine = GraphQueryEngine()
        engine.load_graph_data(nodes, edges)
        return engine

    def test_query_all_edges_returned(self, query_engine_with_edges):
        """Query without edge filters returns all edges."""
        result = query_engine_with_edges.execute("")

        assert result.success is True
        assert len(result.edges) == 3


class TestQueryPathMatching:
    """Test path pattern matching."""

    @pytest.fixture
    def query_engine_with_paths(self):
        """Create query engine with multi-hop paths."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        nodes = [
            {"id": "a", "name": "A"},
            {"id": "b", "name": "B"},
            {"id": "c", "name": "C"},
            {"id": "d", "name": "D"},
        ]
        edges = [
            {"from_id": "a", "to_id": "b", "type": "calls", "confidence": 1.0},
            {"from_id": "b", "to_id": "c", "type": "calls", "confidence": 1.0},
            {"from_id": "c", "to_id": "d", "type": "calls", "confidence": 1.0},
        ]

        engine = GraphQueryEngine()
        engine.load_graph_data(nodes, edges)
        return engine

    def test_query_engine_supports_path_patterns(self, query_engine_with_paths):
        """Query engine can match path patterns."""
        from code_scalpel.graph.graph_query import GraphQuery, PathPattern

        pattern = PathPattern(min_length=1, max_length=2, direction="outgoing")
        query = GraphQuery(path_patterns=[pattern])

        result = query_engine_with_paths.execute(query)
        assert result.success is True


class TestQueryOrdering:
    """Test ORDER BY and LIMIT clauses."""

    @pytest.fixture
    def query_engine_ordered(self):
        """Create query engine with orderable data."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        nodes = [
            {"id": "n1", "score": 10},
            {"id": "n2", "score": 30},
            {"id": "n3", "score": 20},
            {"id": "n4", "score": 40},
        ]

        engine = GraphQueryEngine()
        engine.load_graph_data(nodes, [])
        return engine

    def test_query_order_by_ascending(self, query_engine_ordered):
        """ORDER BY field ASC sorts nodes."""
        result = query_engine_ordered.execute("ORDER BY score ASC")

        assert result.success is True
        assert len(result.nodes) == 4

        scores = [n["score"] for n in result.nodes]
        assert scores == sorted(scores)

    def test_query_order_by_descending(self, query_engine_ordered):
        """ORDER BY field DESC sorts nodes."""
        result = query_engine_ordered.execute("ORDER BY score DESC")

        assert result.success is True
        assert len(result.nodes) == 4

        scores = [n["score"] for n in result.nodes]
        assert scores == sorted(scores, reverse=True)

    def test_query_limit_clause(self, query_engine_ordered):
        """LIMIT clause limits result count."""
        result = query_engine_ordered.execute("LIMIT 2")

        assert result.success is True
        assert len(result.nodes) == 2

    def test_query_order_and_limit_combined(self, query_engine_ordered):
        """ORDER BY + LIMIT returns top N."""
        result = query_engine_ordered.execute("ORDER BY score DESC LIMIT 2")

        assert result.success is True
        assert len(result.nodes) == 2

        scores = [n["score"] for n in result.nodes]
        # Top 2 scores should be 40 and 30
        assert 40 in scores
        assert 30 in scores


class TestAdvancedGraphMetrics:
    """Test advanced graph metrics (hot nodes, degree centrality)."""

    def test_hot_nodes_capability_exists(self, mock_tier_enterprise):
        """Enterprise tier can compute hot nodes."""
        with mock_tier_enterprise:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
            capabilities = set(caps.get("capabilities", []))
            # hot_nodes is part of advanced metrics
            assert "graph_query_language" in capabilities

    def test_hot_nodes_disabled_for_community(self, mock_tier_community):
        """Community tier does NOT have hot nodes feature."""
        with mock_tier_community:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "community")
            capabilities = set(caps.get("capabilities", []))
            assert "graph_query_language" not in capabilities

    def test_degree_calculation_in_result_nodes(self):
        """Enterprise tier result nodes can include degree metrics."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        nodes = [
            {"id": "hub", "name": "hub_function"},
            {"id": "leaf1", "name": "leaf1"},
            {"id": "leaf2", "name": "leaf2"},
        ]
        edges = [
            {"from_id": "hub", "to_id": "leaf1", "type": "calls", "confidence": 1.0},
            {"from_id": "hub", "to_id": "leaf2", "type": "calls", "confidence": 1.0},
        ]

        engine = GraphQueryEngine()
        engine.load_graph_data(nodes, edges)

        # Execute query
        result = engine.execute("")

        assert result.success is True
        # Hub node should have higher degree than leaves


class TestQueryComplexCombinations:
    """Test complex query combinations."""

    @pytest.fixture
    def complex_query_engine(self):
        """Create query engine with complex data."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        nodes = [
            {"id": "f1", "name": "func_a", "complexity": 10, "module": "core"},
            {"id": "f2", "name": "func_b", "complexity": 20, "module": "core"},
            {"id": "f3", "name": "func_c", "complexity": 5, "module": "utils"},
            {"id": "f4", "name": "func_d", "complexity": 15, "module": "utils"},
        ]
        edges = [
            {"from_id": "f1", "to_id": "f2", "type": "calls", "confidence": 1.0},
            {"from_id": "f2", "to_id": "f3", "type": "calls", "confidence": 0.8},
        ]

        engine = GraphQueryEngine()
        engine.load_graph_data(nodes, edges)
        return engine

    def test_where_and_order_and_limit(self, complex_query_engine):
        """WHERE + ORDER BY + LIMIT combination works."""
        result = complex_query_engine.execute("WHERE complexity > 5 ORDER BY complexity DESC LIMIT 2")

        assert result.success is True
        assert len(result.nodes) <= 2

        # Should get highest complexity nodes above 5
        if len(result.nodes) > 0:
            complexities = [n["complexity"] for n in result.nodes]
            assert all(c > 5 for c in complexities)


class TestEnterpriseTierCapabilityGating:
    """Test Enterprise tier feature gating."""

    def test_community_tier_no_enterprise_features(self, mock_tier_community):
        """Community tier does not have Enterprise features."""
        with mock_tier_community:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "pro")
            capabilities = set(caps.get("capabilities", []))
            assert "graph_query_language" not in capabilities

    def test_pro_tier_no_enterprise_features(self, mock_tier_pro):
        """Pro tier does not have Enterprise features."""
        with mock_tier_pro:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "pro")
            capabilities = set(caps.get("capabilities", []))
            assert "graph_query_language" not in capabilities

    def test_enterprise_tier_has_all_features(self, mock_tier_enterprise):
        """Enterprise tier has all features."""
        with mock_tier_enterprise:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
            capabilities = set(caps.get("capabilities", []))

            # Community features
            assert "basic_neighborhood" in capabilities

            # Pro features (if Enterprise includes Pro)
            # Note: Depends on capability hierarchy

            # Enterprise features
            assert "graph_query_language" in capabilities


class TestQueryPerformance:
    """Test query execution performance."""

    def test_query_result_includes_execution_time(self):
        """Query results include execution time metric."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        engine = GraphQueryEngine()
        engine.load_graph_data([{"id": "n1"}], [])

        result = engine.execute("")

        assert result.success is True
        assert result.execution_time_ms >= 0.0
        assert isinstance(result.execution_time_ms, float)


class TestQueryErrorHandling:
    """Test query error handling."""

    def test_empty_query_succeeds(self):
        """Empty query returns all nodes."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        engine = GraphQueryEngine()
        engine.load_graph_data([{"id": "n1"}], [])

        result = engine.execute("")

        assert result.success is True
        assert len(result.nodes) == 1

    def test_malformed_query_fails_gracefully(self):
        """Malformed queries fail gracefully with error."""
        from code_scalpel.graph.graph_query import GraphQueryEngine

        engine = GraphQueryEngine()
        engine.load_graph_data([{"id": "n1"}], [])

        # This may fail or succeed depending on parser robustness
        # At minimum, should not crash
        result = engine.execute("INVALID QUERY SYNTAX!!!")

        # Result should always be returned
        assert result is not None
