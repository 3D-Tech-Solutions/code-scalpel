"""
Governance and compliance reporting module for Code Scalpel.

[20251221_FEATURE] v3.1.0 - Unified governance system with policy consolidation

This module provides enterprise-grade compliance reporting and unified governance
that integrates policy enforcement with change budgeting.
"""

# [20251216_FEATURE] v2.5.0 Compliance reporting module
# [20251221_FEATURE] v3.1.0 Unified governance system and policy consolidation

# [20251221_FEATURE] Change budget implementation
from code_scalpel.governance.change_budget import (
    BudgetDecision,
    BudgetViolation,
    ChangeBudget,
    FileChange,
    Operation,
)
from code_scalpel.governance.compliance_reporter import (
    ComplianceReport,
    ComplianceReporter,
    OverrideAnalysis,
    Recommendation,
    ReportSummary,
    SecurityPosture,
    ViolationAnalysis,
)

# [20251225_FEATURE] Governance configuration (moved from config/)
from code_scalpel.governance.governance_config import (
    AuditConfig,
    AutonomyConstraintsConfig,
    BlastRadiusConfig,
    ChangeBudgetingConfig,
    GovernanceConfig,
    GovernanceConfigLoader,
)

# [20251221_FEATURE] Unified governance system
from code_scalpel.governance.unified_governance import (
    GovernanceContext,
    GovernanceDecision,
    GovernanceViolation,
    UnifiedGovernance,
    ViolationSource,
)
from code_scalpel.policy_engine import PolicyEngine

# [20251221_REFACTOR] v3.1.0 - Use policy_engine's audit_log, not local stub
from code_scalpel.policy_engine.audit_log import AuditLog

__all__ = [
    # Compliance reporting (v2.5.0)
    "ComplianceReporter",
    "ComplianceReport",
    "ReportSummary",
    "ViolationAnalysis",
    "OverrideAnalysis",
    "SecurityPosture",
    "Recommendation",
    "AuditLog",
    "PolicyEngine",
    # Change budgeting (v3.1.0)
    "ChangeBudget",
    "BudgetViolation",
    "Operation",
    "FileChange",
    "BudgetDecision",
    # Unified governance (v3.1.0)
    "UnifiedGovernance",
    "GovernanceDecision",
    "GovernanceViolation",
    "GovernanceContext",
    "ViolationSource",
    # Governance configuration (moved from config/)
    "GovernanceConfig",
    "GovernanceConfigLoader",
    "ChangeBudgetingConfig",
    "BlastRadiusConfig",
    "AutonomyConstraintsConfig",
    "AuditConfig",
]
