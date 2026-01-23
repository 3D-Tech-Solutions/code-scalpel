"""
UnifiedExtractor - DEPRECATED: Moved to code_scalpel.surgery.unified_extractor.

# [20251224_DEPRECATE] This module has been moved to surgery/unified_extractor.py
# as part of Issue #2 in PROJECT_REORG_REFACTOR.md Phase 1.
# This file provides backward-compatibility aliases.
# Import from code_scalpel.surgery.unified_extractor instead.

Migration:
    # Old (deprecated):
    from code_scalpel.unified_extractor import UnifiedExtractor

    # New (recommended):
    from code_scalpel.surgery import UnifiedExtractor
"""

import warnings

warnings.warn(
    "code_scalpel.unified_extractor is deprecated. " "Import from code_scalpel.surgery instead.",
    DeprecationWarning,
    stacklevel=2,
)

# [20260102_REFACTOR] Backward-compat shim keeps imports below for legacy users.
# ruff: noqa: E402
# Re-export everything from new location for backward compatibility
from code_scalpel.surgery.unified_extractor import (  # Convenience functions
    FileSummary,
    ImportInfo,
    Language,
    SignatureInfo,
    SymbolInfo,
    UnifiedExtractionResult,
    UnifiedExtractor,
    detect_language,
    extract_from_code,
    extract_from_file,
)

__all__ = [
    "UnifiedExtractor",
    "UnifiedExtractionResult",
    "Language",
    "SymbolInfo",
    "ImportInfo",
    "FileSummary",
    "SignatureInfo",
    "detect_language",
    "extract_from_file",
    "extract_from_code",
]
