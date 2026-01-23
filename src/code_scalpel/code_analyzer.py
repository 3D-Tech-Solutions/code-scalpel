"""
CodeAnalyzer - DEPRECATED: Moved to code_scalpel.analysis.code_analyzer.

# [20251224_DEPRECATE] This module has been moved to analysis/code_analyzer.py
# as part of Issue #3 in PROJECT_REORG_REFACTOR.md Phase 1.
# This file provides backward-compatibility aliases.
# Import from code_scalpel.analysis.code_analyzer instead.

Migration:
    # Old (deprecated):
    from code_scalpel.code_analyzer import CodeAnalyzer

    # New (recommended):
    from code_scalpel.analysis import CodeAnalyzer
"""

import warnings

warnings.warn(
    "code_scalpel.code_analyzer is deprecated. " "Import from code_scalpel.analysis instead.",
    DeprecationWarning,
    stacklevel=2,
)

# [20260102_REFACTOR] Backward-compat shim keeps imports below for legacy users.
# ruff: noqa: E402
# Re-export everything from new location for backward compatibility
from code_scalpel.analysis.code_analyzer import (
    AnalysisLanguage,
    AnalysisLevel,
    AnalysisMetrics,
    AnalysisResult,
    CodeAnalyzer,
    DeadCodeItem,
    RefactorSuggestion,
    analyze_code,
)

__all__ = [
    "CodeAnalyzer",
    "AnalysisResult",
    "AnalysisMetrics",
    "AnalysisLevel",
    "AnalysisLanguage",
    "DeadCodeItem",
    "RefactorSuggestion",
    "analyze_code",
]
