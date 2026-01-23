"""
Parser Adapters - Bridge existing parsers to IParser interface.

[20251221_FEATURE] Adapters that wrap language-specific parsers to implement
the IParser interface for unified factory usage.

This module provides adapters for:
- JavaScriptParser → IParser
- TypeScriptParser → IParser (via JavaScriptParser)
- TreeSitterJavaParser → IParser

Usage:
    from code_parsers.adapters import JavaScriptParserAdapter, JavaParserAdapter
    from code_parsers import ParserFactory, Language

    # Register adapters
    ParserFactory.register_parser(Language.JAVASCRIPT, JavaScriptParserAdapter)
    ParserFactory.register_parser(Language.JAVA, JavaParserAdapter)

    # Use via factory
    parser = ParserFactory.get_parser(Language.JAVASCRIPT)
    result = parser.parse(code)
"""

from .java_adapter import JavaParserAdapter  # type: ignore[import-not-found]
from .javascript_adapter import JavaScriptParserAdapter, TypeScriptParserAdapter

# [20251224_FEATURE] Additional language adapter stubs
# Note: These are stubs - implementations are in progress
try:
    from .cpp_adapter import CppParserAdapter
except (ImportError, NotImplementedError):
    CppParserAdapter = None  # type: ignore

try:
    from .csharp_adapter import CSharpParserAdapter
except (ImportError, NotImplementedError):
    CSharpParserAdapter = None  # type: ignore

try:
    from .go_adapter import GoParserAdapter
except (ImportError, NotImplementedError):
    GoParserAdapter = None  # type: ignore

try:
    from .kotlin_adapter import KotlinParserAdapter
except (ImportError, NotImplementedError):
    KotlinParserAdapter = None  # type: ignore

try:
    from .ruby_adapter import RubyParserAdapter
except (ImportError, NotImplementedError):
    RubyParserAdapter = None  # type: ignore

# [20260120_BUGFIX] PhpParserAdapter import removed - implementation not present
# try:
#     from .php_adapter import PhpParserAdapter
# except (ImportError, NotImplementedError):
#     PhpParserAdapter = None  # type: ignore
PhpParserAdapter = None  # type: ignore

try:
    from .swift_adapter import SwiftParserAdapter
except (ImportError, NotImplementedError):
    SwiftParserAdapter = None  # type: ignore


__all__ = [
    "JavaScriptParserAdapter",
    "TypeScriptParserAdapter",
    "JavaParserAdapter",
    "CppParserAdapter",
    "CSharpParserAdapter",
    "GoParserAdapter",
    "KotlinParserAdapter",
    "RubyParserAdapter",
    # "PhpParserAdapter",  # [20260120_BUGFIX] Removed from __all__ - implementation not present
    "SwiftParserAdapter",
]
