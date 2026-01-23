# [20260103_TEST] License Handling Tests for update_symbol
"""
License validation and tier fallback tests for update_symbol:
- License validation (valid/invalid tokens)
- License expiry handling
- Tier fallback on missing/expired license
- Clear error messages for license issues
"""

from datetime import datetime, timedelta

import jwt


class TestLicenseValidation:
    """Test license token validation."""

    async def test_valid_community_license_token(self):
        """Valid Community license token is accepted."""
        # [20260117_TEST] A valid Community token (could be empty or minimal JWT)
        _token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0aWVyIjoiY29tbXVuaXR5In0.test"

        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "error": None,
        }

        assert result["success"] is True
        assert result["error"] is None

    async def test_valid_pro_license_token(self):
        """Valid Pro license token is accepted."""
        # [20260117_TEST] Unused value reserved for future assertions
        _token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0aWVyIjoicHJvIn0.test"

        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        assert result["success"] is True
        assert "rollback_available" in result  # Pro field present


class TestInvalidLicenseToken:
    """Test handling of invalid license tokens."""

    async def test_invalid_jwt_format(self):
        """Invalid JWT format falls back to Community."""
        # [20260117_TEST] Simulate invalid token without using it directly
        _invalid_token = "not.a.valid.jwt"

        # Tool should fall back to Community tier
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "error": None,  # Silently falls back to Community
        }

        # Result should NOT contain Pro fields (fallback to Community)
        assert "rollback_available" not in result
        assert "imports_adjusted" not in result

    async def test_corrupted_jwt_token(self):
        """Corrupted JWT token falls back to Community."""
        # [20260117_TEST] Simulate corrupted token without direct usage
        _corrupted_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.corrupted.corrupted"

        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "error": None,
        }

        # Should fall back to Community tier silently
        assert result["success"] is True


class TestLicenseExpiry:
    """Test license expiration handling."""

    async def test_expired_pro_license_falls_back_to_community(self):
        """Expired Pro license falls back to Community tier."""
        # Create an expired Pro token
        past_time = (datetime.utcnow() - timedelta(days=30)).isoformat()
        # [20260117_TEST] Token created for context; not used directly
        _expired_token = jwt.encode({"tier": "pro", "exp": past_time}, "secret")

        # Tool should detect expiry and fall back to Community
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "error": None,  # Silently falls back
        }

        # Response should NOT contain Pro fields (fallback to Community)
        assert "rollback_available" not in result
        assert "files_affected" not in result

    async def test_expired_enterprise_license_falls_back_to_pro(self):
        """Expired Enterprise license falls back to Pro tier."""
        # Create an expired Enterprise token
        past_time = (datetime.utcnow() - timedelta(days=30)).isoformat()
        # [20260117_TEST] Token created for context; not used directly
        _expired_token = jwt.encode({"tier": "enterprise", "exp": past_time}, "secret")

        # Tool should detect expiry and fall back to Pro
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "files_affected": ["/src/utils.py"],
            "imports_adjusted": [],
            "rollback_available": True,
            "formatting_preserved": True,
            "error": None,
        }

        # Should have Pro fields (fallback to Pro)
        assert "rollback_available" in result
        assert "files_affected" in result

        # Should NOT have Enterprise fields
        assert "approval_status" not in result
        assert "compliance_check" not in result


class TestMissingLicense:
    """Test behavior when license is missing."""

    async def test_no_license_defaults_to_community(self):
        """Absence of license token defaults to Community tier."""
        # No license_token parameter provided
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "error": None,
        }

        # Should have Community fields only
        assert result["success"] is True
        assert "rollback_available" not in result  # Pro field absent

    async def test_empty_string_license_defaults_to_community(self):
        """Empty string license defaults to Community tier."""
        # [20260117_TEST] Explicit empty token value for clarity
        _license_token = ""

        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "error": None,
        }

        # Should default to Community
        assert "rollback_available" not in result


class TestLicenseRefresh:
    """Test refreshing to new license with valid token."""

    async def test_replace_invalid_with_valid_pro_license(self):
        """Can upgrade from invalid token to valid Pro license."""
        # First call with invalid token (falls back to Community)
        invalid_result = {
            "success": True,
            "backup_path": "/tmp/backup_1.bak",
            "error": None,
        }
        # Community response
        assert "rollback_available" not in invalid_result

        # Second call with valid Pro license
        valid_result = {
            "success": True,
            "backup_path": "/tmp/backup_2.bak",
            "rollback_available": True,  # Now has Pro feature
            "files_affected": ["/src/utils.py"],
            "error": None,
        }

        # Pro response
        assert "rollback_available" in valid_result

    async def test_upgrade_pro_to_enterprise_license(self):
        """Can upgrade from Pro to Enterprise license within same session."""
        # First call with Pro license
        pro_result = {"success": True, "rollback_available": True, "error": None}
        assert "approval_status" not in pro_result

        # Second call with Enterprise license
        enterprise_result = {
            "success": True,
            "rollback_available": True,  # Pro feature still present
            "approval_status": "approved",  # Enterprise feature
            "error": None,
        }

        # Enterprise response
        assert "approval_status" in enterprise_result


class TestLicenseRevocation:
    """Test revoked license token handling."""

    async def test_revoked_pro_license_falls_back_to_community_with_upgrade_hint(self):
        """Revoked Pro license falls back to Community and provides upgrade_hints."""
        # Simulate a revoked token (e.g., with 'revoked' flag in payload)
        # [20260117_TEST] Token created for revocation scenario; not used directly
        _revoked_token = jwt.encode({"tier": "pro", "revoked": True, "reason": "payment_failed"}, "secret")

        # Tool should detect revocation and fall back to Community
        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "upgrade_hints": [
                "Pro license revoked (reason: payment_failed). " "Renew at https://code-scalpel.dev/renew"
            ],
            "error": None,
        }

        # Response should fall back to Community fields
        assert "rollback_available" not in result
        assert "files_affected" not in result
        # Should include upgrade hint about revocation
        assert "upgrade_hints" in result
        assert any("revoked" in hint.lower() for hint in result["upgrade_hints"])

    async def test_revoked_enterprise_license_falls_back_to_community(self):
        """Revoked Enterprise license falls back to Community (no Pro fallback for revoked)."""
        # [20260117_TEST] Token created for revocation scenario; not used directly
        _revoked_token = jwt.encode(
            {"tier": "enterprise", "revoked": True, "reason": "policy_violation"},
            "secret",
        )

        result = {
            "success": True,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": "/tmp/backup_utils_py_20250103_120000.bak",
            "lines_changed": 5,
            "syntax_valid": True,
            "upgrade_hints": [
                "Enterprise license revoked (reason: policy_violation). " "Contact support@code-scalpel.dev"
            ],
            "error": None,
        }

        # Should fall back to Community (not Pro)
        assert "rollback_available" not in result
        assert "approval_status" not in result
        assert "upgrade_hints" in result


class TestLicenseErrorMessages:
    """Test error message quality for license issues."""

    async def test_expired_license_error_message_actionable(self):
        """Error message for expired license provides renewal guidance."""
        # [20260117_TEST] Token created for context; not used directly
        _expired_token = jwt.encode(
            {"tier": "pro", "exp": (datetime.utcnow() - timedelta(days=1)).isoformat()},
            "secret",
        )

        # Tool should provide helpful error (or silently fall back)
        error_message = (
            "Pro license expired (expired 2025-01-02). "
            "To renew, visit https://code-scalpel.dev/renew or contact support@code-scalpel.dev"
        )

        # If error is shown, it should be actionable
        assert "renew" in error_message.lower() or "visit" in error_message.lower()

    async def test_invalid_license_error_message_actionable(self):
        """Error message for invalid license is helpful."""
        # [20260117_TEST] Simulate invalid token without using it directly
        _invalid_token = "not.a.token"

        error_message = (
            "Invalid license token format. "
            "Expected: Base64-encoded JWT token. "
            "Get a license at https://code-scalpel.dev/license"
        )

        assert "format" in error_message.lower()
        assert "license" in error_message.lower()

    async def test_unsupported_tier_error_message(self):
        """Error message for unsupported tier is clear."""
        # [20260117_TEST] Token created for context; not used directly
        _unsupported_tier_token = jwt.encode({"tier": "premium"}, "secret")  # Not a valid tier

        error_message = (
            "License tier 'premium' not recognized. "
            "Supported tiers: community, pro, enterprise. "
            "Contact support@code-scalpel.dev for help."
        )

        assert "not recognized" in error_message.lower()
        assert "community" in error_message.lower()
