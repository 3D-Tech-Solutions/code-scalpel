"""Integration tests for MCP server with telemetry.

Tests that:
1. MCP server starts with dashboard
2. Dashboard boots and is accessible
3. Telemetry events are captured when tools run
4. Events appear in dashboard API
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def test_python_file():
    """Create a temporary Python file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def hello(name):
    '''Greet someone.'''
    print(f"Hello, {name}!")

class Greeter:
    def __init__(self, greeting="Hi"):
        self.greeting = greeting

    def greet(self, name):
        return f"{self.greeting}, {name}!"
""")
        return f.name


def test_dashboard_service_starts():
    """Test that dashboard service can be created and started."""
    from code_scalpel.dashboard_service import DashboardServer

    server = DashboardServer()
    port = server.start()

    assert port > 1024
    assert port < 65535

    # Give server time to start
    time.sleep(0.5)

    # Verify it's accessible
    import httpx
    try:
        response = httpx.get(f"http://127.0.0.1:{port}", timeout=2)
        assert response.status_code == 200
        assert "Code Scalpel" in response.text
    finally:
        server.stop()


def test_telemetry_emitted_for_analyze_code(test_python_file):
    """Test that analyze_code emits telemetry events."""
    from code_scalpel import telemetry
    from code_scalpel.mcp.tools.analyze import analyze_code
    from code_scalpel.mcp.protocol import set_current_tier

    telemetry.clear_events()
    set_current_tier("community")

    # Call analyze_code
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            analyze_code(file_path=test_python_file)
        )
    finally:
        loop.close()

    # Check that telemetry event was emitted
    events = telemetry.get_recent_events(limit=1)
    assert len(events) > 0, "No telemetry events found"

    event = events[0]
    assert event["tool_name"] == "analyze_code"
    assert event["status"] == "success"
    assert event["tier_applied"] in ["community", "pro", "enterprise"]
    assert event["duration_ms"] > 0
    assert "function_count" in event["output_summary"]
    assert "class_count" in event["output_summary"]


async def test_dashboard_api_returns_events():
    """Test that dashboard API endpoint returns emitted events."""
    from code_scalpel import telemetry
    from code_scalpel.dashboard_service import start_dashboard
    import httpx

    telemetry.clear_events()

    # Emit test event
    telemetry.emit_tool_event(
        tool_name="test_tool",
        tier_applied="community",
        duration_ms=50,
        status="success",
        output_summary={"test": "data"},
    )

    # Start dashboard
    dashboard_url = start_dashboard()
    await asyncio.sleep(0.5)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{dashboard_url}/api/events")
            assert response.status_code == 200

            data = response.json()
            assert "events" in data
            assert "stats" in data
            assert len(data["events"]) > 0
            assert data["events"][0]["tool_name"] == "test_tool"
    finally:
        from code_scalpel.dashboard_service import stop_dashboard
        stop_dashboard()


async def test_dashboard_shows_tier_and_license_status():
    """Test that dashboard license API returns tier info."""
    from code_scalpel.dashboard_service import start_dashboard
    from code_scalpel.mcp.server import CURRENT_TIER
    import httpx

    # Start dashboard
    dashboard_url = start_dashboard()
    await asyncio.sleep(0.5)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{dashboard_url}/api/license")
            assert response.status_code == 200

            data = response.json()
            assert "current_tier" in data
            assert "is_valid" in data
            assert data["current_tier"] in ["community", "pro", "enterprise"]
    finally:
        from code_scalpel.dashboard_service import stop_dashboard
        stop_dashboard()


def test_telemetry_stats_calculation():
    """Test that telemetry stats are calculated correctly."""
    from code_scalpel import telemetry

    telemetry.clear_events()

    # Emit multiple events
    telemetry.emit_tool_event("tool_a", status="success", duration_ms=100)
    telemetry.emit_tool_event("tool_b", status="success", duration_ms=200)
    telemetry.emit_tool_event("tool_a", status="failure", error="Test error")

    stats = telemetry.get_event_stats()
    assert stats["total_events"] == 3
    assert stats["success_count"] == 2
    assert stats["failure_count"] == 1
    assert stats["success_rate"] == pytest.approx(2 / 3, abs=0.01)
    assert stats["avg_duration_ms"] == 150.0
    assert stats["tool_counts"]["tool_a"] == 2
    assert stats["tool_counts"]["tool_b"] == 1


@pytest.mark.asyncio
async def test_analyze_code_with_dashboard_integration(test_python_file):
    """Integration test: analyze code, verify event in dashboard."""
    from code_scalpel import telemetry
    from code_scalpel.mcp.tools.analyze import analyze_code
    from code_scalpel.mcp.protocol import set_current_tier
    from code_scalpel.dashboard_service import start_dashboard
    import httpx

    telemetry.clear_events()
    set_current_tier("community")

    # Start dashboard
    dashboard_url = start_dashboard()
    await asyncio.sleep(0.5)

    try:
        # Call analyze_code
        result = await analyze_code(file_path=test_python_file)
        assert result is not None

        # Give telemetry time to broadcast
        await asyncio.sleep(0.1)

        # Query dashboard API
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{dashboard_url}/api/events")
            assert response.status_code == 200

            data = response.json()
            events = data["events"]

            assert len(events) > 0, "No events in dashboard"
            event = events[0]

            # Verify event details
            assert event["tool_name"] == "analyze_code"
            assert event["status"] == "success"
            assert event["tier_applied"] in ["community", "pro", "enterprise"]
            assert event["duration_ms"] > 0
            assert "function_count" in event["output_summary"]

            # Verify stats
            stats = data["stats"]
            assert stats["total_events"] > 0
            assert stats["success_rate"] > 0
            assert "analyze_code" in stats["tool_counts"]

    finally:
        from code_scalpel.dashboard_service import stop_dashboard
        stop_dashboard()


if __name__ == "__main__":
    # Run basic tests
    print("Running integration tests...\n")
    pytest.main([__file__, "-v"])
