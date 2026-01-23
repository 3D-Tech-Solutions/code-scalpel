"""
Code Scalpel Polyglot Module - Multi-language code analysis.

[20251224_DEPRECATION] v3.2.0 - This module is DEPRECATED.
Functionality has been migrated to code_parsers/ for architectural consistency:
    - polyglot/extractor.py → code_parsers/extractor.py
    - polyglot/typescript/* → code_parsers/typescript_parsers/
    - polyglot/alias_resolver.py → code_parsers/typescript_parsers/alias_resolver.py
    - polyglot/tsx_analyzer.py → code_parsers/typescript_parsers/tsx_analyzer.py
    - polyglot/contract_breach_detector.py → security/contract_breach_detector.py

This module provides backward-compatible aliases that will be removed in v3.3.0.

Migration Guide:
    # Old imports (deprecated):
    from code_scalpel.polyglot import PolyglotExtractor, Language
    from code_scalpel.polyglot.extractor import detect_language

    # New imports (recommended):
    from code_scalpel.code_parsers import PolyglotExtractor, Language
    from code_scalpel.code_parsers.extractor import detect_language
    from code_scalpel.code_parsers.typescript_parsers import TypeScriptParser

[20251214_FEATURE] v2.0.0 - Unified interface for Python, JavaScript, TypeScript, and Java.

This module provides:
- PolyglotExtractor: Multi-language code extraction
- Language detection from file extensions
- Unified IR-based analysis




"""

import warnings

# [20251224_DEPRECATION] Issue deprecation warning on module import
warnings.warn(
    "The 'code_scalpel.polyglot' module is deprecated and will be removed in v3.3.0. "
    "Use 'code_scalpel.code_parsers' instead. "
    "See migration guide in module docstring.",
    DeprecationWarning,
    stacklevel=2,
)

# [20260102_REFACTOR] Backward-compat shim keeps imports below for legacy users.
# ruff: noqa: E402
# [20251224_REFACTOR] Import from new locations for backward compatibility
from code_scalpel.code_parsers.extractor import (
    EXTENSION_MAP,
    Language,
    PolyglotExtractionResult,
    PolyglotExtractor,
    detect_language,
    extract_from_code,
    extract_from_file,
)

__all__ = [
    "Language",
    "PolyglotExtractor",
    "PolyglotExtractionResult",
    "detect_language",
    "extract_from_file",
    "extract_from_code",
    "EXTENSION_MAP",
]
