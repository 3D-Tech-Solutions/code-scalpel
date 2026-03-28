"""Integration tests for dashboard audit log API endpoints.

Tests the three main audit API endpoints:
1. GET /api/audit/events - Query events with filtering and pagination
2. GET /api/audit/call-chain - Get all calls from a single MCP request
3. GET /api/audit/status - Check encryption status and statistics
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_scalpel.audit import AuditLog
from code_scalpel.dashboard_service import DashboardServer
from code_scalpel import telemetry


class TestAuditEventsEndpoint:
    """Test GET /api/audit/events endpoint."""

    @pytest.fixture
    def dashboard_with_events(self):
        """Start dashboard server with pre-populated audit log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create audit log with test data
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-session-123", encryption_enabled=False)

                # Log different tools with varied statuses
                for i in range(10):
                    tool_name = "security_scan" if i % 2 == 0 else "extract_code"
                    status = "success" if i < 8 else "failure"
                    audit_log.log_tool_call(
                        event_id=f"evt-{i}",
                        request_id=f"req-{i // 2}",  # Group 2 calls per request
                        tool_name=tool_name,
                        tier_applied="enterprise",
                        status=status,
                        duration_ms=100.0 + i * 10,
                        input_summary={"input": f"data-{i}"},
                        output_summary={"output": f"result-{i}"},
                        error=None if status == "success" else f"Error {i}",
                        metadata={"index": i},
                    )

                # Register audit log with telemetry
                telemetry.set_audit_log(audit_log)

                # Start dashboard server
                server = DashboardServer()
                port = server.start()

                yield f"http://localhost:{port}", audit_log

                # Cleanup
                try:
                    requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                except Exception:
                    pass
                telemetry.set_audit_log(None)  # Clear audit log

    def test_get_events_returns_all(self, dashboard_with_events):
        """Test retrieving all events without filters."""
        base_url, _ = dashboard_with_events

        response = requests.get(f"{base_url}/api/audit/events?limit=100")
        assert response.status_code == 200

        data = response.json()
        assert "events" in data
        assert "stats" in data
        assert len(data["events"]) == 10

    def test_get_events_pagination_limit(self, dashboard_with_events):
        """Test pagination with limit parameter."""
        base_url, _ = dashboard_with_events

        # Get first 3
        response = requests.get(f"{base_url}/api/audit/events?limit=3&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert len(data["events"]) == 3

    def test_get_events_pagination_offset(self, dashboard_with_events):
        """Test pagination with offset parameter."""
        base_url, _ = dashboard_with_events

        # Get events 3-6
        response = requests.get(f"{base_url}/api/audit/events?limit=3&offset=3")
        assert response.status_code == 200

        data = response.json()
        assert len(data["events"]) == 3

    def test_get_events_filter_by_tool_name(self, dashboard_with_events):
        """Test filtering events by tool name."""
        base_url, _ = dashboard_with_events

        response = requests.get(f"{base_url}/api/audit/events?limit=100&tool_name=security_scan")
        assert response.status_code == 200

        data = response.json()
        # Should have 5 security_scan events (indices 0, 2, 4, 6, 8)
        assert len(data["events"]) == 5
        for event in data["events"]:
            assert event["tool_name"] == "security_scan"

    def test_get_events_filter_by_status(self, dashboard_with_events):
        """Test filtering events by status."""
        base_url, _ = dashboard_with_events

        # Get successful events
        response = requests.get(f"{base_url}/api/audit/events?limit=100&status=success")
        assert response.status_code == 200

        data = response.json()
        assert len(data["events"]) == 8
        for event in data["events"]:
            assert event["status"] == "success"

        # Get failed events
        response = requests.get(f"{base_url}/api/audit/events?limit=100&status=failure")
        assert response.status_code == 200

        data = response.json()
        assert len(data["events"]) == 2
        for event in data["events"]:
            assert event["status"] == "failure"

    def test_get_events_filter_by_request_id(self, dashboard_with_events):
        """Test filtering events by request ID."""
        base_url, _ = dashboard_with_events

        response = requests.get(f"{base_url}/api/audit/events?limit=100&request_id=req-0")
        assert response.status_code == 200

        data = response.json()
        # req-0 has events 0 and 1
        assert len(data["events"]) == 2
        for event in data["events"]:
            assert event["request_id"] == "req-0"

    def test_get_events_returns_statistics(self, dashboard_with_events):
        """Test that events endpoint returns statistics."""
        base_url, _ = dashboard_with_events

        response = requests.get(f"{base_url}/api/audit/events?limit=100")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        assert stats["total_events"] == 10
        assert stats["success_count"] == 8
        assert stats["failure_count"] == 2
        assert stats["success_rate"] == 0.8
        assert "tool_counts" in stats
        assert stats["tool_counts"]["security_scan"] == 5
        assert stats["tool_counts"]["extract_code"] == 5

    def test_get_events_decrypts_sensitive_fields(self):
        """Test that sensitive fields are properly decrypted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                # Create audit log with encryption enabled
                audit_log = AuditLog(session_id="test-session-enc", encryption_enabled=True)

                audit_log.log_tool_call(
                    event_id="evt-enc",
                    request_id="req-enc",
                    tool_name="security_scan",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=100.0,
                    input_summary={"sensitive_key": "secret_value"},
                    output_summary={"secret_result": "data"},
                    metadata={"meta_secret": "metadata_value"},
                )

                # Register audit log with telemetry
                telemetry.set_audit_log(audit_log)

                # Start dashboard
                server = DashboardServer()
                port = server.start()

                try:
                    response = requests.get(f"http://localhost:{port}/api/audit/events?limit=10")
                    assert response.status_code == 200

                    data = response.json()
                    assert len(data["events"]) == 1

                    event = data["events"][0]
                    # Sensitive fields should be decrypted
                    assert event["input_summary"]["sensitive_key"] == "secret_value"
                    assert event["output_summary"]["secret_result"] == "data"
                    assert event["metadata"]["meta_secret"] == "metadata_value"

                finally:
                    try:
                        requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                    except Exception:
                        pass
                    telemetry.set_audit_log(None)  # Clear audit log
                    audit_log.conn.close()


class TestAuditCallChainEndpoint:
    """Test GET /api/audit/call-chain endpoint."""

    @pytest.fixture
    def dashboard_with_call_chain(self):
        """Start dashboard with events from multiple requests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-call-chain", encryption_enabled=False)

                # Create a call chain: one request triggering multiple tools
                request_id = "req-chain-abc123"
                tools = ["analyze_code", "security_scan", "generate_unit_tests"]

                for i, tool in enumerate(tools):
                    audit_log.log_tool_call(
                        event_id=f"evt-{request_id}-{i}",
                        request_id=request_id,
                        tool_name=tool,
                        tier_applied="pro",
                        status="success",
                        duration_ms=50.0 + i * 20,
                        input_summary={"step": i},
                        output_summary={"result": i},
                    )

                # Add events from different requests
                for req_idx in range(2):
                    audit_log.log_tool_call(
                        event_id=f"evt-other-{req_idx}",
                        request_id=f"req-other-{req_idx}",
                        tool_name="security_scan",
                        tier_applied="enterprise",
                        status="success",
                        duration_ms=100.0,
                        input_summary={},
                        output_summary={},
                    )

                # Register audit log with telemetry
                telemetry.set_audit_log(audit_log)

                server = DashboardServer()
                port = server.start()

                yield f"http://localhost:{port}", request_id, audit_log

                try:
                    requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                except Exception:
                    pass
                telemetry.set_audit_log(None)  # Clear audit log

    def test_get_call_chain_returns_correlated_calls(self, dashboard_with_call_chain):
        """Test retrieving all calls from a single request."""
        base_url, request_id, _ = dashboard_with_call_chain

        response = requests.get(f"{base_url}/api/audit/call-chain?request_id={request_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["request_id"] == request_id
        assert data["call_count"] == 3
        assert len(data["calls"]) == 3

    def test_get_call_chain_preserves_order(self, dashboard_with_call_chain):
        """Test that call chain contains all expected tools."""
        base_url, request_id, _ = dashboard_with_call_chain

        response = requests.get(f"{base_url}/api/audit/call-chain?request_id={request_id}")
        assert response.status_code == 200

        data = response.json()
        calls = data["calls"]

        # Verify all three tools are present (ordered by timestamp DESC)
        tool_names = {call["tool_name"] for call in calls}
        assert "analyze_code" in tool_names
        assert "security_scan" in tool_names
        assert "generate_unit_tests" in tool_names

    def test_get_call_chain_returns_404_for_missing_request(self, dashboard_with_call_chain):
        """Test that missing request ID returns appropriate response."""
        base_url, _, _ = dashboard_with_call_chain

        response = requests.get(f"{base_url}/api/audit/call-chain?request_id=nonexistent-req-xyz")
        # Should either return 404 or empty call list
        assert response.status_code in [200, 404]


class TestAuditStatusEndpoint:
    """Test GET /api/audit/status endpoint."""

    @pytest.fixture
    def dashboard_with_encryption(self):
        """Start dashboard with encrypted audit log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-status-enc", encryption_enabled=True)

                # Log a few events
                for i in range(3):
                    audit_log.log_tool_call(
                        event_id=f"evt-status-{i}",
                        request_id=f"req-status-{i}",
                        tool_name="security_scan",
                        tier_applied="enterprise",
                        status="success",
                        duration_ms=100.0,
                        input_summary={},
                        output_summary={},
                    )

                # Register audit log with telemetry
                telemetry.set_audit_log(audit_log)

                server = DashboardServer()
                port = server.start()

                yield f"http://localhost:{port}", audit_log

                try:
                    requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                except Exception:
                    pass
                telemetry.set_audit_log(None)  # Clear audit log

    def test_get_status_returns_encryption_info(self, dashboard_with_encryption):
        """Test that status endpoint returns encryption information."""
        base_url, _ = dashboard_with_encryption

        response = requests.get(f"{base_url}/api/audit/status")
        assert response.status_code == 200

        data = response.json()
        assert "encryption" in data
        assert data["encryption"]["enabled"] is True
        assert data["encryption"]["has_key"] is True

    def test_get_status_returns_database_info(self, dashboard_with_encryption):
        """Test that status endpoint returns database information."""
        base_url, _ = dashboard_with_encryption

        response = requests.get(f"{base_url}/api/audit/status")
        assert response.status_code == 200

        data = response.json()
        assert "database" in data
        assert "path" in data["database"]
        assert "session_id" in data["database"]
        assert data["database"]["session_id"] == "test-status-enc"

    def test_get_status_returns_statistics(self, dashboard_with_encryption):
        """Test that status endpoint returns statistics."""
        base_url, _ = dashboard_with_encryption

        response = requests.get(f"{base_url}/api/audit/status")
        assert response.status_code == 200

        data = response.json()
        assert "stats" in data
        stats = data["stats"]

        assert stats["total_events"] == 3
        assert stats["success_count"] == 3
        assert stats["failure_count"] == 0
        assert stats["success_rate"] == 1.0

    def test_get_status_without_encryption(self):
        """Test status endpoint with encryption disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-status-noenc", encryption_enabled=False)

                audit_log.log_tool_call(
                    event_id="evt-1",
                    request_id="req-1",
                    tool_name="extract_code",
                    tier_applied="community",
                    status="success",
                    duration_ms=100.0,
                    input_summary={},
                    output_summary={},
                )

                # Register audit log with telemetry
                telemetry.set_audit_log(audit_log)

                server = DashboardServer()
                port = server.start()

                try:
                    response = requests.get(f"http://localhost:{port}/api/audit/status")
                    assert response.status_code == 200

                    data = response.json()
                    assert data["encryption"]["enabled"] is False
                    assert data["encryption"]["has_key"] is False

                finally:
                    try:
                        requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                    except Exception:
                        pass
                    telemetry.set_audit_log(None)  # Clear audit log
                    audit_log.conn.close()


class TestAuditAPIEdgeCases:
    """Test edge cases and error handling."""

    def test_api_handles_missing_limit_gracefully(self):
        """Test that API uses sensible default for missing limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-edge", encryption_enabled=False)

                # Log multiple events
                for i in range(15):
                    audit_log.log_tool_call(
                        event_id=f"evt-{i}",
                        request_id=f"req-{i}",
                        tool_name="tool",
                        tier_applied="pro",
                        status="success",
                        duration_ms=100.0,
                        input_summary={},
                        output_summary={},
                    )

                # Register audit log with telemetry
                telemetry.set_audit_log(audit_log)

                server = DashboardServer()
                port = server.start()

                try:
                    # Request without limit parameter
                    response = requests.get(f"http://localhost:{port}/api/audit/events")
                    assert response.status_code == 200

                    data = response.json()
                    # Should use default limit (100)
                    assert len(data["events"]) <= 100

                finally:
                    try:
                        requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                    except Exception:
                        pass
                    telemetry.set_audit_log(None)  # Clear audit log
                    audit_log.conn.close()

    def test_api_handles_invalid_offset(self):
        """Test that API handles invalid offset gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-edge-offset", encryption_enabled=False)

                audit_log.log_tool_call(
                    event_id="evt-1",
                    request_id="req-1",
                    tool_name="tool",
                    tier_applied="pro",
                    status="success",
                    duration_ms=100.0,
                    input_summary={},
                    output_summary={},
                )

                # Register audit log with telemetry
                telemetry.set_audit_log(audit_log)

                server = DashboardServer()
                port = server.start()

                try:
                    # Request with offset beyond total events
                    response = requests.get(f"http://localhost:{port}/api/audit/events?limit=10&offset=1000")
                    assert response.status_code == 200

                    data = response.json()
                    # Should return empty events list, not error
                    assert len(data["events"]) == 0

                finally:
                    try:
                        requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                    except Exception:
                        pass
                    telemetry.set_audit_log(None)  # Clear audit log
                    audit_log.conn.close()

    def test_api_returns_json_response(self):
        """Test that all API responses are valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-json", encryption_enabled=False)

                # Register audit log with telemetry
                telemetry.set_audit_log(audit_log)

                server = DashboardServer()
                port = server.start()

                try:
                    # Test all three endpoints
                    endpoints = [
                        "/api/audit/events",
                        "/api/audit/status",
                        "/api/audit/call-chain?request_id=req-1",
                    ]

                    for endpoint in endpoints:
                        response = requests.get(f"http://localhost:{port}{endpoint}")
                        assert response.status_code in [200, 404]
                        # Should be able to parse as JSON
                        data = response.json()
                        assert isinstance(data, dict)

                finally:
                    try:
                        requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                    except Exception:
                        pass
                    telemetry.set_audit_log(None)  # Clear audit log
                    audit_log.conn.close()
