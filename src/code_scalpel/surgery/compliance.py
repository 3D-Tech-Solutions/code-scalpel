"""Enterprise compliance checking for rename operations.

# [20260108_FEATURE] Enterprise-tier compliance validation

This module provides compliance checking for code surgery operations,
enabling Enterprise customers to validate operations against governance
policies before execution.

Integration with UnifiedGovernance system:
- Policy validation (OPA/Rego)
- Change budget enforcement
- Semantic security analysis
- Compliance reporting
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from code_scalpel.governance.unified_governance import (
        GovernanceDecision,
        UnifiedGovernance,
    )

    Operation = None  # type: ignore

    GOVERNANCE_AVAILABLE = True
except ImportError:
    GOVERNANCE_AVAILABLE = False
    Operation = None  # type: ignore
    UnifiedGovernance = None  # type: ignore
    GovernanceDecision = None  # type: ignore


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check."""

    allowed: bool
    reason: str | None = None
    violations: list[dict] | None = None

    def __post_init__(self):
        if self.violations is None:
            self.violations = []


def check_rename_compliance(
    target_file: str,
    target_type: str,
    target_name: str,
    new_name: str,
    project_root: Path | None = None,
    governance_dir: str | None = None,
) -> ComplianceCheckResult:
    """
    Check if a rename operation complies with governance policies.

    Args:
        target_file: File containing the symbol to rename
        target_type: Type of symbol (function, class, method)
        target_name: Original name
        new_name: New name
        project_root: Project root directory
        governance_dir: Governance configuration directory (default: .code-scalpel)

    Returns:
        ComplianceCheckResult indicating if operation is allowed
    """
    if not GOVERNANCE_AVAILABLE:
        # If governance not available, allow by default (graceful degradation)
        return ComplianceCheckResult(allowed=True, reason="Governance system not available, allowing by default")

    try:
        # Initialize governance system
        if governance_dir is None and project_root:
            governance_dir = str(project_root / ".code-scalpel")

        if UnifiedGovernance is None:
            return ComplianceCheckResult(
                allowed=False,
                reason="UnifiedGovernance is not available",
                violations=[],
            )
        gov = UnifiedGovernance(governance_dir or ".code-scalpel")

        # Create operation for governance evaluation
        if Operation is None:
            return ComplianceCheckResult(
                allowed=False,
                reason="Governance operation not available",
                violations=[],
            )

        operation = Operation(
            type="rename_symbol",
            code=f"# Rename {target_type} {target_name} -> {new_name}",
            language="python",
            file_path=target_file,
            metadata={
                "target_type": target_type,
                "target_name": target_name,
                "new_name": new_name,
                "operation": "rename",
            },
        )

        # Evaluate against policies
        decision = gov.evaluate(operation)

        if decision.allowed:
            return ComplianceCheckResult(allowed=True)
        else:
            # Extract violation details
            violations = [
                {
                    "rule": v.rule,
                    "message": v.message,
                    "severity": v.severity,
                    "source": (v.source.value if hasattr(v.source, "value") else str(v.source)),
                }
                for v in decision.violations
            ]

            return ComplianceCheckResult(allowed=False, reason=decision.reason, violations=violations)

    except Exception as e:
        # Fail closed: if governance check fails, deny the operation
        return ComplianceCheckResult(
            allowed=False,
            reason=f"Governance check failed: {e}",
            violations=[
                {
                    "rule": "governance_error",
                    "message": str(e),
                    "severity": "critical",
                    "source": "compliance",
                }
            ],
        )


def format_compliance_error(result: ComplianceCheckResult) -> str:
    """
    Format compliance check result into user-friendly error message.

    Args:
        result: ComplianceCheckResult from check_rename_compliance

    Returns:
        Formatted error message
    """
    if result.allowed:
        return ""

    lines = [f"Compliance check failed: {result.reason}"]

    if result.violations:
        lines.append("\nViolations:")
        for v in result.violations:
            severity = v.get("severity", "unknown")
            rule = v.get("rule", "unknown")
            message = v.get("message", "")
            source = v.get("source", "unknown")
            lines.append(f"  [{severity.upper()}] {rule} ({source}): {message}")

    return "\n".join(lines)
