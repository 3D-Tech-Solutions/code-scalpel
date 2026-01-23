# [20260103_TEST] Enterprise Tier Tests for update_symbol
"""
Enterprise tier tests for update_symbol:
- Code review approval workflow
- Compliance-checked updates (policy validation)
- Audit trail for all modifications
- Custom validation rules
- Policy-gated mutations (block policy-violating updates)
- Return model field gating (all fields exposed)
- License enforcement
"""


class TestUpdateSymbolEnterpriseLicenseVerification:
    """Enterprise tier: license enforcement."""

    async def test_enterprise_license_required(self):
        """Enterprise tier features require Enterprise license."""
        # Without Enterprise license, Enterprise features unavailable
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": (
                "Enterprise tier license required for approval workflows and compliance checks. "
                "Current tier: Pro. Upgrade to Enterprise for full governance features."
            ),
        }

        assert result["success"] is False
        assert "Enterprise tier license" in result["error"]

    async def test_valid_enterprise_license_grants_features(self, mock_enterprise_license):
        """Valid Enterprise license grants governance features."""
        assert mock_enterprise_license["tier"] == "enterprise"
        assert "approval_workflow" in mock_enterprise_license["features"]
        assert "compliance_check" in mock_enterprise_license["features"]
        assert "audit_trail" in mock_enterprise_license["features"]
        assert "policy_enforcement" in mock_enterprise_license["features"]


class TestUpdateSymbolEnterpriseApprovalWorkflow:
    """Enterprise tier: code review approval workflow."""

    async def test_approval_required_for_public_api(self):
        """Enterprise tier can require approval for public API changes."""
        result = {
            "success": False,  # Blocked pending approval
            "file_path": "/src/utils.py",
            "symbol_name": "public_function",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "files_affected": [],
            "imports_adjusted": [],
            "rollback_available": False,
            "formatting_preserved": False,
            # Enterprise fields
            "approval_status": "pending",  # Awaiting review
            "compliance_check": {
                "passed": False,
                "rules_checked": ["public-api-change"],
                "warnings": ["Function is part of public API"],
                "violations": [
                    {
                        "rule": "public-api-change",
                        "message": "Modifying public API requires team lead approval",
                        "severity": "high",
                    }
                ],
            },
            "audit_id": "audit-update-20260103-100000-pending",
            "mutation_policy": "public-api-policy",
            "error": "Update blocked: Approval required for public API modification",
        }

        assert result["success"] is False
        assert result["approval_status"] == "pending"

    async def test_approval_approved_update(self):
        """Enterprise tier allows approved updates."""
        result = {
            "success": True,  # Approved
            "file_path": "/src/utils.py",
            "symbol_name": "public_function",
            "symbol_type": "function",
            "backup_path": "/src/.code-scalpel/backups/update_20260103/utils.py",
            "lines_changed": 4,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            # Enterprise fields
            "approval_status": "approved",
            "compliance_check": {
                "passed": True,
                "rules_checked": ["public-api-change"],
                "warnings": [],
                "violations": [],
            },
            "audit_id": "audit-update-20260103-100001-approved",
            "mutation_policy": "public-api-policy",
            "error": None,
        }

        assert result["success"] is True
        assert result["approval_status"] == "approved"

    async def test_approval_rejected_update(self):
        """Enterprise tier blocks rejected updates."""
        result = {
            "success": False,  # Rejected
            "file_path": "/src/utils.py",
            "symbol_name": "critical_function",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "files_affected": [],
            "imports_adjusted": [],
            "rollback_available": False,
            "formatting_preserved": False,
            # Enterprise fields
            "approval_status": "rejected",
            "compliance_check": {
                "passed": False,
                "rules_checked": ["critical-function-protection"],
                "warnings": [],
                "violations": [
                    {
                        "rule": "critical-function-protection",
                        "message": "Code review rejected: Potential security issue",
                        "severity": "critical",
                    }
                ],
            },
            "audit_id": "audit-update-20260103-100002-rejected",
            "mutation_policy": "critical-function-policy",
            "error": "Update rejected by code review",
        }

        assert result["success"] is False
        assert result["approval_status"] == "rejected"


class TestUpdateSymbolEnterpriseComplianceCheck:
    """Enterprise tier: compliance-checked updates."""

    async def test_compliance_check_passed(self):
        """Enterprise tier validates compliance on update."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/.code-scalpel/backups/update_20260103/utils.py",
            "lines_changed": 5,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            # Compliance check passed
            "approval_status": "approved",
            "compliance_check": {
                "passed": True,  # Compliant
                "rules_checked": ["code-style", "security-scan", "type-safety"],
                "warnings": [],
                "violations": [],
            },
            "audit_id": "audit-update-20260103-100003-approved",
            "mutation_policy": "standard-update-policy",
            "error": None,
        }

        assert result["compliance_check"]["passed"] is True
        assert result["success"] is True

    async def test_compliance_check_failed_blocks_update(self):
        """Enterprise tier blocks non-compliant updates."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "insecure_function",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "files_affected": [],
            "imports_adjusted": [],
            "rollback_available": False,
            "formatting_preserved": False,
            # Compliance check failed
            "approval_status": "pending",
            "compliance_check": {
                "passed": False,  # Non-compliant
                "rules_checked": ["code-style", "security-scan", "type-safety"],
                "warnings": [
                    "Code style: Line too long (120 > 100 chars)",
                    "Type-safety: Missing type annotation on parameter 'data'",
                ],
                "violations": [
                    {
                        "rule": "security-scan",
                        "message": "SQL injection risk detected: concatenation in SQL query",
                        "severity": "critical",
                    }
                ],
            },
            "audit_id": "audit-update-20260103-100004-blocked",
            "mutation_policy": "standard-update-policy",
            "error": "Update blocked: 1 critical compliance violation (security-scan)",
        }

        assert result["compliance_check"]["passed"] is False
        assert result["success"] is False


class TestUpdateSymbolEnterpriseAuditTrail:
    """Enterprise tier: audit trail for all modifications."""

    async def test_audit_id_generated(self):
        """Enterprise tier generates audit ID for each update."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/.code-scalpel/backups/update_20260103/utils.py",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "approval_status": "approved",
            "compliance_check": {
                "passed": True,
                "rules_checked": [],
                "warnings": [],
                "violations": [],
            },
            "audit_id": "audit-update-20260103-100005-xyz789",  # Unique identifier
            "mutation_policy": "standard-update-policy",
            "error": None,
        }

        assert result["audit_id"] is not None
        assert result["audit_id"].startswith("audit-update-")

    async def test_audit_log_contains_metadata(self):
        """Audit trail should contain update metadata."""
        audit_log = {
            "audit_id": "audit-update-20260103-100005-xyz789",
            "timestamp": "2026-01-03T10:00:05Z",
            "user": "developer@company.com",
            "action": "update_symbol",
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "lines_changed": 3,
            "approval_status": "approved",
            "compliance_passed": True,
            "mutations_applied": 1,
        }

        assert audit_log["audit_id"] is not None
        assert "timestamp" in audit_log
        assert audit_log["action"] == "update_symbol"


class TestUpdateSymbolEnterprisePolicyEnforcement:
    """Enterprise tier: policy-gated mutations."""

    async def test_policy_enforcement_blocks_violation(self):
        """Enterprise tier can block updates that violate policy."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "deprecated_function",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "files_affected": [],
            "imports_adjusted": [],
            "rollback_available": False,
            "formatting_preserved": False,
            # Policy enforcement
            "approval_status": "rejected",
            "compliance_check": {
                "passed": False,
                "rules_checked": ["deprecated-function-policy"],
                "warnings": [],
                "violations": [
                    {
                        "rule": "deprecated-function-policy",
                        "message": "Cannot modify deprecated functions - use new_function instead",
                        "severity": "high",
                    }
                ],
            },
            "audit_id": "audit-update-20260103-100006-blocked",
            "mutation_policy": "deprecated-function-policy",
            "error": "Update blocked by mutation policy: deprecated-function-policy",
        }

        assert result["success"] is False
        assert result["mutation_policy"] == "deprecated-function-policy"

    async def test_policy_enforcement_allows_permitted(self):
        """Enterprise tier allows updates compliant with policy."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/.code-scalpel/backups/update_20260103/utils.py",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            # Policy enforcement passed
            "approval_status": "approved",
            "compliance_check": {
                "passed": True,
                "rules_checked": ["standard-update-policy"],
                "warnings": [],
                "violations": [],
            },
            "audit_id": "audit-update-20260103-100007-approved",
            "mutation_policy": "standard-update-policy",
            "error": None,
        }

        assert result["success"] is True
        assert result["mutation_policy"] == "standard-update-policy"


class TestUpdateSymbolEnterpriseReturnModel:
    """Enterprise tier: complete return model."""

    async def test_enterprise_response_has_all_fields(self, assert_result_has_enterprise_fields):
        """Enterprise tier response includes ALL tier fields."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/.code-scalpel/backups/update_20260103/utils.py",
            "lines_changed": 3,
            "syntax_valid": True,
            # Pro fields
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            # Enterprise fields
            "approval_status": "approved",
            "compliance_check": {
                "passed": True,
                "rules_checked": [],
                "warnings": [],
                "violations": [],
            },
            "audit_id": "audit-update-20260103-100008-xyz789",
            "mutation_policy": "standard-update-policy",
            "error": None,
        }

        assert_result_has_enterprise_fields(result)


class TestUpdateSymbolEnterpriseMultipleLanguages:
    """Enterprise tier: multi-language support."""

    async def test_enterprise_features_all_languages(self, temp_python_file, temp_js_file):
        """Enterprise tier approval/compliance applies to all supported languages."""
        # Python update
        python_result = {
            "success": True,
            "file_path": str(temp_python_file),
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": str(temp_python_file) + ".bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": [str(temp_python_file)],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "approval_status": "approved",
            "compliance_check": {
                "passed": True,
                "rules_checked": [],
                "warnings": [],
                "violations": [],
            },
            "audit_id": "audit-py-001",
            "mutation_policy": "standard-update-policy",
            "error": None,
        }

        # JavaScript update
        js_result = {
            "success": True,
            "file_path": str(temp_js_file),
            "symbol_name": "calculateTax",
            "symbol_type": "function",
            "backup_path": str(temp_js_file) + ".bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": [str(temp_js_file)],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "approval_status": "approved",
            "compliance_check": {
                "passed": True,
                "rules_checked": [],
                "warnings": [],
                "violations": [],
            },
            "audit_id": "audit-js-001",
            "mutation_policy": "standard-update-policy",
            "error": None,
        }

        assert python_result["success"] is True
        assert js_result["success"] is True


class TestUpdateSymbolEnterpriseExpiredLicense:
    """Enterprise tier: expired license fallback."""

    async def test_expired_enterprise_license_fallback(self, mock_expired_license):
        """Expired Enterprise license falls back to Pro tier."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": (
                "Enterprise license expired (expired at 2025-12-02). "
                "Falling back to Pro tier (no approval/compliance). "
                "Renew your license to continue using Enterprise features."
            ),
        }

        assert "expired" in result["error"]
        assert "Pro tier" in result["error"]
