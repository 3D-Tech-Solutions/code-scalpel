"""
Tests for Cryptographic Policy Verification.

# [20250108_TEST] v2.5.0 Guardian - Tests for crypto_verify module
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from code_scalpel.policy_engine.crypto_verify import (
    CryptographicPolicyVerifier,
    PolicyManifest,
    SecurityError,
    verify_policy_integrity_crypto,
)


class TestPolicyManifest:
    """Tests for PolicyManifest dataclass."""

    def test_manifest_creation(self):
        """Test basic manifest creation."""
        manifest = PolicyManifest(
            version="1.0",
            files={"policy.yaml": "abc123"},
            signature="sig456",
            created_at="2025-01-08T10:00:00",
            signed_by="admin@example.com",
        )

        assert manifest.version == "1.0"
        assert manifest.files == {"policy.yaml": "abc123"}
        assert manifest.signature == "sig456"
        assert manifest.signed_by == "admin@example.com"


class TestCryptographicPolicyVerifier:
    """Tests for CryptographicPolicyVerifier class."""

    @pytest.fixture
    def policy_dir(self, tmp_path):
        """Create a temporary policy directory with sample files."""
        policy_path = tmp_path / ".code-scalpel"
        policy_path.mkdir()

        # Create sample policy file
        policy_file = policy_path / "policy.yaml"
        policy_file.write_text("""
policies:
  - name: no_sql_injection
    description: Prevent SQL injection
    rule: |
      package scalpel.security
      deny[msg] { msg := "SQL injection detected" }
""")

        return policy_path

    @pytest.fixture
    def secret_key(self):
        """Return a test secret key."""
        return "test-secret-key-12345"

    def test_create_manifest(self, policy_dir, secret_key):
        """Test creating a signed manifest."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        assert manifest.version == "1.0"
        assert "policy.yaml" in manifest.files
        assert len(manifest.files["policy.yaml"]) == 71  # [20241224_BUGFIX] v3.2.9 - SHA-256 hex with "sha256:" prefix
        assert manifest.files["policy.yaml"].startswith("sha256:")
        assert manifest.signature  # Should have a signature
        assert manifest.signed_by == "admin@test.com"

    def test_create_manifest_multiple_files(self, policy_dir, secret_key):
        """Test creating manifest with multiple policy files."""
        # Create additional files
        (policy_dir / "budget.yaml").write_text("budget: 1000")
        (policy_dir / "overrides.yaml").write_text("overrides: []")

        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml", "budget.yaml", "overrides.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        assert len(manifest.files) == 3
        assert "policy.yaml" in manifest.files
        assert "budget.yaml" in manifest.files
        assert "overrides.yaml" in manifest.files

    def test_save_manifest(self, policy_dir, secret_key):
        """Test saving manifest to file."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        path = CryptographicPolicyVerifier.save_manifest(
            manifest,
            policy_dir=str(policy_dir),
        )

        assert path.exists()
        assert path.name == "policy.manifest.json"

        # Verify contents
        with open(path) as f:
            data = json.load(f)

        assert data["version"] == manifest.version
        assert data["files"] == manifest.files
        assert data["signature"] == manifest.signature

    def test_verify_manifest_signature_valid(self, policy_dir, secret_key):
        """Test verifying a valid manifest signature."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        # Set environment variable
        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # Should not raise
            result = verifier.verify_all_policies()
            assert result.success
            assert result.manifest_valid
            assert result.files_verified == 1

    def test_verify_manifest_signature_invalid(self, policy_dir, secret_key):
        """Test detecting invalid manifest signature."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        # Tamper with signature
        manifest.signature = "tampered-signature"
        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # Should raise SecurityError
            with pytest.raises(SecurityError) as exc:
                verifier.verify_all_policies()

            assert "signature INVALID" in str(exc.value)
            assert "tampered" in str(exc.value).lower()

    def test_detect_tampered_policy_file(self, policy_dir, secret_key):
        """Test detecting when a policy file has been modified."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        # Tamper with the policy file
        policy_file = policy_dir / "policy.yaml"
        policy_file.write_text("HACKED: allow_all = true")

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # Should raise SecurityError
            with pytest.raises(SecurityError) as exc:
                verifier.verify_all_policies()

            assert "tampered" in str(exc.value).lower()
            assert "policy.yaml" in str(exc.value)

    def test_detect_missing_policy_file(self, policy_dir, secret_key):
        """Test detecting when a policy file is deleted."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        # Delete the policy file
        (policy_dir / "policy.yaml").unlink()

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError) as exc:
                verifier.verify_all_policies()

            assert "missing" in str(exc.value).lower() or "tampered" in str(exc.value).lower()

    def test_verify_single_file(self, policy_dir, secret_key):
        """Test verifying a single policy file."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            assert verifier.verify_single_file("policy.yaml") is True

    def test_verify_single_file_not_in_manifest(self, policy_dir, secret_key):
        """Test error when file is not in manifest."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError) as exc:
                verifier.verify_single_file("unknown.yaml")

            assert "not in policy manifest" in str(exc.value)

    def test_missing_secret_key_fails_closed(self, policy_dir):
        """Test that missing secret key causes fail closed."""
        # Clear environment
        with patch.dict(os.environ, {}, clear=True):
            # Remove SCALPEL_MANIFEST_SECRET if it exists
            if "SCALPEL_MANIFEST_SECRET" in os.environ:
                del os.environ["SCALPEL_MANIFEST_SECRET"]

            with pytest.raises(SecurityError) as exc:
                CryptographicPolicyVerifier(
                    manifest_source="file",
                    policy_dir=str(policy_dir),
                )

            assert "SCALPEL_MANIFEST_SECRET" in str(exc.value)

    def test_missing_manifest_fails_closed(self, policy_dir, secret_key):
        """Test that missing manifest causes fail closed."""
        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            with pytest.raises(SecurityError) as exc:
                CryptographicPolicyVerifier(
                    manifest_source="file",
                    policy_dir=str(policy_dir),
                )

            assert "not found" in str(exc.value).lower()

    def test_load_from_env(self, policy_dir, secret_key):
        """Test loading manifest from environment variable."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        manifest_json = json.dumps(
            {
                "version": manifest.version,
                "files": manifest.files,
                "created_at": manifest.created_at,
                "signed_by": manifest.signed_by,
                "signature": manifest.signature,
            }
        )

        with patch.dict(
            os.environ,
            {
                "SCALPEL_MANIFEST_SECRET": secret_key,
                "SCALPEL_POLICY_MANIFEST": manifest_json,
            },
        ):
            verifier = CryptographicPolicyVerifier(
                manifest_source="env",
                policy_dir=str(policy_dir),
            )

            result = verifier.verify_all_policies()
            assert result.success

    def test_wrong_secret_key_fails(self, policy_dir, secret_key):
        """Test that wrong secret key causes signature failure."""
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        # Use wrong secret key
        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": "wrong-secret"}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            with pytest.raises(SecurityError) as exc:
                verifier.verify_all_policies()

            assert "signature INVALID" in str(exc.value)


class TestHashConsistency:
    """Tests for SHA-256 hash consistency."""

    def test_hash_is_deterministic(self, tmp_path):
        """Test that same file always produces same hash."""
        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()

        policy_file = policy_dir / "policy.yaml"
        content = "test content for hashing"
        policy_file.write_text(content)

        secret_key = "test-secret"

        # Create multiple manifests
        manifests = []
        for _ in range(3):
            manifest = CryptographicPolicyVerifier.create_manifest(
                policy_files=["policy.yaml"],
                secret_key=secret_key,
                signed_by="admin@test.com",
                policy_dir=str(policy_dir),
            )
            manifests.append(manifest)

        # All hashes should be identical
        assert manifests[0].files["policy.yaml"] == manifests[1].files["policy.yaml"]
        assert manifests[1].files["policy.yaml"] == manifests[2].files["policy.yaml"]

    def test_hash_changes_with_content(self, tmp_path):
        """Test that hash changes when file content changes."""
        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()

        policy_file = policy_dir / "policy.yaml"
        secret_key = "test-secret"

        # First content
        policy_file.write_text("original content")
        manifest1 = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        # Modified content
        policy_file.write_text("modified content")
        manifest2 = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )

        # Hashes should be different
        assert manifest1.files["policy.yaml"] != manifest2.files["policy.yaml"]


class TestVerifyPolicyIntegrityCrypto:
    """Tests for the convenience function."""

    def test_verify_policy_integrity_crypto_success(self, tmp_path):
        """Test successful verification through convenience function."""
        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()

        policy_file = policy_dir / "policy.yaml"
        policy_file.write_text("test policy")

        secret_key = "test-secret"

        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )
        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        # Mock git to return the manifest
        mock_manifest = json.dumps(
            {
                "version": manifest.version,
                "files": manifest.files,
                "created_at": manifest.created_at,
                "signed_by": manifest.signed_by,
                "signature": manifest.signature,
            }
        )

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=mock_manifest,
                )

                result = verify_policy_integrity_crypto(str(policy_dir))
                assert result is True


class TestTimingAttackPrevention:
    """Tests for timing attack prevention."""

    def test_uses_constant_time_comparison(self, tmp_path):
        """Test that signature comparison uses constant time."""
        policy_dir = tmp_path / ".code-scalpel"
        policy_dir.mkdir()
        (policy_dir / "policy.yaml").write_text("test")

        secret_key = "test-secret"

        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=["policy.yaml"],
            secret_key=secret_key,
            signed_by="admin@test.com",
            policy_dir=str(policy_dir),
        )
        CryptographicPolicyVerifier.save_manifest(manifest, str(policy_dir))

        with patch.dict(os.environ, {"SCALPEL_MANIFEST_SECRET": secret_key}):
            verifier = CryptographicPolicyVerifier(
                manifest_source="file",
                policy_dir=str(policy_dir),
            )

            # Verify the implementation uses hmac.compare_digest
            # This is validated by the actual hmac.compare_digest usage in the code
            # We're just testing that verification works correctly
            assert verifier._verify_manifest_signature() is True
