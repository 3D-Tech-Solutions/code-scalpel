"""
Code Policy Check - Code analysis and policy enforcement engine.

[20251226_FEATURE] v3.4.0 - New tool for code style, best practices, and compliance checking.

This module provides tier-based code policy enforcement:
- Community: Style guide checking (PEP8, ESLint), basic pattern detection
- Pro: Best practice analysis, async patterns, security patterns, custom rules
- Enterprise: Compliance auditing (HIPAA, SOC2, GDPR), PDF certification, audit trail

Usage:
    from code_scalpel.policy_engine.code_policy_check import CodePolicyChecker

    checker = CodePolicyChecker(tier="community")
    result = checker.check_files(["src/main.py"])

    if not result.success:
        for violation in result.violations:
            print(f"{violation.file}:{violation.line} - {violation.message}")
"""

from .analyzer import CodePolicyChecker
from .models import (
    AuditEntry,
    BestPracticeViolation,
    Certification,
    CodePolicyResult,
    ComplianceReport,
    PatternMatch,
    PolicyViolation,
    SecurityWarning,
    ViolationSeverity,
)
from .patterns import ASYNC_PATTERNS, PYTHON_ANTIPATTERNS, SECURITY_PATTERNS

__all__ = [
    # Main checker
    "CodePolicyChecker",
    # Result models
    "CodePolicyResult",
    "PolicyViolation",
    "BestPracticeViolation",
    "PatternMatch",
    "SecurityWarning",
    "ComplianceReport",
    "AuditEntry",
    "Certification",
    "ViolationSeverity",
    # Pattern definitions
    "PYTHON_ANTIPATTERNS",
    "SECURITY_PATTERNS",
    "ASYNC_PATTERNS",
]
