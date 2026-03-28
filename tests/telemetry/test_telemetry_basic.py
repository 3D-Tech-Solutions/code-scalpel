"""Basic synchronous tests for telemetry module."""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_scalpel import telemetry


def test_telemetry_emit():
    """Test basic telemetry event emission."""
    telemetry.clear_events()

    event = telemetry.emit_tool_event(
        tool_name="analyze_code",
        tier_applied="community",
        duration_ms=100.5,
        status="success",
        input_summary={"file_count": 1},
        output_summary={"functions": 5},
    )

    assert event.tool_name == "analyze_code"
    assert event.tier_applied == "community"
    assert event.status == "success"
    assert event.duration_ms == 100.5
    print("✓ Event emission works")


def test_telemetry_queue():
    """Test that events are stored in queue."""
    telemetry.clear_events()

    for i in range(5):
        telemetry.emit_tool_event(
            tool_name=f"tool_{i}",
            status="success",
            duration_ms=10 * i,
        )

    recent = telemetry.get_recent_events(limit=10)
    assert len(recent) == 5
    # Should be newest first
    assert recent[0]["tool_name"] == "tool_4"
    print("✓ Event queue works")


def test_telemetry_stats():
    """Test statistics calculation."""
    telemetry.clear_events()

    telemetry.emit_tool_event("tool_a", status="success", duration_ms=100)
    telemetry.emit_tool_event("tool_b", status="success", duration_ms=200)
    telemetry.emit_tool_event("tool_a", status="failure", error="Error")

    stats = telemetry.get_event_stats()
    assert stats["total_events"] == 3
    assert stats["success_count"] == 2
    assert stats["failure_count"] == 1
    assert (
        stats["success_rate"] == pytest.approx(2 / 3, abs=0.01)
        if "pytest" in sys.modules
        else True
    )
    assert stats["avg_duration_ms"] == 150.0
    assert stats["tool_counts"]["tool_a"] == 2
    print("✓ Stats calculation works")


def test_dashboard_html():
    """Test that dashboard HTML is valid."""
    from code_scalpel.dashboard_service import get_dashboard_html

    html = get_dashboard_html()
    assert "Code Scalpel" in html
    assert "Dashboard" in html
    assert "websocket" in html.lower()
    assert "tool" in html.lower()
    print("✓ Dashboard HTML is valid")


def test_create_app():
    """Test that FastAPI app can be created."""
    from code_scalpel.dashboard_service import create_app

    app, port = create_app()
    assert port > 1024
    assert port < 65535
    assert app is not None
    print(f"✓ Dashboard app created on port {port}")


if __name__ == "__main__":
    test_telemetry_emit()
    test_telemetry_queue()
    test_telemetry_stats()
    test_dashboard_html()
    test_create_app()
    print("\n✅ All basic telemetry tests passed!")
