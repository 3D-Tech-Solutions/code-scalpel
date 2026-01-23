"""
Policy Engine - Enterprise Governance for AI Agents.

[20251216_FEATURE] v2.5.0 Guardian - Policy-as-Code enforcement using OPA/Rego

This module provides declarative policy enforcement using Open Policy Agent's
Rego language for enterprise governance. It enables organizations to define
rules that agents must follow when modifying code.

Key Features:
- Declarative policy definitions in YAML
- Rego-based policy evaluation via OPA CLI
- Semantic code analysis (SQL injection, etc.)
- Fail CLOSED security model
- Human override with audit trail
- Tamper-resistant policy enforcement
- HMAC-signed audit logging
- TOTP-based human override system
- Policy file integrity verification

Example:
    from code_scalpel.policy_engine import PolicyEngine, Operation

    engine = PolicyEngine(".code-scalpel/policy.yaml")
    operation = Operation(
        type="code_edit",
        code="cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
        language="python",
        file_path="app.py"
    )

    decision = engine.evaluate(operation)
    if not decision.allowed:
        print(f"Policy violation: {decision.reason}")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# NOTE: This package contains both:
# - YAML/OPA policy engine components (require optional deps like PyYAML)
# - Cryptographic integrity verification (pure stdlib)
#
# Importing the cryptographic verifier must NOT require PyYAML, because the MCP
# server can be run in a minimal environment where only the integrity tool is
# needed.

if TYPE_CHECKING:
    from .audit_log import AuditLog
    from .exceptions import (
        InvalidOverrideCodeError,
        OverrideTimeoutError,
        PolicyEngineError,
        PolicyModificationError,
        TamperDetectedError,
    )
    from .models import HumanResponse
    from .policy_engine import (
        Operation,
        OverrideDecision,
        Policy,
        PolicyDecision,
        PolicyEngine,
        PolicyError,
        PolicyViolation,
    )
    from .semantic_analyzer import SemanticAnalyzer
    from .tamper_resistance import TamperResistance

# [20250108_FEATURE] Cryptographic Policy Verification (v2.5.0 Guardian)
from .crypto_verify import (
    CryptographicPolicyVerifier,
    PolicyManifest,
    SecurityError,
    VerificationResult,
    verify_policy_integrity_crypto,
)


def __getattr__(name: str):
    """Lazy-load YAML/OPA-dependent policy engine symbols.

    This keeps cryptographic verification usable even when optional policy
    engine dependencies (like PyYAML) are not installed.
    """

    if name in {
        "PolicyEngine",
        "Policy",
        "PolicyDecision",
        "PolicyViolation",
        "Operation",
        "OverrideDecision",
        "PolicyError",
    }:
        from . import policy_engine as _policy_engine

        return getattr(_policy_engine, name)

    if name == "SemanticAnalyzer":
        from .semantic_analyzer import SemanticAnalyzer

        return SemanticAnalyzer

    if name in {
        "TamperResistance",
        "AuditLog",
        "PolicyEngineError",
        "TamperDetectedError",
        "PolicyModificationError",
        "OverrideTimeoutError",
        "InvalidOverrideCodeError",
        "HumanResponse",
    }:
        from .audit_log import AuditLog
        from .exceptions import (
            InvalidOverrideCodeError,
            OverrideTimeoutError,
            PolicyEngineError,
            PolicyModificationError,
            TamperDetectedError,
        )
        from .models import HumanResponse
        from .tamper_resistance import TamperResistance

        mapping = {
            "TamperResistance": TamperResistance,
            "AuditLog": AuditLog,
            "PolicyEngineError": PolicyEngineError,
            "TamperDetectedError": TamperDetectedError,
            "PolicyModificationError": PolicyModificationError,
            "OverrideTimeoutError": OverrideTimeoutError,
            "InvalidOverrideCodeError": InvalidOverrideCodeError,
            "HumanResponse": HumanResponse,
        }
        return mapping[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Policy Engine core
    "PolicyEngine",
    "Policy",
    "PolicyDecision",
    "PolicyViolation",
    "Operation",
    "OverrideDecision",
    "PolicyError",
    "SemanticAnalyzer",
    # Tamper Resistance
    "TamperResistance",
    "AuditLog",
    # Cryptographic Verification (v2.5.0)
    "CryptographicPolicyVerifier",
    "PolicyManifest",
    "VerificationResult",
    "SecurityError",
    "verify_policy_integrity_crypto",
    # Exceptions
    "PolicyEngineError",
    "TamperDetectedError",
    "PolicyModificationError",
    "OverrideTimeoutError",
    "InvalidOverrideCodeError",
    # Models
    "HumanResponse",
]
