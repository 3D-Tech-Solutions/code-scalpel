#!/usr/bin/env python3
"""
JavaScript Parsers Module - Comprehensive JavaScript/TypeScript code analysis.

This module provides multiple JavaScript parsing and analysis tools:

Parsers:
    JavaScriptParser (esprima)  - Pure Python AST parsing with detailed extraction
    TreeSitterJSParser          - Fast native incremental parsing
    TypeScriptParser            - TypeScript type extraction and analysis
    FlowParser                  - Facebook Flow type checking integration
    BabelParser                 - Modern ECMAScript feature detection

Linting & Style:
    ESLintParser                - Pluggable linting with directive parsing
    JSHintParser                - Error detection and code quality
    StandardJSParser            - Zero-config JavaScript style guide
    PrettierFormatter           - Code formatting verification

Code Quality:
    CodeQualityAnalyzer         - Comprehensive code smell detection

Features:
    Core Analysis:
        - Cognitive & cyclomatic complexity calculation
        - Halstead complexity metrics (vocabulary, volume, difficulty, effort)
        - Function call graph building
        - Import/export dependency tracking
        - CommonJS vs ES6 module detection
        - Maintainability index calculation

    Security Analysis:
        - XSS vulnerability detection (innerHTML, document.write, eval)
        - Hardcoded secrets detection (API keys, passwords)
        - eval/Function constructor detection
        - setTimeout/setInterval string argument detection

    Code Quality Checks:
        - Callback hell / deep nesting detection
        - Magic number/string detection
        - Long function detection (configurable threshold)
        - Too many parameters detection
        - Duplicate code block detection
        - Empty catch block detection
        - Console.log/debugger statement detection
        - Nested ternary detection
        - Complex boolean condition detection
        - Promise anti-pattern detection

    Framework Detection:
        - React (components, hooks, JSX)
        - Vue (Options API, Composition API)
        - Angular (components, services, decorators)
        - Express.js / Next.js / NestJS
        - jQuery, Redux, Lodash

    ESLint Integration:
        - Rule documentation URL generation
        - Inline directive parsing (eslint-disable/enable)
        - Suppression report generation
"""

from .javascript_parsers_babel import (
    BabelAnalysis,
    BabelConfig,
    BabelParser,
    BabelPlugin,
    BabelPreset,
    ECMAScriptVersion,
    JSXElement,
    ModernJSSyntax,
    ProposalStage,
    SyntaxFeature,
    TransformationResult,
)
from .javascript_parsers_code_quality import (
    CodeQualityAnalyzer,
    CodeQualityResult,
    CodeSmell,
    CodeSmellSeverity,
    CodeSmellType,
    DuplicateCodeBlock,
    FrameworkDetection,
    FrameworkType,
    ModuleAnalysis,
    ModuleType,
    TodoComment,
)
from .javascript_parsers_eslint import (
    ESLintConfig,
    ESLintDirective,
    ESLintDirectiveType,
    ESLintFileResult,
    ESLintParser,
    ESLintSeverity,
    ESLintViolation,
)
from .javascript_parsers_esprima import (  # Dataclasses for analysis
    CodeMetrics,
    DesignPatternMatch,
    DesignPatternType,
    ExportInfo,
    FunctionCallInfo,
    FunctionInfo,
    HalsteadMetrics,
    ImportInfo,
    JavaScriptParser,
    ScopeInfo,
    SecurityIssue,
    SecuritySeverity,
)
from .javascript_parsers_flow import (
    FlowAnalysis,
    FlowConfig,
    FlowCoverage,
    FlowError,
    FlowInterface,
    FlowParser,
    FlowSeverity,
    FlowTypeAlias,
    FlowTypeAnnotation,
    FlowTypeKind,
    FlowTypeParameter,
    Variance,
)
from .javascript_parsers_jshint import (
    JSHintConfig,
    JSHintError,
    JSHintFileResult,
    JSHintParser,
    JSHintSeverity,
)
from .javascript_parsers_prettier import (
    EndOfLine,
    FormatDiff,
    FormatResult,
    HTMLWhitespaceSensitivity,
    PrettierConfig,
    PrettierFormatter,
)
from .javascript_parsers_prettier import PrettierParser as PrettierParserType
from .javascript_parsers_prettier import (
    ProseWrap,
    QuoteType,
    TrailingComma,
)
from .javascript_parsers_standard import (
    StandardConfig,
    StandardFileResult,
    StandardJSParser,
    StandardSeverity,
    StandardViolation,
)
from .javascript_parsers_treesitter import (
    ExportStatement,
    ImportStatement,
    JSLanguageVariant,
    JSSymbol,
    JSXComponent,
)
from .javascript_parsers_treesitter import SyntaxError as TreeSitterSyntaxError
from .javascript_parsers_treesitter import (
    TreeSitterJSParser,
    TreeSitterNode,
    TreeSitterParseResult,
)
from .javascript_parsers_typescript import (
    DecoratorKind,
    DecoratorUsage,
    EnumDeclaration,
    EnumMember,
    IndexSignature,
    InterfaceDeclaration,
    MethodSignature,
    NamespaceDeclaration,
    ParameterDeclaration,
    PropertySignature,
    TypeAliasDeclaration,
    TypeAnnotation,
    TypeGuard,
    TypeKind,
    TypeParameter,
    TypeScriptAnalysis,
    TypeScriptParser,
)

__all__ = [
    # Core parser (esprima)
    "JavaScriptParser",
    # Core analysis dataclasses
    "FunctionInfo",
    "FunctionCallInfo",
    "HalsteadMetrics",
    "ScopeInfo",
    "SecurityIssue",
    "SecuritySeverity",
    "DesignPatternType",
    "DesignPatternMatch",
    "ImportInfo",
    "ExportInfo",
    "CodeMetrics",
    # ESLint
    "ESLintParser",
    "ESLintViolation",
    "ESLintFileResult",
    "ESLintConfig",
    "ESLintSeverity",
    "ESLintDirective",
    "ESLintDirectiveType",
    # JSHint
    "JSHintParser",
    "JSHintError",
    "JSHintFileResult",
    "JSHintConfig",
    "JSHintSeverity",
    # Prettier
    "PrettierFormatter",
    "PrettierConfig",
    "FormatDiff",
    "FormatResult",
    "PrettierParserType",
    "EndOfLine",
    "QuoteType",
    "TrailingComma",
    "ProseWrap",
    "HTMLWhitespaceSensitivity",
    # StandardJS
    "StandardJSParser",
    "StandardViolation",
    "StandardFileResult",
    "StandardConfig",
    "StandardSeverity",
    # Tree-sitter
    "TreeSitterJSParser",
    "TreeSitterNode",
    "TreeSitterParseResult",
    "JSLanguageVariant",
    "JSSymbol",
    "JSXComponent",
    "ImportStatement",
    "ExportStatement",
    "TreeSitterSyntaxError",
    # TypeScript
    "TypeScriptParser",
    "TypeScriptAnalysis",
    "TypeKind",
    "TypeAnnotation",
    "TypeParameter",
    "InterfaceDeclaration",
    "TypeAliasDeclaration",
    "PropertySignature",
    "MethodSignature",
    "IndexSignature",
    "ParameterDeclaration",
    "EnumDeclaration",
    "EnumMember",
    "DecoratorUsage",
    "DecoratorKind",
    "NamespaceDeclaration",
    "TypeGuard",
    # Babel
    "BabelParser",
    "BabelAnalysis",
    "BabelConfig",
    "BabelPlugin",
    "BabelPreset",
    "ECMAScriptVersion",
    "ProposalStage",
    "SyntaxFeature",
    "TransformationResult",
    "JSXElement",
    "ModernJSSyntax",
    # Flow
    "FlowParser",
    "FlowAnalysis",
    "FlowConfig",
    "FlowError",
    "FlowCoverage",
    "FlowSeverity",
    "FlowTypeKind",
    "FlowTypeAnnotation",
    "FlowTypeParameter",
    "FlowTypeAlias",
    "FlowInterface",
    "Variance",
    # Code Quality
    "CodeQualityAnalyzer",
    "CodeQualityResult",
    "CodeSmell",
    "CodeSmellType",
    "CodeSmellSeverity",
    "TodoComment",
    "DuplicateCodeBlock",
    "FrameworkDetection",
    "FrameworkType",
    "ModuleAnalysis",
    "ModuleType",
    # Registry
    "JavaScriptParserRegistry",
]


class JavaScriptParserRegistry:
    """Registry for JavaScript/TypeScript static-analysis tool parsers.

    [20260304_FEATURE] Polyglot Phase 2: lazy-load factory for JS/TS tools.
    Registers parsers that have execute_* methods (they run the tool themselves).
    ESLint executes the tool itself via analyze_file() and is now included.
    Note: npm-audit is invoked on the *project directory*, not a single file;
    callers should pass str(Path(file_path).parent) as the path argument.
    """

    _TOOL_MAP: dict = {
        "npm-audit": ("javascript_parsers_npm_audit", "NpmAuditParser"),
        "npm_audit": ("javascript_parsers_npm_audit", "NpmAuditParser"),
        # [20260304_FEATURE] ESLint now has execute_eslint() wrapper
        "eslint": ("javascript_parsers_eslint", "ESLintParser"),
    }

    def get_parser(self, tool_name: str):
        """Return an instantiated parser for *tool_name*.

        Args:
            tool_name: One of the recognised tool identifiers (case-insensitive).

        Raises:
            ValueError: If *tool_name* is not a recognised executable tool.
        """
        import importlib

        key = tool_name.lower()
        if key not in self._TOOL_MAP:
            raise ValueError(
                f"Unknown JavaScript parser tool: {tool_name!r}. "
                f"Valid options: {sorted(set(self._TOOL_MAP.keys()))}"
            )
        module_name, class_name = self._TOOL_MAP[key]
        module = importlib.import_module(f".{module_name}", package=__package__)
        return getattr(module, class_name)()
