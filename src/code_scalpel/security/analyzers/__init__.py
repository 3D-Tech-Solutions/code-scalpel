"""
Security Analyzers - Core security analysis tools.

[20251225_FEATURE] Created as part of Project Reorganization Issue #8.
[20251226_FEATURE] v3.2.9 - Added Pro/Enterprise tier analyzers.

This module contains the core security analysis tools:
- security_analyzer.py: Main vulnerability detection engine
- taint_tracker.py: Data flow taint tracking
- unified_sink_detector.py: Polyglot sink detection
- cross_file_taint.py: Cross-file taint flow analysis

Pro Tier:
- sanitizer_detector.py: Sanitization function detection
- confidence_scorer.py: Vulnerability confidence scoring
- false_positive_analyzer.py: False positive reduction

Enterprise Tier:
- policy_engine.py: Custom policy enforcement
- compliance_mapper.py: Compliance framework mapping
- custom_rules.py: Organization-specific rules
"""

from .compliance_mapper import ComplianceMapper
from .confidence_scorer import ConfidenceScorer
from .cross_file_taint import CrossFileTaintTracker
from .custom_rules import CustomRule, CustomRuleResult, CustomRulesEngine
from .false_positive_analyzer import FalsePositiveAnalyzer

# Enterprise tier
from .policy_engine import PolicyEngine, PolicyViolation

# Pro tier
from .sanitizer_detector import SanitizerDetector, SanitizerMatch
from .security_analyzer import SecurityAnalysisResult, SecurityAnalyzer
from .taint_tracker import TaintInfo, TaintLevel, TaintTracker
from .unified_sink_detector import DetectedSink, UnifiedSinkDetector

__all__ = [
    # Security Analyzer
    "SecurityAnalyzer",
    "SecurityAnalysisResult",
    # Taint Tracker
    "TaintTracker",
    "TaintLevel",
    "TaintInfo",
    # Unified Sink Detector
    "UnifiedSinkDetector",
    "DetectedSink",
    # Cross-File Taint
    "CrossFileTaintTracker",
    # Pro Tier
    "SanitizerDetector",
    "SanitizerMatch",
    "ConfidenceScorer",
    "FalsePositiveAnalyzer",
    # Enterprise Tier
    "PolicyEngine",
    "PolicyViolation",
    "ComplianceMapper",
    "CustomRulesEngine",
    "CustomRule",
    "CustomRuleResult",
]
