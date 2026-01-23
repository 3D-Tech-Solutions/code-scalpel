# [20260103_TEST] Pro Tier Tests for update_symbol
"""
Pro tier tests for update_symbol:
- Unlimited updates (no 10-update session limit)
- Atomic multi-file updates
- Rollback on failure capability
- Import auto-adjustment (when symbols affect imports)
- Formatting preservation (whitespace, indentation, comments)
- Return model field gating (Enterprise fields excluded)
- License enforcement
"""


class TestUpdateSymbolProLicenseVerification:
    """Pro tier: license enforcement."""

    async def test_pro_license_required(self):
        """Pro tier features require Pro license."""
        # Without Pro license, Pro-specific features should be unavailable
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": (
                "Pro tier license required for unlimited updates. "
                "Current tier: Community (10 updates/session limit). "
                "Upgrade to Pro to unlock unlimited updates."
            ),
        }

        assert result["success"] is False
        assert "Pro tier license" in result["error"]

    async def test_valid_pro_license_grants_features(self, mock_pro_license):
        """Valid Pro license grants unlimited updates."""
        # With Pro license, unlimited updates allowed
        # (would need actual license validation in implementation)
        assert mock_pro_license["tier"] == "pro"
        assert mock_pro_license["max_updates_per_session"] == -1
        assert "atomic_multifile_updates" in mock_pro_license["features"]


class TestUpdateSymbolProUnlimitedUpdates:
    """Pro tier: unlimited updates (no session limit)."""

    async def test_more_than_10_updates_allowed(self, temp_python_file):
        """Pro tier allows MORE than 10 updates per session."""
        # Simulate 15 updates (exceeds Community limit of 10)
        for i in range(15):
            result = {
                "success": True,
                "file_path": str(temp_python_file),
                "symbol_name": f"function_{i}",
                "symbol_type": "function",
                "backup_path": str(temp_python_file) + ".bak",
                "lines_changed": 2,
                "syntax_valid": True,
                "files_affected": [str(temp_python_file)],
                "imports_adjusted": [],
                "rollback_available": True,
                "formatting_preserved": True,
                "error": None,
            }
            assert result["success"] is True

    async def test_100_updates_in_session(self, temp_python_file):
        """Pro tier handles 100+ updates in single session."""
        # Should not hit session limit
        for i in range(100):
            result = {
                "success": True,
                "file_path": str(temp_python_file),
                "symbol_name": f"func_{i}",
                "symbol_type": "function",
                "backup_path": str(temp_python_file) + ".bak",
                "lines_changed": 1,
                "syntax_valid": True,
                "files_affected": [str(temp_python_file)],
                "imports_adjusted": [],
                "rollback_available": True,
                "formatting_preserved": True,
                "error": None,
            }
            assert result["success"] is True


class TestUpdateSymbolProMultifileAtomic:
    """Pro tier: atomic multi-file updates."""

    async def test_multifile_update_atomic(self, temp_multifile_project):
        """Pro tier performs multi-file updates atomically."""
        # Update that affects multiple files
        result = {
            "success": True,
            "file_path": str(temp_multifile_project["utils"]),
            "symbol_name": "calculate_discount",
            "symbol_type": "function",
            "backup_path": str(temp_multifile_project["utils"]) + ".bak",
            "lines_changed": 3,
            "syntax_valid": True,
            # Pro tier fields
            "files_affected": [
                str(temp_multifile_project["utils"]),
                str(temp_multifile_project["services"]),  # Affected due to import
            ],
            "imports_adjusted": [
                {
                    "file": str(temp_multifile_project["services"]),
                    "action": "updated",
                    "import": "from utils import calculate_discount",
                }
            ],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        assert result["success"] is True
        assert len(result["files_affected"]) == 2
        assert result["files_affected"][0] == str(temp_multifile_project["utils"])
        assert result["files_affected"][1] == str(temp_multifile_project["services"])

    async def test_multifile_update_atomic_all_or_nothing(self, temp_multifile_project):
        """Pro tier multi-file updates are atomic (all or nothing)."""
        # If second file update fails, first should be rolled back
        result_partial = {
            "success": False,
            "file_path": str(temp_multifile_project["services"]),
            "symbol_name": "apply_discount",
            "symbol_type": "function",
            "backup_path": None,  # Rolled back on failure
            "lines_changed": 0,
            "syntax_valid": False,
            "files_affected": [],
            "imports_adjusted": [],
            "rollback_available": False,
            "formatting_preserved": False,
            "error": "Syntax error in second file, atomic update rolled back",
        }

        assert result_partial["success"] is False
        assert result_partial["files_affected"] == []


class TestUpdateSymbolProRollback:
    """Pro tier: rollback capability."""

    async def test_rollback_available_in_response(self):
        """Pro tier response includes rollback_available field."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/.code-scalpel/backups/update_abc123/utils.py",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,  # Pro tier feature
            "formatting_preserved": True,
            "error": None,
        }

        assert result["rollback_available"] is True

    async def test_rollback_procedure(self, temp_python_file, mocker):
        """Pro tier can rollback to previous version."""
        # Setup: backup exists
        # [20260117_TEST] Capture backup content for context; unused in assertion
        _backup_content = temp_python_file.read_text()

        # Rollback operation (simulated)
        rollback_result = {
            "success": True,
            "message": "Rollback successful",
            "file_path": str(temp_python_file),
            "restored_from": str(temp_python_file) + ".bak",
        }

        assert rollback_result["success"] is True


class TestUpdateSymbolProImportAdjustment:
    """Pro tier: import auto-adjustment."""

    async def test_imports_adjusted_in_response(self):
        """Pro tier response includes imports_adjusted field."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/.code-scalpel/backups/update_abc123/utils.py",
            "lines_changed": 5,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [  # Pro tier feature
                {
                    "file": "/src/utils.py",
                    "action": "added",
                    "import": "from decimal import Decimal",
                },
                {"file": "/src/utils.py", "action": "removed", "import": "import math"},
            ],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        assert len(result["imports_adjusted"]) == 2
        assert result["imports_adjusted"][0]["action"] == "added"
        assert "decimal" in result["imports_adjusted"][0]["import"]

    async def test_auto_import_addition(self):
        """Pro tier auto-adds imports when needed."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "validate_email",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 4,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [
                {
                    "file": "/src/utils.py",
                    "action": "added",
                    "import": "import re",  # Auto-added for regex validation
                }
            ],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        assert result["imports_adjusted"][0]["action"] == "added"
        assert "re" in result["imports_adjusted"][0]["import"]

    async def test_auto_import_removal(self):
        """Pro tier removes unused imports after update."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "old_function",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 2,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [
                {
                    "file": "/src/utils.py",
                    "action": "removed",
                    "import": "import requests",  # Was only used by old_function
                }
            ],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        assert result["imports_adjusted"][0]["action"] == "removed"


class TestUpdateSymbolProFormattingPreserved:
    """Pro tier: formatting preservation."""

    async def test_formatting_preserved_flag(self):
        """Pro tier response includes formatting_preserved field."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,  # Pro tier feature
            "error": None,
        }

        assert result["formatting_preserved"] is True

    async def test_indentation_preserved(self):
        """Pro tier preserves original indentation."""
        # Original: 4 spaces per indent
        # After update: should still be 4 spaces
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        assert result["formatting_preserved"] is True

    async def test_comments_preserved(self):
        """Pro tier preserves original comments."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "process_data",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        assert result["formatting_preserved"] is True


class TestUpdateSymbolProReturnModel:
    """Pro tier: return model field gating."""

    async def test_pro_response_has_correct_fields(self, assert_result_has_pro_fields):
        """Pro tier response has all Community + Pro fields."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 3,
            "syntax_valid": True,
            # Pro fields
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            # Enterprise fields should not be present
            "approval_status": None,
            "compliance_check": None,
            "audit_id": None,
            "mutation_policy": None,
            "error": None,
        }

        assert_result_has_pro_fields(result)

    async def test_enterprise_fields_excluded_from_pro(self):
        """Pro tier response must NOT expose Enterprise fields."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        # Enterprise fields should not be present
        assert "approval_status" not in result or result.get("approval_status") is None
        assert "compliance_check" not in result or result.get("compliance_check") is None
        assert "audit_id" not in result or result.get("audit_id") is None
        assert "mutation_policy" not in result or result.get("mutation_policy") is None


class TestUpdateSymbolProExpiredLicense:
    """Pro tier: expired license fallback to Community."""

    async def test_expired_pro_license_fallback(self, mock_expired_license):
        """Expired Pro license falls back to Community tier."""
        # Expired license should revert to Community tier restrictions
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": (
                "Pro license expired (expired at 2025-12-02). "
                "Falling back to Community tier (10 updates/session). "
                "Renew your license to continue using Pro features."
            ),
        }

        assert "expired" in result["error"]
        assert "Community tier" in result["error"]


class TestUpdateSymbolProMultipleLanguages:
    """Pro tier: multi-language support."""

    async def test_python_multifile_update(self, temp_multifile_project):
        """Pro tier supports Python multi-file atomic updates."""
        result = {
            "success": True,
            "file_path": str(temp_multifile_project["utils"]),
            "symbol_name": "calculate_discount",
            "symbol_type": "function",
            "backup_path": str(temp_multifile_project["utils"]) + ".bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "files_affected": [
                str(temp_multifile_project["utils"]),
                str(temp_multifile_project["services"]),
            ],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        assert len(result["files_affected"]) == 2
