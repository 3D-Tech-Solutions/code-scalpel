"""
ErrorScanner - DEPRECATED: Moved to code_scalpel.quality_assurance.error_scanner.

# [20251224_DEPRECATE] This module has been moved to quality_assurance/error_scanner.py
# as part of Issue #1 in PROJECT_REORG_REFACTOR.md Phase 1.
# This file provides backward-compatibility aliases.
# Import from code_scalpel.quality_assurance.error_scanner instead.

Migration:
    # Old (deprecated):
    from code_scalpel.error_scanner import ErrorScanner

    # New (recommended):
    from code_scalpel.quality_assurance import ErrorScanner
"""

import warnings

warnings.warn(
    "code_scalpel.error_scanner is deprecated. " "Import from code_scalpel.quality_assurance instead.",
    DeprecationWarning,
    stacklevel=2,
)

# [20260102_REFACTOR] Backward-compat shim keeps imports below for legacy users.
# ruff: noqa: E402
# Re-export everything from new location for backward compatibility
from code_scalpel.quality_assurance.error_scanner import (
    CodeError,
    ErrorScanner,
    ErrorSeverity,
    ScanResults,
)

__all__ = [
    "ErrorScanner",
    "ScanResults",
    "CodeError",
    "ErrorSeverity",
]
