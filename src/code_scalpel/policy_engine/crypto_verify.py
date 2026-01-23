"""
Cryptographic Policy Verification.

# [20250108_FEATURE] v2.5.0 Guardian - Cryptographic policy verification

This module provides cryptographic verification of policy files to prevent
agents from bypassing file permission controls.

Addresses 3rd party review feedback:
"File permissions are bypassable. Agent can `chmod +w`."

Solution: Hash verification against cryptographically signed manifest stored in:
1. Git commit history (can't be modified without visible commit)
2. Environment variable (set by CI/CD, not accessible to agent)
3. External secret store (HashiCorp Vault, AWS Secrets Manager)

Security Model: FAIL CLOSED
- Missing manifest -> DENY ALL
- Invalid signature -> DENY ALL
- Hash mismatch -> DENY ALL
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any  # [20241225_BUGFIX] v3.3.0 - Added Any


class SecurityError(Exception):
    """Raised when cryptographic verification fails."""

    pass


@dataclass
class PolicyManifest:
    """
    Signed manifest for policy files.

    # [20250108_FEATURE] Contains hashes and signature for verification

    Attributes:
        version: Manifest format version
        files: Mapping of filename to SHA-256 hash (or dict with hash/size)
        signature: HMAC signature of the manifest data
        created_at: ISO timestamp when manifest was created
        signed_by: Identity of the signer (admin email/name), optional for legacy
    """

    version: str
    files: dict[str, str | dict[str, Any]]  # filename -> SHA-256 hash or {hash, size}
    signature: str  # HMAC signature of the manifest
    created_at: str
    signed_by: str = "unknown"  # [20241225_BUGFIX] v3.3.0 - Make optional with default


@dataclass
class VerificationResult:
    """
    Result of cryptographic policy verification.

    # [20250108_FEATURE] Detailed verification outcome

    Attributes:
        success: Whether all verifications passed
        manifest_valid: Whether manifest signature is valid
        files_verified: Number of files successfully verified
        files_failed: List of files that failed verification
        error: Error message if verification failed
    """

    success: bool
    manifest_valid: bool = False
    files_verified: int = 0
    files_failed: list[str] = field(default_factory=list)
    error: str | None = None


class CryptographicPolicyVerifier:
    """
    Verify policy files against cryptographically signed manifests.

    # [20250108_FEATURE] v2.5.0 Guardian - Cryptographic verification

    This class addresses the 3rd party review feedback that file permissions
    can be bypassed by running `chmod +w` on policy files. By verifying
    SHA-256 hashes against a signed manifest, any modification is detected
    regardless of file permissions.

    Security Model: FAIL CLOSED
    - If manifest cannot be loaded: DENY ALL
    - If signature verification fails: DENY ALL
    - If any file hash mismatches: DENY ALL

    The signing secret should be stored in:
    - Environment variable (SCALPEL_MANIFEST_SECRET)
    - CI/CD secrets (not accessible to agent)
    - HashiCorp Vault or similar

    Example:
        verifier = CryptographicPolicyVerifier(manifest_source="git")
        try:
            verifier.verify_all_policies()
            print("Policy integrity verified")
        except SecurityError as e:
            print(f"SECURITY: {e}")
            # Fail closed - deny all operations
    """

    def __init__(
        self,
        manifest_source: str = "git",  # "git", "env", "file"
        secret_key: str | None = None,
        policy_dir: str = ".code-scalpel",
    ):
        """
        Initialize cryptographic policy verifier.

        # [20250108_FEATURE] Configure verification source

        Args:
            manifest_source: Where to load manifest from ("git", "env", "file")
            secret_key: HMAC signing secret (uses env var if not provided)
            policy_dir: Directory containing policy files

        Raises:
            SecurityError: If secret key not available or manifest cannot be loaded
        """
        self.manifest_source = manifest_source
        self.policy_dir = Path(policy_dir)
        self.secret_key = secret_key or self._get_secret_from_env()
        self.manifest: PolicyManifest | None = None

        # Load manifest (fail closed if unavailable)
        try:
            self.manifest = self._load_manifest()
        except Exception as e:
            raise SecurityError(
                f"Failed to load policy manifest: {e}. " "All operations DENIED until manifest is available."
            )

    def _get_secret_from_env(self) -> str:
        """
        Get signing secret from environment.

        # [20250108_SECURITY] Secret must be set externally

        Returns:
            Secret key string

        Raises:
            SecurityError: If secret not found in environment
        """
        secret = os.environ.get("SCALPEL_MANIFEST_SECRET")
        if not secret:
            raise SecurityError(
                "SCALPEL_MANIFEST_SECRET environment variable not set. "
                "Policy verification requires a signing secret set by administrator."
            )
        return secret

    def _load_manifest(self) -> PolicyManifest:
        """
        Load policy manifest from configured source.

        # [20250108_FEATURE] Multi-source manifest loading

        Returns:
            PolicyManifest object

        Raises:
            SecurityError: If manifest cannot be loaded
        """
        if self.manifest_source == "git":
            return self._load_from_git()
        elif self.manifest_source == "env":
            return self._load_from_env()
        elif self.manifest_source == "file":
            return self._load_from_file()
        else:
            raise SecurityError(f"Unknown manifest source: {self.manifest_source}")

    def _load_from_git(self) -> PolicyManifest:
        """
        Load manifest from git history.

        # [20250108_FEATURE] Load from committed manifest

        The manifest is stored in a committed file that the agent
        cannot modify without creating a visible git commit.

        Returns:
            PolicyManifest loaded from git

        Raises:
            SecurityError: If manifest not found in git
        """
        try:
            # Get manifest from the committed version (not working tree)
            result = subprocess.run(
                ["git", "show", f"HEAD:{self.policy_dir}/policy.manifest.json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise SecurityError(
                    "Policy manifest not found in git history. "
                    "Run `scalpel policy sign` to create one and commit it."
                )

            data = json.loads(result.stdout)
            return PolicyManifest(**data)

        except subprocess.TimeoutExpired:
            raise SecurityError("Git command timeout while loading manifest. Failing CLOSED.")
        except json.JSONDecodeError as e:
            raise SecurityError(f"Policy manifest is not valid JSON: {e}. Failing CLOSED.")

    def _load_from_env(self) -> PolicyManifest:
        """
        Load manifest from environment variable.

        # [20250108_FEATURE] Load from CI/CD injected env var

        Useful for CI/CD pipelines that inject the manifest as a secret.

        Returns:
            PolicyManifest loaded from environment

        Raises:
            SecurityError: If manifest env var not set
        """
        manifest_json = os.environ.get("SCALPEL_POLICY_MANIFEST")
        if not manifest_json:
            raise SecurityError("SCALPEL_POLICY_MANIFEST environment variable not set. " "Failing CLOSED.")

        try:
            data = json.loads(manifest_json)
            return PolicyManifest(**data)
        except json.JSONDecodeError as e:
            raise SecurityError(f"SCALPEL_POLICY_MANIFEST is not valid JSON: {e}. Failing CLOSED.")

    def _load_from_file(self) -> PolicyManifest:
        """
        Load manifest from local file.

        # [20250108_FEATURE] Load from local manifest file

        Note: This is less secure than git or env sources since the file
        could potentially be modified. Use only for development/testing.

        Returns:
            PolicyManifest loaded from file

        Raises:
            SecurityError: If manifest file not found or invalid
        """
        manifest_path = self.policy_dir / "policy.manifest.json"

        if not manifest_path.exists():
            raise SecurityError(
                f"Policy manifest not found: {manifest_path}. " "Run `scalpel policy sign` to create one."
            )

        try:
            with open(manifest_path) as f:
                data = json.load(f)
            return PolicyManifest(**data)
        except json.JSONDecodeError as e:
            raise SecurityError(f"Policy manifest is not valid JSON: {e}. Failing CLOSED.")

    def verify_all_policies(self) -> VerificationResult:
        """
        Verify all policy files match their manifest hashes.

        # [20250108_FEATURE] Full policy verification

        Performs:
        1. Verify manifest HMAC signature
        2. Verify each policy file hash matches manifest

        Returns:
            VerificationResult with detailed status

        Raises:
            SecurityError: If any verification fails (FAIL CLOSED)
        """
        result = VerificationResult(success=False)

        if not self.manifest:
            result.error = "Policy manifest not loaded. All operations DENIED."
            raise SecurityError(result.error)

        # First verify manifest signature
        if not self._verify_manifest_signature():
            result.error = (
                "Policy manifest signature INVALID. " "Manifest may have been tampered with. " "All operations DENIED."
            )
            raise SecurityError(result.error)

        result.manifest_valid = True

        # Verify each file
        files_failed = []
        files_verified = 0

        for filename, expected_hash_or_dict in self.manifest.files.items():
            try:
                # [20241225_BUGFIX] v3.3.0 - Handle both flat hash strings and nested dicts
                if isinstance(expected_hash_or_dict, dict):
                    expected_hash = expected_hash_or_dict.get("hash")
                    if not expected_hash:
                        files_failed.append(filename)
                        continue
                else:
                    expected_hash = expected_hash_or_dict

                actual_hash = self._hash_file(filename)

                if actual_hash != expected_hash:
                    files_failed.append(filename)
                else:
                    files_verified += 1

            except FileNotFoundError:
                files_failed.append(filename)

        result.files_verified = files_verified
        result.files_failed = files_failed

        if files_failed:
            result.error = (
                f"Policy files tampered or missing: {', '.join(files_failed)}. "
                "All operations DENIED until policy integrity restored."
            )
            raise SecurityError(result.error)

        result.success = True
        return result

    def verify_single_file(self, filename: str) -> bool:
        """
        Verify a single policy file.

        # [20250108_FEATURE] Single file verification

        Args:
            filename: Name of policy file to verify

        Returns:
            True if file matches manifest hash

        Raises:
            SecurityError: If file doesn't match or is missing
        """
        if not self.manifest:
            raise SecurityError("Policy manifest not loaded. Cannot verify file.")

        if filename not in self.manifest.files:
            raise SecurityError(f"File '{filename}' not in policy manifest. Cannot verify.")

        # [20241224_BUGFIX] v3.2.9 - Handle both flat hash strings and nested dicts
        expected_hash_or_dict = self.manifest.files[filename]
        if isinstance(expected_hash_or_dict, dict):
            expected_hash = expected_hash_or_dict.get("hash")
            if not expected_hash:
                raise SecurityError(f"Policy manifest for '{filename}' missing hash field. Cannot verify.")
        else:
            expected_hash = expected_hash_or_dict

        actual_hash = self._hash_file(filename)

        if actual_hash != expected_hash:
            raise SecurityError(
                f"Policy file tampered: {filename}\n"
                f"Expected: {expected_hash}\n"
                f"Actual:   {actual_hash}\n"
                "All operations DENIED."
            )

        return True

    def _verify_manifest_signature(self) -> bool:
        """
        Verify HMAC signature of the manifest.

        # [20250108_SECURITY] Signature verification

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.manifest:
            return False

        # [20241225_BUGFIX] v3.3.0 - Reconstruct the signed data exactly as it was signed
        # Only include signed_by if it's not the default value (for backward compatibility)
        signed_data = {
            "version": self.manifest.version,
            "files": self.manifest.files,
            "created_at": self.manifest.created_at,
        }
        if self.manifest.signed_by != "unknown":
            signed_data["signed_by"] = self.manifest.signed_by

        # [20241225_BUGFIX] v3.3.0 - Use same JSON format as signing
        message = json.dumps(signed_data, sort_keys=True, separators=(",", ":"))
        expected_signature = hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()

        # [20241225_BUGFIX] v3.3.0 - Strip hmac-sha256: prefix if present
        manifest_signature = self.manifest.signature
        if not manifest_signature:  # [20241225_BUGFIX] v3.3.0 - Handle null signature
            return False
        if manifest_signature.startswith("hmac-sha256:"):
            manifest_signature = manifest_signature[len("hmac-sha256:") :]

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, manifest_signature)

    def _hash_file(self, filename: str) -> str:
        """
        Calculate SHA-256 hash of a file.

        # [20250108_FEATURE] File hashing

        Args:
            filename: Name of file in policy directory

        Returns:
            SHA-256 hash as hex string

        Raises:
            FileNotFoundError: If file does not exist
        """
        path = self.policy_dir / filename

        if not path.exists():
            raise FileNotFoundError(f"Policy file missing: {filename}")

        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

        # [20241225_BUGFIX] v3.3.0 - Return hash with sha256: prefix for compatibility
        return "sha256:" + hasher.hexdigest()

    @staticmethod
    def create_manifest(
        policy_files: list[str],
        secret_key: str,
        signed_by: str,
        policy_dir: str = ".code-scalpel",
    ) -> PolicyManifest:
        """
        Create a new signed manifest for policy files.

        # [20250108_FEATURE] Manifest creation for administrators

        This should be run by a human administrator, NOT an agent.
        The manifest should be committed to git after creation.

        Args:
            policy_files: List of policy filenames to include
            secret_key: HMAC signing secret
            signed_by: Identity of the signer (email/name)
            policy_dir: Directory containing policy files

        Returns:
            Signed PolicyManifest
        """
        policy_path = Path(policy_dir)
        files = {}

        for filename in policy_files:
            path = policy_path / filename
            if path.exists():
                hasher = hashlib.sha256()
                with open(path, "rb") as f:
                    hasher.update(f.read())
                files[filename] = "sha256:" + hasher.hexdigest()  # [20241225_BUGFIX] v3.3.0 - Use prefixed format

        manifest_data = {
            "version": "1.0",
            "files": files,
            "created_at": datetime.now().isoformat(),
            "signed_by": signed_by,
        }

        # Create HMAC signature
        message = json.dumps(
            manifest_data, sort_keys=True, separators=(",", ":")
        )  # [20241225_BUGFIX] v3.3.0 - Use canonical format
        signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()

        return PolicyManifest(
            version=manifest_data["version"],
            files=manifest_data["files"],
            created_at=manifest_data["created_at"],
            signed_by=manifest_data["signed_by"],
            signature=signature,
        )

    @staticmethod
    def save_manifest(manifest: PolicyManifest, policy_dir: str = ".code-scalpel") -> Path:
        """
        Save manifest to file.

        # [20250108_FEATURE] Write manifest for git commit

        Args:
            manifest: PolicyManifest to save
            policy_dir: Directory to save manifest in

        Returns:
            Path to saved manifest file
        """
        manifest_path = Path(policy_dir) / "policy.manifest.json"

        manifest_data = {
            "version": manifest.version,
            "files": manifest.files,
            "created_at": manifest.created_at,
            "signed_by": manifest.signed_by,
            "signature": manifest.signature,
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        return manifest_path


# [20250108_FEATURE] Integration with TamperResistance
def verify_policy_integrity_crypto(policy_dir: str = ".code-scalpel") -> bool:
    """
    Verify policy integrity using cryptographic verification.

    This is a convenience function that integrates with the existing
    TamperResistance system.

    Args:
        policy_dir: Directory containing policy files

    Returns:
        True if verification passes

    Raises:
        SecurityError: If verification fails (FAIL CLOSED)
    """
    try:
        verifier = CryptographicPolicyVerifier(
            manifest_source="git",
            policy_dir=policy_dir,
        )
        result = verifier.verify_all_policies()
        return result.success
    except SecurityError:
        # Re-raise security errors
        raise
    except Exception as e:
        # Any unexpected error - FAIL CLOSED
        raise SecurityError(f"Unexpected error during policy verification: {e}. Failing CLOSED.")
