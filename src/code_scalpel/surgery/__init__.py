"""
Surgery Module - Surgical code extraction and patching for LLM-driven operations.

[20251224_REFACTOR] Created as part of Project Reorganization Issue #2.
Consolidated surgical code tools from top-level modules.

This module provides:
- SurgicalExtractor: Precision code extraction for token-efficient LLM interactions
- SurgicalPatcher: Safe code modification for LLM-driven refactoring
- UnifiedExtractor: Universal extraction across all languages
- UnifiedPatcher: Cross-language patching with language detection

Migration Guide:
    # Old imports (deprecated in v3.3.0):
    from code_scalpel.surgical_extractor import SurgicalExtractor
    from code_scalpel.surgical_patcher import SurgicalPatcher
    from code_scalpel.unified_extractor import UnifiedExtractor

    # New imports (recommended):
    from code_scalpel.surgery import SurgicalExtractor, SurgicalPatcher, UnifiedExtractor
    # Or:
    from code_scalpel.surgery.surgical_extractor import SurgicalExtractor
    from code_scalpel.surgery.surgical_patcher import SurgicalPatcher
    from code_scalpel.surgery.unified_extractor import UnifiedExtractor

"""

# [20251224_REFACTOR] Import from submodules
from .surgical_extractor import (
    ContextualExtraction,
    CrossFileResolution,
    CrossFileSymbol,
    ExtractionResult,
    SurgicalExtractor,
)
from .surgical_patcher import (
    PatchLanguage,
    PatchResult,
    PolyglotPatcher,
    SurgicalPatcher,
    UnifiedPatcher,
)
from .unified_extractor import (
    FileSummary,
    ImportInfo,
    Language,
    SignatureInfo,
    SymbolInfo,
    UnifiedExtractionResult,
    UnifiedExtractor,
)

__all__ = [
    # Surgical Extractor
    "SurgicalExtractor",
    "ExtractionResult",
    "ContextualExtraction",
    "CrossFileSymbol",
    "CrossFileResolution",
    # Surgical Patcher
    "SurgicalPatcher",
    "PatchResult",
    "PatchLanguage",
    "UnifiedPatcher",
    "PolyglotPatcher",
    # Unified Extractor
    "UnifiedExtractor",
    "UnifiedExtractionResult",
    "Language",
    "SymbolInfo",
    "ImportInfo",
    "FileSummary",
    "SignatureInfo",
]

__version__ = "1.0.0"
