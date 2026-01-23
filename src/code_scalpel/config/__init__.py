# [20251218_FEATURE] Governance configuration module for v3.0.0 "Autonomy"

"""
Configuration module for Code Scalpel.
"""

# [20251225_DEPRECATE] Governance config moved to code_scalpel.governance
# For backward compatibility, import from new location
from code_scalpel.governance import (
    AuditConfig,
    AutonomyConstraintsConfig,
    BlastRadiusConfig,
    ChangeBudgetingConfig,
    GovernanceConfig,
    GovernanceConfigLoader,
)

# [20251219_FEATURE] v3.0.2 - Configuration initialization
from .init_config import init_config_dir

__all__ = [
    "ChangeBudgetingConfig",
    "BlastRadiusConfig",
    "AutonomyConstraintsConfig",
    "AuditConfig",
    "GovernanceConfig",
    "GovernanceConfigLoader",
    "init_config_dir",
]
