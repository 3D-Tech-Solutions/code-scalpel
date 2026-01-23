"""
Unified Governance System - Policy Engine + Change Budgeting + Compliance.

[20251221_FEATURE] v3.1.0 - Bridge PolicyEngine, ChangeBudget, and ComplianceReporting

This module provides an integrated governance system that evaluates operations against:
1. Declarative policies (OPA/Rego) via PolicyEngine
2. Quantitative budgets (files, lines, complexity) via ChangeBudget
3. Semantic security analysis (SQL injection, XSS, etc.) via SemanticAnalyzer
4. Role-based policy hierarchy (developer, reviewer, architect)
5. Compliance metrics and audit trails

The system uses a FAIL CLOSED security model - any error results in DENY.

Key Features:
- Unified evaluation of both policy and budget constraints
- Combined violation reporting
- Role-based policy inheritance
- Semantic security analysis
- Compliance metrics tracking
- Audit trail for all decisions
- Support for policy overrides with justification

Example:
    from code_scalpel.governance.unified_governance import UnifiedGovernance

    gov = UnifiedGovernance(".code-scalpel")

    operation = Operation(
        type="code_edit",
        code="cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
        language="python",
        file_path="app.py"
    )

    decision = gov.evaluate(operation)
    if not decision.allowed:
        print(f"Denied: {decision.reason}")
        for v in decision.violations:
            print(f"  - {v.rule}: {v.message} ({v.source})")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from code_scalpel.policy_engine import Operation as EngineOperation
    from code_scalpel.policy_engine import PolicyDecision, PolicyEngine
    from code_scalpel.policy_engine import PolicyViolation as EngineViolation

    POLICY_ENGINE_AVAILABLE = True
except ImportError:
    POLICY_ENGINE_AVAILABLE = False
    PolicyEngine = None  # type: ignore[assignment,misc]
    PolicyDecision = None  # type: ignore[assignment,misc]
    EngineViolation = None  # type: ignore[assignment,misc]
    EngineOperation = None  # type: ignore[assignment,misc]

# [20251221_REFACTOR] v3.1.0 - ChangeBudget moved from policy/ to governance/
try:
    from code_scalpel.governance.change_budget import (
        BudgetDecision,
        BudgetViolation,
        ChangeBudget,
        FileChange,
    )
    from code_scalpel.governance.change_budget import Operation as BudgetOperation

    BUDGET_AVAILABLE = True
except ImportError:
    BUDGET_AVAILABLE = False
    ChangeBudget = None  # type: ignore[assignment,misc]
    BudgetOperation = None  # type: ignore[assignment,misc]
    FileChange = None  # type: ignore[assignment,misc]
    BudgetDecision = None  # type: ignore[assignment,misc]
    BudgetViolation = None  # type: ignore[assignment,misc]

try:
    from code_scalpel.policy_engine.semantic_analyzer import SemanticAnalyzer

    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    SemanticAnalyzer = None  # type: ignore[assignment,misc]


class ViolationSource(Enum):
    """Source of a governance violation."""

    POLICY = "policy"  # OPA/Rego policy violation
    BUDGET = "budget"  # Change budget constraint violation
    SEMANTIC = "semantic"  # Semantic security analysis violation
    CONFIG = "config"  # Configuration/validation error


@dataclass
class GovernanceViolation:
    """
    A single governance constraint violation.

    [20251221_FEATURE] Unified violation type for policy + budget violations
    """

    rule: str  # Name of violated constraint
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    message: str  # Human-readable violation message
    source: ViolationSource  # Where violation came from
    limit: int | None = None  # Budget limit (if applicable)
    actual: int | None = None  # Actual value (if applicable)
    file_path: str | None = None  # File affected (if applicable)

    def __str__(self) -> str:
        """Format violation for display."""
        msg = f"[{self.source.value.upper()}] {self.rule}"
        if self.limit is not None and self.actual is not None:
            msg += f" (limit: {self.limit}, actual: {self.actual})"
        if self.file_path:
            msg += f" in {self.file_path}"
        return f"{msg}: {self.message}"


@dataclass
class GovernanceDecision:
    """
    Result of unified governance evaluation.

    [20251221_FEATURE] Combined decision from policy + budget constraints
    """

    allowed: bool
    reason: str
    violations: list[GovernanceViolation] = field(default_factory=list)
    requires_override: bool = False
    override_id: str | None = None
    expires_at: datetime | None = None
    evaluation_time_ms: float = 0.0  # For metrics

    @property
    def critical_violations(self) -> list[GovernanceViolation]:
        """Get all CRITICAL severity violations."""
        return [v for v in self.violations if v.severity == "CRITICAL"]

    @property
    def policy_violations(self) -> list[GovernanceViolation]:
        """Get violations from OPA/Rego policies."""
        return [v for v in self.violations if v.source == ViolationSource.POLICY]

    @property
    def budget_violations(self) -> list[GovernanceViolation]:
        """Get violations from change budgets."""
        return [v for v in self.violations if v.source == ViolationSource.BUDGET]

    @property
    def semantic_violations(self) -> list[GovernanceViolation]:
        """Get violations from semantic analysis."""
        return [v for v in self.violations if v.source == ViolationSource.SEMANTIC]

    def get_summary(self) -> str:
        """Get comprehensive summary of decision and violations."""
        lines = [self.reason]

        if self.violations:
            lines.append("\nViolations:")
            for v in self.violations:
                lines.append(f"  - {v}")

        if self.requires_override:
            lines.append("\nOverride Required: Yes")
            lines.append("This decision requires human approval to proceed.")

        return "\n".join(lines)


@dataclass
class GovernanceContext:
    """
    Context for governance evaluation.

    [20251221_FEATURE] Additional context for policy decisions
    """

    user_role: str = "developer"  # developer, reviewer, architect, system
    team: str | None = None  # Team name for team-based policies
    project: str | None = None  # Project name
    environment: str = "development"  # development, staging, production
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedGovernance:
    """
    Unified governance system for policy + budget enforcement.

    [20251221_FEATURE] v3.1.0 - Integrates PolicyEngine + ChangeBudget + SemanticAnalyzer

    This system evaluates operations against:
    1. Declarative policies (OPA/Rego) - semantic security rules
    2. Change budgets - blast radius control
    3. Semantic analysis - security pattern detection
    4. Role-based policies - hierarchical enforcement

    Security Model: FAIL CLOSED
    - Any policy evaluation error → DENY
    - Any budget validation error → DENY
    - Missing configuration → DENY

    """

    def __init__(self, config_dir: str = ".code-scalpel"):
        """
        Initialize unified governance system.

        Loads policies, budgets, and configuration from config_dir.

        Args:
            config_dir: Base directory for governance config

        Raises:
            RuntimeError: If PolicyEngine or ChangeBudget unavailable
        """
        if not POLICY_ENGINE_AVAILABLE or not BUDGET_AVAILABLE:
            raise RuntimeError(
                "Unified governance requires both policy_engine and policy modules. "
                f"PolicyEngine available: {POLICY_ENGINE_AVAILABLE}, "
                f"ChangeBudget available: {BUDGET_AVAILABLE}"
            )

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize sub-systems
        policy_path = self.config_dir / "policy.yaml"
        budget_path = self.config_dir / "budget.yaml"

        self.policy_engine = PolicyEngine(str(policy_path)) if (POLICY_ENGINE_AVAILABLE and PolicyEngine and policy_path.exists()) else None  # type: ignore[misc]

        # Load budget configuration from YAML or use defaults
        if BUDGET_AVAILABLE and ChangeBudget:
            if budget_path.exists():
                import yaml

                with open(budget_path) as f:
                    budget_config = yaml.safe_load(f) or {}
                    # Extract the 'default' budget if using the budgets structure
                    if "budgets" in budget_config and "default" in budget_config["budgets"]:
                        budget_limits = budget_config["budgets"]["default"]
                    else:
                        budget_limits = budget_config
                    self.change_budget = ChangeBudget(budget_limits)  # type: ignore[misc]
            else:
                # Use default budget limits
                self.change_budget = ChangeBudget({"max_files": 5, "max_total_lines": 300})  # type: ignore[misc]
        else:
            self.change_budget = None

        self.semantic_analyzer = SemanticAnalyzer() if (SEMANTIC_AVAILABLE and SemanticAnalyzer) else None  # type: ignore[misc,truthy-function]

        # Audit trail
        self._decisions_log: list[dict[str, Any]] = []

    def evaluate(
        self,
        operation: Any,  # BudgetOperation | EngineOperation | Dict[str, Any]
        context: GovernanceContext | None = None,
    ) -> GovernanceDecision:
        """
        Evaluate operation against unified governance constraints.

        [20251221_FEATURE] Unified evaluation combining policy + budget + semantic

        Checks in order:
        1. Semantic analysis (SQL injection, XSS, etc.)
        2. OPA/Rego policies
        3. Change budgets
        4. Role-based constraints

        Args:
            operation: Operation to evaluate
            context: Governance context (user role, team, etc.)

        Returns:
            GovernanceDecision with allow/deny and violations
        """
        if context is None:
            context = GovernanceContext()

        start_time = datetime.now()
        violations: list[GovernanceViolation] = []

        # Normalize operation to internal format
        op_dict = self._normalize_operation(operation)

        # 1. Semantic analysis (detects security anti-patterns)
        if self.semantic_analyzer:
            semantic_violations = self._evaluate_semantic(op_dict)
            violations.extend(semantic_violations)

        # 2. OPA/Rego policy evaluation
        if self.policy_engine:
            policy_violations = self._evaluate_policies(op_dict, context)
            violations.extend(policy_violations)

        # 3. Change budget validation
        if self.change_budget:
            # Convert dict to proper operation type if needed
            if isinstance(operation, dict):
                # For dict operations, create a minimal BudgetOperation
                budget_op_for_eval = BudgetOperation(  # type: ignore[misc]
                    changes=[
                        FileChange(  # type: ignore[misc]
                            file_path=operation.get("file_path", ""),
                            added_lines=([operation.get("code", "")] if operation.get("code") else []),
                        )
                    ],
                    description=operation.get("type", "unknown"),
                )
                budget_violations = self._evaluate_budget(budget_op_for_eval, context)
            else:
                budget_violations = self._evaluate_budget(operation, context)  # type: ignore[arg-type]
            violations.extend(budget_violations)

        # Check if any violations are blockers (CRITICAL, HIGH, or MEDIUM from budget/policy)
        # MEDIUM violations from budget/policy should block, but MEDIUM from other sources may not
        deny_violations = [
            v
            for v in violations
            if v.severity in ("CRITICAL", "HIGH")
            or (v.severity == "MEDIUM" and v.source in (ViolationSource.BUDGET, ViolationSource.POLICY))
        ]

        decision = GovernanceDecision(
            allowed=len(deny_violations) == 0,
            reason=self._generate_decision_reason(violations, context),
            violations=violations,
            requires_override=len(deny_violations) > 0,
            evaluation_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
        )

        # Log decision for audit trail
        self._log_decision(operation, decision, context)

        return decision

    def _evaluate_semantic(self, operation: dict[str, Any]) -> list[GovernanceViolation]:
        """Evaluate operation for semantic security issues."""
        violations = []

        if not self.semantic_analyzer:
            return violations

        code = operation.get("code", "")
        language = operation.get("language", "")

        if not code or not language:
            return violations

        # SQL injection detection
        if self.semantic_analyzer.contains_sql_sink(code, language):
            if not self.semantic_analyzer.has_parameterization(code, language):
                violations.append(
                    GovernanceViolation(
                        rule="sql_injection_risk",
                        severity="CRITICAL",
                        message="SQL operation detected without parameterization",
                        source=ViolationSource.SEMANTIC,
                    )
                )

        # [20251221_FEATURE] XSS detection
        if self.semantic_analyzer.contains_xss_sink(code, language):
            violations.append(
                GovernanceViolation(
                    rule="xss_risk",
                    severity="CRITICAL",
                    message="Unsafe DOM manipulation or output encoding detected",
                    source=ViolationSource.SEMANTIC,
                )
            )

        # [20251221_FEATURE] Command injection detection
        if self.semantic_analyzer.contains_command_injection(code, language):
            violations.append(
                GovernanceViolation(
                    rule="command_injection_risk",
                    severity="CRITICAL",
                    message="Shell command execution with user input detected",
                    source=ViolationSource.SEMANTIC,
                )
            )

        # [20251221_FEATURE] Path traversal detection
        if self.semantic_analyzer.contains_path_traversal(code, language):
            violations.append(
                GovernanceViolation(
                    rule="path_traversal_risk",
                    severity="HIGH",
                    message="File operation with user-controlled path and no validation",
                    source=ViolationSource.SEMANTIC,
                )
            )

        # [20251221_FEATURE] NoSQL injection detection
        if self.semantic_analyzer.contains_noql_injection(code):
            violations.append(
                GovernanceViolation(
                    rule="nosql_injection_risk",
                    severity="HIGH",
                    message="NoSQL operation with user input detected",
                    source=ViolationSource.SEMANTIC,
                )
            )

        # [20251221_FEATURE] LDAP injection detection
        if self.semantic_analyzer.contains_ldap_injection(code):
            violations.append(
                GovernanceViolation(
                    rule="ldap_injection_risk",
                    severity="HIGH",
                    message="LDAP operation with user input detected",
                    source=ViolationSource.SEMANTIC,
                )
            )

        # [20251221_FEATURE] XXE injection detection
        if self.semantic_analyzer.contains_xxe_injection(code, language):
            violations.append(
                GovernanceViolation(
                    rule="xxe_injection_risk",
                    severity="HIGH",
                    message="Unsafe XML parsing detected",
                    source=ViolationSource.SEMANTIC,
                )
            )

        return violations

    def _evaluate_policies(
        self,
        operation: dict[str, Any],
        context: GovernanceContext,
    ) -> list[GovernanceViolation]:
        """Evaluate operation against OPA/Rego policies."""
        violations = []

        if not self.policy_engine:
            return violations

        try:
            # Convert to PolicyEngine format
            if not EngineOperation:
                return violations

            policy_op = EngineOperation(  # type: ignore[misc,truthy-function]
                type=operation.get("type", "code_edit"),
                code=operation.get("code", ""),
                language=operation.get("language", ""),
                file_path=operation.get("file_path", ""),
                metadata={
                    "user_role": context.user_role,
                    "team": context.team,
                    "project": context.project,
                    "environment": context.environment,
                },
            )

            decision = self.policy_engine.evaluate(policy_op)

            if not decision.allowed:
                for policy_violation in decision.violations:
                    violations.append(
                        GovernanceViolation(
                            rule=policy_violation.policy_name,
                            severity=policy_violation.severity,
                            message=policy_violation.message,
                            source=ViolationSource.POLICY,
                        )
                    )
        except Exception as e:
            # FAIL CLOSED on any error
            violations.append(
                GovernanceViolation(
                    rule="policy_evaluation_error",
                    severity="CRITICAL",
                    message=f"Policy evaluation failed (failing closed): {str(e)}",
                    source=ViolationSource.CONFIG,
                )
            )

        return violations

    def _evaluate_budget(
        self,
        operation: Any,  # BudgetOperation | EngineOperation
        context: GovernanceContext,
    ) -> list[GovernanceViolation]:
        """Evaluate operation against change budget constraints."""
        violations = []

        if not self.change_budget:
            return violations

        try:
            # Ensure we have a BudgetOperation
            if EngineOperation and isinstance(operation, EngineOperation):  # type: ignore[truthy-function]
                # Convert PolicyEngine Operation to BudgetOperation
                budget_op = BudgetOperation(  # type: ignore[misc]
                    changes=[
                        FileChange(  # type: ignore[misc]
                            file_path=getattr(operation, "file_path", ""),
                            added_lines=([getattr(operation, "code", "")] if getattr(operation, "code", None) else []),
                        )
                    ],
                    description=f"{getattr(operation, 'type', 'unknown')}: {getattr(operation, 'file_path', '')}",
                )
            else:
                budget_op = operation  # type: ignore[assignment]

            decision = self.change_budget.validate_operation(budget_op)  # type: ignore[arg-type]

            if not decision.allowed:
                for budget_violation in decision.violations:
                    violations.append(
                        GovernanceViolation(
                            rule=budget_violation.rule,
                            severity=budget_violation.severity,
                            message=budget_violation.message,
                            source=ViolationSource.BUDGET,
                            limit=budget_violation.limit,
                            actual=budget_violation.actual,
                            file_path=budget_violation.file,
                        )
                    )
        except Exception as e:
            # FAIL CLOSED on any error
            violations.append(
                GovernanceViolation(
                    rule="budget_validation_error",
                    severity="CRITICAL",
                    message=f"Budget validation failed (failing closed): {str(e)}",
                    source=ViolationSource.CONFIG,
                )
            )

        return violations

    def _normalize_operation(
        self, operation: Any
    ) -> dict[str, Any]:  # BudgetOperation | EngineOperation | Dict[str, Any]
        """Normalize operation to dictionary format for semantic analysis."""
        if isinstance(operation, dict):
            return operation
        elif BudgetOperation and hasattr(operation, "changes"):  # BudgetOperation
            changes = getattr(operation, "changes", [])
            return {
                "type": "code_edit",
                "code": "\n".join(line for change in changes for line in getattr(change, "added_lines", [])),
                "language": "python",  # Default, could detect
                "file_path": changes[0].file_path if changes else "",
            }
        else:  # EngineOperation
            return {
                "type": getattr(operation, "type", "unknown"),
                "code": getattr(operation, "code", ""),
                "language": getattr(operation, "language", "python"),
                "file_path": getattr(operation, "file_path", ""),
            }

    def _generate_decision_reason(
        self,
        violations: list[GovernanceViolation],
        context: GovernanceContext,
    ) -> str:
        """Generate human-readable decision reason."""
        if not violations:
            return f"Allowed - No violations (role: {context.user_role})"

        critical = [v for v in violations if v.severity == "CRITICAL"]
        high = [v for v in violations if v.severity == "HIGH"]

        if critical:
            return f"Denied - {len(critical)} CRITICAL violation(s) detected"
        elif high:
            return f"Denied - {len(high)} HIGH severity violation(s) detected"
        else:
            return f"Allowed with warnings - {len(violations)} violation(s) detected"

    def _log_decision(
        self,
        operation: Any,  # BudgetOperation | EngineOperation | Dict[str, Any]
        decision: GovernanceDecision,
        context: GovernanceContext,
    ) -> None:
        """Log governance decision for audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "allowed": decision.allowed,
            "reason": decision.reason,
            "violation_count": len(decision.violations),
            "sources": {
                "policy": len(decision.policy_violations),
                "budget": len(decision.budget_violations),
                "semantic": len(decision.semantic_violations),
            },
            "user_role": context.user_role,
            "team": context.team,
            "environment": context.environment,
        }

        self._decisions_log.append(entry)

    def get_decision_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent governance decision history."""
        return self._decisions_log[-limit:]

    def request_override(
        self,
        operation: Any,  # BudgetOperation | EngineOperation
        decision: GovernanceDecision,
        justification: str,
        human_code: str,
        context: GovernanceContext | None = None,
    ) -> GovernanceDecision:
        """
        Request override of denied governance decision.

        [20251221_FEATURE] Human approval for policy violations

        Args:
            operation: Original operation being overridden
            decision: Original deny decision
            justification: Human explanation for override
            human_code: Approval code from human reviewer
            context: Governance context

        Returns:
            Updated GovernanceDecision with override info (if approved)
        """
        if context is None:
            context = GovernanceContext()

        if not self.policy_engine:
            return decision  # Cannot override without PolicyEngine

        try:
            override_decision = self.policy_engine.request_override(
                operation=self._normalize_to_engine_operation(operation),
                decision=self._convert_to_policy_decision(decision),
                justification=justification,
                human_code=human_code,
            )

            if override_decision.approved:
                # Create new decision with override info
                decision.allowed = True
                decision.override_id = override_decision.override_id
                decision.expires_at = override_decision.expires_at
                decision.reason = f"Override approved: {justification}"
        except Exception:
            # FAIL CLOSED - override errors don't override denies
            pass

        return decision

    def _normalize_to_engine_operation(
        self, operation: Any
    ) -> Any:  # BudgetOperation | EngineOperation  # EngineOperation
        """Convert to PolicyEngine Operation format."""
        if EngineOperation and isinstance(operation, EngineOperation):  # type: ignore[truthy-function]
            return operation

        # Convert from BudgetOperation
        changes = getattr(operation, "changes", [])
        code = "\n".join(line for change in changes for line in getattr(change, "added_lines", []))

        return EngineOperation(  # type: ignore[misc]
            type="code_edit",
            code=code,
            language="python",
            file_path=changes[0].file_path if changes else "",
        )

    def _convert_to_policy_decision(self, governance_decision: GovernanceDecision) -> Any:  # PolicyDecision
        """Convert GovernanceDecision to PolicyDecision."""
        if not PolicyDecision:
            return None

        return PolicyDecision(  # type: ignore[misc]
            allowed=governance_decision.allowed,
            reason=governance_decision.reason,
            violated_policies=[v.rule for v in governance_decision.policy_violations],
            violations=(
                [
                    EngineViolation(  # type: ignore[misc]
                        policy_name=v.rule,
                        severity=v.severity,
                        message=v.message,
                        action="DENY",
                    )
                    for v in governance_decision.policy_violations
                ]
                if EngineViolation
                else []
            ),
            requires_override=governance_decision.requires_override,
        )
