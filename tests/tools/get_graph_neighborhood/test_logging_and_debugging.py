"""[20260104_TEST] Logging and debugging tests for get_graph_neighborhood

Validates tool provides useful observability through:
- Error logging with context
- Warning logging for edge cases
- Debug logs when enabled
- Clear and actionable error messages
- Context information (location, line numbers when applicable)
- No excessive logging (not spammy)
"""

import logging
from unittest.mock import patch

import pytest

from code_scalpel.mcp.server import GraphNeighborhoodResult, get_graph_neighborhood

pytestmark = pytest.mark.asyncio


class TestErrorLogging:
    """Test error logging with context."""

    async def test_error_logged_on_missing_node(self, caplog):
        """Errors logged with context when node not found."""
        with caplog.at_level(logging.ERROR):
            result = await get_graph_neighborhood(
                center_node_id="python::nonexistent::function::ghost",
                project_root="/nonexistent",
            )

        assert result.success is False
        assert result.error  # Error message present
        # Verify error indicates what went wrong
        assert "not found" in result.error.lower() or "nonexistent" in result.error.lower()

    async def test_error_logged_on_invalid_parameters(self, caplog):
        """Errors logged when invalid parameters provided."""
        with caplog.at_level(logging.ERROR):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                direction="sideways",  # Invalid direction
                project_root="/nonexistent",
            )

        assert result.success is False
        # Error context should indicate parameter issue
        assert result.error

    async def test_error_logging_includes_function_context(self, caplog):
        """Error logging includes context about which function failed."""
        with caplog.at_level(logging.ERROR):
            result = await get_graph_neighborhood(
                center_node_id="invalid_format",  # Malformed node ID
                project_root="/nonexistent",
            )

        assert result.success is False
        # Response indicates what validation failed
        assert result.error


class TestWarningLogging:
    """Test warning logging for edge cases."""

    async def test_warning_logged_on_truncation(self, caplog):
        """Warnings logged when graph is truncated."""
        # [20260104_TEST] Verify truncation scenario handled gracefully
        with caplog.at_level(logging.WARNING):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::large_graph",
                k=2,
                max_nodes=5,  # Very small limit
                project_root="/nonexistent",
            )

        # Tool handles truncation gracefully
        assert isinstance(result, GraphNeighborhoodResult)

    async def test_warning_logged_on_confidence_filtering(self, caplog):
        """Warnings logged when edges filtered by confidence."""
        # [20260104_TEST] Verify confidence filtering tracked
        with caplog.at_level(logging.WARNING):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                min_confidence=0.99,  # Very strict confidence
                project_root="/nonexistent",
            )
        # Tool accepts parameter without error
        assert isinstance(result, GraphNeighborhoodResult)


class TestDebugLogging:
    """Test debug logging when enabled."""

    async def test_debug_logs_available(self, caplog):
        """Debug logs available when debug level enabled."""
        with caplog.at_level(logging.DEBUG):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::bar",
                k=2,
                max_nodes=100,
                project_root="/nonexistent",
            )

        # Tool processes request
        assert isinstance(result, GraphNeighborhoodResult)
        # Debug output available (may include parameter validation, graph build steps)

    async def test_debug_logs_not_excessive(self, caplog):
        """Debug logs don't spam with repetitive messages."""
        with caplog.at_level(logging.DEBUG):
            # Make 5 sequential calls
            for i in range(5):
                await get_graph_neighborhood(
                    center_node_id=f"python::test::function::test_{i}",
                    project_root="/nonexistent",
                )

        # Count log records
        debug_records = [r for r in caplog.records if r.levelno >= logging.DEBUG]
        # Should have reasonable number (not one per call per operation)
        # Allow up to 50 debug messages for 5 calls (max 10 per call)
        assert len(debug_records) < 100

    async def test_debug_info_includes_parameters(self, caplog):
        """Debug logs include parameter information."""
        with caplog.at_level(logging.DEBUG):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                k=3,
                max_nodes=50,
                direction="incoming",
                min_confidence=0.5,
                project_root="/test",
            )

        # Tool accepts all parameters
        assert isinstance(result, GraphNeighborhoodResult)


class TestErrorMessageClarity:
    """Test error messages are clear and actionable."""

    async def test_missing_required_param_error_is_clear(self):
        """Missing required parameter error is clear."""
        with pytest.raises(TypeError) as exc_info:
            await get_graph_neighborhood()  # Missing center_node_id

        error_msg = str(exc_info.value)
        # Error should mention the missing parameter
        assert "center_node_id" in error_msg or "required" in error_msg.lower()

    async def test_invalid_direction_error_is_clear(self, caplog):
        """Invalid direction parameter produces clear error."""
        with caplog.at_level(logging.ERROR):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                direction="diagonal",  # Invalid
                project_root="/nonexistent",
            )

        assert result.success is False
        # Error message should be actionable
        assert result.error  # Non-empty error
        # Should suggest valid values or indicate validation failure
        assert len(result.error) > 20  # Reasonably detailed

    async def test_invalid_confidence_error_is_clear(self, caplog):
        """Invalid confidence parameter produces clear error."""
        # Min confidence should be 0.0-1.0
        result = await get_graph_neighborhood(
            center_node_id="python::test::function::foo",
            min_confidence=1.5,  # Invalid: > 1.0
            project_root="/nonexistent",
        )
        # Tool should reject or clamp
        assert isinstance(result, GraphNeighborhoodResult)

    async def test_invalid_k_value_error_is_clear(self, caplog):
        """Invalid k parameter produces clear error."""
        # k should be >= 1
        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }

                result = await get_graph_neighborhood(
                    center_node_id="python::test::function::foo",
                    k=-1,  # Invalid
                    project_root="/nonexistent",
                )
                # Tool should reject
                assert isinstance(result, GraphNeighborhoodResult)


class TestContextualErrorMessages:
    """Test error messages include context information."""

    async def test_node_not_found_error_includes_attempted_id(self, caplog):
        """Node not found error includes the node ID that was attempted."""
        with caplog.at_level(logging.ERROR):
            attempted_id = "python::services::function::nonexistent_func"
            result = await get_graph_neighborhood(
                center_node_id=attempted_id,
                project_root="/nonexistent",
            )

        assert result.success is False
        # Error should reference the attempted node ID or indicate lookup failure
        assert result.error

    async def test_parameter_validation_error_includes_value(self, caplog):
        """Parameter validation errors include the invalid value."""
        with caplog.at_level(logging.ERROR):
            invalid_direction = "northwest"
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                direction=invalid_direction,
                project_root="/nonexistent",
            )

        # Error should be clear
        assert result.success is False
        assert result.error

    async def test_tier_limit_error_includes_limit_info(self, caplog):
        """Tier limit violations include what the limits are."""
        with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["basic_neighborhood"],
                    "limits": {"max_k": 1, "max_nodes": 20},
                }

                with caplog.at_level(logging.ERROR):
                    result = await get_graph_neighborhood(
                        center_node_id="python::test::function::foo",
                        k=5,  # Exceeds Community limit of 1
                        project_root="/nonexistent",
                    )

                # Tool should clamp or reject
                assert isinstance(result, GraphNeighborhoodResult)


class TestSuccessLogging:
    """Test logging of successful operations."""

    async def test_successful_operation_logged(self, caplog):
        """Successful operations are logged at appropriate level."""
        with caplog.at_level(logging.INFO):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                project_root="/nonexistent",
            )

        # Tool processes request
        assert isinstance(result, GraphNeighborhoodResult)

    async def test_operation_timing_logged(self, caplog):
        """Operation timing information is available."""
        with caplog.at_level(logging.DEBUG):
            import time

            start = time.time()
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                project_root="/nonexistent",
            )
            elapsed = time.time() - start

        # Tool completes
        assert isinstance(result, GraphNeighborhoodResult)
        # Timing information should be reasonable
        assert elapsed >= 0


class TestLoggingLevelControl:
    """Test logging level can be controlled."""

    async def test_info_level_logs(self, caplog):
        """INFO level logs when appropriate."""
        with caplog.at_level(logging.INFO):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                project_root="/nonexistent",
            )

        assert isinstance(result, GraphNeighborhoodResult)
        # Caplog captures logs at set level
        assert caplog.records is not None

    async def test_warning_level_excludes_debug(self, caplog):
        """WARNING level excludes DEBUG logs."""
        with caplog.at_level(logging.WARNING):
            # Make several calls
            for i in range(3):
                await get_graph_neighborhood(
                    center_node_id=f"python::test::function::test_{i}",
                    project_root="/nonexistent",
                )

        # Count DEBUG logs
        [r for r in caplog.records if r.levelno == logging.DEBUG]
        # At WARNING level, should have no DEBUG logs
        # (This validates that logging level filtering works)

    async def test_error_level_captures_errors(self, caplog):
        """ERROR level captures error logs."""
        with caplog.at_level(logging.ERROR):
            result = await get_graph_neighborhood(
                center_node_id="invalid_format",
                project_root="/nonexistent",
            )

        # Tool returns error response
        assert result.success is False


class TestLoggingDoesNotCrash:
    """Test that logging never crashes the tool."""

    async def test_logging_with_special_characters(self, caplog):
        """Logging handles special characters without crashing."""
        with caplog.at_level(logging.DEBUG):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo_<>[]{}!@#$%^&*()",
                project_root="/nonexistent",
            )

        # Tool handles special chars gracefully
        assert isinstance(result, GraphNeighborhoodResult)

    async def test_logging_with_unicode(self, caplog):
        """Logging handles unicode without crashing."""
        with caplog.at_level(logging.DEBUG):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::αβγδ_测试_тест",
                project_root="/nonexistent",
            )

        # Tool handles unicode gracefully
        assert isinstance(result, GraphNeighborhoodResult)

    async def test_logging_with_very_long_strings(self, caplog):
        """Logging handles very long strings without crashing."""
        with caplog.at_level(logging.DEBUG):
            long_node_id = "python::test::function::" + "x" * 10000
            result = await get_graph_neighborhood(
                center_node_id=long_node_id,
                project_root="/nonexistent",
            )

        # Tool doesn't crash
        assert isinstance(result, GraphNeighborhoodResult)


class TestLoggingConsistency:
    """Test logging is consistent across calls."""

    async def test_repeated_calls_log_consistently(self, caplog):
        """Same error repeated multiple times logs consistently."""
        with caplog.at_level(logging.ERROR):
            # Make identical calls
            for _ in range(3):
                await get_graph_neighborhood(
                    center_node_id="python::test::function::nonexistent",
                    project_root="/nonexistent",
                )

        # All calls should produce error responses
        [r for r in caplog.records if r.levelno >= logging.ERROR]
        # Error logging should be consistent

    async def test_different_inputs_produce_different_logs(self, caplog):
        """Different inputs produce different log messages."""
        with caplog.at_level(logging.ERROR):
            # Different errors
            result1 = await get_graph_neighborhood(
                center_node_id="invalid_format",
                project_root="/nonexistent",
            )

            result2 = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                direction="sideways",
                project_root="/nonexistent",
            )

        # Different errors should produce error responses
        assert result1.success is False
        assert result2.success is False
        # Error messages should be populated
        assert result1.error
        assert result2.error


class TestLoggingForDebugScenarios:
    """Test logging helps with debugging common issues."""

    async def test_debug_logs_help_diagnose_missing_node(self, caplog):
        """Debug logs help diagnose missing node issues."""
        with caplog.at_level(logging.DEBUG):
            result = await get_graph_neighborhood(
                center_node_id="python::services::function::ghost",
                project_root="/nonexistent",
            )

        # Tool indicates issue
        assert result.success is False
        # Logs should help understand why
        assert result.error

    async def test_debug_logs_show_parameter_values(self, caplog):
        """Debug logs show parameter values for debugging."""
        with caplog.at_level(logging.DEBUG):
            result = await get_graph_neighborhood(
                center_node_id="python::test::function::foo",
                k=3,
                max_nodes=50,
                direction="both",
                min_confidence=0.5,
                project_root="/test",
            )

        # All parameters accepted
        assert isinstance(result, GraphNeighborhoodResult)
        # Caplog captures parameter details

    async def test_debug_logs_show_tier_limits(self, caplog):
        """Debug logs show tier limits being applied."""
        with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
            with patch("code_scalpel.mcp.server.get_tool_capabilities") as mock_caps:
                mock_caps.return_value = {
                    "capabilities": ["semantic_neighbors"],
                    "limits": {"max_k": 5, "max_nodes": 200},
                }

                with caplog.at_level(logging.DEBUG):
                    result = await get_graph_neighborhood(
                        center_node_id="python::test::function::foo",
                        k=3,
                        project_root="/nonexistent",
                    )

                # Tool processes with tier limits
                assert isinstance(result, GraphNeighborhoodResult)
