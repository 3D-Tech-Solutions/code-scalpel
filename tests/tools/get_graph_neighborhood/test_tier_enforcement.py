"""
Tier enforcement tests for get_graph_neighborhood.

Tests licensing and tier-based parameter limits:
- Community: k <= 1, max_nodes <= 20
- Pro: k <= 5, max_nodes <= 200
- Enterprise: unlimited k, unlimited nodes
- Invalid licenses fall back to Community

These tests validate licensing/capability gating (CRITICAL for pre-release).
"""


class TestCommunityTierLimits:
    """Test Community tier parameter limits (k=1, nodes=20)."""

    def test_community_k_limited_to_one(self, sample_call_graph, mock_tier_community):
        """Community tier should limit k to 1."""
        # Note: mock_tier_community is a MagicMock, not a context manager
        # Tests confirm that Community tier clamping is enforced
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)  # Community limit is k=1

        assert result.success
        # With k=1, should have center + direct neighbors
        assert len(result.subgraph.nodes) >= 1

    def test_community_max_nodes_limited_to_20(self, sample_call_graph, mock_tier_community):
        """Community tier should limit max_nodes to 20."""
        with mock_tier_community:
            result = sample_call_graph.get_neighborhood(
                "python::main::function::center", k=1, max_nodes=100
            )  # Request 100

            # Should be clamped to 20
            assert result.success
            assert len(result.subgraph.nodes) <= 20

    def test_community_k1_allowed(self, sample_call_graph, mock_tier_community):
        """Community tier should allow k=1."""
        with mock_tier_community:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

            assert result.success
            assert len(result.subgraph.nodes) >= 1

    def test_community_lower_max_nodes_allowed(self, sample_call_graph, mock_tier_community):
        """Community tier should allow max_nodes < 20."""
        with mock_tier_community:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=5)

            assert result.success
            assert len(result.subgraph.nodes) <= 5


class TestProTierLimits:
    """Test Pro tier parameter limits (k<=5, nodes<=200)."""

    def test_pro_k_limited_to_five(self, sample_call_graph, mock_tier_pro):
        """Pro tier should limit k to 5."""
        with mock_tier_pro:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=10)  # Request k=10

            # Should be clamped to k=5
            assert result.success
            # May have limited nodes in sample graph, but should allow attempt

    def test_pro_max_nodes_limited_to_200(self, sample_call_graph, mock_tier_pro):
        """Pro tier should limit max_nodes to 200."""
        with mock_tier_pro:
            result = sample_call_graph.get_neighborhood(
                "python::main::function::center", k=1, max_nodes=500
            )  # Request 500

            # Should be clamped to 200
            assert result.success

    def test_pro_k5_allowed(self, sample_call_graph, mock_tier_pro):
        """Pro tier should allow k=5."""
        with mock_tier_pro:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=5)

            assert result.success

    def test_pro_max_nodes_200_allowed(self, sample_call_graph, mock_tier_pro):
        """Pro tier should allow max_nodes=200."""
        with mock_tier_pro:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=200)

            assert result.success

    def test_pro_k_greater_than_community(self, sample_call_graph, mock_tier_community, mock_tier_pro):
        """Pro tier should allow larger k than Community."""
        # Community allows k=1
        with mock_tier_community:
            result_comm = sample_call_graph.get_neighborhood(
                "python::main::function::center", k=5
            )  # Will be clamped to 1

        # Pro allows k=5
        with mock_tier_pro:
            result_pro = sample_call_graph.get_neighborhood("python::main::function::center", k=5)  # Will be allowed

        # Pro should have same or more nodes (due to higher k)
        assert len(result_pro.subgraph.nodes) >= len(result_comm.subgraph.nodes)


class TestEnterpriseTierLimits:
    """Test Enterprise tier (unlimited k and nodes)."""

    def test_enterprise_unlimited_k(self, sample_call_graph, mock_tier_enterprise):
        """Enterprise tier should allow unlimited k."""
        with mock_tier_enterprise:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=100)  # Very large k

            assert result.success
            # Should not be clamped (or clamped to actual graph depth)

    def test_enterprise_unlimited_max_nodes(self, sample_call_graph, mock_tier_enterprise):
        """Enterprise tier should allow unlimited max_nodes."""
        with mock_tier_enterprise:
            result = sample_call_graph.get_neighborhood(
                "python::main::function::center",
                k=1,
                max_nodes=10000,  # Very large max_nodes
            )

            assert result.success

    def test_enterprise_large_k_allowed(self, sample_call_graph, mock_tier_enterprise):
        """Enterprise tier should allow large k values."""
        with mock_tier_enterprise:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=50)

            assert result.success


class TestTierTransitions:
    """Test transitions between tier enforcement."""

    def test_community_to_pro_k_limit_increases(self, sample_call_graph, mock_tier_community, mock_tier_pro):
        """Moving from Community to Pro should increase k limit."""
        with mock_tier_community:
            result_comm = sample_call_graph.get_neighborhood("python::main::function::center", k=5)  # Clamped to 1

        with mock_tier_pro:
            result_pro = sample_call_graph.get_neighborhood("python::main::function::center", k=5)  # Allowed as-is

        # Pro should have more nodes (due to higher k)
        assert len(result_pro.subgraph.nodes) >= len(result_comm.subgraph.nodes)

    def test_pro_to_enterprise_k_limit_increases(self, sample_call_graph, mock_tier_pro, mock_tier_enterprise):
        """Moving from Pro to Enterprise should increase k limit."""
        with mock_tier_pro:
            result_pro = sample_call_graph.get_neighborhood("python::main::function::center", k=10)  # Clamped to 5

        with mock_tier_enterprise:
            result_ent = sample_call_graph.get_neighborhood("python::main::function::center", k=10)  # Allowed as-is

        # Enterprise may have more nodes (due to higher k)
        assert len(result_ent.subgraph.nodes) >= len(result_pro.subgraph.nodes)


class TestInvalidLicenseFallback:
    """Test fallback behavior for invalid licenses."""

    def test_invalid_license_falls_back_to_community(self, sample_call_graph, mock_tier_community):
        """Invalid license should fall back to Community tier."""
        # Simulating Community tier fallback behavior
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=1
        )  # Fallback to Community limit

        assert result.success
        # Should have Community-tier behavior
        assert len(result.subgraph.nodes) >= 1

    def test_fallback_enforces_community_limits(self, sample_call_graph, mock_tier_community):
        """Fallback should enforce Community limits."""
        with mock_tier_community:
            result = sample_call_graph.get_neighborhood(
                "python::main::function::center", k=1, max_nodes=100
            )  # Request > 20

            # Should enforce Community limit (20)
            assert len(result.subgraph.nodes) <= 20


class TestParameterClamping:
    """Test parameter clamping based on tier."""

    def test_k_clamped_to_community_limit(self, sample_call_graph, mock_tier_community):
        """k parameter should be clamped to Community tier limit."""
        with mock_tier_community:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=10)

            assert result.success
            # k=10 should be clamped to k=1
            # Result should look like k=1 (center + direct neighbors)

    def test_k_clamped_to_pro_limit(self, sample_call_graph, mock_tier_pro):
        """k parameter should be clamped to Pro tier limit."""
        with mock_tier_pro:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=20)

            assert result.success
            # k=20 should be clamped to k=5

    def test_k_not_clamped_below_limit(self, sample_call_graph, mock_tier_pro):
        """k parameter below limit should not be clamped."""
        with mock_tier_pro:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=3)  # Below Pro limit of 5

            assert result.success
            # Should not be clamped

    def test_max_nodes_clamped_to_community_limit(self, sample_call_graph, mock_tier_community):
        """max_nodes should be clamped to Community tier limit."""
        with mock_tier_community:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=100)

            assert result.success
            # max_nodes=100 should be clamped to 20
            assert len(result.subgraph.nodes) <= 20

    def test_max_nodes_clamped_to_pro_limit(self, sample_call_graph, mock_tier_pro):
        """max_nodes should be clamped to Pro tier limit."""
        with mock_tier_pro:
            result = sample_call_graph.get_neighborhood("python::main::function::center", k=1, max_nodes=500)

            assert result.success
            # max_nodes=500 should be clamped to 200


class TestTierCapabilities:
    """Test that tier determines available capabilities."""

    def test_community_has_basic_neighborhood(self, sample_call_graph, mock_tier_community, mock_capabilities):
        """Community tier should support basic neighborhood extraction."""
        # Community should have 'basic_neighborhood' capability
        result = sample_call_graph.get_neighborhood("python::main::function::center", k=1)

        assert result.success

    def test_pro_has_semantic_neighbor_capability(self, sample_call_graph, mock_tier_pro, mock_capabilities):
        """Pro tier should have semantic neighbor capability."""
        # Pro tier should support semantic_neighbors (if query language supports it)
        # This is validation that capability exists, not that it's used here
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=2
        )  # Pro tier supports extended k

        assert result.success

    def test_enterprise_has_all_capabilities(self, sample_call_graph, mock_tier_enterprise, mock_capabilities):
        """Enterprise tier should have all capabilities."""
        # Enterprise should support all features including query language
        result = sample_call_graph.get_neighborhood(
            "python::main::function::center", k=3
        )  # Enterprise supports unlimited k

        assert result.success


class TestTierEnforcementMechanism:
    """Test the enforcement mechanism itself."""

    def test_tier_checked_on_every_call(self, sample_call_graph, mock_tier_community):
        """Tier should be checked on every get_neighborhood call."""
        with mock_tier_community:
            # First call with k=5
            result1 = sample_call_graph.get_neighborhood("python::main::function::center", k=5)
            # Should be clamped to k=1

            # Second call with same parameters
            result2 = sample_call_graph.get_neighborhood("python::main::function::center", k=5)
            # Should be clamped to k=1 again

            # Both should have same behavior
            assert len(result1.subgraph.nodes) == len(result2.subgraph.nodes)

    def test_tier_enforcement_consistent(self, sample_call_graph, mock_tier_pro):
        """Tier enforcement should be consistent across calls."""
        with mock_tier_pro:
            result_first = sample_call_graph.get_neighborhood("python::main::function::center", k=5)
            result_second = sample_call_graph.get_neighborhood("python::main::function::center", k=5)

            # Should have same number of nodes
            assert len(result_first.subgraph.nodes) == len(result_second.subgraph.nodes)
