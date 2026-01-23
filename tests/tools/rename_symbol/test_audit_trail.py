# [20260108_TEST] Enterprise audit trail tests for rename_symbol
"""
Tests for Enterprise-tier audit trail functionality.

Verifies that all rename operations are logged with:
- Timestamp and operation details
- Files changed and success/failure status
- User/session identification
- Structured JSON logging
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from code_scalpel.surgery.audit_trail import (
    AuditEntry,
    AuditTrail,
    configure_audit_trail,
)
from code_scalpel.surgery.rename_symbol_refactor import rename_references_across_project


class TestAuditTrailBasics:
    """Test basic audit trail functionality."""

    def test_audit_entry_creation(self):
        """Audit entries can be created with required fields."""
        entry = AuditEntry(
            timestamp="2026-01-08T10:00:00Z",
            operation="rename_symbol",
            session_id="test123",
            target_file="src/utils.py",
            target_type="function",
            target_name="old_func",
            new_name="new_func",
            success=True,
            changed_files=["src/utils.py", "src/main.py"],
            tier="enterprise",
        )

        assert entry.operation == "rename_symbol"
        assert entry.target_name == "old_func"
        assert entry.new_name == "new_func"
        assert entry.success is True
        assert len(entry.changed_files) == 2
        assert entry.tier == "enterprise"

    def test_audit_trail_disabled(self):
        """Audit trail can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditTrail(log_dir=tmpdir, enabled=False)

            entry = AuditEntry(
                timestamp=datetime.utcnow().isoformat(),
                operation="test",
                session_id="test",
                target_file="test.py",
                target_type="function",
                target_name="test",
            )

            audit.log(entry)

            # No files should be created when disabled
            log_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(log_files) == 0

    def test_audit_trail_enabled(self):
        """Audit trail creates log files when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditTrail(log_dir=tmpdir, enabled=True, log_to_file=True)

            entry = AuditEntry(
                timestamp=datetime.utcnow().isoformat(),
                operation="rename_symbol",
                session_id="test456",
                target_file="src/module.py",
                target_type="class",
                target_name="OldClass",
                new_name="NewClass",
                success=True,
                tier="enterprise",
            )

            audit.log(entry)

            # Log file should be created
            log_files = list(Path(tmpdir).glob("audit_*.jsonl"))
            assert len(log_files) == 1

            # Verify content
            content = log_files[0].read_text()
            data = json.loads(content.strip())

            assert data["operation"] == "rename_symbol"
            assert data["target_name"] == "OldClass"
            assert data["new_name"] == "NewClass"
            assert data["success"] is True

    def test_audit_entry_serialization(self):
        """Audit entries serialize to valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditTrail(log_dir=tmpdir)

            entry = audit.create_entry(
                operation="rename_symbol",
                session_id="abc123",
                target_file="/path/to/file.py",
                target_type="function",
                target_name="old_name",
                new_name="new_name",
                tier="enterprise",
                success=True,
                changed_files=["/path/to/file.py", "/path/to/other.py"],
                warnings=["Warning 1", "Warning 2"],
                duration_ms=123.45,
            )

            audit.log(entry)

            # Read and parse
            log_file = list(Path(tmpdir).glob("audit_*.jsonl"))[0]
            content = log_file.read_text()
            data = json.loads(content.strip())

            # Verify all fields
            assert data["operation"] == "rename_symbol"
            assert data["session_id"] == "abc123"
            assert data["target_file"] == "/path/to/file.py"
            assert data["target_type"] == "function"
            assert data["target_name"] == "old_name"
            assert data["new_name"] == "new_name"
            assert data["tier"] == "enterprise"
            assert data["success"] is True
            assert len(data["changed_files"]) == 2
            assert len(data["warnings"]) == 2
            assert data["duration_ms"] == 123.45


class TestAuditTrailQuery:
    """Test audit trail query functionality."""

    def test_query_by_operation(self):
        """Can query audit log by operation type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditTrail(log_dir=tmpdir)

            # Log multiple operations
            for i in range(3):
                entry = audit.create_entry(
                    operation="rename_symbol" if i < 2 else "update_function",
                    session_id=f"session{i}",
                    target_file=f"file{i}.py",
                    target_type="function",
                    target_name=f"func{i}",
                    tier="enterprise",
                )
                audit.log(entry)

            # Query for rename_symbol operations
            results = audit.query(operation="rename_symbol")
            assert len(results) == 2
            assert all(e.operation == "rename_symbol" for e in results)

    def test_query_by_target_file(self):
        """Can query audit log by target file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditTrail(log_dir=tmpdir)

            # Log operations on different files
            for i in range(3):
                entry = audit.create_entry(
                    operation="rename_symbol",
                    session_id=f"session{i}",
                    target_file="src/utils.py" if i == 1 else f"src/file{i}.py",
                    target_type="function",
                    target_name=f"func{i}",
                    tier="enterprise",
                )
                audit.log(entry)

            # Query for specific file
            results = audit.query(target_file="src/utils.py")
            assert len(results) == 1
            assert results[0].target_file == "src/utils.py"

    def test_query_by_success_status(self):
        """Can query audit log by success status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditTrail(log_dir=tmpdir)

            # Log successful and failed operations
            for i in range(4):
                entry = audit.create_entry(
                    operation="rename_symbol",
                    session_id=f"session{i}",
                    target_file=f"file{i}.py",
                    target_type="function",
                    target_name=f"func{i}",
                    tier="enterprise",
                    success=(i % 2 == 0),
                    error=None if i % 2 == 0 else "Test error",
                )
                audit.log(entry)

            # Query for successful operations
            success_results = audit.query(success=True)
            assert len(success_results) == 2
            assert all(e.success for e in success_results)

            # Query for failed operations
            failed_results = audit.query(success=False)
            assert len(failed_results) == 2
            assert not any(e.success for e in failed_results)


class TestAuditTrailIntegration:
    """Test audit trail integration with rename operations."""

    def test_rename_with_audit_enabled(self, temp_project):
        """Rename operation creates audit log when enabled."""
        with tempfile.TemporaryDirectory() as audit_dir:
            # Configure global audit trail
            configure_audit_trail(log_dir=audit_dir, enabled=True)

            main_py = temp_project / "main.py"

            # Perform rename with audit enabled
            result = rename_references_across_project(
                project_root=temp_project,
                target_file=main_py,
                target_type="function",
                target_name="old_function",
                new_name="new_function",
                create_backup=False,
                max_files_searched=10,
                max_files_updated=10,
                tier="enterprise",
                enable_audit=True,
            )

            assert result.success is True
            assert result.audit_entry is not None
            assert result.audit_entry.operation == "rename_symbol_cross_file"
            assert result.audit_entry.target_name == "old_function"
            assert result.audit_entry.new_name == "new_function"
            assert result.audit_entry.tier == "enterprise"
            assert result.audit_entry.success is True

            # Verify audit log file was created
            log_files = list(Path(audit_dir).glob("audit_*.jsonl"))
            assert len(log_files) == 1

            # Verify content
            content = log_files[0].read_text()
            lines = [line for line in content.strip().split("\n") if line]
            assert len(lines) >= 1

            data = json.loads(lines[-1])
            assert data["operation"] == "rename_symbol_cross_file"
            assert data["success"] is True
            assert len(data["changed_files"]) >= 2  # main.py + references

    def test_rename_without_audit(self, temp_project):
        """Rename operation works without audit trail."""
        main_py = temp_project / "main.py"

        # Perform rename with audit disabled
        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="another_function",
            create_backup=False,
            max_files_searched=10,
            max_files_updated=10,
            tier="pro",
            enable_audit=False,
        )

        assert result.success is True
        assert result.audit_entry is None

    def test_failed_rename_logged(self, temp_project):
        """Failed rename operations are logged in audit trail."""
        with tempfile.TemporaryDirectory() as audit_dir:
            configure_audit_trail(log_dir=audit_dir, enabled=True)

            main_py = temp_project / "main.py"

            # Try to rename to invalid identifier
            result = rename_references_across_project(
                project_root=temp_project,
                target_file=main_py,
                target_type="function",
                target_name="old_function",
                new_name="123invalid",  # Invalid identifier
                create_backup=False,
                max_files_searched=10,
                max_files_updated=10,
                tier="enterprise",
                enable_audit=True,
            )

            assert result.success is False
            assert result.audit_entry is not None
            assert result.audit_entry.success is False
            assert result.audit_entry.error is not None
            assert "Invalid Python identifier" in result.audit_entry.error

            # Verify failure logged
            log_files = list(Path(audit_dir).glob("audit_*.jsonl"))
            assert len(log_files) == 1

            content = log_files[0].read_text()
            data = json.loads(content.strip())
            assert data["success"] is False
            assert "Invalid Python identifier" in data["error"]

    def test_audit_includes_performance_metrics(self, temp_project):
        """Audit log includes performance metrics."""
        with tempfile.TemporaryDirectory() as audit_dir:
            configure_audit_trail(log_dir=audit_dir, enabled=True)

            main_py = temp_project / "main.py"

            result = rename_references_across_project(
                project_root=temp_project,
                target_file=main_py,
                target_type="function",
                target_name="old_function",
                new_name="perf_function",
                create_backup=False,
                max_files_searched=10,
                max_files_updated=10,
                tier="enterprise",
                enable_audit=True,
            )

            assert result.audit_entry.duration_ms is not None
            assert result.audit_entry.duration_ms > 0
            assert "files_searched" in result.audit_entry.metadata
            assert "files_updated" in result.audit_entry.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
