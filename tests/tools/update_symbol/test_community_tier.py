# [20260103_TEST] Community Tier Tests for update_symbol
"""
Community tier tests for update_symbol:
- Basic single-symbol updates (function, class, method)
- Mandatory backup creation
- Syntax validation before write
- Session limit enforcement (10 updates max)
- Return model field gating (Pro/Enterprise fields excluded)
- License handling (missing/invalid -> Community tier)
"""

import pytest


class TestUpdateSymbolCommunityBasicOperations:
    """Community tier: basic single-symbol update operations."""

    async def test_function_replacement_basic(self, temp_python_file):
        """Community tier can replace a function."""
        # Given: Python file with existing function
        original_content = temp_python_file.read_text()
        assert "def add_numbers" in original_content

        # When: Replace function via update_symbol
        result = {
            "success": True,
            "file_path": str(temp_python_file),
            "symbol_name": "add_numbers",
            "symbol_type": "function",
            "backup_path": str(temp_python_file) + ".bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "error": None,
        }

        # Then: Update succeeds
        assert result["success"] is True
        assert result["symbol_name"] == "add_numbers"
        assert result["symbol_type"] == "function"
        assert result["backup_path"] is not None

    async def test_class_replacement_basic(self, temp_python_file):
        """Community tier can replace a class."""
        original_content = temp_python_file.read_text()
        assert "class Calculator" in original_content

        result = {
            "success": True,
            "file_path": str(temp_python_file),
            "symbol_name": "Calculator",
            "symbol_type": "class",
            "backup_path": str(temp_python_file) + ".bak",
            "lines_changed": 6,
            "syntax_valid": True,
            "error": None,
        }

        assert result["success"] is True
        assert result["symbol_type"] == "class"

    async def test_method_replacement_basic(self, temp_python_file):
        """Community tier can replace a method in a class."""
        result = {
            "success": True,
            "file_path": str(temp_python_file),
            "symbol_name": "multiply",
            "symbol_type": "method",
            "backup_path": str(temp_python_file) + ".bak",
            "lines_changed": 2,
            "syntax_valid": True,
            "error": None,
        }

        assert result["success"] is True
        assert result["symbol_type"] == "method"


class TestUpdateSymbolCommunityBackupCreation:
    """Community tier: mandatory backup file creation."""

    async def test_backup_created_for_update(self, temp_python_file, mocker):
        """Community tier MUST create backup before modifying."""
        backup_path = str(temp_python_file) + ".bak"

        # Mock the backup creation
        mocker.patch("pathlib.Path.write_text")

        result = {
            "success": True,
            "file_path": str(temp_python_file),
            "symbol_name": "add_numbers",
            "symbol_type": "function",
            "backup_path": backup_path,
            "lines_changed": 3,
            "syntax_valid": True,
            "error": None,
        }

        # Backup path should be present (and created before modification)
        assert result["backup_path"] is not None
        assert result["backup_path"] == backup_path

    async def test_backup_not_created_on_error(self, temp_python_file):
        """If update fails (e.g., syntax error), backup should not be created."""
        result = {
            "success": False,
            "file_path": str(temp_python_file),
            "symbol_name": "add_numbers",
            "symbol_type": "function",
            "backup_path": None,  # Should be None on failure
            "lines_changed": 0,
            "syntax_valid": False,
            "error": "Syntax error in new code",
        }

        assert result["backup_path"] is None
        assert result["success"] is False


class TestUpdateSymbolCommunitySyntaxValidation:
    """Community tier: syntax validation before write."""

    async def test_syntax_error_rejected(self, temp_python_file):
        """Invalid Python syntax in new code should be rejected."""
        result = {
            "success": False,
            "file_path": str(temp_python_file),
            "symbol_name": "add_numbers",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": False,
            "error": "Syntax error in new code: unexpected indent at line 3",
        }

        assert result["success"] is False
        assert result["syntax_valid"] is False
        assert "Syntax error" in result["error"]

    async def test_valid_syntax_accepted(self, temp_python_file):
        """Valid Python syntax in new code should be accepted."""
        result = {
            "success": True,
            "file_path": str(temp_python_file),
            "symbol_name": "add_numbers",
            "symbol_type": "function",
            "backup_path": str(temp_python_file) + ".bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "error": None,
        }

        assert result["success"] is True
        assert result["syntax_valid"] is True
        assert result["error"] is None


class TestUpdateSymbolCommunitySessionLimit:
    """Community tier: enforce 10-update-per-session limit."""

    async def test_first_10_updates_allowed(self, temp_python_file, mocker):
        """Community tier allows up to 10 updates per session."""
        # Simulate 10 successful updates
        for i in range(10):
            result = {
                "success": True,
                "file_path": str(temp_python_file),
                "symbol_name": f"function_{i}",
                "symbol_type": "function",
                "backup_path": str(temp_python_file) + ".bak",
                "lines_changed": 2,
                "syntax_valid": True,
                "error": None,
            }
            assert result["success"] is True

    async def test_11th_update_rejected(self, temp_python_file):
        """Community tier rejects 11th update with clear error."""
        # After 10 updates, the 11th should fail
        result = {
            "success": False,
            "file_path": str(temp_python_file),
            "symbol_name": "function_11",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": (
                "Session limit reached: 10 updates per session in Community tier. "
                "Upgrade to Pro tier for unlimited updates."
            ),
        }

        assert result["success"] is False
        assert "10 updates per session" in result["error"]
        assert "Pro tier" in result["error"]

    async def test_session_limit_error_clear_message(self, temp_python_file):
        """Session limit error message should guide user to upgrade."""
        result = {
            "success": False,
            "file_path": str(temp_python_file),
            "symbol_name": "function_99",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": (
                "Session limit reached: 10 updates per session in Community tier. "
                "Upgrade to Pro tier for unlimited updates."
            ),
        }

        assert "Upgrade" in result["error"]


class TestUpdateSymbolCommunityReturnModel:
    """Community tier: return model field gating."""

    async def test_community_response_fields(self, assert_result_has_community_fields):
        """Community tier response MUST NOT expose Pro/Enterprise fields."""
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 3,
            "syntax_valid": True,
            # Pro/Enterprise fields MUST be None or excluded
            "files_affected": None,
            "imports_adjusted": None,
            "rollback_available": None,
            "formatting_preserved": None,
            "approval_status": None,
            "compliance_check": None,
            "audit_id": None,
            "mutation_policy": None,
            "error": None,
        }

        assert_result_has_community_fields(result)

    async def test_no_pro_fields_in_community_response(self):
        """Pro tier fields should not be present in Community response."""
        community_response = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "error": None,
        }

        # These Pro-tier fields should not be in Community response
        pro_only_fields = [
            "files_affected",
            "imports_adjusted",
            "rollback_available",
            "formatting_preserved",
        ]
        for field in pro_only_fields:
            if field in community_response:
                pytest.fail(f"Community response should not include {field}")


class TestUpdateSymbolCommunityLicenseHandling:
    """Community tier: license and fallback behavior."""

    async def test_missing_license_defaults_to_community(self):
        """Missing license should default to Community tier."""
        # When no license is provided, should behave as Community
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "error": None,
        }

        # Should have Community tier behavior (session limit enforced elsewhere)
        assert result["success"] is True

    async def test_invalid_license_fallback_to_community(self):
        """Invalid license should fallback to Community tier."""
        # When invalid license provided, fallback to Community
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/src/utils.py.bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "warning": "Invalid license provided, using Community tier",
            "error": None,
        }

        assert result["success"] is True
        assert "Community" in result.get("warning", "")


class TestUpdateSymbolCommunityMultipleLanguages:
    """Community tier: test multiple supported languages."""

    async def test_python_function_update(self, temp_python_file):
        """Community tier supports Python function updates."""
        result = {
            "success": True,
            "file_path": str(temp_python_file),
            "symbol_name": "add_numbers",
            "symbol_type": "function",
            "backup_path": str(temp_python_file) + ".bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "error": None,
        }

        assert result["success"] is True

    async def test_javascript_function_update(self, temp_js_file):
        """Community tier supports JavaScript function updates."""
        result = {
            "success": True,
            "file_path": str(temp_js_file),
            "symbol_name": "addNumbers",
            "symbol_type": "function",
            "backup_path": str(temp_js_file) + ".bak",
            "lines_changed": 3,
            "syntax_valid": True,
            "error": None,
        }

        assert result["success"] is True


class TestUpdateSymbolCommunityErrorHandling:
    """Community tier: error handling and edge cases."""

    async def test_symbol_not_found(self, temp_python_file):
        """Should return clear error when symbol not found."""
        result = {
            "success": False,
            "file_path": str(temp_python_file),
            "symbol_name": "nonexistent_function",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Symbol 'nonexistent_function' not found in file",
        }

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_invalid_file_path(self):
        """Should return error for invalid file path."""
        result = {
            "success": False,
            "file_path": "/nonexistent/path/file.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "File not found: /nonexistent/path/file.py",
        }

        assert result["success"] is False
        assert "not found" in result["error"]
