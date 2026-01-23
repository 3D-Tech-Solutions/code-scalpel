"""
Integration Tests for JWT License System with Tool Handlers

[20251225_TEST] Test JWT license validation integrated with tool capabilities

Tests cover:
- Tool capabilities based on license tier
- Limit enforcement in tool handlers
- Feature availability checks
- Tier-based tool behavior
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if JWT_AVAILABLE:
    from code_scalpel.licensing import (
        get_current_tier,
        get_license_info,
        get_tool_capabilities,
    )
    from code_scalpel.licensing.jwt_generator import generate_license


pytestmark = pytest.mark.skipif(not JWT_AVAILABLE, reason="PyJWT not installed")


TEST_SECRET_KEY = "test_secret_key_12345"


@pytest.fixture
def clean_env():
    """Clean environment variables."""
    original = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
    original_secret = os.environ.get("CODE_SCALPEL_SECRET_KEY")
    original_allow_hs256 = os.environ.get("CODE_SCALPEL_ALLOW_HS256")
    os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
    os.environ["CODE_SCALPEL_SECRET_KEY"] = TEST_SECRET_KEY
    # [20251227_TEST] HS256 is dev-only and requires explicit opt-in
    os.environ["CODE_SCALPEL_ALLOW_HS256"] = "1"
    yield
    if original:
        os.environ["CODE_SCALPEL_LICENSE_PATH"] = original
    else:
        os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)

    if original_secret is not None:
        os.environ["CODE_SCALPEL_SECRET_KEY"] = original_secret
    else:
        os.environ.pop("CODE_SCALPEL_SECRET_KEY", None)

    if original_allow_hs256 is not None:
        os.environ["CODE_SCALPEL_ALLOW_HS256"] = original_allow_hs256
    else:
        os.environ.pop("CODE_SCALPEL_ALLOW_HS256", None)


class TestToolCapabilitiesByTier:
    """Test tool capabilities for each tier."""

    def test_community_tier_capabilities(self, clean_env):
        """Test Community tier has basic capabilities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                tier = get_current_tier()
                assert tier == "community"

                # Check security_scan capabilities
                caps = get_tool_capabilities("security_scan", tier)

                assert caps is not None
                assert "capabilities" in caps
                assert "limits" in caps
                # [20251227_FIX] Updated to match limits.toml: community has 50 max findings
                assert caps.get("limits", {}).get("max_findings") == 50

            finally:
                os.chdir(original_cwd)

    def test_pro_tier_capabilities(self, clean_env):
        """Test Pro tier has enhanced capabilities."""
        token = generate_license(
            tier="pro",
            customer_id="test",
            duration_days=365,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            tier = get_current_tier()
            assert tier == "pro"

        # Check security_scan capabilities
        caps = get_tool_capabilities("security_scan", tier)

        # Pro should have more capabilities
        # [20251227_FIX] Test actual capabilities returned (TOML merge not implemented yet)
        assert "context_aware_scanning" in caps.get("capabilities", [])
        assert "sanitizer_recognition" in caps.get("capabilities", [])
        # Pro may not have a findings limit (unlimited)
        pro_limit = caps.get("limits", {}).get("max_findings")
        assert pro_limit is None or pro_limit > 50

    def test_enterprise_tier_capabilities(self, clean_env):
        """Test Enterprise tier has all capabilities."""
        token = generate_license(
            tier="enterprise",
            customer_id="test",
            duration_days=365,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            tier = get_current_tier()
            assert tier == "enterprise"

        # Check security_scan capabilities
        caps = get_tool_capabilities("security_scan", tier)

        # Enterprise should have compliance features
        # [20251227_FIX] Test actual capabilities (custom_policy_engine is in Enterprise)
        assert "custom_policy_engine" in caps.get("capabilities", [])
        assert "compliance_rule_checking" in caps.get("capabilities", [])
        # Enterprise has no limits
        assert caps.get("limits", {}).get("max_findings") is None


class TestToolHandlerIntegration:
    """Test integration with tool handlers."""

    def test_tool_handler_respects_tier_limits(self, clean_env):
        """Test that tool handlers respect tier-based limits."""

        # Simulate security_scan tool handler
        def mock_security_scan(code: str):
            tier = get_current_tier()
            caps = get_tool_capabilities("security_scan", tier)

            # Simulate finding 15 vulnerabilities
            findings = list(range(1, 16))

            # Apply tier limits
            max_findings = caps.get("limits", {}).get("max_findings")
            if max_findings:
                findings = findings[:max_findings]

            return {
                "findings": findings,
                "tier": tier,
                "applied_limit": max_findings,
            }

        # Test with Community tier
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                result = mock_security_scan("test code")

                assert result["tier"] == "community"
                # [20251227_FIX] Updated to match limits.toml: community has 50 max findings
                assert result["applied_limit"] == 50
                # We're simulating 15 findings, so all 15 should be returned (under the 50 limit)
                assert len(result["findings"]) == 15

            finally:
                os.chdir(original_cwd)

    def test_tool_handler_adds_features(self, clean_env):
        """Test that tool handlers add tier-specific features."""

        # Simulate tool with conditional features
        def mock_crawl_project():
            tier = get_current_tier()
            caps = get_tool_capabilities("crawl_project", tier)

            result = {
                "files": ["file1.py", "file2.py"],
                "tier": tier,
            }

            # Add framework detection if available in Pro+
            if "framework_entrypoint_detection" in caps.get("capabilities", []):
                result["frameworks"] = ["Django", "FastAPI"]

            # Add incremental indexing if available in Enterprise
            if "incremental_indexing" in caps.get("capabilities", []):
                result["incremental"] = True

            return result

        # Test with Community
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                result = mock_crawl_project()

                assert result["tier"] == "community"
                assert "frameworks" not in result  # Not in Community
                assert "incremental" not in result  # Not in Community

            finally:
                os.chdir(original_cwd)

        # Test with Pro
        token = generate_license(
            tier="pro",
            customer_id="test",
            duration_days=365,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            result = mock_crawl_project()

            assert result["tier"] == "pro"
            assert "frameworks" in result  # In Pro


class TestLicenseInfoDisplay:
    """Test license info for user display."""

    def test_license_info_community(self, clean_env):
        """Test license info display for Community tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                info = get_license_info()

                assert info["tier"] == "community"
                assert info["is_valid"] is True
                assert info["customer_id"] == ""
                assert info["organization"] is None

            finally:
                os.chdir(original_cwd)

    def test_license_info_pro(self, clean_env):
        """Test license info display for Pro tier."""
        token = generate_license(
            tier="pro",
            customer_id="acme_123",
            organization="Acme Corporation",
            duration_days=365,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            info = get_license_info()

        assert info["tier"] == "pro"
        assert info["is_valid"] is True
        assert info["customer_id"] == "acme_123"
        assert info["organization"] == "Acme Corporation"
        assert info["days_until_expiration"] > 0

    def test_license_info_enterprise_seats(self, clean_env):
        """Test license info displays seat count for Enterprise."""
        token = generate_license(
            tier="enterprise",
            customer_id="bigtech_456",
            organization="Big Tech Inc",
            seats=50,
            duration_days=730,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            info = get_license_info()

        assert info["tier"] == "enterprise"
        assert info["seats"] == 50
        assert info["organization"] == "Big Tech Inc"


class TestMultipleTiersSequence:
    """Test switching between different tiers."""

    def test_switch_from_community_to_pro(self, clean_env):
        """Test that switching from Community to Pro works."""
        # Start with Community
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                assert get_current_tier() == "community"

                # Install Pro license
                token = generate_license(
                    tier="pro",
                    customer_id="test",
                    duration_days=365,
                    algorithm="HS256",
                    secret_key=TEST_SECRET_KEY,
                )

                license_path = Path(tmpdir) / "license.jwt"
                license_path.write_text(token)
                os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

                assert get_current_tier() == "pro"

                # Tool capabilities change
                community_caps = get_tool_capabilities("analyze_code", "community")
                pro_caps = get_tool_capabilities("analyze_code", "pro")

                # Pro has more capabilities
                assert len(pro_caps.get("capabilities", [])) > len(community_caps.get("capabilities", []))

            finally:
                os.chdir(original_cwd)

    def test_license_expiration_downgrade(self, clean_env):
        """Test that license expiration downgrades to Community."""
        from datetime import datetime, timedelta

        # Create expired license
        now = datetime.utcnow()
        expired_date = now - timedelta(days=10)  # Expired 10 days ago

        claims = {
            "iss": "code-scalpel-licensing",
            "aud": "code-scalpel",
            "sub": "test",
            "jti": "test-expired-10d-jti",
            "tier": "pro",
            "features": [],
            "exp": int(expired_date.timestamp()),
            "iat": int((expired_date - timedelta(days=365)).timestamp()),
        }

        token = jwt.encode(claims, TEST_SECRET_KEY, algorithm="HS256")

        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            # Should downgrade to community (beyond grace period)
            info = get_license_info()

            assert info["is_expired"] is True
            assert info["is_in_grace_period"] is False

            tier = get_current_tier()
            assert tier == "community"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
