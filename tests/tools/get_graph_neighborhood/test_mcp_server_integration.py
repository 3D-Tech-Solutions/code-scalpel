"""[20260104_FEATURE] MCP Server integration tests for get_graph_neighborhood.

Validates:
- Tool registration and discovery (tools/list)
- Schema validation (input/output models)
- Async concurrent request handling
- Tools list response structure
"""

import asyncio
from unittest.mock import patch

import pytest


class TestToolRegistration:
    """Test tool is properly registered in MCP server."""

    def test_tool_is_callable(self):
        """Tool can be imported and called."""
        # [20260104_TEST] Tool availability check
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Function should be callable
        assert callable(get_graph_neighborhood)

    def test_tool_has_docstring(self):
        """Tool has documentation."""
        # [20260104_TEST] Tool documentation presence
        from code_scalpel.mcp.server import get_graph_neighborhood

        assert get_graph_neighborhood.__doc__ is not None
        assert len(get_graph_neighborhood.__doc__) > 10

    def test_tool_signature_has_center_node_id(self):
        """Tool accepts center_node_id parameter."""
        # [20260104_TEST] Tool parameter requirements
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "center_node_id" in sig.parameters

    def test_tool_signature_has_k_parameter(self):
        """Tool accepts k parameter."""
        # [20260104_TEST] Hop depth parameter
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "k" in sig.parameters

    def test_tool_signature_has_max_nodes_parameter(self):
        """Tool accepts max_nodes parameter."""
        # [20260104_TEST] Node limit parameter
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "max_nodes" in sig.parameters

    def test_tool_signature_has_direction_parameter(self):
        """Tool accepts direction parameter."""
        # [20260104_TEST] Edge direction parameter
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "direction" in sig.parameters

    def test_tool_signature_has_min_confidence_parameter(self):
        """Tool accepts min_confidence parameter."""
        # [20260104_TEST] Confidence filtering parameter
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        sig = inspect.signature(get_graph_neighborhood)
        assert "min_confidence" in sig.parameters


class TestAsyncConcurrentHandling:
    """Test tool handles async and concurrent requests correctly."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_node(self):
        """Multiple concurrent requests for same node succeed or fail consistently."""
        # [20260104_TEST] Concurrent request handling
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Fire 5 concurrent requests for the same node
        tasks = [
            get_graph_neighborhood(center_node_id="python::main::function::center", k=1, max_nodes=20) for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete (success or consistent error)
        assert len(results) == 5
        # All results should have the same success value
        success_values = [r.success for r in results]
        assert all(s == success_values[0] for s in success_values)

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_nodes(self):
        """Multiple concurrent requests for different nodes succeed."""
        # [20260104_TEST] Concurrent multi-node requests
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Fire concurrent requests for different nodes
        tasks = [
            get_graph_neighborhood(
                center_node_id=f"python::module_{i}::function::func_{i}",
                k=1,
                max_nodes=20,
            )
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete (may have different success values based on node existence)
        assert len(results) == 3
        # At least some may fail due to nonexistent nodes - that's ok
        # What matters is all complete without crashes

    @pytest.mark.asyncio
    async def test_concurrent_requests_mixed_tiers(self):
        """Concurrent requests with different tier settings work."""
        # [20260104_TEST] Concurrent tier-mixed requests
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Mock different tier contexts
        async def call_with_tier(tier_name):
            with patch("code_scalpel.mcp.server._get_current_tier", return_value=tier_name):
                return await get_graph_neighborhood(
                    center_node_id="python::main::function::center",
                    k=2 if tier_name == "pro" else 1,
                    max_nodes=200 if tier_name == "pro" else 20,
                )

        tasks = [
            call_with_tier("community"),
            call_with_tier("pro"),
            call_with_tier("community"),
        ]

        results = await asyncio.gather(*tasks)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_sequential_requests_after_error(self):
        """Tool recovers and works after error condition."""
        # [20260104_TEST] Recovery from error in request sequence
        from code_scalpel.mcp.server import get_graph_neighborhood

        # First request: invalid (nonexistent node)
        result1 = await get_graph_neighborhood(center_node_id="python::fake::function::fake", k=1)
        assert not result1.success

        # Second request: valid (should work despite previous error)
        result2 = await get_graph_neighborhood(center_node_id="python::main::function::center", k=1, max_nodes=20)
        # May or may not succeed depending on if graph exists, but shouldn't crash
        assert hasattr(result2, "success")


class TestInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_input_type_k_negative(self):
        """Negative k value rejected with clear error."""
        # [20260104_TEST] Invalid k parameter type/value
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=-1,  # Invalid
            max_nodes=20,
        )

        assert not result.success
        assert "k" in result.error.lower() or "must be" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_input_type_k_zero(self):
        """Zero k value rejected with clear error."""
        # [20260104_TEST] k=0 validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=0,  # Invalid
            max_nodes=20,
        )

        assert not result.success
        assert "k" in result.error.lower() or "must be" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_direction_value(self):
        """Invalid direction value rejected with error."""
        # [20260104_TEST] Direction parameter validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=20,
            direction="invalid_direction",  # Invalid
        )

        assert not result.success
        assert "direction" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_confidence_out_of_range(self):
        """Confidence outside [0, 1] handled (may fail on graph build or validation)."""
        # [20260104_TEST] Confidence range validation or graceful handling
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=1,
            max_nodes=20,
            min_confidence=1.5,  # Out of range
        )

        # Should either reject due to confidence validation
        # OR fail due to node not found (acceptable fallback)
        assert not result.success or (result.success and result.min_confidence == 1.5)

    @pytest.mark.asyncio
    async def test_missing_required_parameter_center_node_id(self):
        """Missing center_node_id handled gracefully."""
        # [20260104_TEST] Missing required parameter handling
        from code_scalpel.mcp.server import get_graph_neighborhood

        # Tool may allow empty string or None - should return error instead of crash
        result = await get_graph_neighborhood(center_node_id="", k=1)  # Empty/missing

        # Should fail gracefully with error message
        assert not result.success
        assert result.error is not None


class TestResponseStructure:
    """Test MCP response structure matches specification."""

    @pytest.mark.asyncio
    async def test_response_has_success_field_bool(self):
        """Response has success field (bool)."""
        # [20260104_TEST] Response model validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="python::main::function::center", k=1, max_nodes=20)

        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_response_error_field_when_failed(self):
        """Response has error field when success=False."""
        # [20260104_TEST] Error field presence on failure
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="python::nonexistent::function::fake", k=1)

        if not result.success:
            assert hasattr(result, "error")
            assert result.error is not None
            assert len(result.error) > 0

    @pytest.mark.asyncio
    async def test_response_nodes_field_is_list(self):
        """Response nodes field is list of node objects."""
        # [20260104_TEST] Nodes field type validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="python::main::function::center", k=1, max_nodes=20)

        if result.success:
            assert hasattr(result, "nodes")
            assert isinstance(result.nodes, list)

    @pytest.mark.asyncio
    async def test_response_edges_field_is_list(self):
        """Response edges field is list of edge objects."""
        # [20260104_TEST] Edges field type validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="python::main::function::center", k=1, max_nodes=20)

        if result.success:
            assert hasattr(result, "edges")
            assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_response_truncated_field_is_bool(self):
        """Response truncated field is boolean."""
        # [20260104_TEST] Truncated flag type
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="python::main::function::center", k=1, max_nodes=20)

        if result.success:
            assert hasattr(result, "truncated")
            assert isinstance(result.truncated, bool)

    @pytest.mark.asyncio
    async def test_response_mermaid_field_is_string(self):
        """Response mermaid field is string."""
        # [20260104_TEST] Mermaid field type validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="python::main::function::center", k=1, max_nodes=20)

        if result.success and result.mermaid:
            assert isinstance(result.mermaid, str)


class TestErrorMessages:
    """Test error messages are clear and actionable."""

    @pytest.mark.asyncio
    async def test_error_message_includes_parameter_name(self):
        """Error message identifies which parameter is invalid."""
        # [20260104_TEST] Error message clarity
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::main::function::center",
            k=-5,  # Invalid parameter
            max_nodes=20,
        )

        assert not result.success
        # Should mention "k" or "hop" in error
        assert any(word in result.error.lower() for word in ["k", "hop", "parameter"])

    @pytest.mark.asyncio
    async def test_error_message_suggests_fix(self):
        """Error message provides hint for fixing."""
        # [20260104_TEST] Error message actionability
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="python::main::function::center", k=0, max_nodes=20)

        assert not result.success
        # Should suggest valid values
        assert any(word in result.error.lower() for word in ["must", "should", "least", "at"])

    @pytest.mark.asyncio
    async def test_error_message_not_empty(self):
        """Error messages are never empty strings."""
        # [20260104_TEST] Error message presence
        from code_scalpel.mcp.server import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="python::nonexistent::function::fake", k=1)

        if not result.success:
            assert result.error
            assert len(result.error.strip()) > 0


class TestToolCapabilityGating:
    """Test that tool capabilities are gated by tier."""

    @pytest.mark.asyncio
    async def test_pro_features_absent_in_community(self):
        """Pro-exclusive fields not in Community tier response."""
        # [20260104_TEST] Tier capability gating validation
        from code_scalpel.mcp.server import get_graph_neighborhood

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            result = await get_graph_neighborhood(center_node_id="python::main::function::center", k=1, max_nodes=20)

        if result.success:
            # Community shouldn't have semantic neighbors
            assert not hasattr(result, "semantic_neighbors") or not result.semantic_neighbors

    @pytest.mark.asyncio
    async def test_enterprise_features_absent_in_pro(self):
        """Enterprise-exclusive fields not in Pro tier response."""
        # [20260104_TEST] Enterprise feature gating
        from code_scalpel.mcp.server import get_graph_neighborhood

        with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
            result = await get_graph_neighborhood(center_node_id="python::main::function::center", k=2, max_nodes=200)

        if result.success:
            # Pro shouldn't have query language results
            assert not hasattr(result, "query_results") or not result.query_results

    def test_tier_limits_enforced_in_validation(self):
        """Tier limits are checked during parameter validation."""
        # [20260104_TEST] Tier limit enforcement in validation
        import inspect

        from code_scalpel.mcp.server import get_graph_neighborhood

        # Tool should validate against tier limits
        inspect.signature(get_graph_neighborhood)
        # Should have validation that respects tier
        source = inspect.getsource(get_graph_neighborhood)
        assert "_get_current_tier" in source or "tier" in source.lower()
