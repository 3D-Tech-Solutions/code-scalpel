"""
[20251216_FEATURE] v2.2.0 - Tests for MCP structured logging and analytics.

This module tests the MCP logging infrastructure including:
- Tool invocation logging
- Success/failure tracking
- Analytics queries
- Error handling
"""

from datetime import datetime

import pytest

from code_scalpel.mcp.logging import (
    MCPAnalytics,
    ToolInvocation,
    _sanitize_params,
    get_analytics,
    log_tool_error,
    log_tool_invocation,
    log_tool_success,
)


class TestToolInvocation:
    """Test ToolInvocation dataclass."""

    def test_create_successful_invocation(self):
        """Create a successful tool invocation."""
        inv = ToolInvocation(
            tool_name="extract_code",
            timestamp=datetime.now(),
            duration_ms=150.5,
            success=True,
            metrics={"lines_extracted": 42, "tokens_saved": 1500},
        )

        assert inv.tool_name == "extract_code"
        assert inv.success is True
        assert inv.error_type is None
        assert inv.metrics["lines_extracted"] == 42

    def test_create_failed_invocation(self):
        """Create a failed tool invocation."""
        inv = ToolInvocation(
            tool_name="security_scan",
            timestamp=datetime.now(),
            duration_ms=50.0,
            success=False,
            error_type="ValueError",
            error_message="Invalid input",
        )

        assert inv.tool_name == "security_scan"
        assert inv.success is False
        assert inv.error_type == "ValueError"
        assert inv.error_message == "Invalid input"


class TestMCPAnalytics:
    """Test MCPAnalytics class."""

    def test_empty_analytics(self):
        """Test analytics with no invocations."""
        analytics = MCPAnalytics()
        stats = analytics.get_tool_usage_stats()

        assert stats["total_invocations"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["most_used_tools"] == []

    def test_record_single_invocation(self):
        """Record a single tool invocation."""
        analytics = MCPAnalytics()
        inv = ToolInvocation(
            tool_name="extract_code",
            timestamp=datetime.now(),
            duration_ms=100.0,
            success=True,
            metrics={"tokens_saved": 1000},
        )
        analytics.record_invocation(inv)

        stats = analytics.get_tool_usage_stats()
        assert stats["total_invocations"] == 1
        assert stats["success_rate"] == 1.0
        assert "extract_code" in stats["most_used_tools"]
        assert stats["tokens_saved_total"] == 1000

    def test_record_multiple_invocations(self):
        """Record multiple tool invocations."""
        analytics = MCPAnalytics()

        # Record 3 successful and 1 failed
        for _i in range(3):
            inv = ToolInvocation(
                tool_name="extract_code",
                timestamp=datetime.now(),
                duration_ms=100.0,
                success=True,
                metrics={"tokens_saved": 500},
            )
            analytics.record_invocation(inv)

        inv_failed = ToolInvocation(
            tool_name="security_scan",
            timestamp=datetime.now(),
            duration_ms=50.0,
            success=False,
            error_type="ValueError",
        )
        analytics.record_invocation(inv_failed)

        stats = analytics.get_tool_usage_stats()
        assert stats["total_invocations"] == 4
        assert stats["success_rate"] == 0.75
        assert stats["tokens_saved_total"] == 1500

    def test_most_used_tools(self):
        """Test most_used_tools calculation."""
        analytics = MCPAnalytics()

        # Record different tools with different frequencies
        tools = [
            ("extract_code", 5),
            ("security_scan", 3),
            ("analyze_code", 2),
        ]

        for tool_name, count in tools:
            for _ in range(count):
                inv = ToolInvocation(
                    tool_name=tool_name,
                    timestamp=datetime.now(),
                    duration_ms=100.0,
                    success=True,
                )
                analytics.record_invocation(inv)

        stats = analytics.get_tool_usage_stats()
        most_used = stats["most_used_tools"]

        # Should be ordered by usage
        assert most_used[0] == "extract_code"
        assert most_used[1] == "security_scan"
        assert most_used[2] == "analyze_code"

    def test_tool_specific_stats(self):
        """Test get_tool_stats for a specific tool."""
        analytics = MCPAnalytics()

        # Record 2 successful and 1 failed for same tool
        for _ in range(2):
            inv = ToolInvocation(
                tool_name="extract_code",
                timestamp=datetime.now(),
                duration_ms=100.0,
                success=True,
            )
            analytics.record_invocation(inv)

        inv_failed = ToolInvocation(
            tool_name="extract_code",
            timestamp=datetime.now(),
            duration_ms=50.0,
            success=False,
            error_type="FileNotFoundError",
            error_message="File not found",
        )
        analytics.record_invocation(inv_failed)

        tool_stats = analytics.get_tool_stats("extract_code")
        assert tool_stats["total_invocations"] == 3
        assert tool_stats["success_rate"] == pytest.approx(0.667, 0.01)
        assert len(tool_stats["failures"]) == 1
        assert tool_stats["failures"][0]["error_type"] == "FileNotFoundError"

    def test_error_summary(self):
        """Test get_error_summary."""
        analytics = MCPAnalytics()

        # Record mixed successes and failures
        inv_success = ToolInvocation(
            tool_name="extract_code",
            timestamp=datetime.now(),
            duration_ms=100.0,
            success=True,
        )
        analytics.record_invocation(inv_success)

        inv_error1 = ToolInvocation(
            tool_name="security_scan",
            timestamp=datetime.now(),
            duration_ms=50.0,
            success=False,
            error_type="ValueError",
            error_message="Invalid input",
        )
        analytics.record_invocation(inv_error1)

        inv_error2 = ToolInvocation(
            tool_name="extract_code",
            timestamp=datetime.now(),
            duration_ms=30.0,
            success=False,
            error_type="FileNotFoundError",
            error_message="File not found",
        )
        analytics.record_invocation(inv_error2)

        error_summary = analytics.get_error_summary()
        assert error_summary["total_errors"] == 2
        assert error_summary["error_rate"] == pytest.approx(0.667, 0.01)
        assert "ValueError" in error_summary["error_types"]
        assert "FileNotFoundError" in error_summary["error_types"]


class TestLoggingFunctions:
    """Test logging helper functions."""

    def test_log_tool_invocation(self):
        """Test log_tool_invocation function."""
        # Should not raise an error
        log_tool_invocation("extract_code", params={"file_path": "/test.py", "target_name": "MyClass"})

    def test_log_tool_success(self):
        """Test log_tool_success function."""
        # Should not raise an error
        log_tool_success(
            "extract_code",
            duration_ms=150.5,
            metrics={"lines_extracted": 42, "tokens_saved": 1500},
        )

        # Check analytics recorded it
        analytics = get_analytics()
        stats = analytics.get_tool_usage_stats()
        assert stats["total_invocations"] > 0

    def test_log_tool_error(self):
        """Test log_tool_error function."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_tool_error(
                "security_scan",
                error=e,
                duration_ms=50.0,
                params={"file_path": "/test.py"},
            )

        # Check analytics recorded it
        analytics = get_analytics()
        error_summary = analytics.get_error_summary()
        assert error_summary["total_errors"] > 0

    def test_sanitize_params(self):
        """Test parameter sanitization."""
        params = {
            "file_path": "/test.py",
            "api_key": "secret123",
            "password": "mypassword",
            "normal_param": "value",
            "long_string": "x" * 2000,
        }

        sanitized = _sanitize_params(params)

        # Sensitive params should be redacted
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["password"] == "***REDACTED***"

        # Normal params should be preserved
        assert sanitized["file_path"] == "/test.py"
        assert sanitized["normal_param"] == "value"

        # Long strings should be truncated
        assert "truncated" in sanitized["long_string"]
        assert len(sanitized["long_string"]) < 200


class TestIntegration:
    """Integration tests for MCP logging."""

    def test_full_workflow(self):
        """Test complete logging workflow."""
        analytics = MCPAnalytics()

        # Simulate tool invocation
        start_time = datetime.now()
        log_tool_invocation("extract_code", params={"file_path": "/test.py"})

        # Simulate success
        duration_ms = 150.0
        inv = ToolInvocation(
            tool_name="extract_code",
            timestamp=start_time,
            duration_ms=duration_ms,
            success=True,
            metrics={"lines_extracted": 42, "tokens_saved": 1500},
        )
        analytics.record_invocation(inv)

        # Check stats
        stats = analytics.get_tool_usage_stats()
        assert stats["total_invocations"] >= 1
        assert stats["success_rate"] > 0

    def test_multiple_tools_workflow(self):
        """Test logging multiple different tools."""
        analytics = MCPAnalytics()

        tools = ["extract_code", "security_scan", "analyze_code"]

        for tool in tools:
            inv = ToolInvocation(
                tool_name=tool,
                timestamp=datetime.now(),
                duration_ms=100.0,
                success=True,
            )
            analytics.record_invocation(inv)

        stats = analytics.get_tool_usage_stats()
        assert stats["total_invocations"] >= 3
        assert len(stats["tool_counts"]) >= 3
