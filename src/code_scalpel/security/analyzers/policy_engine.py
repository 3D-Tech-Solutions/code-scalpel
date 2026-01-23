"""
Policy Engine - Enterprise Tier Feature.

[20251226_FEATURE] v3.2.9 - Enterprise tier custom policy enforcement.

This module enforces organization-specific security policies:
- Weak cryptography detection (MD5, SHA-1)
- Sensitive data logging detection
- Banned API usage
- Custom organizational rules
"""

import ast
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PolicyViolation:
    """A detected policy violation."""

    policy_id: str  # Unique policy identifier
    policy_name: str  # Human-readable name
    severity: str  # "critical", "high", "medium", "low"
    line: int  # Line number
    description: str  # Violation description
    remediation: str  # How to fix


class PolicyEngine:
    """
    Enforces custom security policies.

    Enterprise tier feature for organization-specific security rules.
    """

    def __init__(self):
        """Initialize the policy engine."""
        self.policies = self._load_default_policies()

    def _load_default_policies(self) -> dict[str, dict[str, Any]]:
        """Load default policies."""
        return {
            "weak_crypto": {
                "id": "POL001",
                "name": "Weak Cryptography Forbidden",
                "severity": "high",
                "patterns": ["md5", "sha1", "sha-1", "des"],
                "description": "Weak cryptographic algorithms must not be used",
                "remediation": "Use SHA-256 or stronger algorithms",
            },
            "sensitive_logging": {
                "id": "POL002",
                "name": "Sensitive Data Logging Forbidden",
                "severity": "high",
                "patterns": ["password", "token", "secret", "api_key", "credit_card"],
                "description": "Sensitive data must not be logged",
                "remediation": "Remove sensitive data from log statements or use masking",
            },
            "banned_functions": {
                "id": "POL003",
                "name": "Banned Functions",
                "severity": "critical",
                "functions": ["eval", "exec", "compile", "__import__"],
                "description": "Banned dangerous functions",
                "remediation": "Refactor to avoid dynamic code execution",
            },
            "insecure_random": {
                "id": "POL004",
                "name": "Insecure Random Number Generation",
                "severity": "medium",
                "patterns": ["random.random", "random.randint", "random.choice"],
                "description": "Use secrets module for cryptographic randomness",
                "remediation": "Replace with secrets.SystemRandom() or secrets module",
            },
        }

    def check_weak_crypto(self, code: str) -> list[PolicyViolation]:
        """
        Check for weak cryptography usage.

        Args:
            code: Python source code

        Returns:
            List of policy violations
        """
        violations = []
        policy = self.policies["weak_crypto"]

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_function_name(node)
                if func_name:
                    for pattern in policy["patterns"]:
                        if pattern.lower() in func_name.lower():
                            violations.append(
                                PolicyViolation(
                                    policy_id=policy["id"],
                                    policy_name=policy["name"],
                                    severity=policy["severity"],
                                    line=node.lineno,
                                    description=f"{policy['description']}: {func_name} detected",
                                    remediation=policy["remediation"],
                                )
                            )
                            break

        return violations

    def check_sensitive_logging(self, code: str) -> list[PolicyViolation]:
        """
        Check for sensitive data in logging statements.

        Args:
            code: Python source code

        Returns:
            List of policy violations
        """
        violations = []
        policy = self.policies["sensitive_logging"]

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_function_name(node)
                if func_name and any(log_func in func_name.lower() for log_func in ["log", "print", "logger"]):
                    # Check arguments for sensitive keywords
                    for arg in node.args:
                        arg_str = ast.unparse(arg) if hasattr(ast, "unparse") else ""
                        for pattern in policy["patterns"]:
                            if pattern.lower() in arg_str.lower():
                                violations.append(
                                    PolicyViolation(
                                        policy_id=policy["id"],
                                        policy_name=policy["name"],
                                        severity=policy["severity"],
                                        line=node.lineno,
                                        description=f"{policy['description']}: '{pattern}' found in log statement",
                                        remediation=policy["remediation"],
                                    )
                                )
                                break

        return violations

    def check_banned_functions(self, code: str) -> list[PolicyViolation]:
        """
        Check for banned function usage.

        Args:
            code: Python source code

        Returns:
            List of policy violations
        """
        violations = []
        policy = self.policies["banned_functions"]

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_function_name(node)
                if func_name:
                    for banned in policy["functions"]:
                        if banned == func_name or func_name.endswith(f".{banned}"):
                            violations.append(
                                PolicyViolation(
                                    policy_id=policy["id"],
                                    policy_name=policy["name"],
                                    severity=policy["severity"],
                                    line=node.lineno,
                                    description=f"{policy['description']}: {func_name} is banned",
                                    remediation=policy["remediation"],
                                )
                            )
                            break

        return violations

    def check_insecure_random(self, code: str) -> list[PolicyViolation]:
        """
        Check for insecure random number generation.

        Args:
            code: Python source code

        Returns:
            List of policy violations
        """
        violations = []
        policy = self.policies["insecure_random"]

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_function_name(node)
                if func_name:
                    for pattern in policy["patterns"]:
                        if pattern in func_name:
                            violations.append(
                                PolicyViolation(
                                    policy_id=policy["id"],
                                    policy_name=policy["name"],
                                    severity=policy["severity"],
                                    line=node.lineno,
                                    description=f"{policy['description']}: {func_name} is not cryptographically secure",
                                    remediation=policy["remediation"],
                                )
                            )
                            break

        return violations

    def check_all_policies(self, code: str) -> list[PolicyViolation]:
        """
        Run all policy checks.

        Args:
            code: Python source code

        Returns:
            List of all policy violations
        """
        all_violations = []

        all_violations.extend(self.check_weak_crypto(code))
        all_violations.extend(self.check_sensitive_logging(code))
        all_violations.extend(self.check_banned_functions(code))
        all_violations.extend(self.check_insecure_random(code))

        return all_violations

    def _get_function_name(self, node: ast.Call) -> str | None:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle module.function calls
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def add_custom_policy(
        self,
        policy_id: str,
        name: str,
        severity: str,
        patterns: list[str],
        description: str,
        remediation: str,
    ) -> None:
        """
        Add a custom policy.

        Args:
            policy_id: Unique policy ID
            name: Policy name
            severity: Severity level
            patterns: List of patterns to match
            description: Policy description
            remediation: How to fix violations
        """
        self.policies[policy_id] = {
            "id": policy_id,
            "name": name,
            "severity": severity,
            "patterns": patterns,
            "description": description,
            "remediation": remediation,
        }
