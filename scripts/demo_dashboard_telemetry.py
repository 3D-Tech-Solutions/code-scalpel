#!/usr/bin/env python3
"""Demo script for Code Scalpel Dashboard Telemetry.

Shows the dashboard running with sample telemetry events.
Useful for testing the UI and verifying the telemetry pipeline works.

Usage:
    python scripts/demo_dashboard_telemetry.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_scalpel import telemetry
from code_scalpel.dashboard_service import start_dashboard, broadcast_event


async def emit_demo_events():
    """Emit sample telemetry events to demonstrate dashboard."""
    print("\n📊 Code Scalpel Dashboard Demo\n")

    # Start dashboard
    print("Starting dashboard service...")
    dashboard_url = start_dashboard()
    print(f"✓ Dashboard started: {dashboard_url}\n")

    # Emit sample events
    events = [
        {
            "tool_name": "analyze_code",
            "tier": "community",
            "duration": 145.5,
            "status": "success",
            "input": {"file_count": 1, "language": "python"},
            "output": {"functions": 5, "classes": 2},
        },
        {
            "tool_name": "security_scan",
            "tier": "pro",
            "duration": 234.2,
            "status": "success",
            "input": {"file_path": "src/app.py"},
            "output": {"vulnerabilities": 2, "severity": "medium"},
        },
        {
            "tool_name": "extract_code",
            "tier": "community",
            "duration": 89.3,
            "status": "success",
            "input": {"file_path": "src/utils.py", "target": "calculate_tax"},
            "output": {"lines": 25, "dependencies": 3},
        },
        {
            "tool_name": "symbolic_execute",
            "tier": "enterprise",
            "duration": 523.1,
            "status": "success",
            "input": {"file_path": "src/crypto.py"},
            "output": {"paths": 12, "edge_cases": 3},
        },
        {
            "tool_name": "get_call_graph",
            "tier": "pro",
            "duration": 312.4,
            "status": "success",
            "input": {"entry_point": "main", "depth": 5},
            "output": {"nodes": 47, "edges": 89},
        },
    ]

    print("Emitting sample telemetry events...\n")
    for i, event_data in enumerate(events, 1):
        print(f"  {i}. {event_data['tool_name']:20} ({event_data['status']:7}) "
              f"{event_data['duration']:7.1f}ms")

        # Emit the event
        event = telemetry.emit_tool_event(
            tool_name=event_data["tool_name"],
            tier_applied=event_data["tier"],
            duration_ms=event_data["duration"],
            status=event_data["status"],
            input_summary=event_data.get("input", {}),
            output_summary=event_data.get("output", {}),
        )

        # Broadcast to dashboard
        try:
            await broadcast_event(event.to_dict())
        except Exception as e:
            print(f"    (broadcast error: {e})")

        # Stagger events for better visual effect
        await asyncio.sleep(0.3)

    # Show stats
    print("\n✓ Sample events emitted\n")
    stats = telemetry.get_event_stats()
    print("Dashboard Statistics:")
    print(f"  Total Events: {stats['total_events']}")
    print(f"  Success Rate: {stats['success_rate']*100:.1f}%")
    print(f"  Avg Duration: {stats['avg_duration_ms']:.1f}ms")
    print(f"  Tools Used: {', '.join(stats['tool_counts'].keys())}\n")

    # Keep dashboard running
    print("=" * 70)
    print(f"Dashboard is running at: {dashboard_url}")
    print("=" * 70)
    print("\nOpen the dashboard URL in your browser to see the telemetry data.")
    print("Press Ctrl+C to stop the demo.\n")

    try:
        # Keep the dashboard running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n✓ Demo stopped")
        from code_scalpel.dashboard_service import stop_dashboard
        stop_dashboard()


if __name__ == "__main__":
    asyncio.run(emit_demo_events())
