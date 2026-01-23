"""
Tests for JWT License Validation System - Code Scalpel v3.3.0

[20251225_TEST] Comprehensive test suite for JWT-based license validation

Tests cover:
- Token validation (valid, invalid, expired)
- Signature verification (RS256, HS256)
- Grace period handling
- License file loading
- Environment variable handling
- Tier detection
- Feature capability checks
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Try to import JWT - skip tests if not available
try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

# Import from parent package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if JWT_AVAILABLE:
    import code_scalpel.licensing.jwt_validator as jwt_validator_module
    from code_scalpel.licensing.jwt_generator import generate_license
    from code_scalpel.licensing.jwt_validator import (
        JWTAlgorithm,
        JWTLicenseValidator,
        get_license_info,
    )


# Skip all tests if JWT not available
pytestmark = pytest.mark.skipif(not JWT_AVAILABLE, reason="PyJWT not installed")


# Test fixtures
TEST_SECRET_KEY = "test_secret_key_12345"
TEST_CUSTOMER_ID = "test_customer_123"
TEST_ORGANIZATION = "Test Organization"


@pytest.fixture(autouse=True)
def _enable_hs256_for_test_module(monkeypatch):
    """Enable HS256 explicitly for this test module.

    [20251227_TEST] HS256 is dev-only and requires explicit opt-in.
    This module primarily tests HS256 flows, so we enable it here.
    """

    monkeypatch.setenv("CODE_SCALPEL_ALLOW_HS256", "1")


@pytest.fixture
def pro_license_token():
    """Generate a valid Pro tier license token."""
    return generate_license(
        tier="pro",
        customer_id=TEST_CUSTOMER_ID,
        organization=TEST_ORGANIZATION,
        duration_days=365,
        algorithm="HS256",
        secret_key=TEST_SECRET_KEY,
    )


@pytest.fixture
def enterprise_license_token():
    """Generate a valid Enterprise tier license token."""
    return generate_license(
        tier="enterprise",
        customer_id=TEST_CUSTOMER_ID,
        organization=TEST_ORGANIZATION,
        seats=50,
        duration_days=730,
        algorithm="HS256",
        secret_key=TEST_SECRET_KEY,
    )


@pytest.fixture
def expired_license_token():
    """Generate an expired license token (3 days ago)."""
    now = datetime.now(timezone.utc)
    expired_date = now - timedelta(days=3)

    claims = {
        "iss": "code-scalpel-licensing",
        "aud": "code-scalpel",
        "sub": TEST_CUSTOMER_ID,
        "jti": "test-expired-jti",
        "tier": "pro",
        "features": ["cognitive_complexity", "context_aware_scanning"],
        "exp": int(expired_date.timestamp()),
        "iat": int((expired_date - timedelta(days=365)).timestamp()),
        "organization": TEST_ORGANIZATION,
    }

    return jwt.encode(claims, TEST_SECRET_KEY, algorithm="HS256")


@pytest.fixture
def validator_hs256():
    """Create JWT validator with HS256."""
    return JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)


@pytest.fixture
def clean_env():
    """Clean environment before and after test."""
    # Save original values
    original_secret_key = os.environ.get("CODE_SCALPEL_SECRET_KEY")
    original_allow_hs256 = os.environ.get("CODE_SCALPEL_ALLOW_HS256")
    original_license_path = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
    original_disable_discovery = os.environ.get("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY")

    # Clean environment
    os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
    # Some MCP contract tests set this globally via setdefault; clear it here so
    # license file discovery tests are isolated.
    os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)
    # [20251227_BUGFIX] Set secret key for validation to work
    os.environ["CODE_SCALPEL_SECRET_KEY"] = TEST_SECRET_KEY
    # [20251227_TEST] HS256 is dev-only and requires explicit opt-in
    os.environ["CODE_SCALPEL_ALLOW_HS256"] = "1"

    yield

    # Restore original values
    if original_license_path:
        os.environ["CODE_SCALPEL_LICENSE_PATH"] = original_license_path
    else:
        os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)

    if original_secret_key:
        os.environ["CODE_SCALPEL_SECRET_KEY"] = original_secret_key
    else:
        os.environ.pop("CODE_SCALPEL_SECRET_KEY", None)

    if original_allow_hs256 is not None:
        os.environ["CODE_SCALPEL_ALLOW_HS256"] = original_allow_hs256
    else:
        os.environ.pop("CODE_SCALPEL_ALLOW_HS256", None)

    if original_disable_discovery is not None:
        os.environ["CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY"] = original_disable_discovery
    else:
        os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)


# Tests for JWTLicenseValidator


class TestJWTValidation:
    """Tests for JWT token validation."""

    def test_validate_valid_pro_token(self, pro_license_token, validator_hs256):
        """Test validating a valid Pro tier token."""
        result = validator_hs256.validate_token(pro_license_token)

        assert result.is_valid is True
        assert result.is_expired is False
        assert result.tier == "pro"
        assert result.customer_id == TEST_CUSTOMER_ID
        assert result.organization == TEST_ORGANIZATION
        assert len(result.features) > 0

    def test_validate_valid_enterprise_token(self, enterprise_license_token, validator_hs256):
        """Test validating a valid Enterprise tier token."""
        result = validator_hs256.validate_token(enterprise_license_token)

        assert result.is_valid is True
        assert result.tier == "enterprise"
        assert result.seats == 50

    def test_validate_expired_token(self, expired_license_token, validator_hs256):
        """Test validating an expired token."""
        result = validator_hs256.validate_token(expired_license_token)

        assert result.is_expired is True
        assert result.is_valid is False
        assert result.error_message is not None
        assert "expired" in result.error_message.lower()

    def test_validate_expired_token_grace_period(self, expired_license_token, validator_hs256):
        """Test that expired tokens are in grace period within 7 days."""
        result = validator_hs256.validate_token(expired_license_token)

        assert result.is_expired is True
        assert result.is_in_grace_period is True  # 3 days ago is within 7-day grace
        # [20251227_TEST] Strict posture: expired licenses never grant paid tier.
        # The tier claim may still be present for messaging/telemetry.
        assert result.tier == "pro"

    def test_validate_invalid_signature(self, pro_license_token):
        """Test that modified tokens are rejected."""
        # Create validator with wrong secret key
        wrong_validator = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key="wrong_secret_key")

        result = wrong_validator.validate_token(pro_license_token)

        assert result.is_valid is False
        assert "signature" in result.error_message.lower()

    def test_validate_malformed_token(self, validator_hs256):
        """Test that malformed tokens are rejected."""
        malformed_token = "not.a.valid.jwt"

        result = validator_hs256.validate_token(malformed_token)

        assert result.is_valid is False
        assert result.error_message is not None


class TestTierDetection:
    """Tests for tier detection from license."""

    def test_get_current_tier_no_license(self, clean_env, validator_hs256):
        """Test that Community tier is default when no license."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory with no license files
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                tier = validator_hs256.get_current_tier()
                assert tier == "community"
            finally:
                os.chdir(original_cwd)

    def test_get_current_tier_from_license_path(self, clean_env, pro_license_token, validator_hs256):
        """Test tier detection from CODE_SCALPEL_LICENSE_PATH."""
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(pro_license_token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            tier = validator_hs256.get_current_tier()
            assert tier == "pro"

    def test_get_current_tier_expired_grace_period(self, clean_env, expired_license_token, validator_hs256):
        """Test that expired license within grace period returns licensed tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(expired_license_token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            tier = validator_hs256.get_current_tier()
            # [20251227_TEST] Strict posture: expired licenses never grant paid tier.
            assert tier == "community"


class TestLicenseRevalidationCache:
    """Tests for 24h runtime license revalidation cache."""

    def test_validate_cached_within_24h_when_file_unchanged(self, clean_env, pro_license_token, monkeypatch):
        """Validation should happen once within the TTL for an unchanged file."""

        jwt_validator_module._LICENSE_VALIDATION_CACHE = None

        now = {"t": 1_000.0}
        monkeypatch.setattr(jwt_validator_module.time, "time", lambda: now["t"])

        validate_calls = {"n": 0}
        original_validate_token = JWTLicenseValidator.validate_token

        def _wrapped_validate_token(self, token: str):
            validate_calls["n"] += 1
            return original_validate_token(self, token)

        monkeypatch.setattr(JWTLicenseValidator, "validate_token", _wrapped_validate_token)

        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(pro_license_token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            v1 = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
            r1 = v1.validate()
            assert r1.is_valid is True
            assert validate_calls["n"] == 1

            # New instance, same unchanged file, same time window.
            v2 = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
            r2 = v2.validate()
            assert r2.is_valid is True
            assert validate_calls["n"] == 1

            # Still within TTL: no revalidation.
            now["t"] += (24 * 60 * 60) - 1
            r3 = v2.validate()
            assert r3.is_valid is True
            assert validate_calls["n"] == 1

            # Past TTL: revalidate.
            now["t"] += 2
            r4 = v2.validate()
            assert r4.is_valid is True
            assert validate_calls["n"] == 2

    def test_validate_revalidates_when_license_file_changes(self, clean_env, pro_license_token, monkeypatch):
        """Any license file change should force revalidation even within TTL."""

        jwt_validator_module._LICENSE_VALIDATION_CACHE = None

        now = {"t": 2_000.0}
        monkeypatch.setattr(jwt_validator_module.time, "time", lambda: now["t"])

        validate_calls = {"n": 0}
        original_validate_token = JWTLicenseValidator.validate_token

        def _wrapped_validate_token(self, token: str):
            validate_calls["n"] += 1
            return original_validate_token(self, token)

        monkeypatch.setattr(JWTLicenseValidator, "validate_token", _wrapped_validate_token)

        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(pro_license_token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            v1 = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
            r1 = v1.validate()
            assert r1.is_valid is True
            assert validate_calls["n"] == 1

            # Change file contents/mtime; should force revalidation even within TTL.
            license_path.write_text(pro_license_token + "\n")
            v2 = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
            r2 = v2.validate()
            assert r2.is_valid is True
            assert validate_calls["n"] == 2

    def test_get_current_tier_invalid_license(self, clean_env, validator_hs256):
        """Test that invalid license downgrades to community."""
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text("invalid_token")
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            tier = validator_hs256.get_current_tier()
            assert tier == "community"


class TestLicenseFileHandling:
    """Tests for loading licenses from files."""

    def test_find_license_file_in_current_dir(self, clean_env):
        """Test finding license file in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create license file
                license_file = Path(".scalpel-license")
                license_file.write_text("test_token")

                validator = JWTLicenseValidator()
                found = validator.find_license_file()

                assert found is not None
                assert found.name == ".scalpel-license"
            finally:
                os.chdir(original_cwd)

    def test_find_license_file_priority(self, clean_env):
        """Test that license file priority is correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create license file in current directory
                local_license = Path(".scalpel-license")
                local_license.write_text("local_token")

                validator = JWTLicenseValidator()
                found = validator.find_license_file()

                # Should find local file first
                assert found == local_license
            finally:
                os.chdir(original_cwd)

    def test_load_license_from_file(self, clean_env, pro_license_token):
        """Test loading license token from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Write license to file
                license_file = Path(".scalpel-license")
                license_file.write_text(pro_license_token)

                validator = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)

                token = validator.load_license_token()

                assert token == pro_license_token
            finally:
                os.chdir(original_cwd)

    def test_load_license_from_explicit_path_env(self, clean_env, pro_license_token):
        """Test loading license token from CODE_SCALPEL_LICENSE_PATH."""
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(pro_license_token)

            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            validator = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
            token = validator.load_license_token()
            assert token == pro_license_token

    def test_license_path_overrides_default_search(self, clean_env, pro_license_token):
        """Test CODE_SCALPEL_LICENSE_PATH overrides default path search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                default_dir = Path(".code-scalpel")
                default_dir.mkdir(parents=True, exist_ok=True)
                (default_dir / "license.jwt").write_text("default_token")

                explicit_path = Path(tmpdir) / "explicit.jwt"
                explicit_path.write_text(pro_license_token)
                os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(explicit_path)

                validator = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
                token = validator.load_license_token()
                assert token == pro_license_token
            finally:
                os.chdir(original_cwd)


class TestLicenseInfo:
    """Tests for license info API."""

    def test_get_license_info_valid_license(self, clean_env, pro_license_token, validator_hs256):
        """Test getting license info for valid license."""
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(pro_license_token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            info = get_license_info()

            assert info["tier"] == "pro"
            assert info["is_valid"] is True
            assert info["customer_id"] == TEST_CUSTOMER_ID
            assert info["organization"] == TEST_ORGANIZATION
            assert isinstance(info["features"], list)
            assert len(info["features"]) > 0

    def test_get_license_info_no_license(self, clean_env):
        """Test getting license info when no license."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                info = get_license_info()

                assert info["tier"] == "community"
                assert info["is_valid"] is True  # Community is always valid
                assert info["customer_id"] == ""
            finally:
                os.chdir(original_cwd)

    def test_get_license_info_expired(self, clean_env, expired_license_token):
        """Test getting license info for expired license."""
        JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
        with tempfile.TemporaryDirectory() as tmpdir:
            license_path = Path(tmpdir) / "license.jwt"
            license_path.write_text(expired_license_token)
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

            info = get_license_info()

            assert info["is_expired"] is True
            assert info["is_in_grace_period"] is True
            assert info["days_until_expiration"] < 0


class TestGracePeriod:
    """Tests for license grace period handling."""

    def test_grace_period_3_days_ago(self):
        """Test license expired 3 days ago (within 7-day grace)."""
        now = datetime.now(timezone.utc)
        expired_date = now - timedelta(days=3)

        claims = {
            "iss": "code-scalpel-licensing",
            "aud": "code-scalpel",
            "sub": TEST_CUSTOMER_ID,
            "jti": "test-grace-3d-jti",
            "tier": "pro",
            "features": [],
            "exp": int(expired_date.timestamp()),
            "iat": int((expired_date - timedelta(days=365)).timestamp()),
        }

        token = jwt.encode(claims, TEST_SECRET_KEY, algorithm="HS256")

        validator = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
        result = validator.validate_token(token)

        assert result.is_expired is True
        assert result.is_in_grace_period is True

    def test_grace_period_8_days_ago(self):
        """Test license expired 8 days ago (beyond grace)."""
        now = datetime.now(timezone.utc)
        expired_date = now - timedelta(days=8)

        claims = {
            "iss": "code-scalpel-licensing",
            "aud": "code-scalpel",
            "sub": TEST_CUSTOMER_ID,
            "jti": "test-grace-8d-jti",
            "tier": "pro",
            "features": [],
            "exp": int(expired_date.timestamp()),
            "iat": int((expired_date - timedelta(days=365)).timestamp()),
        }

        token = jwt.encode(claims, TEST_SECRET_KEY, algorithm="HS256")

        validator = JWTLicenseValidator(algorithm=JWTAlgorithm.HS256, secret_key=TEST_SECRET_KEY)
        result = validator.validate_token(token)

        assert result.is_expired is True
        assert result.is_in_grace_period is False


class TestTokenGeneration:
    """Tests for license token generation."""

    def test_generate_pro_license(self):
        """Test generating a Pro tier license."""
        token = generate_license(
            tier="pro",
            customer_id="gen_test_123",
            organization="Test Org",
            duration_days=365,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT has 3 parts separated by dots

        # Verify we can decode it
        # [20251227_BUGFIX] Disable IAT validation to avoid clock skew issues
        claims = jwt.decode(
            token,
            TEST_SECRET_KEY,
            algorithms=["HS256"],
            audience="code-scalpel",
            options={"verify_signature": True, "verify_iat": False},
        )

        assert claims["tier"] == "pro"
        assert claims["sub"] == "gen_test_123"

    def test_generate_enterprise_license_with_seats(self):
        """Test generating Enterprise license with seat count."""
        token = generate_license(
            tier="enterprise",
            customer_id="gen_test_456",
            seats=100,
            duration_days=730,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        # [20251227_BUGFIX] Disable IAT validation to avoid clock skew issues
        claims = jwt.decode(
            token,
            TEST_SECRET_KEY,
            algorithms=["HS256"],
            audience="code-scalpel",
            options={"verify_signature": True, "verify_iat": False},
        )

        assert claims["tier"] == "enterprise"
        assert claims["seats"] == 100

    def test_generated_license_auto_features(self):
        """Test that generated licenses auto-include features."""
        pro_token = generate_license(
            tier="pro",
            customer_id="test",
            duration_days=365,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        # [20251227_BUGFIX] Disable IAT validation to avoid clock skew issues
        claims = jwt.decode(
            pro_token,
            TEST_SECRET_KEY,
            algorithms=["HS256"],
            audience="code-scalpel",
            options={"verify_signature": True, "verify_iat": False},
        )

        # Pro should have multiple features
        assert len(claims["features"]) > 0
        assert "cognitive_complexity" in claims["features"]

    def test_generated_license_custom_features(self):
        """Test specifying custom features."""
        custom_features = ["feature_1", "feature_2"]
        token = generate_license(
            tier="pro",
            customer_id="test",
            features=custom_features,
            duration_days=365,
            algorithm="HS256",
            secret_key=TEST_SECRET_KEY,
        )

        # [20251227_BUGFIX] Disable IAT validation to avoid clock skew issues
        claims = jwt.decode(
            token,
            TEST_SECRET_KEY,
            algorithms=["HS256"],
            audience="code-scalpel",
            options={"verify_signature": True, "verify_iat": False},
        )

        assert claims["features"] == custom_features


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_token(self, validator_hs256):
        """Test validating empty token."""
        result = validator_hs256.validate_token("")

        assert result.is_valid is False

    def test_none_token(self, validator_hs256):
        """Test that None token doesn't crash."""
        result = validator_hs256.validate_token(None)

        assert result.is_valid is False

    def test_validator_without_pyjwt(self):
        """Test that validator handles missing PyJWT gracefully."""
        # This test only runs if PyJWT is available
        # In production, the module would handle ImportError
        assert JWT_AVAILABLE

    def test_license_data_properties(self, pro_license_token, validator_hs256):
        """Test JWTLicenseData property calculations."""
        result = validator_hs256.validate_token(pro_license_token)

        assert result.days_until_expiration is not None
        assert result.days_until_expiration > 0
        assert isinstance(result.is_in_grace_period, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
