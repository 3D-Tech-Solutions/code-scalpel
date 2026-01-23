"""
Security Module - Comprehensive security analysis for Code Scalpel.

[20251225_FEATURE] Created as part of Project Reorganization Issues #8-10.

This module organizes all security analysis tools into logical subdirectories:

Subdirectories:
    analyzers/: Core security analysis (taint tracking, sink detection)
    type_safety/: Type-related security (type evaporation detection)
    dependencies/: Dependency vulnerability scanning
    sanitization/: Sanitizer effectiveness analysis
    secrets/: Secret detection
    ml/: ML-based vulnerability prediction

Tier Requirements:
    - COMMUNITY: Basic security scanning
    - PRO: security_scan, unified_sink_detect, scan_dependencies
    - ENTERPRISE: cross_file_security_scan, type_evaporation_scan

Usage:
    from code_scalpel.security import SecurityAnalyzer, TaintTracker
    from code_scalpel.security.analyzers import UnifiedSinkDetector
    from code_scalpel.security.type_safety import TypeEvaporationDetector
"""

# [20251225_FEATURE] Re-export from analyzers (core security)
from .analyzers import (
    CrossFileTaintTracker,
    DetectedSink,
    SecurityAnalysisResult,
    SecurityAnalyzer,
    TaintInfo,
    TaintLevel,
    TaintTracker,
    UnifiedSinkDetector,
)

# [20251225_FEATURE] Import contract_breach_detector from current location
from .contract_breach_detector import ContractBreach, ContractBreachDetector

# [20251225_FEATURE] Re-export from dependencies
from .dependencies import ScanResult, VulnerabilityFinding, VulnerabilityScanner

# [20251225_FEATURE] Re-export from ml
from .ml import VulnerabilityPrediction, VulnerabilityPredictor

# [20251225_FEATURE] Re-export from sanitization
from .sanitization import SanitizerAnalyzer, SanitizerEffectiveness, SanitizerType

# [20251225_FEATURE] Re-export from secrets
from .secrets import SecretScanner

# [20251225_FEATURE] Re-export from type_safety
from .type_safety import TypeEvaporationDetector, TypeEvaporationVulnerability

__all__ = [
    # Core Analyzers
    "SecurityAnalyzer",
    "SecurityAnalysisResult",
    "TaintTracker",
    "TaintLevel",
    "TaintInfo",
    "UnifiedSinkDetector",
    "DetectedSink",
    "CrossFileTaintTracker",
    # Type Safety
    "TypeEvaporationDetector",
    "TypeEvaporationVulnerability",
    # Dependencies
    "VulnerabilityScanner",
    "ScanResult",
    "VulnerabilityFinding",
    # Sanitization
    "SanitizerAnalyzer",
    "SanitizerType",
    "SanitizerEffectiveness",
    # Secrets
    "SecretScanner",
    # ML
    "VulnerabilityPredictor",
    "VulnerabilityPrediction",
    # Contract Breach
    "ContractBreachDetector",
    "ContractBreach",
]

__version__ = "1.0.0"
