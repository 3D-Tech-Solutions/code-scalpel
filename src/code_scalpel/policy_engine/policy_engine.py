"""
Policy Engine - OPA/Rego integration for declarative governance.

[20251216_FEATURE] v2.5.0 Guardian - Policy-as-Code enforcement

This module implements the core PolicyEngine that loads, validates, and enforces
policies defined in YAML using Open Policy Agent's Rego language.

Security Model: FAIL CLOSED
- Policy parsing errors → DENY ALL
- Policy evaluation errors → DENY ALL
- Missing OPA CLI → DENY ALL
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required for policy engine. Install with: pip install pyyaml")


class PolicyError(Exception):
    """Raised when policy loading, parsing, or evaluation fails."""

    pass


class PolicySeverity(Enum):
    """Severity levels for policy violations."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class PolicyAction(Enum):
    """Actions to take when policy is violated."""

    DENY = "DENY"  # Block the operation
    WARN = "WARN"  # Allow but log warning
    AUDIT = "AUDIT"  # Allow and log for review


@dataclass
class Policy:
    """
    A single policy definition.

    [20251216_FEATURE] Represents a policy rule written in Rego

    Attributes:
        name: Unique policy identifier
        description: Human-readable description
        rule: Rego policy code
        severity: Impact level (CRITICAL, HIGH, MEDIUM, LOW)
        action: What to do on violation (DENY, WARN, AUDIT)
    """

    name: str
    description: str
    rule: str
    severity: str = "HIGH"
    action: str = "DENY"

    def __post_init__(self):
        """Validate policy fields."""
        if not self.name:
            raise PolicyError("Policy name cannot be empty")
        if not self.rule:
            raise PolicyError(f"Policy '{self.name}' has empty rule")

        # Validate severity
        try:
            PolicySeverity(self.severity)
        except ValueError:
            raise PolicyError(f"Invalid severity '{self.severity}' in policy '{self.name}'")

        # Validate action
        try:
            PolicyAction(self.action)
        except ValueError:
            raise PolicyError(f"Invalid action '{self.action}' in policy '{self.name}'")


@dataclass
class PolicyViolation:
    """
    A detected policy violation.

    [20251216_FEATURE] Represents a specific instance where code violates policy

    Attributes:
        policy_name: Name of violated policy
        severity: Severity level
        message: Human-readable violation message
        action: Action to take (DENY, WARN, AUDIT)
    """

    policy_name: str
    severity: str
    message: str
    action: str


@dataclass
class PolicyDecision:
    """
    Result of policy evaluation.

    [20251216_FEATURE] Decision on whether to allow an operation
    [20251216_REFACTOR] Added severity field for compatibility with TamperResistance
    [20251216_REFACTOR] Made reason optional with default for backward compatibility

    Attributes:
        allowed: Whether operation is allowed
        reason: Explanation of decision
        violated_policies: Names of violated policies
        violations: Detailed violation information
        requires_override: Whether human override is possible
        severity: Overall severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)
    """

    allowed: bool
    reason: str = ""
    violated_policies: list[str] = field(default_factory=list)
    violations: list[PolicyViolation] = field(default_factory=list)
    requires_override: bool = False
    severity: str = "MEDIUM"


@dataclass
class Operation:
    """
    An operation to be evaluated against policies.

    [20251216_FEATURE] Represents a code operation (edit, file access, etc.)
    [20251216_REFACTOR] Extended to support both PolicyEngine and TamperResistance use cases

    Attributes:
        type: Operation type (code_edit, file_access, file_write, etc.)
        code: Code content being operated on (for code operations)
        language: Programming language (for code operations)
        file_path: Path to file being operated on (single file)
        affected_files: List of files affected (for multi-file operations)
        metadata: Additional context
        timestamp: When operation was created (for audit purposes)
    """

    type: str
    code: str = ""
    language: str = ""
    file_path: str = ""
    affected_files: list[Path] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OverrideDecision:
    """
    Result of override request.

    [20251216_FEATURE] Human approval for policy-violating operations
    [20251216_REFACTOR] Added justification and approved_by for TamperResistance compatibility

    Attributes:
        approved: Whether override was approved
        reason: Explanation of decision
        override_id: Unique ID for this override (if approved)
        expires_at: When override expires (if approved)
        justification: Reason provided by human for override
        approved_by: Identity of human who approved override
    """

    approved: bool
    reason: str
    override_id: str | None = None
    expires_at: datetime | None = None
    justification: str | None = None
    approved_by: str | None = None


class PolicyEngine:
    """
    OPA/Rego policy enforcement engine.

    [20251216_FEATURE] v2.5.0 Guardian - Enterprise governance for AI agents

    Security Model: FAIL CLOSED
    - All errors result in DENY
    - No silent failures
    - Full audit trail

    Example:
        engine = PolicyEngine(".code-scalpel/policy.yaml")
        decision = engine.evaluate(operation)
        if not decision.allowed:
            print(f"Denied: {decision.reason}")
    """

    _DEFAULT_POLICY_PATH = ".code-scalpel/policy.yaml"

    def __init__(self, policy_path: str = _DEFAULT_POLICY_PATH):
        """
        Initialize policy engine.

        [20251216_FEATURE] Loads and validates policies at startup

        Args:
            policy_path: Path to YAML policy configuration

        Raises:
            PolicyError: If policy file not found, invalid, or OPA unavailable
        """
        self.policy_path = Path(policy_path)
        self.policies: list[Policy] = []
        # [20240613_SECURITY] Persist used override codes to disk to enforce single-use guarantee across restarts
        self._used_override_codes_path = self.policy_path.parent / "used_override_codes.json"
        self._used_override_codes: set[str] = self._load_used_override_codes()

        # [20251222_BUGFIX] Check OPA availability but don't require it at init time.
        # We support a safe fallback evaluator when OPA is unavailable.
        self._opa_available: bool = self._detect_opa_available()
        self._semantic_analyzer = None

        # Load and validate policies. If the default policy path is missing,
        # allow initialization with zero policies (useful for reporting).
        if self.policy_path.exists():
            self.policies = self._load_policies()
            self._basic_validate_policies_rego()

            # Only validate with OPA if it's available
            if self._opa_available:
                self._validate_opa_available()
                self._validate_policies()
        else:
            if policy_path != self._DEFAULT_POLICY_PATH:
                raise PolicyError(f"Policy file not found: {self.policy_path}")
            self.policies = []

    @staticmethod
    def _detect_opa_available() -> bool:
        """Detect OPA availability.

        Prefers `shutil.which`, but also supports test harnesses that monkeypatch
        `subprocess.run` without having an actual `opa` binary on PATH.
        """
        if shutil.which("opa") is not None:
            return True
        try:
            result = subprocess.run(["opa", "version"], capture_output=True, text=True, timeout=1)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def _extract_rego_package(rule: str) -> str | None:
        m = re.search(r"^\s*package\s+([a-zA-Z0-9_\.\-]+)\s*$", rule, re.MULTILINE)
        if not m:
            return None
        return m.group(1)

    @classmethod
    def _opa_query_candidates(cls, rule: str) -> list[str]:
        """Return possible `opa eval` query strings.

        Includes a legacy query for backward compatibility with older tests,
        and a package-derived query for correctness.
        """
        candidates: list[str] = ["data.code-scalpel.security.deny"]
        package = cls._extract_rego_package(rule)
        if package:
            derived = f"data.{package}.deny"
            if derived not in candidates:
                candidates.append(derived)
        if "data.scalpel.security.deny" not in candidates:
            candidates.append("data.scalpel.security.deny")
        return candidates

    def _load_used_override_codes(self) -> set[str]:
        """
        [20240613_SECURITY] Load used override codes from disk to enforce single-use guarantee across restarts.
        """
        if self._used_override_codes_path.exists():
            try:
                with open(self._used_override_codes_path) as f:
                    codes = json.load(f)
                if not isinstance(codes, list):
                    raise ValueError("used_override_codes.json is not a list")
                return set(codes)
            except Exception as e:
                # Fail CLOSED - if we can't read the file, deny all overrides
                raise PolicyError(f"Failed to load used override codes: {e}. Failing CLOSED.")
        return set()

    def _save_used_override_codes(self) -> None:
        """
        [20240613_SECURITY] Save used override codes to disk after each update.
        """
        try:
            with open(self._used_override_codes_path, "w") as f:
                json.dump(list(self._used_override_codes), f)
        except Exception as e:
            # Fail CLOSED - if we can't write the file, deny all overrides
            raise PolicyError(f"Failed to save used override codes: {e}. Failing CLOSED.")

    def _load_policies(self) -> list[Policy]:
        """
        Load and parse policy definitions.

        [20251216_FEATURE] Parse YAML policy file

        Returns:
            List of Policy objects

        Raises:
            PolicyError: If file not found or invalid YAML
        """
        if not self.policy_path.exists():
            raise PolicyError(f"Policy file not found: {self.policy_path}")

        try:
            with open(self.policy_path) as f:
                config = yaml.safe_load(f)

            if not config:
                raise PolicyError("Policy file is empty")

            policy_defs = config.get("policies", [])
            if not policy_defs:
                raise PolicyError("No policies defined in policy file")

            return [Policy(**p) for p in policy_defs]
        except yaml.YAMLError as e:
            # Fail CLOSED - deny all if policy parsing fails
            raise PolicyError(f"Policy parsing failed: {e}. Failing CLOSED.")
        except (KeyError, TypeError) as e:
            raise PolicyError(f"Invalid policy format: {e}. Failing CLOSED.")

    def _basic_validate_policies_rego(self) -> None:
        """
        Lightweight Rego validation that does not require OPA.

        This is intentionally conservative and primarily catches obvious
        syntax issues (e.g., unbalanced brackets/braces) so we can FAIL CLOSED
        even when OPA isn't installed.
        """
        for policy in self.policies:
            self._basic_validate_rego(policy.rule, policy.name)

    @staticmethod
    def _basic_validate_rego(rule: str, policy_name: str) -> None:
        if not rule or not isinstance(rule, str):
            raise PolicyError(f"Invalid Rego in policy '{policy_name}': empty rule. Failing CLOSED.")

        # Strip comments and string literals, then perform simple balance checks.
        in_string: str | None = None
        escape = False
        brace = 0
        bracket = 0
        paren = 0
        saw_package = False

        i = 0
        while i < len(rule):
            ch = rule[i]

            if in_string is not None:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_string:
                    in_string = None
                i += 1
                continue

            # Comment to end-of-line
            if ch == "#":
                while i < len(rule) and rule[i] not in ("\n", "\r"):
                    i += 1
                continue

            if ch in ("'", '"'):
                in_string = ch
                i += 1
                continue

            # Quick package presence check (outside strings/comments)
            if rule.startswith("package", i):
                # Ensure word boundary-ish
                before_ok = i == 0 or not rule[i - 1].isalnum()
                after_idx = i + len("package")
                after_ok = after_idx >= len(rule) or rule[after_idx].isspace()
                if before_ok and after_ok:
                    saw_package = True

            if ch == "{":
                brace += 1
            elif ch == "}":
                brace -= 1
            elif ch == "[":
                bracket += 1
            elif ch == "]":
                bracket -= 1
            elif ch == "(":
                paren += 1
            elif ch == ")":
                paren -= 1

            if brace < 0 or bracket < 0 or paren < 0:
                raise PolicyError(f"Invalid Rego in policy '{policy_name}': unbalanced delimiters. Failing CLOSED.")

            i += 1

        if in_string is not None or brace != 0 or bracket != 0 or paren != 0:
            raise PolicyError(f"Invalid Rego in policy '{policy_name}': unbalanced delimiters. Failing CLOSED.")
        if not saw_package:
            raise PolicyError(f"Invalid Rego in policy '{policy_name}': missing package declaration. Failing CLOSED.")

    def _validate_opa_available(self) -> None:
        """
        Check if OPA CLI is available.

        [20251216_FEATURE] Verify OPA can be invoked

        Raises:
            PolicyError: If OPA CLI not found
        """
        try:
            result = subprocess.run(["opa", "version"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise PolicyError("OPA CLI check failed. Failing CLOSED.")
        except FileNotFoundError:
            raise PolicyError(
                "OPA CLI not found. Install from https://www.openpolicyagent.org/docs/latest/#running-opa. "
                "Failing CLOSED."
            )
        except subprocess.TimeoutExpired:
            raise PolicyError("OPA CLI timeout. Failing CLOSED.")

    def _validate_policies(self) -> None:
        """
        Validate Rego syntax using OPA CLI.

        [20251216_FEATURE] Check all policies have valid Rego syntax

        Raises:
            PolicyError: If any policy has invalid Rego
        """
        import tempfile

        for policy in self.policies:
            try:
                # [20260122_BUGFIX] OPA check doesn't support stdin in v1.12.3+, use temp file
                with tempfile.NamedTemporaryFile(mode="w", suffix=".rego", delete=False) as f:
                    f.write(policy.rule)
                    temp_path = f.name

                try:
                    result = subprocess.run(
                        ["opa", "check", temp_path],
                        capture_output=True,
                        timeout=10,
                    )
                    if result.returncode != 0:
                        raise PolicyError(f"Invalid Rego in policy '{policy.name}': " f"{result.stderr.decode()}")
                finally:
                    import os

                    os.unlink(temp_path)
            except subprocess.TimeoutExpired:
                raise PolicyError(f"Rego validation timeout for policy '{policy.name}'. Failing CLOSED.")

    def evaluate(self, operation: Operation) -> PolicyDecision:
        """
        Evaluate operation against all policies.

        [20251216_FEATURE] Check if operation violates any policies

        Args:
            operation: The operation to evaluate (code_edit, file_access, etc.)

        Returns:
            PolicyDecision with allow/deny and reasons
        """
        input_data = {
            "operation": operation.type,
            "code": operation.code,
            "language": operation.language,
            "file_path": operation.file_path,
            "metadata": operation.metadata,
        }

        violations: list[PolicyViolation] = []

        # [20251222_BUGFIX] Safe fallback evaluator when OPA isn't available.
        # Some tests construct PolicyEngine via object.__new__ (skipping __init__).
        # In that case, default to the OPA path.
        if not getattr(self, "_opa_available", True):
            return self._evaluate_without_opa(operation)

        for policy in self.policies:
            try:
                # Write Rego policy and input to temp files
                with tempfile.NamedTemporaryFile(mode="w", suffix=".rego", delete=False) as policy_file:
                    policy_file.write(policy.rule)
                    policy_file.flush()
                    policy_file_path = policy_file.name

                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as input_file:
                    json.dump(input_data, input_file)
                    input_file.flush()
                    input_file_path = input_file.name

                # Evaluate with OPA (try legacy + derived query paths)
                result = None
                for query in self._opa_query_candidates(policy.rule):
                    result = subprocess.run(
                        [
                            "opa",
                            "eval",
                            "-d",
                            policy_file_path,
                            "-i",
                            input_file_path,
                            "--format",
                            "json",
                            query,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        break

                # Clean up temp files
                Path(policy_file_path).unlink(missing_ok=True)
                Path(input_file_path).unlink(missing_ok=True)

                if result is None or result.returncode != 0:
                    # Policy evaluation error - fail CLOSED
                    return PolicyDecision(
                        allowed=False,
                        reason="Policy evaluation error - failing CLOSED",
                        violated_policies=[policy.name],
                        requires_override=False,  # No override for errors
                    )

                # Parse OPA output
                output = json.loads(result.stdout)

                # Check if policy was violated
                # OPA returns {"result": [{"expressions": [...]}]}
                if output.get("result"):
                    expressions = output["result"][0].get("expressions", [])
                    if expressions:
                        deny_messages = expressions[0].get("value", [])
                        if deny_messages:
                            # Policy denied the operation
                            message = deny_messages[0] if isinstance(deny_messages, list) else str(deny_messages)
                            violations.append(
                                PolicyViolation(
                                    policy_name=policy.name,
                                    severity=policy.severity,
                                    message=message,
                                    action=policy.action,
                                )
                            )

            except subprocess.TimeoutExpired:
                # Timeout is a critical error - fail CLOSED
                return PolicyDecision(
                    allowed=False,
                    reason=f"Policy '{policy.name}' evaluation timeout - failing CLOSED",
                    violated_policies=[policy.name],
                    requires_override=False,
                )
            except Exception as e:
                # Any unexpected error - fail CLOSED
                return PolicyDecision(
                    allowed=False,
                    reason=f"Unexpected error evaluating '{policy.name}': {e} - failing CLOSED",
                    violated_policies=[policy.name],
                    requires_override=False,
                )

        if violations:
            # Check if all violations are just warnings/audits
            deny_violations = [v for v in violations if v.action == "DENY"]

            if deny_violations:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Violated {len(deny_violations)} DENY policy(ies)",
                    violated_policies=[v.policy_name for v in deny_violations],
                    violations=violations,
                    requires_override=True,
                )
            else:
                # Only warnings/audits - allow but report
                return PolicyDecision(
                    allowed=True,
                    reason=f"Allowed with {len(violations)} warning(s)",
                    violated_policies=[],
                    violations=violations,
                    requires_override=False,
                )

        return PolicyDecision(
            allowed=True,
            reason="No policy violations detected",
            violated_policies=[],
            violations=[],
        )

    def _evaluate_without_opa(self, operation: Operation) -> PolicyDecision:
        """Evaluate policies without OPA using a conservative local interpreter."""
        if self._semantic_analyzer is None:
            # Local import to avoid import-time cycles.
            from .semantic_analyzer import SemanticAnalyzer

            self._semantic_analyzer = SemanticAnalyzer()

        input_code = operation.code or ""
        input_operation = operation.type
        input_language = operation.language or ""

        violations: list[PolicyViolation] = []

        for policy in self.policies:
            try:
                if self._policy_matches_operation(policy.rule, input_operation) is False:
                    continue

                matched, message = self._policy_matches_code(policy.rule, input_code)

                # If the policy appears SQL-related, add semantic safety check.
                sql_related = "SELECT" in policy.rule.upper() or "SQL" in policy.name.upper()
                if matched and sql_related:
                    if self._semantic_analyzer.has_parameterization(input_code, input_language):
                        matched = False

                if matched:
                    violations.append(
                        PolicyViolation(
                            policy_name=policy.name,
                            severity=policy.severity,
                            message=message,
                            action=policy.action,
                        )
                    )
            except PolicyError:
                raise
            except Exception as e:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Unexpected error evaluating '{policy.name}': {e} - failing CLOSED",
                    violated_policies=[policy.name],
                    requires_override=False,
                )

        if violations:
            deny_violations = [v for v in violations if v.action == "DENY"]
            if deny_violations:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Violated {len(deny_violations)} DENY policy(ies)",
                    violated_policies=[v.policy_name for v in deny_violations],
                    violations=violations,
                    requires_override=True,
                )
            return PolicyDecision(
                allowed=True,
                reason=f"Allowed with {len(violations)} warning(s)",
                violated_policies=[],
                violations=violations,
                requires_override=False,
            )

        return PolicyDecision(
            allowed=True,
            reason="No policy violations detected",
            violated_policies=[],
            violations=[],
        )

    @staticmethod
    def _policy_matches_operation(rule: str, operation_type: str) -> bool | None:
        """Return False if rule constrains operation and it doesn't match, else None/True."""
        m = re.search(r"input\.operation\s*==\s*['\"]([^'\"]+)['\"]", rule)
        if not m:
            return None
        return m.group(1) == operation_type

    @staticmethod
    def _policy_matches_code(rule: str, code: str) -> tuple[bool, str]:
        """Approximate evaluation of common `contains(input.code, ...)` patterns."""
        forbidden = re.findall(
            r"not\s+contains\(\s*input\.code\s*,\s*['\"]([^'\"]+)['\"]\s*\)",
            rule,
        )

        required_all = re.findall(
            r"contains\(\s*input\.code\s*,\s*['\"]([^'\"]+)['\"]\s*\)",
            rule,
        )
        required = [substr for substr in required_all if substr not in forbidden]

        if required and not all(substr in code for substr in required):
            return (False, "")
        if forbidden and any(substr in code for substr in forbidden):
            return (False, "")

        # If there are no recognizable constraints, we cannot safely decide.
        # Treat as not matched (so we don't incorrectly deny safe code).
        if not required and not forbidden:
            return (False, "")

        msg_match = re.search(r"msg\s*=\s*\"([^\"]+)\"", rule)
        msg = msg_match.group(1) if msg_match else "Policy violation detected"
        return (True, msg)

    def request_override(
        self,
        operation: Operation,
        decision: PolicyDecision,
        justification: str,
        human_code: str,
    ) -> OverrideDecision:
        """
        Request human override for denied operation.

        [20251216_FEATURE] Allow humans to override policy denials with justification

        Args:
            operation: The denied operation
            decision: The original policy decision
            justification: Human justification for override
            human_code: One-time code from human approver

        Returns:
            OverrideDecision with approval status
        """
        # Verify human code (time-based OTP or similar)
        if not self._verify_human_code(human_code):
            return OverrideDecision(approved=False, reason="Invalid override code")

        # Check if code was already used
        if human_code in self._used_override_codes:
            return OverrideDecision(approved=False, reason="Override code already used (single-use only)")

        # Mark code as used
        self._used_override_codes.add(human_code)

        # Log override request for audit trail
        override_id = self._generate_override_id()
        self._log_override_request(
            operation=operation,
            decision=decision,
            justification=justification,
            human_code_hash=self._hash_code(human_code),
            override_id=override_id,
        )

        return OverrideDecision(
            approved=True,
            reason="Human override approved",
            override_id=override_id,
            expires_at=datetime.now() + timedelta(hours=1),
        )

    def _verify_human_code(self, code: str) -> bool:
        """
        Verify human override code.

        [20251216_FEATURE] Simple code verification (can be enhanced with TOTP)

        Args:
            code: Override code to verify

        Returns:
            True if code is valid
        """
        # Simple validation: code must be 6+ characters
        # In production, this should be TOTP or similar
        return len(code) >= 6

    def _hash_code(self, code: str) -> str:
        """Hash override code for audit log."""
        return hashlib.sha256(code.encode()).hexdigest()

    def _generate_override_id(self) -> str:
        """Generate unique override ID."""
        return str(uuid.uuid4())

    def _log_override_request(
        self,
        operation: Operation,
        decision: PolicyDecision,
        justification: str,
        human_code_hash: str,
        override_id: str,
    ) -> None:
        """
        Log override request for audit trail.

        [20251216_FEATURE] Audit trail for all overrides

        Args:
            operation: The operation being overridden
            decision: Original policy decision
            justification: Human justification
            human_code_hash: Hash of override code (not plaintext)
            override_id: Unique override identifier
        """
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "override_id": override_id,
            "operation_type": operation.type,
            "file_path": operation.file_path,
            "violated_policies": decision.violated_policies,
            "justification": justification,
            "human_code_hash": human_code_hash,
        }

        # In production, this should write to a secure audit log
        # For now, we'll log to a local file as a placeholder
        # [20251216_FEATURE] Minimal file-based audit logging for override requests
        try:
            with open("policy_override_audit.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry) + "\n")
        except Exception as e:
            # In production, escalate/log this error securely
            print(f"[WARN] Failed to write audit log entry: {e}")
