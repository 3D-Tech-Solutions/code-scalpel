"""
TypeScript/JavaScript Parser Module.

[20251224_REFACTOR] Migrated from polyglot/typescript/ to code_parsers/typescript_parsers/
for architectural consistency with {lang}_parsers/ naming convention.

This module provides AST parsing and analysis for TypeScript and JavaScript
using tree-sitter for parsing and a normalized IR for cross-language analysis.

Architecture:
    TypeScript/JS Source
           ↓
    tree-sitter-typescript (Native Parser)
           ↓
    ESTree-compatible AST
           ↓
    Code Scalpel Normalized IR  ← Same IR as Python
           ↓
    PDG/Symbolic/Security Analysis (Shared)

Dependencies:
    - tree-sitter>=0.21.0 (optional, fallback to regex)
    - tree-sitter-typescript>=0.21.0 (optional)
    - tree-sitter-javascript>=0.21.0 (optional)

Exports:
    - TypeScriptParser: Low-level AST parser
    - TypeScriptAnalyzer: Structural analysis and metrics
    - TypeNarrowing: Control-flow type narrowing analysis
    - DecoratorAnalyzer: TypeScript decorator extraction
    - AliasResolver: Module alias resolution (tsconfig, webpack, vite)
    - TSX Utilities: React component detection and JSX analysis

ESTIMATED TOTAL TESTS: 570
"""

from .alias_resolver import AliasResolver, create_alias_resolver
from .analyzer import (
    NormalizedClass,
    NormalizedFunction,
    TSAnalysisResult,
    TypeScriptAnalyzer,
    normalize_typescript_class,
    normalize_typescript_function,
)
from .decorator_analyzer import (
    SECURITY_SINK_DECORATORS,
    DecoratorAnalyzer,
    extract_decorators_from_code,
)

# [20251224_REFACTOR] Updated imports for new location
from .parser import Decorator, TSNode, TSNodeType, TSParseResult, TypeScriptParser
from .tsx_analyzer import (
    ReactComponentInfo,
    detect_server_directive,
    has_jsx_syntax,
    is_react_component,
    normalize_jsx_syntax,
)
from .type_narrowing import (
    REDUCED_RISK_TYPES,
    SAFE_PRIMITIVE_TYPES,
    BranchState,
    NarrowedType,
    NarrowingResult,
    TypeGuard,
    TypeNarrowing,
    analyze_type_narrowing,
)

__all__ = [
    # Parser
    "TypeScriptParser",
    "TSParseResult",
    "TSNode",
    "TSNodeType",
    "Decorator",
    # Analyzer
    "TypeScriptAnalyzer",
    "TSAnalysisResult",
    "NormalizedFunction",
    "NormalizedClass",
    "normalize_typescript_function",
    "normalize_typescript_class",
    # Type Narrowing
    "TypeNarrowing",
    "NarrowingResult",
    "TypeGuard",
    "BranchState",
    "NarrowedType",
    "analyze_type_narrowing",
    "SAFE_PRIMITIVE_TYPES",
    "REDUCED_RISK_TYPES",
    # Decorator Analyzer
    "DecoratorAnalyzer",
    "extract_decorators_from_code",
    "SECURITY_SINK_DECORATORS",
    # Alias Resolver
    "AliasResolver",
    "create_alias_resolver",
    # TSX Analyzer
    "ReactComponentInfo",
    "detect_server_directive",
    "has_jsx_syntax",
    "is_react_component",
    "normalize_jsx_syntax",
]

__version__ = "1.0.0"
