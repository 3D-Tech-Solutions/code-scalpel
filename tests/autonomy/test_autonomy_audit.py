"""
Tests for Autonomy Audit Trail (v3.0.0).

# [20251217_TEST] Comprehensive tests for audit trail functionality

Test Categories:
1. Basic Recording - Verify audit entry creation
2. Parent-Child Relationships - Verify nested operation tracking
3. Immutability - Verify entries cannot be modified
4. Cryptographic Hashes - Verify input/output integrity
5. Export Formats - Verify JSON, CSV, HTML export
6. Filtering - Verify time range, event type, success filtering
7. Query Operations - Verify trace and summary queries
8. Edge Cases - Large data, many operations, etc.
"""

import json
from datetime import datetime, timedelta

import pytest

from code_scalpel.autonomy import AutonomyAuditTrail

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_audit_dir(tmp_path):
    """Create temporary directory for audit storage."""
    audit_dir = tmp_path / ".code-scalpel" / "autonomy_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


@pytest.fixture
def audit_trail(temp_audit_dir):
    """Create audit trail instance with temp storage."""
    trail = AutonomyAuditTrail(storage_path=str(temp_audit_dir))
    return trail


# =============================================================================
# Test Basic Recording (P0)
# =============================================================================


class TestBasicRecording:
    """Verify audit entry recording works correctly."""

    def test_record_simple_operation(self, audit_trail):
        """Test recording a simple operation."""
        entry_id = audit_trail.record(
            event_type="FIX_LOOP_START",
            operation="fix_syntax_error",
            input_data={"code": "x = 1", "error": "syntax error"},
            output_data={"fixed_code": "x = 1"},
            success=True,
            duration_ms=120,
        )

        assert entry_id is not None
        assert entry_id.startswith("op_")

        # Verify entry was stored
        entries = audit_trail._load_entries()
        assert len(entries) == 1
        assert entries[0].id == entry_id
        assert entries[0].event_type == "FIX_LOOP_START"
        assert entries[0].operation == "fix_syntax_error"
        assert entries[0].success is True
        assert entries[0].duration_ms == 120

    def test_record_with_metadata(self, audit_trail):
        """Test recording with metadata."""
        audit_trail.record(
            event_type="ERROR_ANALYSIS",
            operation="analyze_error",
            input_data={"error": "NameError"},
            output_data={"cause": "undefined variable"},
            success=True,
            duration_ms=50,
            metadata={"file": "test.py", "line": 42},
        )

        entries = audit_trail._load_entries()
        assert len(entries) == 1
        assert entries[0].metadata == {"file": "test.py", "line": 42}

    def test_record_failure(self, audit_trail):
        """Test recording a failed operation."""
        audit_trail.record(
            event_type="FIX_GENERATION",
            operation="generate_fix",
            input_data={"error": "complex error"},
            output_data={"error": "could not generate fix"},
            success=False,
            duration_ms=1000,
        )

        entries = audit_trail._load_entries()
        assert len(entries) == 1
        assert entries[0].success is False

    def test_multiple_operations(self, audit_trail):
        """Test recording multiple operations."""
        entry_ids = []
        for i in range(5):
            entry_id = audit_trail.record(
                event_type=f"EVENT_{i}",
                operation=f"operation_{i}",
                input_data={"index": i},
                output_data={"result": i * 2},
                success=True,
                duration_ms=100 + i * 10,
            )
            entry_ids.append(entry_id)

        entries = audit_trail._load_entries()
        assert len(entries) == 5
        assert [e.id for e in entries] == entry_ids


# =============================================================================
# Test Parent-Child Relationships (P0)
# =============================================================================


class TestParentChildRelationships:
    """Verify nested operation tracking."""

    def test_parent_child_recording(self, audit_trail):
        """Test recording parent and child operations."""
        # Record parent
        parent_id = audit_trail.record(
            event_type="FIX_LOOP_START",
            operation="fix_syntax_error",
            input_data={"code": "x = 1"},
            output_data={"fixed": True},
            success=True,
            duration_ms=3200,
        )

        # Record children
        child1_id = audit_trail.record(
            event_type="ERROR_ANALYSIS",
            operation="analyze_error",
            input_data={"error": "syntax"},
            output_data={"cause": "missing colon"},
            success=True,
            duration_ms=120,
            parent_id=parent_id,
        )

        child2_id = audit_trail.record(
            event_type="FIX_GENERATION",
            operation="generate_fix",
            input_data={"cause": "missing colon"},
            output_data={"fix": "add colon"},
            success=True,
            duration_ms=450,
            parent_id=parent_id,
        )

        entries = audit_trail._load_entries()
        assert len(entries) == 3

        # Verify parent has no parent
        parent = next(e for e in entries if e.id == parent_id)
        assert parent.parent_id is None

        # Verify children have correct parent
        child1 = next(e for e in entries if e.id == child1_id)
        assert child1.parent_id == parent_id

        child2 = next(e for e in entries if e.id == child2_id)
        assert child2.parent_id == parent_id

    def test_nested_hierarchy(self, audit_trail):
        """Test three-level nested hierarchy."""
        # Level 1
        parent_id = audit_trail.record(
            event_type="LEVEL1",
            operation="parent",
            input_data={},
            output_data={},
            success=True,
            duration_ms=1000,
        )

        # Level 2
        child_id = audit_trail.record(
            event_type="LEVEL2",
            operation="child",
            input_data={},
            output_data={},
            success=True,
            duration_ms=500,
            parent_id=parent_id,
        )

        # Level 3
        grandchild_id = audit_trail.record(
            event_type="LEVEL3",
            operation="grandchild",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
            parent_id=child_id,
        )

        entries = audit_trail._load_entries()
        assert len(entries) == 3

        # Verify hierarchy
        grandchild = next(e for e in entries if e.id == grandchild_id)
        assert grandchild.parent_id == child_id

        child = next(e for e in entries if e.id == child_id)
        assert child.parent_id == parent_id

        parent = next(e for e in entries if e.id == parent_id)
        assert parent.parent_id is None


# =============================================================================
# Test Cryptographic Hashes (P0)
# =============================================================================


class TestCryptographicHashes:
    """Verify input/output hashing."""

    def test_input_hash_consistent(self, audit_trail):
        """Test that same input produces same hash."""
        input_data = {"code": "x = 1", "file": "test.py"}

        hash1 = audit_trail._hash_data(input_data)
        hash2 = audit_trail._hash_data(input_data)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_different_input_different_hash(self, audit_trail):
        """Test that different inputs produce different hashes."""
        input1 = {"code": "x = 1"}
        input2 = {"code": "y = 2"}

        hash1 = audit_trail._hash_data(input1)
        hash2 = audit_trail._hash_data(input2)

        assert hash1 != hash2

    def test_hashes_stored_in_entry(self, audit_trail):
        """Test that hashes are stored in audit entry."""
        audit_trail.record(
            event_type="TEST",
            operation="test_op",
            input_data={"input": "data"},
            output_data={"output": "result"},
            success=True,
            duration_ms=100,
        )

        entries = audit_trail._load_entries()
        entry = entries[0]

        assert entry.input_hash is not None
        assert entry.output_hash is not None
        assert len(entry.input_hash) == 64
        assert len(entry.output_hash) == 64

    def test_hash_integrity_verification(self, audit_trail):
        """Test that stored data matches hash."""
        input_data = {"test": "input"}
        output_data = {"test": "output"}

        audit_trail.record(
            event_type="TEST",
            operation="test_op",
            input_data=input_data,
            output_data=output_data,
            success=True,
            duration_ms=100,
        )

        entries = audit_trail._load_entries()
        entry = entries[0]

        # Verify hashes match original data
        expected_input_hash = audit_trail._hash_data(input_data)
        expected_output_hash = audit_trail._hash_data(output_data)

        assert entry.input_hash == expected_input_hash
        assert entry.output_hash == expected_output_hash


# =============================================================================
# Test Export Formats (P0)
# =============================================================================


class TestExportFormats:
    """Verify multi-format export functionality."""

    def test_export_json(self, audit_trail):
        """Test JSON export."""
        # Record some operations
        audit_trail.record(
            event_type="EVENT1",
            operation="op1",
            input_data={"a": 1},
            output_data={"b": 2},
            success=True,
            duration_ms=100,
        )

        audit_trail.record(
            event_type="EVENT2",
            operation="op2",
            input_data={"c": 3},
            output_data={"d": 4},
            success=False,
            duration_ms=200,
        )

        # Export to JSON
        json_output = audit_trail.export(format="json")

        # Verify valid JSON
        data = json.loads(json_output)
        assert "session_id" in data
        assert "summary" in data
        assert "operations" in data

        assert data["summary"]["total_operations"] == 2
        assert data["summary"]["successful"] == 1
        assert data["summary"]["failed"] == 1
        assert len(data["operations"]) == 2

    def test_export_csv(self, audit_trail):
        """Test CSV export."""
        # Record operations
        audit_trail.record(
            event_type="EVENT1",
            operation="op1",
            input_data={"a": 1},
            output_data={"b": 2},
            success=True,
            duration_ms=100,
        )

        # Export to CSV
        csv_output = audit_trail.export(format="csv")

        # Verify CSV format
        lines = csv_output.strip().split("\n")
        assert len(lines) >= 2  # Header + at least 1 data row

        # Verify header
        header = lines[0]
        assert "id" in header
        assert "timestamp" in header
        assert "event_type" in header
        assert "success" in header

    def test_export_html(self, audit_trail):
        """Test HTML export."""
        # Record operations
        audit_trail.record(
            event_type="EVENT1",
            operation="op1",
            input_data={"a": 1},
            output_data={"b": 2},
            success=True,
            duration_ms=100,
        )

        # Export to HTML
        html_output = audit_trail.export(format="html")

        # Verify HTML structure
        assert "<!DOCTYPE html>" in html_output
        assert "<html>" in html_output
        assert "<table>" in html_output
        assert "Autonomy Audit Report" in html_output
        assert audit_trail.current_session_id in html_output

    def test_export_invalid_format(self, audit_trail):
        """Test that invalid format raises error."""
        with pytest.raises(ValueError) as exc_info:
            audit_trail.export(format="invalid")

        assert "Unknown format" in str(exc_info.value)


# =============================================================================
# Test Filtering (P0)
# =============================================================================


class TestFiltering:
    """Verify filtering by time, type, and success."""

    def test_filter_by_event_type(self, audit_trail):
        """Test filtering by event type."""
        # Record different event types
        audit_trail.record(
            event_type="TYPE_A",
            operation="op1",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        audit_trail.record(
            event_type="TYPE_B",
            operation="op2",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        audit_trail.record(
            event_type="TYPE_A",
            operation="op3",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        # Export with filter
        json_output = audit_trail.export(format="json", event_types=["TYPE_A"])

        data = json.loads(json_output)
        operations = data["operations"]

        # Should only have TYPE_A operations
        assert len(operations) == 2
        assert all(op["event_type"] == "TYPE_A" for op in operations)

    def test_filter_by_success(self, audit_trail):
        """Test filtering by success status."""
        # Record successes and failures
        audit_trail.record(
            event_type="EVENT",
            operation="op1",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        audit_trail.record(
            event_type="EVENT",
            operation="op2",
            input_data={},
            output_data={},
            success=False,
            duration_ms=100,
        )

        audit_trail.record(
            event_type="EVENT",
            operation="op3",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        # Export only successes
        json_output = audit_trail.export(format="json", success_only=True)

        data = json.loads(json_output)
        operations = data["operations"]

        # Should only have successful operations
        assert len(operations) == 2
        assert all(op["success"] for op in operations)

    # [20251217_BUGFIX] Removed unused datetime.now() call flagged by static analysis
    def test_filter_by_time_range(self, audit_trail):
        """Test filtering by time range."""

        # Record operations at different times
        # We'll manipulate the timestamps manually for testing
        audit_trail.record(
            event_type="EVENT",
            operation="op1",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        # Slight delay to ensure different timestamps
        import time

        time.sleep(0.01)

        mid_time = datetime.now()

        time.sleep(0.01)

        audit_trail.record(
            event_type="EVENT",
            operation="op2",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        # Filter to only include second operation
        json_output = audit_trail.export(format="json", time_range=(mid_time, datetime.now() + timedelta(seconds=1)))

        data = json.loads(json_output)
        operations = data["operations"]

        # Should only have second operation
        assert len(operations) == 1
        assert operations[0]["operation"] == "op2"


# =============================================================================
# Test Query Operations (P0)
# =============================================================================


class TestQueryOperations:
    """Verify trace and summary queries."""

    def test_get_operation_trace(self, audit_trail):
        """Test getting full operation trace."""
        # Create parent and children
        parent_id = audit_trail.record(
            event_type="PARENT",
            operation="parent_op",
            input_data={},
            output_data={},
            success=True,
            duration_ms=1000,
        )

        child1_id = audit_trail.record(
            event_type="CHILD1",
            operation="child1_op",
            input_data={},
            output_data={},
            success=True,
            duration_ms=200,
            parent_id=parent_id,
        )

        child2_id = audit_trail.record(
            event_type="CHILD2",
            operation="child2_op",
            input_data={},
            output_data={},
            success=True,
            duration_ms=300,
            parent_id=parent_id,
        )

        # Get trace
        trace = audit_trail.get_operation_trace(parent_id)

        # Should include parent and all children
        assert len(trace) == 3
        assert trace[0].id == parent_id
        assert any(e.id == child1_id for e in trace)
        assert any(e.id == child2_id for e in trace)

    def test_get_operation_trace_nested(self, audit_trail):
        """Test getting trace for nested operations."""
        # Three-level hierarchy
        parent_id = audit_trail.record(
            event_type="PARENT",
            operation="parent",
            input_data={},
            output_data={},
            success=True,
            duration_ms=1000,
        )

        child_id = audit_trail.record(
            event_type="CHILD",
            operation="child",
            input_data={},
            output_data={},
            success=True,
            duration_ms=500,
            parent_id=parent_id,
        )

        grandchild_id = audit_trail.record(
            event_type="GRANDCHILD",
            operation="grandchild",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
            parent_id=child_id,
        )

        # Get full trace
        trace = audit_trail.get_operation_trace(parent_id)

        # Should include all three levels
        assert len(trace) == 3
        assert trace[0].id == parent_id
        assert any(e.id == child_id for e in trace)
        assert any(e.id == grandchild_id for e in trace)

    def test_get_operation_trace_nonexistent(self, audit_trail):
        """Test getting trace for non-existent operation."""
        trace = audit_trail.get_operation_trace("nonexistent_id")
        assert len(trace) == 0

    def test_get_session_summary(self, audit_trail):
        """Test getting session summary."""
        # Record mix of operations
        audit_trail.record(
            event_type="TYPE_A",
            operation="op1",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        audit_trail.record(
            event_type="TYPE_B",
            operation="op2",
            input_data={},
            output_data={},
            success=False,
            duration_ms=200,
        )

        audit_trail.record(
            event_type="TYPE_A",
            operation="op3",
            input_data={},
            output_data={},
            success=True,
            duration_ms=150,
        )

        # Get summary
        summary = audit_trail.get_session_summary()

        assert summary["session_id"] == audit_trail.current_session_id
        assert summary["total_operations"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["total_duration_ms"] == 450

        # Check event type counts
        assert summary["event_types"]["TYPE_A"] == 2
        assert summary["event_types"]["TYPE_B"] == 1


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_large_input_data(self, audit_trail):
        """Test handling of large input data (truncation)."""
        # Create large input (> 10000 chars)
        large_input = {"code": "x" * 15000}

        entry_id = audit_trail.record(
            event_type="TEST",
            operation="large_op",
            input_data=large_input,
            output_data={"result": "ok"},
            success=True,
            duration_ms=100,
        )

        # Verify entry was stored
        entries = audit_trail._load_entries()
        assert len(entries) == 1

        # Verify data was truncated in storage
        session_dir = audit_trail.storage_path / audit_trail.current_session_id
        data_dir = session_dir / "data"

        with open(data_dir / f"{entry_id}_input.json") as f:
            stored_data = json.load(f)
            assert stored_data["truncated"] is True
            assert len(stored_data["data"]) <= 10000

    def test_empty_session(self, audit_trail):
        """Test operations on empty session."""
        # Get summary of empty session
        summary = audit_trail.get_session_summary()

        assert summary["total_operations"] == 0
        assert summary["successful"] == 0
        assert summary["failed"] == 0
        assert summary["total_duration_ms"] == 0

        # Export empty session
        json_output = audit_trail.export(format="json")
        data = json.loads(json_output)

        assert data["summary"]["total_operations"] == 0
        assert len(data["operations"]) == 0

    def test_session_id_format(self, audit_trail):
        """Test session ID format is correct."""
        session_id = audit_trail.current_session_id

        # Format: YYYYMMDD_HHMMSS_<hash>
        parts = session_id.split("_")
        assert len(parts) == 3

        # Date part should be 8 digits
        assert len(parts[0]) == 8
        assert parts[0].isdigit()

        # Time part should be 6 digits
        assert len(parts[1]) == 6
        assert parts[1].isdigit()

        # Hash part should be 6 hex chars
        assert len(parts[2]) == 6

    def test_entry_id_format(self, audit_trail):
        """Test entry ID format is correct."""
        entry_id = audit_trail.record(
            event_type="TEST",
            operation="test_op",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        # Format: op_<timestamp>_<hash>
        assert entry_id.startswith("op_")
        parts = entry_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "op"

    def test_concurrent_sessions(self, temp_audit_dir):
        """Test multiple concurrent sessions."""
        trail1 = AutonomyAuditTrail(storage_path=str(temp_audit_dir))
        trail2 = AutonomyAuditTrail(storage_path=str(temp_audit_dir))

        # Should have different session IDs
        assert trail1.current_session_id != trail2.current_session_id

        # Record to each
        trail1.record(
            event_type="SESSION1",
            operation="op1",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        trail2.record(
            event_type="SESSION2",
            operation="op2",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        # Each should only see their own entries
        entries1 = trail1._load_entries()
        entries2 = trail2._load_entries()

        assert len(entries1) == 1
        assert len(entries2) == 1
        assert entries1[0].event_type == "SESSION1"
        assert entries2[0].event_type == "SESSION2"


# =============================================================================
# Test Immutability (P0)
# =============================================================================


class TestImmutability:
    """Verify entries are immutable."""

    def test_entries_cannot_be_modified(self, audit_trail):
        """Test that entries are immutable after creation."""
        # Record entry
        audit_trail.record(
            event_type="TEST",
            operation="test_op",
            input_data={"original": "data"},
            output_data={"original": "result"},
            success=True,
            duration_ms=100,
        )

        # Load entry
        entries = audit_trail._load_entries()
        original_entry = entries[0]

        # Store original values
        original_event_type = original_entry.event_type
        original_success = original_entry.success

        # Attempt to modify (this will only modify the in-memory object)
        original_entry.event_type = "MODIFIED"
        original_entry.success = False

        # Reload from disk
        entries_reloaded = audit_trail._load_entries()
        reloaded_entry = entries_reloaded[0]

        # Should still have original values
        assert reloaded_entry.event_type == original_event_type
        assert reloaded_entry.success == original_success

    def test_stored_data_immutable(self, audit_trail):
        """Test that stored data files are append-only."""
        entry_id = audit_trail.record(
            event_type="TEST",
            operation="test_op",
            input_data={"test": "data"},
            output_data={"test": "result"},
            success=True,
            duration_ms=100,
        )

        # Get the entry file path
        session_dir = audit_trail.storage_path / audit_trail.current_session_id
        entry_file = session_dir / f"{entry_id}.json"

        # Read original content
        with open(entry_file) as f:
            original_content = f.read()

        # Verify we can't modify it without explicit file write
        # (The system should use append-only semantics)
        assert entry_file.exists()

        # Record another entry
        audit_trail.record(
            event_type="TEST2",
            operation="test_op2",
            input_data={},
            output_data={},
            success=True,
            duration_ms=100,
        )

        # Original entry should still be unchanged
        with open(entry_file) as f:
            current_content = f.read()

        assert current_content == original_content
