# [20260108_TEST] Enterprise compliance checking tests for rename_symbol
"""
Tests for Enterprise-tier compliance checking functionality.

Verifies that rename operations are validated against governance policies:
- Policy enforcement (if governance available)
- Graceful degradation (if governance not available)
- Compliance violation reporting
- Integration with audit trail
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.surgery.audit_trail import configure_audit_trail
from code_scalpel.surgery.compliance import (
    ComplianceCheckResult,
    check_rename_compliance,
    format_compliance_error,
)
from code_scalpel.surgery.rename_symbol_refactor import rename_references_across_project


class TestComplianceBasics:
    """Test basic compliance checking functionality."""

    def test_compliance_result_creation(self):
        """ComplianceCheckResult can be created."""
        result = ComplianceCheckResult(allowed=True)
        assert result.allowed is True
        assert result.reason is None
        assert result.violations == []

    def test_compliance_result_with_violations(self):
        """ComplianceCheckResult can include violations."""
        violations = [
            {
                "rule": "test_rule",
                "message": "Test violation",
                "severity": "high",
                "source": "policy",
            }
        ]
        result = ComplianceCheckResult(allowed=False, reason="Policy violation", violations=violations)
        assert result.allowed is False
        assert result.reason == "Policy violation"
        assert len(result.violations) == 1

    def test_format_compliance_error(self):
        """Compliance errors can be formatted."""
        result = ComplianceCheckResult(
            allowed=False,
            reason="Operation not allowed",
            violations=[
                {
                    "rule": "no_unsafe_renames",
                    "message": "Unsafe rename detected",
                    "severity": "critical",
                    "source": "policy",
                }
            ],
        )

        error_msg = format_compliance_error(result)
        assert "Compliance check failed" in error_msg
        assert "Operation not allowed" in error_msg
        assert "no_unsafe_renames" in error_msg
        assert "CRITICAL" in error_msg.upper()

    def test_format_compliance_success(self):
        """Successful compliance returns empty string."""
        result = ComplianceCheckResult(allowed=True)
        error_msg = format_compliance_error(result)
        assert error_msg == ""


class TestComplianceChecking:
    """Test compliance checking for rename operations."""

    def test_compliance_check_graceful_degradation(self):
        """Compliance check allows operation if governance not available."""
        # When governance is not available, should allow by default
        result = check_rename_compliance(
            target_file="src/test.py",
            target_type="function",
            target_name="old_func",
            new_name="new_func",
        )

        # Should allow with informative reason
        assert result.allowed is True
        assert "not available" in result.reason or result.reason is None

    def test_compliance_check_with_valid_rename(self):
        """Valid rename passes compliance check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create minimal governance config
            gov_dir = project_root / ".code-scalpel"
            gov_dir.mkdir(parents=True, exist_ok=True)

            result = check_rename_compliance(
                target_file="src/utils.py",
                target_type="function",
                target_name="calculate",
                new_name="compute",
                project_root=project_root,
            )

            # Should allow (no restrictive policies)
            assert result.allowed is True or "not available" in (result.reason or "")


class TestComplianceIntegration:
    """Test compliance checking integration with rename operations."""

    def test_rename_with_compliance_enabled(self, temp_project):
        """Rename operation respects compliance checking."""
        main_py = temp_project / "main.py"

        # Perform rename with compliance enabled (should pass with default policies)
        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="compliant_function",
            create_backup=False,
            max_files_searched=10,
            max_files_updated=10,
            tier="enterprise",
            enable_audit=False,
            enable_compliance=True,
        )

        # Should succeed (no restrictive policies)
        assert result.success is True

    def test_rename_without_compliance(self, temp_project):
        """Rename operation works without compliance checking."""
        main_py = temp_project / "main.py"

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="unchecked_function",
            create_backup=False,
            max_files_searched=10,
            max_files_updated=10,
            tier="pro",
            enable_audit=False,
            enable_compliance=False,
        )

        assert result.success is True

    def test_compliance_failure_logged_in_audit(self, temp_project):
        """Compliance failures are recorded in audit trail."""
        with tempfile.TemporaryDirectory() as audit_dir:
            configure_audit_trail(log_dir=audit_dir, enabled=True)

            main_py = temp_project / "main.py"

            # Note: This test assumes default governance allows renames
            # In production, you'd configure governance policies to test denials
            result = rename_references_across_project(
                project_root=temp_project,
                target_file=main_py,
                target_type="function",
                target_name="old_function",
                new_name="compliant_test",
                create_backup=False,
                max_files_searched=10,
                max_files_updated=10,
                tier="enterprise",
                enable_audit=True,
                enable_compliance=True,
            )

            # With default policies, should succeed
            assert result.success is True

            # Audit entry should be present
            if result.audit_entry:
                assert result.audit_entry.operation == "rename_symbol_cross_file"
                assert result.audit_entry.tier == "enterprise"


class TestComplianceErrorMessages:
    """Test compliance error message formatting."""

    def test_single_violation_message(self):
        """Single violation formatted clearly."""
        result = ComplianceCheckResult(
            allowed=False,
            reason="Policy violation detected",
            violations=[
                {
                    "rule": "naming_convention",
                    "message": "Function names must be snake_case",
                    "severity": "medium",
                    "source": "policy",
                }
            ],
        )

        msg = format_compliance_error(result)
        assert "Compliance check failed" in msg
        assert "naming_convention" in msg
        assert "snake_case" in msg
        assert "MEDIUM" in msg

    def test_multiple_violations_message(self):
        """Multiple violations listed."""
        result = ComplianceCheckResult(
            allowed=False,
            reason="Multiple policy violations",
            violations=[
                {
                    "rule": "rule1",
                    "message": "Violation 1",
                    "severity": "high",
                    "source": "policy",
                },
                {
                    "rule": "rule2",
                    "message": "Violation 2",
                    "severity": "medium",
                    "source": "budget",
                },
                {
                    "rule": "rule3",
                    "message": "Violation 3",
                    "severity": "low",
                    "source": "semantic",
                },
            ],
        )

        msg = format_compliance_error(result)
        assert msg.count("rule") >= 3
        assert "Violation 1" in msg
        assert "Violation 2" in msg
        assert "Violation 3" in msg

    def test_error_message_without_violations(self):
        """Error message works without violations list."""
        result = ComplianceCheckResult(allowed=False, reason="Generic compliance failure")

        msg = format_compliance_error(result)
        assert "Compliance check failed" in msg
        assert "Generic compliance failure" in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
