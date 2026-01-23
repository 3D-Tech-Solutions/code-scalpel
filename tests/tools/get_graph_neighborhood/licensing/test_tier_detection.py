"""
[20260105_TEST] Tier detection tests for get_graph_neighborhood.

Tests that tier is correctly detected from real license claims (not mocked).
Validates tier extraction from JWT payload and environment variable precedence.
"""

import os
from pathlib import Path

import pytest

from code_scalpel.mcp.server import _get_current_tier

LICENSE_DIR = Path(__file__).parent.parent.parent.parent / "licenses"


@pytest.fixture(autouse=True)
def clear_license_cache():
    """Clear license validation cache before and after each test."""
    from code_scalpel.licensing import config_loader, jwt_validator
    from code_scalpel.mcp import server

    # Clear before test
    jwt_validator._LICENSE_VALIDATION_CACHE = None
    config_loader.clear_cache()
    if hasattr(server, "_cached_tier"):
        server._cached_tier = None
    if hasattr(server, "_LAST_VALID_LICENSE_AT"):
        server._LAST_VALID_LICENSE_AT = None
    if hasattr(server, "_LAST_VALID_LICENSE_TIER"):
        server._LAST_VALID_LICENSE_TIER = None

    # Clear environment variables
    os.environ.pop("CODE_SCALPEL_TIER", None)
    os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
    os.environ.pop("CODE_SCALPEL_LICENSE_KEY", None)
    os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)
    os.environ.pop("CODE_SCALPEL_TEST_FORCE_TIER", None)

    yield

    # Clear after test
    jwt_validator._LICENSE_VALIDATION_CACHE = None
    config_loader.clear_cache()
    if hasattr(server, "_cached_tier"):
        server._cached_tier = None
    if hasattr(server, "_LAST_VALID_LICENSE_AT"):
        server._LAST_VALID_LICENSE_AT = None
    if hasattr(server, "_LAST_VALID_LICENSE_TIER"):
        server._LAST_VALID_LICENSE_TIER = None

    os.environ.pop("CODE_SCALPEL_TIER", None)
    os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
    os.environ.pop("CODE_SCALPEL_LICENSE_KEY", None)
    os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)
    os.environ.pop("CODE_SCALPEL_TEST_FORCE_TIER", None)


class TestTierDetectionFromLicense:
    """Test tier detection from JWT license claims."""

    def test_pro_tier_detected_from_license(self, monkeypatch):
        """Pro license should be detected from JWT 'tier' claim."""
        pro_licenses = list(LICENSE_DIR.glob("code_scalpel_license_pro_*.jwt"))
        pro_licenses = [lic for lic in pro_licenses if "broken" not in lic.name]

        if not pro_licenses:
            pytest.skip("No valid Pro license found")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(pro_licenses[0]))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier == "pro", f"Expected pro tier from license, got {tier}"

    def test_enterprise_tier_detected_from_license(self, monkeypatch):
        """Enterprise license should be detected from JWT 'tier' claim."""
        enterprise_licenses = list(LICENSE_DIR.glob("code_scalpel_license_enterprise_*.jwt"))
        enterprise_licenses = [lic for lic in enterprise_licenses if "broken" not in lic.name]

        if not enterprise_licenses:
            pytest.skip("No valid Enterprise license found")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(enterprise_licenses[0]))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier == "enterprise", f"Expected enterprise tier from license, got {tier}"

    def test_community_tier_when_no_license(self, monkeypatch, tmp_path):
        """No license should default to Community tier."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(tmp_path / "nonexistent.jwt"))

        tier = _get_current_tier()
        assert tier == "community", f"Expected community tier without license, got {tier}"


class TestTierNormalization:
    """Test tier name normalization and case handling."""

    def test_tier_names_normalized_to_lowercase(self, monkeypatch):
        """Tier names should be normalized to lowercase."""
        pro_licenses = list(LICENSE_DIR.glob("code_scalpel_license_pro_*.jwt"))
        pro_licenses = [lic for lic in pro_licenses if "broken" not in lic.name]

        if not pro_licenses:
            pytest.skip("No valid Pro license found")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(pro_licenses[0]))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier.islower(), f"Tier should be lowercase, got {tier}"
        assert tier in ["community", "pro", "enterprise"]


class TestEnvironmentVariablePrecedence:
    """Test precedence of environment variables in tier detection."""

    def test_license_path_takes_precedence_over_discovery(self, monkeypatch):
        """Explicit LICENSE_PATH should take precedence over discovery."""
        pro_licenses = list(LICENSE_DIR.glob("code_scalpel_license_pro_*.jwt"))
        pro_licenses = [lic for lic in pro_licenses if "broken" not in lic.name]

        if not pro_licenses:
            pytest.skip("No valid Pro license found")

        # Set explicit path and disable discovery
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(pro_licenses[0]))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier == "pro"

    def test_disable_discovery_with_no_path_uses_community(self, monkeypatch, tmp_path):
        """Disabling discovery without explicit path should default to Community."""
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        # No LICENSE_PATH set

        tier = _get_current_tier()
        assert tier == "community", f"Expected community tier when discovery disabled and no path set, got {tier}"


class TestLicenseClaimValidation:
    """Test validation of license claims (tier, sub, iss, aud)."""

    def test_license_with_missing_tier_claim_rejected(self, monkeypatch, tmp_path):
        """License without 'tier' claim should be rejected."""
        # This would require creating a JWT without tier claim, which is complex
        # For now, test that broken licenses fall back to Community
        broken_license = LICENSE_DIR / "code_scalpel_license_pro_test_broken.jwt"

        if not broken_license.exists():
            pytest.skip("Broken test license not found")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(broken_license))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier == "community", f"License with missing claims should fall back to community, got {tier}"

    def test_license_must_have_valid_signature(self, monkeypatch, tmp_path):
        """License with invalid signature should be rejected."""
        fake_jwt = tmp_path / "fake.jwt"
        # Create a JWT-like string with invalid signature
        fake_jwt.write_text("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0aWVyIjoicHJvIn0.invalid_signature")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(fake_jwt))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier = _get_current_tier()
        assert tier == "community", f"License with invalid signature should fall back to community, got {tier}"


class TestCrossToolConsistency:
    """Test that tier detection is consistent across tool invocations."""

    def test_tier_consistent_across_multiple_calls(self, monkeypatch):
        """Tier should remain consistent across multiple _get_current_tier() calls."""
        pro_licenses = list(LICENSE_DIR.glob("code_scalpel_license_pro_*.jwt"))
        pro_licenses = [lic for lic in pro_licenses if "broken" not in lic.name]

        if not pro_licenses:
            pytest.skip("No valid Pro license found")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(pro_licenses[0]))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        # Call multiple times
        tier1 = _get_current_tier()
        tier2 = _get_current_tier()
        tier3 = _get_current_tier()

        assert tier1 == tier2 == tier3 == "pro", f"Tier should be consistent across calls: {tier1}, {tier2}, {tier3}"

    def test_tier_changes_when_license_changed(self, monkeypatch):
        """Tier should update when license environment variable changes."""
        # Start with Pro
        pro_licenses = list(LICENSE_DIR.glob("code_scalpel_license_pro_*.jwt"))
        pro_licenses = [lic for lic in pro_licenses if "broken" not in lic.name]

        if not pro_licenses:
            pytest.skip("No valid Pro license found")

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(pro_licenses[0]))
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

        tier1 = _get_current_tier()
        assert tier1 == "pro"

        # Clear cache and switch to no license (Community)
        from code_scalpel.licensing import config_loader, jwt_validator
        from code_scalpel.mcp import server

        jwt_validator._LICENSE_VALIDATION_CACHE = None
        config_loader.clear_cache()
        if hasattr(server, "_cached_tier"):
            server._cached_tier = None

        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", "/nonexistent/path.jwt")

        tier2 = _get_current_tier()
        assert tier2 == "community", f"Tier should change to community when license removed, got {tier2}"
