"""
SurgicalPatcher - DEPRECATED: Moved to code_scalpel.surgery.surgical_patcher.

# [20251224_DEPRECATE] This module has been moved to surgery/surgical_patcher.py
# as part of Issue #2 in PROJECT_REORG_REFACTOR.md Phase 1.
# This file provides backward-compatibility aliases.
# Import from code_scalpel.surgery.surgical_patcher instead.

Migration:
    # Old (deprecated):
    from code_scalpel.surgical_patcher import SurgicalPatcher

    # New (recommended):
    from code_scalpel.surgery import SurgicalPatcher
"""

import warnings

warnings.warn(
    "code_scalpel.surgical_patcher is deprecated. " "Import from code_scalpel.surgery instead.",
    DeprecationWarning,
    stacklevel=2,
)

# [20260102_REFACTOR] Backward-compat shim keeps imports below for legacy users.
# ruff: noqa: E402
# Re-export everything from new location for backward compatibility
from code_scalpel.surgery.surgical_patcher import (  # Convenience functions
    PatchLanguage,
    PatchResult,
    PolyglotPatcher,
    SurgicalPatcher,
    UnifiedPatcher,
    update_class_in_file,
    update_function_in_file,
    update_method_in_file,
)

__all__ = [
    "SurgicalPatcher",
    "PatchResult",
    "PatchLanguage",
    "UnifiedPatcher",
    "PolyglotPatcher",
    "update_function_in_file",
    "update_class_in_file",
    "update_method_in_file",
]
