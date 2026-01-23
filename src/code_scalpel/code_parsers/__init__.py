# __init__.py
"""
Code Parser Module - Multi-language code parsing and analysis.

This module provides a unified interface for parsing code in various languages
using different analysis tools.

[20251224_REFACTOR] polyglot/ module absorbed into code_parsers/:
    - polyglot/extractor.py → code_parsers/extractor.py
    - polyglot/typescript/* → code_parsers/typescript_parsers/
    - polyglot/alias_resolver.py → code_parsers/typescript_parsers/alias_resolver.py
    - polyglot/tsx_analyzer.py → code_parsers/typescript_parsers/tsx_analyzer.py
    - polyglot/contract_breach_detector.py → security/contract_breach_detector.py

    The polyglot/ module now re-exports from here with deprecation warnings.

[20251221_DEPRECATION] Old parsers/ module is DEPRECATED and should be removed:
    - parsers/ is a legacy minimal implementation with only Python support
    - code_parser/ is the current production-grade implementation
    - parsers/ is no longer used in production (only in legacy tests)

"""

from .base_parser import BaseParser, Language, ParseResult, PreprocessorConfig

# [20251224_FEATURE] Import from polyglot extractor (migrated from polyglot/)
from .extractor import (
    EXTENSION_MAP,
    PolyglotExtractionResult,
    PolyglotExtractor,
    detect_language,
    extract_from_code,
    extract_from_file,
)
from .extractor import (
    Language as PolyglotLanguage,  # Alias to avoid conflict with base_parser.Language
)
from .factory import ParserFactory
from .interface import IParser
from .python_parser import PythonParser

# Import parsers from python_parsers submodule
# These use lazy imports to avoid loading all dependencies at startup
from .python_parsers import (  # These will be available when their modules are complete; BanditParser,; Flake8Parser,; MypyParser,; PylintParser,; PydocstyleParser,; PycodestyleParser,; ProspectorParser,
    PythonASTParser,
    RuffParser,
)

# [20251224_FEATURE] TypeScript parser exports (migrated from polyglot/typescript/)
from .typescript_parsers import (
    AliasResolver,
    DecoratorAnalyzer,
    TypeNarrowing,
    TypeScriptAnalyzer,
    TypeScriptParser,
)

__all__ = [
    # Base classes
    "BaseParser",
    "Language",
    "ParseResult",
    "PreprocessorConfig",
    "IParser",
    "ParserFactory",
    "PythonParser",
    # Python parsers
    "PythonASTParser",
    "RuffParser",
    # Polyglot extractor (migrated from polyglot/)
    "PolyglotExtractor",
    "PolyglotExtractionResult",
    "detect_language",
    "extract_from_file",
    "extract_from_code",
    "EXTENSION_MAP",
    "PolyglotLanguage",
    # TypeScript parsers (migrated from polyglot/typescript/)
    "TypeScriptParser",
    "TypeScriptAnalyzer",
    "TypeNarrowing",
    "DecoratorAnalyzer",
    "AliasResolver",
]
