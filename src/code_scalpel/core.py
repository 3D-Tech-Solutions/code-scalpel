"""
CodeAnalysisToolkit - DEPRECATED: Moved to code_scalpel.analysis.core.

# [20251225_DEPRECATE] This module has been moved to analysis/core.py
# as part of Issue #3 in PROJECT_REORG_REFACTOR.md Phase 1.
# This file provides backward-compatibility aliases.
# Import from code_scalpel.analysis.core instead.

Migration:
    # Old (deprecated):
    from code_scalpel.core import CodeAnalysisToolkit

    # New (recommended):
    from code_scalpel.analysis import CodeAnalysisToolkit
"""

import warnings

warnings.warn(
    "code_scalpel.core is deprecated. " "Import from code_scalpel.analysis instead.",
    DeprecationWarning,
    stacklevel=2,
)

# [20260102_REFACTOR] Backward-compat shim keeps imports below for legacy users.
# ruff: noqa: E402
# Re-export everything from new location for backward compatibility
from code_scalpel.analysis.core import CodeAnalysisToolkit

__all__ = [
    "CodeAnalysisToolkit",
]
