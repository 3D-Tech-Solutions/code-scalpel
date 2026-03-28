"""Unit tests for the audit logging system.

Tests cover:
- AuditLog initialization and encryption setup
- Logging tool calls with encryption
- Querying events with filtering
- Statistics calculation
- JSONL export
- Decryption on retrieval
"""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_scalpel.audit import AuditLog


class TestAuditLogInitialization:
    """Test AuditLog initialization and setup."""

    def test_audit_log_creates_database(self):
        """Test that AuditLog creates a database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "test-session-123"

            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id=session_id, encryption_enabled=True)

                # Check that database file was created
                assert audit_log.db_path.exists()
                assert "test-session-123" in str(audit_log.db_path)

                audit_log.conn.close()

    def test_encryption_initialized_when_enabled(self):
        """Test that encryption is initialized when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=True)

                assert audit_log.encryption.enabled is True
                assert audit_log.encryption.key is not None
                assert audit_log.encryption.cipher is not None
                assert len(audit_log.encryption.key) == 44  # Fernet key length

                audit_log.conn.close()

    def test_encryption_disabled_when_requested(self):
        """Test that encryption can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                assert audit_log.encryption.enabled is False
                assert audit_log.encryption.key is None
                assert audit_log.encryption.cipher is None

                audit_log.conn.close()

    def test_database_schema_created(self):
        """Test that database schema is properly created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                # Check that tables exist
                cursor = audit_log.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = {row[0] for row in cursor.fetchall()}
                assert "tool_calls" in tables

                audit_log.conn.close()


class TestAuditLogLogging:
    """Test logging tool calls to audit log."""

    def test_log_tool_call_success(self):
        """Test logging a successful tool call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                audit_log.log_tool_call(
                    event_id="evt-123",
                    request_id="req-123",
                    tool_name="security_scan",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=145.5,
                    input_summary={"code_length": 1024},
                    output_summary={"vulnerabilities": 3},
                    error=None,
                    metadata={"language": "python"},
                )

                # Verify event was logged
                event = audit_log.get_event("evt-123")
                assert event is not None
                assert event["tool_name"] == "security_scan"
                assert event["status"] == "success"
                assert event["duration_ms"] == 145.5
                assert event["input_summary"]["code_length"] == 1024
                assert event["output_summary"]["vulnerabilities"] == 3

                audit_log.conn.close()

    def test_log_tool_call_with_encryption(self):
        """Test logging with encryption enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=True)

                audit_log.log_tool_call(
                    event_id="evt-456",
                    request_id="req-456",
                    tool_name="extract_code",
                    tier_applied="pro",
                    status="success",
                    duration_ms=234.0,
                    input_summary={"file_path": "/path/to/file.py"},
                    output_summary={"lines": 42},
                    metadata={"language": "python"},
                )

                # Verify event was encrypted in database
                cursor = audit_log.conn.execute(
                    "SELECT encrypted FROM tool_calls WHERE event_id = ?",
                    ("evt-456",),
                )
                encrypted_flag = cursor.fetchone()[0]
                assert encrypted_flag == 1  # Should be encrypted

                # Verify decryption works
                event = audit_log.get_event("evt-456")
                assert event is not None
                assert event["input_summary"]["file_path"] == "/path/to/file.py"
                assert event["output_summary"]["lines"] == 42

                audit_log.conn.close()

    def test_log_tool_call_with_error(self):
        """Test logging a failed tool call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                audit_log.log_tool_call(
                    event_id="evt-error",
                    request_id="req-error",
                    tool_name="analyze_code",
                    tier_applied="community",
                    status="failure",
                    duration_ms=50.0,
                    input_summary={"code_provided": False},
                    output_summary={},
                    error="Invalid argument: code required",
                    metadata={},
                )

                event = audit_log.get_event("evt-error")
                assert event is not None
                assert event["status"] == "failure"
                assert event["error"] == "Invalid argument: code required"

                audit_log.conn.close()


class TestAuditLogQueries:
    """Test querying audit log with filtering."""

    def test_get_events_all(self):
        """Test retrieving all events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                # Log multiple events
                for i in range(5):
                    audit_log.log_tool_call(
                        event_id=f"evt-{i}",
                        request_id=f"req-{i}",
                        tool_name="security_scan" if i % 2 == 0 else "extract_code",
                        tier_applied="enterprise",
                        status="success",
                        duration_ms=100.0 + i,
                        input_summary={},
                        output_summary={},
                    )

                events = audit_log.get_events(limit=10)
                assert len(events) == 5

                audit_log.conn.close()

    def test_get_events_with_limit_and_offset(self):
        """Test pagination with limit and offset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                # Log 10 events
                for i in range(10):
                    audit_log.log_tool_call(
                        event_id=f"evt-{i}",
                        request_id=f"req-{i}",
                        tool_name="security_scan",
                        tier_applied="enterprise",
                        status="success",
                        duration_ms=100.0,
                        input_summary={},
                        output_summary={},
                    )

                # Get first 3
                events = audit_log.get_events(limit=3, offset=0)
                assert len(events) == 3

                # Get next 3
                events = audit_log.get_events(limit=3, offset=3)
                assert len(events) == 3

                audit_log.conn.close()

    def test_get_events_filter_by_tool_name(self):
        """Test filtering by tool name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                # Log different tools
                audit_log.log_tool_call(
                    event_id="evt-1",
                    request_id="req-1",
                    tool_name="security_scan",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=100.0,
                    input_summary={},
                    output_summary={},
                )

                audit_log.log_tool_call(
                    event_id="evt-2",
                    request_id="req-2",
                    tool_name="extract_code",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=150.0,
                    input_summary={},
                    output_summary={},
                )

                # Filter by tool name
                events = audit_log.get_events(tool_name="security_scan")
                assert len(events) == 1
                assert events[0]["tool_name"] == "security_scan"

                audit_log.conn.close()

    def test_get_events_filter_by_status(self):
        """Test filtering by status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                # Log success and failure
                audit_log.log_tool_call(
                    event_id="evt-1",
                    request_id="req-1",
                    tool_name="tool1",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=100.0,
                    input_summary={},
                    output_summary={},
                )

                audit_log.log_tool_call(
                    event_id="evt-2",
                    request_id="req-2",
                    tool_name="tool2",
                    tier_applied="enterprise",
                    status="failure",
                    duration_ms=50.0,
                    input_summary={},
                    output_summary={},
                    error="Something went wrong",
                )

                # Filter by status
                success_events = audit_log.get_events(status="success")
                assert len(success_events) == 1
                assert success_events[0]["status"] == "success"

                failure_events = audit_log.get_events(status="failure")
                assert len(failure_events) == 1
                assert failure_events[0]["status"] == "failure"

                audit_log.conn.close()

    def test_get_events_filter_by_request_id(self):
        """Test filtering by request ID (call chain)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                # Log multiple calls from same request
                request_id = "req-chain-123"
                for i in range(3):
                    audit_log.log_tool_call(
                        event_id=f"evt-{i}",
                        request_id=request_id,
                        tool_name=f"tool-{i}",
                        tier_applied="enterprise",
                        status="success",
                        duration_ms=100.0,
                        input_summary={},
                        output_summary={},
                    )

                # Log calls from different request
                audit_log.log_tool_call(
                    event_id="evt-other",
                    request_id="req-other-123",
                    tool_name="tool-other",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=100.0,
                    input_summary={},
                    output_summary={},
                )

                # Get call chain
                events = audit_log.get_events(request_id=request_id)
                assert len(events) == 3
                for event in events:
                    assert event["request_id"] == request_id

                audit_log.conn.close()


class TestAuditLogStatistics:
    """Test audit log statistics."""

    def test_get_stats(self):
        """Test getting audit log statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                # Log mixed results
                audit_log.log_tool_call(
                    event_id="evt-1",
                    request_id="req-1",
                    tool_name="security_scan",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=100.0,
                    input_summary={},
                    output_summary={},
                )

                audit_log.log_tool_call(
                    event_id="evt-2",
                    request_id="req-2",
                    tool_name="extract_code",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=150.0,
                    input_summary={},
                    output_summary={},
                )

                audit_log.log_tool_call(
                    event_id="evt-3",
                    request_id="req-3",
                    tool_name="security_scan",
                    tier_applied="enterprise",
                    status="failure",
                    duration_ms=50.0,
                    input_summary={},
                    output_summary={},
                    error="Error",
                )

                stats = audit_log.get_stats()

                assert stats["total_events"] == 3
                assert stats["success_count"] == 2
                assert stats["failure_count"] == 1
                assert stats["success_rate"] == 2 / 3
                assert stats["tool_counts"]["security_scan"] == 2
                assert stats["tool_counts"]["extract_code"] == 1

                audit_log.conn.close()

    def test_get_stats_empty(self):
        """Test statistics on empty audit log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                stats = audit_log.get_stats()

                assert stats["total_events"] == 0
                assert stats["success_count"] == 0
                assert stats["failure_count"] == 0
                assert stats["success_rate"] == 0.0
                assert stats["tool_counts"] == {}

                audit_log.conn.close()


class TestAuditLogExport:
    """Test exporting audit log to JSONL."""

    def test_export_to_jsonl(self):
        """Test exporting audit log to JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                # Log some events
                audit_log.log_tool_call(
                    event_id="evt-1",
                    request_id="req-1",
                    tool_name="security_scan",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=100.0,
                    input_summary={"key": "value"},
                    output_summary={"result": "data"},
                )

                # Export
                export_file = audit_log.export_to_jsonl()

                assert export_file.exists()
                assert export_file.suffix == ".jsonl"

                # Verify content
                with open(export_file) as f:
                    line = f.readline()
                    event = json.loads(line)
                    assert event["tool_name"] == "security_scan"
                    assert event["input_summary"]["key"] == "value"

                audit_log.conn.close()

    def test_export_decrypts_data(self):
        """Test that export decrypts encrypted data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=True)

                # Log with encryption
                audit_log.log_tool_call(
                    event_id="evt-1",
                    request_id="req-1",
                    tool_name="security_scan",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=100.0,
                    input_summary={"sensitive": "data"},
                    output_summary={"results": "encrypted"},
                )

                # Export
                export_file = audit_log.export_to_jsonl()

                # Verify exported data is plain JSON (decrypted)
                with open(export_file) as f:
                    line = f.readline()
                    event = json.loads(line)
                    assert event["input_summary"]["sensitive"] == "data"
                    assert event["output_summary"]["results"] == "encrypted"

                audit_log.conn.close()


class TestAuditLogCleanup:
    """Test audit log cleanup on shutdown."""

    def test_cleanup_exports_and_closes(self):
        """Test cleanup exports events and closes database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                audit_log.log_tool_call(
                    event_id="evt-1",
                    request_id="req-1",
                    tool_name="tool1",
                    tier_applied="enterprise",
                    status="success",
                    duration_ms=100.0,
                    input_summary={},
                    output_summary={},
                )

                # Cleanup
                export_file = audit_log.cleanup()

                assert export_file is not None
                assert export_file.exists()

                # Verify database is closed (should raise error on access)
                with pytest.raises(sqlite3.ProgrammingError):
                    audit_log.conn.execute("SELECT * FROM tool_calls")


class TestEncryptionStatus:
    """Test encryption status reporting."""

    def test_get_encryption_status_enabled(self):
        """Test encryption status when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=True)

                status = audit_log.get_encryption_status()

                assert status["enabled"] is True
                assert status["has_key"] is True
                assert status["session_id"] == "test-123"
                assert "audit_session_test-123" in status["db_path"]

                audit_log.conn.close()

    def test_get_encryption_status_disabled(self):
        """Test encryption status when disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                audit_log = AuditLog(session_id="test-123", encryption_enabled=False)

                status = audit_log.get_encryption_status()

                assert status["enabled"] is False
                assert status["has_key"] is False

                audit_log.conn.close()
