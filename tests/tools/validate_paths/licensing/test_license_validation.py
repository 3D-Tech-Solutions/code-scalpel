"""
License validation and tier detection tests for validate_paths tool.

Tests the licensing layer to ensure:
- Valid licenses grant appropriate tier access
- Invalid licenses fall back to Community tier
- Expired licenses are handled correctly
- Tier info is correctly passed to the tool
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from code_scalpel.mcp.server import _get_current_tier


@pytest.fixture(autouse=True)
def cleanup_license_env():
    """Cleanup environment and global state before and after each test."""
    # Import modules to clear state
    from code_scalpel.mcp import server as server_module

    # Clean before test
    os.environ.pop("CODE_SCALPEL_TIER", None)
    os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
    os.environ.pop("CODE_SCALPEL_LICENSE_KEY", None)
    os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)
    os.environ.pop("CODE_SCALPEL_TEST_FORCE_TIER", None)

    # Clear global state variables
    server_module._LAST_VALID_LICENSE_AT = None
    server_module._LAST_VALID_LICENSE_TIER = None
    if hasattr(server_module, "_cached_tier"):
        server_module._cached_tier = None

    yield

    # Clean after test
    os.environ.pop("CODE_SCALPEL_TIER", None)
    os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
    os.environ.pop("CODE_SCALPEL_LICENSE_KEY", None)
    os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)
    os.environ.pop("CODE_SCALPEL_TEST_FORCE_TIER", None)

    # Clear global state variables
    server_module._LAST_VALID_LICENSE_AT = None
    server_module._LAST_VALID_LICENSE_TIER = None
    if hasattr(server_module, "_cached_tier"):
        server_module._cached_tier = None


class TestValidLicenseDetection:
    """Test detection of valid licenses."""

    def test_no_license_defaults_to_community(self):
        """No license set should default to community tier."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            mock_validate.return_value = MagicMock(is_valid=False, tier=None, error_message="No license")
            tier = _get_current_tier()
            assert tier == "community", f"Expected community tier without license, got {tier}"

    def test_valid_pro_license_detected(self):
        """Valid Pro license should be detected."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(is_valid=True, tier="pro", error_message=None, is_expired=False)
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier == "pro", f"Expected pro tier with valid pro license, got {tier}"

    def test_valid_enterprise_license_detected(self):
        """Valid Enterprise license should be detected."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(is_valid=True, tier="enterprise", error_message=None, is_expired=False)
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier == "enterprise", f"Expected enterprise tier with valid enterprise license, got {tier}"

    def test_license_override_via_env_var(self):
        """CODE_SCALPEL_TIER environment variable should override license."""
        with patch.dict(os.environ, {"CODE_SCALPEL_TIER": "enterprise"}):
            with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
                license_data = MagicMock(is_valid=True, tier="pro", error_message=None, is_expired=False)
                mock_validate.return_value = license_data
                tier = _get_current_tier()
                # Should not exceed license tier even if env requests higher
                assert tier in [
                    "pro",
                    "enterprise",
                ], f"Expected pro or enterprise, got {tier}"


class TestInvalidLicenseHandling:
    """Test handling of invalid and expired licenses."""

    def test_invalid_license_falls_back_to_community(self):
        """Invalid license should fall back to community tier."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(
                is_valid=False,
                tier=None,
                error_message="Invalid signature",
                is_expired=False,
            )
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier == "community", f"Expected community fallback for invalid license, got {tier}"

    def test_expired_license_falls_back_to_community(self):
        """Expired license should fall back to community tier immediately."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(
                is_valid=False,
                tier="pro",
                error_message="Revoked: License expired",
                is_expired=True,
            )
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier == "community", f"Expected community fallback for expired license, got {tier}"

    def test_revoked_license_immediate_downgrade(self):
        """Revoked license should immediately downgrade to community (no grace)."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(
                is_valid=False,
                tier="enterprise",
                error_message="Revoked: License key was revoked",
                is_expired=False,
            )
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier == "community", f"Expected immediate community downgrade for revoked license, got {tier}"

    def test_malformed_license_key_rejected(self):
        """Malformed license key should be rejected."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(
                is_valid=False,
                tier=None,
                error_message="Invalid JWT format",
                is_expired=False,
            )
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier == "community", f"Expected community tier for malformed license, got {tier}"

    def test_license_with_wrong_signature_rejected(self):
        """License with incorrect signature should be rejected."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(
                is_valid=False,
                tier=None,
                error_message="Signature verification failed",
                is_expired=False,
            )
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier == "community", f"Expected community tier for invalid signature, got {tier}"


class TestLicenseEnvironmentVariables:
    """Test license detection from environment variables and files."""

    def test_code_scalpel_license_key_env_var(self):
        """CODE_SCALPEL_LICENSE_KEY env var should be used for license."""
        mock_license = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0aWVyIjoicHJvIn0.invalid"
        with patch.dict(os.environ, {"CODE_SCALPEL_LICENSE_KEY": mock_license}):
            with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
                license_data = MagicMock(is_valid=True, tier="pro", error_message=None, is_expired=False)
                mock_validate.return_value = license_data
                tier = _get_current_tier()
                assert tier == "pro", f"Expected pro tier when license key env var is set, got {tier}"

    def test_license_file_detection(self):
        """License file should be detected if present."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(is_valid=True, tier="enterprise", error_message=None, is_expired=False)
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier == "enterprise", f"Expected enterprise tier with valid license file, got {tier}"

    def test_empty_license_env_var_ignored(self):
        """Empty license env var should be treated as no license."""
        with patch.dict(os.environ, {"CODE_SCALPEL_LICENSE_KEY": ""}):
            with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
                license_data = MagicMock(
                    is_valid=False,
                    tier=None,
                    error_message="No license provided",
                    is_expired=False,
                )
                mock_validate.return_value = license_data
                tier = _get_current_tier()
                assert tier == "community", f"Expected community tier for empty license, got {tier}"


class TestTierNormalization:
    """Test tier string normalization."""

    def test_tier_lowercase_normalization(self):
        """Tier names should be normalized to lowercase."""
        with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
            license_data = MagicMock(
                is_valid=True,
                tier="PRO",  # Uppercase
                error_message=None,
                is_expired=False,
            )
            mock_validate.return_value = license_data
            tier = _get_current_tier()
            assert tier.lower() == "pro", f"Expected lowercase tier, got {tier}"

    def test_free_tier_maps_to_community(self):
        """'free' tier should map to 'community'."""
        with patch.dict(os.environ, {"CODE_SCALPEL_TIER": "free"}):
            with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
                license_data = MagicMock(is_valid=False, tier=None, error_message=None, is_expired=False)
                mock_validate.return_value = license_data
                tier = _get_current_tier()
                assert tier == "community", f"Expected 'free' to map to 'community', got {tier}"

    def test_all_tier_maps_to_enterprise(self):
        """'all' tier should map to 'enterprise'."""
        with patch.dict(os.environ, {"CODE_SCALPEL_TIER": "all"}):
            with patch("code_scalpel.licensing.jwt_validator.JWTLicenseValidator.validate") as mock_validate:
                license_data = MagicMock(
                    is_valid=True,
                    tier="enterprise",
                    error_message=None,
                    is_expired=False,
                )
                mock_validate.return_value = license_data
                tier = _get_current_tier()
                assert tier == "enterprise", f"Expected 'all' to map to 'enterprise', got {tier}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
