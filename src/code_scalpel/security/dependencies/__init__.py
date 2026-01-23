"""
Dependencies - Dependency vulnerability scanning.

[20251225_FEATURE] Created as part of Project Reorganization Issue #10.
[20251226_FEATURE] v3.2.9 - Pro and Enterprise tier features added.

This module contains dependency analysis tools:
- vulnerability_scanner.py: Dependency vulnerability scanning (OSV API)
- osv_client.py: OSV API client (moved from ast_tools/ in Phase 4)

Pro Tier Features:
- vulnerability_reachability.py: Reachability analysis for vulnerabilities
- false_positive_reducer.py: False positive reduction
- severity_contextualizer.py: Context-aware severity assessment

Enterprise Tier Features:
- license_compliance.py: License compliance scanning
- typosquatting_detector.py: Typosquatting attack detection
- supply_chain_scorer.py: Supply chain risk scoring
"""

from .false_positive_reducer import FalsePositiveAssessment, FalsePositiveReducer

# [20251226_FEATURE] Enterprise tier features
from .license_compliance import ComplianceReport, LicenseComplianceScanner, LicenseInfo

# [20251225_FEATURE] OSV client (moved from ast_tools/)
from .osv_client import (  # Constants for backward compatibility
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    OSV_API_URL,
    OSV_BATCH_URL,
    RETRY_DELAY,
    OSVClient,
    OSVError,
    Vulnerability,
)
from .severity_contextualizer import ContextualizedSeverity, SeverityContextualizer
from .supply_chain_scorer import RiskScore, SupplyChainReport, SupplyChainRiskScorer
from .typosquatting_detector import (
    TyposquattingAlert,
    TyposquattingDetector,
    TyposquattingReport,
)

# [20251226_FEATURE] Pro tier features
from .vulnerability_reachability import (
    ReachabilityResult,
    VulnerabilityReachabilityAnalyzer,
)
from .vulnerability_scanner import (  # [20251225_BUGFIX] Export for MCP tools
    DependencyParser,
    ScanResult,
    VulnerabilityFinding,
    VulnerabilityScanner,
)

__all__ = [
    # Community tier
    "VulnerabilityScanner",
    "ScanResult",
    "VulnerabilityFinding",
    "DependencyParser",
    # OSV client
    "OSVClient",
    "Vulnerability",
    "OSVError",
    # OSV constants
    "OSV_API_URL",
    "OSV_BATCH_URL",
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES",
    "RETRY_DELAY",
    # Pro tier
    "VulnerabilityReachabilityAnalyzer",
    "ReachabilityResult",
    "FalsePositiveReducer",
    "FalsePositiveAssessment",
    "SeverityContextualizer",
    "ContextualizedSeverity",
    # Enterprise tier
    "LicenseComplianceScanner",
    "LicenseInfo",
    "ComplianceReport",
    "TyposquattingDetector",
    "TyposquattingAlert",
    "TyposquattingReport",
    "SupplyChainRiskScorer",
    "RiskScore",
    "SupplyChainReport",
]
