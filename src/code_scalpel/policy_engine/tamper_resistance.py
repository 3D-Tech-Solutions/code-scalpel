"""
Tamper-Resistant Policy Enforcement.

# [20251216_FEATURE] v2.5.0 Guardian - Tamper resistance

This module provides tamper-resistant policy enforcement to prevent agents
from circumventing policy controls.
"""

import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path

from .audit_log import AuditLog
from .exceptions import PolicyModificationError, TamperDetectedError
from .models import HumanResponse
from .policy_engine import Operation, OverrideDecision, PolicyDecision


class TamperResistance:
    """
    Tamper-resistant policy enforcement.

    # [20251216_FEATURE] v2.5.0 Guardian P0

    Features:
    - Policy file integrity verification (SHA-256)
    - Read-only file permissions for policy files
    - Policy modification prevention
    - TOTP-based human override system
    - Comprehensive audit logging
    """

    def __init__(self, policy_path: str = ".code-scalpel/policy.yaml"):
        """
        Initialize tamper resistance system.

        Args:
            policy_path: Path to main policy file
        """
        self.policy_path = Path(policy_path)
        self.policy_hash = self._hash_policy_file()
        # [20251222_BUGFIX] Use a persistent audit log colocated with policy files.
        self.audit_log = AuditLog(str(self.policy_path.parent / "audit.log"))
        self._lock_policy_files()

        # Override tracking
        self._used_override_ids = set()

    def _lock_policy_files(self) -> None:
        """
        Make policy files read-only to agent.

        # [20251216_FEATURE] v2.5.0 Guardian P0 - File locking
        """

        # Use policy_path parent as base directory for relative paths
        policy_dir = self.policy_path.parent

        policy_files = [
            self.policy_path,
            policy_dir / "budget.yaml",
            policy_dir / "overrides.yaml",
        ]

        for policy_file in policy_files:
            if policy_file.exists():
                # Set read-only permissions (0o444 = r--r--r--)
                policy_file.chmod(0o444)

    def verify_policy_integrity(self) -> bool:
        """
        Verify policy file has not been tampered with.

        # [20251216_FEATURE] v2.5.0 Guardian P0 - Integrity check

        Returns:
            True if policy is intact, raises error if tampered


        Raises:
            TamperDetectedError: If policy integrity check fails
        """
        current_hash = self._hash_policy_file()

        if current_hash != self.policy_hash:
            self.audit_log.record_event(
                event_type="POLICY_TAMPERING_DETECTED",
                severity="CRITICAL",
                details={
                    "expected_hash": self.policy_hash,
                    "actual_hash": current_hash,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Fail CLOSED - deny all operations
            raise TamperDetectedError("Policy file integrity check failed. All operations denied.")

        return True

    def _hash_policy_file(self) -> str:
        """
        Calculate SHA-256 hash of policy file.

        # [20251216_FEATURE] v2.5.0 Guardian P0 - Hash calculation

        Returns:
            SHA-256 hash as hex string
        """
        if not self.policy_path.exists():
            return ""

        hasher = hashlib.sha256()
        with open(self.policy_path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def prevent_policy_modification(self, operation: Operation) -> bool:
        """
        Prevent agent from modifying policy files.

        # [20251216_FEATURE] v2.5.0 Guardian P0 - Modification prevention

        Args:
            operation: Operation to check

        Returns:
            True if operation is allowed, raises error if blocked

        Raises:
            PolicyModificationError: If operation targets protected files
        """
        protected_paths = [
            ".code-scalpel/",
            "scalpel.policy.yaml",
            "budget.yaml",
            "overrides.yaml",
        ]

        # Support both single file_path and affected_files list
        files_to_check = []
        if hasattr(operation, "affected_files") and operation.affected_files:
            files_to_check = operation.affected_files
        elif hasattr(operation, "file_path") and operation.file_path:
            files_to_check = [operation.file_path]

        for file_path in files_to_check:
            file_str = str(file_path)
            if any(file_str.startswith(p) or p in file_str for p in protected_paths):
                self.audit_log.record_event(
                    event_type="POLICY_MODIFICATION_ATTEMPTED",
                    severity="CRITICAL",
                    details={
                        "file": str(file_path),
                        "operation": operation.type,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                raise PolicyModificationError(f"Agent attempted to modify protected policy file: {file_path}")

        return True

    def require_human_override(
        self,
        operation: Operation,
        policy_decision: PolicyDecision,
        timeout_seconds: int = 300,
    ) -> OverrideDecision:
        """
        Require human approval for policy overrides.

        # [20251216_FEATURE] v2.5.0 Guardian P0 - Human override system

        Uses time-based one-time password (TOTP) for verification.

        Args:
            operation: Operation requiring override
            policy_decision: Policy decision being overridden
            timeout_seconds: Timeout for human response (default: 300s/5min)

        Returns:
            OverrideDecision with approval status
        """
        # Generate challenge
        challenge = self._generate_challenge()

        # Wait for human response (with timeout)
        response = self._wait_for_human_response(challenge=challenge, timeout_seconds=timeout_seconds)

        if not response:
            self.audit_log.record_event(
                event_type="OVERRIDE_TIMEOUT",
                severity="HIGH",
                details={
                    "operation": operation.type,
                    "policy_violated": policy_decision.violated_policies,
                },
            )
            return OverrideDecision(approved=False, reason="Override request timed out")

        # Verify human code
        if not self._verify_totp(response.code, challenge):
            self.audit_log.record_event(
                event_type="INVALID_OVERRIDE_CODE",
                severity="HIGH",
                details={
                    "operation": operation.type,
                    "attempted_code": "***",  # Never log actual code
                },
            )
            return OverrideDecision(approved=False, reason="Invalid override code")

        # Generate override ID
        override_id = self._generate_override_id()

        # Check for override reuse
        if override_id in self._used_override_ids:
            self.audit_log.record_event(
                event_type="OVERRIDE_REUSE_ATTEMPTED",
                severity="HIGH",
                details={"operation": operation.type, "override_id": override_id},
            )
            return OverrideDecision(approved=False, reason="Override code cannot be reused")

        # Mark override as used
        self._used_override_ids.add(override_id)

        # Record approval
        self.audit_log.record_event(
            event_type="OVERRIDE_APPROVED",
            severity="MEDIUM",
            details={
                "operation": operation.type,
                "policy_violated": policy_decision.violated_policies,
                "justification": response.justification,
                "approved_by": response.human_id,
                "override_id": override_id,
            },
        )

        return OverrideDecision(
            approved=True,
            reason="Human override approved",
            override_id=override_id,
            expires_at=datetime.now() + timedelta(minutes=30),
            justification=response.justification,
            approved_by=response.human_id,
        )

    def _generate_challenge(self) -> str:
        """
        Generate challenge for TOTP verification.

        Returns:
            Challenge string
        """
        return secrets.token_hex(16)

    def _wait_for_human_response(self, challenge: str, timeout_seconds: int) -> HumanResponse | None:
        """
        Wait for human response to override challenge.

        # [20251216_FEATURE] Mock implementation for testing

        In production, this would integrate with a UI or notification system.
        For now, it checks for a response file.

        Args:
            challenge: Challenge string
            timeout_seconds: Timeout in seconds

        Returns:
            HumanResponse if received within timeout, None otherwise
        """
        # Check in multiple locations for flexibility
        response_paths = [
            Path(".code-scalpel/override_response.json"),
            self.policy_path.parent / "override_response.json",
        ]

        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            for response_file in response_paths:
                if response_file.exists():
                    try:
                        import json

                        with open(response_file) as f:
                            data = json.load(f)

                        # Delete response file after reading
                        response_file.unlink()

                        return HumanResponse(
                            code=data["code"],
                            justification=data["justification"],
                            human_id=data["human_id"],
                        )
                    except Exception:
                        pass

            time.sleep(0.1)  # Poll more frequently for testing

        return None

    def _verify_totp(self, code: str, challenge: str) -> bool:
        """
        Verify TOTP code.

        # [20251216_FEATURE] Simplified verification for testing

        In production, this would use proper TOTP library (pyotp).
        For now, uses HMAC-based verification.

        Args:
            code: Code provided by human
            challenge: Challenge string

        Returns:
            True if code is valid
        """
        # Get secret from environment
        secret = os.environ.get("SCALPEL_TOTP_SECRET", "default-totp-secret")

        # Generate expected code
        expected_code = hmac.new(secret.encode(), challenge.encode(), hashlib.sha256).hexdigest()[:8]

        return code == expected_code

    def _generate_override_id(self) -> str:
        """
        Generate unique override ID.

        Returns:
            Unique override ID
        """
        return secrets.token_hex(16)

    def is_override_valid(self, override_id: str, expires_at: datetime) -> bool:
        """
        Check if override is still valid.

        # [20251216_FEATURE] v2.5.0 Guardian P0 - Override expiry

        Args:
            override_id: Override ID to check
            expires_at: Override expiration time

        Returns:
            True if override is valid and not expired
        """
        # Check if already used
        if override_id in self._used_override_ids:
            return False

        # Check if expired
        if datetime.now() > expires_at:
            return False

        return True
